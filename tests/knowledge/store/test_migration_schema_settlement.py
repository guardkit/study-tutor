"""Migration schema tests for revision b7d1e4f92a3c (Phase E, S-E1).

Covers the second Alembic revision ever — the settlement + confidence-history
surface layered on top of the initial schema (3c7cd4bca034):

* ``session.settled_at`` and ``session.text_name`` (both nullable) — and, most
  importantly, that ``settled_at`` is NULL for session rows that pre-existed the
  upgrade (the settlement sweep's work-queue depends on this).
* ``achievement.session_id`` (nullable, FK to ``session``) — replay support.
* ``topic_confidence_history`` (table + check constraint + cascade FK + the
  ``recent`` index).
* the revision's own ``downgrade`` (one step back to 3c7cd4bca034), which must
  return to the initial 7-table schema.

``schema_reference.sql`` is a living reference kept in sync by hand; ``alembic
upgrade head`` is the source of truth.

This module self-provisions its OWN throwaway ``postgres:16`` on a dedicated
port + container name so it never touches a durable store and can run
concurrently with the other migration/integration suites. It NEVER reads the
env DSN — the root ``conftest.py`` guard stays untouched.
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


#: The revision under test and the revision it downgrades to.
_HEAD_REVISION = "b7d1e4f92a3c"
_PREVIOUS_REVISION = "3c7cd4bca034"

#: Dedicated container + port for this module's throwaway Postgres. Port 55435
#: is reserved for this settlement-migration module (55432/55433/55434/55436 are
#: taken by the integration suites and the first migration-schema module).
_SETTLEMENT_MIGRATION_CONTAINER = "study-tutor-migration-settlement-test-pg"
_SETTLEMENT_MIGRATION_PORT = 55435


def _normalize_dsn_to_asyncpg(raw_dsn: str) -> str:
    """Normalize a PostgreSQL DSN to use the asyncpg dialect."""
    if raw_dsn.startswith("postgresql://") and "+asyncpg://" not in raw_dsn:
        return raw_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw_dsn


@pytest.fixture(scope="module")
def ephemeral_postgres_dsn() -> Iterator[str]:
    """Provision an OWN throwaway ``postgres:16`` for these destructive tests.

    Like the first migration-schema module, this self-provisions rather than
    trusting ``STUDY_TUTOR_PG_DSN`` — the tests run ``alembic upgrade`` /
    ``downgrade`` and DROP tables, which must never be aimed at a durable store.

    Requires Docker; skips if unavailable. The tests share this one container
    and run in definition order.
    """
    if shutil.which("docker") is None:
        pytest.skip("docker unavailable — ephemeral Postgres required")

    dsn = (
        f"postgresql://study_tutor:test@localhost:"
        f"{_SETTLEMENT_MIGRATION_PORT}/study_tutor"
    )

    subprocess.run(
        ["docker", "rm", "-f", _SETTLEMENT_MIGRATION_CONTAINER],
        capture_output=True,
        check=False,
    )
    subprocess.run(
        [
            "docker", "run", "-d", "--name", _SETTLEMENT_MIGRATION_CONTAINER,
            "-e", "POSTGRES_USER=study_tutor",
            "-e", "POSTGRES_PASSWORD=test",
            "-e", "POSTGRES_DB=study_tutor",
            "-p", f"{_SETTLEMENT_MIGRATION_PORT}:5432",
            "postgres:16",
        ],
        check=True,
        capture_output=True,
    )
    try:
        for _ in range(30):
            ready = subprocess.run(
                [
                    "docker", "exec", _SETTLEMENT_MIGRATION_CONTAINER,
                    "pg_isready", "-U", "study_tutor",
                ],
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
            ["docker", "rm", "-f", _SETTLEMENT_MIGRATION_CONTAINER],
            capture_output=True,
            check=False,
        )


@pytest.fixture(scope="module")
def alembic_project_root() -> Path:
    """Return the project root directory containing alembic.ini."""
    test_dir = Path(__file__).parent
    return test_dir.parent.parent.parent


def _run_alembic(
    project_root: Path, dsn: str, *args: str
) -> subprocess.CompletedProcess[str]:
    """Run an alembic subcommand against the throwaway DSN."""
    python_exe = project_root / ".venv" / "bin" / "python"
    return subprocess.run(
        [str(python_exe), "-m", "alembic", *args],
        cwd=project_root,
        capture_output=True,
        text=True,
        env={**os.environ, "STUDY_TUTOR_PG_DSN": dsn},
    )


@pytest.mark.asyncio
async def test_pre_existing_session_rows_get_null_settled_at(
    ephemeral_postgres_dsn: str,
    alembic_project_root: Path,
) -> None:
    """A session row created before the upgrade must have NULL settled_at.

    Upgrades to the *previous* revision first, inserts a student + session row,
    then upgrades to head — exercising the real "pre-existing row" path the
    settlement sweep relies on (status='ended' AND settled_at IS NULL is the
    work queue). Also asserts the new nullable plan-fact column text_name.
    """
    # 1. Upgrade to the FIRST revision only (no settlement columns yet).
    result = _run_alembic(
        alembic_project_root, ephemeral_postgres_dsn, "upgrade", _PREVIOUS_REVISION
    )
    assert result.returncode == 0, f"alembic upgrade (prev) failed: {result.stderr}"

    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    try:
        # Insert a student + a session row that pre-dates the second revision.
        async with engine.begin() as conn:
            await conn.execute(
                text(
                    """
                    INSERT INTO student
                        (student_id, name, year_group, target_grade, created_at)
                    VALUES ('preexisting', 'Pre', 10, '6', NOW())
                    """
                )
            )
            await conn.execute(
                text(
                    """
                    INSERT INTO session
                        (session_id, student_id, subject, status,
                         started_at, last_activity)
                    VALUES ('sess-pre', 'preexisting', 'english', 'ended',
                            NOW(), NOW())
                    """
                )
            )

        # 2. Upgrade to head (adds settled_at / text_name).
        result = _run_alembic(
            alembic_project_root, ephemeral_postgres_dsn, "upgrade", "head"
        )
        assert result.returncode == 0, f"alembic upgrade head failed: {result.stderr}"

        # 3. The pre-existing row must have NULL settled_at AND NULL text_name.
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        "SELECT settled_at, text_name FROM session "
                        "WHERE session_id = 'sess-pre'"
                    )
                )
            ).fetchone()
    finally:
        await engine.dispose()

    assert row is not None, "pre-existing session row vanished across upgrade"
    assert row[0] is None, "settled_at must be NULL for a pre-existing session row"
    assert row[1] is None, "text_name must be NULL for a pre-existing session row"


@pytest.mark.asyncio
async def test_current_revision_is_head(
    ephemeral_postgres_dsn: str,
    alembic_project_root: Path,
) -> None:
    """After upgrade head, the DB reports revision b7d1e4f92a3c as current."""
    result = _run_alembic(
        alembic_project_root, ephemeral_postgres_dsn, "current"
    )
    assert result.returncode == 0, f"alembic current failed: {result.stderr}"
    assert _HEAD_REVISION in result.stdout, (
        f"expected head {_HEAD_REVISION!r}, got: {result.stdout!r}"
    )


@pytest.mark.asyncio
async def test_session_settlement_columns_shape(
    ephemeral_postgres_dsn: str,
) -> None:
    """session.settled_at and session.text_name are the right type + nullable."""
    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    try:
        async with engine.connect() as conn:
            rows = (
                await conn.execute(
                    text(
                        """
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'session'
                          AND column_name IN ('settled_at', 'text_name')
                        """
                    )
                )
            ).fetchall()
    finally:
        await engine.dispose()

    cols = {r[0]: (r[1], r[2]) for r in rows}
    assert "settled_at" in cols, "session.settled_at column not found"
    assert cols["settled_at"][0] == "timestamp with time zone"
    assert cols["settled_at"][1] == "YES", "settled_at must be nullable"
    assert "text_name" in cols, "session.text_name column not found"
    assert cols["text_name"][0] == "text"
    assert cols["text_name"][1] == "YES", "text_name must be nullable"


@pytest.mark.asyncio
async def test_achievement_session_id_fk(
    ephemeral_postgres_dsn: str,
) -> None:
    """achievement.session_id is nullable and references session(session_id)."""
    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    try:
        async with engine.connect() as conn:
            col = (
                await conn.execute(
                    text(
                        """
                        SELECT data_type, is_nullable
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'achievement'
                          AND column_name = 'session_id'
                        """
                    )
                )
            ).fetchone()

            fk = (
                await conn.execute(
                    text(
                        """
                        SELECT ccu.table_name
                        FROM information_schema.table_constraints AS tc
                        JOIN information_schema.constraint_column_usage AS ccu
                          ON tc.constraint_name = ccu.constraint_name
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                          AND tc.table_name = 'achievement'
                          AND tc.constraint_name = 'achievement_session_id_fkey'
                        """
                    )
                )
            ).fetchone()
    finally:
        await engine.dispose()

    assert col is not None, "achievement.session_id column not found"
    assert col[0] == "text"
    assert col[1] == "YES", "achievement.session_id must be nullable"
    assert fk is not None, "achievement_session_id_fkey FK not found"
    assert fk[0] == "session", "achievement.session_id must reference session"


@pytest.mark.asyncio
async def test_topic_confidence_history_table_shape(
    ephemeral_postgres_dsn: str,
) -> None:
    """topic_confidence_history has the spec columns, index, and CASCADE FK."""
    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    try:
        async with engine.connect() as conn:
            cols = {
                r[0]: (r[1], r[2])
                for r in (
                    await conn.execute(
                        text(
                            """
                            SELECT column_name, data_type, is_nullable
                            FROM information_schema.columns
                            WHERE table_schema = 'public'
                              AND table_name = 'topic_confidence_history'
                            """
                        )
                    )
                ).fetchall()
            }

            index_present = (
                await conn.execute(
                    text(
                        """
                        SELECT 1 FROM pg_indexes
                        WHERE schemaname = 'public'
                          AND indexname = 'topic_confidence_history_recent_idx'
                        """
                    )
                )
            ).fetchone()

            fk_rule = (
                await conn.execute(
                    text(
                        """
                        SELECT rc.delete_rule
                        FROM information_schema.table_constraints AS tc
                        JOIN information_schema.referential_constraints AS rc
                          ON tc.constraint_name = rc.constraint_name
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                          AND tc.table_schema = 'public'
                          AND tc.table_name = 'topic_confidence_history'
                        """
                    )
                )
            ).fetchone()
    finally:
        await engine.dispose()

    expected = {
        "id": ("bigint", "NO"),
        "student_id": ("text", "NO"),
        "topic_name": ("text", "NO"),
        "percentage": ("integer", "NO"),
        "session_id": ("text", "YES"),
        "recorded_at": ("timestamp with time zone", "NO"),
        "source": ("text", "NO"),
    }
    assert cols == expected, f"column mismatch: {cols}"
    assert index_present is not None, "topic_confidence_history_recent_idx missing"
    assert fk_rule is not None, "topic_confidence_history student FK missing"
    assert fk_rule[0] == "CASCADE", "student FK must be ON DELETE CASCADE"


@pytest.mark.asyncio
async def test_topic_confidence_history_percentage_check(
    ephemeral_postgres_dsn: str,
) -> None:
    """The percentage CHECK constraint rejects out-of-range values."""
    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    try:
        with pytest.raises(Exception) as excinfo:
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        """
                        INSERT INTO topic_confidence_history
                            (student_id, topic_name, percentage, recorded_at,
                             source)
                        VALUES ('preexisting', 'algebra', 101, NOW(), 'test')
                        """
                    )
                )
        msg = str(excinfo.value).lower()
        assert "percentage" in msg or "check" in msg or "constraint" in msg, (
            f"expected check-constraint error, got: {excinfo.value}"
        )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_downgrade_one_step_restores_initial_schema(
    ephemeral_postgres_dsn: str,
    alembic_project_root: Path,
) -> None:
    """Downgrading b7d1e4f92a3c → 3c7cd4bca034 removes only its additions.

    The topic_confidence_history table, achievement.session_id, and the two
    session columns must be gone; the initial 7 tables must remain.
    """
    result = _run_alembic(
        alembic_project_root, ephemeral_postgres_dsn, "downgrade", _PREVIOUS_REVISION
    )
    assert result.returncode == 0, f"alembic downgrade failed: {result.stderr}"

    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    try:
        async with engine.connect() as conn:
            history_gone = (
                await conn.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM information_schema.tables
                        WHERE table_schema = 'public'
                          AND table_name = 'topic_confidence_history'
                        """
                    )
                )
            ).scalar()

            removed_cols = (
                await conn.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND (
                            (table_name = 'session'
                             AND column_name IN ('settled_at', 'text_name'))
                            OR (table_name = 'achievement'
                                AND column_name = 'session_id')
                          )
                        """
                    )
                )
            ).scalar()

            base_tables = (
                await conn.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM information_schema.tables
                        WHERE table_schema = 'public'
                          AND table_name = ANY(:names)
                        """
                    ),
                    {
                        "names": [
                            "student",
                            "topic_confidence",
                            "misconception",
                            "session",
                            "session_turn",
                            "achievement",
                            "quest",
                        ]
                    },
                )
            ).scalar()
    finally:
        await engine.dispose()

    assert history_gone == 0, "topic_confidence_history survived downgrade"
    assert removed_cols == 0, "settlement/plan-fact columns survived downgrade"
    assert base_tables == 7, "initial 7 tables must remain after one-step downgrade"
