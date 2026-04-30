"""Integration smoke for the primary-text-RAG → verifier → Coach handover.

Producer / consumer wiring under test (FEAT-PRV4 / FEAT-PH1-004):

* TASK-PRV-002 — :class:`CorpusChunk` is the data contract.
* TASK-PRV-003 — ``should_retrieve`` returns the four-branch
  :class:`RetrievalDecision`; this test exercises three of the four
  branches end-to-end (retrieve, AnalysisMode-no-primary,
  AO3-only-bypass — the mixed branch is covered by the dedicated unit
  test in ``test_retrieval.py``).
* TASK-PRV-004 — ``retrieve`` is wired against an in-memory fake
  ChromaDB collection seeded with the fixture corpus, so the
  precedence-ordering + AQA defence-in-depth is exercised on the same
  code path production runs.
* TASK-PRV-005 — :func:`verify_quotes` is the source-typed quote
  verifier; this test asserts the resulting :class:`VerifierMetadata`
  shape against a Player response that carries one verbatim primary
  quote and one secondary study-guide phrase.
* TASK-PRV-006 — :func:`apply_quote_verification` is the seam to the
  Coach. The AnalysisMode path calls into it with an empty corpus and
  ``retrieval_skipped_reason`` so we can assert the metadata flag
  Coach reads to suppress the ``quote_fidelity`` down-rank.

Why three paths and not four
----------------------------
The task spec explicitly scopes this integration test to the three
**production-relevant** flows: retrieve-and-verify, AnalysisMode skip
(no primary text indexed), and AO3-only bypass. The mixed-AO3 fourth
branch already has a focused unit test against the same module-level
constants; integration adds no new wiring there.

Why the fixture corpus is tiny (~3 chunks per text)
---------------------------------------------------
The AC requires this test to run in <30s in CI, with no external
downloads. Three primary chunks + one secondary chunk + zero
Inspector-Calls primaries is enough to exercise the source-filtered
retrieval, primary-first ordering, AnalysisMode skip, and AO3 bypass
without paying the ~568 MB BGE reranker cost: the reranker factory is
injected with an ``ImportError``-raising stub so the
graceful-degradation path is what production CI also takes.

Hermeticity
-----------
No network. No filesystem writes outside ``tmp_path``. No real ChromaDB
or sentence-transformers — the fake collection and reranker factory are
both injected. Module-level state in
``study_tutor.knowledge.retrieval`` (the primary-text index, collection
provider, reranker factory, embedder probe) is reset around every test
via the autouse fixture so cases stay independent.
"""

from __future__ import annotations

import time
from typing import Any, Iterator

import pytest

from study_tutor.knowledge.coach_handover import apply_quote_verification
from study_tutor.knowledge.corpus_models import (
    CorpusChunk,
    PlayCitationAnchor,
    SourceType,
)
from study_tutor.knowledge.quote_verifier import (
    PrimaryMatch,
    SecondaryRewrite,
    VerifierMetadata,
)
from study_tutor.knowledge.retrieval import (
    REASON_AO3_ONLY,
    REASON_NO_PRIMARY,
    clear_primary_text_index,
    register_primary_text,
    reset_collection_provider,
    reset_embedder_probe,
    reset_reranker_factory,
    retrieve,
    set_collection_provider,
    set_reranker_factory,
    should_retrieve,
)


# ---------------------------------------------------------------------------
# Fixture corpus — three Macbeth primary chunks + one study-guide chunk.
# An Inspector Calls is intentionally absent from the primary-text index so
# the AnalysisMode-skip path has something to assert against.
# ---------------------------------------------------------------------------

# A canonical Shakespeare line from Macbeth 1.7. The Player response below
# quotes it verbatim — the verifier should annotate it with the chunk's
# citation anchor (and the long-passage shortener should NOT trigger
# because the span is well under 30 words).
_MACBETH_VERBATIM = "I have no spur to prick the sides of my intent"


