"""Pytest fixtures for SessionService composed-path integration tests (Phase R / S-R1).

Self-provisions a throwaway PostgreSQL container (never the env DSN, never a
non-loopback host — the root ``conftest.py`` guard enforces this) so the tests
can drive the *composed service path* (``SessionService`` over a real
``PostgresStudentStore``) against genuine Postgres semantics.

Port/container allocation (see the S-R1 spec): 55432/55433/55434 are taken by
existing suites and 55435 is reserved for the Phase E migration tests, so this
module claims **55436** with a fresh container name.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from study_tutor.knowledge.store.postgres import PostgresStudentStore

_CONTAINER_NAME = "guardkit-test-pg-session-svc"
_PORT = 55436


@pytest.fixture(scope="session")
def session_service_pg_container() -> Generator[str, None, None]:
    """Start an ephemeral PostgreSQL container for the SessionService tests.

    Yields the loopback DSN; the container is torn down at session end.
    """
    dsn = f"postgresql://study_tutor:test@localhost:{_PORT}/study_tutor"

    # Clean up any leftover container from a previous run
    subprocess.run(
        ["docker", "rm", "-f", _CONTAINER_NAME],
        capture_output=True,
        check=False,
    )

    subprocess.run(
        [
            "docker", "run", "-d", "--name", _CONTAINER_NAME,
            "-e", "POSTGRES_USER=study_tutor",
            "-e", "POSTGRES_PASSWORD=test",
            "-e", "POSTGRES_DB=study_tutor",
            "-p", f"{_PORT}:5432",
            "postgres:16",
        ],
        check=True,
        capture_output=True,
    )

    # Wait for readiness (max 30 seconds)
    for _ in range(30):
        result = subprocess.run(
            ["docker", "exec", _CONTAINER_NAME, "pg_isready"],
            capture_output=True,
        )
        if result.returncode == 0:
            break
        time.sleep(1)
    else:
        subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], check=False)
        pytest.fail("PostgreSQL container failed to start within 30 seconds")

    # Run Alembic migrations to set up the schema against the throwaway DSN.
    project_root = Path(__file__).parents[4]
    env = os.environ.copy()
    env["STUDY_TUTOR_PG_DSN"] = dsn
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        env=env,
        cwd=str(project_root),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        subprocess.run(["docker", "rm", "-f", _CONTAINER_NAME], check=False)
        pytest.fail(
            f"Alembic migration failed (exit {result.returncode}):\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    yield dsn

    subprocess.run(
        ["docker", "rm", "-f", _CONTAINER_NAME],
        capture_output=True,
        check=False,
    )


@pytest.fixture
async def pg_store(session_service_pg_container):
    """A ``PostgresStudentStore`` on a freshly-cleaned throwaway database."""
    dsn = session_service_pg_container
    store = PostgresStudentStore(dsn)

    engine = create_async_engine(
        dsn.replace("postgresql://", "postgresql+asyncpg://")
    )
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM session_turn"))
        await conn.execute(text("DELETE FROM session"))
        await conn.execute(text("DELETE FROM misconception"))
        await conn.execute(text("DELETE FROM topic_confidence"))
        await conn.execute(text("DELETE FROM student"))

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
async def pg_engine(session_service_pg_container):
    """Direct engine access for row-level assertions."""
    dsn = session_service_pg_container
    engine = create_async_engine(
        dsn.replace("postgresql://", "postgresql+asyncpg://")
    )
    yield engine
    await engine.dispose()


@pytest.fixture
def student_id() -> str:
    return "test_student"
