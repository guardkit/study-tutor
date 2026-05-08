"""RAG wiring helper for ``serve`` startup (TASK-RAG-002).

This module owns the side-effect of opening the persistent ChromaDB
collection, wiring it into the runtime via
:func:`study_tutor.knowledge.retrieval.set_collection_provider`, and
replaying the primary-text registry sidecar from disk so
:func:`study_tutor.knowledge.retrieval.has_primary_text` returns the
correct branch in the four-branch decision tree.

The function lives in its own module rather than inside
:mod:`study_tutor.cli.main` so:

* the ``serve`` command remains terse and focused on the FastMCP run
  loop;
* the wiring logic is independently testable without needing to drive
  click's command machinery.

Graceful degradation envelope (per the AC and DECISION-RAG-001 §4):

* ``chromadb`` not importable → log ``event=rag_disabled
  reason=chromadb_missing`` and return; collection provider stays
  unwired and ``retrieve()`` returns ``[]``.
* persist dir missing → log ``event=rag_disabled
  reason=persist_dir_missing path=...`` and return.
* ``OpenAIEmbeddingFunction`` construction fails (e.g. ``openai``
  missing in degraded install) → log ``event=rag_disabled
  reason=embedding_function_unavailable`` and return.

In all three branches the verifier still runs (against an empty corpus)
so the Coach receives a structured :class:`VerifierMetadata` and the
serve loop continues. The runtime never fails closed on RAG.

Env vars consumed (DECISION-RAG-001 §3.1 — fleet alignment with the
ingest script):

* ``CHROMA_PERSIST_DIR`` — default ``data/chroma``.
* ``CHROMA_COLLECTION`` — default ``gcse-english-v1``.
* The three ``LLM_EMBEDDINGS_*`` vars are read inside
  :func:`study_tutor.knowledge.embedding_function.build_openai_embedding_function`.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

from study_tutor.knowledge.embedding_function import (
    build_openai_embedding_function,
)
from study_tutor.knowledge.retrieval import (
    register_primary_text,
    set_collection_provider,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level constants (DECISION-RAG-001 §3.1 + §4.2)
# ---------------------------------------------------------------------------

#: Env var name for the persistent ChromaDB directory. Fleet-shared per
#: DECISION-RAG-001 §3.1 — both the ingest script and the runtime CLI
#: read the same name so a single env block in docker-compose configures
#: the lot.
RAG_PERSIST_DIR_ENV: str = "CHROMA_PERSIST_DIR"

#: Env var name for the ChromaDB collection. Same alignment rationale.
RAG_COLLECTION_ENV: str = "CHROMA_COLLECTION"

#: Default persist directory (``data/chroma`` per DECISION-RAG-001 §4.2).
DEFAULT_PERSIST_DIR: Path = Path("data/chroma")

#: Default collection name (versioned per DECISION-RAG-001 §3.1 — the
#: ``-v1`` suffix is load-bearing for forward-compat once the schema
#: changes).
DEFAULT_COLLECTION_NAME: str = "gcse-english-v1"

#: Sidecar filename inside ``persist_dir`` written by the ingest script
#: (see :data:`scripts.ingest_corpus.PRIMARY_TEXT_INDEX_FILENAME`). One
#: ``text_name`` per line, sorted, trailing newline.
PRIMARY_TEXT_INDEX_FILENAME: str = ".primary_text_index"


# ---------------------------------------------------------------------------
# Public wiring entry point
# ---------------------------------------------------------------------------


def build_rag_providers(role_config: Any) -> None:
    """Open the persistent collection and wire it into the runtime.

    Side-effect-only: returns ``None``. On the happy path this calls
    :func:`set_collection_provider` and replays the primary-text registry
    sidecar; on any failure path it logs a structured ``rag_disabled``
    line at WARNING and returns. The runtime never fails closed on RAG.

    The ``role_config`` argument is currently unused — it's threaded
    through so future role-specific wiring (per-role collection names,
    role-aware reranker configs) can land without a public-API change.

    Parameters
    ----------
    role_config
        The resolved role manifest (from ``load_role(...)``). Reserved
        for future use; not consulted in Phase 1.

    Notes
    -----
    Called once at ``serve`` startup, before the orchestrator factory is
    constructed and before :class:`MCPAdapter`'s boot smoke runs. The
    boot smoke (TASK-RAG-002 / TASK-LCA-004 extension) reads the wired
    provider via :func:`get_collection_provider` to verify wiring.

    TODO — DECISION-RAG-001 §3.1: install a real embedder probe via
    :func:`study_tutor.knowledge.retrieval.set_embedder_probe` that
    pings ``LLM_EMBEDDINGS_BASE_URL`` with a single one-token payload.
    Phase 1 keeps the no-op default so the four-branch decision still
    routes correctly when llama-swap is reachable (the demo state). The
    failure mode this would catch is "llama-swap unreachable at serve
    startup" → ``reason=analysis_mode:embedder_timeout``. Deferred per
    plan AD-4.
    """
    persist_dir = Path(
        os.environ.get(RAG_PERSIST_DIR_ENV, str(DEFAULT_PERSIST_DIR))
    )
    collection_name = os.environ.get(
        RAG_COLLECTION_ENV, DEFAULT_COLLECTION_NAME
    )

    # Log resolved values so the demo log pane shows config at boot.
    logger.info(
        "event=rag_wiring_resolved persist_dir=%s collection=%s",
        persist_dir,
        collection_name,
    )

    try:
        import chromadb  # type: ignore[import-not-found]
    except ImportError:
        logger.warning("event=rag_disabled reason=chromadb_missing")
        return

    if not persist_dir.exists():
        logger.warning(
            "event=rag_disabled reason=persist_dir_missing path=%s",
            persist_dir,
        )
        return

    try:
        ef = build_openai_embedding_function()
    except ImportError:
        logger.warning(
            "event=rag_disabled reason=embedding_function_unavailable"
        )
        return

    client = chromadb.PersistentClient(path=str(persist_dir))
    collection = client.get_or_create_collection(
        name=collection_name,
        embedding_function=ef,
    )

    # Pin the collection in a zero-arg lambda — the retrieval module
    # treats the provider as a callable so tests can swap the underlying
    # collection without re-wiring the seam.
    set_collection_provider(lambda: collection)

    primary_count = _replay_primary_text_index(persist_dir)

    logger.info(
        "event=rag_wired collection=%s persist_dir=%s primary_texts=%d",
        collection_name,
        persist_dir,
        primary_count,
    )


# ---------------------------------------------------------------------------
# Sidecar replay (per-entry fail-soft, AD-7)
# ---------------------------------------------------------------------------


def _replay_primary_text_index(persist_dir: Path) -> int:
    """Replay the primary-text registry sidecar from disk.

    The sidecar is one ``text_name`` per line, sorted, trailing newline
    (see :func:`scripts.ingest_corpus._register_primary_texts`). At serve
    startup we read each line, strip whitespace, skip empties, and call
    :func:`register_primary_text` on the rest.

    Per-entry failures are logged at WARNING and skipped (per plan AD-7
    + architect's recommendation). A corrupt sidecar must not crash boot,
    but a silently-missed registration would route ``decide_retrieval``
    to the wrong branch (AnalysisMode for a text that *does* have
    primary chunks indexed) with no operator signal — WARNING is the
    right level for that operator-actionable mis-state.

    Parameters
    ----------
    persist_dir
        Directory containing the sidecar at
        :data:`PRIMARY_TEXT_INDEX_FILENAME`.

    Returns
    -------
    int
        Number of names successfully registered. ``0`` when the sidecar
        is missing (the most common case during a clean checkout before
        the operator has run the ingest script).
    """
    sidecar = persist_dir / PRIMARY_TEXT_INDEX_FILENAME
    if not sidecar.exists():
        logger.info(
            "event=rag_primary_text_index_missing path=%s",
            sidecar,
        )
        return 0

    count = 0
    try:
        contents = sidecar.read_text(encoding="utf-8")
    except OSError as exc:
        logger.warning(
            "event=rag_primary_text_index_read_failed path=%s error=%s",
            sidecar,
            exc,
        )
        return 0

    for raw_line in contents.splitlines():
        name = raw_line.strip()
        if not name:
            continue
        try:
            register_primary_text(name)
            count += 1
        except Exception as exc:  # noqa: BLE001 — fail-soft per AD-7
            logger.warning(
                "event=rag_primary_text_register_failed name=%r error=%s",
                name,
                exc,
            )
    return count


__all__ = [
    "DEFAULT_COLLECTION_NAME",
    "DEFAULT_PERSIST_DIR",
    "PRIMARY_TEXT_INDEX_FILENAME",
    "RAG_COLLECTION_ENV",
    "RAG_PERSIST_DIR_ENV",
    "build_rag_providers",
]
