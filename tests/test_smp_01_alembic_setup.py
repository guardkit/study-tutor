"""Tests for TASK-SMP-01: SQLAlchemy-async/asyncpg/Alembic deps + async Alembic scaffolding.

This test file validates all acceptance criteria for SMP-01:
- AC-001: Dependencies in pyproject.toml
- AC-002: uv.lock is in sync
- AC-003: Alembic CLI is installed and working
- AC-004: alembic.ini exists and is configured correctly
- AC-005: alembic/env.py exists with async engine support
- AC-006: env.py sets target_metadata from shared metadata
- AC-007: alembic/versions/ exists and is empty
- AC-008: alembic history runs without error
- AC-009: alembic current runs without error
- AC-010: Tree still imports cleanly
- AC-011: No tables/DDL created by this task
"""
from __future__ import annotations

import configparser
import os
import subprocess
import sys
from pathlib import Path

import pytest


# Test fixtures
@pytest.fixture
def repo_root() -> Path:
    """Return the repository root directory."""
    return Path(__file__).parent.parent


@pytest.fixture
def pyproject_path(repo_root: Path) -> Path:
    """Return path to pyproject.toml."""
    return repo_root / "pyproject.toml"


@pytest.fixture
def alembic_ini_path(repo_root: Path) -> Path:
    """Return path to alembic.ini."""
    return repo_root / "alembic.ini"


@pytest.fixture
def alembic_env_path(repo_root: Path) -> Path:
    """Return path to alembic/env.py."""
    return repo_root / "alembic" / "env.py"


@pytest.fixture
def alembic_versions_path(repo_root: Path) -> Path:
    """Return path to alembic/versions/ directory."""
    return repo_root / "alembic" / "versions"


# AC-001: pyproject.toml dependencies
def test_ac001_pyproject_dependencies(pyproject_path: Path) -> None:
    """Verify pyproject.toml contains required SQLAlchemy async dependencies.

    AC-001: pyproject.toml [project.dependencies] lists sqlalchemy[asyncio]>=2.0,
    asyncpg>=0.29, and alembic>=1.13.
    """
    content = pyproject_path.read_text()

    # Check for sqlalchemy[asyncio]>=2.0
    assert "sqlalchemy[asyncio]" in content, "Missing sqlalchemy[asyncio] dependency"
    assert ">=2.0" in content, "Missing SQLAlchemy 2.0+ version constraint"

    # Check for asyncpg
    assert "asyncpg" in content, "Missing asyncpg dependency"
    assert ">=0.29" in content or "asyncpg>=0.29" in content, "Missing asyncpg version constraint"

    # Check for alembic
    assert "alembic" in content, "Missing alembic dependency"
    assert ">=1.13" in content or "alembic>=1.13" in content, "Missing alembic version constraint"


