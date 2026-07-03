"""Integration tests for PostgresStudentStore.apply_confidence_update (TASK-SMP-04).

Tests F2 write path: UPSERT into topic_confidence with band derivation,
range validation, FK enforcement, UTC timestamps, concurrency, and SQL injection
protection.

Runs against an ephemeral PostgreSQL container (non-5434 port) per Coach
Validation section.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import create_async_engine

from study_tutor.knowledge.store.entities import ConfidenceUpdate
from study_tutor.knowledge.store.postgres import PostgresStudentStore
from study_tutor.knowledge.student_model import EPOCH_NEVER_REVISED


@pytest.fixture
async def pg_store(postgres_container):
    """Provide a PostgresStudentStore connected to ephemeral test database."""
    dsn = postgres_container
    store = PostgresStudentStore(dsn)

    # Clean tables before each test
    engine = create_async_engine(dsn.replace("postgresql://", "postgresql+asyncpg://"))
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM topic_confidence"))
        await conn.execute(text("DELETE FROM student"))

    # Insert test student
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "INSERT INTO student (student_id, name, year_group, target_grade, created_at) "
                "VALUES (:student_id, :name, :year_group, :target_grade, :created_at)"
            ),
            {
                "student_id": "test_student",
                "name": "Test Student",
                "year_group": 10,
                "target_grade": "7",
                "created_at": datetime.now(timezone.utc),
            },
        )

    yield store

    await engine.dispose()


@pytest.fixture
async def pg_engine(postgres_container):
    """Provide direct engine access for test verification."""
    dsn = postgres_container
    engine = create_async_engine(dsn.replace("postgresql://", "postgresql+asyncpg://"))
    yield engine
    await engine.dispose()


class TestApplyConfidenceUpdate:
    """AC-001: UPSERT with ON CONFLICT DO UPDATE."""

    @pytest.mark.asyncio
    async def test_insert_new_topic_confidence(self, pg_store, pg_engine):
        """First update for a topic inserts a new row."""
        update = ConfidenceUpdate(topic_name="Macbeth Themes", percentage=75)

        await pg_store.apply_confidence_update(student_id="test_student", update=update)

        # Verify row was inserted
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT topic_name, percentage, band FROM topic_confidence "
                    "WHERE student_id = :student_id AND topic_name = :topic_name"
                ),
                {"student_id": "test_student", "topic_name": "Macbeth Themes"},
            )
            row = result.fetchone()
            assert row is not None
            assert row[0] == "Macbeth Themes"
            assert row[1] == 75
            assert row[2] == "secure"

    @pytest.mark.asyncio
    async def test_update_existing_topic_confidence(self, pg_store, pg_engine):
        """Second update for same topic updates the existing row (last write wins)."""
        # First update
        await pg_store.apply_confidence_update(
            student_id="test_student",
            update=ConfidenceUpdate(topic_name="Macbeth Themes", percentage=40),
        )

        # Second update (should overwrite)
        await pg_store.apply_confidence_update(
            student_id="test_student",
            update=ConfidenceUpdate(topic_name="Macbeth Themes", percentage=85),
        )

        # Verify only one row exists with latest value
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT percentage, band FROM topic_confidence "
                    "WHERE student_id = :student_id AND topic_name = :topic_name"
                ),
                {"student_id": "test_student", "topic_name": "Macbeth Themes"},
            )
            rows = result.fetchall()
            assert len(rows) == 1
            assert rows[0][0] == 85
            assert rows[0][1] == "mastered"


class TestBandDerivation:
    """AC-002: Band derived at write time matches 40/60/80 taxonomy."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "percentage,expected_band",
        [
            (0, "struggling"),
            (39, "struggling"),
            (40, "developing"),
            (59, "developing"),
            (60, "secure"),
            (79, "secure"),
            (80, "mastered"),
            (100, "mastered"),
        ],
    )
    async def test_band_boundaries(self, pg_store, pg_engine, percentage, expected_band):
        """Band derivation respects 40/60/80 boundaries."""
        await pg_store.apply_confidence_update(
            student_id="test_student",
            update=ConfidenceUpdate(topic_name="Test Topic", percentage=percentage),
        )

        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT band FROM topic_confidence "
                    "WHERE student_id = :student_id AND topic_name = :topic_name"
                ),
                {"student_id": "test_student", "topic_name": "Test Topic"},
            )
            row = result.fetchone()
            assert row[0] == expected_band


