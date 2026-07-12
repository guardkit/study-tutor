"""Tests for ``SessionService.build_turn_session_state`` (S-R4 §2.5/§2.6).

The player-context boundary is assembled ONCE, in the core, from a single
student-state read plus a transcript rehydration — never in a transport
adapter (D14). These tests drive the service against the in-memory fake store
and pin the four §2.5 context fields plus the §2.6 transcript window (with the
trailing current-user turn excluded).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from study_tutor.session.service import (
    DEFAULT_GRADE_TARGET,
    SessionService,
)
from tests.unit.knowledge.store.fakes import FakeStudentStore


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _seed_student(store: FakeStudentStore, *, target_grade: str | None) -> None:
    store._students["lilymay"] = {
        "name": "Lily-May",
        "year_group": 10,
        "target_grade": target_grade,
    }


def _set_conf(store: FakeStudentStore, topic: str, pct: int, band: str) -> None:
    store._confidences[("lilymay", topic)] = {
        "topic_name": topic,
        "percentage": pct,
        "band": band,
        "last_revised_at": _now(),
    }


def _add_misc(store: FakeStudentStore, topic: str, text: str, when: datetime) -> None:
    store._misconceptions.append(
        {
            "student_id": "lilymay",
            "topic_name": topic,
            "text": text,
            "observed_at": when,
            "band_at_observation": "developing",
        }
    )


@pytest.mark.asyncio
async def test_context_fields_populated_from_single_state_read() -> None:
    store = FakeStudentStore()
    await _seed_student(store, target_grade="8")
    _set_conf(store, "Ambition", 30, "struggling")
    _set_conf(store, "Imagery", 55, "developing")
    _set_conf(store, "Structure", 90, "mastered")  # excluded from weakest
    _add_misc(store, "Ambition", "Macbeth is purely evil", _now())

    record, _ = await store.create_session(
        student_id="lilymay", subject="english", topic="Ambition"
    )
    service = SessionService(store=store)

    state = await service.build_turn_session_state(
        student_id="lilymay", session_id=record.session_id
    )

    assert state.topic == "Ambition"
    assert state.mode == "tutor"
    assert state.text_name is None
    # band for the session topic
    assert state.topic_confidence_band == "struggling"
    # weakest below-Mastered, ascending, Mastered excluded
    assert state.weakest_topics == ("Ambition", "Imagery")
    assert "Structure" not in state.weakest_topics
    # misconception text surfaced
    assert state.recent_misconceptions == ("Macbeth is purely evil",)
    assert state.grade_target == "8"


@pytest.mark.asyncio
async def test_grade_target_defaults_to_grade6_when_unset() -> None:
    store = FakeStudentStore()
    await _seed_student(store, target_grade=None)
    record, _ = await store.create_session(
        student_id="lilymay", subject="english", topic="Ambition"
    )
    service = SessionService(store=store)

    state = await service.build_turn_session_state(
        student_id="lilymay", session_id=record.session_id
    )
    assert state.grade_target == DEFAULT_GRADE_TARGET == "6"


@pytest.mark.asyncio
async def test_transcript_window_excludes_trailing_current_user_turn() -> None:
    store = FakeStudentStore()
    await _seed_student(store, target_grade="6")
    record, _ = await store.create_session(
        student_id="lilymay", subject="english", topic="Ambition"
    )
    sid = record.session_id
    # Prior exchange + the just-appended current user turn (mirrors turn()).
    await store.append_turn(session_id=sid, role="user", content="q1")
    await store.append_turn(session_id=sid, role="tutor", content="a1")
    await store.append_turn(session_id=sid, role="user", content="CURRENT")

    service = SessionService(store=store)
    state = await service.build_turn_session_state(
        student_id="lilymay", session_id=sid
    )

    contents = [t.content for t in state.transcript]
    assert contents == ["q1", "a1"]
    assert "CURRENT" not in contents


@pytest.mark.asyncio
async def test_unknown_student_degrades_to_empty_context() -> None:
    store = FakeStudentStore()
    record, _ = await store.create_session(
        student_id="ghost", subject="english", topic="Ambition"
    )
    service = SessionService(store=store)
    state = await service.build_turn_session_state(
        student_id="ghost", session_id=record.session_id
    )
    assert state.topic_confidence_band is None
    assert state.weakest_topics == ()
    assert state.recent_misconceptions == ()
    assert state.grade_target == "6"
    assert state.transcript == ()


@pytest.mark.asyncio
async def test_session_topic_misconceptions_lead_the_window() -> None:
    store = FakeStudentStore()
    await _seed_student(store, target_grade="6")
    _set_conf(store, "Ambition", 40, "developing")
    old = _now() - timedelta(days=2)
    new = _now()
    # A more-recent misconception on a DIFFERENT topic, plus an older one on
    # the session topic — the session-topic match must lead.
    _add_misc(store, "Imagery", "off-topic misc", new)
    _add_misc(store, "Ambition", "on-topic misc", old)

    record, _ = await store.create_session(
        student_id="lilymay", subject="english", topic="Ambition"
    )
    service = SessionService(store=store)
    state = await service.build_turn_session_state(
        student_id="lilymay", session_id=record.session_id
    )
    assert state.recent_misconceptions[0] == "on-topic misc"
