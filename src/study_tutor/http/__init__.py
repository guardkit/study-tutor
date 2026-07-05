"""HTTP adapter package for mobile/voice app access (FEAT-APP-001).

This package provides the HTTP/WebSocket transport layer for the session API
(contract docs/design/contracts/API-session-http-binding.md). Built on Starlette,
it implements:

- Token-table auth layer (interim single-user mode, pre-Keycloak; TASK-APP1-02)
- Six session endpoints (TASK-APP1-03)
- Dev reset endpoint (TASK-APP1-03)
- Serve entrypoint with lifespan (TASK-APP1-04)
- StudentStore seed on startup (TASK-APP1-05)

The auth layer resolves Bearer tokens from the Authorization header to student_id
via a static config table (STUDY_TUTOR_HTTP_TOKENS env var). The unseeded-student
guard (ASSUM-001) refuses requests before any store write. No Keycloak/JWT imports —
table lookup only.
"""

from __future__ import annotations

__all__: list[str] = []
