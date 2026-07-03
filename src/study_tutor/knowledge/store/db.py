"""Shared SQLAlchemy metadata and base for the Postgres StudentStore.

TASK-SMP-01 / FEAT-SMP-001 (2026-07-03): This module exports the shared
``metadata`` object that Alembic's ``env.py`` references for autogenerate
and that declarative table definitions (landing in SMP-02) will use.

The metadata object is the single source of truth for all table schemas;
Alembic migrations are generated from it via ``alembic revision --autogenerate``.

Design intent:
- ``metadata`` is a module-level singleton shared across the process.
- No tables are defined here yet (schema lands in SMP-02).
- ``create_async_engine`` is the entrypoint for building the connection pool
  from a DSN (``postgresql+asyncpg://...``).
"""
from __future__ import annotations

from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

# Shared metadata object for all StudentStore tables.
# Alembic's env.py sets ``target_metadata = metadata`` to enable autogenerate.
# Table definitions (SMP-02) will reference this via ``metadata=metadata``.
metadata = MetaData()


def make_engine(dsn: str, *, echo: bool = False) -> AsyncEngine:
    """Create an async SQLAlchemy engine from a DSN.

    Args:
        dsn: Postgres connection string with asyncpg driver, e.g.
             ``postgresql+asyncpg://user:pass@host:port/dbname``
        echo: If True, log all SQL statements (useful for debugging).

    Returns:
        AsyncEngine configured for the Postgres StudentStore.
    """
    return create_async_engine(dsn, echo=echo, future=True)


__all__ = ["metadata", "make_engine"]
