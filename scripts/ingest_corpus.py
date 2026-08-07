#!/usr/bin/env python3
"""TASK-RAG-001 — chromadb ingestion script for the source-typed corpus.

This is the thin caller that the loader's docstring (``corpus.py:43``) defers
to: it imports ``chromadb`` lazily, walks a four-folder corpus root through
:func:`study_tutor.knowledge.corpus.load_corpus`, and upserts each
:class:`CorpusChunk` into a persistent collection.

The script is one-shot — it ingests and exits. **Runtime wiring of the
collection into ``set_collection_provider`` is out of scope** (TASK-RAG-002).

Fleet alignment (DECISION-RAG-001)
----------------------------------
Defaults and embedding wiring conform to
``guardkit/docs/decisions/DECISION-RAG-001-unified-chromadb-approach.md``
(accepted 2026-05-07). Both the specialist-agent and study-tutor share a
single ChromaDB pattern: ``PersistentClient`` co-located with the agent on
the GB10, with ``OpenAIEmbeddingFunction`` pointing at llama-swap's
OpenAI-compatible ``/v1/embeddings`` endpoint (``nomic-embed`` — the
llama-swap alias for upstream ``nomic-ai/nomic-embed-text-v1.5``, 768
dimensions). No Ollama, no Chroma server process, no cross-network hops.
The decision-§3.1 env vars (``CHROMA_PERSIST_DIR``, ``CHROMA_COLLECTION``,
``LLM_EMBEDDINGS_BASE_URL``, ``LLM_EMBEDDINGS_API_KEY``,
``LLM_EMBEDDINGS_MODEL``) override the hard-coded defaults; CLI flags
override env vars. If llama-swap is unreachable at ingest time the
embedding-side error propagates up from ``collection.upsert`` — there is no
silent fallback to the in-process default model.

Metadata contract
-----------------
The retrieval module's ``_hydrate_chunk`` (``retrieval.py:502``) reads each
row's ``chunk_json`` metadata key and round-trips it through
``CorpusChunk.model_validate_json``. Because Chroma metadata values must be
scalar (``str | int | float | bool``), the structured ``citation_anchor``
discriminated union cannot live as nested fields — it goes inside
``chunk_json``. The flat scalar fields (``text_name``, ``source_type``,
``source_path``, ``chunk_index``) are surfaced separately so Chroma's
``where``-clause filtering still works (the retriever filters by
``text_name`` and ``source_type``).

Idempotency
-----------
Each chunk's Chroma ID is ``f"{text_name}:{chunk_index}"`` — deterministic
across runs. The script uses ``collection.upsert`` so re-ingest of an
unchanged corpus produces zero new rows. ``--reset`` drops and recreates
the collection (operator safety hatch for schema-change re-ingests).

Output format
-------------
NDJSON to stdout (one JSON object per line); regular logging to stderr.
The operator can pipe stdout through ``jq`` cleanly. Event types:

* ``ingest_summary`` — emitted once: chunks created, refusals, skips,
  primary texts registered.
* ``per_text_count`` — emitted once per (``text_name``, ``source_type``)
  pair in the corpus, with the chunk count.
* ``citation_anchor_summary`` — emitted once per primary ``text_name``
  with ``anchored`` / ``unanchored`` chunk counts (always emitted; the
  regression gate for the 2026-05-10 all-anchors-lost re-ingest). Pair
  with ``--fail-on-unanchored`` to make a 100%-unanchored text fatal.
* ``refusal`` — emitted per refusal with ``reason`` and ``detail``.
* ``skip`` — emitted per skip with ``reason`` and ``detail``.

Install
-------
``chromadb`` is in the optional ``rag`` dependency group. Install with::

    uv sync --extra rag

The reranker (``sentence-transformers``) ships in the same extra so the
runtime CLI in TASK-RAG-002 can pin both deps with one command, but this
script does **not** import it.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Sequence

# Allow direct invocation (``python scripts/ingest_corpus.py`` or
# ``./scripts/ingest_corpus.py``) without first running ``uv sync``: prepend
# ``<repo_root>/src`` to ``sys.path`` so the in-tree ``study_tutor`` package is
# importable. Pytest already has this via ``pythonpath = ["src", "."]`` in
# ``pyproject.toml``; the bootstrap below is just for the script's
# operator-facing direct-invocation path.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_PATH = str(_REPO_ROOT / "src")
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)

# The corpus loader is the only study_tutor import this module needs;
# everything else (chromadb, retrieval registration) is touched lazily inside
# ``main`` so the module imports cleanly without the optional ``rag`` extra.
from study_tutor.knowledge.corpus import IngestResult, load_corpus  # noqa: E402
from study_tutor.knowledge.corpus_models import CorpusChunk, SourceType  # noqa: E402
from study_tutor.knowledge.embedding_function import (  # noqa: E402
    build_openai_embedding_function,
)

logger = logging.getLogger("study_tutor.ingest_corpus")


DEFAULT_DOMAIN_ROOT: Path = Path("domains/gcse-english/sources")
# DECISION-RAG-001 §3.1 / §4.2: versioned collection name and per-project
# ``data/chroma/`` persist root. The earlier values (unversioned name +
# ``./chroma/gcse-english/``) predated the fleet decision; aligning here so
# TASK-RAG-002, the docker-compose mounts, and the operator runbook all
# resolve to the same on-disk shape.
DEFAULT_COLLECTION_NAME: str = "gcse-english-v1"
DEFAULT_PERSIST_DIR: Path = Path("data/chroma")

# DECISION-RAG-001 §3.1 / §2.2: llama-swap defaults for the embedding
# function. ``api_key="not-needed"`` is the load-bearing magic string —
# llama-swap ignores auth, but ``OpenAIEmbeddingFunction`` rejects an empty
# string at construction time, so we must pass *something*. A future
# deployment that does require auth flips ``LLM_EMBEDDINGS_API_KEY`` only.
#
# Model name: ``nomic-embed`` is the llama-swap alias for upstream
# ``nomic-ai/nomic-embed-text-v1.5`` (768-dim) on the canonical GB10
# deployment (verified 2026-05-08, TASK-RAG-002 smoke). DECISION-RAG-001
# §3.1 originally drafted this as ``nomic-embed-text`` (the upstream id);
# the deployment registers the shorter alias instead. The shared helper
# at ``study_tutor.knowledge.embedding_function`` carries the same
# default — keep them in sync to avoid the writer/reader EF-mismatch
# failure mode the decision warns about.
DEFAULT_EMBEDDINGS_BASE_URL: str = "http://localhost:9000/v1"
DEFAULT_EMBEDDINGS_API_KEY: str = "not-needed"
DEFAULT_EMBEDDINGS_MODEL: str = "nomic-embed"

PRIMARY_TEXT_INDEX_FILENAME: str = ".primary_text_index"


# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ingest_corpus",
        description=(
            "Ingest a four-folder source-typed corpus into a persistent "
            "ChromaDB collection. Walks the corpus via "
            "study_tutor.knowledge.corpus.load_corpus, then upserts each "
            "CorpusChunk into the collection with a JSON-serialised payload "
            "under the 'chunk_json' metadata key (the retrieval module's "
            "load-bearing hydration contract)."
        ),
        epilog=(
            "Install: uv sync --extra rag\n"
            "Re-runs are idempotent (deterministic chunk IDs + upsert). Use "
            "--reset only after a schema-affecting code change."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # ADR-ARCH-032 D5: the subject convenience flag. When given, it
    # derives the corpus root (domains/gcse-<subject>/sources/), the
    # collection (gcse-<subject>-v1), and the sidecar name
    # (.primary_text_index.<subject>; english keeps the legacy name).
    # Explicit --domain-root / --collection-name still override.
    parser.add_argument(
        "--subject",
        type=str,
        default=None,
        help=(
            "Subject slug (e.g. 'english', 'french'). Derives the corpus "
            "root, collection name, and sidecar per ADR-ARCH-032; "
            "explicit --domain-root/--collection-name win. "
            "Default: english."
        ),
    )
    parser.add_argument(
        "--domain-root",
        type=Path,
        default=None,
        help=(
            "Path to the corpus root. Must contain four subfolders: "
            "primary_text/, secondary_study_guide/, secondary_critical/, "
            "context_historical/. Default: domains/gcse-<subject>/sources "
            f"(with no --subject: {DEFAULT_DOMAIN_ROOT})"
        ),
    )
    # CHROMA_COLLECTION / CHROMA_PERSIST_DIR (DECISION-RAG-001 §3.1) keep
    # their env-override meaning; resolution happens in ``main`` so the
    # --subject derivation can participate.
    parser.add_argument(
        "--collection-name",
        type=str,
        default=None,
        help=(
            "ChromaDB collection name. Default: $CHROMA_COLLECTION, else "
            f"gcse-<subject>-v1 (with no --subject: {DEFAULT_COLLECTION_NAME})"
        ),
    )
    parser.add_argument(
        "--persist-dir",
        type=Path,
        default=Path(os.environ.get("CHROMA_PERSIST_DIR", str(DEFAULT_PERSIST_DIR))),
        help=(
            "Directory for the persistent ChromaDB client. Will be created "
            "if missing. The .primary_text_index sidecar is written here too. "
            f"Default: $CHROMA_PERSIST_DIR or {DEFAULT_PERSIST_DIR}"
        ),
    )
    parser.add_argument(
        "--fail-on-unanchored",
        action="store_true",
        help=(
            "Exit non-zero (3) when any primary text ingests with 100%% "
            "unanchored chunks (citation-anchor inference produced nothing "
            "for that text — the 2026-05-10 regression shape). Off by "
            "default so existing callers are unaffected; the "
            "citation_anchor_summary NDJSON events are emitted either way."
        ),
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help=(
            "Drop the collection before ingest. Use after a schema-affecting "
            "code change (chunker tuning, citation-anchor format, etc.). "
            "Routine re-runs do NOT need this — upsert is idempotent."
        ),
    )
    return parser


# ---------------------------------------------------------------------------
# Chunk → Chroma payload
# ---------------------------------------------------------------------------


def _chunk_id(chunk: CorpusChunk) -> str:
    """Deterministic ID for a chunk: ``"<source_type>:<text_name>:<chunk_index>"``.

    Stable across runs so ``upsert`` is idempotent. ``source_type`` is part of
    the key because the loader's ``_derive_text_name`` uses the file's stem,
    so a primary-text edition and a study guide for the same work both yield
    ``text_name="macbeth"``; without the source-type prefix their chunks would
    collide on ID and ``collection.upsert`` would raise ``DuplicateIDError``.
    """
    return f"{chunk.source_type.value}:{chunk.text_name}:{chunk.chunk_index}"


def _chunk_metadata(chunk: CorpusChunk) -> dict[str, str | int]:
    """Build the Chroma metadata dict for ``chunk``.

    The shape MUST match what ``study_tutor.knowledge.retrieval._hydrate_chunk``
    reads (the JSON payload under ``chunk_json``) and what
    ``_query_collection`` filters on (``text_name`` and ``source_type``).
    Changing these keys is a breaking change for the retrieval contract.
    """
    return {
        "text_name": chunk.text_name,
        "source_type": chunk.source_type.value,
        "source_path": chunk.source_path,
        "chunk_index": chunk.chunk_index,
        "chunk_json": chunk.model_dump_json(),
    }


# ---------------------------------------------------------------------------
# Collection lifecycle
# ---------------------------------------------------------------------------


def _make_embedding_function() -> Any:
    """Build the ``OpenAIEmbeddingFunction`` per DECISION-RAG-001 §2.2.

    Delegates to
    :func:`study_tutor.knowledge.embedding_function.build_openai_embedding_function`
    — the single source of truth for the EF construction shared with the
    runtime CLI (TASK-RAG-002). Two copies (writer + reader) would
    re-introduce the embedding-space mismatch failure mode DECISION-RAG-001
    §3.1 warns about.

    The local module-level constants
    (:data:`DEFAULT_EMBEDDINGS_BASE_URL`, :data:`DEFAULT_EMBEDDINGS_API_KEY`,
    :data:`DEFAULT_EMBEDDINGS_MODEL`) remain because they're referenced by
    ``--help`` text; behaviour is identical because the shared helper
    reads its own copies from env vars with the same canonical defaults.
    """
    return build_openai_embedding_function()


def _open_collection(
    persist_dir: Path,
    collection_name: str,
    *,
    reset: bool,
    embedding_function: Any | None = None,
) -> Any:
    """Open a persistent ChromaDB collection, creating ``persist_dir`` if needed.

    When ``reset`` is true, drop the collection first; ``get_or_create`` then
    yields a fresh, empty one. The drop is best-effort: if the collection
    doesn't exist yet, swallow the ``ValueError`` chromadb raises rather than
    treating "nothing to delete" as an error.

    ``embedding_function`` defaults to ``None`` meaning "build the production
    ``OpenAIEmbeddingFunction`` via :func:`_make_embedding_function`". Tests
    that need to avoid contacting llama-swap pass an in-process EF (e.g.
    ``DefaultEmbeddingFunction()``) so collection writes are hermetic.

    Lazy import of ``chromadb`` keeps the module importable on the dev path
    (no ``rag`` extra installed) — tests that don't exercise the chromadb
    surface can still import this module without paying the dependency cost.
    """
    import chromadb  # type: ignore[import-not-found]

    persist_dir.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(persist_dir))

    if reset:
        try:
            client.delete_collection(name=collection_name)
        except Exception as exc:  # noqa: BLE001 — chromadb raises ValueError; tolerate
            logger.info(
                "ingest.reset.delete_skipped",
                extra={"detail": f"{type(exc).__name__}: {exc}"},
            )

    if embedding_function is None:
        embedding_function = _make_embedding_function()

    return client.get_or_create_collection(
        name=collection_name,
        embedding_function=embedding_function,
    )


def _upsert_chunks(collection: Any, chunks: Sequence[CorpusChunk]) -> None:
    """Upsert all ``chunks`` into ``collection`` in a single call.

    chromadb accepts batched ``upsert`` and is significantly faster than
    chunk-at-a-time calls; the script's correctness doesn't depend on the
    batch size, only on deterministic IDs. An empty ``chunks`` sequence
    short-circuits — chromadb's ``upsert`` rejects empty arrays.
    """
    if not chunks:
        return
    collection.upsert(
        ids=[_chunk_id(c) for c in chunks],
        documents=[c.text for c in chunks],
        metadatas=[_chunk_metadata(c) for c in chunks],
    )


# ---------------------------------------------------------------------------
# Primary-text registry sidecar
# ---------------------------------------------------------------------------


def _primary_text_names(chunks: Iterable[CorpusChunk]) -> list[str]:
    """Return the distinct ``text_name`` values for primary-text chunks.

    Output is sorted for stable downstream display and for deterministic
    sidecar file content (so re-runs over the same corpus produce
    byte-identical files).
    """
    names: set[str] = set()
    for chunk in chunks:
        if chunk.source_type is SourceType.PRIMARY_TEXT:
            names.add(chunk.text_name)
    return sorted(names)


def _citation_anchor_counts(
    chunks: Iterable[CorpusChunk],
) -> dict[str, tuple[int, int]]:
    """Per-primary-text ``(anchored, unanchored)`` chunk counts.

    Only ``PRIMARY_TEXT`` chunks are counted — secondary / context chunks
    never carry a :class:`CitationAnchor` by contract, so including them
    would drown the signal this gate exists for (the quote verifier's
    citation rendering depends on primary anchors; a text ingesting 100%
    unanchored means every verified quote for it degrades to an uncited
    quotation).
    """
    counts: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for chunk in chunks:
        if chunk.source_type is not SourceType.PRIMARY_TEXT:
            continue
        if chunk.citation_anchor is None:
            counts[chunk.text_name][1] += 1
        else:
            counts[chunk.text_name][0] += 1
    return {name: (anchored, unanchored) for name, (anchored, unanchored) in counts.items()}


def _sidecar_filename(subject: str) -> str:
    """Sidecar name for ``subject`` (ADR-ARCH-032 D2/D5).

    English keeps the legacy unsuffixed name so pre-scoping stores stay
    readable; other subjects get ``.primary_text_index.<subject>``.
    Mirrors ``study_tutor.cli.rag_wiring.subject_sidecar_filename`` —
    kept as a local copy because this script must stay runnable without
    importing CLI wiring; the ingest round-trip test pins the two
    functions to the same values.
    """
    if subject == "english":
        return PRIMARY_TEXT_INDEX_FILENAME
    return f"{PRIMARY_TEXT_INDEX_FILENAME}.{subject}"


def _register_primary_texts(
    persist_dir: Path, names: Sequence[str], subject: str = "english"
) -> Path:
    """Register each ``text_name`` in the runtime registry and write a sidecar.

    Two writes happen here:

    1. ``study_tutor.knowledge.retrieval.register_primary_text`` populates the
       in-process subject-keyed index that ``has_primary_text`` reads. This is
       lost when the script exits, but it makes the script's exit invariant
       observable to any in-process caller (e.g. tests).
    2. ``<persist_dir>/<sidecar>`` records the registered names so the
       runtime CLI in TASK-RAG-002 can replay the registration at startup.
       One name per line, sorted, trailing newline; sidecar name per
       :func:`_sidecar_filename`.

    Returns the sidecar path so callers can log it.
    """
    from study_tutor.knowledge.retrieval import register_primary_text

    for name in names:
        register_primary_text(name, subject)

    sidecar = persist_dir / _sidecar_filename(subject)
    sidecar.write_text("\n".join(names) + ("\n" if names else ""), encoding="utf-8")
    return sidecar


# ---------------------------------------------------------------------------
# NDJSON summary
# ---------------------------------------------------------------------------


def _emit(record: dict[str, Any]) -> None:
    """Write a single NDJSON record to stdout."""
    sys.stdout.write(json.dumps(record, sort_keys=True) + "\n")
    sys.stdout.flush()


def _emit_summary(
    result: IngestResult,
    primary_text_names: Sequence[str],
    sidecar_path: Path,
    anchor_counts: dict[str, tuple[int, int]] | None = None,
) -> None:
    """Emit the NDJSON summary lines: refusals, skips, per-text, anchors, header.

    ``anchor_counts`` (from :func:`_citation_anchor_counts`) drives the
    always-emitted ``citation_anchor_summary`` events; ``None`` computes
    it from ``result.chunks`` so direct callers stay one-argument-simple.
    """
    if anchor_counts is None:
        anchor_counts = _citation_anchor_counts(result.chunks)
    for refusal in result.refusals:
        _emit(
            {
                "event": "refusal",
                "path": refusal.path,
                "reason": refusal.reason.value,
                "detail": refusal.detail,
            }
        )
    for skip in result.skips:
        _emit(
            {
                "event": "skip",
                "path": skip.path,
                "reason": skip.reason.value,
                "detail": skip.detail,
            }
        )

    counts: dict[tuple[str, str], int] = defaultdict(int)
    for chunk in result.chunks:
        counts[(chunk.text_name, chunk.source_type.value)] += 1
    for (text_name, source_type), chunk_count in sorted(counts.items()):
        _emit(
            {
                "event": "per_text_count",
                "text_name": text_name,
                "source_type": source_type,
                "chunk_count": chunk_count,
            }
        )

    for text_name, (anchored, unanchored) in sorted(anchor_counts.items()):
        _emit(
            {
                "event": "citation_anchor_summary",
                "text_name": text_name,
                "anchored": anchored,
                "unanchored": unanchored,
            }
        )

    _emit(
        {
            "event": "ingest_summary",
            "chunks_created": result.chunks_created,
            "refusals": len(result.refusals),
            "skips": len(result.skips),
            "primary_text_names": list(primary_text_names),
            "primary_text_index_sidecar": str(sidecar_path),
        }
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ingestion. ``argv`` is exposed for programmatic / test use.

    Returns the process exit code (0 on success, non-zero on fatal error).
    Per-file refusals and skips are NOT fatal — they're surfaced in the
    NDJSON summary so the operator can audit them, but the ingest still
    completes for the rest of the corpus.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )

    args = _build_parser().parse_args(argv)

    # ADR-ARCH-032 D5 resolution order: explicit flag > env (collection
    # only) > --subject derivation > the english defaults (which are the
    # subject derivation for 'english' — DEFAULT_DOMAIN_ROOT and
    # DEFAULT_COLLECTION_NAME both parse under the scheme).
    subject: str = args.subject or "english"
    domain_root: Path = args.domain_root or Path(
        f"domains/gcse-{subject}/sources"
    )
    persist_dir: Path = args.persist_dir
    collection_name: str = (
        args.collection_name
        or os.environ.get("CHROMA_COLLECTION")
        or f"gcse-{subject}-v1"
    )

    try:
        result = load_corpus(domain_root)
    except FileNotFoundError as exc:
        logger.error(
            "ingest.corpus_root_missing",
            extra={"detail": str(exc), "domain_root": str(domain_root)},
        )
        return 2

    collection = _open_collection(
        persist_dir=persist_dir,
        collection_name=collection_name,
        reset=args.reset,
    )
    _upsert_chunks(collection, result.chunks)

    primary_names = _primary_text_names(result.chunks)
    sidecar = _register_primary_texts(persist_dir, primary_names, subject)

    anchor_counts = _citation_anchor_counts(result.chunks)
    _emit_summary(result, primary_names, sidecar, anchor_counts)

    if args.fail_on_unanchored:
        fully_unanchored = sorted(
            text_name
            for text_name, (anchored, unanchored) in anchor_counts.items()
            if anchored == 0 and unanchored > 0
        )
        if fully_unanchored:
            logger.error(
                "ingest.citation_anchor.fully_unanchored",
                extra={"text_names": ",".join(fully_unanchored)},
            )
            return 3

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
