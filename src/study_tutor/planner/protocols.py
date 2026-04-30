"""Rule protocol, ``PlannerContext``, and ``Candidate`` types.

FEAT-PH1-002 / TASK-DSP-002 — Wave-1 foundation. Every ranking rule
(rule-1, rule-3, rule-4, rule-6 fallback) and the dispatch pipeline
import these symbols so the rule interface is locked in before any rule
implementation lands.

Three public surfaces:

* :class:`Rule` — a :class:`typing.Protocol` declaring the structural
  contract every rule conforms to.
* :class:`PlannerContext` — a frozen dataclass bundling all per-call
  inputs the rules read, plus an injected ``clock`` and ``rng`` so
  determinism is structural rather than incidental.
* :class:`Candidate` — an immutable plan fragment a rule returns when it
  has selected a topic (or ``None`` when it has nothing to offer).

Design notes:

- ``PlannerBand`` deliberately drops ``"mastered"`` from the
  :class:`ConfidenceBand` set: the rules never need to surface mastered
  topics, so the band parameter is narrowed.
- ``PlannerContext.create`` is the production-side factory; it
  normalises an empty-string override to ``None`` so rules treat
  "missing" and "blank" identically (acceptance criterion AC-006).
- ``clock`` and ``rng`` default factories live inside ``create`` rather
  than at module scope so we never freeze a single ``datetime.utcnow``
  reference at import time.
"""
from __future__ import annotations

import random
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Literal, Protocol, runtime_checkable

from study_tutor.knowledge.student_model import (
    Misconception,
    TopicConfidence,
)
from study_tutor.planner.types import AssessmentObjectiveCode

# ---------------------------------------------------------------------------
# Type aliases
# ---------------------------------------------------------------------------

#: Planner-local alias for an Assessment Objective code (AO1..AO6).
#: Re-exported so rule modules can import a single name from one place.
AOCode = AssessmentObjectiveCode

#: Bands the planner rules may request via ``topics_in_band``. ``mastered``
#: is intentionally excluded — rules surface gaps, not mastery.
PlannerBand = Literal["struggling", "developing", "secure"]

#: Frozen runtime view of :data:`PlannerBand` for input validation.
_VALID_BANDS: frozenset[str] = frozenset({"struggling", "developing", "secure"})

#: Discriminator on :class:`Candidate` indicating which rule produced it.
RuleSource = Literal["rule-1", "rule-3", "rule-4", "rule-6"]


# ---------------------------------------------------------------------------
# Default clock / rng factories
# ---------------------------------------------------------------------------


def _default_clock() -> datetime:
    """Return the current UTC ``datetime`` at call time.

    Used as the default ``clock`` factory inside
    :meth:`PlannerContext.create`. Defined as a function (not a captured
    ``datetime.utcnow`` reference) so each call resolves the time fresh
    and so we avoid the Python 3.12+ deprecation warning attached to
    :func:`datetime.datetime.utcnow`.
    """
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Candidate
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Candidate:
    """An immutable candidate plan fragment produced by a rule.

    The pipeline gathers ``Candidate`` objects from rules in priority
    order and converts the winning one into a :class:`SessionPlan`.
    Frozen so a candidate pinned by the pipeline can never be quietly
    rewritten by a downstream code path.

    Attributes:
        topic_name: Topic the rule proposes for this session.
        rule_source: Which rule produced this candidate.
        confidence_percentage: The learner's current confidence on the
            chosen topic, or ``None`` for off-curriculum overrides where
            no confidence record exists.
        related_misconceptions: Misconception summaries the tutor should
            watch for; populated by rule-4 and otherwise empty.
        rationale_fragment: Short, human-readable phrase explaining why
            this rule selected this candidate. Becomes part of
            ``SessionPlan.rationale``.
    """

    topic_name: str
    rule_source: RuleSource
    confidence_percentage: float | None
    related_misconceptions: list[str]
    rationale_fragment: str


# ---------------------------------------------------------------------------
# PlannerContext
# ---------------------------------------------------------------------------


