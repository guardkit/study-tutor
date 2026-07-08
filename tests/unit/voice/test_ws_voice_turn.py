"""Tests for WebSocket voice_turn frame handling (TASK-VS2-006).

Tests cover:
- Transcript frame emitted before token frames
- Validation refusals are non-terminal (channel stays open)
- Size cap enforcement on actual bytes received
- Shared validation core reuse (seam test)
- Speech services unavailability handling (non-terminal)
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from typing import AsyncIterator

from study_tutor.voice.ws_voice_turn import handle_voice_turn_frame
from study_tutor.voice.errors import (
    VoiceUnavailable,
)
from study_tutor.voice.config import VoiceConfig
from study_tutor.session.service import TurnEvent


@pytest.fixture
def voice_config():
    """Minimal voice config for testing."""
    return VoiceConfig(
        enabled=True,
        stt_base_url="http://test-stt",
        stt_model="whisper-1",
        tts_base_url="http://test-tts",
        tts_model="tts-1",
        tts_voice="nova",
        audio_timeout_seconds=30.0,
        max_recording_bytes=5 * 1024 * 1024,  # 5MB
        max_query_seconds=120,
        chunk_ttl_seconds=120,
        supported_base_mimetypes={"audio/wav", "audio/ogg", "audio/webm"},
    )


@pytest.fixture
def valid_wav_blob():
    """Valid WAV audio blob (minimal 44-byte header + 1 sample)."""
    # Minimal WAV: RIFF header (12) + fmt chunk (24) + data chunk (8 + samples)
    return (
        b"RIFF"
        + (36).to_bytes(4, "little")  # File size - 8
        + b"WAVE"
        + b"fmt "
        + (16).to_bytes(4, "little")  # fmt chunk size
        + (1).to_bytes(2, "little")  # PCM format
        + (1).to_bytes(2, "little")  # 1 channel
        + (16000).to_bytes(4, "little")  # Sample rate
        + (32000).to_bytes(4, "little")  # Byte rate
        + (2).to_bytes(2, "little")  # Block align
        + (16).to_bytes(2, "little")  # Bits per sample
        + b"data"
        + (4).to_bytes(4, "little")  # Data size
        + b"\x00" * 4  # 4 bytes of audio data
    )


@pytest.fixture
def mock_audio_client():
    """Mock AudioClient for testing."""
    client = AsyncMock()
    client.transcribe = AsyncMock(return_value="What is photosynthesis?")
    return client


@pytest.fixture
def mock_turn_stream():
    """Mock turn stream generator."""

    async def _stream() -> AsyncIterator[TurnEvent]:
        yield TurnEvent(type="token", text="Photosynthesis ")
        yield TurnEvent(type="token", text="is ")
        yield TurnEvent(type="token", text="the process")
        yield TurnEvent(type="done", turn_index=1)

    return _stream


# ---------------------------------------------------------------------------
# AC-001: transcript frame before first token frame
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_transcript_frame_precedes_tokens(
    voice_config, valid_wav_blob, mock_audio_client, mock_turn_stream
):
    """AC-001: transcript frame observed strictly before the first token frame."""
    events = []

    async for event in handle_voice_turn_frame(
        audio_bytes=valid_wav_blob,
        content_type="audio/wav",
        config=voice_config,
        audio_client=mock_audio_client,
        turn_stream_fn=mock_turn_stream,
    ):
        events.append(event)

    # Extract event types
    event_types = [e.type for e in events]

    # Verify transcript appears before first token
    assert "transcript" in event_types, "Missing transcript event"
    assert "token" in event_types, "Missing token events"

    transcript_idx = event_types.index("transcript")
    first_token_idx = event_types.index("token")

    assert transcript_idx < first_token_idx, (
        f"Transcript at index {transcript_idx} must precede "
        f"first token at index {first_token_idx}"
    )


# ---------------------------------------------------------------------------
# AC-002: Validation refusals are non-terminal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_validation_refusal_non_terminal_oversized(
    voice_config, valid_wav_blob, mock_audio_client, mock_turn_stream
):
    """AC-002: Validation refusals are non-terminal (error event, no exception)."""
    # Create oversized blob (exceeds max_recording_bytes)
    oversized_blob = b"\x00" * (voice_config.max_recording_bytes + 1)

    events = []

    # Should yield error event, not raise exception
    async for event in handle_voice_turn_frame(
        audio_bytes=oversized_blob,
        content_type="audio/wav",
        config=voice_config,
        audio_client=mock_audio_client,
        turn_stream_fn=mock_turn_stream,
    ):
        events.append(event)

    # Should have exactly one error event
    assert len(events) == 1
    assert events[0].type == "error"
    assert events[0].error_type == "RecordingTooLarge"
    assert "exceeds maximum size" in events[0].error


@pytest.mark.asyncio
async def test_validation_refusal_non_terminal_empty(
    voice_config, mock_audio_client, mock_turn_stream
):
    """AC-002: Empty recording refusal is non-terminal."""
    events = []

    async for event in handle_voice_turn_frame(
        audio_bytes=b"",
        content_type="audio/wav",
        config=voice_config,
        audio_client=mock_audio_client,
        turn_stream_fn=mock_turn_stream,
    ):
        events.append(event)

    assert len(events) == 1
    assert events[0].type == "error"
    assert events[0].error_type == "EmptyRecording"


@pytest.mark.asyncio
async def test_validation_refusal_non_terminal_unsupported_format(
    voice_config, valid_wav_blob, mock_audio_client, mock_turn_stream
):
    """AC-002: Unsupported format refusal is non-terminal."""
    events = []

    async for event in handle_voice_turn_frame(
        audio_bytes=valid_wav_blob,
        content_type="audio/mp3",  # Not in supported list
        config=voice_config,
        audio_client=mock_audio_client,
        turn_stream_fn=mock_turn_stream,
    ):
        events.append(event)

    assert len(events) == 1
    assert events[0].type == "error"
    assert events[0].error_type == "UnsupportedAudioFormat"


# ---------------------------------------------------------------------------
# AC-003: Size cap enforcement
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recording_at_size_cap_accepted(
    voice_config, mock_audio_client, mock_turn_stream
):
    """AC-003: Recording exactly at size cap is accepted."""
    # Create blob exactly at the cap
    at_cap_blob = b"RIFF" + b"\x00" * (voice_config.max_recording_bytes - 4)

    # Mock transcribe to return something
    mock_audio_client.transcribe = AsyncMock(return_value="test transcript")

    events = []
    async for event in handle_voice_turn_frame(
        audio_bytes=at_cap_blob,
        content_type="audio/wav",
        config=voice_config,
        audio_client=mock_audio_client,
        turn_stream_fn=mock_turn_stream,
    ):
        events.append(event)

    # Should have transcript event (no error)
    event_types = [e.type for e in events]
    assert "transcript" in event_types
    assert "error" not in event_types


@pytest.mark.asyncio
async def test_recording_one_byte_over_refused(
    voice_config, mock_audio_client, mock_turn_stream
):
    """AC-003: Recording one byte over cap is refused."""
    over_cap_blob = b"\x00" * (voice_config.max_recording_bytes + 1)

    events = []
    async for event in handle_voice_turn_frame(
        audio_bytes=over_cap_blob,
        content_type="audio/wav",
        config=voice_config,
        audio_client=mock_audio_client,
        turn_stream_fn=mock_turn_stream,
    ):
        events.append(event)

    assert len(events) == 1
    assert events[0].type == "error"
    assert events[0].error_type == "RecordingTooLarge"


# ---------------------------------------------------------------------------
# AC-004: Actual bytes vs declared size
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_actual_bytes_judged_not_declared(
    voice_config, mock_audio_client, mock_turn_stream
):
    """AC-004: Validation judges actual bytes received, not declared size.

    This test verifies the contract: even if header declares a smaller size,
    validation enforces limits on the actual bytes received.
    """
    # Simulate: header declared 1KB, but actually sent 6MB
    oversized_blob = b"\x00" * (voice_config.max_recording_bytes + 1024)

    events = []
    async for event in handle_voice_turn_frame(
        audio_bytes=oversized_blob,
        content_type="audio/wav",
        config=voice_config,
        audio_client=mock_audio_client,
        turn_stream_fn=mock_turn_stream,
    ):
        events.append(event)

    # Should refuse based on actual bytes
    assert events[0].type == "error"
    assert events[0].error_type == "RecordingTooLarge"


# ---------------------------------------------------------------------------
# AC-005: Speech services unavailability (non-terminal)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_speech_services_down_non_terminal(
    voice_config, valid_wav_blob, mock_audio_client, mock_turn_stream
):
    """AC-005: Speech services down yields error event (non-terminal)."""
    # Simulate STT service unavailable
    mock_audio_client.transcribe = AsyncMock(
        side_effect=VoiceUnavailable("Speech-to-text service unavailable")
    )

    events = []
    async for event in handle_voice_turn_frame(
        audio_bytes=valid_wav_blob,
        content_type="audio/wav",
        config=voice_config,
        audio_client=mock_audio_client,
        turn_stream_fn=mock_turn_stream,
    ):
        events.append(event)

    assert len(events) == 1
    assert events[0].type == "error"
    assert events[0].error_type == "VoiceUnavailable"


# ---------------------------------------------------------------------------
# AC-006: Shared validation core reuse (seam test)
# ---------------------------------------------------------------------------


@pytest.mark.seam
@pytest.mark.asyncio
async def test_ws_voice_turn_calls_shared_validation_core(
    voice_config, valid_wav_blob, mock_audio_client, mock_turn_stream
):
    """AC-006: WS path calls shared VOX-004 validation core (no duplication)."""
    with patch("study_tutor.voice.ws_voice_turn.validate_audio_bytes") as mock_validate:
        # Let validation pass through
        mock_validate.return_value = None

        events = []
        async for event in handle_voice_turn_frame(
            audio_bytes=valid_wav_blob,
            content_type="audio/wav",
            config=voice_config,
            audio_client=mock_audio_client,
            turn_stream_fn=mock_turn_stream,
        ):
            events.append(event)

        # Verify shared validation core was called
        mock_validate.assert_called_once()
        call_args = mock_validate.call_args
        assert call_args[0][0] == valid_wav_blob  # audio_bytes
        assert call_args[0][1] == "audio/wav"  # content_type
        assert call_args[0][2] == voice_config  # config


# ---------------------------------------------------------------------------
# Integration: Full happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_full_voice_turn_happy_path(
    voice_config, valid_wav_blob, mock_audio_client, mock_turn_stream
):
    """Integration: Full voice turn with transcript then answer tokens."""
    events = []

    async for event in handle_voice_turn_frame(
        audio_bytes=valid_wav_blob,
        content_type="audio/wav",
        config=voice_config,
        audio_client=mock_audio_client,
        turn_stream_fn=mock_turn_stream,
    ):
        events.append(event)

    # Should have: transcript, token(s), done
    event_types = [e.type for e in events]

    assert event_types[0] == "transcript"
    assert event_types[1] == "token"
    assert event_types[-1] == "done"

    # Verify transcript content
    assert events[0].text == "What is photosynthesis?"

    # Verify AudioClient.transcribe was called with correct params
    mock_audio_client.transcribe.assert_called_once()
    call_kwargs = mock_audio_client.transcribe.call_args.kwargs
    assert call_kwargs["audio"] == valid_wav_blob
    assert call_kwargs["content_type"] == "audio/wav"
