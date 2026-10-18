"""Integration tests for the CLI RAG wiring (TASK-RAG-002).

Exercises the production wiring that turns "we built RAG" into "RAG is
on in production":

* :func:`study_tutor.cli.rag_wiring.build_rag_providers` —
  serve-startup helper that opens the persistent collection and wires
  it into :func:`set_collection_provider`.
* :func:`study_tutor.cli.main._build_coach_handover` — the closure
  that routes the four-branch decision into the verifier seam on
  every Player turn.

Five tests, mirroring the AC bullets:

1. Provider-wired path — fake ``chromadb.PersistentClient`` returns a
   stub collection; assert the provider seam ends up wired.
2. Provider-missing path — non-existent persist dir → structured
   ``rag_disabled`` log + provider stays unwired; orchestrator factory
   still constructs.
3. Closure end-to-end — Macbeth + AO1+AO2 → primary-first retrieval +
   verifier annotation in the rewritten response.
4. AO3 bypass — focus_aos={"AO3"} → zero retrieve calls;
   ``retrieval_skipped_reason="ao3_only:training_first"``.
5. Verifier-exception regression — ``verify_quotes`` raises →
   original response unchanged + ``verifier_exception=True``; no
   exception bubbles out of the closure.

Hermeticity
-----------
No network. No filesystem writes outside ``tmp_path``. No real ChromaDB
or sentence-transformers — the fake collection is duck-typed against
the same surface ``test_rag_end_to_end.py`` uses; the reranker factory
forces the no-rerank graceful-degradation path.
"""

from __future__ import annotations

import logging
import sys
import types
from types import SimpleNamespace
from typing import Any, Iterator

import pytest

from study_tutor.cli.main import _build_coach_handover
from study_tutor.cli.rag_wiring import (
    RAG_COLLECTION_ENV,
    RAG_PERSIST_DIR_ENV,
    build_rag_providers,
)
from study_tutor.knowledge.corpus_models import (
    CorpusChunk,
    PlayCitationAnchor,
    SourceType,
)
from study_tutor.knowledge.quote_verifier import UNVERIFIED_QUOTE_TEXT
from study_tutor.knowledge.retrieval import (
    NON_AO3_SOURCE_TYPES,
    clear_primary_text_index,
    get_collection_provider,
    register_primary_text,
    reset_collection_provider,
    reset_embedder_probe,
    reset_reranker_factory,
    set_collection_provider,
    set_reranker_factory,
)
from study_tutor.roles.loader import load_role


# ---------------------------------------------------------------------------
# Fake ChromaDB collection — duplicated from
# ``tests/integration/test_rag_end_to_end.py`` (canonical site
# ``_FakeCollection`` at line ~179). Mirrors the AQA-filter-regex
# precedent in ``retrieval.py:395``: two copies that must remain in
# lock-step rather than a fragile cross-test import.
# ---------------------------------------------------------------------------


class _FakeCollection:
    """In-memory stand-in for a ``chromadb`` collection.

    Implements just enough of the real ``query`` surface to satisfy
    ``study_tutor.knowledge.retrieval._query_collection``.
    """

    def __init__(self, chunks: list[CorpusChunk]) -> None:
        self._chunks = chunks
        self.query_calls = 0

    def count(self) -> int:
        # The ADR-ARCH-032 per-subject coverage log reads this at wiring.
        return len(self._chunks)

    def query(
        self,
        *,
        query_texts: list[str],
        n_results: int,
        where: dict[str, Any],
    ) -> dict[str, Any]:
        self.query_calls += 1
        self.last_query = {
            "query_texts": query_texts,
            "n_results": n_results,
            "where": where,
        }

        text_name_filter: str | None = None
        allowed_source_types: set[str] = set()
        # A bare single-clause filter (text_name=None retrieval, boot probe)
        # is the clause itself; Chroma rejects a one-clause ``$and``.
        clauses = where.get("$and", [where])
        for clause in clauses:
            if "text_name" in clause:
                text_name_filter = clause["text_name"]
            if "source_type" in clause:
                allowed_source_types = set(clause["source_type"]["$in"])

        matched: list[CorpusChunk] = [
            chunk
            for chunk in self._chunks
            if (
                text_name_filter is None
                or chunk.text_name == text_name_filter
            )
            and chunk.source_type.value in allowed_source_types
        ]
        matched.sort(key=lambda c: c.chunk_index)
        matched = matched[:n_results]

        return {
            "metadatas": [
                [{"chunk_json": c.model_dump_json()} for c in matched]
            ],
            "documents": [[c.text for c in matched]],
            "distances": [[float(idx) for idx, _ in enumerate(matched)]],
        }


