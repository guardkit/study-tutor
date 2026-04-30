"""Immutable :class:`SessionPlan` contract and baseline-degraded helper.

FEAT-PH1-002 / TASK-DSP-001 — Wave-1 foundation. Every other DSP task
(rules 1/3/4, the rule-6 fallback, the pipeline, the MCP adapter) imports
``SessionPlan`` from this module so the rule pipeline can be assembled
without circular dependencies on any rule-implementation module.

Two public surfaces:

* :class:`SessionPlan` — the frozen Pydantic v2 model the planner returns.
* :func:`_baseline_plan` — the degraded-path helper used when the
  student-model read fails (``learner_state_available=False``) or the
  learner has been seeded but has no topic-confidence entries
  (``learner_state_available=True``). The leading underscore matches the
  task spec; it signals "called by the planner pipeline, not part of the
  public MCP contract".

The helper deliberately reads ``curriculum_defaults.yaml`` rather than
hard-coding topic strings: the no-state-available case still returns a
valid plan even if the YAML is missing (so the MCP adapter never raises),
but the seeded-but-empty-state case requires the curriculum file so the
proposed topic is sourced from data, not literals (see acceptance
criterion AC-004 on TASK-DSP-001).
"""
from __future__ import annotations

from importlib import resources
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_validator

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Default suggested session duration (ASSUM-002, signed off).
DEFAULT_DURATION_MINUTES: int = 20

#: Inclusive lower bound on suggested session duration (ASSUM-002).
MIN_DURATION_MINUTES: int = 10

#: Inclusive upper bound on suggested session duration (ASSUM-002).
MAX_DURATION_MINUTES: int = 45

#: All AQA 8702 Assessment Objective codes accepted in ``focus_aos``.
AO_LITERALS: tuple[str, ...] = ("AO1", "AO2", "AO3", "AO4", "AO5", "AO6")

#: Type alias for the AO enum used on :attr:`SessionPlan.focus_aos`.
AssessmentObjectiveCode = Literal["AO1", "AO2", "AO3", "AO4", "AO5", "AO6"]

#: ``rule_selected`` discriminator — which rule (or fallback) chose the topic.
RuleSelected = Literal["rule-1", "rule-3", "rule-4", "rule-6", "baseline"]

#: ``fallback_used`` discriminator — which fallback path produced the plan.
#: ``None`` when a primary rule (1, 3, or 4) selected the topic.
FallbackKind = Literal["rule-6", "baseline"]

# Stable opening prompt used when the planner can't draw on a learner state
# at all. We do NOT source this from the curriculum YAML because the
# no-state branch must return *something* even if the YAML is missing; the
# seeded-empty branch sources its prompt from data instead.
_NO_STATE_OPENING_PROMPT: str = (
    "Welcome — let's get to know how you study. Tell me a text or topic you "
    "feel comfortable with, and one you find tricky, so I can plan a useful "
    "first session."
)

_NO_STATE_TOPIC_NAME: str = "introductory diagnostic"

# Package-data path to the baseline curriculum defaults YAML.
_CURRICULUM_DEFAULTS_PACKAGE: str = "study_tutor.planner.data"
_CURRICULUM_DEFAULTS_FILENAME: str = "curriculum_defaults.yaml"


# ---------------------------------------------------------------------------
# SessionPlan model
# ---------------------------------------------------------------------------