def _make_macbeth_primary_chunk(
    chunk_index: int,
    text: str,
    *,
    act: int,
    scene: int,
    line: int,
) -> CorpusChunk:
    """Build a primary-text Macbeth ``CorpusChunk`` with a play anchor."""
    return CorpusChunk(
        text=text,
        source_type=SourceType.PRIMARY_TEXT,
        source_path="/fixture/primary_text/macbeth.txt",
        text_name="Macbeth",
        citation_anchor=PlayCitationAnchor(act=act, scene=scene, line=line),
        chunk_index=chunk_index,
    )


def _make_macbeth_secondary_chunk(chunk_index: int, text: str) -> CorpusChunk:
    """Build a secondary study-guide ``CorpusChunk`` for Macbeth (no anchor)."""
    return CorpusChunk(
        text=text,
        source_type=SourceType.SECONDARY_STUDY_GUIDE,
        source_path="/fixture/secondary_study_guide/macbeth.txt",
        text_name="Macbeth",
        chunk_index=chunk_index,
    )


@pytest.fixture
def macbeth_corpus() -> list[CorpusChunk]:
    """Three primary Macbeth chunks + one secondary study-guide chunk.

    The primary chunks span Act 1 Scenes 5–7 so the precedence ordering
    test has something realistic to walk; the secondary chunk carries a
    study-guide phrase the Player response will quote so the verifier
    routes it through the :class:`SecondaryRewrite` branch.
    """
    return [
        _make_macbeth_primary_chunk(
            0,
            "Come, you spirits that tend on mortal thoughts, "
            "unsex me here, and fill me from the crown to the toe top-full "
            "of direst cruelty.",
            act=1,
            scene=5,
            line=40,
        ),
        _make_macbeth_primary_chunk(
            1,
            "If it were done when 'tis done, then 'twere well it were done quickly. "
            f"{_MACBETH_VERBATIM}, but only vaulting ambition, which o'erleaps itself.",
            act=1,
            scene=7,
            line=1,
        ),
        _make_macbeth_primary_chunk(
            2,
            "Is this a dagger which I see before me, the handle toward my hand? "
            "Come, let me clutch thee.",
            act=2,
            scene=1,
            line=33,
        ),
        _make_macbeth_secondary_chunk(
            3,
            "Lady Macbeth's invocation establishes a study-guide motif of "
            "feminine ambition transgressing Jacobean gender expectations.",
        ),
    ]


# ---------------------------------------------------------------------------
# Fake ChromaDB collection — minimal duck-type matching the API the
# retrieval module's ``_query_collection`` calls into. Holds the fixture
# corpus in-memory; ``query`` filters by the where-clause that retrieval
# constructs (text_name + source_type ∈ NON_AO3_SOURCE_TYPES).
# ---------------------------------------------------------------------------


class _FakeCollection:
    """In-memory stand-in for a ``chromadb`` collection.

    Implements just enough of the real ``query`` surface to satisfy
    ``study_tutor.knowledge.retrieval._query_collection``: the
    ``$and`` / ``$in`` where-clause shape, JSON-serialised chunk payload
    in metadata, and a stable distance ordering by chunk index.
    """

    def __init__(self, chunks: list[CorpusChunk]) -> None:
        self._chunks = chunks

    def query(
        self,
        *,
        query_texts: list[str],
        n_results: int,
        where: dict[str, Any],
    ) -> dict[str, Any]:
        # Decode the constructed where-clause. ``retrieval._query_collection``
        # always emits ``{"$and": [{"text_name": ...},
        # {"source_type": {"$in": [...]}}]}``.
        text_name_filter: str | None = None
        allowed_source_types: set[str] = set()
        for clause in where.get("$and", []):
            if "text_name" in clause:
                text_name_filter = clause["text_name"]
            if "source_type" in clause:
                allowed_source_types = set(clause["source_type"]["$in"])

        matched: list[CorpusChunk] = [
            chunk
            for chunk in self._chunks
            if (text_name_filter is None or chunk.text_name == text_name_filter)
            and chunk.source_type.value in allowed_source_types
        ]
        # Stable order: chunk_index ascending so the no-rerank fallback
        # produces deterministic results without depending on insertion order.
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
    """Reranker factory that raises ``ImportError``.

    Mirrors what production CI sees when ``sentence_transformers`` is not
    installed: ``retrieve`` falls back to base-similarity ordering with
    ``mode="no_rerank"``. Restricting to ``ImportError`` keeps the
    graceful-degradation contract narrow — a broader exception would be
    a real bug we want surfaced, not silenced.
    """
    raise ImportError("sentence_transformers not installed (test stub)")


