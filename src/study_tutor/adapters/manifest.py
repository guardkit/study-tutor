"""Tutor agent manifest factory for NATS fleet registration.

Produces the ``AgentManifest`` that advertises study-tutor's four tutoring
commands as ``ToolCapability`` entries plus tutoring ``IntentCapability``
entries so jarvis's intent router can dispatch GCSE / revision / session
queries to gcse-tutor.

Tool parameter schemas mirror the adapter signatures in
``study_tutor/mcp/adapter.py`` and the FastMCP registration in
``study_tutor/mcp/server.py:19-58`` — single-source-of-truth contract that
TASK-NATS-PH1-004's CommandRouter dispatches against.

Intents include at least one entry as a Bug #5 regression guard:
``nats_core.manifest.InMemoryManifestRegistry.register`` rejects manifests
with an empty intents array.
"""
from __future__ import annotations

import logging

from nats_core.manifest import AgentManifest, IntentCapability, ToolCapability

logger = logging.getLogger(__name__)

__all__ = ["_tutor_manifest_factory"]


_TUTOR_TOOLS: list[ToolCapability] = [
    ToolCapability(
        name="tutor_start_session",
        description=(
            "Start a new tutoring session for the given student. Sync; "
            "returns session_id immediately; LLM model is warmed up in the "
            "background as fire-and-forget. Topic and player_model are "
            "optional overrides."
        ),
        parameters={
            "type": "object",
            "properties": {
                "student_id": {
                    "type": "string",
                    "description": "Student identifier (the learner's ID).",
                },
                "topic_override": {
                    "type": "string",
                    "description": (
                        "Optional override for the planned topic; defaults "
                        "to the student's current curriculum step."
                    ),
                },
                "player_model": {
                    "type": "string",
                    "description": (
                        "Optional LLM model override (e.g. for A/B "
                        "experiments)."
                    ),
                },
            },
            "required": ["student_id"],
        },
        returns=(
            "dict with session_id, plan, planner_status, and warmup status."
        ),
        risk_level="mutating",
        async_mode=False,
    ),
    ToolCapability(
        name="tutor_turn",
        description=(
            "Submit a user message for the given session_id and receive a "
            "tutor response. Sync, typically returns within 15s."
        ),
        parameters={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session identifier from tutor_start_session.",
                },
                "user_message": {
                    "type": "string",
                    "description": "The learner's message for this turn.",
                },
                "player_model": {
                    "type": "string",
                    "description": "Optional LLM model override for this turn.",
                },
            },
            "required": ["session_id", "user_message"],
        },
        returns="dict with reply text plus turn metadata (model used, latency).",
        risk_level="mutating",
        async_mode=False,
    ),
    ToolCapability(
        name="tutor_session_status",
        description="Sync; returns current session state for the given session_id.",
        parameters={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session identifier.",
                },
            },
            "required": ["session_id"],
        },
        returns="dict with session status, turn count, and current plan step.",
        risk_level="read_only",
        async_mode=False,
    ),
    ToolCapability(
        name="tutor_session_end",
        description="Sync; marks the session ended and releases resources.",
        parameters={
            "type": "object",
            "properties": {
                "session_id": {
                    "type": "string",
                    "description": "Session identifier.",
                },
            },
            "required": ["session_id"],
        },
        returns="dict with confirmation and final session metadata.",
        risk_level="mutating",
        async_mode=False,
    ),
]


_TUTOR_INTENTS: list[IntentCapability] = [
    IntentCapability(
        pattern="tutoring.*",
        signals=[
            "help me revise",
            "tutor me on",
            "explain",
            "session",
            "GCSE",
            "maths",
            "english",
            "biology",
            "physics",
            "chemistry",
            "history",
        ],
        confidence=0.90,
        description=(
            "GCSE-level tutoring sessions — start a session, take a "
            "teaching turn, check status, end."
        ),
    ),
]


def _tutor_manifest_factory(agent_id: str) -> AgentManifest:
    """Build a tutor :class:`AgentManifest` for the given agent_id.

    The agent_id must be kebab-case (``^[a-z][a-z0-9-]*$``) — that pattern
    is enforced by :class:`nats_core.manifest.AgentManifest` itself, so a
    non-conforming value raises :class:`pydantic.ValidationError` here.

    Returns an :class:`AgentManifest` with exactly four ``ToolCapability``
    entries (one per Phase-0 MCP tool) and at least one
    ``IntentCapability`` (Bug #5 regression guard:
    ``InMemoryManifestRegistry.register`` rejects empty intents arrays).
    """
    return AgentManifest(
        agent_id=agent_id,
        name="GCSE Tutor Agent",
        version="0.1.0",
        template="study-tutor-phase-1",
        trust_tier="specialist",
        required_permissions=[
            "graphiti:read",
            "graphiti:write",
            "filesystem:read",
        ],
        max_concurrent=4,
        intents=list(_TUTOR_INTENTS),
        tools=list(_TUTOR_TOOLS),
    )
