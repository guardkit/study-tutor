"""TASK-DSP-005 — ``plan_session`` pipeline + rule-6 fallback.

This module composes the deterministic planner's rule pipeline. Each
``Rule`` is dispatched in priority order and the first non-``None``
:class:`Candidate` wins. When rules 1/3/4 all return ``None`` the
pipeline falls back to **rule 6** (random selection from the developing
band) and, if even the developing band is empty, to the
:func:`_baseline_plan` helper from :mod:`study_tutor.planner.types`.

Determinism is structural:

- ``clock`` and ``rng`` are dependency-injected at the
  :class:`PlannerContext` boundary; no rule (and not the rule-6
  fallback) reaches for ``datetime.utcnow`` or module-level
  :mod:`random` state.
- Rule-6 sorts candidate topics alphabetically by ``topic_ref`` before
  sampling so the output of a seeded :class:`random.Random` is stable
  across CPython versions.
- ``Rule6Random`` is intentionally *not* a separate class: rule 6
  participates only after the rule-list short-circuits and needs to
  read ``ctx.rng`` directly. Folding it into ``plan_session`` keeps the
  rule-list contract honest — every entry is a primary ranking rule, not
  a fallback.

The module exposes two public entry points:

- :func:`plan_session` — the production async entry point. Builds a
  :class:`PlannerContext` via :func:`_build_planner_context` and
  delegates to :func:`run_rule_pipeline`.
- :func:`run_rule_pipeline` — sync core. Tests construct a
  :class:`PlannerContext` directly and call this function so they don't
  need to mock the FEAT-PH1-001 read boundary.
"""
from __future__ import annotations

import asyncio
import logging
import os
import random
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any, Callable

