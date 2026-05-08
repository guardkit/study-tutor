"""Tutor role — fleet registration entry point (TASK-NATS-PH1-003).

Importing this sub-package registers the ``tutor`` role with the in-process
fleet registry (``study_tutor.roles.registry``). The package's only side
effect at import time is the ``register_role`` call below; the constants
above it (``TOOL_TO_COMMAND``) are deliberately exported so router tests
(TASK-NATS-PH1-004) can assert against the canonical alias map without
having to go through the registry.

The ``TOOL_TO_COMMAND`` map is the **single source of truth** for the
Bug #2 fix: incoming MCP tool names (``tutor_start_session`` etc.) must
resolve to the canonical internal command names (``start_session`` etc.)
before the router's dispatch table is consulted. Keep the map *here* —
not in the router — so the registry test and the router test can both
assert against it independently.
"""

from __future__ import annotations

from study_tutor.roles.registry import register_role

# Mapping: MCP tool name -> canonical internal command name.
# Keys must match the tool names exposed by ``study_tutor.mcp.adapter``;
# values must match dispatch keys in the router's ``command_map``.
TOOL_TO_COMMAND: dict[str, str] = {
    "tutor_start_session": "start_session",
    "tutor_turn": "tutor_turn",
    "tutor_session_status": "session_status",
    "tutor_session_end": "end_session",
}

# Side effect: register on import. ``register_role`` is idempotent for
# identical mappings, so re-imports (e.g. via _ensure_roles_registered)
# are safe.
register_role(name="tutor", tool_to_command=TOOL_TO_COMMAND)


__all__ = ["TOOL_TO_COMMAND"]
