"""Integration tests for PostgresStudentStore.get_student_state (TASK-SMP2-03).

Tests the aggregate learner snapshot: reads from student, topic_confidence,
misconception, and session tables to build a complete StudentState.

Runs against an ephemeral PostgreSQL container per Coach Validation section.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from study_tutor.knowledge.store.entities import (
    MisconceptionSnapshot,
    StudentState,
    TopicConfidenceSnapshot,
)
from study_tutor.knowledge.store.postgres import PostgresStudentStore


@pytest.fixture
async def pg_store_with_full_data(postgres_container):
    """Provide PostgresStudentStore with student, confidences, misconceptions, and sessions."""
    dsn = postgres_container
    store = PostgresStudentStore(dsn)

    # Clean tables and seed comprehensive test data
    engine = create_async_engine(dsn.replace("postgresql://", "postgresql+asyncpg://"))
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM session"))
        await conn.execute(text("DELETE FROM misconception"))
        await conn.execute(text("DELETE FROM topic_confidence"))
        await conn.execute(text("DELETE FROM student"))

        # Insert test student
        await conn.execute(
            text(
                "INSERT INTO student (student_id, name, year_group, target_grade, created_at) "
                "VALUES (:student_id, :name, :year_group, :target_grade, :created_at)"
            ),
            {
                "student_id": "lilymay",
                "name": "Lily May",
                "year_group": 10,
                "target_grade": "7",
                "created_at": datetime.now(timezone.utc),
            },
        )

        # Insert topic confidences
        base_time = datetime.now(timezone.utc) - timedelta(days=5)
        await conn.execute(
            text(
                "INSERT INTO topic_confidence (student_id, topic_name, percentage, band, last_revised_at) "
                "VALUES (:student_id, :topic_name, :percentage, :band, :last_revised_at)"
            ),
            {
                "student_id": "lilymay",
                "topic_name": "Macbeth Themes",
                "percentage": 72,
                "band": "secure",
                "last_revised_at": base_time,
            },
        )

        await conn.execute(
            text(
                "INSERT INTO topic_confidence (student_id, topic_name, percentage, band, last_revised_at) "
                "VALUES (:student_id, :topic_name, :percentage, :band, :last_revised_at)"
            ),
            {
                "student_id": "lilymay",
                "topic_name": "Power & Conflict Poetry",
                "percentage": 45,
                "band": "developing",
                "last_revised_at": base_time + timedelta(hours=1),
            },
        )

        # Insert recent misconceptions (within 30-day window)
        recent_time = datetime.now(timezone.utc) - timedelta(days=10)
        await conn.execute(
            text(
                "INSERT INTO misconception (student_id, topic_name, text, observed_at) "
                "VALUES (:student_id, :topic_name, :text, :observed_at)"
            ),
            {
                "student_id": "lilymay",
                "topic_name": "Macbeth Themes",
                "text": "Confused ambition with guilt",
                "observed_at": recent_time,
            },
        )

        # Insert old misconception (outside 30-day window)
        old_time = datetime.now(timezone.utc) - timedelta(days=35)
        await conn.execute(
            text(
                "INSERT INTO misconception (student_id, topic_name, text, observed_at) "
                "VALUES (:student_id, :topic_name, :text, :observed_at)"
            ),
            {
                "student_id": "lilymay",
                "topic_name": "Power & Conflict Poetry",
                "text": "Old misconception outside window",
                "observed_at": old_time,
            },
        )

        # Insert sessions with different last_activity timestamps
        session_time_1 = datetime.now(timezone.utc) - timedelta(days=2)
        await conn.execute(
            text(
                "INSERT INTO session (session_id, student_id, subject, topic, status, "
                "started_at, last_activity, turn_count, xp_awarded, aos_scaffolded) "
                "VALUES (:session_id, :student_id, :subject, :topic, :status, "
                ":started_at, :last_activity, :turn_count, :xp_awarded, CAST(:aos_scaffolded AS JSONB))"
            ),
            {
                "session_id": "sess-001",
                "student_id": "lilymay",
                "subject": "English",
                "topic": "Macbeth",
                "status": "ended",
                "started_at": session_time_1,
                "last_activity": session_time_1,
                "turn_count": 5,
                "xp_awarded": 100,
                "aos_scaffolded": json.dumps([]),
            },
        )

        # Most recent session
        session_time_2 = datetime.now(timezone.utc) - timedelta(hours=1)
        await conn.execute(
            text(
                "INSERT INTO session (session_id, student_id, subject, topic, status, "
                "started_at, last_activity, turn_count, xp_awarded, aos_scaffolded) "
                "VALUES (:session_id, :student_id, :subject, :topic, :status, "
                ":started_at, :last_activity, :turn_count, :xp_awarded, CAST(:aos_scaffolded AS JSONB))"
            ),
            {
                "session_id": "sess-002",
                "student_id": "lilymay",
                "subject": "English",
                "topic": "Poetry",
                "status": "active",
                "started_at": session_time_2,
                "last_activity": session_time_2,
                "turn_count": 3,
                "xp_awarded": 50,
                "aos_scaffolded": json.dumps([]),
            },
        )

    yield store
    await engine.dispose()


class TestKnownLearnerProfile:
    """AC-001: Known learner returns StudentState with profile data."""

    @pytest.mark.asyncio
    async def test_known_learner_returns_student_state(self, pg_store_with_full_data):
        """get_student_state returns StudentState with student profile for known learner."""
        result = await pg_store_with_full_data.get_student_state("lilymay")

        assert isinstance(result, StudentState)
        assert result.empty is False
        assert result.student_id == "lilymay"
        assert result.year_group == 10
        assert result.target_grade == "7"

    @pytest.mark.asyncio
    async def test_stale_always_false(self, pg_store_with_full_data):
        """stale field is always False (Graphiti-era flag retired)."""
        result = await pg_store_with_full_data.get_student_state("lilymay")

        assert result.stale is False


class TestTopicConfidencesAndMisconceptions:
    """AC-002: topic_confidences and recent_misconceptions populated correctly."""

    @pytest.mark.asyncio
    async def test_topic_confidences_populated(self, pg_store_with_full_data):
        """topic_confidences contains TopicConfidenceSnapshot entries."""
        result = await pg_store_with_full_data.get_student_state("lilymay")

        assert len(result.topic_confidences) == 2
        assert all(
            isinstance(tc, TopicConfidenceSnapshot) for tc in result.topic_confidences
        )

        # Verify field mapping (uses topic_name, not topic_ref)
        topic_names = {tc.topic_name for tc in result.topic_confidences}
        assert topic_names == {"Macbeth Themes", "Power & Conflict Poetry"}

        # Verify fields match what get_topic_confidences would return
        macbeth = next(
            tc for tc in result.topic_confidences if tc.topic_name == "Macbeth Themes"
        )
        assert macbeth.percentage == 72
        assert macbeth.band == "secure"
        assert macbeth.last_revised_at is not None

    @pytest.mark.asyncio
    async def test_recent_misconceptions_populated(self, pg_store_with_full_data):
        """recent_misconceptions contains MisconceptionSnapshot entries."""
        result = await pg_store_with_full_data.get_student_state("lilymay")

        # Only recent misconception (within 30-day window) should appear
        assert len(result.recent_misconceptions) == 1
        assert all(
            isinstance(m, MisconceptionSnapshot) for m in result.recent_misconceptions
        )

        misc = result.recent_misconceptions[0]
        assert misc.topic_name == "Macbeth Themes"
        assert misc.text == "Confused ambition with guilt"
        assert misc.observed_at is not None
        # MisconceptionSnapshot has NO band field (different from domain Misconception)
        assert not hasattr(misc, "confidence_band_at_observation")


class TestMisconceptionWindow:
    """AC-003: recent_misconceptions uses 30-day inclusive window."""

    @pytest.mark.asyncio
    async def test_30_day_window_applied(self, pg_store_with_full_data):
        """Only misconceptions within 30-day window are included."""
        result = await pg_store_with_full_data.get_student_state("lilymay")

        # We inserted 2 misconceptions: one at day-10 (recent), one at day-35 (old)
        # Only the recent one should appear
        assert len(result.recent_misconceptions) == 1
        assert result.recent_misconceptions[0].text == "Confused ambition with guilt"


class TestMostRecentSession:
    """AC-004: most_recent_session_id from session table by last_activity."""

    @pytest.mark.asyncio
    async def test_most_recent_session_id(self, pg_store_with_full_data):
        """most_recent_session_id is session with greatest last_activity."""
        result = await pg_store_with_full_data.get_student_state("lilymay")

        # sess-002 has last_activity 1 hour ago (most recent)
        assert result.most_recent_session_id == "sess-002"

    @pytest.mark.asyncio
    async def test_no_sessions_returns_none(self, postgres_container):
        """most_recent_session_id is None when student has no sessions."""
        dsn = postgres_container
        store = PostgresStudentStore(dsn)

        # Create student with no sessions
        engine = create_async_engine(
            dsn.replace("postgresql://", "postgresql+asyncpg://")
        )
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM session"))
            await conn.execute(text("DELETE FROM student"))

            await conn.execute(
                text(
                    "INSERT INTO student (student_id, name, year_group, target_grade, created_at) "
                    "VALUES (:student_id, :name, :year_group, :target_grade, :created_at)"
                ),
                {
                    "student_id": "no_sessions",
                    "name": "No Sessions",
                    "year_group": 9,
                    "target_grade": "6",
                    "created_at": datetime.now(timezone.utc),
                },
            )

        result = await store.get_student_state("no_sessions")

        assert result.most_recent_session_id is None
        await engine.dispose()


class TestUnmodeledFields:
    """AC-005: subjects/current_texts always empty, stale always False."""

    @pytest.mark.asyncio
    async def test_subjects_current_texts_empty(self, pg_store_with_full_data):
        """subjects and current_texts are always empty lists."""
        result = await pg_store_with_full_data.get_student_state("lilymay")

        assert result.subjects == []
        assert result.current_texts == []


class TestUnknownStudent:
    """AC-006: Unknown student_id returns empty=True."""

    @pytest.mark.asyncio
    async def test_unknown_student_returns_empty(self, postgres_container):
        """Unknown student_id returns StudentState(empty=True)."""
        dsn = postgres_container
        store = PostgresStudentStore(dsn)

        result = await store.get_student_state("unknown_student")

        assert result.empty is True
        # Callers can branch on empty without inspecting other fields
        assert isinstance(result, StudentState)


class TestTimezoneAware:
    """AC-007: All timestamps are timezone-aware UTC."""

    @pytest.mark.asyncio
    async def test_timestamps_are_utc_aware(self, pg_store_with_full_data):
        """All datetime fields are timezone-aware UTC."""
        result = await pg_store_with_full_data.get_student_state("lilymay")

        # Check topic_confidences timestamps
        for tc in result.topic_confidences:
            if tc.last_revised_at is not None:
                assert tc.last_revised_at.tzinfo is not None
                assert tc.last_revised_at.tzinfo == timezone.utc

        # Check misconceptions timestamps
        for misc in result.recent_misconceptions:
            assert misc.observed_at.tzinfo is not None
            assert misc.observed_at.tzinfo == timezone.utc
