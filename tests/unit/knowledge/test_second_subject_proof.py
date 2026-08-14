"""Second-subject seam proof — a genuine second subject, end to end, hermetically.

Lane 3 step 4, D-stage of the upload-surface build spec
(``docs/design/upload-surface-build-spec-2026-08-14.md``). Independent of the upload
page itself: this module exercises the multi-subject plumbing that ALREADY exists, so
the weekend's first real scan lands on a seam that has been proved rather than
assumed.

What the proof drives
---------------------
The REAL ingest CLI — ``scripts/ingest_corpus.py``'s ``main`` — over a crafted fixture
corpus (``tests/fixtures/demo_history_corpus``, every word written for this test) copied
into a temp directory in the four-folder shape, under subject ``demo_history``. It then
reads the resulting store back and asserts the four things the second subject depends on:

1. the collection is named ``gcse-demo_history-v1`` and holds every chunk the loader
   produced, with the metadata contract ``retrieval._hydrate_chunk`` reads;
2. the AQA assessment-material refusal gate applies to the new subject exactly as it
   does to english;
3. the primary-text sidecar lands at the filename ``rag_wiring`` reads for that subject,
   and ``build_rag_providers`` discovers, wires and replays the subject from disk;
4. the live english store is untouched — ``gcse-english-v1`` still holds exactly 581
   chunks and no ``demo_history`` collection appeared beside it.

Why it is hermetic (no marker needed — the hermetic run is everything not marked
``integration``/``live``/``keycloak``)
-------------------------------------------------------------------------------------
* **No network.** ``ingest_corpus._make_embedding_function`` is replaced with
  :class:`StubEmbeddingFunction` — deterministic sha256-derived vectors — so nothing
  reaches llama-swap's ``/v1/embeddings``. The stub is also what ``rag_wiring`` gets.
* **No live store.** Every write goes to a ``tmp_path`` persist dir. The repo's
  ``data/chroma`` is opened READ-ONLY, through sqlite in ``mode=ro``, never through a
  chromadb client — that directory is baked into the next image build, so a stray write
  would ship a demo corpus to production.
* No broker, no Postgres, no docker.

Editing the fixture corpus changes the pinned counts below; re-run this module and
update the ``EXPECTED_*`` constants in the same commit.
"""

from __future__ import annotations

import hashlib
import io
import json
import shutil
import sqlite3
from contextlib import redirect_stdout
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

import pytest

# chromadb ships in the optional [rag] extra; skip cleanly on the dev path (the same
# posture as tests/unit/scripts/test_ingest_corpus.py) rather than failing collection.
chromadb = pytest.importorskip("chromadb")

from chromadb.api.types import (  # noqa: E402
    Documents,
    EmbeddingFunction,
    Embeddings,
)

from scripts import ingest_corpus  # noqa: E402
from study_tutor.cli import rag_wiring  # noqa: E402
from study_tutor.knowledge.corpus_models import CorpusChunk  # noqa: E402
from study_tutor.knowledge.retrieval import (  # noqa: E402
    clear_primary_text_index,
    get_collection_provider,
    has_corpus,
    has_primary_text,
    reset_collection_provider,
)

# ---------------------------------------------------------------------------
# The subject under proof, and everything pinned about it
# ---------------------------------------------------------------------------

SUBJECT: str = "demo_history"
EXPECTED_COLLECTION: str = "gcse-demo_history-v1"

#: tests/unit/knowledge/… → tests/fixtures/demo_history_corpus
FIXTURE_CORPUS: Path = (
    Path(__file__).resolve().parents[2] / "fixtures" / "demo_history_corpus"
)

#: Chunk counts the crafted corpus produces under the loader's 512/100 chunker.
EXPECTED_CHUNKS_BY_SOURCE_TYPE: dict[str, int] = {
    "PRIMARY_TEXT": 7,
    "SECONDARY_STUDY_GUIDE": 4,
    "SECONDARY_CRITICAL": 3,
    "CONTEXT_HISTORICAL": 3,
}
EXPECTED_TOTAL_CHUNKS: int = sum(EXPECTED_CHUNKS_BY_SOURCE_TYPE.values())

#: One primary text; the ``.md`` study guide and the two prose files are secondaries.
EXPECTED_PRIMARY_TEXT_NAMES: list[str] = ["ashwood_charter"]

#: The file whose NAME (not content) must trip the AQA refusal regex.
AQA_REFUSED_FILENAME: str = "ashwood_mark_scheme.txt"

#: 6 of the 7 primary chunks carry a novel anchor; the front-matter chunk precedes
#: "Chapter 1" and legitimately has none (the loader logs it and carries on).
EXPECTED_ANCHORED_PRIMARY_CHUNKS: int = 6

