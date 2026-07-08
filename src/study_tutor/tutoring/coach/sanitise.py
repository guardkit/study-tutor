"""Coach-side sanitisation + per-observation dispatcher for F1 misconception writes.

This module owns two responsibilities for **TASK-DTL-004** (FEAT-PH1-003):

1. :func:`sanitise_misconception` — a **pure** function that strips control
   characters and zero-width Unicode, escapes coarse prompt-injection markers,
   and caps the misconception text at a configurable upper bound. The function
   is idempotent (``sanitise(sanitise(x)) == sanitise(x)``) so repeated passes
   through the dispatcher pipeline (e.g. retries, defensive double-call) do
   not destructively re-mangle text.

2. :class:`CoachMisconceptionDispatcher` — the per-observation dispatch
   surface that sits inside the Coach AsyncSubAgent. For every misconception
   observation produced by an evaluator pass it:

   - Sanitises the misconception text (via :func:`sanitise_misconception`).
   - Calls ``asyncio.create_task(write_helper.write_misconception(student_id,
     sanitised_observation))`` — fire-and-forget, never awaited.
   - Logs a structured warning line if scheduling fails (extreme edge — only
     fires when the event loop is shutting down).
   - Wraps the helper coroutine so any exception inside the helper task is
     logged, not raised into the task surface (helper-failure isolation per
     AC #3 / DDR-002 §Decision).

**Why sanitisation is caller-side, not helper-side** (Finding F9 of
TASK-REV-DTL3): the shared write helper is a dispatch surface — it knows about
``asyncio.create_task``, structured logging on failure, and the F-id log
dimension. It does *not* know about misconception payloads vs session episodes
vs topic-confidence deltas. Putting content-aware sanitisation in the helper
would force it to switch on payload type, breaking the symmetry DDR-002
protects.

**Why per-observation, not per-turn** (DDR-002 §Decision): each Coach
observation flushes independently from inside the Coach's task surface. When
the Coach observes N misconceptions in a single turn, N independent
``create_task`` calls fire — never one batched call with a list. This module
hard-codes that contract: :meth:`CoachMisconceptionDispatcher.dispatch`
accepts a *single* :class:`MisconceptionObservation` and never a list.

Cross-references:
    - DDR-002 (Coach AsyncSubAgent owns misconception writes — per-observation)
    - ADR-ARCH-019 (async write-back at every flush point)
    - ASSUM-007 (shutdown grace ≤ 30s)
    - phase-1-scope.md §FEAT-PH1-003 / FEAT-PH1-001 (architectural shape)
"""
from __future__ import annotations

import asyncio
import logging
import re
import unicodedata
from typing import Any, Protocol

# Canonical MisconceptionObservation now lives in ``factory`` (TASK-DTL-001).
# Re-imported here so existing call sites (``from study_tutor.tutoring.coach
# .sanitise import MisconceptionObservation``) continue to resolve to the
# canonical model — this honours the migration plan written into the
# original sanitise module docstring ("when TASK-DTL-001 lands, the
# canonical model can be re-exported here").
from study_tutor.tutoring.coach.factory import MisconceptionObservation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

#: Maximum length (characters) of sanitised misconception text. Generous
#: upper bound — the helper layer further caps to 500 chars for the actual
#: store payload, so this acts as a defensive guard against pathological
#: learner inputs (e.g. paste-attack megastrings) before they hit the helper.
MAX_MISCONCEPTION_TEXT_LENGTH: int = 4000

#: Suffix appended to truncated text. Chosen to be visually distinct so a
#: human auditor reviewing logs can tell at a glance the entry was capped.
TRUNCATION_SUFFIX: str = "[…truncated]"


# ---------------------------------------------------------------------------
# Sanitisation primitives
# ---------------------------------------------------------------------------

# ASCII control characters except TAB (\x09), LF (\x0A), and CR (\x0D). DEL
# (\x7F) is also stripped because it is non-printable and has been used in
# smuggling tricks against extraction LLMs.
_CONTROL_CHARS_PATTERN: re.Pattern[str] = re.compile(
    r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]"
)

# Zero-width / bidi-control Unicode characters that render invisibly but can
# carry instruction semantics in tokenisers. Stripped wholesale — there is no
# legitimate reason for a learner-typed misconception to contain ZWJ, ZWNJ,
# RLO/LRO bidi overrides, or BOM marks.
_ZERO_WIDTH_PATTERN: re.Pattern[str] = re.compile(
    r"[​-‏‪-‮⁠-⁤⁪-⁯﻿]"
)

