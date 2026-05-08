"""Shared OpenAI embedding-function helper (TASK-RAG-002 / DECISION-RAG-001 §3.1).

This module is the **single source of truth** for the runtime construction
of the ``OpenAIEmbeddingFunction`` that both the ingestion script
(:mod:`scripts.ingest_corpus`) and the CLI runtime
(:mod:`study_tutor.cli.rag_wiring`) use to talk to llama-swap. Two
copies of the construction logic — one in the writer, one in the reader
— would re-introduce the embedding-space mismatch failure mode that
DECISION-RAG-001 §3.1 calls out:

    Chroma's ``PersistentClient`` does not persist the embedding function
    across process restarts. If the runtime opens the collection with a
    different EF (or no EF at all, falling back to Chroma's bundled
    384-dim ``all-MiniLM-L6-v2``) than the writer used, every query
    embeds against vectors written under a different dimension and
    returns garbage.

Centralising the construction here means a single place to update the
canonical defaults, and both call sites inherit any fix automatically.

The function reads three env vars (DECISION-RAG-001 §3.1):

* ``LLM_EMBEDDINGS_BASE_URL`` (default ``http://localhost:9000/v1``) —
  llama-swap's OpenAI-compatible endpoint.
* ``LLM_EMBEDDINGS_API_KEY`` (default ``not-needed``) — load-bearing
  magic string. llama-swap ignores auth, but
  ``OpenAIEmbeddingFunction`` rejects empty strings at construction.
* ``LLM_EMBEDDINGS_MODEL`` (default ``nomic-embed-text``) — 768-dim
  embedding model the GB10 fleet has standardised on.

Lazy imports of ``chromadb`` keep the module importable on the dev path
that does not have the optional ``[rag]`` extra installed; ``ImportError``
is raised on call so the caller can implement the graceful-degradation
envelope (log ``event=rag_disabled, reason=embedding_function_unavailable``
and continue).
"""

from __future__ import annotations

import os
from typing import Any

#: DECISION-RAG-001 §3.1 canonical default for ``LLM_EMBEDDINGS_BASE_URL``.
#: Points at llama-swap's loopback OpenAI-compatible endpoint.
DEFAULT_EMBEDDINGS_BASE_URL: str = "http://localhost:9000/v1"

#: DECISION-RAG-001 §3.1 canonical default for ``LLM_EMBEDDINGS_API_KEY``.
#: ``"not-needed"`` is a load-bearing magic string —
#: ``OpenAIEmbeddingFunction`` rejects empty/None at construction.
DEFAULT_EMBEDDINGS_API_KEY: str = "not-needed"

#: DECISION-RAG-001 §3.1 canonical default for ``LLM_EMBEDDINGS_MODEL``.
#: 768-dim ``nomic-embed-text`` is the fleet-standard embedding model.
DEFAULT_EMBEDDINGS_MODEL: str = "nomic-embed-text"


def build_openai_embedding_function() -> Any:
    """Construct the canonical ``OpenAIEmbeddingFunction`` per DECISION-RAG-001 §3.1.

    Reads three env vars (with the defaults above). Construction is
    offline — the EF stores config and only contacts the endpoint when
    the collection's upsert/query paths invoke ``__call__``.

    Returns
    -------
    Any
        A ``chromadb.utils.embedding_functions.OpenAIEmbeddingFunction``
        instance. Typed as ``Any`` because ``chromadb`` is in the
        optional ``[rag]`` extra and would force every importer of this
        module to install it just to read the type annotation.

    Raises
    ------
    ImportError
        If ``chromadb`` (or its transitive ``openai`` dependency) is not
        importable. The caller decides whether to degrade gracefully
        (log ``event=rag_disabled, reason=embedding_function_unavailable``
        and continue with no collection wired) or propagate.
    """
    from chromadb.utils.embedding_functions import (  # type: ignore[import-not-found]
        OpenAIEmbeddingFunction,
    )

    return OpenAIEmbeddingFunction(
        api_base=os.environ.get(
            "LLM_EMBEDDINGS_BASE_URL", DEFAULT_EMBEDDINGS_BASE_URL
        ),
        api_key=os.environ.get(
            "LLM_EMBEDDINGS_API_KEY", DEFAULT_EMBEDDINGS_API_KEY
        ),
        model_name=os.environ.get(
            "LLM_EMBEDDINGS_MODEL", DEFAULT_EMBEDDINGS_MODEL
        ),
    )


__all__ = [
    "DEFAULT_EMBEDDINGS_API_KEY",
    "DEFAULT_EMBEDDINGS_BASE_URL",
    "DEFAULT_EMBEDDINGS_MODEL",
    "build_openai_embedding_function",
]
