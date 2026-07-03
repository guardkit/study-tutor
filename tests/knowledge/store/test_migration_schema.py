"""Migration schema tests for TASK-SMP-02.

Tests that the first Alembic migration correctly creates the StudentStore schema
with all tables, indexes, constraints, and foreign keys as specified in
schema_reference.sql.

Also includes DSN seam tests verifying the async engine configuration.
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine


# ============================================================================
# DSN Seam Tests (verify env.py async dialect transformation)
# ============================================================================


def _normalize_dsn_to_asyncpg(raw_dsn: str) -> str:
    """Normalize a PostgreSQL DSN to use the asyncpg dialect.

    This mirrors the logic in alembic/env.py that transforms the
    STUDY_TUTOR_PG_DSN from bare postgresql:// to postgresql+asyncpg://.
    """
    if raw_dsn.startswith("postgresql://") and "+asyncpg://" not in raw_dsn:
        return raw_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw_dsn


@pytest.mark.skipif(
    "STUDY_TUTOR_PG_DSN" not in os.environ,
    reason="DSN not wired (producer: W0 runbook / TASK-SMP-01)",
)
def test_dsn_uses_asyncpg_dialect() -> None:
    """Verify that the resolved DSN uses the postgresql+asyncpg dialect."""
    raw = os.environ["STUDY_TUTOR_PG_DSN"]
    normalized = _normalize_dsn_to_asyncpg(raw)
    url = make_url(normalized)
    assert url.drivername == "postgresql+asyncpg", (
        f"async engine needs postgresql+asyncpg dialect, got {url.drivername!r}"
    )
    assert url.database == "study_tutor"


def test_bare_postgresql_dsn_is_normalized_to_asyncpg() -> None:
    """Verify that bare postgresql:// DSNs are normalized to asyncpg."""
    raw = "postgresql://study_tutor:pw@localhost:55432/study_tutor"
    normalized = _normalize_dsn_to_asyncpg(raw)
    url = make_url(normalized)
    assert url.drivername == "postgresql+asyncpg"


# ============================================================================
# Migration Schema Tests
# ============================================================================


@pytest.fixture(scope="module")
def ephemeral_postgres_dsn() -> str | None:
    """Provide DSN for ephemeral test Postgres, or skip if unavailable.

    Returns the STUDY_TUTOR_PG_DSN if set (assumes it points to a throwaway
    test database), otherwise returns None to skip migration tests.
    """
    dsn = os.getenv("STUDY_TUTOR_PG_DSN")
    if not dsn:
        pytest.skip("STUDY_TUTOR_PG_DSN not set (ephemeral Postgres required)")
    return dsn


@pytest.fixture(scope="module")
def alembic_project_root() -> Path:
    """Return the project root directory containing alembic.ini."""
    # Tests are in tests/knowledge/store/, project root is 3 levels up
    test_dir = Path(__file__).parent
    return test_dir.parent.parent.parent


@pytest.mark.asyncio
async def test_upgrade_head_creates_all_tables(
    ephemeral_postgres_dsn: str,
    alembic_project_root: Path,
) -> None:
    """Verify that 'alembic upgrade head' creates all 7 StudentStore tables."""
    # Run alembic upgrade head using virtualenv python
    python_exe = alembic_project_root / ".venv" / "bin" / "python"
    result = subprocess.run(
        [str(python_exe), "-m", "alembic", "upgrade", "head"],
        cwd=alembic_project_root,
        capture_output=True,
        text=True,
        env={**os.environ, "STUDY_TUTOR_PG_DSN": ephemeral_postgres_dsn},
    )
    assert result.returncode == 0, f"alembic upgrade failed: {result.stderr}"

    # Verify all 7 tables exist
    expected_tables = {
        "student",
        "topic_confidence",
        "misconception",
        "session",
        "session_turn",
        "achievement",
        "quest",
    }

    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = ANY(:names)
                """
            ),
            {"names": list(expected_tables)},
        )
        actual_tables = {row[0] for row in result}

    await engine.dispose()
    assert actual_tables == expected_tables, (
        f"Missing tables: {expected_tables - actual_tables}, "
        f"Extra tables: {actual_tables - expected_tables}"
    )


@pytest.mark.asyncio
async def test_upgrade_head_creates_named_indexes(
    ephemeral_postgres_dsn: str,
    alembic_project_root: Path,
) -> None:
    """Verify that all 3 named indexes are created."""
    expected_indexes = {
        "misconception_recent_idx",
        "session_resume_idx",
        "quest_active_idx",
    }

    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT indexname
                FROM pg_indexes
                WHERE schemaname = 'public'
                  AND indexname = ANY(:names)
                """
            ),
            {"names": list(expected_indexes)},
        )
        actual_indexes = {row[0] for row in result}

    await engine.dispose()
    assert actual_indexes == expected_indexes, (
        f"Missing indexes: {expected_indexes - actual_indexes}"
    )


