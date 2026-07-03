"""Unit tests for ``study_tutor.knowledge.student_model``.

Covers all six acceptance criteria of TASK-GSM-001:

- AC-001: Seven Pydantic entity classes with field types matching the
  scope-doc tables.
- AC-002: Six relationship name constants exported as string literals.
- AC-003: Three group-id constants exported as module-level constants.
- AC-004: ``confidence_band_for`` returns the correct band at every
  ASSUM-001 boundary.
- AC-005: Module docstring documents the cross-repo divergence
  (``fleet:appmilla`` vs ``appmilla-fleet``).
- AC-006: Entity Pydantic schema dumps match expected JSON shape, and
  the module is stack-agnostic (does not import graphiti-core).
"""
from __future__ import annotations

import inspect
from datetime import datetime, timezone

import pytest
from pydantic import BaseModel, ValidationError

from study_tutor.knowledge import student_model as student_model_module
from study_tutor.knowledge.student_model import (
    ASSESSED_BY,
    COVERS,
    EPOCH_NEVER_REVISED,
    FLEET_GROUP_ID,
    HAS_CONFIDENCE,
    HAS_TEXT,
    STUDENT_GROUP_PREFIX,
    STUDIES,
    SUBJECT_GROUP_PREFIX,
    WORKING_ON,
    AssessmentObjective,
    Misconception,
    Student,
    Subject,
    Text,
    Topic,
    TopicConfidence,
    confidence_band_for,
)


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

_FIXED_NOW = datetime(2026, 4, 27, 10, 0, tzinfo=timezone.utc)


def _student_payload() -> dict:
    return dict(
        student_id="lilymay",
        name="Lilymay",
        year_group=10,
        target_grade="8",
        created_at=_FIXED_NOW,
    )


def _subject_payload() -> dict:
    return dict(
        name="English Literature",
        exam_board="AQA",
        spec_code="8702",
    )


def _text_payload() -> dict:
    return dict(
        name="Macbeth",
        kind="primary",
        source_path="domains/gcse-english/sources/primary_text/macbeth.txt",
    )


def _topic_payload() -> dict:
    return dict(
        name="Witches Act 1",
        subject_ref="8702",
        ao_refs=["AO1", "AO2"],
    )


def _ao_payload() -> dict:
    return dict(
        code="AO1",
        description="Read, understand and respond to texts.",
        exam_board="AQA",
    )


def _misconception_payload() -> dict:
    return dict(
        text="Believes iambic pentameter requires end-rhyme.",
        topic_ref="iambic pentameter",
        observed_at=_FIXED_NOW,
        confidence_band_at_observation="developing",
    )


def _topic_confidence_payload() -> dict:
    return dict(
        student_ref="lilymay",
        topic_ref="Witches Act 1",
        percentage=68,
        band="developing",
        last_revised_at=_FIXED_NOW,
    )


# ---------------------------------------------------------------------------
# AC-001: Seven entity classes are pydantic.BaseModel subclasses
# ---------------------------------------------------------------------------

ENTITIES = [
    Student,
    Subject,
    Text,
    Topic,
    AssessmentObjective,
    Misconception,
    TopicConfidence,
]


def test_seven_entities_exist() -> None:
    assert len(ENTITIES) == 7


@pytest.mark.parametrize("cls", ENTITIES)
def test_entity_is_pydantic_basemodel(cls: type) -> None:
    assert issubclass(cls, BaseModel), f"{cls.__name__} must subclass pydantic.BaseModel"


def test_student_validates_required_fields() -> None:
    student = Student(**_student_payload())
    assert student.student_id == "lilymay"
    assert student.year_group == 10
    assert student.target_grade == "8"
    assert isinstance(student.created_at, datetime)


def test_student_year_group_bounds_enforced() -> None:
    payload = _student_payload()
    payload["year_group"] = 6  # below KS3
    with pytest.raises(ValidationError):
        Student(**payload)
    payload["year_group"] = 14  # above KS5
    with pytest.raises(ValidationError):
        Student(**payload)


@pytest.mark.parametrize(
    "missing",
    ["student_id", "name", "year_group", "target_grade", "created_at"],
)
def test_student_rejects_missing_required(missing: str) -> None:
    payload = _student_payload()
    payload.pop(missing)
    with pytest.raises(ValidationError):
        Student(**payload)


@pytest.mark.parametrize(
    "missing",
    ["name", "exam_board", "spec_code"],
)
def test_subject_rejects_missing_required(missing: str) -> None:
    payload = _subject_payload()
    payload.pop(missing)
    with pytest.raises(ValidationError):
        Subject(**payload)


@pytest.mark.parametrize("kind", ["primary", "secondary", "context"])
def test_text_accepts_all_kinds(kind: str) -> None:
    payload = _text_payload()
    payload["kind"] = kind
    text = Text(**payload)
    assert text.kind == kind


def test_text_rejects_invalid_kind() -> None:
    payload = _text_payload()
    payload["kind"] = "tertiary"  # not in TextKind
    with pytest.raises(ValidationError):
        Text(**payload)


