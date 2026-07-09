"""Unit tests for ``FakeStudentStore.get_gamification_state``.

Exercises the store-method contract directly (auth blocks the unknown-student
path at the HTTP layer, so it is only reachable here). Parity with the Postgres
store is guaranteed by both delegating to the same ``study_tutor.gamification``
builder; this asserts the fake wires the right rows into it.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.unit.knowledge.store.fakes import FakeStudentStore

UTC = timezone.utc


async def test_unknown_student_returns_exists_false() -> None:
    store = FakeStudentStore()
    state = await store.get_gamification_state("nobody")
    assert state.exists is False
    assert state.total_xp == 0
    assert state.streak_days == 0
    assert state.level_name is None


async def test_seeded_but_empty_is_zeroed_beginner() -> None:
    store = FakeStudentStore()
    store.add_student("lilymay", name="Lily May")
    state = await store.get_gamification_state("lilymay")
    assert state.exists is True
    assert state.student_name == "Lily May"
    assert state.total_xp == 0
    assert state.recent_xp == 0
    assert state.streak_days == 0
    assert state.level_name == "Beginner"


async def test_ended_sessions_bank_real_xp_and_streak() -> None:
    store = FakeStudentStore()
    store.add_student("lilymay", name="Lily May")
    now = datetime.now(UTC)
    # 40-min completed session today → 180 XP (long band), streak 1.
    store.add_ended_session(
        "lilymay", started_at=now - timedelta(minutes=40), last_activity=now
    )
    state = await store.get_gamification_state("lilymay")
    assert state.exists is True
    assert state.total_xp == 180
    assert state.recent_xp == 180
    assert state.streak_days == 1
    assert state.level_name == "Novice"  # 180 ≥ 100


async def test_active_sessions_do_not_count() -> None:
    # An in-flight (non-ended) session banks nothing until it ends.
    store = FakeStudentStore()
    store.add_student("lilymay", name="Lily May")
    now = datetime.now(UTC)
    store.add_ended_session(
        "lilymay", started_at=now - timedelta(minutes=40), last_activity=now
    )
    # Directly stage an active session (create_session leaves it active).
    _, _created = await store.create_session(student_id="lilymay", subject="english")
    state = await store.get_gamification_state("lilymay")
    assert state.total_xp == 180  # unchanged by the active session
