"""Typed ``SessionState`` boundary object (TASK-LCA-003).

``SessionState`` replaces the opaque ``session_state: Any`` dict that flowed
through ``Player.respond`` / ``Player.revise`` / ``Coach.evaluate`` in the
Phase 0 wiring. It is the producer side of the §4 SessionState integration
contract consumed by TASK-LCA-001 (Player adapter) and TASK-LCA-002 (Coach
adapter).

Frozen immutability is load-bearing: per-turn factory isolation (AC-LCA-01)
relies on ``SessionState`` being non-mutable so a Coach observation cannot
write back into the object and leak into another concurrent session. The
``@dataclass(frozen=True)`` machinery raises ``FrozenInstanceError`` on any
attribute assignment and produces a stable ``__hash__`` derived from the
field values, which downstream adapters can use to key per-turn caches.

Optional fields default to ``None`` / ``()`` / ``"tutor"`` per ASSUM-LCA-007
so the MCP construction site at ``study_tutor.mcp.adapter.MCPAdapter
.tutor_turn`` can build a minimal ``SessionState`` even when the cached
``SessionPlan`` is the baseline-degraded one (no ``text_name``, empty
``focus_aos``).

This module is intentionally stdlib-only — no Pydantic — to match the
existing ``SessionPlan`` / ``TutorSession`` data-model layer.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SessionState:
    """Typed boundary object passed from MCP into the tutoring orchestrator.

    Field shape is fixed by the §4 integration contract — adding or
    renaming a field is a breaking change for the Player and Coach
    adapters and must be co-ordinated across TASK-LCA-001 / TASK-LCA-002.
    """

    session_id: str
    student_id: str
    text_name: str | None = None
    topic: str | None = None
    focus_aos: tuple[str, ...] = field(default_factory=tuple)
    mode: str = "tutor"