def _raise_import_error_factory() -> Any:
    """Reranker factory that raises ``ImportError`` (graceful-degradation path)."""
    raise ImportError("sentence_transformers not installed (test stub)")


# ---------------------------------------------------------------------------
# Macbeth fixture corpus — verbatim Shakespeare span the closure should
# annotate. Same canonical line as ``test_rag_end_to_end.py``.
# ---------------------------------------------------------------------------


_MACBETH_VERBATIM = "I have no spur to prick the sides of my intent"


@pytest.fixture
def macbeth_corpus() -> list[CorpusChunk]:
    """Three primary Macbeth chunks (Act 1 Scenes 5–7)."""
    return [
        CorpusChunk(
            text=(
                "Come, you spirits that tend on mortal thoughts, "
                "unsex me here, and fill me from the crown to the toe "
                "top-full of direst cruelty."
            ),
            source_type=SourceType.PRIMARY_TEXT,
            source_path="/fixture/primary_text/macbeth.txt",
            text_name="Macbeth",
            citation_anchor=PlayCitationAnchor(act=1, scene=5, line=40),
            chunk_index=0,
        ),
        CorpusChunk(
            text=(
                "If it were done when 'tis done, then 'twere well it were "
                f"done quickly. {_MACBETH_VERBATIM}, but only vaulting "
                "ambition, which o'erleaps itself."
            ),
            source_type=SourceType.PRIMARY_TEXT,
            source_path="/fixture/primary_text/macbeth.txt",
            text_name="Macbeth",
            citation_anchor=PlayCitationAnchor(act=1, scene=7, line=1),
            chunk_index=1,
        ),
        CorpusChunk(
            text=(
                "Is this a dagger which I see before me, the handle "
                "toward my hand? Come, let me clutch thee."
            ),
            source_type=SourceType.PRIMARY_TEXT,
            source_path="/fixture/primary_text/macbeth.txt",
            text_name="Macbeth",
            citation_anchor=PlayCitationAnchor(act=2, scene=1, line=33),
            chunk_index=2,
        ),
    ]


# ---------------------------------------------------------------------------
# Module-state isolation. Same pattern as
# ``tests/integration/test_rag_end_to_end.py``.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _isolate_retrieval_state() -> Iterator[None]:
    clear_primary_text_index()
    reset_collection_provider()
    reset_reranker_factory()
    reset_embedder_probe()
    yield
    clear_primary_text_index()
    reset_collection_provider()
    reset_reranker_factory()
    reset_embedder_probe()


# ---------------------------------------------------------------------------
# Helper: a fake ``chromadb`` module installed into ``sys.modules`` so
# ``import chromadb`` inside ``build_rag_providers`` returns our stub.
# ---------------------------------------------------------------------------


class _FakePersistentClient:
    """Minimal stand-in for ``chromadb.PersistentClient``.

    Stores constructor args for assertion and returns a pre-built
    collection from ``get_or_create_collection``.
    """

    def __init__(self, path: str) -> None:
        self.path = path
        self._collection: Any = None

    def install_collection(self, collection: Any) -> None:
        self._collection = collection

    def list_collections(self) -> list[Any]:
        # ADR-ARCH-032 D2 subject discovery consults this at wiring time;
        # an empty listing means only the env-resolved default-subject
        # collection gets wired — the pre-scoping behaviour these tests
        # pin.
        return []

    def get_or_create_collection(
        self, *, name: str, embedding_function: Any
    ) -> Any:
        # Stash for assertion in tests that care about EF wiring.
        self.last_collection_name = name
        self.last_embedding_function = embedding_function
        return self._collection


