"""Voice HTTP routes (TASK-VOX-006).

Two flag-gated voice endpoints bound to frozen contract (binding §2/§4 Rev 1):
- POST /api/sessions/{session_id}/voice-turn: multipart audio upload → transcript + audio refs
- GET /api/sessions/{session_id}/voice-audio/{chunk_id}: retrieve audio chunks

Both routes enforce session ownership via _resolve_student_id (app.py:88-110 pattern)
and map errors per-handler (no middleware).
"""

from __future__ import annotations

import logging

from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from study_tutor.http.auth import resolve_student_from_token
from study_tutor.session.errors import (
    SessionNotFoundError,
    SessionEnded,
    SessionForbidden,
    Unauthenticated,
)
from study_tutor.voice.errors import (
    RecordingTooLarge,
    QueryTooLong,
    UnsupportedAudioFormat,
    EmptyRecording,
    UnintelligibleQuery,
    VoiceUnavailable,
)
from study_tutor.voice.service import VoiceTurnService, ChunkStore

logger = logging.getLogger(__name__)


# -------------------- Error mapping --------------------


def _map_voice_error_to_response(error: Exception) -> JSONResponse:
    """Map voice and session errors to HTTP status + flat envelope.

    Voice errors (RecordingTooLarge, QueryTooLong, etc.) map to their specific
    status codes with error_type (binding §2 Rev 1). Session errors
    (SessionNotFoundError, etc.) reuse app.py error mapping.

    Args:
        error: Exception from voice service or auth/session layer.

    Returns:
        JSONResponse with appropriate status code and error envelope.
    """
    # Voice-specific errors (binding §2 Rev 1)
    if isinstance(error, RecordingTooLarge):
        return JSONResponse(
            {"error": str(error), "error_type": "RecordingTooLarge"},
            status_code=413,
        )
    if isinstance(error, QueryTooLong):
        return JSONResponse(
            {"error": str(error), "error_type": "QueryTooLong"},
            status_code=413,
        )
    if isinstance(error, UnsupportedAudioFormat):
        return JSONResponse(
            {"error": str(error), "error_type": "UnsupportedAudioFormat"},
            status_code=415,
        )
    if isinstance(error, EmptyRecording):
        return JSONResponse(
            {"error": str(error), "error_type": "EmptyRecording"},
            status_code=422,
        )
    if isinstance(error, UnintelligibleQuery):
        return JSONResponse(
            {"error": str(error), "error_type": "UnintelligibleQuery"},
            status_code=422,
        )
    if isinstance(error, VoiceUnavailable):
        return JSONResponse(
            {"error": str(error), "error_type": "VoiceUnavailable"},
            status_code=503,
        )

    # Session errors (existing mapping from app.py)
    if isinstance(error, SessionNotFoundError):
        return JSONResponse(
            {"error": str(error), "error_type": "SessionNotFoundError"},
            status_code=404,
        )
    if isinstance(error, SessionEnded):
        return JSONResponse(
            {"error": str(error), "error_type": "SessionEnded"},
            status_code=410,
        )
    if isinstance(error, SessionForbidden):
        return JSONResponse(
            {"error": str(error), "error_type": "SessionForbidden"},
            status_code=403,
        )
    if isinstance(error, Unauthenticated):
        return JSONResponse(
            {"error": str(error), "error_type": "Unauthenticated"},
            status_code=401,
        )

    # Unexpected server error (binding doc §4.2 — no error_type)
    logger.exception("Unexpected error in voice handler: %s", error)
    return JSONResponse(
        {"error": "Internal server error"},
        status_code=500,
    )


async def _resolve_student_id(request: Request) -> str:
    """Extract and resolve student_id from Authorization header.

    Mirrors app.py:88-110 pattern using auth config and student store from app.state.

    Args:
        request: Starlette request with Authorization header.

    Returns:
        Resolved student_id from token table.

    Raises:
        Unauthenticated: On missing/invalid token or unseeded student.
    """
    auth_header = request.headers.get("Authorization")
    auth_config = request.app.state.auth_config
    student_store = request.app.state.student_store

    student_id = await resolve_student_from_token(
        authorization_header=auth_header,
        config=auth_config,
        student_store=student_store,
    )

    return student_id


