"""Unit tests for student-model episode types.

Covers AC-001..AC-005 of TASK-GSM-002:
  - All four classes exist and inherit correctly (AC-001)
  - ``episode_kind`` discriminator field is present and pinned (AC-002)
  - ``to_graphiti_episode_body()`` is deterministic (AC-003)
  - Required fields are rejected when omitted; type coercion works (AC-004)
  - No imports from graphiti-core (AC-005)
"""

from __future__ import annotations

import inspect
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from study_tutor.knowledge import episodes as episodes_module
from study_tutor.knowledge.episodes import (
    EpisodeBase,
    MisconceptionObservedEpisode,
    SessionCompletedEpisode,
    TopicConfidenceUpdatedEpisode,
)


# ---------------------------------------------------------------------------
# Fixture-style payload helpers
# ---------------------------------------------------------------------------


def _session_payload() -> dict:
    return dict(
        session_id="sess-001",
        student_id="lilymay",
        subject_slug="english-literature-gcse",
        text_name="Macbeth",
        topics_covered=["ambition", "fate"],
        aos_exercised=["AO1", "AO2"],
        narrative_summary="Discussed Macbeth's ambition and fate.",
        started_at=datetime(2026, 4, 27, 10, 0, tzinfo=timezone.utc),
        ended_at=datetime(2026, 4, 27, 10, 45, tzinfo=timezone.utc),
    )


def _topic_payload() -> dict:
    return dict(
        student_id="lilymay",
        topic_name="ambition",
        previous_band="developing",
        new_band="proficient",
        previous_percentage=45,
        new_percentage=70,
        observed_at=datetime(2026, 4, 27, 10, 45, tzinfo=timezone.utc),
        triggering_session_id="sess-001",
        # AC-CONF-07 (TASK-GR-CONF): required field discriminating Phase-1
        # heuristic-era data from FEAT-PH2-001 real-signal data.
        confidence_source="phase1_minimal_policy",
    )


def _misconception_payload() -> dict:
    return dict(
        student_id="lilymay",
        topic_name="iambic pentameter",
        misconception_text="Believes iambic pentameter requires end-rhyme.",
        observed_at=datetime(2026, 4, 27, 10, 30, tzinfo=timezone.utc),
        triggering_session_id="sess-001",
        confidence_band_at_observation="developing",
    )


# ---------------------------------------------------------------------------
# AC-001: classes exist and inherit from EpisodeBase
# ---------------------------------------------------------------------------


def test_concrete_classes_subclass_episodebase():
    for cls in (
        SessionCompletedEpisode,
        TopicConfidenceUpdatedEpisode,
        MisconceptionObservedEpisode,
    ):
        assert issubclass(cls, EpisodeBase), (
            f"{cls.__name__} must inherit from EpisodeBase"
        )


def test_episodebase_is_pydantic_model():
    from pydantic import BaseModel

    assert issubclass(EpisodeBase, BaseModel)


# ---------------------------------------------------------------------------
# AC-002: episode_kind discriminator present and matches scope-doc names
# ---------------------------------------------------------------------------


def test_episode_kind_field_present_on_all_classes():
    for cls in (
        EpisodeBase,
        SessionCompletedEpisode,
        TopicConfidenceUpdatedEpisode,
        MisconceptionObservedEpisode,
    ):
        assert "episode_kind" in cls.model_fields, (
            f"{cls.__name__} must expose episode_kind"
        )


def test_session_completed_kind_value():
    ep = SessionCompletedEpisode(**_session_payload())
    assert ep.episode_kind == "session_completed"


def test_topic_confidence_updated_kind_value():
    ep = TopicConfidenceUpdatedEpisode(**_topic_payload())
    assert ep.episode_kind == "topic_confidence_updated"


def test_misconception_observed_kind_value():
    ep = MisconceptionObservedEpisode(**_misconception_payload())
    assert ep.episode_kind == "misconception_observed"


def test_session_rejects_wrong_episode_kind():
    payload = _session_payload()
    payload["episode_kind"] = "topic_confidence_updated"
    with pytest.raises(ValidationError):
        SessionCompletedEpisode(**payload)


def test_topic_rejects_wrong_episode_kind():
    payload = _topic_payload()
    payload["episode_kind"] = "session_completed"
    with pytest.raises(ValidationError):
        TopicConfidenceUpdatedEpisode(**payload)


def test_misconception_rejects_wrong_episode_kind():
    payload = _misconception_payload()
    payload["episode_kind"] = "session_completed"
    with pytest.raises(ValidationError):
        MisconceptionObservedEpisode(**payload)


def test_misconception_rejects_unknown_episode_kind_string():
    payload = _misconception_payload()
    payload["episode_kind"] = "totally_made_up_kind"
    with pytest.raises(ValidationError):
        MisconceptionObservedEpisode(**payload)


# ---------------------------------------------------------------------------
# AC-003: to_graphiti_episode_body is deterministic
# ---------------------------------------------------------------------------


def test_session_body_is_deterministic_across_calls():
    ep = SessionCompletedEpisode(**_session_payload())
    assert ep.to_graphiti_episode_body() == ep.to_graphiti_episode_body()


def test_session_body_is_deterministic_across_instances():
    e1 = SessionCompletedEpisode(**_session_payload())
    e2 = SessionCompletedEpisode(**_session_payload())
    assert e1.to_graphiti_episode_body() == e2.to_graphiti_episode_body()


def test_topic_body_is_deterministic_across_instances():
    e1 = TopicConfidenceUpdatedEpisode(**_topic_payload())
    e2 = TopicConfidenceUpdatedEpisode(**_topic_payload())
    assert e1.to_graphiti_episode_body() == e2.to_graphiti_episode_body()


