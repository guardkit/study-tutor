"""Unit tests for the SessionPlan model and the baseline-degraded helper.

Covers TASK-DSP-001 acceptance criteria AC-001 through AC-007. AC-008
(lint/format) is enforced by the project's quality gates, not by this
test module.
"""
from __future__ import annotations

import pytest
import yaml
from pydantic import ValidationError

from study_tutor.planner import (
    AO_LITERALS,
    DEFAULT_DURATION_MINUTES,
    MAX_DURATION_MINUTES,
    MIN_DURATION_MINUTES,
    SessionPlan,
    _baseline_plan,
    load_curriculum_defaults,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _valid_plan_kwargs() -> dict:
    """Return a baseline kwargs dict that constructs a valid SessionPlan."""
    return {
        "topic_name": "metaphor identification",
        "focus_aos": ["AO2"],
        "opening_prompt": "Let's spot some metaphors.",
        "suggested_duration_minutes": 20,
        "related_misconceptions": [],
        "rationale": "Default test plan.",
        "fallback_used": None,
        "rule_selected": "rule-1",
        "ao_mapping_found": True,
        "learner_state_available": True,
    }


# ---------------------------------------------------------------------------
# AC-001: required-field rejection
# ---------------------------------------------------------------------------


def test_session_plan_instantiates_with_full_kwargs() -> None:
    plan = SessionPlan(**_valid_plan_kwargs())
    assert plan.topic_name == "metaphor identification"
    assert plan.focus_aos == ["AO2"]
    assert plan.rule_selected == "rule-1"


@pytest.mark.parametrize(
    "missing_field",
    [
        "topic_name",
        "focus_aos",
        "opening_prompt",
        "related_misconceptions",
        "rationale",
        "fallback_used",
        "rule_selected",
        "ao_mapping_found",
        "learner_state_available",
    ],
)
def test_session_plan_rejects_missing_required_field(missing_field: str) -> None:
    kwargs = _valid_plan_kwargs()
    kwargs.pop(missing_field)
    with pytest.raises(ValidationError) as exc_info:
        SessionPlan(**kwargs)
    # Pydantic surfaces the missing field name in the error payload.
    assert missing_field in str(exc_info.value)


# ---------------------------------------------------------------------------
# AC-002: frozen=True post-construction immutability
# ---------------------------------------------------------------------------


def test_session_plan_is_frozen_against_attribute_assignment() -> None:
    plan = SessionPlan(**_valid_plan_kwargs())
    with pytest.raises(ValidationError):
        plan.topic_name = "rewritten by caller"  # type: ignore[misc]


def test_session_plan_is_frozen_against_unknown_attribute() -> None:
    plan = SessionPlan(**_valid_plan_kwargs())
    with pytest.raises(ValidationError):
        plan.new_field = "nope"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# AC-003: baseline plan when learner state unavailable
# ---------------------------------------------------------------------------


def test_baseline_plan_no_learner_state() -> None:
    plan = _baseline_plan(learner_state_available=False)
    assert plan.rule_selected == "baseline"
    assert plan.fallback_used == "baseline"
    assert plan.learner_state_available is False
    assert plan.related_misconceptions == []
    assert plan.suggested_duration_minutes == DEFAULT_DURATION_MINUTES
    assert plan.focus_aos == []
    assert plan.ao_mapping_found is False
    assert plan.topic_name  # non-empty
    assert plan.opening_prompt  # non-empty


# ---------------------------------------------------------------------------
# AC-004: baseline plan with learner state draws topic from YAML
# ---------------------------------------------------------------------------


def test_baseline_plan_with_learner_state_draws_topic_from_yaml() -> None:
    plan = _baseline_plan(learner_state_available=True)
    entries = load_curriculum_defaults()

    # The proposed topic must come from the curriculum YAML, not a literal.
    yaml_topic_names = {entry["topic_name"] for entry in entries}
    assert plan.topic_name in yaml_topic_names

    # The chosen entry's focus AOs and opening prompt should round-trip from
    # the same YAML entry (we pick the first by convention).
    first = entries[0]
    assert plan.topic_name == first["topic_name"]
    assert plan.focus_aos == list(first["focus_aos"])
    assert plan.opening_prompt == str(first["opening_prompt_template"])

    assert plan.rule_selected == "baseline"
    assert plan.fallback_used == "baseline"
    assert plan.learner_state_available is True


# ---------------------------------------------------------------------------
# AC-005: suggested_duration_minutes default + range enforcement
# ---------------------------------------------------------------------------


def test_suggested_duration_defaults_to_twenty() -> None:
    kwargs = _valid_plan_kwargs()
    kwargs.pop("suggested_duration_minutes")
    plan = SessionPlan(**kwargs)
    assert plan.suggested_duration_minutes == DEFAULT_DURATION_MINUTES == 20


@pytest.mark.parametrize(
    "boundary_value",
    [MIN_DURATION_MINUTES, MAX_DURATION_MINUTES],
)
def test_suggested_duration_accepts_inclusive_boundaries(boundary_value: int) -> None:
    plan = SessionPlan(
        **{**_valid_plan_kwargs(), "suggested_duration_minutes": boundary_value},
    )
    assert plan.suggested_duration_minutes == boundary_value


@pytest.mark.parametrize(
    "out_of_range",
    [MIN_DURATION_MINUTES - 1, MAX_DURATION_MINUTES + 1, 0, -5, 60, 9999],
)
def test_suggested_duration_rejects_out_of_range(out_of_range: int) -> None:
    with pytest.raises(ValidationError):
        SessionPlan(
            **{
                **_valid_plan_kwargs(),
                "suggested_duration_minutes": out_of_range,
            },
        )


# ---------------------------------------------------------------------------
# AC-006: focus_aos rejects values outside AO1–AO6
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("ao_code", list(AO_LITERALS))
def test_focus_aos_accepts_each_valid_ao_code(ao_code: str) -> None:
    plan = SessionPlan(**{**_valid_plan_kwargs(), "focus_aos": [ao_code]})
    assert plan.focus_aos == [ao_code]


@pytest.mark.parametrize(
    "invalid_value",
    ["AO0", "AO7", "ao1", "AO", "AO12", "", "Reading", 1],
)
def test_focus_aos_rejects_invalid_codes(invalid_value: object) -> None:
    with pytest.raises(ValidationError):
        SessionPlan(**{**_valid_plan_kwargs(), "focus_aos": [invalid_value]})


def test_focus_aos_rejects_duplicates() -> None:
    with pytest.raises(ValidationError):
        SessionPlan(**{**_valid_plan_kwargs(), "focus_aos": ["AO1", "AO1"]})


# ---------------------------------------------------------------------------
# AC-007: curriculum_defaults.yaml exists, parses, has at least one entry
# ---------------------------------------------------------------------------


def test_curriculum_defaults_yaml_parses_and_has_at_least_one_entry() -> None:
    entries = load_curriculum_defaults()
    assert isinstance(entries, list)
    assert len(entries) >= 1
    for entry in entries:
        assert entry["topic_name"]
        assert entry["focus_aos"]
        assert entry["opening_prompt_template"]


def test_curriculum_defaults_yaml_focus_aos_are_valid_ao_codes() -> None:
    entries = load_curriculum_defaults()
    for entry in entries:
        for ao in entry["focus_aos"]:
            assert ao in AO_LITERALS, (
                f"curriculum_defaults.yaml entry {entry['topic_name']!r} "
                f"contains invalid AO code {ao!r}"
            )


def test_curriculum_defaults_yaml_is_loadable_via_pyyaml_directly() -> None:
    """Sanity check: the file is syntactically valid YAML at the bytes level."""
    from importlib import resources

    text = (
        resources.files("study_tutor.planner.data")
        .joinpath("curriculum_defaults.yaml")
        .read_text(encoding="utf-8")
    )
    parsed = yaml.safe_load(text)
    assert "entries" in parsed
    assert len(parsed["entries"]) >= 1