# Coarse prompt-injection markers. We **escape** rather than reject so a
# misconception that legitimately *quotes* a marker (e.g. "the student wrote
# `<|im_start|>` thinking it was an HTML tag") survives the round-trip in a
# defanged form. Unlike the helper-side defence in
# ``study_tutor.knowledge.async_write.sanitise_misconception_text`` which
# raises ``ValueError`` on these patterns, the Coach-side pass is non-fatal.
_INJECTION_TOKEN_PATTERN: re.Pattern[str] = re.compile(
    r"(?i)(<\|[^|>\\]*?\|>|\[INST\]|\[/INST\]|<\|im_start\|>|<\|im_end\|>)"
)


def _escape_injection_match(match: re.Match[str]) -> str:
    """Backslash-escape pipe and bracket characters in the matched marker.

    Idempotency guarantee: a re-escape would require the regex to match
    ``<\\|im_start\\|>`` (backslash-pipe), but the regex requires literal
    pipes (``\\|`` in regex syntax = literal pipe), so already-escaped
    markers do not match a second time. The exclusion of ``\\`` from the
    inner character class (``[^|>\\\\]``) is what makes this safe.
    """
    raw = match.group(0)
    return raw.replace("|", r"\|").replace("[", r"\[").replace("]", r"\]")


def sanitise_misconception(
    text: str,
    *,
    max_length: int = MAX_MISCONCEPTION_TEXT_LENGTH,
) -> str:
    """Sanitise free-text misconception content before dispatch.

    Order of operations (each step is idempotent on its own output):

    1. Coerce non-string input to a string for defensive boundary handling.
    2. Normalise Unicode to NFKC so visually-equivalent forms collapse and
       cannot be used to evade the marker regex.
    3. Strip ASCII control characters (preserving TAB, LF, CR).
    4. Strip zero-width / bidi-control Unicode characters.
    5. **Escape** (not reject) coarse prompt-injection markers so quoting a
       marker in a legitimate misconception still round-trips.
    6. Truncate to ``max_length`` characters with :data:`TRUNCATION_SUFFIX`
       appended (the result never exceeds ``max_length``).

    Args:
        text: Raw misconception text observed by the Coach. Non-string inputs
            are coerced via :func:`str` for defence-in-depth at the boundary.
        max_length: Maximum length (characters) of the returned string.
            Defaults to :data:`MAX_MISCONCEPTION_TEXT_LENGTH`.

    Returns:
        The sanitised text, length-capped at ``max_length`` characters.

    Raises:
        ValueError: If ``max_length`` is non-positive.
    """
    if max_length <= 0:
        raise ValueError(
            f"max_length must be positive, got {max_length}"
        )

    # 1. Boundary coercion. Belt-and-braces: callers should already pass str,
    #    but we guard here so a stray ``None`` from a buggy Coach output schema
    #    becomes the literal string "None" and is auditable, rather than
    #    blowing up the Coach's task surface mid-dispatch.
    if not isinstance(text, str):
        text = str(text)

    # 2. Unicode normalisation. NFKC folds compatibility characters (e.g.
    #    fullwidth ASCII, ligatures) into their canonical forms so injection
    #    markers cannot hide behind visually-similar Unicode.
    cleaned = unicodedata.normalize("NFKC", text)

    # 3. Strip ASCII control characters.
    cleaned = _CONTROL_CHARS_PATTERN.sub("", cleaned)

    # 4. Strip zero-width / bidi-control Unicode.
    cleaned = _ZERO_WIDTH_PATTERN.sub("", cleaned)

    # 5. Escape prompt-injection markers.
    cleaned = _INJECTION_TOKEN_PATTERN.sub(_escape_injection_match, cleaned)

    # 6. Length cap with truncation suffix.
    if len(cleaned) > max_length:
        keep = max_length - len(TRUNCATION_SUFFIX)
        if keep <= 0:
            # Pathological case: the suffix itself is longer than max_length.
            # Return the suffix truncated to fit — never exceed the cap.
            return TRUNCATION_SUFFIX[:max_length]
        cleaned = cleaned[:keep] + TRUNCATION_SUFFIX

    return cleaned


# ---------------------------------------------------------------------------
# Coach-side data contract
# ---------------------------------------------------------------------------


# NOTE: ``MisconceptionObservation`` previously had a local Pydantic
# definition here. It now lives in ``study_tutor.tutoring.coach.factory``
# (TASK-DTL-001) and is re-imported at the top of this module to keep the
# original public symbol path (``study_tutor.tutoring.coach.sanitise
# .MisconceptionObservation``) stable for any consumer that already imports
# it from this location.


class _WriteHelperLike(Protocol):
    """Structural protocol for the shared misconception write helper.

    The helper exposes ``write_misconception(student_id, observation)`` as a
    coroutine method. We use a Protocol rather than a hard import so the
    dispatcher remains testable with ``unittest.mock.AsyncMock`` without
    coupling to any concrete backend.
    """

    async def write_misconception(
        self, student_id: str, observation: Any
    ) -> None:  # pragma: no cover - protocol declaration only
        ...


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