def _install_fake_chromadb_module(
    monkeypatch: pytest.MonkeyPatch,
    fake_client: _FakePersistentClient,
) -> None:
    """Install a fake ``chromadb`` and ``chromadb.utils.embedding_functions``.

    Both are stubbed so ``build_rag_providers`` finds a usable
    ``PersistentClient`` AND
    ``build_openai_embedding_function`` succeeds without contacting
    llama-swap. The EF stand-in is a sentinel object — we only assert
    it gets passed to ``get_or_create_collection``.
    """
    fake_module = types.ModuleType("chromadb")
    fake_module.PersistentClient = lambda path: fake_client  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "chromadb", fake_module)

    fake_ef_sentinel = object()

    def _fake_openai_ef(**_kwargs: Any) -> Any:
        return fake_ef_sentinel

    fake_utils = types.ModuleType("chromadb.utils")
    fake_ef_module = types.ModuleType("chromadb.utils.embedding_functions")
    fake_ef_module.OpenAIEmbeddingFunction = _fake_openai_ef  # type: ignore[attr-defined]
    fake_utils.embedding_functions = fake_ef_module  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "chromadb.utils", fake_utils)
    monkeypatch.setitem(
        sys.modules, "chromadb.utils.embedding_functions", fake_ef_module
    )


# ---------------------------------------------------------------------------
# Test 1 — provider-wired happy path.
# ---------------------------------------------------------------------------


def test_provider_wired_path(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    macbeth_corpus: list[CorpusChunk],
) -> None:
    """``build_rag_providers`` opens the fake client and installs the provider."""
    persist_dir = tmp_path / "chroma"
    persist_dir.mkdir()

    fake_collection = _FakeCollection(macbeth_corpus)
    fake_client = _FakePersistentClient(path=str(persist_dir))
    fake_client.install_collection(fake_collection)
    _install_fake_chromadb_module(monkeypatch, fake_client)

    monkeypatch.setenv(RAG_PERSIST_DIR_ENV, str(persist_dir))
    monkeypatch.setenv(RAG_COLLECTION_ENV, "test-collection-v1")

    role_config = load_role("tutor")
    build_rag_providers(role_config)

    provider = get_collection_provider()
    assert provider is not None, "provider should be wired after build"
    assert provider() is fake_collection, (
        "provider must return the same fake collection passed to "
        "get_or_create_collection"
    )
    assert fake_client.last_collection_name == "test-collection-v1"
    # The EF sentinel should have been passed through the construction
    # chain (DECISION-RAG-001 §3.1 — the EF must reach Chroma).
    assert fake_client.last_embedding_function is not None


# ---------------------------------------------------------------------------
# Test 2 — provider-missing path (persist dir absent) → graceful degrade.
# ---------------------------------------------------------------------------


