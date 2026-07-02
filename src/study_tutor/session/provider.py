"""Injection seam for the ``SessionService`` (FEAT-SMP-003).

Mirrors ``knowledge.store.provider`` byte-for-byte: the shared
``SessionService`` is wired **once at orchestrator startup** and both the MCP
adapter and the future HTTP/WS adapter resolve it here, rather than each
constructing its own. This is the second level of the two-level injection — the
service itself resolves the ``StudentStore`` via ``knowledge.store.provider``.

``None`` means "no service wired" — an adapter that resolves ``None`` should fail
fast at boot (the CLI wires this before serving), not paper over it per request.
"""
from __future__ import annotations

from study_tutor.session.service import SessionService

# Module-level single slot, owned by startup wiring (same posture as
# ``store.provider._student_store``).
_session_service: SessionService | None = None


def set_session_service(service: SessionService) -> None:
    """Install the process-wide ``SessionService``. Called once at startup;
    tests rebind per case."""
    global _session_service
    _session_service = service


def get_session_service() -> SessionService | None:
    """Return the wired service, or ``None`` if none is installed."""
    return _session_service


def reset_session_service() -> None:
    """Remove the installed service (test teardown helper)."""
    global _session_service
    _session_service = None


__all__ = ["get_session_service", "reset_session_service", "set_session_service"]