class CoachMisconceptionDispatcher:
    """Per-observation misconception dispatcher embedded in the Coach AsyncSubAgent.

    The dispatcher owns the F1 fire-and-forget surface inside the Coach's task
    boundary. Per **DDR-002 §Decision** each call to :meth:`dispatch` schedules
    exactly one ``asyncio.create_task`` — the helper accepts one observation
    per call and *never* a list. This is a hard structural invariant, not a
    convention.

    Helper-failure isolation (AC #3): the dispatcher wraps the helper coroutine
    so any exception raised inside the in-flight write task is caught and
    logged with structured fields, never propagated up to the Coach task
    surface or the Tutor handler. This keeps the per-turn budget independent
    of helper failures.
    """

    def __init__(self, write_helper: _WriteHelperLike) -> None:
        """Construct the dispatcher around an injected helper instance.

        Args:
            write_helper: The shared misconception write helper. Injected via
                constructor — the dispatcher does **not** import the helper
                module-globally (per TASK-DTL-001 consumer_context).
        """
        self._write_helper = write_helper

    def dispatch(
        self,
        student_id: str,
        observation: MisconceptionObservation,
    ) -> asyncio.Task[None] | None:
        """Sanitise + fire-and-forget dispatch a single misconception write.

        Per DDR-002 the helper accepts ONE observation per call. Passing a
        list here is a programming error and raises immediately — making
        per-observation ownership a structural property, not a discipline.

        Args:
            student_id: The student the observation was made for.
            observation: A single :class:`MisconceptionObservation`. Lists
                are explicitly rejected.

        Returns:
            The :class:`asyncio.Task` wrapping the in-flight write, or
            ``None`` if scheduling failed (event loop shutting down).

        Raises:
            TypeError: If ``observation`` is a list/tuple/set (DDR-002
                violation: helper accepts one observation per call).
        """
        # Hard-fail on list/tuple inputs: per-observation ownership is an
        # interface property, not a caller convention. If a caller wants to
        # dispatch N observations, they must call dispatch() N times.
        if isinstance(observation, (list, tuple, set)):
            raise TypeError(
                "DDR-002 violation: dispatch() accepts ONE observation per call, "
                f"got {type(observation).__name__}. "
                "Call dispatch() once per observation instead."
            )

        # Sanitise BEFORE the helper sees the payload — Finding F9 of
        # TASK-REV-DTL3: sanitisation is caller-side. The helper is a content-
        # agnostic dispatch surface and MUST NOT see raw learner text.
        sanitised_text = sanitise_misconception(observation.misconception_text)
        sanitised_observation = observation.model_copy(
            update={"misconception_text": sanitised_text}
        )

        # Wrap the helper coroutine so any exception inside the in-flight
        # write task is logged here, not surfaced as an unhandled task
        # exception. AC #3: helper failure must not raise into the Coach
        # task surface or up to the Tutor handler.
        write_coro = self._invoke_helper_safely(
            student_id=student_id, observation=sanitised_observation
        )

        try:
            task = asyncio.create_task(write_coro)
        except RuntimeError as exc:
            # No running event loop / loop closed mid-dispatch. Close the
            # coroutine to avoid the "coroutine was never awaited"
            # ResourceWarning, then log and return None — never raise.
            write_coro.close()
            logger.warning(
                "coach misconception dispatch unschedulable",
                extra={
                    "event": "coach_misconception_dispatch_unschedulable",
                    "student_id": student_id,
                    "topic_name": sanitised_observation.topic_name,
                    "error_class": exc.__class__.__name__,
                },
            )
            return None

        return task

    async def _invoke_helper_safely(
        self,
        *,
        student_id: str,
        observation: MisconceptionObservation,
    ) -> None:
        """Call the helper coroutine inside a structured try/except.

        The shared helper is expected to log + swallow internally (per
        TASK-GSM-004 ADR-ARCH-019), but we add a defence-in-depth wrapper at
        this seam so a misbehaving helper cannot leak an exception into the
        Coach's task surface (AC #3). The log line uses an event name distinct
        from the helper's own failure event so the two cannot conflate
        — a Coach-side log is auditably separate from a helper-side log.
        """
        try:
            await self._write_helper.write_misconception(
                student_id, observation
            )
        except BaseException as exc:  # noqa: BLE001 -- AC #3: log-only, never raise
            logger.warning(
                "coach misconception write failed",
                extra={
                    "event": "coach_misconception_write_failed",
                    "student_id": student_id,
                    "topic_name": observation.topic_name,
                    "error_class": exc.__class__.__name__,
                },
            )
            return None


__all__ = [
    "MAX_MISCONCEPTION_TEXT_LENGTH",
    "TRUNCATION_SUFFIX",
    "CoachMisconceptionDispatcher",
    "MisconceptionObservation",
    "sanitise_misconception",
]
