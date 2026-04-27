"""MCP adapter for the tutor role (Phase 0).

Registers four tools on the FastMCP server:

* ``tutor_start_session`` — sync classification (per ADR-ARCH-017); returns
  ``session_id`` synchronously while a warm-up LLM call pre-loads model
  weights as fire-and-forget. No still-running task to poll. Phase 1 may
  revert to long-running if the Graphiti student-model read at session
  start exceeds ~3s.
* ``tutor_turn`` — sync; generates one tutor reply per user message.
* ``tutor_session_status`` — sync; pure read of session state.
* ``tutor_session_end`` — sync; marks session ended (Phase 0 no-op beyond
  status flip; Phase 1 adds async Graphiti write per DEC-02).

SR-03: every handler resolves the provider via ``_default_player_model()``
at call time — no module-level provider hard-coding.

SR-07: ``tutor_session_end`` description is *only* ``"marks session ended"``.
The Phase 1 Graphiti write is a ``# TODO(phase-1)`` in code, not user-facing text.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from study_tutor.llm.client import LLMClient, _default_player_model
from study_tutor.roles.loader import RoleConfig
from study_tutor.session.tutor_session import (
    SessionNotFoundError,
    SessionStore,
    get_default_store,
)

logger = logging.getLogger(__name__)


class MCPAdapter:
    """Dispatches MCP tool calls for the tutor role."""

    def __init__(
        self,
        role_config: RoleConfig,
        store: SessionStore | None = None,
    ) -> None:
        self._role = role_config
        self._store = store or get_default_store()
        self._player_prompt = role_config.load_player_prompt()
        # Track warm-up task so pytest/GC don't complain about orphans.
        self._warmup_tasks: set[asyncio.Task[Any]] = set()

    async def tutor_start_session(
        self,
        subject: str,
        topic: str | None = None,
        player_model: str | None = None,
    ) -> dict[str, Any]:
        """Create a session and warm up the LLM in the background.

        Returns ``{"session_id": "<uuid>"}`` in well under one second. A
        fire-and-forget ``asyncio.create_task`` primes the Ollama model so
        the first ``tutor_turn`` doesn't pay cold-start latency.
        """
        session = self._store.create(subject=subject, topic=topic)
        provider = player_model or _default_player_model()
        task = asyncio.create_task(
            self._warm_up(provider), name=f"warmup-{session.session_id}"
        )
        self._warmup_tasks.add(task)
        task.add_done_callback(self._warmup_tasks.discard)
        return {"session_id": session.session_id}

    async def tutor_turn(
        self,
        session_id: str,
        user_message: str,
        player_model: str | None = None,
    ) -> dict[str, Any]:
        """Generate one tutor reply for ``user_message`` within the session."""
        try:
            session = self._store.get(session_id)
        except SessionNotFoundError:
            return _session_not_found(session_id)

        if session.status == "ended":
            return {
                "error": f"Session '{session_id}' has ended.",
                "error_type": "SessionEnded",
            }

        provider = player_model or _default_player_model()
        client = LLMClient(provider=provider)

        self._store.append_turn(session_id, "user", user_message)

        # Generate in a worker thread so async MCP framework isn't blocked
        # by the synchronous httpx call inside LLMClient.generate().
        response = await asyncio.to_thread(
            client.generate, user_message, self._player_prompt
        )

        self._store.append_turn(session_id, "tutor", response)
        return {"tutor_response": response}

    async def tutor_session_status(self, session_id: str) -> dict[str, Any]:
        """Return current session state."""
        try:
            session = self._store.get(session_id)
        except SessionNotFoundError:
            return _session_not_found(session_id)

        return {
            "session_id": session.session_id,
            "status": session.status,
            "turn_count": len(session.turns),
            "started_at": session.started_at.isoformat(),
        }

    async def tutor_session_end(self, session_id: str) -> dict[str, Any]:
        """Mark the session ended.

        Phase 0: flip status only. Phase 1 adds a Graphiti write here per
        DEC-02 — kept out of the tool description (SR-07).
        """
        # TODO(phase-1): add async Graphiti write per DEC-02
        try:
            self._store.end(session_id)
        except SessionNotFoundError:
            return _session_not_found(session_id)

        return {"session_id": session_id, "status": "ended"}

    async def _warm_up(self, provider: str) -> None:
        """Fire an empty generate() to prime the Ollama model into memory."""
        try:
            client = LLMClient(provider=provider)
            await asyncio.to_thread(client.generate, "", None)
        except Exception as exc:  # noqa: BLE001 — warm-up must never crash
            logger.debug("Warm-up call failed (non-fatal): %s", exc)


def _session_not_found(session_id: str) -> dict[str, Any]:
    return {
        "error": f"Session '{session_id}' not found.",
        "error_type": "SessionNotFoundError",
    }
