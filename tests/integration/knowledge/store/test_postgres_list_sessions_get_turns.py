"""Integration tests for PostgresStudentStore.list_sessions and get_turns.

Tests ordered read operations for session management (TASK-SMP3-02).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text


@pytest.mark.asyncio
async def test_list_sessions_returns_newest_first(pg_store, pg_engine, student_id):
    """list_sessions returns sessions ordered by last_activity DESC."""
    # Create three sessions with different last_activity times
    now = datetime.now(timezone.utc)

    async with pg_engine.begin() as conn:
        # Oldest session
        await conn.execute(
            text(
                "INSERT INTO session (session_id, student_id, subject, topic, status, "
                "started_at, last_activity, turn_count) "
                "VALUES (:sid, :student_id, :subject, :topic, :status, :started_at, "
                ":last_activity, :turn_count)"
            ),
            {
                "sid": "session-1",
                "student_id": student_id,
                "subject": "Mathematics",
                "topic": "Algebra",
                "status": "ended",
                "started_at": now - timedelta(hours=3),
                "last_activity": now - timedelta(hours=3),
                "turn_count": 5,
            },
        )

        # Newest session
        await conn.execute(
            text(
                "INSERT INTO session (session_id, student_id, subject, topic, status, "
                "started_at, last_activity, turn_count) "
                "VALUES (:sid, :student_id, :subject, :topic, :status, :started_at, "
                ":last_activity, :turn_count)"
            ),
            {
                "sid": "session-2",
                "student_id": student_id,
                "subject": "Science",
                "topic": "Physics",
                "status": "active",
                "started_at": now - timedelta(hours=1),
                "last_activity": now - timedelta(minutes=10),
                "turn_count": 3,
            },
        )

        # Middle session
        await conn.execute(
            text(
                "INSERT INTO session (session_id, student_id, subject, topic, status, "
                "started_at, last_activity, turn_count) "
                "VALUES (:sid, :student_id, :subject, :topic, :status, :started_at, "
                ":last_activity, :turn_count)"
            ),
            {
                "sid": "session-3",
                "student_id": student_id,
                "subject": "English",
                "topic": None,
                "status": "active",
                "started_at": now - timedelta(hours=2),
                "last_activity": now - timedelta(hours=1),
                "turn_count": 2,
            },
        )

    # Act
    sessions = await pg_store.list_sessions(student_id)

    # Assert
    assert len(sessions) == 3
    assert sessions[0].session_id == "session-2"  # Newest (10 min ago)
    assert sessions[1].session_id == "session-3"  # Middle (1 hour ago)
    assert sessions[2].session_id == "session-1"  # Oldest (3 hours ago)


@pytest.mark.asyncio
async def test_list_sessions_respects_limit(pg_store, pg_engine, student_id):
    """list_sessions respects the limit parameter."""
    now = datetime.now(timezone.utc)

    # Create 5 sessions — one subject each: one-active-per-(student, subject)
    # is structural since rev 346cd366b66e (ruled (b), 2026-08-04).
    async with pg_engine.begin() as conn:
        for i in range(5):
            await conn.execute(
                text(
                    "INSERT INTO session (session_id, student_id, subject, status, "
                    "started_at, last_activity, turn_count) "
                    "VALUES (:sid, :student_id, :subject, :status, :started_at, "
                    ":last_activity, :turn_count)"
                ),
                {
                    "sid": f"session-{i}",
                    "student_id": student_id,
                    "subject": f"subject-{i}",
                    "status": "active",
                    "started_at": now - timedelta(hours=i),
                    "last_activity": now - timedelta(hours=i),
                    "turn_count": 0,
                },
            )

    # Act - request only 3
    sessions = await pg_store.list_sessions(student_id, limit=3)

    # Assert
    assert len(sessions) == 3
    # Should get the 3 most recent (session-0, session-1, session-2)
    assert sessions[0].session_id == "session-0"
    assert sessions[1].session_id == "session-1"
    assert sessions[2].session_id == "session-2"


@pytest.mark.asyncio
async def test_list_sessions_filters_by_status(pg_store, pg_engine, student_id):
    """list_sessions filters by status when provided."""
    now = datetime.now(timezone.utc)

    async with pg_engine.begin() as conn:
        # Create 2 active sessions — one subject each (the one-active
        # invariant is per (student, subject), rev 346cd366b66e).
        for i in range(2):
            await conn.execute(
                text(
                    "INSERT INTO session (session_id, student_id, subject, status, "
                    "started_at, last_activity, turn_count) "
                    "VALUES (:sid, :student_id, :subject, :status, :started_at, "
                    ":last_activity, :turn_count)"
                ),
                {
                    "sid": f"active-{i}",
                    "student_id": student_id,
                    "subject": f"subject-{i}",
                    "status": "active",
                    "started_at": now - timedelta(hours=i),
                    "last_activity": now - timedelta(hours=i),
                    "turn_count": 0,
                },
            )

        # Create 3 ended sessions
        for i in range(3):
            await conn.execute(
                text(
                    "INSERT INTO session (session_id, student_id, subject, status, "
                    "started_at, last_activity, turn_count) "
                    "VALUES (:sid, :student_id, :subject, :status, :started_at, "
                    ":last_activity, :turn_count)"
                ),
                {
                    "sid": f"ended-{i}",
                    "student_id": student_id,
                    "subject": "Science",
                    "status": "ended",
                    "started_at": now - timedelta(hours=i + 2),
                    "last_activity": now - timedelta(hours=i + 2),
                    "turn_count": 0,
                },
            )

    # Act
    active_sessions = await pg_store.list_sessions(student_id, status="active")
    ended_sessions = await pg_store.list_sessions(student_id, status="ended")
    all_sessions = await pg_store.list_sessions(student_id)

    # Assert
    assert len(active_sessions) == 2
    assert all(s.status == "active" for s in active_sessions)

    assert len(ended_sessions) == 3
    assert all(s.status == "ended" for s in ended_sessions)

    assert len(all_sessions) == 5


@pytest.mark.asyncio
async def test_list_sessions_returns_empty_for_unknown_student(pg_store):
    """list_sessions returns [] for a student with no sessions."""
    sessions = await pg_store.list_sessions("unknown_student")
    assert sessions == []


@pytest.mark.asyncio
async def test_get_turns_returns_ordered_transcript(pg_store, pg_engine, student_id):
    """get_turns returns SessionTurns ordered by turn_index ascending."""
    # Create a session
    session_id = "test-session"
    now = datetime.now(timezone.utc)

    async with pg_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO session (session_id, student_id, subject, status, "
                "started_at, last_activity, turn_count) "
                "VALUES (:sid, :student_id, :subject, :status, :started_at, "
                ":last_activity, :turn_count)"
            ),
            {
                "sid": session_id,
                "student_id": student_id,
                "subject": "Mathematics",
                "status": "active",
                "started_at": now,
                "last_activity": now,
                "turn_count": 3,
            },
        )

        # Create turns in non-sequential order to test ordering
        turns_data = [
            (2, "tutor", "Here's another hint", now + timedelta(seconds=20), "AO-003"),
            (0, "user", "I need help with algebra", now, None),
            (1, "tutor", "Let me help you", now + timedelta(seconds=10), "AO-001"),
        ]

        for turn_index, role, content, ts, ao_scaffolded in turns_data:
            await conn.execute(
                text(
                    "INSERT INTO session_turn (session_id, turn_index, role, content, ts, "
                    "ao_scaffolded) VALUES (:sid, :turn_index, :role, :content, :ts, "
                    ":ao_scaffolded)"
                ),
                {
                    "sid": session_id,
                    "turn_index": turn_index,
                    "role": role,
                    "content": content,
                    "ts": ts,
                    "ao_scaffolded": ao_scaffolded,
                },
            )

    # Act
    turns = await pg_store.get_turns(session_id)

    # Assert
    assert len(turns) == 3
    assert turns[0].turn_index == 0
    assert turns[0].role == "user"
    assert turns[0].content == "I need help with algebra"
    assert turns[0].ao_scaffolded is None

    assert turns[1].turn_index == 1
    assert turns[1].role == "tutor"
    assert turns[1].ao_scaffolded == "AO-001"

    assert turns[2].turn_index == 2
    assert turns[2].role == "tutor"
    assert turns[2].ao_scaffolded == "AO-003"


@pytest.mark.asyncio
async def test_get_turns_returns_empty_for_unknown_session(pg_store):
    """get_turns returns [] for unknown session."""
    turns = await pg_store.get_turns("unknown-session")
    assert turns == []


@pytest.mark.asyncio
async def test_get_turns_returns_empty_for_session_with_no_turns(pg_store, pg_engine, student_id):
    """get_turns returns [] for a session with no turns yet."""
    session_id = "empty-session"
    now = datetime.now(timezone.utc)

    async with pg_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO session (session_id, student_id, subject, status, "
                "started_at, last_activity, turn_count) "
                "VALUES (:sid, :student_id, :subject, :status, :started_at, "
                ":last_activity, :turn_count)"
            ),
            {
                "sid": session_id,
                "student_id": student_id,
                "subject": "Mathematics",
                "status": "active",
                "started_at": now,
                "last_activity": now,
                "turn_count": 0,
            },
        )

    # Act
    turns = await pg_store.get_turns(session_id)

    # Assert
    assert turns == []


@pytest.mark.asyncio
async def test_timestamps_are_tz_aware(pg_store, pg_engine, student_id):
    """Timestamps in SessionRecord and SessionTurn are tz-aware UTC."""
    session_id = "tz-test-session"
    now = datetime.now(timezone.utc)

    async with pg_engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO session (session_id, student_id, subject, status, "
                "started_at, last_activity, turn_count) "
                "VALUES (:sid, :student_id, :subject, :status, :started_at, "
                ":last_activity, :turn_count)"
            ),
            {
                "sid": session_id,
                "student_id": student_id,
                "subject": "Mathematics",
                "status": "active",
                "started_at": now,
                "last_activity": now,
                "turn_count": 1,
            },
        )

        await conn.execute(
            text(
                "INSERT INTO session_turn (session_id, turn_index, role, content, ts) "
                "VALUES (:sid, :turn_index, :role, :content, :ts)"
            ),
            {
                "sid": session_id,
                "turn_index": 0,
                "role": "user",
                "content": "Test",
                "ts": now,
            },
        )

    # Act
    sessions = await pg_store.list_sessions(student_id)
    turns = await pg_store.get_turns(session_id)

    # Assert - timestamps are tz-aware UTC
    assert sessions[0].started_at.tzinfo is not None
    assert sessions[0].last_activity.tzinfo is not None
    assert sessions[0].started_at.tzinfo == timezone.utc
    assert sessions[0].last_activity.tzinfo == timezone.utc

    assert turns[0].ts.tzinfo is not None
    assert turns[0].ts.tzinfo == timezone.utc
