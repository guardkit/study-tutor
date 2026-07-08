"""Unit tests for voice/service.py (TASK-VOX-005).

Tests for ChunkStore (in-memory TTL storage) and VoiceTurnService (voice-turn orchestration).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from unittest.mock import AsyncMock, Mock

import pytest
from starlette.datastructures import Headers
from starlette.requests import Request

from study_tutor.session.service import SessionService
from study_tutor.voice.client import AudioClient
from study_tutor.voice.config import VoiceConfig
from study_tutor.voice.errors import UnintelligibleQuery, VoiceUnavailable
from study_tutor.voice.service import (
    AudioRef,
    ChunkStore,
    VoiceTurnResult,
    VoiceTurnService,
)


# ---------------------------------------------------------------------------
# ChunkStore Tests
# ---------------------------------------------------------------------------


class TestChunkStore:
    """Tests for ChunkStore in-memory TTL storage."""

    def test_put_returns_unguessable_chunk_id(self) -> None:
        """ChunkStore.put returns unique, unguessable chunk_id using secrets.token_urlsafe."""
        store = ChunkStore(ttl_seconds=120, max_entries=100)
        chunk_id_1 = store.put("session1", b"audio data 1")
        chunk_id_2 = store.put("session1", b"audio data 2")

        # IDs should be different and non-trivial
        assert chunk_id_1 != chunk_id_2
        assert len(chunk_id_1) > 8
        assert len(chunk_id_2) > 8

    def test_get_retrieves_stored_chunk(self) -> None:
        """ChunkStore.get retrieves the stored bytes for valid session_id and chunk_id."""
        store = ChunkStore(ttl_seconds=120, max_entries=100)
        audio_data = b"test audio wav bytes"
        chunk_id = store.put("session1", audio_data)

        result = store.get("session1", chunk_id)
        assert result == audio_data

    def test_get_returns_none_for_wrong_session(self) -> None:
        """ChunkStore.get returns None when session_id doesn't match (session-scoped keys)."""
        store = ChunkStore(ttl_seconds=120, max_entries=100)
        chunk_id = store.put("session1", b"audio data")

        result = store.get("session2", chunk_id)
        assert result is None

    def test_get_returns_none_for_unknown_chunk_id(self) -> None:
        """ChunkStore.get returns None for unknown chunk_id."""
        store = ChunkStore(ttl_seconds=120, max_entries=100)
        result = store.get("session1", "unknown-chunk-id")
        assert result is None

    def test_ttl_expiry_on_get(self) -> None:
        """ChunkStore.get returns None after TTL expires."""
        store = ChunkStore(ttl_seconds=1, max_entries=100)
        chunk_id = store.put("session1", b"audio data")

        # Should be available immediately
        assert store.get("session1", chunk_id) is not None

        # Wait for TTL to expire
        time.sleep(1.1)

        # Should be evicted
        assert store.get("session1", chunk_id) is None

    def test_ttl_eviction_on_put(self) -> None:
        """ChunkStore.put evicts expired entries before adding new ones."""
        store = ChunkStore(ttl_seconds=1, max_entries=100)
        chunk_id_1 = store.put("session1", b"audio 1")

        # Wait for expiry
        time.sleep(1.1)

        # Put new entry should trigger eviction of expired entry
        chunk_id_2 = store.put("session1", b"audio 2")

        # Old chunk should be evicted
        assert store.get("session1", chunk_id_1) is None
        # New chunk should be available
        assert store.get("session1", chunk_id_2) is not None

    def test_hard_cap_eviction_oldest_first(self) -> None:
        """ChunkStore evicts oldest entries when max_entries is exceeded."""
        store = ChunkStore(ttl_seconds=120, max_entries=3)

        chunk_id_1 = store.put("session1", b"audio 1")
        time.sleep(0.01)  # Ensure ordering
        chunk_id_2 = store.put("session1", b"audio 2")
        time.sleep(0.01)
        chunk_id_3 = store.put("session1", b"audio 3")

        # All three should be present
        assert store.get("session1", chunk_id_1) is not None
        assert store.get("session1", chunk_id_2) is not None
        assert store.get("session1", chunk_id_3) is not None

        # Add fourth entry - should evict oldest (chunk_id_1)
        chunk_id_4 = store.put("session1", b"audio 4")

        assert store.get("session1", chunk_id_1) is None  # Evicted
        assert store.get("session1", chunk_id_2) is not None
        assert store.get("session1", chunk_id_3) is not None
        assert store.get("session1", chunk_id_4) is not None

    @pytest.mark.asyncio
    async def test_asyncio_lock_prevents_race_conditions(self) -> None:
        """ChunkStore operations are guarded by asyncio.Lock."""
        store = ChunkStore(ttl_seconds=120, max_entries=100)

        async def concurrent_put(session_id: str, data: bytes) -> str:
            return store.put(session_id, data)

        # Run multiple puts concurrently
        results = await asyncio.gather(
            concurrent_put("session1", b"audio 1"),
            concurrent_put("session1", b"audio 2"),
            concurrent_put("session1", b"audio 3"),
        )

        # All should succeed with unique IDs
        assert len(results) == 3
        assert len(set(results)) == 3  # All unique


