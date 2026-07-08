"""Sentence-chunked TTS with audio_ref frames (TASK-VS2-007).

Implements Contract §7 Rev 1 audio_ref frame emission: for each verified sentence
chunk, synthesize audio via AudioClient, store in ChunkStore, and emit
{type:"audio_ref", seq, chunk_id, url} frames in sequence order.

ASSUM-006: VoiceUnavailable mid-answer skips remaining audio_ref frames but
allows token frames to continue to completion.

Never-at-rest invariant (design §5.6): audio bytes flow only through memory
(AudioClient → ChunkStore), never touching disk or database.
"""

from __future__ import annotations

import logging
from typing import AsyncIterator, Callable, Any

from study_tutor.session.service import TurnEvent
from study_tutor.voice.client import AudioClient
from study_tutor.voice.service import ChunkStore
from study_tutor.voice.errors import VoiceUnavailable

logger = logging.getLogger(__name__)


async def stream_with_audio_refs(
    *,
    token_stream: AsyncIterator[TurnEvent],
    session_id: str,
    audio_client: AudioClient,
    chunk_store: ChunkStore,
    verifier: Callable[[str], Any],
) -> AsyncIterator[TurnEvent]:
    """Stream turn events with audio_ref frames for verified sentence chunks.

    Pipeline:
    1. Consume token events from upstream
    2. Accumulate tokens and detect sentence boundaries
    3. For each sentence: verify → synthesize → store → emit audio_ref
    4. Pass through all token/done/error events
    5. On VoiceUnavailable: stop audio_ref emission, continue token flow (ASSUM-006)

    Args:
        token_stream: Upstream turn event stream (token/done/transcript/error events).
        session_id: Session identifier for chunk storage scoping.
        audio_client: AudioClient for text-to-speech synthesis.
        chunk_store: ChunkStore for in-memory audio chunk storage.
        verifier: Quote verification callable (from TASK-VS2-002 contract).

    Yields:
        TurnEvent frames: original events plus audio_ref frames for each chunk.

    Raises:
        Nothing - VoiceUnavailable is caught and logged, TTS stops but tokens continue.

    Examples:
        >>> async for event in stream_with_audio_refs(
        ...     token_stream=upstream_events,
        ...     session_id="sess123",
        ...     audio_client=client,
        ...     chunk_store=store,
        ...     verifier=verifier_fn,
        ... ):
        ...     # Handle event (token, audio_ref, done, etc.)
    """
    # Accumulated text for verification and chunking
    accumulated_text = ""
    last_released_pos = 0
    chunk_seq = 0
    tts_failed = False  # Flag to stop audio_ref emission after first failure

    # Buffer for current sentence
    sentence_buffer = ""

    async for event in token_stream:
        # Pass through non-token events immediately
        if event.type != "token":
            # Process any remaining sentence before done/error
            if event.type == "done" and sentence_buffer.strip() and not tts_failed:
                # Final sentence
                accumulated_text += sentence_buffer
                verified_chunk = _verify_and_get_chunk(
                    accumulated_text, last_released_pos, verifier
                )

                if verified_chunk:
                    audio_ref = await _synthesize_and_store(
                        chunk_text=verified_chunk,
                        seq=chunk_seq,
                        session_id=session_id,
                        audio_client=audio_client,
                        chunk_store=chunk_store,
                    )

                    if audio_ref:
                        yield audio_ref
                    else:
                        tts_failed = True

            yield event
            continue

        # Token event: accumulate and check for sentence boundaries
        assert event.text is not None, "Token event must have text"
        sentence_buffer += event.text

        # Yield token immediately (pass-through)
        yield event

        # Check if we have a complete sentence
        if _is_sentence_complete(sentence_buffer) and not tts_failed:
            # Update accumulated text
            accumulated_text += sentence_buffer

            # Verify and get chunk
            verified_chunk = _verify_and_get_chunk(
                accumulated_text, last_released_pos, verifier
            )

            if verified_chunk:
                # Synthesize and emit audio_ref
                audio_ref = await _synthesize_and_store(
                    chunk_text=verified_chunk,
                    seq=chunk_seq,
                    session_id=session_id,
                    audio_client=audio_client,
                    chunk_store=chunk_store,
                )

                if audio_ref:
                    yield audio_ref
                    chunk_seq += 1
                    last_released_pos = len(accumulated_text)
                else:
                    # TTS failed
                    tts_failed = True

            # Reset sentence buffer
            sentence_buffer = ""


def _is_sentence_complete(text: str) -> bool:
    """Check if text ends with a sentence terminator."""
    stripped = text.rstrip()
    if not stripped:
        return False
    return stripped[-1] in ".!?"


def _verify_and_get_chunk(
    accumulated_text: str,
    last_released_pos: int,
    verifier: Callable[[str], Any],
) -> str | None:
    """Verify accumulated text and return the new chunk.

    Args:
        accumulated_text: Full accumulated text so far.
        last_released_pos: Position of last released chunk.
        verifier: Verification callable.

    Returns:
        Verified chunk text or None if verification fails.
    """
    try:
        result = verifier(accumulated_text)

        # Check for verifier exception (ASSUM-007 fail-closed)
        if result.metadata.verifier_exception:
            logger.error(
                "Quote verification failed: verifier_exception=True",
                extra={
                    "event": "chunk_verification_failed",
                    "accumulated_length": len(accumulated_text),
                },
            )
            return None

        # Extract new chunk from last release position
        chunk = accumulated_text[last_released_pos:].rstrip()
        return chunk if chunk else None

    except Exception as e:
        logger.error(
            "Verification error",
            extra={
                "event": "verification_error",
                "error": str(e),
            },
        )
        return None


async def _synthesize_and_store(
    *,
    chunk_text: str,
    seq: int,
    session_id: str,
    audio_client: AudioClient,
    chunk_store: ChunkStore,
) -> TurnEvent | None:
    """Synthesize audio and store in chunk store, return audio_ref event.

    Args:
        chunk_text: Verified chunk text to synthesize.
        seq: Sequence number for this chunk.
        session_id: Session identifier.
        audio_client: AudioClient for synthesis.
        chunk_store: ChunkStore for storage.

    Returns:
        TurnEvent audio_ref event or None if TTS fails.
    """
    try:
        # Synthesize audio for verified chunk
        audio_bytes = await audio_client.synthesize(chunk_text, response_format="wav")

        # Store in chunk store
        chunk_id = chunk_store.put(session_id, audio_bytes)

        # Construct URL
        url = f"/api/sessions/{session_id}/voice-audio/{chunk_id}"

        logger.debug(
            "Emitted audio_ref frame",
            extra={
                "event": "audio_ref_emitted",
                "session_id": session_id,
                "seq": seq,
                "chunk_id": chunk_id,
            },
        )

        # Return audio_ref event
        return TurnEvent(
            type="audio_ref",
            seq=seq,
            chunk_id=chunk_id,
            url=url,
        )

    except VoiceUnavailable as e:
        # ASSUM-006: TTS failure stops audio_ref emission
        logger.warning(
            "TTS unavailable mid-answer, stopping audio_ref emission",
            extra={
                "event": "tts_mid_answer_failure",
                "session_id": session_id,
                "chunk_seq": seq,
                "error": str(e),
            },
        )
        return None


__all__ = ["stream_with_audio_refs"]
