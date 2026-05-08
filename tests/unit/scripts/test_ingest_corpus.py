"""Unit tests for the chromadb ingestion script (TASK-RAG-001).

Each acceptance criterion in
``tasks/in_progress/TASK-RAG-001-chromadb-ingestion-script.md`` is covered
by at least one test below. Tests skip cleanly via ``pytest.importorskip``
if ``chromadb`` is not installed (the dev-path posture: dev path stays
lightweight, the ``rag`` extra is opt-in).

Hermeticity
-----------
* No network. Every test builds its own four-folder fixture corpus inside
  ``tmp_path`` and points the script at a fresh ``persist-dir`` under
  ``tmp_path`` so chromadb's PersistentClient writes are confined.
* The retrieval module's primary-text registry is module-level state;
  the autouse fixture clears it around every case.
"""

from __future__ import annotations

import io
import json
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

import pytest

# Skip the entire module on dev path without the ``rag`` extra installed.
# importorskip raises Skipped at collection time so tests aren't even
# discovered if chromadb is unavailable.
chromadb = pytest.importorskip("chromadb")
from chromadb.utils.embedding_functions import (  # noqa: E402
    DefaultEmbeddingFunction,
)

# Import the script under test AFTER importorskip so the module imports
# don't blow up on the dev path. ``ingest_corpus`` itself imports chromadb
# lazily inside ``main``, so this import is cheap.
from scripts import ingest_corpus  # noqa: E402
from study_tutor.knowledge.corpus_models import CorpusChunk  # noqa: E402
from study_tutor.knowledge.retrieval import (  # noqa: E402
    clear_primary_text_index,
    has_primary_text,
)

# Capture the production ``_make_embedding_function`` *before* the autouse
# stub fixture below replaces it on the module. The env-var wiring test
# (``test_make_embedding_function_uses_decision_defaults``) needs to invoke
# the real function to assert it constructs an ``OpenAIEmbeddingFunction``
# from the decision-§3.1 env vars; reaching for ``ingest_corpus`` after the
# fixture runs would dispatch to the stub instead.
_REAL_MAKE_EMBEDDING_FUNCTION = ingest_corpus._make_embedding_function


# ---------------------------------------------------------------------------
# Module-state isolation
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_primary_text_index() -> Any:
    """Reset the retrieval module's primary-text registry around every test."""
    clear_primary_text_index()
    yield
    clear_primary_text_index()