@pytest.mark.parametrize(
    "missing",
    ["name", "kind", "source_path"],
)
def test_text_rejects_missing_required(missing: str) -> None:
    payload = _text_payload()
    payload.pop(missing)
    with pytest.raises(ValidationError):
        Text(**payload)


def test_topic_ao_refs_default_empty() -> None:
    payload = _topic_payload()
    payload.pop("ao_refs")
    topic = Topic(**payload)
    assert topic.ao_refs == []


def test_topic_rejects_missing_required() -> None:
    payload = _topic_payload()
    payload.pop("name")
    with pytest.raises(ValidationError):
        Topic(**payload)


@pytest.mark.parametrize("code", ["AO1", "AO2", "AO3", "AO4", "AO5", "AO6"])
def test_assessment_objective_accepts_all_valid_codes(code: str) -> None:
    payload = _ao_payload()
    payload["code"] = code
    ao = AssessmentObjective(**payload)
    assert ao.code == code


@pytest.mark.parametrize("bad_code", ["AO0", "AO7", "AOX", "ao1", "AO 1", ""])
def test_assessment_objective_rejects_invalid_codes(bad_code: str) -> None:
    payload = _ao_payload()
    payload["code"] = bad_code
    with pytest.raises(ValidationError):
        AssessmentObjective(**payload)


def test_misconception_rejects_missing_required() -> None:
    payload = _misconception_payload()
    payload.pop("text")
    with pytest.raises(ValidationError):
        Misconception(**payload)


def test_misconception_band_validated() -> None:
    payload = _misconception_payload()
    payload["confidence_band_at_observation"] = "totally-fine"
    with pytest.raises(ValidationError):
        Misconception(**payload)


def test_topic_confidence_percentage_bounds() -> None:
    payload = _topic_confidence_payload()
    payload["percentage"] = -1
    with pytest.raises(ValidationError):
        TopicConfidence(**payload)
    payload["percentage"] = 101
    with pytest.raises(ValidationError):
        TopicConfidence(**payload)


def test_topic_confidence_band_validated() -> None:
    payload = _topic_confidence_payload()
    payload["band"] = "wobbly"
    with pytest.raises(ValidationError):
        TopicConfidence(**payload)


@pytest.mark.parametrize("cls,payload_fn", [
    (Student, _student_payload),
    (Subject, _subject_payload),
    (Text, _text_payload),
    (Topic, _topic_payload),
    (AssessmentObjective, _ao_payload),
    (Misconception, _misconception_payload),
    (TopicConfidence, _topic_confidence_payload),
])
def test_entities_forbid_extra_fields(cls: type, payload_fn) -> None:
    payload = payload_fn()
    payload["unexpected"] = "should-fail"
    with pytest.raises(ValidationError):
        cls(**payload)


# ---------------------------------------------------------------------------
# AC-002: Six relationship name constants
# ---------------------------------------------------------------------------

def test_relationship_constants_match_scope_doc() -> None:
    assert STUDIES == "STUDIES"
    assert WORKING_ON == "WORKING_ON"
    assert HAS_TEXT == "HAS_TEXT"
    assert COVERS == "COVERS"
    assert ASSESSED_BY == "ASSESSED_BY"
    assert HAS_CONFIDENCE == "HAS_CONFIDENCE"


def test_relationship_constants_are_strings() -> None:
    for name in (STUDIES, WORKING_ON, HAS_TEXT, COVERS, ASSESSED_BY, HAS_CONFIDENCE):
        assert isinstance(name, str)


def test_relationship_constants_are_distinct() -> None:
    constants = {STUDIES, WORKING_ON, HAS_TEXT, COVERS, ASSESSED_BY, HAS_CONFIDENCE}
    assert len(constants) == 6


# ---------------------------------------------------------------------------
# AC-003: Three group-id constants
# ---------------------------------------------------------------------------

def test_group_id_constant_values() -> None:
    # Dash form (not colon) — graphiti-core 0.29's GroupIdValidationError
    # rejects characters outside [A-Za-z0-9_-]. See student_model.py
    # constant comments.
    assert STUDENT_GROUP_PREFIX == "student-"
    assert SUBJECT_GROUP_PREFIX == "subject-"
    assert FLEET_GROUP_ID == "fleet-appmilla"


def test_group_id_constants_are_strings() -> None:
    assert isinstance(STUDENT_GROUP_PREFIX, str)
    assert isinstance(SUBJECT_GROUP_PREFIX, str)
    assert isinstance(FLEET_GROUP_ID, str)


def test_group_id_prefixes_compose_to_expected_format() -> None:
    assert f"{STUDENT_GROUP_PREFIX}lilymay" == "student-lilymay"
    assert f"{SUBJECT_GROUP_PREFIX}gcse-english" == "subject-gcse-english"


# ---------------------------------------------------------------------------
# AC-004: confidence_band_for boundaries
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("percentage,expected", [
    # Lower bound + struggling band
    (0, "struggling"),
    (1, "struggling"),
    (39, "struggling"),
    # developing band
    (40, "developing"),
    (50, "developing"),
    (59, "developing"),
    # secure band
    (60, "secure"),
    (70, "secure"),
    (79, "secure"),
    # mastered band + upper bound
    (80, "mastered"),
    (95, "mastered"),
    (100, "mastered"),
])
def test_confidence_band_for_boundaries(percentage: int, expected: str) -> None:
    assert confidence_band_for(percentage) == expected


