"""Deterministic Session Planner (DSP) — Phase 1 / FEAT-PH1-002.

The planner subpackage owns the immutable :class:`SessionPlan` contract
returned by ``tutor_start_session``, the rule pipeline that selects a
topic for a learner, and the structural :class:`Rule` protocol every
rule conforms to. TASK-DSP-001 shipped the output contract; TASK-DSP-002
adds the rule protocol, ``PlannerContext``, and ``Candidate`` types.
"""
from __future__ import annotations

from study_tutor.planner.pipeline import plan_session, run_rule_pipeline
from study_tutor.planner.protocols import (
    AOCode,
    Candidate,
    PlannerBand,
    PlannerContext,
    Rule,
    RuleSource,
)
from study_tutor.planner.types import (
    AO_LITERALS,
    DEFAULT_DURATION_MINUTES,
    MAX_DURATION_MINUTES,
    MIN_DURATION_MINUTES,
    AssessmentObjectiveCode,
    FallbackKind,
    RuleSelected,
    SessionPlan,
    _baseline_plan,
    load_curriculum_defaults,
)

__all__ = [
    "AO_LITERALS",
    "AOCode",
    "AssessmentObjectiveCode",
    "Candidate",
    "DEFAULT_DURATION_MINUTES",
    "FallbackKind",
    "MAX_DURATION_MINUTES",
    "MIN_DURATION_MINUTES",
    "PlannerBand",
    "PlannerContext",
    "Rule",
    "RuleSelected",
    "RuleSource",
    "SessionPlan",
    "_baseline_plan",
    "load_curriculum_defaults",
    "plan_session",
    "run_rule_pipeline",
]
