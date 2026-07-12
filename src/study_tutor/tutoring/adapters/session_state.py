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
class TranscriptTurn:
    """One prior transcript turn threaded into the Player generation prompt.

    The §2.6 in-session-memory carrier: a compact ``(role, content)`` pair
    rehydrated from the durable store by the service and folded into the
    Player's transcript window at prompt-assembly time. Deliberately
    stdlib-only (no Pydantic) to match :class:`SessionState`; ``role`` is
    the store's turn role (``"user"`` / ``"tutor"``).
    """

    role: str
    content: str


@dataclass(frozen=True)
class SessionState:
    """Typed boundary object passed from MCP into the tutoring orchestrator.

    Field shape is fixed by the §4 integration contract — adding or
    renaming a field is a breaking change for the Player and Coach
    adapters and must be co-ordinated across TASK-LCA-001 / TASK-LCA-002.

    S-R4 (spec §2.5/§2.6) adds the *player-context* fields below. They are
    populated **once, in the service** (``SessionService
    .build_turn_session_state``) from a single student-state read per turn
    plus a transcript rehydration — never assembled in a transport adapter.
    Every field defaults to its empty value so pre-S-R4 construction sites
    (and tests) that omit them keep the exact prior behaviour.
    """

    session_id: str
    student_id: str
    text_name: str | None = None
    topic: str | None = None
    focus_aos: tuple[str, ...] = field(default_factory=tuple)
    mode: str = "tutor"
    #: §2.5 — the confidence band for this session's ``topic`` (design §6.1
    #: literal: ``struggling`` / ``developing`` / ``secure`` / ``mastered``),
    #: or ``None`` when the topic has no confidence row yet.
    topic_confidence_band: str | None = None
    #: §2.5 — up to 3 weakest below-Mastered topics (ascending confidence).
    weakest_topics: tuple[str, ...] = field(default_factory=tuple)
    #: §2.5 — up to 3 recent misconception texts to revisit.
    recent_misconceptions: tuple[str, ...] = field(default_factory=tuple)
    #: §2.5 — the learner's GCSE grade target (GOAL.md §7; default Grade 6).
    grade_target: str | None = None
    #: §2.6 — the in-session memory window: prior transcript turns
    #: (oldest → newest), rehydrated from the durable store by the service.
    #: The Player truncates this to the last N turns under a token cap.
    transcript: tuple[TranscriptTurn, ...] = field(default_factory=tuple)