# ---------------------------------------------------------------------------
# Module-state isolation. The retrieval module owns several pieces of
# module-level state (primary-text index, collection provider, reranker
# factory, embedder probe). Reset around every test so cases stay
# independent regardless of execution order.
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
# Wall-clock budget guard for the AC ("runs in <30s against the fixture
# corpus"). Held at module scope so all three cases share a single budget
# allowance — the AC bounds the whole file, not each test individually.
# ---------------------------------------------------------------------------


_MAX_TOTAL_SECONDS = 30.0


# ---------------------------------------------------------------------------
# Test 1: retrieve-and-verify path.
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@pytest.mark.integration_contract("PrimaryTextRagPipeline")
def test_retrieve_and_verify_macbeth_primary_and_secondary(
    macbeth_corpus: list[CorpusChunk],
) -> None:
    """Macbeth, AO1+AO2 → primary-first retrieval + verifier annotation.

    Wiring exercised:
      1. ``register_primary_text("Macbeth")`` populates the corpus index
         so ``should_retrieve`` returns the retrieve branch.
      2. ``retrieve`` is invoked against a fake ChromaDB collection
         seeded with all four chunks; we assert primary-first ordering
         (every primary chunk appears before any secondary chunk).
      3. The Player response is verified via the seam in
         :func:`apply_quote_verification`. The verbatim Shakespeare span
         routes through :class:`PrimaryMatch` (with the chunk's
         :class:`PlayCitationAnchor`); the study-guide phrase routes
         through :class:`SecondaryRewrite` (quotes stripped, attribution
         injected).
    """
    start = time.monotonic()

    register_primary_text("Macbeth")
    fake_collection = _FakeCollection(macbeth_corpus)
    set_collection_provider(lambda: fake_collection)
    # Force the no-rerank graceful-degradation path so the test runs
    # without the real reranker model on disk.
    set_reranker_factory(_raise_import_error_factory)

    decision = should_retrieve("Macbeth", {"AO1", "AO2"})
    assert decision.retrieve is True
    assert decision.mode == "retrieve"

    retrieved = retrieve(
        query="Macbeth's ambition in his Act 1 soliloquy",
        text_name="Macbeth",
        focus_aos={"AO1", "AO2"},
        top_k=4,
    )

    # Primary-first invariant: every primary chunk strictly precedes any
    # secondary chunk in the result list.
    primary_indices = [
        idx
        for idx, chunk in enumerate(retrieved)
        if chunk.source_type is SourceType.PRIMARY_TEXT
    ]
    secondary_indices = [
        idx
        for idx, chunk in enumerate(retrieved)
        if chunk.source_type is not SourceType.PRIMARY_TEXT
    ]
    assert primary_indices, (
        "expected at least one PRIMARY_TEXT chunk; retrieval returned "
        f"{[c.source_type for c in retrieved]}"
    )
    if secondary_indices:
        assert max(primary_indices) < min(secondary_indices), (
            "primary-first ordering violated: primary chunks must precede "
            f"any secondary chunks, got source_types "
            f"{[c.source_type.value for c in retrieved]}"
        )

    # Player response with one verbatim Shakespeare span and one verbatim
    # study-guide phrase. Both spans are above MIN_QUOTE_WORDS (4) so
    # both reach the verifier rather than being silently dropped.
    secondary_phrase = (
        "feminine ambition transgressing Jacobean gender expectations"
    )
    player_response = (
        "Macbeth's hesitation comes through clearest when he admits "
        f'"{_MACBETH_VERBATIM}". This connects to the broader idea of '
        f'"{secondary_phrase}".'
    )

    rewritten, metadata = apply_quote_verification(
        player_response,
        retrieved,
        session_text_name="Macbeth",
        retrieval_skipped_reason=None,
    )

    # AC: VerifierMetadata shape — exactly one PrimaryMatch and exactly
    # one SecondaryRewrite. No fuzzy / no-match / cross-text events
    # should fire on this fixture.
    assert len(metadata.primary_matches) == 1, (
        f"expected one PrimaryMatch, got {len(metadata.primary_matches)}: "
        f"{metadata.primary_matches!r}"
    )
    assert len(metadata.secondary_rewrites) == 1, (
        f"expected one SecondaryRewrite, got "
        f"{len(metadata.secondary_rewrites)}: {metadata.secondary_rewrites!r}"
    )
    assert metadata.fuzzy_corrections == []
    assert metadata.cross_text_events == []
    assert metadata.no_match_strips == []
    assert metadata.verifier_exception is False
    assert metadata.retrieval_skipped_reason is None

    primary_match = metadata.primary_matches[0]
    assert isinstance(primary_match, PrimaryMatch)
    assert primary_match.text_name == "Macbeth"
    assert isinstance(primary_match.citation_anchor, PlayCitationAnchor)
    assert primary_match.citation_anchor.act == 1
    assert primary_match.citation_anchor.scene == 7

    secondary_rewrite = metadata.secondary_rewrites[0]
    assert isinstance(secondary_rewrite, SecondaryRewrite)
    assert secondary_rewrite.source_type is SourceType.SECONDARY_STUDY_GUIDE
    # The rewritten response must carry the rendered citation for the
    # primary span and must NOT carry the original quoted secondary span
    # (quotes get stripped, attribution prefixed).
    assert "(1.7." in rewritten, (
        f"expected a play-anchor citation in rewritten response: {rewritten!r}"
    )
    assert f'"{secondary_phrase}"' not in rewritten, (
        "secondary span should have its quote marks stripped by the "
        f"verifier; rewritten response: {rewritten!r}"
    )

    elapsed = time.monotonic() - start
    assert elapsed < _MAX_TOTAL_SECONDS, (
        f"retrieve-and-verify path took {elapsed:.2f}s, "
        f"AC budget is {_MAX_TOTAL_SECONDS}s"
    )


