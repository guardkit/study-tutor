"""Typed exceptions for the App Access session layer (FEAT-SMP-003).

The :class:`~study_tutor.session.service.SessionService` raises these; the
transports (the MCP adapter today, the HTTP/WS adapter later) catch them at the
boundary and map to the flat ``{"error", "error_type"}`` envelope
(API-tutoring §4) or an HTTP status. The ``error_type`` set is a **closed
contract** (``docs/design/contracts/API-session-cross-device.md`` §9 +
API-tutoring §4): ``SessionNotFoundError``, ``SessionEnded``,
``SessionForbidden``, ``Unauthenticated``. Adding one requires ``/design-refine``.

Reconciliation (design-review #7): a ``SessionNotFoundError(KeyError)`` copy lives
in ``session.tutor_session`` (the in-memory store being retired). **This is the
canonical home.** The FEAT-SMP-003 adapter change must import
``SessionNotFoundError`` from here and ``except`` this exact class — catching a
``KeyError`` *sibling* does not catch the other. This class subclasses ``KeyError``
too, so any residual ``except KeyError`` keeps working through the transition; the
``tutor_session`` copy is deleted when the in-memory store goes (FEAT-SMP-004).
"""
from __future__ import annotations


class SessionServiceError(Exception):
    """Base for every App Access session error."""


class SessionNotFoundError(SessionServiceError, KeyError):
    """No session with the given ``session_id`` (the store returned ``None``)."""


class SessionEnded(SessionServiceError):
    """A mutating verb was called on an ``ended`` session.

    ``session_status`` is the one §9 carve-out — it reads ended sessions too.
    """


class SessionForbidden(SessionServiceError):
    """The session's ``student_id`` does not match the authenticated caller."""


class Unauthenticated(SessionServiceError):
    """Missing/invalid credential.

    Raised at the transport **auth layer**, before any service call — never by
    the service itself (the service only ever sees an already-resolved
    ``student_id``). HTTP/WS only; never emitted in interim single-user mode.
    """


__all__ = [
    "SessionEnded",
    "SessionForbidden",
    "SessionNotFoundError",
    "SessionServiceError",
    "Unauthenticated",
]
