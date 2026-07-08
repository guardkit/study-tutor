"""Ranking-rule implementations for the deterministic session planner.

FEAT-PH1-002 — Wave-2 ranking rules. Each class conforms structurally
to :class:`study_tutor.planner.protocols.Rule`; the dispatch pipeline
(TASK-DSP-005) composes them in priority order and converts the first
non-``None`` :class:`Candidate` into a :class:`SessionPlan`.

Phase-1 rules shipped here:

- **Rule 1 (TASK-DSP-003)** — learner override (opaque short-circuit).
- **Rule 3 (TASK-DSP-003)** — weakest stale topic with 48h cooldown.
- **Rule 4 (TASK-DSP-004)** — unrevisited-misconception preference per
  ASSUM-008 (signed off 2026-04-29).

Phase-2 stubs shipped here (TASK-DSP-004, contract-faithful, return
``None`` unconditionally with a ``# TODO(phase-2)`` marker):

- :class:`Rule2ActiveQuestStub`
- :class:`Rule5AchievementNearUnlockStub`

Design notes:

- **Rule 1 is opaque.** The override string is treated as a single
  literal — instruction-like content, off-curriculum topic names, and
  prompt-injection-style payloads must all pass through unchanged. The
  rule never consults the AO mapping (TASK-DSP-005 sets
  ``ao_mapping_found`` based on the lookup), and it never mutates any
  field on the supplied :class:`PlannerContext`. This is the
  ``@security @rule-1`` invariant in the task scenarios.
- **Rule 3 is pure.** Given the same :class:`PlannerContext`, the rule
  returns the same :class:`Candidate`. The cooldown comparison is
  ``clock() - last_revised_at >= timedelta(hours=48)`` — boundary
  inclusive at exactly 48h per ASSUM-001 (signed off). Tie-break order
  is ``(percentage ASC, last_revised_at ASC, topic_ref ASC)`` per
  ASSUM-004 (signed off): weakest first, then oldest-last-studied, then
  stable alphabetical.
- **Rule 4 reads misconception ``text`` as opaque data
  (``@security @rule-4``).** Only ``topic_ref`` and ``observed_at``
  participate in ranking; an adversarial misconception body cannot
  alter the selection.
- The :class:`PlannerContext` already exposes a ``clock`` callable so
  rules never reach for :func:`datetime.utcnow` directly. Determinism
  is structural, not incidental.
"""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable

