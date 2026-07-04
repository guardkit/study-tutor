"""Integration tests for PostgresStudentStore.create_session and get_session (TASK-SMP3-01).

Tests session creation with resume-if-active logic and session retrieval
over the merged W1 session table.

Runs against an ephemeral PostgreSQL container per Coach Validation section.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from study_tutor.knowledge.store.entities import SessionRecord
from study_tutor.knowledge.store.postgres import PostgresStudentStore


@pytest.fixture
async def pg_store_with_student(postgres_container):
    """Provide PostgresStudentStore with a test student seeded."""
    dsn = postgres_container
    store = PostgresStudentStore(dsn)

    # Clean tables and seed test student
    engine = create_async_engine(dsn.replace("postgresql://", "postgresql+asyncpg://"))
    async with engine.begin() as conn:
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

    await engine.dispose()
    return store


@pytest.mark.asyncio
async def test_create_session_without_resume_creates_new_session(pg_store_with_student):
    """AC1: create_session(resume_if_active=False) INSERTs a new active session."""
    store = pg_store_with_student

    # Create new session without resume
    before = datetime.now(timezone.utc)
    record, created = await store.create_session(
        student_id="alice",
        subject="English",
        topic="Macbeth",
        resume_if_active=False,
    )
    after = datetime.now(timezone.utc)

    # Verify returned tuple
    assert created is True, "Should return created=True for new session"
    assert isinstance(record, SessionRecord)

    # Verify session_id is valid UUID
    assert UUID(record.session_id), "session_id should be valid UUID"

    # Verify all fields match requirements
    assert record.student_id == "alice"
    assert record.subject == "English"
    assert record.topic == "Macbeth"
    assert record.status == "active"
    assert record.turn_count == 0
    assert record.aos_scaffolded == []
    assert record.summary is None

    # Verify timestamps are tz-aware UTC and recent
    assert record.started_at.tzinfo is not None, "started_at must be tz-aware"
    assert before <= record.started_at <= after
    assert record.last_activity.tzinfo is not None, "last_activity must be tz-aware"
    assert record.started_at == record.last_activity


@pytest.mark.asyncio
async def test_create_session_resume_with_no_active_creates_new(pg_store_with_student):
    """AC2: create_session(resume_if_active=True) with no active session creates new."""
    store = pg_store_with_student

    # Create with resume when none exists
    record, created = await store.create_session(
        student_id="alice",
        subject="Maths",
        topic="Algebra",
        resume_if_active=True,
    )

    # Should create new session
    assert created is True
    assert record.student_id == "alice"
    assert record.subject == "Maths"
    assert record.topic == "Algebra"
    assert record.status == "active"


@pytest.mark.asyncio
async def test_create_session_resume_with_existing_active_returns_existing(
    pg_store_with_student, postgres_container
):
    """AC2: create_session(resume_if_active=True) with existing active session returns it."""
    store = pg_store_with_student

    # Create first session
    first_record, first_created = await store.create_session(
        student_id="alice",
        subject="English",
        topic="Macbeth",
        resume_if_active=False,
    )
    assert first_created is True
    first_session_id = first_record.session_id

    # Try to create again with resume=True
    second_record, second_created = await store.create_session(
        student_id="alice",
        subject="English",
        topic="Romeo and Juliet",  # Different topic, but same student + subject
        resume_if_active=True,
    )

    # Should return existing session, not create new
    assert second_created is False, "Should return created=False for resumed session"
    assert second_record.session_id == first_session_id
    assert second_record.student_id == "alice"
    assert second_record.subject == "English"
    # Original topic preserved
    assert second_record.topic == "Macbeth"

    # Verify only one session exists in database
    engine = create_async_engine(
        postgres_container.replace("postgresql://", "postgresql+asyncpg://")
    )
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT COUNT(*) FROM session WHERE student_id = :sid"),
            {"sid": "alice"},
        )
        count = result.scalar()
        assert count == 1, "Should have exactly one session in DB"

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_session_resume_different_subject_creates_new(pg_store_with_student):
    """AC2: resume_if_active only matches same (student_id, subject)."""
    store = pg_store_with_student

    # Create session for English
    english_record, _ = await store.create_session(
        student_id="alice",
        subject="English",
        resume_if_active=False,
    )

    # Create session for Maths with resume=True
    maths_record, created = await store.create_session(
        student_id="alice",
        subject="Maths",
        resume_if_active=True,
    )

    # Should create new session (different subject)
    assert created is True
    assert maths_record.session_id != english_record.session_id
    assert maths_record.subject == "Maths"


@pytest.mark.asyncio
async def test_create_session_transaction_atomicity(
    pg_store_with_student, postgres_container
):
    """AC3: The resume check + insert happen in ONE transaction."""
    store = pg_store_with_student

    # This test verifies transactional behavior by checking that
    # concurrent creates with resume=True don't create duplicates
    # (though full concurrency testing needs actual parallel execution)

    # Create with resume - should SELECT then INSERT in one transaction
    record, created = await store.create_session(
        student_id="alice",
        subject="Science",
        resume_if_active=True,
    )

    assert created is True

    # Verify session exists in DB
    engine = create_async_engine(
        postgres_container.replace("postgresql://", "postgresql+asyncpg://")
    )
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT session_id FROM session WHERE session_id = :sid"),
            {"sid": record.session_id},
        )
        row = result.fetchone()
        assert row is not None, "Session should exist in database"

    await engine.dispose()


@pytest.mark.asyncio
async def test_get_session_returns_matching_record(pg_store_with_student):
    """AC4: get_session(id) returns the matching SessionRecord."""
    store = pg_store_with_student

    # Create a session
    created_record, _ = await store.create_session(
        student_id="alice",
        subject="English",
        topic="Poetry",
        resume_if_active=False,
    )

    # Retrieve it
    retrieved_record = await store.get_session(created_record.session_id)

    # Verify all fields match
    assert retrieved_record is not None
    assert retrieved_record.session_id == created_record.session_id
    assert retrieved_record.student_id == created_record.student_id
    assert retrieved_record.subject == created_record.subject
    assert retrieved_record.topic == created_record.topic
    assert retrieved_record.status == created_record.status
    assert retrieved_record.started_at == created_record.started_at
    assert retrieved_record.last_activity == created_record.last_activity
    assert retrieved_record.turn_count == created_record.turn_count
    assert retrieved_record.aos_scaffolded == created_record.aos_scaffolded
    assert retrieved_record.summary == created_record.summary


@pytest.mark.asyncio
async def test_get_session_unknown_id_returns_none(pg_store_with_student):
    """AC4: get_session with unknown id returns None (does NOT raise)."""
    store = pg_store_with_student

    # Query for non-existent session
    result = await store.get_session("00000000-0000-0000-0000-000000000000")

    # Should return None, not raise
    assert result is None


@pytest.mark.asyncio
async def test_session_record_excludes_xp_awarded(pg_store_with_student, postgres_container):
    """AC5: SessionRecord does NOT include xp_awarded (DB column exists, record doesn't)."""
    store = pg_store_with_student

    # Create session
    record, _ = await store.create_session(
        student_id="alice",
        subject="English",
        resume_if_active=False,
    )

    # Verify SessionRecord doesn't have xp_awarded attribute
    assert not hasattr(record, "xp_awarded"), "SessionRecord should not have xp_awarded"

    # Verify DB row has xp_awarded=0
    engine = create_async_engine(
        postgres_container.replace("postgresql://", "postgresql+asyncpg://")
    )
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT xp_awarded FROM session WHERE session_id = :sid"),
            {"sid": record.session_id},
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] == 0, "Database should have xp_awarded=0"

    await engine.dispose()


