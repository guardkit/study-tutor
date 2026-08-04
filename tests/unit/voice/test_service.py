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
    split_text_for_tts,
)


# ---------------------------------------------------------------------------
# split_text_for_tts Tests
# ---------------------------------------------------------------------------


class TestSplitTextForTts:
    """Tests for the TTS sentence-splitting helper (60s-cap fix)."""

    def test_short_text_returns_single_piece_verbatim(self) -> None:
        text = "What is photosynthesis? It happens in the chloroplasts."
        assert split_text_for_tts(text) == [text]

    def test_empty_and_whitespace_return_empty_list(self) -> None:
        assert split_text_for_tts("") == []
        assert split_text_for_tts("   \n  ") == []

    def test_long_text_splits_on_sentence_boundaries(self) -> None:
        sentence = "Plants use sunlight to convert carbon dioxide into sugar."
        text = " ".join([sentence] * 30)  # 270 words at 9 words/sentence
        pieces = split_text_for_tts(text, max_words=50)

        assert len(pieces) > 1
        for piece in pieces:
            assert len(piece.split()) <= 50
            # Pieces break at sentence boundaries, never mid-sentence
            assert piece.endswith(".")
        # No sentence lost or reordered
        assert " ".join(pieces) == text

    def test_every_word_preserved_in_order_for_varied_prose(self) -> None:
        text = (
            "Photosynthesis is remarkable! How do plants manage it? "
            "They capture light with chlorophyll. The energy splits water "
            "molecules. Oxygen escapes through the stomata. Glucose fuels "
            "growth… And the cycle repeats every single day."
        )
        pieces = split_text_for_tts(text, max_words=10)
        assert len(pieces) > 1
        assert " ".join(pieces).split() == text.split()

    def test_oversized_single_sentence_hard_splits_at_word_boundaries(self) -> None:
        text = "word " * 130  # one 130-word "sentence", no punctuation
        pieces = split_text_for_tts(text.strip(), max_words=50)

        assert len(pieces) == 3  # 50 + 50 + 30
        assert [len(p.split()) for p in pieces] == [50, 50, 30]
        assert " ".join(pieces).split() == text.split()

    def test_default_limit_keeps_pieces_under_tts_ceiling(self) -> None:
        # ~240 words of varied prose — the investigation's truncating case
        sentences = [
            f"Sentence number {i} adds a handful of ordinary words here." for i in range(30)
        ]
        pieces = split_text_for_tts(" ".join(sentences))
        assert len(pieces) >= 2
        for piece in pieces:
            # Investigation ceiling is ~170-180 words; default leaves headroom
            assert len(piece.split()) <= 120


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
        return VoiceConfig.from_env(enabled="true", stt_model="test-stt", tts_model="test-tts")

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
            reply_fn_factory=lambda **kwargs: AsyncMock(),
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
    async def test_voice_turn_uses_injected_reply_factory_not_echo(
        self,
        voice_config: VoiceConfig,
        chunk_store: ChunkStore,
        mock_audio_client: AudioClient,
        mock_request_factory: Any,
    ) -> None:
        """S-R4 §2.7: the REST voice turn drives the injected orchestrator
        reply factory — the Phase-1.2 placeholder echo ("I understand your
        question: ...") is gone. The reply the learner hears is the factory's
        output, proving the real tutor loop is wired.
        """
        # A session service whose turn() actually invokes the reply_fn, so we
        # observe which reply factory the voice service used.
        session_service = Mock(spec=SessionService)

        async def turn_invoking_reply_fn(
            *, student_id: str, session_id: str, user_message: str, reply_fn: Any
        ) -> Any:
            reply = await reply_fn(user_message)
            return Mock(
                tutor_response=reply.response, turn_index=1, metadata=None
            )

        session_service.turn = AsyncMock(side_effect=turn_invoking_reply_fn)

        seen: dict[str, Any] = {}

        def reply_fn_factory(*, session_id: str, student_id: str) -> Any:
            seen["session_id"] = session_id
            seen["student_id"] = student_id

            async def reply_fn(user_message: str) -> Any:
                return Mock(
                    response="Consider Macbeth's ambition as the engine.",
                    metadata=None,
                )

            return reply_fn

        service = VoiceTurnService(
            config=voice_config,
            audio_client=mock_audio_client,
            session_service=session_service,
            chunk_store=chunk_store,
            reply_fn_factory=reply_fn_factory,
        )

        request = mock_request_factory(b"fake audio wav bytes")
        result = await service.voice_turn(
            session_id="sess123", student_id="student1", request=request
        )

        assert result.tutor_response == "Consider Macbeth's ambition as the engine."
        assert "I understand your question" not in result.tutor_response
        # The factory was keyed by the turn's identity.
        assert seen == {"session_id": "sess123", "student_id": "student1"}

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
            reply_fn_factory=lambda **kwargs: AsyncMock(),
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
            reply_fn_factory=lambda **kwargs: AsyncMock(),
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
            reply_fn_factory=lambda **kwargs: AsyncMock(),
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
    async def test_long_reply_returns_multiple_chunks_with_contiguous_seq(
        self,
        voice_config: VoiceConfig,
        chunk_store: ChunkStore,
        mock_audio_client: AudioClient,
        mock_session_service: SessionService,
        mock_request_factory: Any,
    ) -> None:
        """60s-cap fix: a two-piece reply gets full audio, one chunk per piece."""
        long_reply = " ".join(
            f"Sentence number {i} carries a few ordinary words along." for i in range(22)
        )  # ~200 words -> exactly 2 pieces at the 120-word default
        pieces = split_text_for_tts(long_reply)
        assert len(pieces) == 2
        mock_session_service.turn = AsyncMock(
            return_value=Mock(tutor_response=long_reply, turn_index=1, metadata=None)
        )
        synth_inputs: list[str] = []

        async def record_synthesize(text: str, response_format: str = "wav") -> bytes:
            synth_inputs.append(text)
            return b"wav:" + text[:30].encode()

        mock_audio_client.synthesize = AsyncMock(side_effect=record_synthesize)

        service = VoiceTurnService(
            config=voice_config,
            audio_client=mock_audio_client,
            session_service=mock_session_service,
            chunk_store=chunk_store,
            reply_fn_factory=lambda **kwargs: AsyncMock(),
        )

        result = await service.voice_turn(
            "sess123", "student1", mock_request_factory(b"fake audio bytes")
        )

        assert len(result.audio) == 2
        # seq ascending, contiguous, starting at 0 (the app sorts by seq)
        assert [ref.seq for ref in result.audio] == [0, 1]
        # Every synthesis input stayed under the TTS ceiling; all pieces sent
        assert all(len(text.split()) <= 120 for text in synth_inputs)
        assert synth_inputs == pieces
        # Each chunk maps to its piece (seq order == text order) and fetches
        for ref, piece in zip(result.audio, pieces):
            assert chunk_store.get("sess123", ref.chunk_id) == b"wav:" + piece[
                :30
            ].encode()
            assert ref.url == f"/api/sessions/sess123/voice-audio/{ref.chunk_id}"

    @pytest.mark.asyncio
    async def test_very_long_reply_capped_at_max_pieces(
        self,
        voice_config: VoiceConfig,
        chunk_store: ChunkStore,
        mock_audio_client: AudioClient,
        mock_session_service: SessionService,
        mock_request_factory: Any,
    ) -> None:
        """Replies beyond the piece cap speak only the first pieces (the
        wall-time bound); the tail stays text-only."""
        very_long_reply = " ".join(
            f"Sentence number {i} carries a few ordinary words along." for i in range(40)
        )  # ~360 words -> 3+ pieces, above TTS_MAX_PIECES_PER_TURN=2
        pieces = split_text_for_tts(very_long_reply)
        assert len(pieces) >= 3
        mock_session_service.turn = AsyncMock(
            return_value=Mock(
                tutor_response=very_long_reply, turn_index=1, metadata=None
            )
        )
        synth_inputs: list[str] = []

        async def record_synthesize(text: str, response_format: str = "wav") -> bytes:
            synth_inputs.append(text)
            return b"wav:" + text[:30].encode()

        mock_audio_client.synthesize = AsyncMock(side_effect=record_synthesize)

        service = VoiceTurnService(
            config=voice_config,
            audio_client=mock_audio_client,
            session_service=mock_session_service,
            chunk_store=chunk_store,
            reply_fn_factory=lambda **kwargs: AsyncMock(),
        )

        result = await service.voice_turn(
            "sess123", "student1", mock_request_factory(b"fake audio bytes")
        )

        # Only the first two pieces synthesize; full text still returned
        assert result.tutor_response == very_long_reply
        assert [ref.seq for ref in result.audio] == [0, 1]
        assert synth_inputs == pieces[:2]

    @pytest.mark.asyncio
    async def test_partial_tts_failure_returns_pieces_synthesized_so_far(
        self,
        voice_config: VoiceConfig,
        chunk_store: ChunkStore,
        mock_audio_client: AudioClient,
        mock_session_service: SessionService,
        mock_request_factory: Any,
    ) -> None:
        """ASSUM-005 partial policy: contiguous prefix of successes is kept."""
        long_reply = " ".join(
            f"Sentence number {i} carries a few ordinary words along." for i in range(22)
        )
        pieces = split_text_for_tts(long_reply)
        assert len(pieces) == 2
        mock_session_service.turn = AsyncMock(
            return_value=Mock(tutor_response=long_reply, turn_index=1, metadata=None)
        )

        async def fail_second_piece(text: str, response_format: str = "wav") -> bytes:
            # Keyed on input, not call order
            if text == pieces[1]:
                raise VoiceUnavailable("TTS died mid-reply")
            return b"wav:" + text[:30].encode()

        mock_audio_client.synthesize = AsyncMock(side_effect=fail_second_piece)

        service = VoiceTurnService(
            config=voice_config,
            audio_client=mock_audio_client,
            session_service=mock_session_service,
            chunk_store=chunk_store,
            reply_fn_factory=lambda **kwargs: AsyncMock(),
        )

        result = await service.voice_turn(
            "sess123", "student1", mock_request_factory(b"fake audio bytes")
        )

        # Full text still returned; only the contiguous prefix survives,
        # so playback never has a gap
        assert result.tutor_response == long_reply
        assert [ref.seq for ref in result.audio] == [0]
        assert (
            chunk_store.get("sess123", result.audio[0].chunk_id)
            == b"wav:" + pieces[0][:30].encode()
        )

    @pytest.mark.asyncio
    async def test_chunks_stored_only_after_all_synthesis_completes(
        self,
        voice_config: VoiceConfig,
        chunk_store: ChunkStore,
        mock_audio_client: AudioClient,
        mock_session_service: SessionService,
        mock_request_factory: Any,
    ) -> None:
        """TTL fix: no chunk is stored until every piece has synthesized,
        so the 120s ChunkStore TTL starts at response time."""
        long_reply = " ".join(
            f"Sentence number {i} carries a few ordinary words along." for i in range(40)
        )
        mock_session_service.turn = AsyncMock(
            return_value=Mock(tutor_response=long_reply, turn_index=1, metadata=None)
        )
        events: list[str] = []

        async def record_synthesize(text: str, response_format: str = "wav") -> bytes:
            events.append("synthesize")
            return b"wav bytes"

        mock_audio_client.synthesize = AsyncMock(side_effect=record_synthesize)
        original_put = chunk_store.put

        def recording_put(session_id: str, wav_bytes: bytes) -> str:
            events.append("put")
            return original_put(session_id, wav_bytes)

        chunk_store.put = recording_put  # type: ignore[method-assign]

        service = VoiceTurnService(
            config=voice_config,
            audio_client=mock_audio_client,
            session_service=mock_session_service,
            chunk_store=chunk_store,
            reply_fn_factory=lambda **kwargs: AsyncMock(),
        )

        result = await service.voice_turn(
            "sess123", "student1", mock_request_factory(b"fake audio bytes")
        )

        assert len(result.audio) >= 2
        synth_count = events.count("synthesize")
        # Every synthesize event precedes every put event
        assert events == ["synthesize"] * synth_count + ["put"] * len(result.audio)

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
            reply_fn_factory=lambda **kwargs: AsyncMock(),
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
            reply_fn_factory=lambda **kwargs: AsyncMock(),
        )

        # Should raise validation error before STT
        from study_tutor.voice.errors import RecordingTooLarge

        with pytest.raises(RecordingTooLarge):
            await service.voice_turn("sess123", "student1", mock_request)

        # STT should never have been called
        assert stt_call_count == 0