from study_tutor.knowledge.student_model import Misconception, TopicConfidence
from study_tutor.planner.protocols import (
    Candidate,
    PlannerContext,
    SessionCompletion,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Cooldown window separating "still revising" from "stale and overdue".
#: Inclusive lower bound — a topic last revised exactly 48h ago is eligible.
COOLDOWN_HOURS: int = 48

#: Pre-computed timedelta form of the cooldown for boundary comparisons.
_COOLDOWN_DELTA: timedelta = timedelta(hours=COOLDOWN_HOURS)


# ---------------------------------------------------------------------------
# Rule 1 — learner override
# ---------------------------------------------------------------------------


class Rule1LearnerOverride:
    """Short-circuit ranking when the caller supplied a ``topic_override``.

    The override string is treated as an opaque label: the rule does no
    sanitisation, no curriculum lookup, and no learner-state mutation.
    This is the only path by which an off-curriculum or attacker-shaped
    string can reach the :class:`SessionPlan`, so the contract is
    deliberately narrow — anything that smells like processing the
    override would violate ``@security @rule-1``.

    Returns ``None`` when no override is present (``None`` or empty
    string). The :meth:`PlannerContext.create` factory already normalises
    ``""`` to ``None``, but the rule still handles the empty-string case
    defensively so a directly-constructed :class:`PlannerContext` can't
    sneak past it.
    """

    def __call__(self, ctx: PlannerContext) -> Candidate | None:
        override = ctx.topic_override
        if override is None or override == "":
            return None

        rationale_fragment = (
            f"rule-1: learner override — using '{override}' as the "
            f"requested topic"
        )
        return Candidate(
            topic_name=override,
            rule_source="rule-1",
            confidence_percentage=None,
            related_misconceptions=[],
            rationale_fragment=rationale_fragment,
        )


# ---------------------------------------------------------------------------
# Rule 3 — weakest stale topic
# ---------------------------------------------------------------------------


class Rule3WeakestStaleTopic:
    """Pick the lowest-confidence topic that is outside the 48h cooldown.

    A topic is *stale* when ``clock() - last_revised_at >= 48h`` — the
    boundary is inclusive at exactly 48 hours per ASSUM-001 (signed off).
    Among stale topics the rule ranks by:

    1. ``percentage`` ascending (weakest first)
    2. ``last_revised_at`` ascending (oldest revision first)
    3. ``topic_ref`` ascending (stable alphabetical fallback)

    The triple-key sort guarantees that two runs with identical inputs
    always produce the same candidate — the determinism property the
    ``@determinism`` scenarios depend on. Returns ``None`` if no topic
    is eligible (every topic is still inside its cooldown, or the
    learner has no topic-confidence entries at all).
    """

    def __call__(self, ctx: PlannerContext) -> Candidate | None:
        eligible = self._select_eligible_topics(ctx)
        if not eligible:
            return None

        eligible.sort(
            key=lambda tc: (tc.percentage, tc.last_revised_at, tc.topic_ref),
        )
        winner = eligible[0]

        rationale_fragment = self._build_rationale(winner)
        return Candidate(
            topic_name=winner.topic_ref,
            rule_source="rule-3",
            confidence_percentage=float(winner.percentage),
            related_misconceptions=[],
            rationale_fragment=rationale_fragment,
        )

    def _select_eligible_topics(
        self, ctx: PlannerContext
    ) -> list[TopicConfidence]:
        """Return the subset of topics whose cooldown has elapsed.

        Reads ``clock`` once per call so every comparison is against a
        single ``now`` — otherwise a slow loop could split a topic across
        the boundary.
        """
        now = ctx.clock()
        return [
            tc
            for tc in ctx.topic_confidences
            if (now - tc.last_revised_at) >= _COOLDOWN_DELTA
        ]

    @staticmethod
    def _build_rationale(winner: TopicConfidence) -> str:
        """Render the per-rule rationale fragment for ``winner``.

        Includes topic name and confidence percentage so the
        rationale-observability scenarios in TASK-DSP-005/006 can assert
        the chosen metric is surfaced. The phrase "outside 48h cooldown"
        is stable across calls — no time-relative wording — so tests
        comparing rationale strings stay deterministic.
        """
        return (
            f"rule-3: weakest topic '{winner.topic_ref}' at "
            f"{winner.percentage}% confidence (outside 48h cooldown)"
        )


# ---------------------------------------------------------------------------
# Rule 4 internal helpers
# ---------------------------------------------------------------------------


def _to_utc_aware(value: datetime) -> datetime:
    """Normalise ``value`` to a UTC-aware ``datetime``.

    Rule 4 compares episode-end timestamps with misconception observation
    timestamps. Both should be UTC by contract (FEAT-PH1-001 stores UTC
    everywhere) but Pydantic does not enforce timezone-awareness on the
    underlying ``datetime`` field, so we coerce defensively. Naive values
    are interpreted as UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _build_misconception_id(misconception: Misconception) -> str:
    """Return a stable, content-free identifier for a :class:`Misconception`.

    The student-model schema does not currently mint an explicit
    ``misconception_id``; the natural composite key is
    ``(topic_ref, observed_at)``. This function produces a deterministic
    string of that pair so :attr:`Candidate.related_misconceptions`
    surfaces *which* misconceptions justified the selection without
    leaking the (potentially adversarial) free-text body.
    """
    observed_at = _to_utc_aware(misconception.observed_at)
    return f"{misconception.topic_ref}@{observed_at.isoformat()}"


def _is_misconception_revisited(
    misconception: Misconception,
    sessions: Iterable[SessionCompletion],
) -> bool:
    """Return True iff the misconception's topic was revisited per ASSUM-008.

    "Revisited" means: at least one ``SessionCompletion`` carries
    ``misconception.topic_ref`` in its ``topics_covered`` AND the session
    ended strictly after ``misconception.observed_at``. Sessions that
    ended at or before the misconception was observed do NOT count
    (boundary is strict-greater per ASSUM-008).

    The session-end timestamp is read from
    :attr:`SessionCompletion.ended_at`.
    """
    observed_at = _to_utc_aware(misconception.observed_at)
    target_topic = misconception.topic_ref
    for session in sessions:
        if target_topic not in session.topics_covered:
            continue
        session_end = _to_utc_aware(session.ended_at)
        if session_end > observed_at:
            return True
    return False


# ---------------------------------------------------------------------------
# Rule 4 — unrevisited misconception
# ---------------------------------------------------------------------------


@dataclass
class Rule4UnrevisitedMisconception:
    """Prefer topics that carry an unrevisited misconception (ASSUM-008).

    A misconception ``M`` is *unrevisited* iff its ``topic_ref`` does
    NOT appear in :attr:`SessionCompletion.topics_covered` of any
    session that ended strictly after ``M.observed_at`` (ASSUM-008,
    signed off 2026-04-29).

    Constructor parameters:
        clock: Zero-arg callable returning a UTC ``datetime``. Reserved
            for symmetry with Rule 3 and for future rationale-fragment
            age annotations; the unrevisited check itself is
            clock-independent.
        session_completions: Recent :class:`SessionCompletion` records
            for the current student. The pipeline supplies these via the
            store read boundary; in unit tests they are passed in
            directly. Defaults to an empty list, which makes every
            misconception trivially "unrevisited".

    Selection algorithm:
        1. Build the set of unrevisited misconceptions per ASSUM-008.
        2. Group them by ``topic_ref``.
        3. Filter ``ctx.topic_confidences`` to topics that have at least
           one unrevisited misconception linked to them.
        4. Tie-break exactly like Rule 3:
           ``(percentage ASC, last_revised_at ASC, topic_ref ASC)``.
        5. Return a :class:`Candidate` populating
           ``related_misconceptions`` with the deterministic IDs of the
           unrevisited misconceptions for that topic (sorted for
           reproducibility).

    Returns ``None`` when no topic has any unrevisited misconception or
    when ``ctx.topic_confidences`` is empty.

    Performance: ``O(misconceptions × episodes + topics)``. With Phase-1
    single-student volumes this is well under 1ms per call.
    """

    clock: Callable[[], datetime]
    session_completions: list[SessionCompletion] = field(
        default_factory=list,
    )

    def __call__(self, ctx: PlannerContext) -> Candidate | None:
        if not ctx.topic_confidences or not ctx.misconceptions:
            return None

        # Group unrevisited misconceptions by topic_ref so the per-topic
        # check below is O(1).
        unrevisited_by_topic: dict[str, list[Misconception]] = {}
        for misconception in ctx.misconceptions:
            if _is_misconception_revisited(
                misconception, self.session_completions
            ):
                continue
            unrevisited_by_topic.setdefault(
                misconception.topic_ref, []
            ).append(misconception)

        if not unrevisited_by_topic:
            return None

        # Filter to topics that have at least one unrevisited
        # misconception. Preserve only TopicConfidence rows (we need
        # percentage / last_revised for the tie-break) — a misconception
        # for a topic without any TopicConfidence record cannot rank.
        candidates: list[tuple[TopicConfidence, list[Misconception]]] = [
            (tc, unrevisited_by_topic[tc.topic_ref])
            for tc in ctx.topic_confidences
            if tc.topic_ref in unrevisited_by_topic
        ]
        if not candidates:
            return None

        # Tie-break: same as Rule 3 — lowest confidence, oldest last
        # revision, then stable alphabetical. ``last_revised_at`` is
        # normalised to UTC-aware for comparison safety.
        candidates.sort(
            key=lambda pair: (
                pair[0].percentage,
                _to_utc_aware(pair[0].last_revised_at),
                pair[0].topic_ref,
            ),
        )
        winner_tc, winner_misconceptions = candidates[0]

        # ``related_misconceptions`` carries the IDs that JUSTIFY the
        # selection. Sorted for reproducibility — two equal runs must
        # produce byte-identical output.
        related_ids = sorted(
            _build_misconception_id(m) for m in winner_misconceptions
        )

        plural = "s" if len(winner_misconceptions) != 1 else ""
        rationale = (
            f"rule-4: topic '{winner_tc.topic_ref}' carries "
            f"{len(winner_misconceptions)} unrevisited misconception{plural} "
            f"at {winner_tc.percentage}% confidence"
        )

        return Candidate(
            topic_name=winner_tc.topic_ref,
            rule_source="rule-4",
            confidence_percentage=float(winner_tc.percentage),
            related_misconceptions=related_ids,
            rationale_fragment=rationale,
        )


# ---------------------------------------------------------------------------
# Rule 2 — Phase-2 stub (active quest)
# ---------------------------------------------------------------------------


class Rule2ActiveQuestStub:
    """Phase-2 stub for the active-quest selection rule.

    The full Phase-2 rule will surface a topic the learner is currently
    questing on (gamification layer). For Phase 1 this class is
    intentionally inert: it conforms to the :class:`Rule` protocol so
    the pipeline can wire it in unconditionally, and it returns ``None``
    for every input so the priority order falls through.

    The single phase-2 deferral marker on the line above ``return None``
    is asserted by ``test_rules.py`` via :func:`inspect.getsource`. That
    test guards against the stub silently shipping with logic before
    Phase-2 review (``@phase-2-stub``).
    """

    def __call__(self, ctx: PlannerContext) -> Candidate | None:
        # TODO(phase-2)
        return None


# ---------------------------------------------------------------------------
# Rule 5 — Phase-2 stub (achievement near unlock)
# ---------------------------------------------------------------------------


class Rule5AchievementNearUnlockStub:
    """Phase-2 stub for the achievement-near-unlock rule.

    The full Phase-2 rule will prefer topics adjacent to an unlockable
    achievement (gamification layer). For Phase 1 this stub returns
    ``None`` for every context so the pipeline falls through.

    The single phase-2 deferral marker on the line above ``return None``
    is asserted by ``test_rules.py``; see :class:`Rule2ActiveQuestStub`
    for the full rationale.
    """

    def __call__(self, ctx: PlannerContext) -> Candidate | None:
        # TODO(phase-2)
        return None


__all__ = [
    "COOLDOWN_HOURS",
    "Rule1LearnerOverride",
    "Rule2ActiveQuestStub",
    "Rule3WeakestStaleTopic",
    "Rule4UnrevisitedMisconception",
    "Rule5AchievementNearUnlockStub",
]
