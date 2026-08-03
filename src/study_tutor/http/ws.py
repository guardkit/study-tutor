"""WebSocket route for streaming turns (TASK-VS2-004).

WebSocketRoute `GET /api/sessions/{session_id}/ws` for streaming TurnEvent frames
over WebSocket with auth-at-upgrade, feature flag gating (STUDY_TUTOR_VOICE_ENABLED),
per-session ordering lock, and terminal error handling.

Binding §2.1 Rev 1 contract compliance: auth-at-upgrade, terminal vs non-terminal
error close behavior, frozen frame vocabulary (§7 Rev 1).
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any

from starlette.websockets import WebSocket, WebSocketDisconnect

from study_tutor.http.auth import HTTPAuthConfig, resolve_student_from_token
from study_tutor.session.errors import (
    SessionNotFoundError,
    SessionEnded,
    SessionForbidden,
    Unauthenticated,
)
from study_tutor.session.service import SessionService, TurnEvent
from study_tutor.voice.streaming_tts import stream_with_audio_refs
from study_tutor.voice.ws_voice_turn import handle_voice_turn_frame

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-session ordering lock (ASSUM-008)
# ---------------------------------------------------------------------------

#: Per-session locks to serialize turn processing. Maps session_id → asyncio.Lock.
#: Ensures two concurrent turns on the same session (same or different connections)
#: are processed strictly in arrival order with no frame interleaving.
_session_locks: dict[str, asyncio.Lock] = {}


def _get_session_lock(session_id: str) -> asyncio.Lock:
    """Get or create a per-session lock for turn ordering.

    Args:
        session_id: Session identifier.

    Returns:
        asyncio.Lock for this session.
    """
    if session_id not in _session_locks:
        _session_locks[session_id] = asyncio.Lock()
    return _session_locks[session_id]


# ---------------------------------------------------------------------------
# Error handling (contract §9 terminal errors)
# ---------------------------------------------------------------------------


def _is_terminal_error(error: Exception) -> bool:
    """Check if error is terminal (requires immediate close).

    Terminal errors (ASSUM-003 terminal class):
    - Unauthenticated (missing/invalid token)
    - SessionForbidden (wrong student)
    - SessionNotFoundError (unknown session)
    - SessionEnded (session ended)

    Args:
        error: Exception from auth or service layer.

    Returns:
        True if error should trigger immediate WebSocket close.
    """
    return isinstance(
        error, (Unauthenticated, SessionForbidden, SessionNotFoundError, SessionEnded)
    )


def _event_frame(event: TurnEvent) -> dict[str, Any]:
    """Serialize a TurnEvent to the §7 Rev 1 wire frame.

    One shape for both the streamed text turn and the streamed voice
    turn — the frame vocabulary is shared (contract §7).
    """
    return {
        "type": event.type,
        "text": event.text,
        "turn_index": event.turn_index,
        "seq": event.seq,
        "chunk_id": event.chunk_id,
        "url": event.url,
        "error": event.error,
        "error_type": event.error_type,
    }


async def _send_error_and_close(
    websocket: WebSocket, error: Exception, error_type: str
) -> None:
    """Send error frame then close WebSocket (terminal error pattern).

    Args:
        websocket: Active WebSocket connection.
        error: Exception to send.
        error_type: Error type string (closed-set from contract §9).
    """
    try:
        await websocket.send_json({
            "type": "error",
            "error": str(error),
            "error_type": error_type,
        })
    except Exception as send_error:
        logger.warning(
            "Failed to send error frame before close",
            extra={
                "event": "ws_error_frame_send_failed",
                "error_type": type(send_error).__name__,
                "error": str(send_error),
            },
        )
    finally:
        await websocket.close()


# ---------------------------------------------------------------------------
# WebSocket route handler
# ---------------------------------------------------------------------------


async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming turns (binding §2.1 Rev 1).

    Route: GET /api/sessions/{session_id}/ws

    Flow:
    1. Accept WebSocket connection
    2. Auth-at-upgrade: resolve student_id from Authorization header
    3. Wait for {type:"turn"} frame
    4. Acquire per-session lock (ASSUM-008 ordering guarantee)
    5. Stream TurnEvent frames from SessionService.turn_stream
    6. Handle terminal errors: send error frame then close

    Args:
        websocket: Starlette WebSocket connection.
    """
    await websocket.accept()

    # Extract injected dependencies from app.state
    service: SessionService = websocket.app.state.service
    auth_config: HTTPAuthConfig = websocket.app.state.auth_config
    student_store: Any = websocket.app.state.student_store

    session_id: str = websocket.path_params["session_id"]

    # Auth-at-upgrade: resolve student_id from Authorization header
    try:
        student_id = await resolve_student_from_token(
            authorization_header=websocket.headers.get("authorization"),
            config=auth_config,
            student_store=student_store,
        )
    except Unauthenticated as e:
        await _send_error_and_close(websocket, e, "Unauthenticated")
        return

    # Main message loop
    try:
        while True:
            # Wait for incoming message
            try:
                message = await websocket.receive_json()
            except WebSocketDisconnect:
                logger.info(
                    "WebSocket disconnected",
                    extra={
                        "event": "ws_client_disconnect",
                        "session_id": session_id,
                        "student_id": student_id,
                    },
                )
                return

            frame_type = message.get("type")

            # Streamed voice turn (contract §7 Rev 1): header frame then
            # ONE binary audio frame. This dispatch was the missing half
            # of TASK-VS2-006 — the handler existed, the endpoint dropped
            # the header and then crashed on the binary frame (found live
            # 2026-08-03; the app had silently ridden the HTTP fallback
            # while the WS path 403'd on its old wrong path).
            if frame_type == "voice_turn":
                content_type = str(message.get("content_type", ""))
                try:
                    audio_bytes = await websocket.receive_bytes()
                except WebSocketDisconnect:
                    logger.info(
                        "WebSocket disconnected before voice binary frame",
                        extra={
                            "event": "ws_client_disconnect",
                            "session_id": session_id,
                            "student_id": student_id,
                        },
                    )
                    return

                voice_config = getattr(websocket.app.state, "voice_config", None)
                voice_service = getattr(websocket.app.state, "voice_service", None)
                chunk_store = getattr(websocket.app.state, "chunk_store", None)
                if voice_config is None or voice_service is None or chunk_store is None:
                    # /ws is only mounted with voice enabled, so this is a
                    # wiring fault, not a client error — non-terminal, per
                    # the handler's VoiceUnavailable posture.
                    await websocket.send_json({
                        "type": "error",
                        "error": "Voice services not wired",
                        "error_type": "VoiceUnavailable",
                    })
                    continue

                lock = _get_session_lock(session_id)
                async with lock:
                    # The transcript is only known mid-generator; the
                    # factory closes over this holder, and the handler
                    # guarantees the transcript frame is yielded (and
                    # forwarded below, filling the holder) BEFORE it calls
                    # the factory — lazy generators make that ordering
                    # sound.
                    transcript_holder: dict[str, str] = {}

                    def _turn_stream(
                        _sid: str = session_id, _stu: str = student_id
                    ) -> Any:
                        return service.turn_stream(
                            student_id=_stu,
                            session_id=_sid,
                            user_message=transcript_holder.get("text", ""),
                            reply_stream_fn=websocket.app.state.reply_stream_fn_factory(
                                session_id=_sid, student_id=_stu
                            ),
                        )

                    try:
                        # ADR-ARCH-027 composition: the turn stream's
                        # tokens are already verified sentence deltas
                        # (run_turn_stream_verified), so the audio layer
                        # runs verifier-free — it synthesizes each
                        # released sentence and emits audio_ref frames
                        # interleaved with the token flow (§7 Rev 1).
                        voice_events = handle_voice_turn_frame(
                            audio_bytes=audio_bytes,
                            content_type=content_type,
                            config=voice_config,
                            audio_client=voice_service.audio_client,
                            turn_stream_fn=_turn_stream,
                        )
                        async for event in stream_with_audio_refs(
                            token_stream=voice_events,
                            session_id=session_id,
                            audio_client=voice_service.audio_client,
                            chunk_store=chunk_store,
                            verifier=None,
                        ):
                            if event.type == "transcript":
                                transcript_holder["text"] = event.text or ""
                            await websocket.send_json(_event_frame(event))
                    except (
                        SessionForbidden,
                        SessionNotFoundError,
                        SessionEnded,
                    ) as e:
                        # Terminal errors: error frame then close (ASSUM-003)
                        await _send_error_and_close(
                            websocket, e, type(e).__name__
                        )
                        return
                continue

            # Only handle {type:"turn"} frames beyond this point
            if frame_type != "turn":
                logger.warning(
                    "Ignoring non-turn frame",
                    extra={
                        "event": "ws_unexpected_frame_type",
                        "frame_type": frame_type,
                        "session_id": session_id,
                    },
                )
                continue

            user_message = message.get("text", "")

            # Acquire per-session lock to ensure strict ordering (ASSUM-008)
            lock = _get_session_lock(session_id)

            async with lock:
                try:
                    # Stream turn events from SessionService
                    async for event in service.turn_stream(
                        student_id=student_id,
                        session_id=session_id,
                        user_message=user_message,
                        # S-R4 §2.7: the real streaming ReplyStreamFn factory
                        # (async-iterator product), not the non-streaming
                        # ReplyFn this line wrongly passed before.
                        reply_stream_fn=websocket.app.state.reply_stream_fn_factory(
                            session_id=session_id, student_id=student_id
                        ),
                    ):
                        # Send event as JSON frame (§7 shared vocabulary)
                        await websocket.send_json(_event_frame(event))

                except (SessionForbidden, SessionNotFoundError, SessionEnded) as e:
                    # Terminal errors: send error frame then close (ASSUM-003)
                    error_type = type(e).__name__
                    await _send_error_and_close(websocket, e, error_type)
                    return

                except Exception as e:
                    # Unexpected error: log and send generic error
                    logger.exception(
                        "Unexpected error in turn stream",
                        extra={
                            "event": "ws_turn_stream_error",
                            "session_id": session_id,
                            "student_id": student_id,
                            "error_type": type(e).__name__,
                            "error": str(e),
                        },
                    )
                    await _send_error_and_close(
                        websocket, Exception("Internal server error"), "internal_error"
                    )
                    return

    except Exception as e:
        # Outer exception handler for unexpected errors
        logger.exception(
            "WebSocket handler error",
            extra={
                "event": "ws_handler_error",
                "session_id": session_id,
                "error_type": type(e).__name__,
                "error": str(e),
            },
        )
        try:
            await websocket.close()
        except Exception:
            pass  # Best effort close


__all__ = ["websocket_endpoint"]
