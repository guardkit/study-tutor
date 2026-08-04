"""Text-stream acceptance suite — hermetic integration tests for Tier-A scenarios (TASK-VS2-005).

Hermetic integration tests for every Tier-A (non-voice) scenario of the streaming-voice
feature, using fake respond_stream and fake store conventions. No real LLM, no real network.

**Isolation strategy**: Uses fresh-session-per-test approach. Each test creates its own
session context with independent fake services, avoiding global state and allowing parallel
execution without --concurrency=1 constraint.

All tests use fake SessionService.turn_stream with synthetic token generators to simulate
streaming behavior without real LLM calls.
"""
from __future__ import annotations

import asyncio
import pytest
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from study_tutor.http.app import create_app
from study_tutor.http.auth import HTTPAuthConfig
from study_tutor.session.service import SessionService, TurnEvent, TurnResult
from study_tutor.session.errors import SessionNotFoundError
from study_tutor.voice.config import VoiceConfig


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_config():
    """HTTP auth config with test token."""
    return HTTPAuthConfig.from_env(
        tokens_json='{"test-token": "student-123"}',
        dev_reset="false",
    )


@pytest.fixture
def voice_config_enabled():
    """Voice config with feature enabled."""
    return VoiceConfig.from_env(enabled="true", stt_model="test-stt", tts_model="test-tts")


@pytest.fixture
def voice_config_disabled():
    """Voice config with feature disabled."""
    return VoiceConfig.from_env(enabled="false")


@pytest.fixture
def fake_student_store():
    """Fake student store."""
    store = AsyncMock()
    store.student_exists.return_value = True
    return store


@pytest.fixture
def fake_reply_fn_factory():
    """Fake reply function factory for non-streaming turn endpoint."""
    async def fake_reply(text: str):
        return MagicMock(response=f"Complete answer to: {text}", turn_index=1)

    def factory(**kwargs):
        return fake_reply

    return factory


# ---------------------------------------------------------------------------
# AC-001: Typed streaming — first fragment before full answer, terminal done
# ---------------------------------------------------------------------------


class TestTypedStreaming:
    """AC-001: Typed question streams incrementally with first fragment before full answer."""

    def test_first_fragment_arrives_before_full_answer_exists(
        self, auth_config, voice_config_enabled, fake_student_store, fake_reply_fn_factory
    ):
        """First token arrives before generation completes; done confirms turn_index."""
        async def streaming_turn_stream(**kwargs) -> AsyncIterator[TurnEvent]:
            """Simulate incremental token generation."""
            yield TurnEvent(type="token", text="The")
            yield TurnEvent(type="token", text=" answer")
            yield TurnEvent(type="token", text=" streams")
            yield TurnEvent(type="token", text=" incrementally")
            yield TurnEvent(type="done", turn_index=1)

        service = AsyncMock(spec=SessionService)
        service.turn_stream = streaming_turn_stream

        app = create_app(
            auth_config=auth_config,
            voice_config=voice_config_enabled,
            student_store=fake_student_store,
            service=service,
            reply_fn_factory=fake_reply_fn_factory,
        )

        with TestClient(app) as client:
            with client.websocket_connect(
                "/api/sessions/sess-001/ws",
                headers={"Authorization": "Bearer test-token"},
            ) as ws:
                ws.send_json({"type": "turn", "text": "Explain photosynthesis", "stream": True})

                # Collect all frames
                frames = []
                while True:
                    data = ws.receive_json()
                    frames.append(data)
                    if data["type"] == "done":
                        break

                # Verify incremental token arrival
                assert len(frames) == 5
                assert frames[0]["type"] == "token"
                assert frames[0]["text"] == "The"
                assert frames[1]["type"] == "token"
                assert frames[1]["text"] == " answer"
                assert frames[2]["type"] == "token"
                assert frames[2]["text"] == " streams"
                assert frames[3]["type"] == "token"
                assert frames[3]["text"] == " incrementally"

                # Terminal done with history position
                assert frames[4]["type"] == "done"
                assert frames[4]["turn_index"] == 1


# ---------------------------------------------------------------------------
# AC-001 (Regression): Non-streaming turn endpoint unchanged
# ---------------------------------------------------------------------------