def test_topic_body_handles_optional_triggering_session():
    payload = _topic_payload()
    payload.pop("triggering_session_id")
    ep = TopicConfidenceUpdatedEpisode(**payload)
    body = ep.to_graphiti_episode_body()
    # Optional field should still surface deterministically as a sentinel.
    assert "none" in body.lower()


def test_misconception_body_is_deterministic_across_instances():
    e1 = MisconceptionObservedEpisode(**_misconception_payload())
    e2 = MisconceptionObservedEpisode(**_misconception_payload())
    assert e1.to_graphiti_episode_body() == e2.to_graphiti_episode_body()


def test_bodies_contain_key_payload_fields():
    """Sanity-check that body strings actually project the key fields.

    Not a contract (the body wording can evolve), but ensures determinism is
    not achieved by returning a constant unrelated to the payload.
    """
    s = SessionCompletedEpisode(**_session_payload()).to_graphiti_episode_body()
    assert "sess-001" in s
    assert "lilymay" in s
    assert "Macbeth" in s

    t = TopicConfidenceUpdatedEpisode(**_topic_payload()).to_graphiti_episode_body()
    assert "ambition" in t
    assert "developing" in t
    assert "proficient" in t

    m = MisconceptionObservedEpisode(
        **_misconception_payload()
    ).to_graphiti_episode_body()
    assert "iambic pentameter" in m
    assert "end-rhyme" in m


# ---------------------------------------------------------------------------
# AC-004: required fields rejected; type coercion correct
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "missing",
    [
        "session_id",
        "student_id",
        "subject_slug",
        "text_name",
        "topics_covered",
        "aos_exercised",
        "narrative_summary",
        "started_at",
        "ended_at",
    ],
)
def test_session_rejects_missing_required(missing: str):
    payload = _session_payload()
    payload.pop(missing)
    with pytest.raises(ValidationError):
        SessionCompletedEpisode(**payload)


@pytest.mark.parametrize(
    "missing",
    [
        "student_id",
        "topic_name",
        "previous_band",
        "new_band",
        "previous_percentage",
        "new_percentage",
        "observed_at",
        "confidence_source",
    ],
)
def test_topic_rejects_missing_required(missing: str):
    payload = _topic_payload()
    payload.pop(missing)
    with pytest.raises(ValidationError):
        TopicConfidenceUpdatedEpisode(**payload)


def test_topic_rejects_empty_confidence_source():
    """AC-CONF-07: ``confidence_source`` has ``min_length=1`` — empty rejected."""
    payload = _topic_payload()
    payload["confidence_source"] = ""
    with pytest.raises(ValidationError):
        TopicConfidenceUpdatedEpisode(**payload)


def test_topic_body_surfaces_confidence_source():
    """AC-CONF-07: the projection includes the policy identifier so the
    natural-language body is self-describing for downstream analytics.
    """
    payload = _topic_payload()
    payload["confidence_source"] = "phase1_minimal_policy"
    body = TopicConfidenceUpdatedEpisode(**payload).to_graphiti_episode_body()
    assert "phase1_minimal_policy" in body


@pytest.mark.parametrize(
    "missing",
    [
        "student_id",
        "topic_name",
        "misconception_text",
        "observed_at",
        "triggering_session_id",
        "confidence_band_at_observation",
    ],
)
def test_misconception_rejects_missing_required(missing: str):
    payload = _misconception_payload()
    payload.pop(missing)
    with pytest.raises(ValidationError):
        MisconceptionObservedEpisode(**payload)


def test_session_rejects_unknown_extra_field():
    payload = _session_payload()
    payload["surprise"] = "should-fail"
    with pytest.raises(ValidationError):
        SessionCompletedEpisode(**payload)


def test_topic_percentage_type_coercion():
    """Pydantic should coerce numeric strings to int for percentage fields."""
    payload = _topic_payload()
    payload["previous_percentage"] = "45"
    payload["new_percentage"] = "70"
    ep = TopicConfidenceUpdatedEpisode(**payload)
    assert ep.previous_percentage == 45
    assert ep.new_percentage == 70


def test_session_started_at_iso_string_coerced_to_datetime():
    payload = _session_payload()
    payload["started_at"] = "2026-04-27T10:00:00+00:00"
    ep = SessionCompletedEpisode(**payload)
    assert isinstance(ep.started_at, datetime)


def test_session_topics_covered_must_be_list():
    payload = _session_payload()
    payload["topics_covered"] = 12345  # not coercible to list[str]
    with pytest.raises(ValidationError):
        SessionCompletedEpisode(**payload)


# ---------------------------------------------------------------------------
# Round-trip: model_validate(model_dump()) returns an equal instance
# ---------------------------------------------------------------------------


def test_session_roundtrip_equality():
    e1 = SessionCompletedEpisode(**_session_payload())
    e2 = SessionCompletedEpisode.model_validate(e1.model_dump())
    assert e1 == e2


def test_topic_roundtrip_equality():
    e1 = TopicConfidenceUpdatedEpisode(**_topic_payload())
    e2 = TopicConfidenceUpdatedEpisode.model_validate(e1.model_dump())
    assert e1 == e2


def test_misconception_roundtrip_equality():
    e1 = MisconceptionObservedEpisode(**_misconception_payload())
    e2 = MisconceptionObservedEpisode.model_validate(e1.model_dump())
    assert e1 == e2


# ---------------------------------------------------------------------------
# AC-005: episode types are stack-agnostic (no graphiti-core)
# ---------------------------------------------------------------------------


def test_episodes_module_does_not_import_graphiti_core():
    src = inspect.getsource(episodes_module)
    assert "graphiti_core" not in src, (
        "episodes.py must not import graphiti_core — episode types are stack-agnostic"
    )
    assert "from graphiti" not in src
    assert "import graphiti" not in src