def test_provider_missing_persist_dir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Missing persist dir → structured rag_disabled + provider stays unset."""
    missing = tmp_path / "does_not_exist"
    monkeypatch.setenv(RAG_PERSIST_DIR_ENV, str(missing))

    # Ensure chromadb is importable (or stubbed) so the failure mode
    # under test is *specifically* persist_dir_missing, not
    # chromadb_missing.
    fake_client = _FakePersistentClient(path=str(missing))
    _install_fake_chromadb_module(monkeypatch, fake_client)

    role_config = load_role("tutor")
    with caplog.at_level(logging.WARNING, logger="study_tutor.cli.rag_wiring"):
        build_rag_providers(role_config)

    assert get_collection_provider() is None, (
        "provider must remain unwired when persist dir is missing"
    )
    matched = [
        record
        for record in caplog.records
        if "rag_disabled" in record.getMessage()
        and "persist_dir_missing" in record.getMessage()
    ]
    assert matched, (
        f"expected event=rag_disabled reason=persist_dir_missing log; "
        f"got: {[r.getMessage() for r in caplog.records]}"
    )

    # Orchestrator factory should still construct successfully — the
    # graceful-degradation envelope MUST keep the serve loop alive.
    from study_tutor.cli.main import _build_orchestrator_factory

    factory = _build_orchestrator_factory(role_config)
    assert callable(factory)


# ---------------------------------------------------------------------------
# Test 3 — coach-handover closure end-to-end against the Macbeth fixture.
# ---------------------------------------------------------------------------


def test_closure_end_to_end_macbeth(
    macbeth_corpus: list[CorpusChunk],
) -> None:
    """Macbeth + AO1+AO2 → verifier annotates the verbatim Shakespeare span."""
    register_primary_text("Macbeth")
    fake_collection = _FakeCollection(macbeth_corpus)
    set_collection_provider(lambda: fake_collection)
    set_reranker_factory(_raise_import_error_factory)

    closure = _build_coach_handover()

    session_state = SimpleNamespace(
        text_name="Macbeth",
        focus_aos=("AO1", "AO2"),
    )
    raw_response = (
        "Macbeth's hesitation comes through clearest when he admits "
        f'"{_MACBETH_VERBATIM}".'
    )
    rewritten, metadata = closure(
        raw_response, "Macbeth's ambition", session_state
    )

    assert metadata.retrieval_skipped_reason is None
    assert metadata.verifier_exception is False
    assert len(metadata.primary_matches) >= 1, (
        f"expected at least one PrimaryMatch; got {metadata.primary_matches!r}"
    )

    # At least one match must point at Act 1 — that's the canonical
    # location of the verbatim line.
    act1_matches = [
        m
        for m in metadata.primary_matches
        if isinstance(m.citation_anchor, PlayCitationAnchor)
        and m.citation_anchor.act == 1
    ]
    assert act1_matches, (
        f"expected an Act 1 citation anchor; got "
        f"{[m.citation_anchor for m in metadata.primary_matches]}"
    )

    # The rewritten response must carry a play-anchor citation
    # annotation — same surface ``test_rag_end_to_end.py`` asserts.
    assert "(1.7." in rewritten, (
        f"expected play-anchor citation in rewritten response: {rewritten!r}"
    )

    # And the fake collection must actually have been queried.
    assert fake_collection.query_calls >= 1


# ---------------------------------------------------------------------------
# Test 4 — AO3 bypass (zero retrieve calls + skip-reason surfaced).
# ---------------------------------------------------------------------------


def test_ao3_bypass(macbeth_corpus: list[CorpusChunk]) -> None:
    """focus_aos={"AO3"} → zero query calls + ao3_only:training_first."""
    register_primary_text("Macbeth")
    fake_collection = _FakeCollection(macbeth_corpus)
    set_collection_provider(lambda: fake_collection)
    set_reranker_factory(_raise_import_error_factory)

    closure = _build_coach_handover()

    session_state = SimpleNamespace(
        text_name="Macbeth",
        focus_aos=("AO3",),
    )
    rewritten, metadata = closure(
        "AO3 context discussion: Jacobean attitudes to regicide.",
        "What was Jacobean society like?",
        session_state,
    )

    assert fake_collection.query_calls == 0, (
        "AO3-only branch must short-circuit before any retrieve call"
    )
    assert metadata.retrieval_skipped_reason == "ao3_only:training_first"
    assert metadata.verifier_exception is False
    assert metadata.primary_matches == []
    # Verbatim pass-through — no quoted spans in the response.
    assert rewritten == (
        "AO3 context discussion: Jacobean attitudes to regicide."
    )


# ---------------------------------------------------------------------------
# Test 5 — verifier-exception regression. The closure must surface the
# fallback metadata; no exception bubbles up. Since the law-3 strict mode
# (docs/design/quote-law3-no-unverified-quote-2026-10-18.md, R3) the
# production closure fails CLOSED: every quoted span is redacted rather
# than the raw response being passed through.
# ---------------------------------------------------------------------------


def test_verifier_exception_regression(
    monkeypatch: pytest.MonkeyPatch,
    macbeth_corpus: list[CorpusChunk],
) -> None:
    """``verify_quotes`` raises → quoted spans redacted, ``verifier_exception=True``."""
    register_primary_text("Macbeth")
    fake_collection = _FakeCollection(macbeth_corpus)
    set_collection_provider(lambda: fake_collection)
    set_reranker_factory(_raise_import_error_factory)

    def _boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("boom")

    # Patch the symbol the coach_handover module imported at module
    # load — patching the source module wouldn't take effect because
    # the seam already bound a local reference.
    monkeypatch.setattr(
        "study_tutor.knowledge.coach_handover.verify_quotes", _boom
    )

    closure = _build_coach_handover()

    session_state = SimpleNamespace(
        text_name="Macbeth",
        focus_aos=("AO1", "AO2"),
    )
    raw_response = (
        "Macbeth's hesitation comes through when he admits "
        f'"{_MACBETH_VERBATIM}".'
    )
    rewritten, metadata = closure(
        raw_response, "Macbeth's ambition", session_state
    )

    assert rewritten == (
        "Macbeth's hesitation comes through when he admits "
        f"{UNVERIFIED_QUOTE_TEXT}."
    ), "verifier-exception path must redact every quoted span (fail closed)"
    assert _MACBETH_VERBATIM not in rewritten
    assert metadata.verifier_exception is True


# ---------------------------------------------------------------------------
# ADR-ARCH-032 D2 — subject discovery at wiring time
# ---------------------------------------------------------------------------


class _ListingFakePersistentClient(_FakePersistentClient):
    """Fake client whose ``list_collections`` surfaces named collections."""

    def __init__(self, path: str) -> None:
        super().__init__(path)
        self.listed: list[Any] = []
        self.opened_names: list[str] = []

    def list_collections(self) -> list[Any]:
        return self.listed

    def get_or_create_collection(
        self, *, name: str, embedding_function: Any
    ) -> Any:
        self.opened_names.append(name)
        return super().get_or_create_collection(
            name=name, embedding_function=embedding_function
        )


class _NamedCollectionStub:
    def __init__(self, name: str) -> None:
        self.name = name


def test_subject_discovery_wires_every_matching_collection(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    macbeth_corpus: list[CorpusChunk],
) -> None:
    """A ``gcse-french-v1`` collection in the store wires a french provider,
    and its suffixed sidecar replays into french's registry (the legacy
    unsuffixed sidecar stays english's)."""
    persist_dir = tmp_path / "chroma"
    persist_dir.mkdir()
    # Legacy sidecar → english; suffixed sidecar → french.
    (persist_dir / ".primary_text_index").write_text("macbeth\n", encoding="utf-8")
    (persist_dir / ".primary_text_index.french").write_text(
        "candide\n", encoding="utf-8"
    )

    fake_collection = _FakeCollection(macbeth_corpus)
    fake_client = _ListingFakePersistentClient(path=str(persist_dir))
    fake_client.install_collection(fake_collection)
    fake_client.listed = [
        _NamedCollectionStub("gcse-english-v1"),
        _NamedCollectionStub("gcse-french-v1"),
        _NamedCollectionStub("unrelated-store"),  # must NOT wire a subject
    ]
    _install_fake_chromadb_module(monkeypatch, fake_client)

    monkeypatch.setenv(RAG_PERSIST_DIR_ENV, str(persist_dir))
    monkeypatch.delenv(RAG_COLLECTION_ENV, raising=False)

    role_config = load_role("tutor")
    build_rag_providers(role_config)

    assert get_collection_provider() is not None  # english (default)
    assert get_collection_provider("french") is not None
    assert get_collection_provider("unrelated") is None
    assert get_collection_provider("store") is None
    # Registry replay went to the right subjects' indexes.
    from study_tutor.knowledge.retrieval import has_primary_text

    assert has_primary_text("macbeth")
    assert not has_primary_text("candide")
    assert has_primary_text("candide", "french")
    assert not has_primary_text("macbeth", "french")
    # Both scheme collections were opened; the unrelated one was not.
    assert "gcse-english-v1" in fake_client.opened_names
    assert "gcse-french-v1" in fake_client.opened_names
    assert "unrelated-store" not in fake_client.opened_names