# ---------------------------------------------------------------------------
# VoiceTurnService Tests
# ---------------------------------------------------------------------------


class TestVoiceTurnService:
    """Tests for VoiceTurnService voice-turn orchestration."""

    @pytest.fixture
    def voice_config(self) -> VoiceConfig:
        """VoiceConfig fixture."""
        return VoiceConfig.from_env(enabled="true")

    @pytest.fixture
    def chunk_store(self) -> ChunkStore:
        """ChunkStore fixture."""
        return ChunkStore(ttl_seconds=120, max_entries=100)

    @pytest.fixture
    def mock_audio_client(self) -> AudioClient:
        """Mock AudioClient that returns successful responses."""
        mock = Mock(spec=AudioClient)
        mock.transcribe = AsyncMock(return_value="Hello tutor")
        mock.synthesize = AsyncMock(return_value=b"wav audio bytes")
        return mock

    @pytest.fixture
    def mock_session_service(self) -> SessionService:
        """Mock SessionService that records turns."""
        mock = Mock(spec=SessionService)
        mock.turn = AsyncMock(
            return_value=Mock(
                tutor_response="Great question! Let me help.",
                turn_index=1,
                metadata=None,
            )
        )
        return mock

    @pytest.fixture
    def mock_request_factory(self) -> Any:
        """Factory for creating mock Request objects with audio uploads."""

        def create_request(
            audio_bytes: bytes, content_type: str = "audio/wav"
        ) -> Request:
            # Create multipart body
            body = (
                b"------boundary123\r\n"
                b'Content-Disposition: form-data; name="audio"; filename="query.wav"\r\n'
                b"Content-Type: " + content_type.encode() + b"\r\n"
                b"\r\n" + audio_bytes + b"\r\n"
                b"------boundary123--\r\n"
            )

            # Mock request
            mock_request = Mock(spec=Request)
            mock_request.headers = Headers(
                {"content-type": "multipart/form-data; boundary=----boundary123"}
            )

            # Mock stream() to return body chunks
            async def mock_stream():
                yield body

            mock_request.stream = mock_stream
            return mock_request

        return create_request

    @pytest.mark.asyncio
    async def test_happy_path_returns_voice_turn_result(
        self,
        voice_config: VoiceConfig,
        chunk_store: ChunkStore,
        mock_audio_client: AudioClient,
        mock_session_service: SessionService,
        mock_request_factory: Any,
    ) -> None:
        """Happy path: parse -> transcribe -> turn -> synthesize -> store chunk."""
        service = VoiceTurnService(
            config=voice_config,
            audio_client=mock_audio_client,
            session_service=mock_session_service,
            chunk_store=chunk_store,
        )

        request = mock_request_factory(b"fake audio wav bytes")
        result = await service.voice_turn(
            session_id="sess123",
            student_id="student1",
            request=request,
        )

        # Verify result structure
        assert isinstance(result, VoiceTurnResult)
        assert result.transcript == "Hello tutor"
        assert result.tutor_response == "Great question! Let me help."
        assert len(result.audio) == 1

        # Verify audio ref
        audio_ref = result.audio[0]
        assert isinstance(audio_ref, AudioRef)
        assert audio_ref.seq == 0
        assert audio_ref.chunk_id is not None
        assert (
            audio_ref.url == f"/api/sessions/sess123/voice-audio/{audio_ref.chunk_id}"
        )

        # Verify chunk is stored
        stored_audio = chunk_store.get("sess123", audio_ref.chunk_id)
        assert stored_audio == b"wav audio bytes"

        # Verify turn was recorded via SessionService
        mock_session_service.turn.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_unintelligible_query_when_transcript_empty(
        self,
        voice_config: VoiceConfig,
        chunk_store: ChunkStore,
        mock_audio_client: AudioClient,
        mock_session_service: SessionService,
        mock_request_factory: Any,
    ) -> None:
        """Raise UnintelligibleQuery when transcribe returns empty/whitespace."""
        # Configure mock to return empty transcript
        mock_audio_client.transcribe = AsyncMock(return_value="   ")

        service = VoiceTurnService(
            config=voice_config,
            audio_client=mock_audio_client,
            session_service=mock_session_service,
            chunk_store=chunk_store,
        )

        request = mock_request_factory(b"fake audio bytes")

        with pytest.raises(UnintelligibleQuery):
            await service.voice_turn("sess123", "student1", request)

        # No turn should be recorded
        mock_session_service.turn.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_stt_unavailable_propagates_before_turn(
        self,
        voice_config: VoiceConfig,
        chunk_store: ChunkStore,
        mock_audio_client: AudioClient,
        mock_session_service: SessionService,
        mock_request_factory: Any,
    ) -> None:
        """VoiceUnavailable from STT propagates and no turn is recorded."""
        # Configure mock to raise VoiceUnavailable
        mock_audio_client.transcribe = AsyncMock(
            side_effect=VoiceUnavailable("STT service down")
        )

        service = VoiceTurnService(
            config=voice_config,
            audio_client=mock_audio_client,
            session_service=mock_session_service,
            chunk_store=chunk_store,
        )

        request = mock_request_factory(b"fake audio bytes")

        with pytest.raises(VoiceUnavailable):
            await service.voice_turn("sess123", "student1", request)

        # No turn should be recorded
        mock_session_service.turn.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_assum_005_tts_failure_after_turn_returns_text_only(
        self,
        voice_config: VoiceConfig,
        chunk_store: ChunkStore,
        mock_audio_client: AudioClient,
        mock_session_service: SessionService,
        mock_request_factory: Any,
    ) -> None:
        """ASSUM-005: TTS failure after turn is committed returns text-only result with audio=[]."""
        # Configure mocks: STT succeeds, turn succeeds, TTS fails
        mock_audio_client.transcribe = AsyncMock(return_value="Hello tutor")
        mock_audio_client.synthesize = AsyncMock(
            side_effect=VoiceUnavailable("TTS service down")
        )

        service = VoiceTurnService(
            config=voice_config,
            audio_client=mock_audio_client,
            session_service=mock_session_service,
            chunk_store=chunk_store,
        )

        request = mock_request_factory(b"fake audio bytes")

        result = await service.voice_turn("sess123", "student1", request)

        # Turn was recorded (check that turn was called)
        mock_session_service.turn.assert_awaited_once()

        # Result should have transcript and tutor_response but empty audio
        assert result.transcript == "Hello tutor"
        assert result.tutor_response == "Great question! Let me help."
        assert result.audio == []

    @pytest.mark.asyncio
    async def test_no_audio_bytes_in_logs(
        self,
        voice_config: VoiceConfig,
        chunk_store: ChunkStore,
        mock_audio_client: AudioClient,
        mock_session_service: SessionService,
        mock_request_factory: Any,
        caplog: Any,
    ) -> None:
        """Verify no audio bytes appear in log records (AC-004)."""
        caplog.set_level(logging.DEBUG)

        service = VoiceTurnService(
            config=voice_config,
            audio_client=mock_audio_client,
            session_service=mock_session_service,
            chunk_store=chunk_store,
        )

        request = mock_request_factory(b"fake audio wav bytes")
        await service.voice_turn("sess123", "student1", request)

        # Check that no audio bytes appear in any log messages
        for record in caplog.records:
            assert b"fake audio wav bytes" not in record.getMessage().encode()
            assert b"wav audio bytes" not in record.getMessage().encode()

    @pytest.mark.seam
    @pytest.mark.integration_contract("parse_voice_upload")
    @pytest.mark.asyncio
    async def test_rejection_precedes_stt(
        self,
        voice_config: VoiceConfig,
        chunk_store: ChunkStore,
        mock_audio_client: AudioClient,
        mock_session_service: SessionService,
    ) -> None:
        """Seam test: parse_voice_upload raises before AudioClient is invoked.

        Contract: TASK-VOX-004 validation errors propagate before STT.
        """
        # Create request with oversized audio (>10MB)
        oversized_audio = b"x" * (11 * 1024 * 1024)
        body = (
            b"------boundary123\r\n"
            b'Content-Disposition: form-data; name="audio"; filename="query.wav"\r\n'
            b"Content-Type: audio/wav\r\n"
            b"\r\n" + oversized_audio + b"\r\n"
            b"------boundary123--\r\n"
        )

        mock_request = Mock(spec=Request)
        mock_request.headers = Headers(
            {"content-type": "multipart/form-data; boundary=----boundary123"}
        )

        async def mock_stream():
            yield body

        mock_request.stream = mock_stream

        # Track STT calls
        stt_call_count = 0

        async def track_transcribe(*args, **kwargs):
            nonlocal stt_call_count
            stt_call_count += 1
            return "transcript"

        mock_audio_client.transcribe = track_transcribe

        service = VoiceTurnService(
            config=voice_config,
            audio_client=mock_audio_client,
            session_service=mock_session_service,
            chunk_store=chunk_store,
        )

        # Should raise validation error before STT
        from study_tutor.voice.errors import RecordingTooLarge

        with pytest.raises(RecordingTooLarge):
            await service.voice_turn("sess123", "student1", mock_request)

        # STT should never have been called
        assert stt_call_count == 0