# ---------------------------------------------------------------------------
# Test 2: AnalysisMode skip path.
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@pytest.mark.integration_contract("PrimaryTextRagPipeline")
def test_analysis_mode_skip_when_no_primary_text() -> None:
    """Inspector Calls (no primary indexed) → analysis_mode skip + verifier still runs.

    The orchestrator skips retrieval entirely (empty corpus list) but
    still calls into the coach-handover seam so the Coach receives a
    :class:`VerifierMetadata` carrying ``retrieval_skipped_reason``.
    The Coach uses that flag to suppress its ``quote_fidelity``
    down-rank — fabricated quotes are not the Player's fault when the
    corpus had no primary text to ground against.
    """
    start = time.monotonic()

    # Macbeth is registered to prove the decision actually keys off
    # *the queried text* (Inspector Calls), not the global presence of
    # any primary text in the index.
    register_primary_text("Macbeth")

    decision = should_retrieve("An Inspector Calls", {"AO1", "AO2"})
    assert decision.retrieve is False
    assert decision.reason is REASON_NO_PRIMARY  # identity, not equality
    assert decision.reason == "analysis_mode:no_primary_text"
    assert decision.mode == "analysis_mode"

    # AnalysisMode means the orchestrator does not call ``retrieve``;
    # the verifier still runs so the Coach gets a metadata payload.
    player_response = (
        "Birling claims that "
        '"a man has to make his own way in the world", '
        "which the play undercuts immediately."
    )
    rewritten, metadata = apply_quote_verification(
        player_response,
        corpus_chunks=[],
        session_text_name="An Inspector Calls",
        retrieval_skipped_reason=decision.reason,
    )

    assert isinstance(metadata, VerifierMetadata)
    # AC: empty retrieve list (we never called retrieve) AND the
    # retrieval_skipped_reason is forwarded into metadata so the Coach
    # can apply analysis-mode scoring posture.
    assert metadata.retrieval_skipped_reason == "analysis_mode:no_primary_text"
    assert metadata.verifier_exception is False
    # With no primary corpus, the verbatim quote falls through to
    # NoMatchStrip — that's the verifier's expected behaviour, and the
    # Coach reads ``retrieval_skipped_reason`` to suppress the down-rank.
    assert metadata.primary_matches == []
    assert metadata.fuzzy_corrections == []
    assert metadata.cross_text_events == []
    assert len(metadata.no_match_strips) == 1
    # Quotes should be stripped from the rewritten response so the
    # student doesn't see an unannotated verbatim citation.
    assert (
        '"a man has to make his own way in the world"' not in rewritten
    ), (
        "no-match span should have its quote marks stripped; "
        f"rewritten response: {rewritten!r}"
    )

    elapsed = time.monotonic() - start
    assert elapsed < _MAX_TOTAL_SECONDS, (
        f"analysis-mode path took {elapsed:.2f}s, "
        f"AC budget is {_MAX_TOTAL_SECONDS}s"
    )