#: The live english store, pinned read-only (Lane 2 1a: this store is baked into the
#: serving image). A change here means something wrote to production corpus data.
ENGLISH_COLLECTION: str = "gcse-english-v1"
ENGLISH_CHUNK_COUNT: int = 581


# ---------------------------------------------------------------------------
# Stub embedding function — the reason this proof needs no llama-swap
# ---------------------------------------------------------------------------


class StubEmbeddingFunction(EmbeddingFunction[Documents]):
    """Deterministic in-process embeddings: the first N bytes of sha256(document).

    Real ingest calls llama-swap's OpenAI-compatible ``/v1/embeddings``. The proof is
    about the *plumbing* — collection naming, metadata, sidecar, discovery — none of
    which depends on the vectors meaning anything, so we substitute vectors that are
    free, offline, and identical on every run.
    """

    def __init__(self, dimensions: int = 8) -> None:
        self._dimensions = dimensions

    def __call__(self, input: Documents) -> Embeddings:
        return [
            [
                byte / 255.0
                for byte in hashlib.sha256(document.encode("utf-8")).digest()[
                    : self._dimensions
                ]
            ]
            for document in input
        ]

    @staticmethod
    def name() -> str:
        return "study_tutor_stub"

    def get_config(self) -> dict[str, Any]:
        return {"dimensions": self._dimensions}

    @classmethod
    def build_from_config(cls, config: dict[str, Any]) -> "StubEmbeddingFunction":
        return cls(**config)


# ---------------------------------------------------------------------------
# The ingest run (module-scoped: one real CLI invocation, many assertions)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IngestRun:
    """What one ``ingest_corpus.main`` invocation left behind."""

    exit_code: int
    persist_dir: Path
    corpus_root: Path
    events: list[dict[str, Any]]

    def events_of(self, event: str) -> list[dict[str, Any]]:
        return [record for record in self.events if record["event"] == event]

    def summary(self) -> dict[str, Any]:
        (record,) = self.events_of("ingest_summary")
        return record


@pytest.fixture(scope="module")
def ingest_run(tmp_path_factory: pytest.TempPathFactory) -> Iterator[IngestRun]:
    """Run the REAL ingest CLI over a temp copy of the fixture corpus."""
    workspace = tmp_path_factory.mktemp("second_subject_proof")
    corpus_root = workspace / "sources"
    shutil.copytree(FIXTURE_CORPUS, corpus_root)
    (corpus_root / "README.md").unlink(missing_ok=True)  # not corpus material
    persist_dir = workspace / "chroma"

    with pytest.MonkeyPatch.context() as patch:
        # The one seam we substitute: no /v1/embeddings call leaves this process.
        patch.setattr(
            ingest_corpus, "_make_embedding_function", lambda: StubEmbeddingFunction()
        )
        # CHROMA_* would override the --subject derivation this proof is about.
        patch.delenv("CHROMA_COLLECTION", raising=False)
        patch.delenv("CHROMA_PERSIST_DIR", raising=False)
        clear_primary_text_index()

        stdout = io.StringIO()
        with redirect_stdout(stdout):
            exit_code = ingest_corpus.main(
                [
                    "--subject",
                    SUBJECT,
                    "--domain-root",
                    str(corpus_root),
                    "--persist-dir",
                    str(persist_dir),
                ]
            )

    events = [json.loads(line) for line in stdout.getvalue().splitlines() if line]
    try:
        yield IngestRun(
            exit_code=exit_code,
            persist_dir=persist_dir,
            corpus_root=corpus_root,
            events=events,
        )
    finally:
        # ``_register_primary_texts`` writes process-global registry state.
        clear_primary_text_index()
        reset_collection_provider()


def _open_ingested_collection(run: IngestRun) -> Any:
    client = chromadb.PersistentClient(path=str(run.persist_dir))
    return client.get_collection(
        name=EXPECTED_COLLECTION, embedding_function=StubEmbeddingFunction()
    )


# ---------------------------------------------------------------------------
# 1. The CLI accepts the second subject and reports what it did
# ---------------------------------------------------------------------------


def test_real_ingest_cli_completes_for_a_second_subject(ingest_run: IngestRun) -> None:
    """Exit 0, and the NDJSON summary matches the crafted corpus exactly."""
    assert ingest_run.exit_code == 0

    summary = ingest_run.summary()
    assert summary["chunks_created"] == EXPECTED_TOTAL_CHUNKS
    assert summary["primary_text_names"] == EXPECTED_PRIMARY_TEXT_NAMES
    assert summary["skips"] == 0
    # The AQA-named file is the only thing refused.
    assert summary["refusals"] == 1


