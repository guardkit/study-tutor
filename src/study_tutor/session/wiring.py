"""Session service wiring helper for startup (TASK-SMP3-04).

This module owns the side-effect of resolving the single-user identity and
constructing ``SessionService``, then wiring it into the runtime via
:func:`study_tutor.session.provider.set_session_service`.

Mirrors the posture of :func:`study_tutor.knowledge.store.wiring.build_student_store` —
the boot sequence calls this exactly once at each adapter construction site
(``serve`` and ``_build_nats_runtime``), before the orchestrator starts, so the
session service is live and ready for durable cross-device session operations.

Env vars consumed:

* ``STUDY_TUTOR_STUDENT_ID`` — Single-user identity (default ``"lilymay"``).
  This is the OWNERSHIP key kept SEPARATE from the ``tutor_start_session``
  planner-slug arg (ASSUM-001).
* ``STUDY_TUTOR_PG_DSN`` — Postgres connection string. When absent, the wiring
  is skipped (no raise; ``get_session_service()`` stays None) so DSN-less
  dev/CI degrades gracefully.
"""
from __future__ import annotations

import logging
import os

from study_tutor.session.provider import set_session_service
from study_tutor.session.service import SessionService

logger = logging.getLogger(__name__)


def resolve_student_id() -> str:
    """Resolve the single-user identity from environment.

    Returns the configured student ID from the ``STUDY_TUTOR_STUDENT_ID``
    environment variable, defaulting to ``"lilymay"`` if unset. This is the
    OWNERSHIP key for session guards, kept independent of the MCP tool's
    ``student_id`` planner-slug argument (ASSUM-001).

    Returns
    -------
    str
        The configured student ID. Always returns a string (empty string if
        explicitly set to empty, ``"lilymay"`` if unset).

    Notes
    -----
    Called during session service construction. The resolved identity is used
    for all ownership guards (:class:`SessionForbidden` when session's
    ``student_id`` ≠ the caller).
    """
    return os.environ.get("STUDY_TUTOR_STUDENT_ID", "lilymay")


def build_session_service() -> None:
    """Build the SessionService and wire it into the runtime.

    Side-effect-only: returns ``None``. Resolves the ``StudentStore`` via
    :func:`study_tutor.knowledge.store.provider.get_student_store`, constructs
    a ``SessionService`` (which composes the store's session methods), and
    registers it via ``set_session_service``.

    This function is called conditionally from both ``serve`` and
    ``_build_nats_runtime`` in ``cli/main.py`` — only when
    ``STUDY_TUTOR_PG_DSN`` is set. When the DSN is absent, this function is
    NOT called (the guard belongs in main.py, not here), and
    ``get_session_service()`` remains None (adapters degrade gracefully).

    Notes
    -----
    Called once at each adapter startup (MCP and NATS paths), after
    ``build_student_store()`` has wired the Postgres store. The SessionService
    resolves the store lazily via the provider, so there's no circular
    dependency or engine initialization issue.

    The function logs a structured event (``event=session_service_wired``)
    without logging any DSN credentials (AC-004).
    """
    # Construct the SessionService (it resolves the store via provider internally)
    service = SessionService()

    # Register it in the provider slot
    set_session_service(service)

    logger.info("event=session_service_wired")