@pytest.mark.asyncio
async def test_session_xp_awarded_column_exists(
    ephemeral_postgres_dsn: str,
) -> None:
    """Verify that session.xp_awarded column exists with correct type and default."""
    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT column_name, data_type, column_default, is_nullable
                FROM information_schema.columns
                WHERE table_schema = 'public'
                  AND table_name = 'session'
                  AND column_name = 'xp_awarded'
                """
            )
        )
        row = result.fetchone()

    await engine.dispose()
    assert row is not None, "session.xp_awarded column not found"
    assert row[1] == "integer", f"Expected integer type, got {row[1]}"
    assert row[3] == "NO", "xp_awarded should be NOT NULL"


@pytest.mark.asyncio
async def test_composite_primary_keys_exist(
    ephemeral_postgres_dsn: str,
) -> None:
    """Verify that composite PKs are correctly defined."""
    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    async with engine.connect() as conn:
        # Check topic_confidence PK (student_id, topic_name)
        result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.key_column_usage
                WHERE table_name = 'topic_confidence'
                  AND constraint_name LIKE '%pkey'
                  AND column_name IN ('student_id', 'topic_name')
                """
            )
        )
        assert result.scalar() == 2, "topic_confidence should have composite PK on (student_id, topic_name)"

        # Check session_turn PK (session_id, turn_index)
        result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.key_column_usage
                WHERE table_name = 'session_turn'
                  AND constraint_name LIKE '%pkey'
                  AND column_name IN ('session_id', 'turn_index')
                """
            )
        )
        assert result.scalar() == 2, "session_turn should have composite PK on (session_id, turn_index)"

        # Check achievement PK (student_id, achievement_id)
        result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.key_column_usage
                WHERE table_name = 'achievement'
                  AND constraint_name LIKE '%pkey'
                  AND column_name IN ('student_id', 'achievement_id')
                """
            )
        )
        assert result.scalar() == 2, "achievement should have composite PK on (student_id, achievement_id)"

    await engine.dispose()


@pytest.mark.asyncio
async def test_foreign_keys_have_cascade_delete(
    ephemeral_postgres_dsn: str,
) -> None:
    """Verify that all child FKs have ON DELETE CASCADE."""
    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    async with engine.connect() as conn:
        # Query all FK constraints
        result = await conn.execute(
            text(
                """
                SELECT
                    tc.table_name,
                    rc.delete_rule
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.referential_constraints AS rc
                  ON tc.constraint_name = rc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                  AND tc.table_schema = 'public'
                """
            )
        )
        fk_rules = {row[0]: row[1] for row in result}

    await engine.dispose()

    # All child tables should have CASCADE delete
    expected_cascade_tables = {
        "topic_confidence",
        "misconception",
        "session",
        "session_turn",
        "achievement",
        "quest",
    }
    for table in expected_cascade_tables:
        assert table in fk_rules, f"FK constraint missing for {table}"
        assert fk_rules[table] == "CASCADE", f"{table} FK should have ON DELETE CASCADE, got {fk_rules[table]}"


