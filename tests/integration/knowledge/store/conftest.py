"""Pytest configuration for PostgreSQL integration tests.

Provides session-scoped PostgreSQL container lifecycle management for
tests that require a real database (TASK-SMP-04 and related).
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


@pytest.fixture(scope="session")
def postgres_container() -> Generator[str, None, None]:
    """Start ephemeral PostgreSQL container for integration tests.

    Yields the DSN for connecting to the test database.
    Container is torn down at session end.
    """
    container_name = "guardkit-test-pg-integration"
    port = 55433
    dsn = f"postgresql://study_tutor:test@localhost:{port}/study_tutor"

    # Clean up any existing container
    subprocess.run(
        ["docker", "rm", "-f", container_name],
        capture_output=True,
        check=False,
    )

    # Start PostgreSQL container
    subprocess.run(
        [
            "docker", "run", "-d", "--name", container_name,
            "-e", "POSTGRES_USER=study_tutor",
            "-e", "POSTGRES_PASSWORD=test",
            "-e", "POSTGRES_DB=study_tutor",
            "-p", f"{port}:5432",
            "postgres:16",
        ],
        check=True,
        capture_output=True,
    )

    # Wait for PostgreSQL to be ready (max 30 seconds)
    for _ in range(30):
        result = subprocess.run(
            ["docker", "exec", container_name, "pg_isready"],
            capture_output=True,
        )
        if result.returncode == 0:
            break
        time.sleep(1)
    else:
        # Cleanup and fail
        subprocess.run(["docker", "rm", "-f", container_name], check=False)
        pytest.fail("PostgreSQL container failed to start within 30 seconds")

    # Run Alembic migrations to set up schema
    # Use absolute path to project root for running alembic
    project_root = Path(__file__).parent.parent.parent.parent.parent
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
        # Cleanup and fail with detailed error
        subprocess.run(["docker", "rm", "-f", container_name], check=False)
        pytest.fail(
            f"Alembic migration failed (exit {result.returncode}):\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    yield dsn

    # Tear down container
    subprocess.run(
        ["docker", "rm", "-f", container_name],
        capture_output=True,
        check=False,
    )


@pytest.fixture
async def pg_store(postgres_container):
    """Provide a PostgresStudentStore connected to ephemeral test database."""
    dsn = postgres_container
    store = PostgresStudentStore(dsn)

    # Clean tables before each test
    engine = create_async_engine(dsn.replace("postgresql://", "postgresql+asyncpg://"))
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM misconception"))
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


@pytest.fixture
def student_id() -> str:
    """Provide test student ID."""
    return "test_student"
