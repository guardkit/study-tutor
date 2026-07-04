"""Integration tests for PostgresStudentStore.append_turn and end_session (TASK-SMP3-03).

Tests atomic turn append with turn_count bump and session end transition
over the merged W1 session and session_turn tables.

Runs against an ephemeral PostgreSQL container per Coach Validation section.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from study_tutor.knowledge.store.entities import SessionRecord, SessionTurn
from study_tutor.knowledge.store.postgres import PostgresStudentStore
from study_tutor.session.errors import SessionNotFoundError


@pytest.fixture
async def pg_store_with_session(postgres_container):
    """Provide PostgresStudentStore with a test student and active session."""
    dsn = postgres_container
    store = PostgresStudentStore(dsn)

    # Clean tables and seed test student + session
    engine = create_async_engine(dsn.replace("postgresql://", "postgresql+asyncpg://"))
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM session_turn"))
        await conn.execute(text("DELETE FROM session"))
        await conn.execute(text("DELETE FROM student"))

        # Insert test student
        await conn.execute(
            text(
                "INSERT INTO student (student_id, name, year_group, target_grade, created_at) "
                "VALUES (:student_id, :name, :year_group, :target_grade, :created_at)"
            ),
            {
                "student_id": "alice",
                "name": "Alice Test",
                "year_group": 10,
                "target_grade": "7",
                "created_at": datetime.now(timezone.utc),
            },
        )

        # Insert active session
        now = datetime.now(timezone.utc)
        await conn.execute(
            text(
                "INSERT INTO session "
                "(session_id, student_id, subject, topic, status, "
                "started_at, last_activity, turn_count, xp_awarded, aos_scaffolded, summary) "
                "VALUES (:session_id, :student_id, :subject, :topic, :status, "
                ":started_at, :last_activity, :turn_count, :xp_awarded, :aos_scaffolded, :summary)"
            ),
            {
                "session_id": "test-session-1",
                "student_id": "alice",
                "subject": "Maths",
                "topic": "Algebra",
                "status": "active",
                "started_at": now,
                "last_activity": now,
                "turn_count": 0,
                "xp_awarded": 0,
                "aos_scaffolded": "[]",
                "summary": None,
            },
        )

    await engine.dispose()
    return store, "test-session-1"


@pytest.mark.asyncio
async def test_append_turn_first_turn_at_index_zero(pg_store_with_session):
    """AC1/AC2: First turn is at index 0, bumps turn_count to 1."""
    store, session_id = pg_store_with_session

    before = datetime.now(timezone.utc)
    turn = await store.append_turn(
        session_id=session_id,
        role="user",
        content="What is quadratic formula?",
    )
    after = datetime.now(timezone.utc)

    # Verify returned SessionTurn
    assert isinstance(turn, SessionTurn)
    assert turn.session_id == session_id
    assert turn.turn_index == 0, "First turn should be at index 0"
    assert turn.role == "user"
    assert turn.content == "What is quadratic formula?"
    assert turn.ao_scaffolded is None
    assert turn.ts.tzinfo is not None, "ts must be tz-aware"
    assert before <= turn.ts <= after

    # Verify turn_count was bumped
    updated_session = await store.get_session(session_id)
    assert updated_session is not None
    assert updated_session.turn_count == 1, "turn_count should be bumped to 1"
    assert updated_session.last_activity >= before


@pytest.mark.asyncio
async def test_append_turn_second_turn_at_index_one(pg_store_with_session):
    """AC2: Second turn is at index 1 (monotonic, gap-free)."""
    store, session_id = pg_store_with_session

    # Add first turn
    await store.append_turn(
        session_id=session_id,
        role="user",
        content="First message",
    )

    # Add second turn
    turn2 = await store.append_turn(
        session_id=session_id,
        role="tutor",
        content="Second message",
    )

    assert turn2.turn_index == 1, "Second turn should be at index 1"

    # Verify turn_count
    session = await store.get_session(session_id)
    assert session.turn_count == 2


@pytest.mark.asyncio
async def test_append_turn_with_ao_scaffolded_persists_value(pg_store_with_session):
    """AC3: ao_scaffolded is persisted when supplied."""
    store, session_id = pg_store_with_session

    turn = await store.append_turn(
        session_id=session_id,
        role="tutor",
        content="Let's break this down...",
        ao_scaffolded="worked-example",
    )

    assert turn.ao_scaffolded == "worked-example"

    # Verify persistence by reading back
    turns = await store.get_turns(session_id)
    assert len(turns) == 1
    assert turns[0].ao_scaffolded == "worked-example"


@pytest.mark.asyncio
async def test_append_turn_without_ao_scaffolded_stores_null(pg_store_with_session):
    """AC3: ao_scaffolded is null when not supplied."""
    store, session_id = pg_store_with_session

    turn = await store.append_turn(
        session_id=session_id,
        role="user",
        content="Just a question",
    )

    assert turn.ao_scaffolded is None

    # Verify persistence
    turns = await store.get_turns(session_id)
    assert len(turns) == 1
    assert turns[0].ao_scaffolded is None


@pytest.mark.asyncio
async def test_append_turn_unknown_session_rejected_by_fk(postgres_container):
    """AC4: append_turn on unknown session is rejected (FK constraint)."""
    dsn = postgres_container
    store = PostgresStudentStore(dsn)

    # Try to append turn to non-existent session
    with pytest.raises(Exception) as exc_info:
        await store.append_turn(
            session_id="does-not-exist",
            role="user",
            content="This should fail",
        )

    # Verify it's a database FK violation (not a silent failure)
    # IntegrityError or similar should be raised
    assert "foreign key" in str(exc_info.value).lower() or "constraint" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_append_turn_bumps_last_activity(pg_store_with_session, postgres_container):
    """AC1: append_turn bumps last_activity atomically."""
    store, session_id = pg_store_with_session
    dsn = postgres_container

    # Get initial last_activity
    engine = create_async_engine(dsn.replace("postgresql://", "postgresql+asyncpg://"))
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT last_activity FROM session WHERE session_id = :sid"),
            {"sid": session_id},
        )
        initial_last_activity = result.fetchone()[0]

    # Append turn
    before = datetime.now(timezone.utc)
    await store.append_turn(
        session_id=session_id,
        role="user",
        content="Test message",
    )
    after = datetime.now(timezone.utc)

    # Verify last_activity was updated
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT last_activity FROM session WHERE session_id = :sid"),
            {"sid": session_id},
        )
        updated_last_activity = result.fetchone()[0]

    assert updated_last_activity > initial_last_activity
    assert before <= updated_last_activity <= after

    await engine.dispose()


@pytest.mark.asyncio
async def test_end_session_flips_status_to_ended(pg_store_with_session):
    """AC5: end_session flips status to 'ended' and stamps last_activity."""
    store, session_id = pg_store_with_session

    before = datetime.now(timezone.utc)
    record = await store.end_session(session_id)
    after = datetime.now(timezone.utc)

    # Verify returned record
    assert isinstance(record, SessionRecord)
    assert record.session_id == session_id
    assert record.status == "ended", "Status should be 'ended'"
    assert record.last_activity.tzinfo is not None, "last_activity must be tz-aware"
    assert before <= record.last_activity <= after

    # Verify persistence
    persisted = await store.get_session(session_id)
    assert persisted is not None
    assert persisted.status == "ended"


@pytest.mark.asyncio
async def test_end_session_unknown_session_raises_session_not_found_error(postgres_container):
    """AC6: end_session on unknown session raises SessionNotFoundError."""
    dsn = postgres_container
    store = PostgresStudentStore(dsn)

    with pytest.raises(SessionNotFoundError) as exc_info:
        await store.end_session("unknown-session-id")

    # Verify it's the typed error, not a generic exception
    assert "unknown-session-id" in str(exc_info.value).lower() or "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_end_session_preserves_other_fields(pg_store_with_session):
    """end_session should only update status and last_activity, preserving other fields."""
    store, session_id = pg_store_with_session

    # Add some turns first
    await store.append_turn(session_id=session_id, role="user", content="Q1")
    await store.append_turn(session_id=session_id, role="tutor", content="A1")

    # Get session before ending
    before_end = await store.get_session(session_id)
    assert before_end is not None
    assert before_end.turn_count == 2

    # End session
    ended = await store.end_session(session_id)

    # Verify other fields preserved
    assert ended.student_id == before_end.student_id
    assert ended.subject == before_end.subject
    assert ended.topic == before_end.topic
    assert ended.turn_count == 2, "turn_count should be preserved"
    assert ended.started_at == before_end.started_at


@pytest.mark.asyncio
async def test_append_turn_atomic_transaction(pg_store_with_session, postgres_container):
    """AC1: Verify turn insert and session update happen atomically."""
    store, session_id = pg_store_with_session
    dsn = postgres_container

    # Append a turn
    await store.append_turn(
        session_id=session_id,
        role="user",
        content="Atomic test",
    )

    # Verify both turn exists and session updated
    engine = create_async_engine(dsn.replace("postgresql://", "postgresql+asyncpg://"))
    async with engine.connect() as conn:
        # Check turn was inserted
        turn_result = await conn.execute(
            text("SELECT COUNT(*) FROM session_turn WHERE session_id = :sid"),
            {"sid": session_id},
        )
        turn_count_db = turn_result.scalar()
        assert turn_count_db == 1

        # Check session turn_count was updated
        session_result = await conn.execute(
            text("SELECT turn_count FROM session WHERE session_id = :sid"),
            {"sid": session_id},
        )
        session_turn_count = session_result.scalar()
        assert session_turn_count == 1

    await engine.dispose()


@pytest.mark.asyncio
async def test_timestamps_are_utc_aware(pg_store_with_session):
    """AC7: Verify ts and last_activity are tz-aware UTC."""
    store, session_id = pg_store_with_session

    turn = await store.append_turn(
        session_id=session_id,
        role="user",
        content="Timezone test",
    )

    assert turn.ts.tzinfo is not None, "turn.ts must be tz-aware"
    assert turn.ts.tzinfo.tzname(None) == "UTC", "turn.ts must be UTC"

    session = await store.get_session(session_id)
    assert session.last_activity.tzinfo is not None, "last_activity must be tz-aware"
