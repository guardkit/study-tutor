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

            # Only handle {type:"turn"} frames
            if message.get("type") != "turn":
                logger.warning(
                    "Ignoring non-turn frame",
                    extra={
                        "event": "ws_unexpected_frame_type",
                        "frame_type": message.get("type"),
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
                        reply_stream_fn=websocket.app.state.reply_fn_factory(
                            session_id=session_id, student_id=student_id
                        ),
                    ):
                        # Send event as JSON frame
                        await websocket.send_json({
                            "type": event.type,
                            "text": event.text,
                            "turn_index": event.turn_index,
                            "seq": event.seq,
                            "chunk_id": event.chunk_id,
                            "url": event.url,
                            "error": event.error,
                            "error_type": event.error_type,
                        })

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