def test_per_text_counts_cover_all_four_source_type_folders(
    ingest_run: IngestRun,
) -> None:
    """All four folders of the corpus contract carried chunks into the ingest."""
    counts = {
        record["source_type"]: record["chunk_count"]
        for record in ingest_run.events_of("per_text_count")
    }
    assert counts == EXPECTED_CHUNKS_BY_SOURCE_TYPE


def test_citation_anchors_are_inferred_for_the_new_subject(
    ingest_run: IngestRun,
) -> None:
    """The anchor inferer runs for demo_history's primary text, not just english's."""
    (record,) = ingest_run.events_of("citation_anchor_summary")
    assert record["text_name"] == "ashwood_charter"
    assert record["anchored"] == EXPECTED_ANCHORED_PRIMARY_CHUNKS
    assert record["anchored"] + record["unanchored"] == (
        EXPECTED_CHUNKS_BY_SOURCE_TYPE["PRIMARY_TEXT"]
    )


# ---------------------------------------------------------------------------
# 2. The collection: name, size, metadata contract
# ---------------------------------------------------------------------------


def test_collection_is_named_for_the_subject_and_holds_every_chunk(
    ingest_run: IngestRun,
) -> None:
    client = chromadb.PersistentClient(path=str(ingest_run.persist_dir))
    names = {getattr(existing, "name", existing) for existing in client.list_collections()}
    # The subject's collection is the ONLY one the ingest created — a second subject
    # must not spill into english's.
    assert names == {EXPECTED_COLLECTION}
    assert _open_ingested_collection(ingest_run).count() == EXPECTED_TOTAL_CHUNKS


def test_chunk_metadata_matches_the_retrieval_hydration_contract(
    ingest_run: IngestRun,
) -> None:
    """Every row carries the flat filter fields plus a round-trippable chunk_json."""
    stored = _open_ingested_collection(ingest_run).get(
        include=["metadatas", "documents"]
    )
    metadatas = stored["metadatas"]
    assert len(metadatas) == EXPECTED_TOTAL_CHUNKS

    source_type_counts: dict[str, int] = {}
    for chunk_id, metadata, document in zip(
        stored["ids"], metadatas, stored["documents"]
    ):
        assert set(metadata) == {
            "text_name",
            "source_type",
            "source_path",
            "chunk_index",
            "chunk_json",
        }
        # ``_hydrate_chunk`` reads this key and nothing else structural.
        hydrated = CorpusChunk.model_validate_json(metadata["chunk_json"])
        assert hydrated.text == document
        assert hydrated.text_name == metadata["text_name"]
        assert hydrated.source_type.value == metadata["source_type"]
        assert hydrated.chunk_index == metadata["chunk_index"]
        # Deterministic ID shape (``_chunk_id``) — what makes re-ingest idempotent.
        assert chunk_id == (
            f"{metadata['source_type']}:{metadata['text_name']}:"
            f"{metadata['chunk_index']}"
        )
        # The staged corpus root is recorded, so an operator can trace a chunk back.
        assert metadata["source_path"].startswith(str(ingest_run.corpus_root))
        source_type_counts[metadata["source_type"]] = (
            source_type_counts.get(metadata["source_type"], 0) + 1
        )

    assert source_type_counts == EXPECTED_CHUNKS_BY_SOURCE_TYPE


def test_aqa_refusal_gate_applies_to_the_second_subject(
    ingest_run: IngestRun,
) -> None:
    """The refusal is subject-agnostic: refused at the loader, absent from the store."""
    (refusal,) = ingest_run.events_of("refusal")
    assert refusal["reason"] == "AQA_ASSESSMENT_MATERIAL"
    assert refusal["path"].endswith(AQA_REFUSED_FILENAME)

    stored = _open_ingested_collection(ingest_run).get(include=["metadatas"])
    assert all(
        AQA_REFUSED_FILENAME not in metadata["source_path"]
        for metadata in stored["metadatas"]
    )


# ---------------------------------------------------------------------------
# 3. Discovery: the sidecar lands where rag_wiring reads it, and wiring finds it
# ---------------------------------------------------------------------------


def test_sidecar_lands_at_the_filename_rag_wiring_reads(
    ingest_run: IngestRun,
) -> None:
    """Writer (ingest) and reader (rag_wiring) agree on the per-subject sidecar."""
    sidecar = ingest_run.persist_dir / rag_wiring.subject_sidecar_filename(SUBJECT)
    assert sidecar.name == ".primary_text_index.demo_history"
    assert sidecar.exists()
    assert sidecar.read_text(encoding="utf-8") == "ashwood_charter\n"
    # The summary names the same path the reader will open.
    assert ingest_run.summary()["primary_text_index_sidecar"] == str(sidecar)
    # English's legacy unsuffixed sidecar must NOT be created by another subject.
    assert not (ingest_run.persist_dir / ".primary_text_index").exists()


