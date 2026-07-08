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
            "Start an interactive GCSE-level tutoring session. Covers "
            "English Literature, English Language, Maths, Sciences, "
            "History, and other GCSE subjects using Socratic dialogue "
            "scaffolded against AO1/AO2/AO3/AO4 assessment objectives. "
            "Use whenever a learner asks for tutoring, revision, or "
            "subject-specific coaching at GCSE level. Sync; returns "
            "session_id immediately; LLM model is warmed up in the "
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
            "Take one teaching turn in an active GCSE tutoring session. "
            "Submits the learner's response and returns a Socratic "
            "coaching reply that scaffolds the learner toward "
            "grade-level analysis using AO1 (text knowledge), AO2 "
            "(language and structure), and where appropriate AO3 "
            "(context) and AO4 (comparison). Use after "
            "tutor_start_session whenever the learner sends a new "
            "response in an ongoing English Literature, English "
            "Language, Maths, Sciences, or History tutoring exchange. "
            "Sync, typically returns within 15s."
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
        description=(
            "Check the current state of an active GCSE tutoring session — "
            "turn count, current plan step, coaching progress, and AO "
            "coverage so far. Use to verify a session is healthy before "
            "submitting more learner responses. Sync; read-only; "
            "returns current session state for the given session_id."
        ),
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
        description=(
            "End an active GCSE tutoring session — captures a final "
            "session summary covering AO1/AO2/AO3/AO4 progress and "
            "releases planner/LLM resources. Use when a learner "
            "indicates they are finished revising or want to wrap up "
            "the English Literature, Maths, or other GCSE subject "
            "tutoring exchange. Sync; mutating; marks the session "
            "ended and releases resources."
        ),
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
            "filesystem:read",
        ],
        max_concurrent=4,
        intents=list(_TUTOR_INTENTS),
        tools=list(_TUTOR_TOOLS),
    )