# ---------------------------------------------------------------------------
# Test 3: AO3 bypass path.
# ---------------------------------------------------------------------------


@pytest.mark.smoke
@pytest.mark.integration_contract("PrimaryTextRagPipeline")
def test_ao3_only_bypasses_retrieval(
    macbeth_corpus: list[CorpusChunk],
) -> None:
    """Macbeth + ``focus_aos = {"AO3"}`` → ``ao3_only:training_first`` bypass.

    AO3-only turns are training-first: retrieval would distract from
    rubric-only practice. The decision short-circuits before the
    primary-text index is even consulted, so this branch fires even
    though Macbeth IS registered and the corpus IS wired.
    """
    start = time.monotonic()

    register_primary_text("Macbeth")
    fake_collection = _FakeCollection(macbeth_corpus)
    set_collection_provider(lambda: fake_collection)
    set_reranker_factory(_raise_import_error_factory)

    decision = should_retrieve("Macbeth", {"AO3"})
    assert decision.retrieve is False
    assert decision.reason is REASON_AO3_ONLY  # identity
    assert decision.reason == "ao3_only:training_first"
    assert decision.mode == "ao3_bypass"

    # The orchestrator must not call ``retrieve`` on this branch — but
    # if a future regression accidentally invokes it, the verifier still
    # has to behave. We assert the empty-corpus pass-through here so the
    # coach-handover contract holds either way.
    rewritten, metadata = apply_quote_verification(
        "AO3 context discussion: Jacobean attitudes to regicide.",
        corpus_chunks=[],
        session_text_name="Macbeth",
        retrieval_skipped_reason=decision.reason,
    )
    assert metadata.retrieval_skipped_reason == "ao3_only:training_first"
    assert metadata.primary_matches == []
    assert metadata.secondary_rewrites == []
    # No quoted spans at all in this response — verifier passes the
    # response through verbatim.
    assert rewritten == (
        "AO3 context discussion: Jacobean attitudes to regicide."
    )

    elapsed = time.monotonic() - start
    assert elapsed < _MAX_TOTAL_SECONDS, (
        f"AO3-bypass path took {elapsed:.2f}s, "
        f"AC budget is {_MAX_TOTAL_SECONDS}s"
    )