# AC-002: uv.lock is in sync
def test_ac002_uv_lock_in_sync(repo_root: Path) -> None:
    """Verify uv.lock is in sync with pyproject.toml.

    AC-002: uv.lock is regenerated and in sync — `uv lock --check` passes.
    """
    result = subprocess.run(
        ["uv", "lock", "--check"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"uv lock --check failed: {result.stderr}"


# AC-003: Alembic CLI works
def test_ac003_alembic_cli_installed(repo_root: Path) -> None:
    """Verify alembic CLI is installed and prints version.

    AC-003: `.venv/bin/alembic --version` runs and prints a version.
    """
    venv_python = repo_root / ".venv" / "bin" / "python"
    result = subprocess.run(
        [str(venv_python), "-m", "alembic", "--version"],
        cwd=repo_root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"alembic --version failed: {result.stderr}"
    assert "alembic" in result.stdout.lower(), "Alembic version not in output"
    # Extract version (format: "alembic 1.18.5")
    parts = result.stdout.strip().split()
    assert len(parts) >= 2, "Unexpected version output format"
    version = parts[1]
    assert "." in version, "Version doesn't look like a version number"


# AC-004: alembic.ini exists and is configured
def test_ac004_alembic_ini_exists(alembic_ini_path: Path) -> None:
    """Verify alembic.ini exists at repo root with correct configuration.

    AC-004: alembic.ini exists at repo root with script_location = alembic and
    does NOT hardcode a DSN (sqlalchemy.url is empty).
    """
    assert alembic_ini_path.exists(), "alembic.ini does not exist"

    config = configparser.ConfigParser()
    config.read(alembic_ini_path)

    # Check [alembic] section exists
    assert "alembic" in config, "Missing [alembic] section in alembic.ini"

    # Check script_location = alembic
    script_location = config.get("alembic", "script_location")
    assert script_location == "alembic", f"Expected script_location=alembic, got {script_location}"

    # Check sqlalchemy.url is empty (no hardcoded DSN)
    url = config.get("alembic", "sqlalchemy.url", fallback=None)
    assert url is not None, "sqlalchemy.url not found in alembic.ini"
    assert url.strip() == "", f"sqlalchemy.url should be empty, got: {url}"


# AC-005: alembic/env.py exists with async support
def test_ac005_env_py_has_async_support(alembic_env_path: Path) -> None:
    """Verify alembic/env.py exists with async engine configuration.

    AC-005: alembic/env.py exists, builds the online engine with
    `async_engine_from_config` + `asyncio.run`, and transforms the DSN to
    use `postgresql+asyncpg://` if needed.
    """
    assert alembic_env_path.exists(), "alembic/env.py does not exist"

    content = alembic_env_path.read_text()

    # Check for async imports
    assert "import asyncio" in content, "Missing asyncio import"
    assert "async_engine_from_config" in content, "Missing async_engine_from_config"

    # Check for async migration function
    assert "async def run_async_migrations" in content, "Missing async run_async_migrations function"

    # Check for asyncio.run() call
    assert "asyncio.run" in content, "Missing asyncio.run() call"

    # Check for DSN transformation to asyncpg
    assert "postgresql+asyncpg://" in content, "Missing postgresql+asyncpg:// DSN transformation"


# AC-006: env.py sets target_metadata
def test_ac006_env_py_sets_target_metadata(alembic_env_path: Path) -> None:
    """Verify env.py sets target_metadata to shared metadata object.

    AC-006: env.py sets `target_metadata` to the shared `metadata` object from
    `study_tutor.knowledge.store.db`.
    """
    content = alembic_env_path.read_text()

    # Check for import of shared metadata
    assert "from study_tutor.knowledge.store.db import metadata" in content, \
        "Missing import of shared metadata from study_tutor.knowledge.store.db"

    # Check for target_metadata assignment
    assert "target_metadata = metadata" in content, \
        "Missing target_metadata = metadata assignment"


# NOTE: an "alembic/versions/ is empty" test was removed here — it asserted a
# transient scaffold-time state (SMP-01 adds no migration), which SMP-02
# correctly invalidates by landing the initial migration. The lasting scaffold
# invariants (alembic.ini present, async env.py, `alembic history` works) are
# covered by the other AC tests in this module.


# AC-008: alembic history runs without error
def test_ac008_alembic_history_works(repo_root: Path) -> None:
    """Verify `alembic history` runs without error (empty — zero revisions).

    AC-008: `.venv/bin/alembic history` runs without error (empty — zero revisions).
    """
    # Temporarily unset STUDY_TUTOR_PG_DSN to avoid database connection
    env = os.environ.copy()
    env.pop("STUDY_TUTOR_PG_DSN", None)

    venv_python = repo_root / ".venv" / "bin" / "python"
    result = subprocess.run(
        [str(venv_python), "-m", "alembic", "history"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        env=env,
    )
    # Should succeed (exit code 0) with no output (no revisions)
    assert result.returncode == 0, f"alembic history failed: {result.stderr}"


# AC-009: alembic current runs without error
def test_ac009_alembic_current_works(repo_root: Path) -> None:
    """Verify `alembic current` runs without error against a reachable database.

    AC-009: `.venv/bin/alembic current` runs without error against a **reachable
    Postgres** (or gracefully reports no connection if STUDY_TUTOR_PG_DSN is unset).
    """
    venv_python = repo_root / ".venv" / "bin" / "python"

    # Check if STUDY_TUTOR_PG_DSN is set
    dsn = os.getenv("STUDY_TUTOR_PG_DSN")

    if dsn:
        # Database is configured - should connect and report current version (empty)
        result = subprocess.run(
            [str(venv_python), "-m", "alembic", "current"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, f"alembic current failed: {result.stderr}"
    else:
        # No database configured - should gracefully skip connection
        # (our env.py returns early when URL is empty)
        result = subprocess.run(
            [str(venv_python), "-m", "alembic", "current"],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        # Should succeed with no output (skipped connection)
        assert result.returncode == 0, f"alembic current failed: {result.stderr}"


# AC-010: Tree imports cleanly
def test_ac010_tree_imports_cleanly() -> None:
    """Verify the Python package tree still imports cleanly.

    AC-010: The tree still imports cleanly:
    - `import study_tutor`
    - `import study_tutor.knowledge.store.postgres`
    - `import study_tutor.knowledge.store.db`
    """
    # Test imports in a fresh subprocess to avoid polluting this test process
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import study_tutor; "
            "import study_tutor.knowledge.store.postgres; "
            "import study_tutor.knowledge.store.db; "
            "print('OK')"
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, f"Import failed: {result.stderr}"
    assert "OK" in result.stdout, "Imports did not complete successfully"


# AC-011: db.py holds only the shared metadata, not table DDL
def test_ac011_db_defines_metadata_not_tables(repo_root: Path) -> None:
    """Verify db.py defines only the shared MetaData + engine factory, not tables.

    A lasting design invariant: table DDL lives in the SMP-02 migration
    (op.create_table), never in db.py, which is just the shared MetaData holder
    and async engine factory. (The old "alembic/versions/ empty" assertion was
    dropped — that was a transient scaffold-time state SMP-02 correctly ends.)
    """
    # Check db.py only defines metadata, not tables
    db_path = repo_root / "src" / "study_tutor" / "knowledge" / "store" / "db.py"
    assert db_path.exists(), "db.py does not exist"

    db_content = db_path.read_text()

    # Should have metadata = MetaData()
    assert "metadata = MetaData()" in db_content, "db.py should define metadata"

    # Should NOT have Table(...) definitions
    assert "Table(" not in db_content, "db.py should not define any Table objects"

    # Should NOT have any declarative base classes with columns
    assert "Column(" not in db_content, "db.py should not define any Column objects"


# Integration test: Verify shared metadata is importable and usable
def test_shared_metadata_is_importable() -> None:
    """Verify the shared metadata object can be imported and used."""
    from study_tutor.knowledge.store.db import metadata

    # Should be a SQLAlchemy MetaData instance
    from sqlalchemy import MetaData
    assert isinstance(metadata, MetaData), "metadata should be a MetaData instance"

    # Should have no tables yet (schema lands in SMP-02)
    assert len(metadata.tables) == 0, "metadata should have no tables yet"


# Integration test: Verify make_engine creates async engine
def test_make_engine_creates_async_engine() -> None:
    """Verify make_engine() creates an async SQLAlchemy engine."""
    from study_tutor.knowledge.store.db import make_engine
    from sqlalchemy.ext.asyncio import AsyncEngine

    # Create an engine with a dummy DSN
    dsn = "postgresql+asyncpg://user:pass@localhost/db"
    engine = make_engine(dsn)

    # Should be an AsyncEngine instance
    assert isinstance(engine, AsyncEngine), "make_engine should return an AsyncEngine"

    # Clean up
    import asyncio
    asyncio.run(engine.dispose())