# ---------------------------------------------------------------------------
# Boot probe + query-failure detail (2026-10-18: a 768-dim corpus queried
# with a 1024-dim embedder failed every retrieval, silently).
# ---------------------------------------------------------------------------


class _MismatchedCollection(_FakeCollection):
    def query(self, **_kwargs: Any) -> Any:
        raise RuntimeError(
            "Collection expecting embedding with dimension of 768, got 1024"
        )


def _wire(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any, collection: Any
) -> None:
    persist_dir = tmp_path / "chroma"
    persist_dir.mkdir()
    fake_client = _FakePersistentClient(path=str(persist_dir))
    fake_client.install_collection(collection)
    _install_fake_chromadb_module(monkeypatch, fake_client)
    monkeypatch.setenv(RAG_PERSIST_DIR_ENV, str(persist_dir))
    monkeypatch.setenv(RAG_COLLECTION_ENV, "test-collection-v1")
    build_rag_providers(load_role("tutor"))


def test_boot_probe_failure_is_logged_loudly_and_subject_stays_wired(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    macbeth_corpus: list[CorpusChunk],
    caplog: pytest.LogCaptureFixture,
) -> None:
    collection = _MismatchedCollection(macbeth_corpus)
    with caplog.at_level(logging.ERROR, logger="study_tutor.cli.rag_wiring"):
        _wire(monkeypatch, tmp_path, collection)

    errors = [r.getMessage() for r in caplog.records if r.levelno == logging.ERROR]
    assert any(
        "event=rag_subject_probe_failed" in m and "dimension of 768, got 1024" in m
        for m in errors
    ), errors
    # Still wired: a transient embedder outage at boot must not disable
    # retrieval for the life of the process.
    assert get_collection_provider()() is collection


