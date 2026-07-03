"""Alembic migration environment for study-tutor Postgres StudentStore.

TASK-SMP-01 / FEAT-SMP-001 (2026-07-03): Async migration support for the
Postgres StudentStore. This file is executed by the `alembic` CLI and configures
the migration context.

Design intent:
- Uses SQLAlchemy async engine (asyncpg driver) for all migrations.
- Reads DSN from STUDY_TUTOR_PG_DSN environment variable.
- ``target_metadata`` is set to the shared metadata object from
  ``study_tutor.knowledge.store.db`` so autogenerate can detect schema changes.
- ``run_migrations_online()`` is the entry point called by ``alembic upgrade``,
  ``alembic downgrade``, etc.
"""
from __future__ import annotations

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# This is the Alembic Config object, which provides access to the values
# within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import the shared metadata object from the store.
# This is the target_metadata that Alembic will use for autogenerate.
# SMP-02 will add table definitions that populate this metadata.
from study_tutor.knowledge.store.db import metadata  # noqa: E402

target_metadata = metadata

# Read DSN from environment variable.
# The runbook sets STUDY_TUTOR_PG_DSN before calling `alembic upgrade head`.
# Format: postgresql://user:pass@host:port/dbname (we'll transform to asyncpg)
dsn = os.getenv("STUDY_TUTOR_PG_DSN")
if dsn:
    # Transform postgresql:// to postgresql+asyncpg:// for async support.
    # If the DSN already specifies a driver (e.g., postgresql+asyncpg://),
    # leave it as-is.
    if dsn.startswith("postgresql://") and "+asyncpg://" not in dsn:
        dsn = dsn.replace("postgresql://", "postgresql+asyncpg://", 1)
    config.set_main_option("sqlalchemy.url", dsn)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL and not an Engine, though an
    Engine is acceptable here as well. By skipping the Engine creation we don't
    even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the provided connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create an async engine and run migrations in async mode.

    This is the main entry point for async migrations. It creates an async
    engine from the config, acquires a connection, and runs migrations.
    """
    # Build async engine from config.
    # The config's sqlalchemy.url is set above from STUDY_TUTOR_PG_DSN.
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        # Run migrations synchronously within the async connection context.
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine and associate a connection
    with the context. This is the mode used by `alembic upgrade`, `alembic
    downgrade`, etc.

    For async engines (asyncpg), we use asyncio.run() to execute the async
    migration function.

    If no DSN is configured and we're running a command that doesn't need
    a database connection (like `history`), we skip the connection attempt.
    """
    url = config.get_main_option("sqlalchemy.url")
    # Check for both None and empty string (alembic.ini sets it to empty if not configured)
    if not url or url.strip() == "":
        # No DSN configured - some commands (like `history`) work without it.
        # They just query the local versions directory, not the database.
        # For commands that need a connection (like `upgrade`), this will
        # fail gracefully with a clear error message.
        return

    asyncio.run(run_async_migrations())


# Determine which mode to run in based on context.
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
