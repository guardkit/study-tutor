"""study-tutor App Access session layer.

FEAT-SMP-003 ([ADR-ARCH-023] + ``docs/design/contracts/API-session-cross-device.md``):
the transport-agnostic :class:`SessionService` that makes sessions durable,
student-keyed, and resumable over the Postgres ``StudentStore``, plus the typed
errors and the injection seam both the MCP and future HTTP/WS adapters share.

Layout mirrors ``knowledge/store/``:

- :mod:`service` — the :class:`SessionService` + result DTOs + injected-loop types.
- :mod:`errors` — the closed typed-exception set the transports map.
- :mod:`provider` — the ``set_/get_/reset_session_service`` injection seam.
- :mod:`tutor_session` — the legacy in-memory ``SessionStore`` (retired once the
  adapters are repointed at the service; deleted in FEAT-SMP-004).

Wave map: FEAT-SMP-003 implements the durable adapter behind the service and
repoints the MCP adapter at it; FEAT-SMP-004 deletes ``tutor_session`` +
graphiti plumbing. See
``docs/research/ideas/student-model-postgres-migration-scope-and-build-plan.md``.
"""
from __future__ import annotations

from study_tutor.session.errors import (
    SessionEnded,
    SessionForbidden,
    SessionNotFoundError,
    SessionServiceError,
    Unauthenticated,
)
from study_tutor.session.provider import (
    get_session_service,
    reset_session_service,
    set_session_service,
)
from study_tutor.session.service import (
    EndSessionResult,
    ReplyFn,
    ReplyStreamFn,
    ResumeResult,
    SessionCompletion,
    SessionService,
    SessionStatusView,
    StartSessionResult,
    TurnEvent,
    TurnResult,
    TutorReply,
)

__all__ = [
    "EndSessionResult",
    "ReplyFn",
    "ReplyStreamFn",
    "ResumeResult",
    "SessionCompletion",
    "SessionEnded",
    "SessionForbidden",
    "SessionNotFoundError",
    "SessionService",
    "SessionServiceError",
    "SessionStatusView",
    "StartSessionResult",
    "TurnEvent",
    "TurnResult",
    "TutorReply",
    "Unauthenticated",
    "get_session_service",
    "reset_session_service",
    "set_session_service",
]
