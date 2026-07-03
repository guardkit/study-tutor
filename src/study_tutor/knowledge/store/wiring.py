"""Student store wiring helper for startup (TASK-SMP-03).

This module owns the side-effect of reading the Postgres DSN from the
environment, constructing ``PostgresStudentStore``, and wiring it into the
runtime via :func:`study_tutor.knowledge.store.provider.set_student_store`.

Mirrors the posture of :func:`study_tutor.cli.rag_wiring.build_rag_providers` —
the boot sequence calls this exactly once, before the orchestrator starts, so
the async engine / connection pool is live and ready for W1 write methods.

Env vars consumed:

* ``STUDY_TUTOR_PG_DSN`` — Postgres connection string (required at boot; the
  store coerces ``postgresql://`` to ``postgresql+asyncpg://`` internally per
  TASK-SMP-03). Missing var is a boot error (not a silent skip).
"""
from __future__ import annotations

import logging
import os

from study_tutor.knowledge.store.postgres import PostgresStudentStore
from study_tutor.knowledge.store.provider import set_student_store

logger = logging.getLogger(__name__)


def build_student_store() -> None:
    """Build the Postgres student store and wire it into the runtime.

    Side-effect-only: returns ``None``. Reads ``STUDY_TUTOR_PG_DSN`` from the
    environment, constructs a ``PostgresStudentStore`` (which builds a shared
    async engine from the DSN), and registers it via ``set_student_store``.

    Raises
    ------
    KeyError
        When ``STUDY_TUTOR_PG_DSN`` is not set in the environment. This is a
        boot error — the store cannot be wired without a database connection
        string.

    Notes
    -----
    Called once at orchestrator startup, before any write methods
    (``record_session_completion``, ``record_misconception``,
    ``apply_confidence_update``) are invoked. The async engine is built during
    ``PostgresStudentStore.__init__`` and reused for every connection.

    The DSN is coerced to the ``postgresql+asyncpg://`` dialect inside
    ``PostgresStudentStore.__init__`` (TASK-SMP-03 AC-003), so the environment
    can publish a plain ``postgresql://`` DSN (as the W0 runbook does) and the
    engine will still load the asyncpg driver.
    """
    # Missing DSN is a boot error — we cannot silently skip wiring
    dsn = os.environ["STUDY_TUTOR_PG_DSN"]

    logger.info(
        "event=student_store_wiring dsn_host=%s",
        _extract_host_from_dsn(dsn),
    )

    # Build the store (creates the async engine internally)
    store = PostgresStudentStore(dsn)

    # Register it in the provider slot
    set_student_store(store)

    logger.info("event=student_store_wired")


def _extract_host_from_dsn(dsn: str) -> str:
    """Extract the host portion from a DSN for logging (no credentials)."""
    try:
        from sqlalchemy.engine import make_url

        url = make_url(dsn)
        return f"{url.host}:{url.port}" if url.port else str(url.host)
    except Exception:  # noqa: BLE001 — log-formatting fallback
        return "<parse-error>"


__all__ = ["build_student_store"]
