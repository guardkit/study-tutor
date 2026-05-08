"""Dynamic retrieval-decision function (R2 + R3) and source-filtered retrieval.

This module owns two adjacent responsibilities for the primary-text-RAG
pipeline (FEAT-PRV4 / FEAT-PH1-004):

1. The pre-Player decision point (TASK-PRV-003) — ``should_retrieve`` /
   ``decide_retrieval`` encoding the R2 + R3 four-branch decision tree
   plus the embedder-timeout override.
2. The retrieval call itself (TASK-PRV-004) — ``retrieve``, a
   source-filtered ChromaDB similarity search with primary-first
   ordering, BGE reranker baseline (with graceful degradation on
   ``ImportError``), and defence-in-depth AQA exclusion.

The two surfaces share the same module because both honour the same
contract (``CorpusChunk`` from TASK-PRV-002) and tests reset the same
slice of module-level state between cases.

Decision tree (in order)
------------------------
1. ``focus_aos == {"AO3"}`` → AO3 bypass
   (training-first; retrieval would distract from rubric-only practice).
2. ``not has_primary_text(text_name)`` → AnalysisMode
   (no primary text indexed for this work, so retrieval has nothing to
   ground a Player response in).
3. ``"AO3" in focus_aos and len(focus_aos) > 1`` → mixed retrieval
   (AO3 plus AO1/AO2 — Coach scores AO3 differently downstream, so we
   record ``mode="mixed"`` separately from ``retrieve``).
4. Otherwise → primary retrieval.

Embedder unavailability override
--------------------------------
If the embedder probe does not respond within
``EMBEDDER_TIMEOUT_SECONDS`` the orchestrator forces
``(False, REASON_EMBEDDER_TIMEOUT, "analysis_mode")`` regardless of the
four-branch outcome. ``embedder_available_within`` is exposed so the
upstream caller can implement that override; ``decide_retrieval`` is a
convenience wrapper that applies it on top of ``should_retrieve``.

Why a NamedTuple, not a Pydantic model
--------------------------------------
``RetrievalDecision`` is returned from a hot-path pre-Player check; tuple
unpacking is zero-cost. We never deserialise a ``RetrievalDecision`` from
JSON, so Pydantic validation buys nothing.

Why reason strings are module-level constants
---------------------------------------------
The @key-example scenarios assert against literal reason strings; if we
ever rename ``"analysis_mode:no_primary_text"`` tests should fail loudly
via identity check on the constant, not silently still match a stale
literal copy. ASSUM-006 confirmed.

Why ChromaDB and the reranker are dependency-injected
-----------------------------------------------------
Neither ``chromadb`` nor ``sentence_transformers`` is in
``pyproject.toml`` (the loader in ``corpus.py`` is also free of those
imports). Wiring real backends is the orchestrator's job at startup —
this module exposes ``set_collection_provider`` /
``set_reranker_factory`` so the orchestrator (and tests) inject them
without forcing the hot path to pay an import cost on every call. The
``ImportError``-on-default branch in ``_load_reranker`` is the
graceful-degradation path the AC requires: when the reranker package
isn't installed (CI without the ~568 MB model cache, etc.), retrieval
still completes — it just returns base-similarity ordering and records
``mode="no_rerank"`` so the orchestrator can surface the degradation in
turn metadata.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path
from typing import Any, Callable, NamedTuple, Sequence

from study_tutor.knowledge.corpus_models import CorpusChunk, SourceType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level reason-string constants
# ---------------------------------------------------------------------------
#
# Tests assert ``decision.reason is REASON_X`` (identity, not equality), so
# these must remain interned module-level constants, not local literals.

REASON_NO_PRIMARY: str = "analysis_mode:no_primary_text"
REASON_AO3_ONLY: str = "ao3_only:training_first"
REASON_EMBEDDER_TIMEOUT: str = "analysis_mode:embedder_timeout"
REASON_RETRIEVE_PRIMARY: str = "retrieve:primary_present"
REASON_RETRIEVE_MIXED: str = "retrieve:mixed_ao3"

# Wall-clock budget for the embedder availability probe. Sourced from the
# 23-Apr OpenWebUI session — anything beyond this is treated as unavailable.
EMBEDDER_TIMEOUT_SECONDS: float = 5.0


# ---------------------------------------------------------------------------
# Decision result
# ---------------------------------------------------------------------------


class RetrievalDecision(NamedTuple):
    """Outcome of the pre-Player retrieval decision.

    Fields
    ------
    retrieve : bool
        Whether the orchestrator should hit the retriever.
    reason : str
        One of the module-level ``REASON_*`` constants. Tests compare with
        ``is`` rather than ``==`` so renames fail loudly.
    mode : str
        One of ``"retrieve"``, ``"analysis_mode"``, ``"ao3_bypass"``, or
        ``"mixed"``. Recorded separately from ``retrieve`` so Coach can
        apply different scoring posture for AO3 portions of a mixed-mode
        response without re-running this decision.
    """

    retrieve: bool
    reason: str
    mode: str


# ---------------------------------------------------------------------------
# Primary-text corpus index
# ---------------------------------------------------------------------------
#
# The corpus loader (TASK-PRV-002) populates this set at startup with the
# ``text_name`` of every work that has at least one ``PRIMARY_TEXT`` chunk
# indexed. ``has_primary_text`` is a pure lookup against it.
#
# Kept as a module-level mutable set (rather than re-querying the vector
# store on every call) because the decision function runs on the hot path
# before every Player turn — a corpus-index lookup must not pay an I/O
# cost. The set is mutated only through the public registration helpers
# below; tests use them to install fixtures and tear them down.

_PRIMARY_TEXT_INDEX: set[str] = set()


def register_primary_text(text_name: str) -> None:
    """Mark ``text_name`` as having primary-text chunks in the corpus.

    Called by the corpus loader (TASK-PRV-002) once per distinct
    ``text_name`` that yields at least one ``SourceType.PRIMARY_TEXT``
    chunk. Tests use this to install fixtures.

    Raises
    ------
    ValueError
        If ``text_name`` is empty. The corpus contract guarantees a
        non-empty ``text_name`` (``CorpusChunk.text_name`` has
        ``min_length=1``); rejecting empty input here surfaces upstream
        bugs rather than silently registering a sentinel value.
    """
    if not text_name:
        raise ValueError("text_name must be a non-empty string")
    _PRIMARY_TEXT_INDEX.add(text_name)


def clear_primary_text_index() -> None:
    """Reset the primary-text corpus index.

    Called by tests between cases and by the loader on full reload. We
    expose this as a named helper rather than letting callers reach into
    the underscore-prefixed set directly so the contract stays narrow.
    """
    _PRIMARY_TEXT_INDEX.clear()


def has_primary_text(text_name: str) -> bool:
    """Return ``True`` if ``text_name`` has primary-text chunks indexed."""
    return text_name in _PRIMARY_TEXT_INDEX


# ---------------------------------------------------------------------------
# Embedder availability probe
# ---------------------------------------------------------------------------
#
# The decision function itself does not probe the embedder — that would
# couple a pure decision into network I/O. Instead, the probe is a
# separately-installed callable whose wall-clock duration is measured by
# ``embedder_available_within``. Real deployments wire the actual ping
# at startup via ``set_embedder_probe``; tests inject sleep stubs.


def _default_embedder_probe() -> None:
    """Default no-op probe.

    Real systems install a probe that pings the embedding service. The
    no-op default means tests that don't explicitly care about embedder
    availability get ``embedder_available_within → True`` for free.
    """
    return None


_embedder_probe: Callable[[], None] = _default_embedder_probe


def set_embedder_probe(probe: Callable[[], None]) -> None:
    """Install the embedder availability probe.

    The probe is a synchronous callable that returns when the embedding
    service has acknowledged a ping (or raises if it cannot). Wiring is
    done once at orchestrator startup; tests rebind it per case.
    """
    global _embedder_probe
    _embedder_probe = probe


def reset_embedder_probe() -> None:
    """Restore the default no-op probe (test teardown helper)."""
    global _embedder_probe
    _embedder_probe = _default_embedder_probe


def embedder_available_within(timeout_s: float) -> bool:
    """Return ``True`` if the installed probe completes within ``timeout_s``.

    Wall-clock duration is measured around the probe with
    ``time.monotonic`` (which is immune to system-clock jumps). A probe
    that raises is treated as unavailable — we log at WARNING and return
    ``False`` rather than propagate, because the upstream caller's
    handling of "embedder is down" and "embedder is slow" is the same:
    fall back to analysis-mode.

    Parameters
    ----------
    timeout_s : float
        Wall-clock budget for the probe in seconds. Must be positive.

    Raises
    ------
    ValueError
        If ``timeout_s`` is non-positive — we refuse to silently treat
        zero/negative timeouts as "always unavailable", because that
        usually indicates a configuration bug at the call site.
    """
    if timeout_s <= 0:
        raise ValueError(
            f"timeout_s must be positive (got {timeout_s!r})"
        )
    start = time.monotonic()
    try:
        _embedder_probe()
    except Exception as exc:  # noqa: BLE001 — see docstring
        logger.warning(
            "embedder probe raised %s; treating as unavailable",
            type(exc).__name__,
        )
        return False
    elapsed = time.monotonic() - start
    return elapsed <= timeout_s


# ---------------------------------------------------------------------------
# Decision functions
# ---------------------------------------------------------------------------


def should_retrieve(text_name: str, focus_aos: set[str]) -> RetrievalDecision:
    """Pure four-branch retrieval decision (R2 + R3).

    Does NOT probe the embedder — that override is composed on top by
    ``decide_retrieval`` (or any equivalent orchestrator wrapper). Keeping
    ``should_retrieve`` pure makes it cheap to unit-test the four branches
    without mocking out network I/O.

    Parameters
    ----------
    text_name : str
        Name of the literary work the student is studying (e.g.
        ``"Macbeth"``). Looked up against the corpus index.
    focus_aos : set[str]
        Assessment Objectives the current turn is targeting (e.g.
        ``{"AO1", "AO2"}``). Compared against ``{"AO3"}`` for the bypass
        branch and probed for membership/cardinality for the mixed
        branch. Defensively coerced to ``set`` so callers passing
        ``frozenset`` / ``list`` / ``tuple`` are not silently mis-routed
        through the ``==`` comparison.
    """
    focus_aos_set = set(focus_aos)

    # Branch 1: AO3-only training pass — never retrieve, regardless of
    # whether the corpus has a primary text. R3 from the 23-Apr session.
    if focus_aos_set == {"AO3"}:
        return RetrievalDecision(False, REASON_AO3_ONLY, "ao3_bypass")

    # Branch 2: no primary text indexed — fall back to AnalysisMode.
    # Player runs against secondary/context corpora downstream.
    if not has_primary_text(text_name):
        return RetrievalDecision(False, REASON_NO_PRIMARY, "analysis_mode")

    # Branch 3: mixed AO3 + non-AO3 — retrieve, but tag mode="mixed" so
    # Coach can apply AO3-aware scoring on the relevant portions without
    # re-running this decision.
    if "AO3" in focus_aos_set and len(focus_aos_set) > 1:
        return RetrievalDecision(True, REASON_RETRIEVE_MIXED, "mixed")

    # Branch 4: primary present, non-AO3-only — standard retrieval.
    return RetrievalDecision(True, REASON_RETRIEVE_PRIMARY, "retrieve")


def decide_retrieval(
    text_name: str,
    focus_aos: set[str],
    *,
    timeout_s: float = EMBEDDER_TIMEOUT_SECONDS,
) -> RetrievalDecision:
    """Composed decision: embedder-timeout override + four-branch logic.

    This is the entry point the orchestrator calls. It first probes the
    embedder; if the probe takes longer than ``timeout_s`` (or raises),
    it forces analysis-mode regardless of the four-branch outcome.
    Otherwise it delegates to ``should_retrieve``.

    Existing pure callers can keep using ``should_retrieve`` directly;
    this wrapper exists so the parametrised test of all five decision
    cases (four branches + timeout override) has a single entry point.
    """
    if not embedder_available_within(timeout_s):
        return RetrievalDecision(
            False, REASON_EMBEDDER_TIMEOUT, "analysis_mode"
        )
    return should_retrieve(text_name, focus_aos)


# ---------------------------------------------------------------------------
# Source-filtered retrieval (TASK-PRV-004)
# ---------------------------------------------------------------------------
#
# ``retrieve`` is the read entry point downstream of the four-branch
# decision. The orchestrator only calls it when ``RetrievalDecision.retrieve``
# is True — this function does not re-run the decision logic.
#
# Design choices:
#   * The ChromaDB collection is provided by an injectable callable so the
#     hot path never imports ``chromadb`` itself. Real deployments install
#     the provider once at startup (``set_collection_provider``); tests
#     install fakes per case.
#   * The reranker is also injectable. The default factory tries to import
#     ``sentence_transformers.CrossEncoder``; on ``ImportError`` we record
#     ``mode="no_rerank"`` and fall back to base-similarity ordering. The
#     AC requires this graceful-degradation path because CI does not have
#     the ~568 MB BGE model cached and we still need turns to complete.
#   * Primary-first ordering is enforced *after* (re)ranking by partitioning
#     the candidate list — secondary chunks fill remaining top-K slots only
#     when fewer than K primaries are available. The seam test asserts the
#     stronger invariant that ALL primary chunks appear before ANY secondary
#     chunk, not just at equal score.
#   * AQA-pattern filenames are filtered out of the candidate list as
#     defence-in-depth: the loader (TASK-PRV-002) refuses them at ingestion,
#     but if a record slips past (typo, new pattern), the retrieval-time
#     filter is the safety net. The cost is one regex per candidate.

# Reranker model identifier — ASSUM confirmed via the 23-Apr OpenWebUI
# session. Held as a module-level constant so the orchestrator and tests
# can introspect what production would load.
RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"

# Default top-K. ASSUM-001 confirmed K=6 in the task spec.
DEFAULT_TOP_K: int = 6

# We over-fetch from ChromaDB before reranking so the reranker has more
# candidates to reorder. Without over-fetching, the reranker is just
# rubber-stamping the embedding-distance ordering. 4× is the default the
# 23-Apr session settled on; tests don't depend on the exact value.
RETRIEVAL_CANDIDATE_MULTIPLIER: int = 4

# Source types eligible for non-AO3 retrieval. ``CONTEXT_HISTORICAL`` is
# excluded by design — that folder is reserved for AO3-context-historical
# turns (a future enhancement). Mixing it into AO1/AO2 evidence retrieval
# would dilute the result list with material that's pedagogically wrong
# for the criterion being assessed.
NON_AO3_SOURCE_TYPES: tuple[SourceType, ...] = (
    SourceType.PRIMARY_TEXT,
    SourceType.SECONDARY_STUDY_GUIDE,
    SourceType.SECONDARY_CRITICAL,
)

# Mode flags surfaced via ``get_last_retrieval_mode`` for the orchestrator
# to forward into turn metadata. Module-level constants so callers compare
# with ``is`` rather than re-typing the literal at the call site.
MODE_RERANK: str = "rerank"
MODE_NO_RERANK: str = "no_rerank"

# Defence-in-depth AQA filename regex. Mirrors ``corpus.AQA_REFUSAL_PATTERN``
# but is duplicated here intentionally — the safety invariant is enforced at
# both ingestion *and* retrieval, so the two regexes must remain
# independent. If a future engineer changes one, the other should be
# evaluated separately rather than implicitly tracked. The 23-Apr session
# called out this defence-in-depth posture explicitly.
AQA_FILENAME_PATTERN: re.Pattern[str] = re.compile(
    r"(?i)(past[_-]?paper|mark[_-]?scheme|examiner[_-]?report)"
)

# Metadata key under which the loader's ChromaDB writer is expected to
# stash the JSON-serialised ``CorpusChunk`` payload. ChromaDB metadata
# only allows scalar values, so the structured ``citation_anchor`` cannot
# live as nested fields — the simplest portable encoding is a JSON string
# of the full chunk that we re-hydrate on read.
CHUNK_PAYLOAD_KEY: str = "chunk_json"


# Module-level state for the most recent retrieval call. The orchestrator
# reads this immediately after ``retrieve`` returns to forward the mode
# flag into turn metadata. Because retrieval happens once per turn within
# a single thread, racing readers/writers are not a concern at this layer
# (the orchestrator owns the per-turn synchronisation upstream).
_last_retrieval_mode: str = MODE_RERANK


def get_last_retrieval_mode() -> str:
    """Return the mode of the most recent ``retrieve`` call.

    Either :data:`MODE_RERANK` (the reranker was applied) or
    :data:`MODE_NO_RERANK` (the reranker import failed and base-similarity
    ordering was used instead). The orchestrator surfaces this in turn
    metadata so Coach can flag turns that ran without the reranker.
    """
    return _last_retrieval_mode


# Collection-provider injection. The provider is a zero-arg callable that
# returns the ChromaDB collection (or any duck-typed object with a
# ``query`` method matching the chromadb API). ``None`` means "no
# collection wired" — ``retrieve`` returns ``[]`` rather than raising,
# matching the AC for ``text_name`` with no primary edition available.

_collection_provider: Callable[[], Any] | None = None


def set_collection_provider(provider: Callable[[], Any]) -> None:
    """Install the ChromaDB collection provider.

    The provider is a zero-arg callable returning the collection (or
    ``None``). Real systems wire it once at orchestrator startup; tests
    install fakes per case. We keep this dependency-injected rather than
    importing ``chromadb`` here so the dev path stays free of the binary
    dependency.
    """
    global _collection_provider
    _collection_provider = provider


def reset_collection_provider() -> None:
    """Remove the installed collection provider (test teardown helper)."""
    global _collection_provider
    _collection_provider = None


def get_collection_provider() -> Callable[[], Any] | None:
    """Return the currently-installed collection provider, or ``None``.

    Inverse of :func:`set_collection_provider`. The orchestrator's boot
    smoke (TASK-RAG-002 / TASK-LCA-004 extension) calls this once at
    ``MCPAdapter.__init__`` time to verify the collection is wired
    before serving any traffic.
    """
    return _collection_provider


# Reranker-factory injection. The factory is a zero-arg callable that
# returns a reranker object exposing a ``predict(pairs)`` method matching
# ``sentence_transformers.CrossEncoder``. The default factory is ``None``
# which signals "try the real import"; tests inject a factory that either
# returns a stub or raises ``ImportError`` to exercise the
# graceful-degradation path.

_reranker_factory: Callable[[], Any] | None = None


def set_reranker_factory(factory: Callable[[], Any]) -> None:
    """Install the reranker factory.

    The factory must either return a reranker with a ``predict(pairs)``
    method, or raise ``ImportError`` to simulate the graceful-degradation
    path. We restrict the simulated failure to ``ImportError`` because the
    AC explicitly calls out the import-time fallback — broader exception
    catching would mask real bugs.
    """
    global _reranker_factory
    _reranker_factory = factory


def reset_reranker_factory() -> None:
    """Restore the default reranker factory (test teardown helper)."""
    global _reranker_factory
    _reranker_factory = None


def _load_reranker() -> Any:
    """Return a reranker instance or raise ``ImportError``.

    When a factory is installed (test path), delegate to it — the factory
    can return a stub or raise ``ImportError`` to simulate "package not
    installed". When no factory is installed (production path), attempt
    the real ``sentence_transformers`` import. The ``ImportError`` is
    re-raised by ``retrieve`` and turned into the ``mode="no_rerank"``
    fallback.
    """
    if _reranker_factory is not None:
        return _reranker_factory()
    # Real production import. Local import keeps the module-load cost low
    # for callers (decision-tree consumers) that never touch retrieval.
    from sentence_transformers import CrossEncoder  # type: ignore[import-not-found]

    return CrossEncoder(RERANKER_MODEL, device="cpu")


def _hydrate_chunk(metadata: dict[str, Any], document: str | None) -> CorpusChunk | None:
    """Reconstruct a ``CorpusChunk`` from a ChromaDB metadata record.

    Two encoding paths are supported:

    1. *Preferred:* metadata carries a JSON-serialised chunk under
       :data:`CHUNK_PAYLOAD_KEY`. We round-trip via
       ``CorpusChunk.model_validate_json`` so the discriminated
       ``citation_anchor`` union is reconstructed correctly.
    2. *Fallback:* the metadata dict already has the scalar fields
       (``text``, ``source_type``, ``source_path``, ``text_name``,
       ``chunk_index``) and ``citation_anchor`` is either absent or a
       dict that ``CorpusChunk`` can validate. Used by tests and any
       writer that serialises chunks as flat metadata.

    Records that fail validation are dropped with a structured log line
    rather than aborting the whole retrieval — a single corrupt entry
    must not block a turn.
    """
    payload = metadata.get(CHUNK_PAYLOAD_KEY)
    try:
        if isinstance(payload, str) and payload:
            return CorpusChunk.model_validate_json(payload)
        # Fallback path: build from scalar fields. ``document`` (Chroma's
        # primary text storage) wins over a ``text`` metadata key when
        # both are present, mirroring how chromadb itself separates the
        # two.
        candidate = dict(metadata)
        candidate.pop(CHUNK_PAYLOAD_KEY, None)
        if document is not None:
            candidate["text"] = document
        return CorpusChunk.model_validate(candidate)
    except Exception as exc:  # noqa: BLE001 — log + drop, not propagate
        logger.warning(
            "retrieval.hydrate_failed",
            extra={"detail": f"{type(exc).__name__}: {exc}"},
        )
        return None


def _passes_aqa_filter(chunk: CorpusChunk) -> bool:
    """Return ``True`` when the chunk's filename does NOT match the AQA regex.

    Defence-in-depth — the loader already refuses AQA filenames at
    ingestion, but a typo in the loader's regex or a new filename pattern
    must not silently leak into the retrieval result. We match against
    the basename only (``Path(...).name``) because the AQA prohibition is
    about the assessment material itself, not the directory it lives in.
    """
    name = Path(chunk.source_path).name
    if AQA_FILENAME_PATTERN.search(name):
        logger.warning(
            "retrieval.aqa_filter.dropped_chunk",
            extra={
                "source_path": chunk.source_path,
                "text_name": chunk.text_name,
            },
        )
        return False
    return True


def _query_collection(
    collection: Any,
    query: str,
    text_name: str,
    candidate_count: int,
) -> tuple[list[CorpusChunk], list[float]]:
    """Run the ChromaDB query and hydrate results into ``CorpusChunk`` objects.

    Returns ``(chunks, distances)`` aligned by index. ``distances`` are
    Chroma's cosine/L2 distance values — *lower is better* — so the
    no-rerank fallback sorts ascending.

    Failures here are returned as empty lists rather than propagated: an
    unreachable collection at retrieval time is functionally the same as
    an empty corpus from the AC's perspective ("no primary-text edition
    available" — the orchestrator records that reason).
    """
    where: dict[str, Any] = {
        "$and": [
            {"text_name": text_name},
            {
                "source_type": {
                    "$in": [s.value for s in NON_AO3_SOURCE_TYPES]
                }
            },
        ]
    }
    try:
        raw = collection.query(
            query_texts=[query],
            n_results=candidate_count,
            where=where,
        )
    except Exception as exc:  # noqa: BLE001 — log + empty, see docstring
        logger.warning(
            "retrieval.query_failed",
            extra={"detail": f"{type(exc).__name__}: {exc}"},
        )
        return [], []

    metadatas_outer = raw.get("metadatas") or []
    documents_outer = raw.get("documents") or []
    distances_outer = raw.get("distances") or []
    metadatas: Sequence[dict[str, Any]] = (
        metadatas_outer[0] if metadatas_outer else []
    )
    documents: Sequence[str | None] = (
        documents_outer[0] if documents_outer else []
    )
    distances: Sequence[float] = (
        distances_outer[0] if distances_outer else []
    )

    chunks: list[CorpusChunk] = []
    aligned_distances: list[float] = []
    for idx, metadata in enumerate(metadatas):
        document = documents[idx] if idx < len(documents) else None
        # ChromaDB defaults distances to a positive number; if the writer
        # didn't provide them (e.g. fixture corpus), use the index as a
        # stable tie-breaker so ordering is still deterministic.
        distance = (
            float(distances[idx])
            if idx < len(distances) and distances[idx] is not None
            else float(idx)
        )
        chunk = _hydrate_chunk(dict(metadata), document)
        if chunk is None:
            continue
        chunks.append(chunk)
        aligned_distances.append(distance)
    return chunks, aligned_distances


def _rerank(
    query: str,
    chunks: list[CorpusChunk],
    reranker: Any,
) -> list[CorpusChunk]:
    """Re-order ``chunks`` by reranker score (higher is better).

    The cross-encoder receives ``[query, chunk_text]`` pairs and returns a
    relevance score per pair. We sort descending and return the chunks in
    the new order; the original distance metric is discarded once the
    reranker has spoken.
    """
    if not chunks:
        return []
    pairs = [[query, chunk.text] for chunk in chunks]
    scores = reranker.predict(pairs)
    paired = list(zip(chunks, scores, strict=True))
    paired.sort(key=lambda item: item[1], reverse=True)
    return [chunk for chunk, _ in paired]


def _primary_first(
    chunks: list[CorpusChunk],
    top_k: int,
) -> list[CorpusChunk]:
    """Partition ``chunks`` so all primary appear before any secondary.

    Within each partition, original ordering is preserved (which carries
    the ranker's relevance signal). When fewer than ``top_k`` primary
    chunks are available, secondary chunks fill the remaining slots —
    matching the AC ("when fewer than K primary chunks exist, fill with
    secondary up to K").
    """
    primary = [c for c in chunks if c.source_type is SourceType.PRIMARY_TEXT]
    secondary = [
        c for c in chunks if c.source_type is not SourceType.PRIMARY_TEXT
    ]
    return (primary + secondary)[:top_k]


def retrieve(
    query: str,
    text_name: str,
    focus_aos: set[str],
    top_k: int = DEFAULT_TOP_K,
) -> list[CorpusChunk]:
    """Source-filtered retrieval with reranker degradation.

    Parameters
    ----------
    query : str
        Natural-language query the Player is grounding its turn against.
    text_name : str
        Literary work to filter by (e.g. ``"macbeth"``). Maps to the
        ``text_name`` metadata field on each ``CorpusChunk``.
    focus_aos : set[str]
        Assessment Objectives the turn targets. Currently advisory — the
        decision function (``should_retrieve``) handles AO3 routing
        upstream. Accepted here so callers can pass it through unchanged
        and so future AO-aware filters have a place to land.
    top_k : int, optional
        Maximum chunks to return. Defaults to :data:`DEFAULT_TOP_K` (6).

    Returns
    -------
    list[CorpusChunk]
        Up to ``top_k`` chunks, primary-text first, then secondary.
        Empty list when the collection is unwired, the corpus has no
        chunks for ``text_name``, or every candidate was filtered out.

    Notes
    -----
    Side effect: updates the module-level "last retrieval mode" so the
    orchestrator can read :func:`get_last_retrieval_mode` and forward
    ``mode="rerank"`` or ``mode="no_rerank"`` into turn metadata.

    Raises
    ------
    ValueError
        If ``top_k`` is non-positive or ``text_name`` is empty. We refuse
        to silently treat these as "always empty" because both usually
        indicate a configuration bug at the call site.
    """
    if not text_name:
        raise ValueError("text_name must be a non-empty string")
    if top_k <= 0:
        raise ValueError(f"top_k must be positive (got {top_k!r})")

    global _last_retrieval_mode

    if _collection_provider is None:
        # No collection wired. Treat as empty corpus per the AC.
        _last_retrieval_mode = MODE_RERANK
        return []

    collection = _collection_provider()
    if collection is None:
        _last_retrieval_mode = MODE_RERANK
        return []

    candidate_count = max(top_k, top_k * RETRIEVAL_CANDIDATE_MULTIPLIER)
    chunks, _ = _query_collection(collection, query, text_name, candidate_count)
    chunks = [c for c in chunks if _passes_aqa_filter(c)]

    if not chunks:
        _last_retrieval_mode = MODE_RERANK
        return []

    try:
        reranker = _load_reranker()
    except ImportError:
        # Graceful degradation. The caller asked for retrieval; we return
        # base-similarity ordering and surface the degradation via
        # ``get_last_retrieval_mode``. Logged at INFO rather than WARNING
        # because this is an expected operational state on CI / first
        # boot, not an error.
        logger.info(
            "retrieval.reranker_unavailable",
            extra={"model": RERANKER_MODEL, "fallback": MODE_NO_RERANK},
        )
        _last_retrieval_mode = MODE_NO_RERANK
        return _primary_first(chunks, top_k)

    try:
        ranked = _rerank(query, chunks, reranker)
    except Exception as exc:  # noqa: BLE001 — log + degrade, not propagate
        logger.warning(
            "retrieval.rerank_failed",
            extra={"detail": f"{type(exc).__name__}: {exc}"},
        )
        _last_retrieval_mode = MODE_NO_RERANK
        return _primary_first(chunks, top_k)

    _last_retrieval_mode = MODE_RERANK
    return _primary_first(ranked, top_k)


__all__ = [
    "AQA_FILENAME_PATTERN",
    "CHUNK_PAYLOAD_KEY",
    "DEFAULT_TOP_K",
    "EMBEDDER_TIMEOUT_SECONDS",
    "MODE_NO_RERANK",
    "MODE_RERANK",
    "NON_AO3_SOURCE_TYPES",
    "REASON_AO3_ONLY",
    "REASON_EMBEDDER_TIMEOUT",
    "REASON_NO_PRIMARY",
    "REASON_RETRIEVE_MIXED",
    "REASON_RETRIEVE_PRIMARY",
    "RERANKER_MODEL",
    "RETRIEVAL_CANDIDATE_MULTIPLIER",
    "RetrievalDecision",
    "clear_primary_text_index",
    "decide_retrieval",
    "embedder_available_within",
    "get_collection_provider",
    "get_last_retrieval_mode",
    "has_primary_text",
    "register_primary_text",
    "reset_collection_provider",
    "reset_embedder_probe",
    "reset_reranker_factory",
    "retrieve",
    "set_collection_provider",
    "set_embedder_probe",
    "set_reranker_factory",
    "should_retrieve",
]