def test_boot_probe_success_logs_no_error(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    macbeth_corpus: list[CorpusChunk],
    caplog: pytest.LogCaptureFixture,
) -> None:
    collection = _FakeCollection(macbeth_corpus)
    with caplog.at_level(logging.ERROR, logger="study_tutor.cli.rag_wiring"):
        _wire(monkeypatch, tmp_path, collection)
    assert not [r for r in caplog.records if r.levelno == logging.ERROR]
    # Exactly one probe query was made at boot, through the live source filter.
    assert collection.query_calls == 1
    assert collection.last_query["n_results"] == 1
    assert collection.last_query["where"] == {
        "source_type": {"$in": [s.value for s in NON_AO3_SOURCE_TYPES]}
    }


def test_boot_probe_skips_an_empty_collection(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    collection = _FakeCollection([])
    _wire(monkeypatch, tmp_path, collection)
    assert collection.query_calls == 0


def test_query_failure_detail_is_in_the_log_message(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
    macbeth_corpus: list[CorpusChunk],
    caplog: pytest.LogCaptureFixture,
) -> None:
    from study_tutor.knowledge.retrieval import retrieve

    _wire(monkeypatch, tmp_path, _MismatchedCollection(macbeth_corpus))
    with caplog.at_level(logging.WARNING, logger="study_tutor.knowledge.retrieval"):
        assert retrieve("ambition", text_name=None, focus_aos=()) == []
    assert any(
        "retrieval.query_failed" in r.getMessage()
        and "dimension of 768, got 1024" in r.getMessage()
        for r in caplog.records
    ), [r.getMessage() for r in caplog.records]
