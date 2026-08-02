"""Migration schema tests for revision c3f8a1b6d2e4 (Phase E, S-E4).

Covers the third Alembic revision — the per-session ``quotes_embedded`` counter
the W2 Growth tranche (Quote Champion / Quote Master, R8) reads:

* ``session.quotes_embedded`` is INTEGER NOT NULL DEFAULT 0 with a ``>= 0`` check.
* a session row created before the upgrade reads ``quotes_embedded = 0`` after it
  (honest — no verifier signal existed before this wave).
* the revision's own ``downgrade`` (one step back to b7d1e4f92a3c) removes the
  column + its check constraint and leaves the rest of the schema intact.

This module self-provisions its OWN throwaway ``postgres:16`` on a dedicated port
+ container name (port 55437 — 55432/55433/55434/55435/55436 are taken). It NEVER
reads the env DSN — the root ``conftest.py`` guard stays untouched.

``schema_reference.sql`` is a living reference kept in sync by hand; ``alembic
upgrade head`` is the source of truth.
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
from sqlalchemy.ext.asyncio import create_async_engine


#: The revision under test and the revision it downgrades to.
_HEAD_REVISION = "d5a9c2e7f814"
_PREVIOUS_REVISION = "b7d1e4f92a3c"

#: Dedicated container + port for this module's throwaway Postgres. Port 55437 is
#: reserved for this quotes-migration module (55432–55436 are taken by the
#: integration suites and the two earlier migration-schema modules).
_QUOTES_MIGRATION_CONTAINER = "study-tutor-migration-quotes-test-pg"
_QUOTES_MIGRATION_PORT = 55437


def _normalize_dsn_to_asyncpg(raw_dsn: str) -> str:
    """Normalize a PostgreSQL DSN to use the asyncpg dialect."""
    if raw_dsn.startswith("postgresql://") and "+asyncpg://" not in raw_dsn:
        return raw_dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    return raw_dsn


@pytest.fixture(scope="module")
def ephemeral_postgres_dsn() -> Iterator[str]:
    """Provision an OWN throwaway ``postgres:16`` for these destructive tests."""
    if shutil.which("docker") is None:
        pytest.skip("docker unavailable — ephemeral Postgres required")

    dsn = (
        f"postgresql://study_tutor:test@localhost:"
        f"{_QUOTES_MIGRATION_PORT}/study_tutor"
    )

    subprocess.run(
        ["docker", "rm", "-f", _QUOTES_MIGRATION_CONTAINER],
        capture_output=True,
        check=False,
    )
    subprocess.run(
        [
            "docker", "run", "-d", "--name", _QUOTES_MIGRATION_CONTAINER,
            "-e", "POSTGRES_USER=study_tutor",
            "-e", "POSTGRES_PASSWORD=test",
            "-e", "POSTGRES_DB=study_tutor",
            "-p", f"{_QUOTES_MIGRATION_PORT}:5432",
            "postgres:16",
        ],
        check=True,
        capture_output=True,
    )
    try:
        for _ in range(30):
            ready = subprocess.run(
                [
                    "docker", "exec", _QUOTES_MIGRATION_CONTAINER,
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
            ["docker", "rm", "-f", _QUOTES_MIGRATION_CONTAINER],
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
async def test_pre_existing_session_row_gets_zero_quotes_embedded(
    ephemeral_postgres_dsn: str,
    alembic_project_root: Path,
) -> None:
    """A session created before the upgrade reads quotes_embedded = 0 after it."""
    result = _run_alembic(
        alembic_project_root, ephemeral_postgres_dsn, "upgrade", _PREVIOUS_REVISION
    )
    assert result.returncode == 0, f"alembic upgrade (prev) failed: {result.stderr}"

    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    try:
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

        result = _run_alembic(
            alembic_project_root, ephemeral_postgres_dsn, "upgrade", "head"
        )
        assert result.returncode == 0, f"alembic upgrade head failed: {result.stderr}"

        async with engine.connect() as conn:
            value = (
                await conn.execute(
                    text(
                        "SELECT quotes_embedded FROM session "
                        "WHERE session_id = 'sess-pre'"
                    )
                )
            ).scalar()
    finally:
        await engine.dispose()

    assert value == 0, "pre-existing session must read quotes_embedded = 0"


@pytest.mark.asyncio
async def test_current_revision_is_head(
    ephemeral_postgres_dsn: str,
    alembic_project_root: Path,
) -> None:
    """After upgrade head, the DB reports revision c3f8a1b6d2e4 as current."""
    result = _run_alembic(alembic_project_root, ephemeral_postgres_dsn, "current")
    assert result.returncode == 0, f"alembic current failed: {result.stderr}"
    assert _HEAD_REVISION in result.stdout, (
        f"expected head {_HEAD_REVISION!r}, got: {result.stdout!r}"
    )


@pytest.mark.asyncio
async def test_quotes_embedded_column_shape(
    ephemeral_postgres_dsn: str,
) -> None:
    """session.quotes_embedded is integer, NOT NULL, default 0."""
    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    try:
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    text(
                        """
                        SELECT data_type, is_nullable, column_default
                        FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'session'
                          AND column_name = 'quotes_embedded'
                        """
                    )
                )
            ).fetchone()
    finally:
        await engine.dispose()

    assert row is not None, "session.quotes_embedded column not found"
    assert row[0] == "integer"
    assert row[1] == "NO", "quotes_embedded must be NOT NULL"
    assert row[2] is not None and "0" in row[2], "default must be 0"


@pytest.mark.asyncio
async def test_quotes_embedded_check_rejects_negative(
    ephemeral_postgres_dsn: str,
) -> None:
    """The quotes_embedded >= 0 CHECK constraint rejects a negative value."""
    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    try:
        with pytest.raises(Exception) as excinfo:
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        """
                        INSERT INTO session
                            (session_id, student_id, subject, status,
                             started_at, last_activity, quotes_embedded)
                        VALUES ('sess-neg', 'preexisting', 'english', 'ended',
                                NOW(), NOW(), -1)
                        """
                    )
                )
        msg = str(excinfo.value).lower()
        assert "quotes_embedded" in msg or "check" in msg or "constraint" in msg
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_downgrade_one_step_removes_quotes_embedded(
    ephemeral_postgres_dsn: str,
    alembic_project_root: Path,
) -> None:
    """Downgrading c3f8a1b6d2e4 → b7d1e4f92a3c removes only quotes_embedded."""
    result = _run_alembic(
        alembic_project_root, ephemeral_postgres_dsn, "downgrade", _PREVIOUS_REVISION
    )
    assert result.returncode == 0, f"alembic downgrade failed: {result.stderr}"

    dsn = _normalize_dsn_to_asyncpg(ephemeral_postgres_dsn)
    engine = create_async_engine(dsn)
    try:
        async with engine.connect() as conn:
            col_gone = (
                await conn.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'session'
                          AND column_name = 'quotes_embedded'
                        """
                    )
                )
            ).scalar()
            # The prior-revision columns must survive the one-step downgrade.
            survivors = (
                await conn.execute(
                    text(
                        """
                        SELECT COUNT(*) FROM information_schema.columns
                        WHERE table_schema = 'public'
                          AND table_name = 'session'
                          AND column_name IN ('settled_at', 'text_name')
                        """
                    )
                )
            ).scalar()
    finally:
        await engine.dispose()

    assert col_gone == 0, "quotes_embedded survived downgrade"
    assert survivors == 2, "settled_at / text_name must survive the one-step downgrade"