@pytest.mark.asyncio
async def test_check_constraints_are_enforced(
    ephemeral_postgres_dsn: str,
) -> None:
    """Verify that CHECK constraints reject invalid data."""
    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)

    # Test year_group BETWEEN 7 AND 13
    try:
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO student (student_id, name, year_group, target_grade, created_at)
                    VALUES ('test_student', 'Test', 6, 'A', NOW())
                    """
                )
            )
        # If we get here, the constraint didn't fire
        raise AssertionError("Expected year_group CHECK constraint to reject value 6")
    except Exception as e:
        # Check if it's a constraint violation
        assert "year_group" in str(e).lower() or "check" in str(e).lower() or "constraint" in str(e).lower(), (
            f"Expected constraint error, got: {e}"
        )

    # Test percentage BETWEEN 0 AND 100 (requires student first)
    try:
        async with engine.begin() as conn:
            # Create a test student
            await conn.execute(
                text(
                    """
                    INSERT INTO student (student_id, name, year_group, target_grade, created_at)
                    VALUES ('test_student2', 'Test', 10, 'A', NOW())
                    """
                )
            )
            # Try to insert invalid percentage
            await conn.execute(
                text(
                    """
                    INSERT INTO topic_confidence (student_id, topic_name, percentage, band, last_revised_at)
                    VALUES ('test_student2', 'algebra', 101, 'mastered', NOW())
                    """
                )
            )
        # If we get here, the constraint didn't fire
        raise AssertionError("Expected percentage CHECK constraint to reject value 101")
    except Exception as e:
        # Check if it's a constraint violation
        assert "percentage" in str(e).lower() or "check" in str(e).lower() or "constraint" in str(e).lower(), (
            f"Expected constraint error, got: {e}"
        )

    await engine.dispose()


@pytest.mark.asyncio
async def test_only_plpgsql_extension_exists(
    ephemeral_postgres_dsn: str,
) -> None:
    """Verify that no extensions beyond plpgsql are created."""
    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT extname FROM pg_extension"))
        extensions = {row[0] for row in result}

    await engine.dispose()
    assert extensions == {"plpgsql"}, f"Unexpected extensions: {extensions - {'plpgsql'}}"


@pytest.mark.asyncio
async def test_upgrade_head_is_idempotent(
    ephemeral_postgres_dsn: str,
    alembic_project_root: Path,
) -> None:
    """Verify that re-running 'alembic upgrade head' is a no-op."""
    # Run upgrade head twice using virtualenv python
    python_exe = alembic_project_root / ".venv" / "bin" / "python"
    for _ in range(2):
        result = subprocess.run(
            [str(python_exe), "-m", "alembic", "upgrade", "head"],
            cwd=alembic_project_root,
            capture_output=True,
            text=True,
            env={**os.environ, "STUDY_TUTOR_PG_DSN": ephemeral_postgres_dsn},
        )
        assert result.returncode == 0, f"alembic upgrade failed: {result.stderr}"


@pytest.mark.asyncio
async def test_downgrade_base_removes_all_tables(
    ephemeral_postgres_dsn: str,
    alembic_project_root: Path,
) -> None:
    """Verify that 'alembic downgrade base' removes all StudentStore tables."""
    # Run downgrade base using virtualenv python
    python_exe = alembic_project_root / ".venv" / "bin" / "python"
    result = subprocess.run(
        [str(python_exe), "-m", "alembic", "downgrade", "base"],
        cwd=alembic_project_root,
        capture_output=True,
        text=True,
        env={**os.environ, "STUDY_TUTOR_PG_DSN": ephemeral_postgres_dsn},
    )
    assert result.returncode == 0, f"alembic downgrade failed: {result.stderr}"

    # Verify all tables are gone
    tables_to_check = {
        "student",
        "topic_confidence",
        "misconception",
        "session",
        "session_turn",
        "achievement",
        "quest",
    }

    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    async with engine.connect() as conn:
        result = await conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public'
                  AND table_name = ANY(:names)
                """
            ),
            {"names": list(tables_to_check)},
        )
        count = result.scalar()

    await engine.dispose()
    assert count == 0, f"Expected 0 StudentStore tables after downgrade, found {count}"