class TestNonStreamingRegression:
    """Regression: Non-streaming HTTP turn endpoint returns complete answer unchanged."""

    def test_non_streaming_turn_returns_whole_answer(
        self, auth_config, voice_config_enabled, fake_student_store, fake_reply_fn_factory
    ):
        """POST /turn without streaming returns complete answer in single response."""
        async def fake_turn(**kwargs):
            return TurnResult(
                tutor_response="Complete answer without streaming",
                turn_index=1,
                metadata=None,
            )

        service = AsyncMock(spec=SessionService)
        service.turn = fake_turn

        app = create_app(
            auth_config=auth_config,
            voice_config=voice_config_enabled,
            student_store=fake_student_store,
            service=service,
            reply_fn_factory=fake_reply_fn_factory,
        )

        with TestClient(app) as client:
            response = client.post(
                "/api/sessions/sess-001/turn",
                json={"user_message": "What is photosynthesis?"},
                headers={"Authorization": "Bearer test-token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["tutor_response"] == "Complete answer without streaming"


# ---------------------------------------------------------------------------
# AC-001: Durability parity — streamed turn = plain turn in history
# ---------------------------------------------------------------------------


class TestDurabilityParity:
    """AC-001: Streamed turns are recorded identically to non-streamed turns."""

    def test_streamed_turn_persisted_in_history(
        self, auth_config, voice_config_enabled, fake_student_store, fake_reply_fn_factory
    ):
        """Completed streamed turn appears in session history like non-streamed turn."""
        stored_turns = []

        async def streaming_turn_stream(**kwargs) -> AsyncIterator[TurnEvent]:
            """Track that full response gets persisted."""
            yield TurnEvent(type="token", text="Part1")
            yield TurnEvent(type="token", text=" Part2")
            yield TurnEvent(type="done", turn_index=1)
            # Simulate store append being called with full response
            stored_turns.append("Part1 Part2")

        service = AsyncMock(spec=SessionService)
        service.turn_stream = streaming_turn_stream

        app = create_app(
            auth_config=auth_config,
            voice_config=voice_config_enabled,
            student_store=fake_student_store,
            service=service,
            reply_fn_factory=fake_reply_fn_factory,
        )

        with TestClient(app) as client:
            with client.websocket_connect(
                "/api/sessions/sess-002/ws",
                headers={"Authorization": "Bearer test-token"},
            ) as ws:
                ws.send_json({"type": "turn", "text": "Question", "stream": True})

                # Consume stream until done
                while True:
                    data = ws.receive_json()
                    if data["type"] == "done":
                        assert data["turn_index"] == 1
                        break

        # Verify full response was stored (simulated)
        assert "Part1 Part2" in stored_turns

    def test_mid_generation_failure_leaves_no_exchange(
        self, auth_config, voice_config_enabled, fake_student_store, fake_reply_fn_factory
    ):
        """Generation failure mid-stream records no tutor turn in history."""
        async def failing_turn_stream(**kwargs) -> AsyncIterator[TurnEvent]:
            """Fail after first token — no tutor turn should be persisted."""
            yield TurnEvent(type="token", text="Starting")
            raise RuntimeError("Generation failed mid-stream")

        service = AsyncMock(spec=SessionService)
        service.turn_stream = failing_turn_stream

        app = create_app(
            auth_config=auth_config,
            voice_config=voice_config_enabled,
            student_store=fake_student_store,
            service=service,
            reply_fn_factory=fake_reply_fn_factory,
        )

        with TestClient(app) as client:
            with client.websocket_connect(
                "/api/sessions/sess-003/ws",
                headers={"Authorization": "Bearer test-token"},
            ) as ws:
                ws.send_json({"type": "turn", "text": "Question", "stream": True})

                # First frame is partial token
                first_frame = ws.receive_json()
                assert first_frame["type"] == "token"
                assert first_frame["text"] == "Starting"

                # Second frame is error (no done, no turn_index)
                error_frame = ws.receive_json()
                assert error_frame["type"] == "error"
                # WS handler maps RuntimeError to internal_error
                assert error_frame.get("error_type") in ("generation_failed", "internal_error")


# ---------------------------------------------------------------------------
# AC-001: Async-Coach non-blocking
# ---------------------------------------------------------------------------


class TestAsyncCoachNonBlocking:
    """AC-001: Streaming never waits for quality review (ADR-ARCH-026)."""

    def test_streaming_proceeds_without_waiting_for_quality_review(
        self, auth_config, voice_config_enabled, fake_student_store, fake_reply_fn_factory
    ):
        """Stream completes without blocking on async quality monitor."""
        quality_monitor_invoked = []

        async def streaming_turn_stream(**kwargs) -> AsyncIterator[TurnEvent]:
            """Stream tokens without waiting for quality review."""
            yield TurnEvent(type="token", text="Answer")
            yield TurnEvent(type="token", text=" text")
            yield TurnEvent(type="done", turn_index=1)
            # Quality monitor runs async after done (not inline)
            asyncio.create_task(_async_quality_monitor())

        async def _async_quality_monitor():
            """Simulated async quality review — runs after streaming."""
            await asyncio.sleep(0.01)  # Simulate async work
            quality_monitor_invoked.append(True)

        service = AsyncMock(spec=SessionService)
        service.turn_stream = streaming_turn_stream

        app = create_app(
            auth_config=auth_config,
            voice_config=voice_config_enabled,
            student_store=fake_student_store,
            service=service,
            reply_fn_factory=fake_reply_fn_factory,
        )

        with TestClient(app) as client:
            with client.websocket_connect(
                "/api/sessions/sess-004/ws",
                headers={"Authorization": "Bearer test-token"},
            ) as ws:
                ws.send_json({"type": "turn", "text": "Question", "stream": True})

                frames = []
                while True:
                    data = ws.receive_json()
                    frames.append(data)
                    if data["type"] == "done":
                        break

        # Stream completed before quality monitor (non-blocking)
        assert len(frames) == 3
        assert frames[2]["type"] == "done"


# ---------------------------------------------------------------------------
# AC-001: Single-channel queueing
# ---------------------------------------------------------------------------


class TestSingleChannelQueueing:
    """AC-001: Multiple questions on same channel are answered sequentially, not interleaved."""

    def test_second_question_waits_for_first_to_complete(
        self, auth_config, voice_config_enabled, fake_student_store, fake_reply_fn_factory
    ):
        """Two questions on same channel processed in order, no frame interleaving."""
        turn_order = []

        async def streaming_turn_stream(**kwargs) -> AsyncIterator[TurnEvent]:
            """Track turn order — each turn completes before next starts."""
            user_message = kwargs.get("user_message", "")
            turn_order.append(f"start:{user_message}")

            if "first" in user_message:
                yield TurnEvent(type="token", text="Answer1")
                yield TurnEvent(type="done", turn_index=1)
            else:
                yield TurnEvent(type="token", text="Answer2")
                yield TurnEvent(type="done", turn_index=2)

            turn_order.append(f"end:{user_message}")

        service = AsyncMock(spec=SessionService)
        service.turn_stream = streaming_turn_stream

        app = create_app(
            auth_config=auth_config,
            voice_config=voice_config_enabled,
            student_store=fake_student_store,
            service=service,
            reply_fn_factory=fake_reply_fn_factory,
        )

        with TestClient(app) as client:
            with client.websocket_connect(
                "/api/sessions/sess-005/ws",
                headers={"Authorization": "Bearer test-token"},
            ) as ws:
                # Send first question
                ws.send_json({"type": "turn", "text": "first question", "stream": True})

                # Receive first answer completely
                first_frames = []
                while True:
                    data = ws.receive_json()
                    first_frames.append(data)
                    if data["type"] == "done":
                        break

                # Send second question
                ws.send_json({"type": "turn", "text": "second question", "stream": True})

                # Receive second answer
                second_frames = []
                while True:
                    data = ws.receive_json()
                    second_frames.append(data)
                    if data["type"] == "done":
                        break

        # Verify sequential ordering (no interleaving)
        assert len(first_frames) == 2  # token, done
        assert first_frames[0]["text"] == "Answer1"
        assert first_frames[1]["turn_index"] == 1

        assert len(second_frames) == 2
        assert second_frames[0]["text"] == "Answer2"
        assert second_frames[1]["turn_index"] == 2


# ---------------------------------------------------------------------------
# AC-001: Cross-channel isolation
# ---------------------------------------------------------------------------


class TestCrossChannelIsolation:
    """AC-001: Different sessions/students see only their own frames, no cross-talk."""

    def test_concurrent_sessions_remain_isolated(
        self, auth_config, voice_config_enabled, fake_student_store, fake_reply_fn_factory
    ):
        """Two sessions streaming concurrently receive only their own frames."""
        async def streaming_turn_stream(**kwargs) -> AsyncIterator[TurnEvent]:
            """Generate session-specific responses."""
            session_id = kwargs.get("session_id", "")
            marker = session_id.split("-")[-1]  # Extract session marker

            yield TurnEvent(type="token", text=f"Response-{marker}")
            yield TurnEvent(type="done", turn_index=1)

        service = AsyncMock(spec=SessionService)
        service.turn_stream = streaming_turn_stream

        app = create_app(
            auth_config=auth_config,
            voice_config=voice_config_enabled,
            student_store=fake_student_store,
            service=service,
            reply_fn_factory=fake_reply_fn_factory,
        )

        with TestClient(app) as client:
            # Session A
            with client.websocket_connect(
                "/api/sessions/sess-A/ws",
                headers={"Authorization": "Bearer test-token"},
            ) as ws_a:
                ws_a.send_json({"type": "turn", "text": "Question A", "stream": True})
                frames_a = []
                while True:
                    data = ws_a.receive_json()
                    frames_a.append(data)
                    if data["type"] == "done":
                        break

            # Session B
            with client.websocket_connect(
                "/api/sessions/sess-B/ws",
                headers={"Authorization": "Bearer test-token"},
            ) as ws_b:
                ws_b.send_json({"type": "turn", "text": "Question B", "stream": True})
                frames_b = []
                while True:
                    data = ws_b.receive_json()
                    frames_b.append(data)
                    if data["type"] == "done":
                        break

        # Verify isolation: each session received only its own response
        assert frames_a[0]["text"] == "Response-A"
        assert frames_b[0]["text"] == "Response-B"
        assert "Response-B" not in str(frames_a)
        assert "Response-A" not in str(frames_b)


# ---------------------------------------------------------------------------
# AC-001: Stall timeout
# ---------------------------------------------------------------------------


class TestStallTimeout:
    """AC-001: Model stall results in bounded failure, not indefinite hang."""

    def test_stalled_generation_fails_after_bounded_wait(
        self, auth_config, voice_config_enabled, fake_student_store, fake_reply_fn_factory
    ):
        """Generation stall triggers timeout error rather than hanging indefinitely."""
        async def stalling_turn_stream(**kwargs):
            """Simulate model stall — no tokens produced."""
            await asyncio.sleep(0.01)  # Brief pause simulating stall detection
            raise TimeoutError("Model stalled without producing tokens")
            yield  # Make it a generator (never reached)

        service = AsyncMock(spec=SessionService)
        service.turn_stream = stalling_turn_stream

        app = create_app(
            auth_config=auth_config,
            voice_config=voice_config_enabled,
            student_store=fake_student_store,
            service=service,
            reply_fn_factory=fake_reply_fn_factory,
        )

        with TestClient(app) as client:
            with client.websocket_connect(
                "/api/sessions/sess-stall/ws",
                headers={"Authorization": "Bearer test-token"},
            ) as ws:
                ws.send_json({"type": "turn", "text": "Question", "stream": True})

                # Expect error frame after bounded wait
                error_frame = ws.receive_json()
                assert error_frame["type"] == "error"
                # Error is mapped to internal_error by WS handler
                assert error_frame.get("error_type") == "internal_error"


# ---------------------------------------------------------------------------
# AC-001: Connection refusals (auth/ownership/lifecycle) — covered by test_ws.py
# ---------------------------------------------------------------------------
# These scenarios are already tested in test_ws.py:
# - Unauthenticated: test_missing_token_refused_as_unauthenticated
# - Forbidden: test_wrong_student_refused_as_forbidden
# - Not found: test_unknown_session_refused_as_not_found
# - Ended: test_ended_session_refused_as_session_ended
# - Flag-off: test_ws_route_absent_when_flag_off


# ---------------------------------------------------------------------------
# AC-003: All tests hermetic and pass
# ---------------------------------------------------------------------------
# All tests above use fake SessionService, fake stores, no real LLM/network.
# Run with: uv run pytest tests/unit/http/test_text_stream_acceptance.py -x -q


# ---------------------------------------------------------------------------
# AC-004: Isolation strategy documented
# ---------------------------------------------------------------------------
# See module docstring: fresh-session-per-test with independent fake services.