@dataclass
class PlannerContext:
    """Bundle of inputs every rule receives.

    ``clock`` and ``rng`` are dependency-injected so determinism is a
    property of the type system, not a convention: no rule can reach for
    ``datetime.utcnow()`` or unseeded randomness directly. Tests inject a
    frozen clock and a seeded :class:`random.Random`; production callers
    use :meth:`create` to get fresh defaults.

    Attributes:
        student_id: Identifier of the learner this plan is for.
        topic_confidences: Per-topic confidence records read from the
            student-model service (FEAT-PH1-001).
        misconceptions: Documented misconceptions for the learner.
        ao_mapping: ``topic_name`` → list of focus AOs. Used by the rule
            pipeline to populate :attr:`SessionPlan.focus_aos`.
        topic_override: Caller-supplied topic name overriding rule
            selection, or ``None`` when no override applies. Empty
            strings are normalised to ``None`` by :meth:`create`.
        clock: Zero-arg callable returning the current ``datetime``.
        rng: Seeded :class:`random.Random` instance for tie-breaking.
    """

    student_id: str
    topic_confidences: list[TopicConfidence]
    misconceptions: list[Misconception]
    ao_mapping: Mapping[str, list[AOCode]]
    topic_override: str | None
    clock: Callable[[], datetime]
    rng: random.Random
    #: TASK-DSP-006 — flag carried alongside the rule inputs so the
    #: pipeline can choose between ``_baseline_plan(True)`` (seeded
    #: learner with no usable rule fit) and ``_baseline_plan(False)``
    #: (read failed or learner unseeded). Defaults to True so existing
    #: callers that never set the flag preserve the prior behaviour.
    learner_state_available: bool = True

    @classmethod
    def create(
        cls,
        *,
        student_id: str,
        topic_confidences: list[TopicConfidence],
        misconceptions: list[Misconception],
        ao_mapping: Mapping[str, list[AOCode]],
        topic_override: str | None = None,
        clock: Callable[[], datetime] | None = None,
        rng: random.Random | None = None,
        learner_state_available: bool = True,
    ) -> PlannerContext:
        """Construct a ``PlannerContext`` with sensible production defaults.

        - ``topic_override`` is normalised: ``None`` and ``""`` both
          collapse to ``None`` so rules can do a single ``is None`` check.
        - ``clock`` defaults to a function returning the current UTC time
          at each call (no captured reference at module scope).
        - ``rng`` defaults to a fresh, unseeded :class:`random.Random`.
        """
        normalised_override: str | None
        if topic_override is None or topic_override == "":
            normalised_override = None
        else:
            normalised_override = topic_override

        resolved_clock: Callable[[], datetime]
        if clock is None:
            resolved_clock = _default_clock
        else:
            resolved_clock = clock

        resolved_rng: random.Random
        if rng is None:
            resolved_rng = random.Random()
        else:
            resolved_rng = rng

        return cls(
            student_id=student_id,
            topic_confidences=topic_confidences,
            misconceptions=misconceptions,
            ao_mapping=ao_mapping,
            topic_override=normalised_override,
            clock=resolved_clock,
            rng=resolved_rng,
            learner_state_available=learner_state_available,
        )

    def topics_in_band(self, band: PlannerBand) -> list[TopicConfidence]:
        """Return all :class:`TopicConfidence` entries in the supplied band.

        This is the abstraction that lets rules avoid hard-coding band
        thresholds — band classification lives on
        :class:`TopicConfidence` and rules ask for a band by name.

        Args:
            band: One of ``"struggling"``, ``"developing"``, or
                ``"secure"``.

        Returns:
            A list of matching :class:`TopicConfidence` entries (possibly
            empty), preserving the order of :attr:`topic_confidences`.

        Raises:
            ValueError: If ``band`` is not one of the accepted values
                (covers the ``"mastered"`` case and any typo).
        """
        if band not in _VALID_BANDS:
            raise ValueError(
                f"unknown band {band!r}; expected one of "
                f"{sorted(_VALID_BANDS)!r}",
            )
        return [tc for tc in self.topic_confidences if tc.band == band]


# ---------------------------------------------------------------------------
# Rule protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class Rule(Protocol):
    """Structural contract every ranking rule conforms to.

    Any callable accepting a :class:`PlannerContext` and returning either
    a :class:`Candidate` or ``None`` satisfies ``Rule`` — no inheritance
    required. Marked :func:`runtime_checkable` so the dispatch pipeline
    and tests can verify with ``isinstance``.
    """

    def __call__(self, ctx: PlannerContext) -> Candidate | None:
        ...


__all__ = [
    "AOCode",
    "Candidate",
    "PlannerBand",
    "PlannerContext",
    "Rule",
    "RuleSource",
]
