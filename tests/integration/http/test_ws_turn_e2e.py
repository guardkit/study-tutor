"""End-to-end WS turn against the fake LLM (S-R4 §2.7).

Proves the WS streaming path now drives a REAL streaming ``ReplyStreamFn``
(the async-iterator product wired by ``_build_http_reply_stream_fn_factory``)
rather than the non-streaming ``ReplyFn`` it wrongly passed before: a single
``{"type":"turn"}`` frame streams tutor tokens from the (fake) LLM through the
core ``SessionService.turn_stream`` and persists the tutor turn.
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock, patch

import pytest
from starlette.testclient import TestClient

from study_tutor.cli.main import _build_http_reply_stream_fn_factory
from study_tutor.http.app import create_app
from study_tutor.http.auth import HTTPAuthConfig
from study_tutor.session.service import SessionService
from study_tutor.tutoring.adapters.llm_player_adapter import LLMPlayerAdapter
from study_tutor.roles.loader import RoleConfig
from study_tutor.voice.config import VoiceConfig
from tests.unit.knowledge.store.fakes import FakeStudentStore


_FAKE_TOKENS = ["Ambi", "tion ", "drives ", "the ", "plot."]


class _FakeStreamingLLMClient:
    """Stand-in for the fake LLM: yields a fixed token sequence."""

    def __init__(self, provider: str) -> None:
        self.provider = provider

    async def generate_stream(
        self,
        prompt: str,
        system: str | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> AsyncIterator[str]:
        for token in _FAKE_TOKENS:
            yield token


class _StreamingOrchestrator:
    """Minimal orchestrator exposing the §2.7 token-yield seam.

    Delegates straight to the REAL ``LLMPlayerAdapter.respond_stream`` (which
    weaves the §2.5 context + §2.6 window and calls the fake LLM), so the WS
    e2e exercises the production player path without a background Coach.
    """

    def __init__(self, player: LLMPlayerAdapter) -> None:
        self._player = player

    async def run_turn_stream_tokens(
        self, *, session_state: Any, learner_message: str
    ) -> AsyncIterator[str]:
        async for token in self._player.respond_stream(
            session_state=session_state, learner_message=learner_message
        ):
            yield token

    async def run_turn_stream_verified(
        self, *, session_state: Any, learner_message: str
    ) -> AsyncIterator[str]:
        # The production factory drives the ADR-ARCH-027 verified stream;
        # this e2e pins service wiring + persistence, not verification —
        # identity pass-through keeps the token flow observable.
        async for token in self.run_turn_stream_tokens(
            session_state=session_state, learner_message=learner_message
        ):
            yield token


@pytest.fixture
def role_config(tmp_path):
    prompt_path = tmp_path / "player.md"
    prompt_path.write_text("You are a GCSE tutor.", encoding="utf-8")
    return RoleConfig(
        id="tutor",
        name="Tutor Agent",
        description="test",
        player_prompt_path=prompt_path,
        criteria_path=None,
    )


def test_ws_turn_streams_tokens_and_persists(role_config, monkeypatch) -> None:
    monkeypatch.setenv("AGENT_MODELS__REASONING_MODEL", "local")

    store = FakeStudentStore()
    store._students["student-123"] = {
        "name": "Lily-May",
        "year_group": 10,
        "target_grade": "6",
    }
    service = SessionService(store=store)

    # An active session owned by the token's student.
    record, _ = asyncio.run(
        store.create_session(
            student_id="student-123", subject="english", topic="Ambition"
        )
    )
    session_id = record.session_id

    def orchestrator_factory() -> _StreamingOrchestrator:
        return _StreamingOrchestrator(LLMPlayerAdapter(role_config))

    reply_stream_fn_factory = _build_http_reply_stream_fn_factory(
        orchestrator_factory, service
    )

    auth_config = HTTPAuthConfig.from_env(
        tokens_json='{"test-token": "student-123"}', dev_reset="false"
    )
    app = create_app(
        service=service,
        reply_fn=AsyncMock(),  # satisfies the JSON turn route requirement
        reply_stream_fn_factory=reply_stream_fn_factory,
        auth_config=auth_config,
        student_store=store,
        voice_config=VoiceConfig.from_env(enabled="true"),
    )

    with patch(
        "study_tutor.tutoring.adapters.llm_player_adapter.LLMClient",
        _FakeStreamingLLMClient,
    ):
        client = TestClient(app)
        with client.websocket_connect(
            f"/api/sessions/{session_id}/ws",
            headers={"authorization": "Bearer test-token"},
        ) as ws:
            ws.send_json({"type": "turn", "text": "Why murder Duncan?"})
            tokens: list[str] = []
            while True:
                frame = ws.receive_json()
                if frame["type"] == "token":
                    tokens.append(frame["text"])
                elif frame["type"] == "done":
                    break
                elif frame["type"] == "error":
                    pytest.fail(f"unexpected error frame: {frame}")

    # The fake LLM's tokens were streamed verbatim to the client.
    assert "".join(tokens) == "".join(_FAKE_TOKENS)

    # The tutor turn was persisted (user turn + tutor turn).
    turns = asyncio.run(store.get_turns(session_id))
    roles = [t.role for t in turns]
    assert roles == ["user", "tutor"]
    assert turns[-1].content == "".join(_FAKE_TOKENS)
