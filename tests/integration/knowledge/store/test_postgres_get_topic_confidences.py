"""Integration tests for PostgresStudentStore.get_topic_confidences (TASK-SMP2-01).

Tests read path: SELECT from topic_confidence with ordering, band read-back,
empty list handling, UTC timestamp preservation, and SQL injection protection.

Runs against an ephemeral PostgreSQL container (non-5434 port) per Coach
Validation section.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from study_tutor.knowledge.store.postgres import PostgresStudentStore
from study_tutor.knowledge.student_model import TopicConfidence


@pytest.fixture
async def pg_store_with_data(postgres_container):
    """Provide a PostgresStudentStore with pre-seeded topic confidence data."""
    dsn = postgres_container
    store = PostgresStudentStore(dsn)

    # Clean tables and seed test data
    engine = create_async_engine(dsn.replace("postgresql://", "postgresql+asyncpg://"))
    async with engine.begin() as conn:
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

        # Insert topic confidences with different timestamps for ordering test
        base_time = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

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
                "last_revised_at": base_time.replace(hour=13),  # 1 hour later
            },
        )

        await conn.execute(
            text(
                "INSERT INTO topic_confidence (student_id, topic_name, percentage, band, last_revised_at) "
                "VALUES (:student_id, :topic_name, :percentage, :band, :last_revised_at)"
            ),
            {
                "student_id": "lilymay",
                "topic_name": "An Inspector Calls",
                "percentage": 85,
                "band": "mastered",
                "last_revised_at": base_time.replace(hour=11),  # 1 hour earlier
            },
        )

    yield store

    await engine.dispose()


class TestGetTopicConfidences:
    """AC-001: Returns one TopicConfidence per row with correct field mapping."""

    @pytest.mark.asyncio
    async def test_returns_topic_confidences_for_student(self, pg_store_with_data):
        """get_topic_confidences returns TopicConfidence entities for student."""
        result = await pg_store_with_data.get_topic_confidences("lilymay")

        assert len(result) == 3
        assert all(isinstance(tc, TopicConfidence) for tc in result)

        # Verify field mapping: student_ref, topic_ref, percentage, band, last_revised_at
        topic_names = {tc.topic_ref for tc in result}
        assert topic_names == {"Macbeth Themes", "Power & Conflict Poetry", "An Inspector Calls"}

        # All should have student_ref = "lilymay"
        assert all(tc.student_ref == "lilymay" for tc in result)


class TestOrdering:
    """AC-002: Rows ordered by newest last_revised_at first."""

    @pytest.mark.asyncio
    async def test_ordered_by_last_revised_at_desc(self, pg_store_with_data):
        """Results are ordered newest last_revised_at first."""
        result = await pg_store_with_data.get_topic_confidences("lilymay")

        assert len(result) == 3
        # Should be: Power & Conflict (13:00), Macbeth (12:00), Inspector (11:00)
        assert result[0].topic_ref == "Power & Conflict Poetry"
        assert result[1].topic_ref == "Macbeth Themes"
        assert result[2].topic_ref == "An Inspector Calls"

        # Verify timestamps are descending
        for i in range(len(result) - 1):
            assert result[i].last_revised_at >= result[i + 1].last_revised_at


class TestBandReadBack:
    """AC-003: Stored band is returned verbatim (read-back matches write)."""

    @pytest.mark.asyncio
    async def test_band_read_back_verbatim(self, pg_store_with_data):
        """Band column read back matches stored value (no re-derivation)."""
        result = await pg_store_with_data.get_topic_confidences("lilymay")

        # Find each topic and verify band matches what was stored
        macbeth = next(tc for tc in result if tc.topic_ref == "Macbeth Themes")
        assert macbeth.percentage == 72
        assert macbeth.band == "secure"  # Stored as secure, read back as secure

        poetry = next(tc for tc in result if tc.topic_ref == "Power & Conflict Poetry")
        assert poetry.percentage == 45
        assert poetry.band == "developing"  # Stored as developing, read back as developing

        inspector = next(tc for tc in result if tc.topic_ref == "An Inspector Calls")
        assert inspector.percentage == 85
        assert inspector.band == "mastered"  # Stored as mastered, read back as mastered


class TestEmptyResults:
    """AC-004 & AC-005: Empty list for zero rows or unknown student."""

    @pytest.mark.asyncio
    async def test_student_with_no_rows_returns_empty_list(self, postgres_container):
        """Student with zero topic_confidence rows returns []."""
        dsn = postgres_container
        store = PostgresStudentStore(dsn)

        # Create student with no topic confidences
        engine = create_async_engine(dsn.replace("postgresql://", "postgresql+asyncpg://"))
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM topic_confidence"))
            await conn.execute(text("DELETE FROM student"))

            await conn.execute(
                text(
                    "INSERT INTO student (student_id, name, year_group, target_grade, created_at) "
                    "VALUES (:student_id, :name, :year_group, :target_grade, :created_at)"
                ),
                {
                    "student_id": "empty_student",
                    "name": "Empty Student",
                    "year_group": 10,
                    "target_grade": "5",
                    "created_at": datetime.now(timezone.utc),
                },
            )

        result = await store.get_topic_confidences("empty_student")
        assert result == []

        await engine.dispose()

    @pytest.mark.asyncio
    async def test_unknown_student_returns_empty_list(self, postgres_container):
        """Unknown student_id returns [] (no pre-check required)."""
        dsn = postgres_container
        store = PostgresStudentStore(dsn)

        result = await store.get_topic_confidences("unknown_student_xyz")
        assert result == []


class TestUtcTimestamps:
    """AC-006: last_revised_at returned as timezone-aware UTC datetime."""

    @pytest.mark.asyncio
    async def test_timestamp_is_utc_aware(self, pg_store_with_data):
        """Returned last_revised_at is timezone-aware UTC."""
        result = await pg_store_with_data.get_topic_confidences("lilymay")

        assert len(result) > 0
        for tc in result:
            # Verify timezone info is UTC
            assert tc.last_revised_at.tzinfo == timezone.utc
            # Verify it's a datetime
            assert isinstance(tc.last_revised_at, datetime)


class TestParameterBinding:
    """AC-007: student_id passed as bound parameter (SQL injection protection)."""

    @pytest.mark.asyncio
    async def test_sql_injection_protection(self, pg_store_with_data):
        """Malicious student_id is treated as literal, not SQL."""
        malicious_id = "lilymay' OR '1'='1"

        # Should return empty (no student with this exact ID), not all rows
        result = await pg_store_with_data.get_topic_confidences(malicious_id)
        assert result == []


class TestErrorPropagation:
    """AC-008: DB/connection errors are NOT swallowed (propagate to caller)."""

    @pytest.mark.asyncio
    async def test_connection_error_propagates(self):
        """Database connection error propagates (not swallowed)."""
        # Create store with invalid DSN
        store = PostgresStudentStore("postgresql://invalid:invalid@localhost:99999/invalid")

        # Should raise an exception, not return []
        with pytest.raises(Exception):  # Could be connection error or timeout
            await store.get_topic_confidences("student_id")
