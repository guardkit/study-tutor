"""WebSocket voice_turn frame handler (TASK-VS2-006).

Handles {type:"voice_turn"} header + binary frame over WebSocket:
1. Validate audio bytes using shared VOX-004 validation core
2. Transcribe via AudioClient.transcribe
3. Emit transcript frame BEFORE any token frames
4. Stream answer tokens via run_turn_stream

Refusal parity: validation refusals are non-terminal (error frame, channel
stays open) per ASSUM-003. VoiceUnavailable is also non-terminal.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, Callable

from study_tutor.voice.validation import validate_audio_bytes
from study_tutor.voice.config import VoiceConfig
from study_tutor.voice.client import AudioClient
from study_tutor.voice.errors import VoiceError, VoiceUnavailable
from study_tutor.session.service import TurnEvent

logger = logging.getLogger(__name__)


async def handle_voice_turn_frame(
    *,
    audio_bytes: bytes,
    content_type: str,
    config: VoiceConfig,
    audio_client: AudioClient,
    turn_stream_fn: Callable[[], AsyncIterator[TurnEvent]],
) -> AsyncIterator[TurnEvent]:
    """Handle voice_turn WebSocket frame: validate, transcribe, stream answer.

    Pipeline (contract §7 Rev 1):
    1. Validate audio bytes using shared validation core (size→empty→MIME→duration)
    2. Transcribe audio to text via AudioClient
    3. Emit {type:"transcript"} frame FIRST
    4. Stream answer tokens from turn_stream_fn (feeds transcript as learner_message)
    5. Handle validation/transcription errors as non-terminal (error frame, no raise)

    Args:
        audio_bytes: Raw audio data received in binary frame.
        content_type: Audio MIME type from voice_turn header frame.
        config: Voice configuration with validation limits.
        audio_client: AudioClient for transcription.
        turn_stream_fn: Factory function that returns turn event stream.

    Yields:
        TurnEvent frames: transcript (first), then token/done, or error on failure.

    Raises:
        Nothing - all validation and transcription errors are yielded as error events.
    """
    # --- VALIDATION PHASE ---
    # Use shared validation core from TASK-VOX-004 (AC-006 seam test)
    try:
        validate_audio_bytes(audio_bytes, content_type, config)
    except VoiceError as e:
        # Validation refusal: non-terminal error (AC-002)
        logger.info(
            "Voice turn validation failed",
            extra={
                "event": "ws_voice_validation_failed",
                "error_type": type(e).__name__,
                "content_type": content_type,
                "size_bytes": len(audio_bytes),
            },
        )
        yield TurnEvent(
            type="error",
            error=str(e),
            error_type=type(e).__name__,
        )
        return

    # --- TRANSCRIPTION PHASE ---
    # Transcribe audio to text (AC-005: VoiceUnavailable is non-terminal)
    try:
        transcript_text = await audio_client.transcribe(
            audio=audio_bytes,
            filename="voice_turn.audio",  # Placeholder filename for STT API
            content_type=content_type,
        )
    except VoiceUnavailable as e:
        # Speech services down: non-terminal error (AC-005)
        logger.warning(
            "Voice turn transcription unavailable",
            extra={
                "event": "ws_voice_transcription_unavailable",
                "error": str(e),
            },
        )
        yield TurnEvent(
            type="error",
            error=str(e),
            error_type="VoiceUnavailable",
        )
        return
    except Exception as e:
        # Unexpected transcription error
        logger.exception(
            "Voice turn transcription failed unexpectedly",
            extra={
                "event": "ws_voice_transcription_error",
                "error_type": type(e).__name__,
                "error": str(e),
            },
        )
        yield TurnEvent(
            type="error",
            error=f"Transcription failed: {type(e).__name__}",
            error_type="internal_error",
        )
        return

    # --- TRANSCRIPT EMISSION (AC-001: MUST precede tokens) ---
    # Emit transcript frame BEFORE any token frames (contract §7 Rev 1)
    yield TurnEvent(
        type="transcript",
        text=transcript_text,
    )

    logger.info(
        "Voice turn transcript emitted",
        extra={
            "event": "ws_voice_transcript_emitted",
            "transcript_length": len(transcript_text),
        },
    )

    # Discard audio bytes immediately (never-at-rest invariant, design §5.6)
    # Note: audio_bytes goes out of scope here, eligible for GC

    # --- ANSWER STREAMING PHASE ---
    # Stream answer tokens from turn_stream_fn
    # The turn_stream_fn is expected to call run_turn_stream internally
    # with the transcript as learner_message
    try:
        async for event in turn_stream_fn():
            yield event
    except Exception as e:
        # Turn streaming error (should be rare - turn_stream handles most errors)
        logger.exception(
            "Voice turn streaming failed",
            extra={
                "event": "ws_voice_turn_stream_error",
                "error_type": type(e).__name__,
                "error": str(e),
            },
        )
        yield TurnEvent(
            type="error",
            error="Turn streaming failed",
            error_type="internal_error",
        )


__all__ = ["handle_voice_turn_frame"]