# -------------------- Route handlers --------------------


async def voice_turn(request: Request) -> JSONResponse:
    """POST /api/sessions/{session_id}/voice-turn.

    Multipart audio upload → transcript + tutor_response + audio refs.
    Enforces session ownership and maps errors per binding §2/§2.1 Rev 1.

    Args:
        request: Starlette request with path param session_id and multipart audio.

    Returns:
        JSONResponse with {transcript, tutor_response, audio:[{seq, chunk_id, url}]}.

    Raises:
        RecordingTooLarge: Audio exceeds size limit → 413.
        QueryTooLong: Audio duration exceeds limit → 413.
        UnsupportedAudioFormat: Invalid MIME type → 415.
        EmptyRecording: Audio field is empty → 422.
        UnintelligibleQuery: Transcript is empty/whitespace → 422.
        VoiceUnavailable: STT/TTS service unavailable → 503.
        SessionNotFoundError: Session not found → 404.
        SessionEnded: Session has ended → 410.
        SessionForbidden: Student doesn't own session → 403.
        Unauthenticated: Missing/invalid token → 401.
    """
    try:
        # Resolve student_id from Authorization header (app.py:88-110 pattern)
        student_id = await _resolve_student_id(request)

        # Extract session_id from path
        session_id = request.path_params["session_id"]

        # Get voice service from app state
        voice_service: VoiceTurnService = request.app.state.voice_service

        # Execute voice turn (validation, STT, turn, TTS, storage)
        result = await voice_service.voice_turn(
            session_id=session_id,
            student_id=student_id,
            request=request,
        )

        # Project VoiceTurnResult to JSON envelope
        return JSONResponse(
            {
                "transcript": result.transcript,
                "tutor_response": result.tutor_response,
                "audio": [
                    {
                        "seq": ref.seq,
                        "chunk_id": ref.chunk_id,
                        "url": ref.url,
                    }
                    for ref in result.audio
                ],
            },
            status_code=200,
        )

    except Exception as error:
        return _map_voice_error_to_response(error)


async def voice_audio(request: Request) -> Response:
    """GET /api/sessions/{session_id}/voice-audio/{chunk_id}.

    Retrieve audio chunk as audio/wav bytes. Chunk miss → 404 without error_type
    (binding §4.2 Rev 1).

    Args:
        request: Starlette request with path params session_id and chunk_id.

    Returns:
        Response with audio/wav bytes or 404 JSON error.

    Raises:
        Unauthenticated: Missing/invalid token → 401.
    """
    try:
        # Resolve student_id from Authorization header (enforce auth, but don't
        # verify session ownership since audio chunks are session-scoped already)
        await _resolve_student_id(request)

        # Extract path params
        session_id = request.path_params["session_id"]
        chunk_id = request.path_params["chunk_id"]

        # Get chunk store from app state
        chunk_store: ChunkStore = request.app.state.chunk_store

        # Retrieve audio chunk
        audio_bytes = chunk_store.get(session_id, chunk_id)

        if audio_bytes is None:
            # Chunk miss → 404 with NO error_type (binding §4.2 Rev 1)
            return JSONResponse(
                {"error": "audio chunk expired or unknown"},
                status_code=404,
            )

        # Return audio/wav bytes with correct content-type
        return Response(
            content=audio_bytes,
            media_type="audio/wav",
            status_code=200,
        )

    except Unauthenticated as error:
        return _map_voice_error_to_response(error)
    except Exception as error:
        # Unexpected error (no error_type)
        logger.exception("Unexpected error in voice_audio handler: %s", error)
        return JSONResponse(
            {"error": "Internal server error"},
            status_code=500,
        )


__all__ = [
    "voice_turn",
    "voice_audio",
]