class TestPercentageValidation:
    """AC-003: Percentage outside [0, 100] rejected with ValueError."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("invalid_percentage", [-1, 101, -10, 150])
    async def test_reject_invalid_percentage(self, pg_store, pg_engine, invalid_percentage):
        """Invalid percentages raise ValueError and insert nothing."""
        with pytest.raises(ValueError):
            await pg_store.apply_confidence_update(
                student_id="test_student",
                update=ConfidenceUpdate(topic_name="Test", percentage=invalid_percentage),
            )

        # Verify no row was created
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT COUNT(*) FROM topic_confidence WHERE student_id = :student_id"),
                {"student_id": "test_student"},
            )
            count = result.scalar()
            assert count == 0


class TestUtcTimestamps:
    """AC-004: last_revised_at stored as timezone-aware UTC."""

    @pytest.mark.asyncio
    async def test_timestamp_is_utc_aware(self, pg_store, pg_engine):
        """Stored timestamp is UTC and timezone-aware."""
        before = datetime.now(timezone.utc)

        await pg_store.apply_confidence_update(
            student_id="test_student",
            update=ConfidenceUpdate(topic_name="Test", percentage=50),
        )

        after = datetime.now(timezone.utc)

        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT last_revised_at FROM topic_confidence "
                    "WHERE student_id = :student_id AND topic_name = :topic_name"
                ),
                {"student_id": "test_student", "topic_name": "Test"},
            )
            row = result.fetchone()
            stored_ts = row[0]

            # Verify timestamp is between before and after
            assert before <= stored_ts <= after
            # Verify timezone info is UTC
            assert stored_ts.tzinfo == timezone.utc


class TestSentinelOverwrite:
    """AC-005: First update overwrites EPOCH_NEVER_REVISED sentinel."""

    @pytest.mark.asyncio
    async def test_overwrite_sentinel_timestamp(self, pg_store, pg_engine):
        """First real update overwrites EPOCH_NEVER_REVISED baseline."""
        # Seed baseline with sentinel
        async with pg_engine.begin() as conn:
            await conn.execute(
                text(
                    "INSERT INTO topic_confidence "
                    "(student_id, topic_name, percentage, band, last_revised_at) "
                    "VALUES (:student_id, :topic_name, :percentage, :band, :last_revised_at)"
                ),
                {
                    "student_id": "test_student",
                    "topic_name": "Baseline Topic",
                    "percentage": 50,
                    "band": "developing",
                    "last_revised_at": EPOCH_NEVER_REVISED,
                },
            )

        # Apply real update
        await pg_store.apply_confidence_update(
            student_id="test_student",
            update=ConfidenceUpdate(topic_name="Baseline Topic", percentage=70),
        )

        # Verify sentinel was overwritten
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT last_revised_at FROM topic_confidence "
                    "WHERE student_id = :student_id AND topic_name = :topic_name"
                ),
                {"student_id": "test_student", "topic_name": "Baseline Topic"},
            )
            row = result.fetchone()
            stored_ts = row[0]

            assert stored_ts > EPOCH_NEVER_REVISED


class TestForeignKeyRejection:
    """AC-006: FK rejection for unknown student_id."""

    @pytest.mark.asyncio
    async def test_reject_unknown_student(self, pg_store, pg_engine):
        """Write for unknown student_id raises IntegrityError and inserts nothing."""
        with pytest.raises(IntegrityError):
            await pg_store.apply_confidence_update(
                student_id="unknown_student",
                update=ConfidenceUpdate(topic_name="Test", percentage=50),
            )

        # Verify no row was created
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT COUNT(*) FROM topic_confidence "
                    "WHERE student_id = :student_id"
                ),
                {"student_id": "unknown_student"},
            )
            count = result.scalar()
            assert count == 0


class TestSqlInjectionProtection:
    """AC-007: SQL injection protection via bound parameters."""

    @pytest.mark.asyncio
    async def test_malicious_topic_name_stored_verbatim(self, pg_store, pg_engine):
        """Control characters and SQL metacharacters stored as literal text."""
        malicious_topic = "Macbeth'); DROP TABLE topic_confidence;--"

        await pg_store.apply_confidence_update(
            student_id="test_student",
            update=ConfidenceUpdate(topic_name=malicious_topic, percentage=60),
        )

        # Verify topic_confidence table still exists and has the row
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT topic_name FROM topic_confidence "
                    "WHERE student_id = :student_id AND topic_name = :topic_name"
                ),
                {"student_id": "test_student", "topic_name": malicious_topic},
            )
            row = result.fetchone()
            assert row is not None
            assert row[0] == malicious_topic


class TestConcurrentUpdates:
    """AC-008: Concurrent updates resolve via ON CONFLICT (last write wins)."""

    @pytest.mark.asyncio
    async def test_concurrent_updates_resolve_to_single_row(self, pg_store, pg_engine):
        """Two concurrent updates for same topic create exactly one row."""
        # Launch two concurrent updates
        await asyncio.gather(
            pg_store.apply_confidence_update(
                student_id="test_student",
                update=ConfidenceUpdate(topic_name="Concurrent Topic", percentage=40),
            ),
            pg_store.apply_confidence_update(
                student_id="test_student",
                update=ConfidenceUpdate(topic_name="Concurrent Topic", percentage=80),
            ),
        )

        # Verify exactly one row exists
        async with pg_engine.connect() as conn:
            result = await conn.execute(
                text(
                    "SELECT COUNT(*), percentage, band FROM topic_confidence "
                    "WHERE student_id = :student_id AND topic_name = :topic_name "
                    "GROUP BY percentage, band"
                ),
                {"student_id": "test_student", "topic_name": "Concurrent Topic"},
            )
            rows = result.fetchall()
            assert len(rows) == 1
            count, percentage, band = rows[0]
            assert count == 1
            # Verify stored band matches stored percentage
            if percentage == 40:
                assert band == "developing"
            elif percentage == 80:
                assert band == "mastered"
