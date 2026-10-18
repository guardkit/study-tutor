"""Typed exceptions for the App Access session layer (FEAT-SMP-003).

The :class:`~study_tutor.session.service.SessionService` raises these; the
transports (the MCP adapter today, the HTTP/WS adapter later) catch them at the
boundary and map to the flat ``{"error", "error_type"}`` envelope
(API-tutoring §4) or an HTTP status. The ``error_type`` set is a **closed
contract** (``docs/design/contracts/API-session-cross-device.md`` §9 +
API-tutoring §4): ``SessionNotFoundError``, ``SessionEnded``,
``SessionForbidden``, ``Unauthenticated``. Adding one requires ``/design-refine``.
Revision 3 (2026-10-18) added ``TutorBusy`` on the turn verbs
(``docs/design/tutor-busy-and-history-repair-2026-10-18.md``).

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


class TutorBusy(SessionServiceError):
    """The tutor model is busy or refused to load (contract §9 Revision 3).

    Raised by the service when the reply's upstream model answered 429
    (already serving), 502 (llama-swap could not start it — ``mem-check``
    refused the load) or 503. Retryable: the learner can send the turn again.
    """

    #: Learner-facing copy — the wire ``error`` for every transport.
    MESSAGE = "The tutor is busy right now. Please try again in a minute."

    def __init__(self, message: str = MESSAGE) -> None:
        super().__init__(message)


__all__ = [
    "SessionEnded",
    "SessionForbidden",
    "SessionNotFoundError",
    "SessionServiceError",
    "TutorBusy",
    "Unauthenticated",
]
