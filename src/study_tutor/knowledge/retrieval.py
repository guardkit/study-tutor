"""Dynamic retrieval-decision function (R2 + R3) — pre-Player decision point.

Encodes the empirical R2 (dynamic retrieval decision) and R3 (AO3 retrieval
bypass) recommendations from the 23-Apr OpenWebUI session.

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
"""

from __future__ import annotations

import logging
import time
from typing import Callable, NamedTuple

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


__all__ = [
    "REASON_NO_PRIMARY",
    "REASON_AO3_ONLY",
    "REASON_EMBEDDER_TIMEOUT",
    "REASON_RETRIEVE_PRIMARY",
    "REASON_RETRIEVE_MIXED",
    "EMBEDDER_TIMEOUT_SECONDS",
    "RetrievalDecision",
    "has_primary_text",
    "register_primary_text",
    "clear_primary_text_index",
    "embedder_available_within",
    "set_embedder_probe",
    "reset_embedder_probe",
    "should_retrieve",
    "decide_retrieval",
]
