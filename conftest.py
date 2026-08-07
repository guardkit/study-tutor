"""Repo-wide pytest safety guards for durable stores.

Guard 1 — Postgres (2026-07-09 NAS wipe).
Several tests read ``STUDY_TUTOR_PG_DSN`` and run destructive database
operations: ``tests/knowledge/store/test_migration_schema.py`` used to run
``alembic downgrade base`` (drops the whole schema), and integration fixtures
``DELETE`` / ``TRUNCATE`` tables in setup. Pointing any of that at a durable
store wipes it — which is exactly what happened to the NAS student store on
2026-07-09, when the suite ran with ``STUDY_TUTOR_PG_DSN`` set to the NAS.

This guard makes that impossible: if ``STUDY_TUTOR_PG_DSN`` is set to a
non-loopback host, the whole test session aborts *before any test runs*. Tests
that need a real database either self-provision a throwaway localhost container
(``test_migration_schema.py``, ``tests/integration/.../conftest.py``) or read a
loopback DSN — neither of which trips this guard. Override with
``STUDY_TUTOR_ALLOW_DESTRUCTIVE_DB_TESTS=1`` only for a DSN you are certain is
disposable.

Guard 2 — ChromaDB baked store (2026-08-07 T2 store-isolation leak).
``study_tutor.cli.rag_wiring.build_rag_providers`` defaults its persist dir to
the RELATIVE path ``data/chroma`` when ``CHROMA_PERSIST_DIR`` is unset. Once
the ``[rag]`` extra makes ``chromadb`` importable, every test that reaches the
serve boot path — in-process ``CliRunner().invoke(cli, ["serve"])`` or the
subprocess boots in ``tests/unit/http/test_serve_http.py`` /
``tests/unit/mcp/test_stdio_discipline.py`` (which all ``os.environ.copy()``)
— opens the checkout's REAL baked store and appends a row to chroma's internal
``acquire_write`` bookkeeping table per fresh-process open (7 rows across the
suite as measured 2026-08-07; content untouched, bytes changed).

The guard points ``CHROMA_PERSIST_DIR`` at a guaranteed-nonexistent path when
the env var is unset, so ``build_rag_providers`` takes its documented
``rag_disabled reason=persist_dir_missing`` graceful path instead of opening
the store. Tests that need a real/fake store all set the env var or pass an
explicit persist dir themselves (verified 2026-08-07: no test delenvs it).
An operator who explicitly exports ``CHROMA_PERSIST_DIR`` keeps their value —
same posture as the DSN guard: absent config is made safe, explicit config is
respected. Regression pin:
``tests/unit/http/test_serve_http_chroma_isolation.py``.
"""

from __future__ import annotations

import os
import uuid

import pytest
from sqlalchemy.engine import make_url

#: Hosts a throwaway test DB may live on. Anything else is treated as durable.
_LOOPBACK_DB_HOSTS = {"localhost", "127.0.0.1", "::1", ""}


def pytest_configure(config: pytest.Config) -> None:
    """Apply both guards before any test (or spawned subprocess) runs."""
    _guard_chroma_persist_dir()
    _guard_postgres_dsn()


def _guard_chroma_persist_dir() -> None:
    """Point an UNSET ``CHROMA_PERSIST_DIR`` at a nonexistent path.

    Closes the T2 store-isolation leak (known-issues.md, 2026-08-07): with
    ``chromadb`` importable and the env var unset, any test reaching
    ``build_rag_providers`` opens the checkout's real ``data/chroma`` store
    via the relative default and mutates its ``acquire_write`` table. The
    nonexistent path routes the wiring to its ``persist_dir_missing``
    graceful branch. Subprocess-spawning tests inherit this because they
    build their env from ``os.environ.copy()``.
    """
    if not os.environ.get("CHROMA_PERSIST_DIR"):
        os.environ["CHROMA_PERSIST_DIR"] = os.path.join(
            os.sep, "nonexistent", f"chroma-test-guard-{uuid.uuid4().hex}"
        )


def _guard_postgres_dsn() -> None:
    """Abort the session if STUDY_TUTOR_PG_DSN points at a non-loopback host."""
    dsn = os.environ.get("STUDY_TUTOR_PG_DSN")
    if not dsn or os.environ.get("STUDY_TUTOR_ALLOW_DESTRUCTIVE_DB_TESTS") == "1":
        return

    try:
        host = (make_url(dsn).host or "").lower()
    except Exception:
        host = None  # unparseable → cannot verify it is a throwaway; refuse

    if host not in _LOOPBACK_DB_HOSTS:
        pytest.exit(
            f"REFUSING to run the test suite: STUDY_TUTOR_PG_DSN points at "
            f"non-loopback host {host!r}. The suite runs destructive DB ops "
            "(alembic downgrade base drops the schema; fixtures DELETE/TRUNCATE) "
            "and would wipe that database (this nuked the NAS store 2026-07-09). "
            "Unset STUDY_TUTOR_PG_DSN (tests self-provision throwaway DBs) or set "
            "STUDY_TUTOR_ALLOW_DESTRUCTIVE_DB_TESTS=1 to override for a disposable DSN.",
            returncode=2,
        )