def test_confidence_band_for_full_sweep() -> None:
    """All 101 valid integer percentages map to one of the four bands."""
    valid_bands = {"struggling", "developing", "secure", "mastered"}
    for pct in range(0, 101):
        assert confidence_band_for(pct) in valid_bands


@pytest.mark.parametrize("bad_value", [-1, 101, 200, -100])
def test_confidence_band_for_rejects_out_of_range(bad_value: int) -> None:
    with pytest.raises(ValueError):
        confidence_band_for(bad_value)


# ---------------------------------------------------------------------------
# AC-005: Module docstring documents the cross-repo divergence
# ---------------------------------------------------------------------------

def test_module_docstring_documents_cross_repo_divergence() -> None:
    docstring = student_model_module.__doc__ or ""
    # Must mention both conventions and the source of the convention.
    # Either form ("fleet:appmilla" historic / "fleet-appmilla" current)
    # is accepted to keep the assertion stable across the dash-form
    # migration triggered by graphiti-core 0.29's group-id validator.
    assert "fleet:appmilla" in docstring or "fleet-appmilla" in docstring
    assert "appmilla-fleet" in docstring
    # Must mention the upstream specification.
    assert "phase-1-scope.md" in docstring
    # Must mention the sibling repo whose convention differs.
    assert "specialist-agent" in docstring


# ---------------------------------------------------------------------------
# AC-006: Schema-shape and stack-agnostic checks
# ---------------------------------------------------------------------------

def test_student_model_module_does_not_import_graphiti_core() -> None:
    src = inspect.getsource(student_model_module)
    assert "graphiti_core" not in src
    assert "from graphiti" not in src
    assert "import graphiti" not in src


def test_topic_confidence_schema_dump_shape() -> None:
    """Pydantic schema dump matches the expected JSON shape."""
    tc = TopicConfidence(**_topic_confidence_payload())
    dump = tc.model_dump()
    assert set(dump.keys()) == {
        "student_ref",
        "topic_ref",
        "percentage",
        "band",
        "last_revised_at",
    }
    assert dump["percentage"] == 68
    assert dump["band"] == "developing"


def test_student_schema_dump_shape() -> None:
    student = Student(**_student_payload())
    dump = student.model_dump()
    assert set(dump.keys()) == {
        "student_id",
        "name",
        "year_group",
        "target_grade",
        "created_at",
    }


def test_text_schema_dump_shape() -> None:
    text = Text(**_text_payload())
    dump = text.model_dump()
    assert set(dump.keys()) == {"name", "kind", "source_path"}


def test_assessment_objective_schema_dump_shape() -> None:
    ao = AssessmentObjective(**_ao_payload())
    dump = ao.model_dump()
    assert set(dump.keys()) == {"code", "description", "exam_board"}


def test_entity_round_trip_equality() -> None:
    """All seven entities round-trip through model_validate(model_dump())."""
    cases = [
        (Student, _student_payload()),
        (Subject, _subject_payload()),
        (Text, _text_payload()),
        (Topic, _topic_payload()),
        (AssessmentObjective, _ao_payload()),
        (Misconception, _misconception_payload()),
        (TopicConfidence, _topic_confidence_payload()),
    ]
    for cls, payload in cases:
        instance = cls(**payload)
        clone = cls.model_validate(instance.model_dump())
        assert instance == clone, f"{cls.__name__} did not round-trip cleanly"


# ---------------------------------------------------------------------------
# TASK-GSM-009 AC-12 / ADR-ARCH-021 §G3 — EPOCH_NEVER_REVISED sentinel
# ---------------------------------------------------------------------------


def test_epoch_never_revised_is_unix_epoch_utc() -> None:
    """The sentinel is exactly 1970-01-01T00:00:00Z (the Unix epoch)."""
    assert EPOCH_NEVER_REVISED == datetime(1970, 1, 1, tzinfo=timezone.utc)
    assert EPOCH_NEVER_REVISED.tzinfo is timezone.utc


def test_epoch_never_revised_accepted_by_topic_confidence() -> None:
    """A baseline TopicConfidence write with the sentinel is valid."""
    tc = TopicConfidence(
        student_ref="lilymay",
        topic_ref="Macbeth's witches",
        percentage=25,
        band="struggling",
        last_revised_at=EPOCH_NEVER_REVISED,
    )
    assert tc.last_revised_at == EPOCH_NEVER_REVISED


def test_epoch_never_revised_falls_outside_planner_cooldown() -> None:
    """Sanity check: any reasonable ``now`` puts the epoch well outside the
    48h cooldown the planner uses (per ADR-ARCH-021 §G3 trade-off note).
    """
    now = datetime(2026, 5, 4, tzinfo=timezone.utc)
    delta = now - EPOCH_NEVER_REVISED
    # Comfortably more than 48h — actually ~56 years.
    assert delta.total_seconds() > 48 * 3600
    assert delta.days > 365 * 50  # at least 50 years