@pytest.fixture(autouse=True)
def _stub_embedding_function(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Replace ``_make_embedding_function`` with the in-process default EF.

    DECISION-RAG-001 wires ingest through llama-swap at ``localhost:9000``,
    which is unreachable on CI. Stubbing at module level (rather than at
    each call site) makes every existing end-to-end test hermetic without
    threading a parameter through ``main`` → ``_open_collection``.

    ``DefaultEmbeddingFunction`` is chromadb's bundled in-process model
    (all-MiniLM-L6-v2, 384-dim). The test fixtures are tiny — first-call
    download is cached for the rest of the test session. The new env-var
    test bypasses this stub via ``_REAL_MAKE_EMBEDDING_FUNCTION``.
    """
    monkeypatch.setattr(
        ingest_corpus,
        "_make_embedding_function",
        lambda: DefaultEmbeddingFunction(),
    )
    yield


# ---------------------------------------------------------------------------
# Fixture corpus builder — synthetic Macbeth-shaped texts so the loader
# produces predictable chunk counts. We do NOT commit any real source text
# (legal posture per CONTRIBUTING-CORPUS.md); fixtures live in tmp_path.
# ---------------------------------------------------------------------------


# A primary-text-shaped fixture. Long enough that the chunker (CHUNK_SIZE=512)
# produces multiple chunks; structural markers (ACT/SCENE) so the citation-
# anchor inferer fires. Built from the canonical Lady Macbeth invocation.
_PRIMARY_TEXT_BODY = """\
ACT I

SCENE V

LADY MACBETH

Come, you spirits that tend on mortal thoughts, unsex me here, and fill me
from the crown to the toe top-full of direst cruelty. Make thick my blood,
stop up the access and passage to remorse, that no compunctious visitings
of nature shake my fell purpose, nor keep peace between the effect and it.

SCENE VII

MACBETH

If it were done when 'tis done, then 'twere well it were done quickly. If
the assassination could trammel up the consequence and catch with his
surcease success, that but this blow might be the be-all and the end-all
here, but here, upon this bank and shoal of time, we'd jump the life to
come. I have no spur to prick the sides of my intent, but only vaulting
ambition, which o'erleaps itself.
"""


_SECONDARY_TEXT_BODY = """\
Lady Macbeth's invocation in Act 1 Scene 5 is conventionally read as a
moment of feminine ambition transgressing Jacobean gender expectations.
Study guides typically frame the speech as a deliberate inversion of the
contemporary domestic ideal: she calls on supernatural forces to dehumanise
herself in pursuit of political power.
"""


def _write_fixture_corpus(root: Path) -> None:
    """Write a minimal four-folder corpus into ``root``.

    Layout:
      primary_text/macbeth.txt           -> chunked, primary
      secondary_study_guide/macbeth.txt  -> single secondary chunk
      (other two folders empty but present)
    """
    (root / "primary_text").mkdir(parents=True)
    (root / "secondary_study_guide").mkdir(parents=True)
    (root / "secondary_critical").mkdir(parents=True)
    (root / "context_historical").mkdir(parents=True)

    (root / "primary_text" / "macbeth.txt").write_text(
        _PRIMARY_TEXT_BODY, encoding="utf-8"
    )
    (root / "secondary_study_guide" / "macbeth.txt").write_text(
        _SECONDARY_TEXT_BODY, encoding="utf-8"
    )


def _run_ingest(
    *,
    domain_root: Path,
    persist_dir: Path,
    collection_name: str = "test-collection",
    reset: bool = False,
) -> list[dict[str, Any]]:
    """Invoke ``ingest_corpus.main`` programmatically and parse NDJSON stdout.

    Returns the list of parsed NDJSON records emitted by the script. Asserts
    the exit code is 0 on success — every test here drives a corpus that
    should ingest cleanly, so a non-zero return is a failure signal.
    """
    argv = [
        "--domain-root",
        str(domain_root),
        "--persist-dir",
        str(persist_dir),
        "--collection-name",
        collection_name,
    ]
    if reset:
        argv.append("--reset")
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = ingest_corpus.main(argv)
    assert rc == 0, f"ingest_corpus.main exited with {rc}"
    return [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]


def _open_collection(persist_dir: Path, collection_name: str = "test-collection") -> Any:
    """Re-open the same persistent client/collection the script wrote to."""
    client = chromadb.PersistentClient(path=str(persist_dir))
    return client.get_or_create_collection(name=collection_name)


# ---------------------------------------------------------------------------
# AC: ingestion produces the expected chunk count
# ---------------------------------------------------------------------------


def test_ingest_creates_chunks(tmp_path: Path) -> None:
    """Fixture corpus produces a non-empty Chroma collection."""
    domain_root = tmp_path / "corpus"
    persist_dir = tmp_path / "chroma"
    _write_fixture_corpus(domain_root)

    records = _run_ingest(domain_root=domain_root, persist_dir=persist_dir)

    summary = next(r for r in records if r["event"] == "ingest_summary")
    assert summary["chunks_created"] >= 2, (
        "fixture corpus should produce at least one primary + one secondary chunk"
    )
    assert summary["refusals"] == 0
    assert summary["skips"] == 0

    collection = _open_collection(persist_dir)
    assert collection.count() == summary["chunks_created"]


# ---------------------------------------------------------------------------
# AC: re-running the script with no source changes leaves the count unchanged
# ---------------------------------------------------------------------------


def test_ingest_is_idempotent(tmp_path: Path) -> None:
    """Re-running against an unchanged corpus must produce no new rows."""
    domain_root = tmp_path / "corpus"
    persist_dir = tmp_path / "chroma"
    _write_fixture_corpus(domain_root)

    _run_ingest(domain_root=domain_root, persist_dir=persist_dir)
    first_count = _open_collection(persist_dir).count()

    _run_ingest(domain_root=domain_root, persist_dir=persist_dir)
    second_count = _open_collection(persist_dir).count()

    assert first_count == second_count
    assert first_count > 0


# ---------------------------------------------------------------------------
# AC: --reset recreates the collection (asserted via sentinel)
# ---------------------------------------------------------------------------


def test_reset_drops_collection(tmp_path: Path) -> None:
    """Inject a sentinel doc, run with --reset, sentinel must be gone."""
    domain_root = tmp_path / "corpus"
    persist_dir = tmp_path / "chroma"
    _write_fixture_corpus(domain_root)

    _run_ingest(domain_root=domain_root, persist_dir=persist_dir)

    # Inject a sentinel directly into the live collection. If --reset works,
    # this sentinel will not survive the next ingest.
    collection = _open_collection(persist_dir)
    collection.upsert(
        ids=["sentinel"],
        documents=["sentinel doc"],
        metadatas=[{"sentinel": "yes"}],
    )
    assert collection.get(ids=["sentinel"])["ids"] == ["sentinel"]

    _run_ingest(domain_root=domain_root, persist_dir=persist_dir, reset=True)

    fresh = _open_collection(persist_dir)
    assert fresh.get(ids=["sentinel"])["ids"] == [], (
        "--reset should have dropped the collection (sentinel must be gone)"
    )


# ---------------------------------------------------------------------------
# AC: AQA-named files are refused at the loader and surface in NDJSON
# ---------------------------------------------------------------------------


def test_aqa_refusal_pass_through(tmp_path: Path) -> None:
    """An AQA-named file in primary_text/ must not reach the collection."""
    domain_root = tmp_path / "corpus"
    persist_dir = tmp_path / "chroma"
    _write_fixture_corpus(domain_root)

    aqa_path = domain_root / "primary_text" / "macbeth_past_paper.txt"
    aqa_path.write_text(
        "AQA past paper assessment material — must be refused.", encoding="utf-8"
    )

    records = _run_ingest(domain_root=domain_root, persist_dir=persist_dir)

    refusal_records = [r for r in records if r["event"] == "refusal"]
    aqa_refusals = [
        r for r in refusal_records if r["reason"] == "AQA_ASSESSMENT_MATERIAL"
    ]
    assert len(aqa_refusals) == 1, (
        f"expected exactly one AQA refusal, got {refusal_records!r}"
    )
    assert aqa_refusals[0]["path"].endswith("macbeth_past_paper.txt")

    collection = _open_collection(persist_dir)
    fetched = collection.get()
    aqa_source_paths = [
        m for m in fetched["metadatas"] if str(aqa_path) in m.get("source_path", "")
    ]
    assert aqa_source_paths == [], (
        "AQA source path must not appear in any persisted chunk metadata"
    )


# ---------------------------------------------------------------------------
# AC: chunk_json metadata round-trips through CorpusChunk.model_validate_json
# (the contract retrieval._hydrate_chunk depends on)
# ---------------------------------------------------------------------------


def test_metadata_round_trips_via_chunk_json(tmp_path: Path) -> None:
    """Pull one row back, hydrate it, assert it's a valid CorpusChunk."""
    domain_root = tmp_path / "corpus"
    persist_dir = tmp_path / "chroma"
    _write_fixture_corpus(domain_root)

    _run_ingest(domain_root=domain_root, persist_dir=persist_dir)

    collection = _open_collection(persist_dir)
    fetched = collection.get()
    assert fetched["ids"], "fixture ingest must produce at least one row"

    metadata = fetched["metadatas"][0]
    assert "chunk_json" in metadata, (
        "metadata must carry chunk_json — the load-bearing hydration contract"
    )

    rehydrated = CorpusChunk.model_validate_json(metadata["chunk_json"])
    assert rehydrated.text_name == metadata["text_name"]
    assert rehydrated.source_type.value == metadata["source_type"]
    assert rehydrated.source_path == metadata["source_path"]
    assert rehydrated.chunk_index == metadata["chunk_index"]


# ---------------------------------------------------------------------------
# AC: register_primary_text is called for each distinct primary text_name,
# and the .primary_text_index sidecar lists them
# ---------------------------------------------------------------------------


def test_register_primary_text_called_and_sidecar_written(tmp_path: Path) -> None:
    """The script populates the in-process registry and writes the sidecar."""
    domain_root = tmp_path / "corpus"
    persist_dir = tmp_path / "chroma"
    _write_fixture_corpus(domain_root)

    records = _run_ingest(domain_root=domain_root, persist_dir=persist_dir)

    summary = next(r for r in records if r["event"] == "ingest_summary")
    assert "macbeth" in summary["primary_text_names"]
    assert has_primary_text("macbeth"), (
        "register_primary_text must have populated the in-process registry"
    )

    sidecar = persist_dir / ingest_corpus.PRIMARY_TEXT_INDEX_FILENAME
    assert sidecar.exists()
    listed = [line for line in sidecar.read_text().splitlines() if line.strip()]
    assert "macbeth" in listed


# ---------------------------------------------------------------------------
# AC: --help mentions the install command (operator-facing docs)
# ---------------------------------------------------------------------------


def test_help_mentions_uv_sync_extra() -> None:
    """``--help`` must surface the ``uv sync --extra rag`` install hint."""
    result = subprocess.run(
        [sys.executable, "scripts/ingest_corpus.py", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "uv sync --extra rag" in result.stdout, (
        f"--help output should mention the install command; got:\n{result.stdout}"
    )


# ---------------------------------------------------------------------------
# AC: _make_embedding_function reads the DECISION-RAG-001 §3.1 env vars
# (LLM_EMBEDDINGS_BASE_URL / LLM_EMBEDDINGS_API_KEY / LLM_EMBEDDINGS_MODEL)
# ---------------------------------------------------------------------------


def test_make_embedding_function_uses_decision_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The three env vars must flow through to the constructed EF instance.

    Bypasses the autouse stub via the captured ``_REAL_MAKE_EMBEDDING_FUNCTION``
    reference. ``OpenAIEmbeddingFunction.__init__`` is offline — it stores
    ``api_base`` / ``api_key`` / ``model_name`` on private attributes
    (``_api_base`` / ``_api_key`` / ``_model_name``) without contacting the
    endpoint, which is exactly the introspection point we need.
    """
    monkeypatch.setenv("LLM_EMBEDDINGS_BASE_URL", "http://override:1234/v1")
    monkeypatch.setenv("LLM_EMBEDDINGS_API_KEY", "override-key")
    monkeypatch.setenv("LLM_EMBEDDINGS_MODEL", "override-model")

    ef = _REAL_MAKE_EMBEDDING_FUNCTION()

    # Attribute names match what chromadb's ``OpenAIEmbeddingFunction``
    # exposes (public ``api_base`` / ``api_key`` / ``model_name`` on
    # chromadb 1.5+). If the lib renames these in a future major, the test
    # will fail loudly — that's intentional, the wiring contract goes
    # through this exact attribute surface.
    assert ef.api_base == "http://override:1234/v1"
    assert ef.api_key == "override-key"
    assert ef.model_name == "override-model"


def test_make_embedding_function_default_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without env overrides, the EF carries the decision-§3.1 defaults."""
    monkeypatch.delenv("LLM_EMBEDDINGS_BASE_URL", raising=False)
    monkeypatch.delenv("LLM_EMBEDDINGS_API_KEY", raising=False)
    monkeypatch.delenv("LLM_EMBEDDINGS_MODEL", raising=False)

    ef = _REAL_MAKE_EMBEDDING_FUNCTION()

    assert ef.api_base == ingest_corpus.DEFAULT_EMBEDDINGS_BASE_URL
    assert ef.api_key == ingest_corpus.DEFAULT_EMBEDDINGS_API_KEY
    assert ef.model_name == ingest_corpus.DEFAULT_EMBEDDINGS_MODEL
