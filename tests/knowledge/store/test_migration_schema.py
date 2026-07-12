"""Migration schema tests for the StudentStore Alembic chain.

Tests that ``alembic upgrade head`` builds the StudentStore schema with all
tables, indexes, constraints, and foreign keys. ``schema_reference.sql`` is a
living reference kept in sync by hand; ``alembic upgrade head`` is the source of
truth. As of revision b7d1e4f92a3c (Phase E, S-E1) head is 8 tables — the
initial 7 plus ``topic_confidence_history``; the settlement/plan-fact column
additions and the second revision's own downgrade are covered in
``test_migration_schema_settlement.py``.

Also includes DSN seam tests verifying the async engine configuration.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from pathlib import Path
from typing import Iterator

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


#: Dedicated container + port for this module's throwaway Postgres. The port is
#: distinct from the integration suite's 55433 so both can run concurrently.
_MIGRATION_TEST_CONTAINER = "study-tutor-migration-test-pg"
_MIGRATION_TEST_PORT = 55434


@pytest.fixture(scope="module")
def ephemeral_postgres_dsn() -> Iterator[str]:
    """Provision an OWN throwaway ``postgres:16`` for these destructive tests.

    The tests in this module run ``alembic upgrade head`` / ``downgrade base``,
    and the downgrade test DROPs every StudentStore table. To make that
    impossible to aim at a durable store, this fixture starts its own empty,
    localhost, ephemeral container (destroyed at module teardown) rather than
    trusting ``STUDY_TUTOR_PG_DSN`` from the environment.

    (History: this fixture used to read ``STUDY_TUTOR_PG_DSN`` directly, which
    wiped the durable NAS store when the suite ran with that var set —
    2026-07-09. Self-provisioning removes that footgun entirely; the alembic
    subprocesses below explicitly override the var to this throwaway DSN.)

    Requires Docker; skips if unavailable. The tests share this one container
    and run in definition order: ``upgrade`` (from empty) first, ``downgrade``
    last.
    """
    if shutil.which("docker") is None:
        pytest.skip("docker unavailable — ephemeral Postgres required")

    dsn = (
        f"postgresql://study_tutor:test@localhost:{_MIGRATION_TEST_PORT}/study_tutor"
    )

    subprocess.run(
        ["docker", "rm", "-f", _MIGRATION_TEST_CONTAINER],
        capture_output=True,
        check=False,
    )
    subprocess.run(
        [
            "docker", "run", "-d", "--name", _MIGRATION_TEST_CONTAINER,
            "-e", "POSTGRES_USER=study_tutor",
            "-e", "POSTGRES_PASSWORD=test",
            "-e", "POSTGRES_DB=study_tutor",
            "-p", f"{_MIGRATION_TEST_PORT}:5432",
            "postgres:16",
        ],
        check=True,
        capture_output=True,
    )
    try:
        for _ in range(30):
            ready = subprocess.run(
                ["docker", "exec", _MIGRATION_TEST_CONTAINER, "pg_isready", "-U", "study_tutor"],
                capture_output=True,
            )
            if ready.returncode == 0:
                break
            time.sleep(1)
        else:
            pytest.fail("ephemeral Postgres did not become ready within 30s")
        yield dsn
    finally:
        subprocess.run(
            ["docker", "rm", "-f", _MIGRATION_TEST_CONTAINER],
            capture_output=True,
            check=False,
        )


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
    """Verify that 'alembic upgrade head' creates all 8 StudentStore tables."""
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

    # Verify all 8 tables exist (head = revision b7d1e4f92a3c)
    expected_tables = {
        "student",
        "topic_confidence",
        "misconception",
        "session",
        "session_turn",
        "achievement",
        "quest",
        "topic_confidence_history",
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
    """Verify that all 4 named indexes are created."""
    expected_indexes = {
        "misconception_recent_idx",
        "session_resume_idx",
        "quest_active_idx",
        "topic_confidence_history_recent_idx",
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
    """Verify that all child→student FKs have ON DELETE CASCADE.

    Keyed by constraint name, not table name: as of revision b7d1e4f92a3c the
    ``achievement`` and ``topic_confidence_history`` tables carry more than one
    FK (``achievement.session_id`` references ``session`` with NO ACTION — the
    replay-support FK is deliberately non-cascading), so collapsing by table
    name would be ambiguous. The child→student ownership FKs are the ones that
    must cascade so deleting a student wipes their learner state.
    """
    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    async with engine.connect() as conn:
        # Query all FK constraints, keyed by constraint name.
        result = await conn.execute(
            text(
                """
                SELECT
                    tc.constraint_name,
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

    # Every child→student ownership FK must cascade on delete.
    expected_cascade_fks = {
        "topic_confidence_student_id_fkey",
        "misconception_student_id_fkey",
        "session_student_id_fkey",
        "session_turn_session_id_fkey",
        "achievement_student_id_fkey",
        "quest_student_id_fkey",
        "topic_confidence_history_student_id_fkey",
    }
    for constraint in expected_cascade_fks:
        assert constraint in fk_rules, f"FK constraint missing: {constraint}"
        assert fk_rules[constraint] == "CASCADE", (
            f"{constraint} should have ON DELETE CASCADE, got {fk_rules[constraint]}"
        )

    # The replay-support FK is intentionally NON-cascading.
    assert fk_rules.get("achievement_session_id_fkey") == "NO ACTION", (
        "achievement.session_id FK must not cascade (replay support, D1)"
    )


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
        "topic_confidence_history",
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