class SessionPlan(BaseModel):
    """The deterministic planner's output contract.

    Frozen by configuration: callers may serialise or compare plans freely
    but must not mutate them. The MCP adapter and the in-memory session
    store both depend on this immutability so a plan attached to a session
    can never be quietly rewritten by a later code path.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    topic_name: str = Field(
        ...,
        min_length=1,
        description="Topic the planner proposes for this session.",
    )
    focus_aos: list[AssessmentObjectiveCode] = Field(
        ...,
        description=(
            "Assessment Objective codes (AO1–AO6) the chosen topic "
            "exercises. May be empty when an override names a topic outside "
            "the curriculum (TASK-DSP-003 'override-not-in-curriculum')."
        ),
    )
    opening_prompt: str = Field(
        ...,
        min_length=1,
        description="The tutor's first-turn prompt for this session.",
    )
    suggested_duration_minutes: int = Field(
        default=DEFAULT_DURATION_MINUTES,
        ge=MIN_DURATION_MINUTES,
        le=MAX_DURATION_MINUTES,
        description=(
            "Suggested session length in minutes. Default 20, valid range "
            "10–45 inclusive (ASSUM-002, signed off)."
        ),
    )
    related_misconceptions: list[str] = Field(
        ...,
        description=(
            "Misconception summaries the tutor should watch for; populated "
            "by rule 4 and otherwise empty."
        ),
    )
    rationale: str = Field(
        ...,
        min_length=1,
        description=(
            "Human-readable explanation of why this topic was chosen — "
            "consumed by the rationale-observability scenarios."
        ),
    )
    fallback_used: FallbackKind | None = Field(
        ...,
        description=(
            "Which fallback path produced this plan, or ``None`` when a "
            "primary rule (1, 3, or 4) selected the topic."
        ),
    )
    rule_selected: RuleSelected = Field(
        ...,
        description="Which rule (or fallback) selected the topic.",
    )
    ao_mapping_found: bool = Field(
        ...,
        description=(
            "True when the chosen topic was matched to AO codes via the "
            "curriculum mapping; False when no mapping was found "
            "(e.g. an off-curriculum override)."
        ),
    )
    learner_state_available: bool = Field(
        ...,
        description=(
            "True when the planner had access to learner state when "
            "computing this plan; False when the read failed or no state "
            "had been seeded."
        ),
    )

    @field_validator("focus_aos")
    @classmethod
    def _ensure_focus_aos_unique(
        cls, value: list[AssessmentObjectiveCode]
    ) -> list[AssessmentObjectiveCode]:
        """Reject duplicate AO codes — they would distort coach scoring."""
        if len(set(value)) != len(value):
            raise ValueError(
                "focus_aos must not contain duplicate AO codes",
            )
        return value


# ---------------------------------------------------------------------------
# Curriculum defaults loader
# ---------------------------------------------------------------------------


def load_curriculum_defaults() -> list[dict]:
    """Read and return the parsed entries from ``curriculum_defaults.yaml``.

    The file lives under ``src/study_tutor/planner/data/`` and is shipped
    as package data so tests, the planner pipeline, and the MCP adapter
    all resolve the same path regardless of working directory.

    Returns:
        A list of entry dicts, each containing at minimum ``topic_name``,
        ``focus_aos``, and ``opening_prompt_template``.

    Raises:
        ValueError: If the YAML is missing the ``entries`` key, parses to
            an empty list, or contains an entry with empty ``focus_aos``.
    """
    text = (
        resources.files(_CURRICULUM_DEFAULTS_PACKAGE)
        .joinpath(_CURRICULUM_DEFAULTS_FILENAME)
        .read_text(encoding="utf-8")
    )
    parsed = yaml.safe_load(text)
    if not isinstance(parsed, dict) or "entries" not in parsed:
        raise ValueError(
            f"{_CURRICULUM_DEFAULTS_FILENAME} must contain an 'entries' list",
        )
    entries = parsed["entries"]
    if not isinstance(entries, list) or not entries:
        raise ValueError(
            f"{_CURRICULUM_DEFAULTS_FILENAME} must declare at least one entry",
        )
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(
                f"entries[{index}] in {_CURRICULUM_DEFAULTS_FILENAME} "
                f"must be a mapping",
            )
        focus_aos = entry.get("focus_aos") or []
        if not focus_aos:
            raise ValueError(
                f"entries[{index}].focus_aos in "
                f"{_CURRICULUM_DEFAULTS_FILENAME} must be non-empty",
            )
    return entries


# ---------------------------------------------------------------------------
# Baseline-degraded plan helper
# ---------------------------------------------------------------------------


def _baseline_plan(learner_state_available: bool) -> SessionPlan:
    """Return a baseline-curriculum :class:`SessionPlan`.

    Two branches:

    - ``learner_state_available=False`` — the student-model read failed
      or no learner is seeded at all. Returns a fixed no-state plan with
      empty misconceptions, default duration, and the no-state opening
      prompt baked into this module. The plan must be returnable even if
      ``curriculum_defaults.yaml`` is missing, so this branch never reads
      the YAML.
    - ``learner_state_available=True`` — a learner identity exists but
      they have no usable topic-confidence entries yet. Draws topic +
      focus_aos + opening_prompt from the first entry of
      ``curriculum_defaults.yaml`` so the proposed topic is data-sourced,
      not a literal in code (acceptance criterion AC-004).

    Both branches set ``rule_selected="baseline"`` and
    ``fallback_used="baseline"`` so the rationale-observability tests in
    TASK-DSP-005/006 can detect a degraded plan unambiguously.
    """
    if not learner_state_available:
        return SessionPlan(
            topic_name=_NO_STATE_TOPIC_NAME,
            focus_aos=[],
            opening_prompt=_NO_STATE_OPENING_PROMPT,
            suggested_duration_minutes=DEFAULT_DURATION_MINUTES,
            related_misconceptions=[],
            rationale=(
                "Baseline plan: no learner state available — proposing an "
                "introductory diagnostic so the tutor can gather signal."
            ),
            fallback_used="baseline",
            rule_selected="baseline",
            ao_mapping_found=False,
            learner_state_available=False,
        )

    entries = load_curriculum_defaults()
    first = entries[0]
    return SessionPlan(
        topic_name=str(first["topic_name"]),
        focus_aos=list(first["focus_aos"]),
        opening_prompt=str(first["opening_prompt_template"]),
        suggested_duration_minutes=DEFAULT_DURATION_MINUTES,
        related_misconceptions=[],
        rationale=(
            "Baseline plan: learner has no topic-confidence entries yet — "
            "drawing topic and AOs from curriculum_defaults.yaml."
        ),
        fallback_used="baseline",
        rule_selected="baseline",
        ao_mapping_found=True,
        learner_state_available=True,
    )