def test_collection_name_parses_under_the_subject_discovery_pattern() -> None:
    """The slug survives the registry pattern that drives subject discovery."""
    assert rag_wiring.subject_collection_name(SUBJECT) == EXPECTED_COLLECTION
    match = rag_wiring.SUBJECT_COLLECTION_PATTERN.match(EXPECTED_COLLECTION)
    assert match is not None
    assert match.group("subject") == SUBJECT


def test_rag_wiring_discovers_wires_and_replays_the_second_subject(
    ingest_run: IngestRun, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``build_rag_providers`` finds demo_history on disk with no config change."""
    monkeypatch.setenv(rag_wiring.RAG_PERSIST_DIR_ENV, str(ingest_run.persist_dir))
    monkeypatch.delenv(rag_wiring.RAG_COLLECTION_ENV, raising=False)
    monkeypatch.setattr(
        rag_wiring, "build_openai_embedding_function", lambda: StubEmbeddingFunction()
    )
    clear_primary_text_index()
    reset_collection_provider()
    try:
        rag_wiring.build_rag_providers(role_config=None)

        assert has_corpus(SUBJECT)
        provider = get_collection_provider(SUBJECT)
        assert provider is not None
        assert provider().count() == EXPECTED_TOTAL_CHUNKS

        # The sidecar was replayed into the subject's own registry, and only its own.
        assert has_primary_text("ashwood_charter", SUBJECT)
        assert not has_primary_text("ashwood_charter")

        # English is still wired (the default subject always is) but empty here —
        # proof the second subject's chunks landed in the second subject's collection.
        english_provider = get_collection_provider()
        assert english_provider is not None
        assert english_provider().count() == 0
    finally:
        clear_primary_text_index()
        reset_collection_provider()


# ---------------------------------------------------------------------------
# 4. The live english store is untouched (read-only check)
# ---------------------------------------------------------------------------


def _live_chroma_sqlite() -> Path | None:
    """Locate the repo's real ``data/chroma/chroma.sqlite3``, or ``None``.

    ``data/`` is operator data, not tracked in git, so a clean clone legitimately has
    no store and the check skips. In a git worktree the store lives in the main
    checkout, which we reach through the ``gitdir:`` pointer in the worktree's ``.git``
    file (``<main>/.git/worktrees/<name>``).
    """
    repo_root = Path(__file__).resolve().parents[3]
    candidates = [repo_root / "data" / "chroma" / "chroma.sqlite3"]

    git_pointer = repo_root / ".git"
    if git_pointer.is_file():
        for line in git_pointer.read_text(encoding="utf-8").splitlines():
            if line.startswith("gitdir:"):
                gitdir = Path(line.split(":", 1)[1].strip())
                # <main checkout>/.git/worktrees/<name> → <main checkout>
                if len(gitdir.parts) > 3:
                    candidates.append(
                        gitdir.parents[2] / "data" / "chroma" / "chroma.sqlite3"
                    )

    return next((path for path in candidates if path.is_file()), None)


def _collection_chunk_counts(sqlite_path: Path) -> dict[str, int]:
    """Read collection → row count straight out of chroma's sqlite, READ-ONLY.

    Deliberately not a ``chromadb.PersistentClient``: opening the live store through
    chroma can migrate or write to it, and this store is baked into the serving image.
    ``mode=ro`` makes a write physically impossible.
    """
    connection = sqlite3.connect(f"file:{sqlite_path}?mode=ro", uri=True)
    try:
        return {
            name: connection.execute(
                "SELECT count(*) FROM embeddings e JOIN segments s "
                "ON e.segment_id = s.id WHERE s.collection = ?",
                (collection_id,),
            ).fetchone()[0]
            for collection_id, name in connection.execute(
                "SELECT id, name FROM collections"
            ).fetchall()
        }
    finally:
        connection.close()


def test_live_english_store_still_holds_its_pinned_chunk_count(
    ingest_run: IngestRun,
) -> None:
    """581 chunks in gcse-english-v1, and no demo_history collection beside it."""
    sqlite_path = _live_chroma_sqlite()
    if sqlite_path is None:
        pytest.skip(
            "no data/chroma store in this checkout (untracked operator data) — "
            "nothing to protect here"
        )

    counts = _collection_chunk_counts(sqlite_path)
    assert counts.get(ENGLISH_COLLECTION) == ENGLISH_CHUNK_COUNT
    # The proof's writes went to tmp_path; the live store must not have grown a subject.
    assert EXPECTED_COLLECTION not in counts
