"""Repo-wide pytest safety guard against wiping a durable database.

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
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy.engine import make_url

#: Hosts a throwaway test DB may live on. Anything else is treated as durable.
_LOOPBACK_DB_HOSTS = {"localhost", "127.0.0.1", "::1", ""}


def pytest_configure(config: pytest.Config) -> None:
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