from study_tutor.knowledge.episodes import SessionCompletedEpisode
from study_tutor.knowledge.store.reads import PlannerInputs, load_planner_inputs
from study_tutor.planner.protocols import (
    AOCode,
    Candidate,
    PlannerContext,
    Rule,
)
from study_tutor.planner.rules import (
    Rule1LearnerOverride,
    Rule2ActiveQuestStub,
    Rule3WeakestStaleTopic,
    Rule4UnrevisitedMisconception,
    Rule5AchievementNearUnlockStub,
)
from study_tutor.planner.types import (
    DEFAULT_DURATION_MINUTES,
    SessionPlan,
    _baseline_plan,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration (TASK-DSP-006 — inner student-model read timeout)
# ---------------------------------------------------------------------------

#: TASK-DSP-006 — env var that controls the *inner* student-model read
#: timeout (ASSUM-007, signed off 2026-04-29). Default 5.0s. Patched in
#: tests independently of the outer 2.0s MCP-handler budget so each
#: boundary can be exercised in isolation. The outer guard is the binding
#: constraint in the default configuration; this inner timeout fires
#: first only when ``PLANNER_HANDLER_BUDGET_SEC`` is enlarged.
_STUDENT_MODEL_READ_TIMEOUT_ENV: str = "STUDENT_MODEL_READ_TIMEOUT_SEC"
_STUDENT_MODEL_READ_TIMEOUT_DEFAULT: float = 5.0


def _student_model_read_timeout_sec() -> float:
    """Return the inner read timeout for ``_build_planner_context``.

    Reads :data:`_STUDENT_MODEL_READ_TIMEOUT_ENV` from the environment at
    *call* time so test patching of ``os.environ`` flows through without
    a process restart. Falls back to
    :data:`_STUDENT_MODEL_READ_TIMEOUT_DEFAULT` when the var is unset or
    unparseable.
    """
    raw = os.environ.get(_STUDENT_MODEL_READ_TIMEOUT_ENV)
    if raw is None:
        return _STUDENT_MODEL_READ_TIMEOUT_DEFAULT
    try:
        return float(raw)
    except ValueError:
        logger.warning(
            "ignoring unparseable %s=%r; using default %.1fs",
            _STUDENT_MODEL_READ_TIMEOUT_ENV,
            raw,
            _STUDENT_MODEL_READ_TIMEOUT_DEFAULT,
        )
        return _STUDENT_MODEL_READ_TIMEOUT_DEFAULT


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _default_clock() -> datetime:
    """Return current UTC time at call site (no captured reference).

    Used as the default ``clock`` for :func:`plan_session` when the
    caller does not supply one. Defined as a function rather than a
    bound ``datetime.utcnow`` reference so each call resolves the time
    fresh and so we avoid the Python 3.12+ deprecation of
    :func:`datetime.datetime.utcnow`.
    """
    return datetime.now(timezone.utc)


def _build_opening_prompt(topic_name: str) -> str:
    """Render the tutor's first-turn prompt for ``topic_name``.

    The prompt mentions the chosen topic exactly once. The wording is
    intentionally generic — *not* drawn from any prior session
    transcript — so AC-008 (`@edge-case` opening-prompt) holds:
    consecutive sessions on different topics produce different prompts,
    and the planner never reuses a prior session's prompt verbatim.
    """
    return (
        f"Today let's focus on {topic_name}. To start, share what you "
        f"already know about it and where you feel less confident."
    )


def _plan_from_candidate(
    candidate: Candidate,
    fallback_used: str | None,
    context: PlannerContext,
) -> SessionPlan:
    """Convert a winning :class:`Candidate` into a :class:`SessionPlan`.

    Looks up ``focus_aos`` for ``candidate.topic_name`` in
    ``context.ao_mapping``. When the topic is absent from the mapping
    (off-curriculum override, baseline topic with no AO links, etc.)
    ``focus_aos`` is set to ``[]`` and ``ao_mapping_found=False`` —
    AC-009 (`@edge-case @integration-boundary` AO-mapping scenario).
    """
    mapping = context.ao_mapping
    if candidate.topic_name in mapping:
        focus_aos = list(mapping[candidate.topic_name])
        ao_mapping_found = True
    else:
        focus_aos = []
        ao_mapping_found = False

    # ``fallback_used`` is widened to ``str | None`` in the function
    # signature for ergonomics; the SessionPlan field is a Literal so
    # we let Pydantic validate the narrower set at construction time.
    return SessionPlan(
        topic_name=candidate.topic_name,
        focus_aos=focus_aos,  # type: ignore[arg-type]
        opening_prompt=_build_opening_prompt(candidate.topic_name),
        suggested_duration_minutes=DEFAULT_DURATION_MINUTES,
        related_misconceptions=list(candidate.related_misconceptions),
        rationale=candidate.rationale_fragment,
        fallback_used=fallback_used,  # type: ignore[arg-type]
        rule_selected=candidate.rule_source,
        ao_mapping_found=ao_mapping_found,
        # TASK-DSP-006: carry the read-boundary signal through to the
        # plan output rather than hard-coding True. A topic_override that
        # fires for an unseeded learner still surfaces
        # ``learner_state_available=False`` so observability accurately
        # reflects what the planner could see.
        learner_state_available=context.learner_state_available,
    )


# ---------------------------------------------------------------------------
# Sync core: rule dispatch + fallbacks
# ---------------------------------------------------------------------------


def run_rule_pipeline(
    context: PlannerContext,
    *,
    session_completions: list[SessionCompletedEpisode] | None = None,
) -> SessionPlan:
    """Dispatch the rule pipeline against ``context`` and return a plan.

    Steps:

    1. Build the rule list in priority order:
       Rule 1 (override) → Rule 2 stub → Rule 3 (weakest stale) →
       Rule 4 (unrevisited misconception) → Rule 5 stub.
    2. Walk the list with a walrus-expression generator so each rule is
       evaluated **once** even though the filter test references the
       result. This avoids the "double-evaluation" trap of
       ``next(filter(None, (r(ctx) for r in rules)), None)`` which
       calls each rule twice in a naive read.
    3. If a primary rule returns a :class:`Candidate`, build the plan
       with ``fallback_used=None``.
    4. Otherwise, fall back to **rule 6**: pick a developing-band topic
       at random via ``context.rng``. Sort candidates by ``topic_ref``
       before sampling so :class:`random.Random` output is stable across
       CPython versions (AC-007).
    5. If the developing band is empty too, return a baseline plan
       (AC-005, the TASK-REV-DA72 §5 Gap-1 case).

    ``session_completions`` is forwarded to Rule 4 — production wiring
    will source these from the FEAT-PH1-001 query helpers via
    :func:`_build_planner_context`. Tests pass them in directly.
    """
    completions = session_completions or []

    rules: list[Rule] = [
        Rule1LearnerOverride(),
        Rule2ActiveQuestStub(),
        Rule3WeakestStaleTopic(),
        Rule4UnrevisitedMisconception(
            clock=context.clock,
            session_completions=completions,
        ),
        Rule5AchievementNearUnlockStub(),
    ]

    candidate = next(
        (c for r in rules if (c := r(context)) is not None),
        None,
    )

    if candidate is not None:
        return _plan_from_candidate(
            candidate, fallback_used=None, context=context
        )

    # Rule 6: random selection from developing band, sorted alphabetically
    # before sampling so a seeded ``random.Random`` is reproducible across
    # CPython versions (AC-006, AC-007).
    developing = context.topics_in_band("developing")
    if developing:
        developing_sorted = sorted(developing, key=lambda tc: tc.topic_ref)
        chosen = context.rng.choice(developing_sorted)
        rule6_candidate = Candidate(
            topic_name=chosen.topic_ref,
            rule_source="rule-6",
            confidence_percentage=float(chosen.percentage),
            related_misconceptions=[],
            rationale_fragment=(
                "rule-6 fallback: random selection from developing band — "
                f"chose '{chosen.topic_ref}' at {chosen.percentage}% "
                "confidence"
            ),
        )
        return _plan_from_candidate(
            rule6_candidate, fallback_used="rule-6", context=context
        )

    # Final fallback: developing band is empty too. Per TASK-REV-DA72 §5
    # Gap 1 the planner must still return a plan rather than raise — the
    # baseline helper handles the seeded-but-empty-state case.
    #
    # TASK-DSP-006: defer to ``context.learner_state_available`` so a
    # planner-context built off a failed/empty student-model read routes
    # to ``_baseline_plan(False)`` (no-state branch — does not require the
    # YAML), while a populated context with no rule fit still routes to
    # ``_baseline_plan(True)`` (seeded-empty branch — sources from YAML).
    return _baseline_plan(
        learner_state_available=context.learner_state_available,
    )


# ---------------------------------------------------------------------------
# Async wrapper: build context + dispatch
# ---------------------------------------------------------------------------


async def _build_planner_context(
    student_id: str,
    *,
    clock: Callable[[], datetime],
    rng: random.Random,
    topic_override: str | None,
    client: Any | None = None,
    ao_mapping: Mapping[str, list[AOCode]] | None = None,
) -> PlannerContext:
    """Read student state and build a :class:`PlannerContext`.

    TASK-SMP2-05: This is the read boundary for the planner. It calls
    :func:`load_planner_inputs` to fetch the learner's per-topic
    confidence and recent misconceptions from the store-backed read layer,
    which returns domain entities directly (no snapshot projection needed).

    TASK-DSP-006: this builder enforces the **inner** student-model read
    timeout itself via :func:`asyncio.wait_for` — driven by the
    :data:`_STUDENT_MODEL_READ_TIMEOUT_ENV` env var (default 5.0s,
    ASSUM-007). The MCP adapter additionally wraps the entire
    :func:`plan_session` call in a 2.0s outer guard
    (``PLANNER_HANDLER_BUDGET_SEC``, ASSUM-006). The outer guard is the
    binding constraint by design; this inner one only fires first when
    tests enlarge the outer budget.

    On read failure (timeout) this function still returns a valid
    :class:`PlannerContext` so a learner-supplied ``topic_override``
    continues to flow through to Rule 1, but the context is tagged
    ``learner_state_available=False`` so the pipeline (and any plan it
    emits) carries that signal through to the response. When no override
    is in play and no rule produces a candidate, :func:`run_rule_pipeline`
    then routes to :func:`_baseline_plan(False)
    <study_tutor.planner.types._baseline_plan>`.

    Note: The ``client`` parameter is retained for backwards compatibility
    but is no longer used — the store-backed read does not require it.
    """
    timeout = _student_model_read_timeout_sec()

    try:
        inputs = await asyncio.wait_for(
            load_planner_inputs(student_id),
            timeout=timeout,
        )
    except asyncio.TimeoutError:
        logger.warning(
            "student-model read exceeded planner inner timeout",
            extra={
                "event": "planner_student_model_read_timeout",
                "student_id": student_id,
                "timeout_sec": timeout,
            },
        )
        # On timeout, degrade to unavailable state
        inputs = PlannerInputs([], [], learner_state_available=False)

    return PlannerContext.create(
        student_id=student_id,
        topic_confidences=inputs.topic_confidences,
        misconceptions=inputs.misconceptions,
        ao_mapping=ao_mapping or {},
        topic_override=topic_override,
        clock=clock,
        rng=rng,
        learner_state_available=inputs.learner_state_available,
    )


async def plan_session(
    student_id: str,
    topic_override: str | None = None,
    *,
    clock: Callable[[], datetime] | None = None,
    rng: random.Random | None = None,
    client: Any | None = None,
    ao_mapping: Mapping[str, list[AOCode]] | None = None,
    session_completions: list[SessionCompletedEpisode] | None = None,
) -> SessionPlan:
    """Plan a session for ``student_id`` via the deterministic pipeline.

    Args:
        student_id: Stable learner slug (e.g. ``"lilymay"``).
        topic_override: Optional learner-supplied topic; short-circuits
            the rule list via Rule 1 when present.
        clock: Zero-arg callable returning the current UTC ``datetime``.
            Defaults to :func:`_default_clock` so production callers get
            a fresh timestamp per call without a captured reference.
        rng: Seeded :class:`random.Random` for the rule-6 fallback.
            Production callers may pass an unseeded ``random.Random()``;
            tests pass a seeded one for reproducibility.
        client: A :class:`GraphitiClient` wrapper or duck-typed inner
            client. Forwarded to :func:`get_student_state`. ``None`` is
            allowed and triggers the baseline-degraded branch.
        ao_mapping: Optional ``topic_name → [AO codes]`` lookup used to
            populate :attr:`SessionPlan.focus_aos`. Defaults to ``{}``.
        session_completions: Recent completion episodes used by Rule 4.
            Production callers will eventually wire this from the
            FEAT-PH1-001 query helpers; for now defaults to ``[]``.

    Returns:
        A :class:`SessionPlan` selected by rules 1/3/4, the rule-6
        fallback, or the baseline helper (in priority order).
    """
    if rng is None:
        rng = random.Random()
    if clock is None:
        clock = _default_clock

    context = await _build_planner_context(
        student_id,
        clock=clock,
        rng=rng,
        topic_override=topic_override,
        client=client,
        ao_mapping=ao_mapping,
    )

    return run_rule_pipeline(context, session_completions=session_completions)


__all__ = [
    "plan_session",
    "run_rule_pipeline",
]