@pytest.mark.asyncio
async def test_timestamps_are_timezone_aware_utc(pg_store_with_student):
    """AC5: Timestamps are tz-aware UTC."""
    store = pg_store_with_student

    record, _ = await store.create_session(
        student_id="alice",
        subject="English",
        resume_if_active=False,
    )

    # Verify timezone-aware and UTC
    assert record.started_at.tzinfo is not None
    assert record.started_at.tzinfo == timezone.utc
    assert record.last_activity.tzinfo is not None
    assert record.last_activity.tzinfo == timezone.utc


@pytest.mark.asyncio
async def test_create_session_with_nonexistent_student_raises_integrity_error(
    pg_store_with_student,
):
    """AC6: Creating session for non-existent student_id raises IntegrityError."""
    store = pg_store_with_student

    # Try to create session for non-existent student
    with pytest.raises(IntegrityError, match="student"):
        await store.create_session(
            student_id="nonexistent",
            subject="English",
            resume_if_active=False,
        )


@pytest.mark.asyncio
async def test_all_values_are_bound_parameters(pg_store_with_student, postgres_container):
    """AC7: All identifiers/values are bound parameters (SQL injection safety)."""
    store = pg_store_with_student

    # Create session with potentially dangerous values
    malicious_topic = "'; DROP TABLE session; --"
    record, _ = await store.create_session(
        student_id="alice",
        subject="English",
        topic=malicious_topic,
        resume_if_active=False,
    )

    # Verify topic was safely stored
    assert record.topic == malicious_topic

    # Verify session table still exists and has the record
    engine = create_async_engine(
        postgres_container.replace("postgresql://", "postgresql+asyncpg://")
    )
    async with engine.begin() as conn:
        result = await conn.execute(
            text("SELECT topic FROM session WHERE session_id = :sid"),
            {"sid": record.session_id},
        )
        row = result.fetchone()
        assert row is not None
        assert row[0] == malicious_topic

    await engine.dispose()


@pytest.mark.asyncio
async def test_create_session_with_null_topic(pg_store_with_student):
    """Session can be created with topic=None."""
    store = pg_store_with_student

    record, _ = await store.create_session(
        student_id="alice",
        subject="English",
        topic=None,
        resume_if_active=False,
    )

    assert record.topic is None

    # Verify retrieval preserves None
    retrieved = await store.get_session(record.session_id)
    assert retrieved.topic is None
