"""Starlette HTTP app for session API (TASK-APP1-03).

Six JSON endpoints (contract §5) over SessionService with §9 error envelope mapping.
Routes match docs/design/contracts/API-session-http-binding.md exactly (frozen contract).

No WebSocket streaming this wave — turn_stream stays NotImplementedError per AC-001.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from study_tutor.http.auth import HTTPAuthConfig, resolve_student_from_token
from study_tutor.session.errors import (
    SessionNotFoundError,
    SessionEnded,
    SessionForbidden,
    Unauthenticated,
)
from study_tutor.session.service import (
    SessionService,
    TutorReply,
)

logger = logging.getLogger(__name__)

# Type alias for the injected reply function
ReplyFn = Callable[[str], Awaitable[TutorReply]]


# -------------------- Error mapping (contract §9 + §4) --------------------


def _map_error_to_response(error: Exception) -> JSONResponse:
    """Map closed-set domain errors to HTTP status + flat envelope (contract §9).

    Closed-set errors get error_type (SessionNotFoundError, SessionEnded,
    SessionForbidden, Unauthenticated). Transport errors (validation, unexpected)
    get no error_type per contract §4.2.

    Args:
        error: Exception from service or auth layer.

    Returns:
        JSONResponse with appropriate status code and error envelope.
    """
    # Closed-set domain errors (contract §9, binding doc §4.1)
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
    logger.exception("Unexpected error in HTTP handler: %s", error)
    return JSONResponse(
        {"error": "Internal server error"},
        status_code=500,
    )


async def _resolve_student_id(request: Request) -> str:
    """Extract and resolve student_id from Authorization header.

    Uses the auth config and student store injected into app.state.

    Args:
        request: Starlette request with Authorization header.

    Returns:
        Resolved student_id from token table.

    Raises:
        Unauthenticated: On missing/invalid token or unseeded student.
    """
    auth_header = request.headers.get("Authorization")
    auth_config: HTTPAuthConfig = request.app.state.auth_config
    student_store = request.app.state.student_store

    return await resolve_student_from_token(
        authorization_header=auth_header,
        config=auth_config,
        student_store=student_store,
    )


# -------------------- Route handlers --------------------


async def start_session(request: Request) -> JSONResponse:
    """POST /api/sessions/start — create or resume session (contract §5.1).

    Request body: {subject?, topic?, resume_if_active?}
    Response: {session_id, student_id, resumed, turns?}
    """
    try:
        student_id = await _resolve_student_id(request)
        body = await request.json()

        # Validate body is a dict (malformed type → 400, not 500)
        if not isinstance(body, dict):
            raise ValueError(
                f"Request body must be a JSON object, not {type(body).__name__}"
            )

        service: SessionService = request.app.state.service
        result = await service.start_session(
            student_id=student_id,
            subject=body.get("subject", ""),
            topic=body.get("topic"),
            resume_if_active=body.get("resume_if_active", False),
        )

        # Project to contract response shape (§5.1)
        response_data: dict[str, Any] = {
            "session_id": result.session_id,
            "student_id": result.student_id,
            "resumed": result.resumed,
        }

        # Include turns only if resumed (AC-005: resumed semantics surface unchanged)
        if result.turns is not None:
            response_data["turns"] = [
                {
                    "role": turn.role,
                    "content": turn.content,
                    "timestamp": turn.ts.isoformat(),
                }
                for turn in result.turns
            ]

        return JSONResponse(response_data, status_code=200)

    except (SessionNotFoundError, SessionEnded, SessionForbidden, Unauthenticated) as e:
        return _map_error_to_response(e)
    except (ValueError, KeyError, TypeError) as e:
        # Malformed/missing required fields → 400 validation error (no error_type, §4.2)
        logger.warning("Validation error in start_session: %s", e)
        return JSONResponse(
            {"error": f"Validation failed: {e}"},
            status_code=400,
        )
    except Exception as e:
        return _map_error_to_response(e)


async def list_sessions(request: Request) -> JSONResponse:
    """GET /api/sessions — list caller's sessions (contract §5.2).

    Query params: status?, limit?
    Response: [{session_id, subject, topic, status, started_at, last_activity, turn_count}]
    """
    try:
        student_id = await _resolve_student_id(request)

        # Parse query params
        status_param = request.query_params.get("status")
        limit_param = request.query_params.get("limit", "20")

        service: SessionService = request.app.state.service
        sessions = await service.list_sessions(
            student_id=student_id,
            status=status_param,  # type: ignore
            limit=int(limit_param),
        )

        # Project to contract response shape (§5.2)
        response_data = [
            {
                "session_id": s.session_id,
                "subject": s.subject,
                "topic": s.topic,
                "status": s.status,
                "started_at": s.started_at.isoformat(),
                "last_activity": s.last_activity.isoformat(),
                "turn_count": s.turn_count,
            }
            for s in sessions
        ]

        return JSONResponse(response_data, status_code=200)

    except Unauthenticated as e:
        return _map_error_to_response(e)
    except Exception as e:
        return _map_error_to_response(e)


async def resume_session(request: Request) -> JSONResponse:
    """GET /api/sessions/{session_id}/resume — rehydrate transcript (contract §5.3).

    Path param: session_id
    Response: {session_id, status, turns, student_id}
    """
    try:
        student_id = await _resolve_student_id(request)
        session_id = request.path_params["session_id"]

        service: SessionService = request.app.state.service
        result = await service.resume_session(
            student_id=student_id,
            session_id=session_id,
        )

        # Project to contract response shape (§5.3 — ordered transcript)
        response_data = {
            "session_id": result.session_id,
            "student_id": result.student_id,
            "status": result.status,
            "turns": [
                {
                    "role": turn.role,
                    "content": turn.content,
                    "timestamp": turn.ts.isoformat(),
                }
                for turn in result.turns
            ],
        }

        return JSONResponse(response_data, status_code=200)

    except (SessionNotFoundError, SessionEnded, SessionForbidden, Unauthenticated) as e:
        return _map_error_to_response(e)
    except Exception as e:
        return _map_error_to_response(e)


async def turn(request: Request) -> JSONResponse:
    """POST /api/sessions/{session_id}/turn — process user turn (contract §5.4).

    Request body: {user_message, stream?}
    Response: {tutor_response}

    Note: stream is ignored this wave (no WS transport).
    """
    try:
        student_id = await _resolve_student_id(request)
        session_id = request.path_params["session_id"]
        body = await request.json()

        # Validate body is a dict
        if not isinstance(body, dict):
            raise ValueError(
                f"Request body must be a JSON object, not {type(body).__name__}"
            )

        user_message = body.get("user_message")
        if not user_message:
            raise ValueError("user_message is required")

        service: SessionService = request.app.state.service
        reply_fn: ReplyFn = request.app.state.reply_fn

        result = await service.turn(
            student_id=student_id,
            session_id=session_id,
            user_message=user_message,
            reply_fn=reply_fn,
        )

        # Project to contract response shape (§5.4)
        response_data = {
            "tutor_response": result.tutor_response,
        }

        return JSONResponse(response_data, status_code=200)

    except (SessionNotFoundError, SessionEnded, SessionForbidden, Unauthenticated) as e:
        return _map_error_to_response(e)
    except (ValueError, KeyError, TypeError) as e:
        logger.warning("Validation error in turn: %s", e)
        return JSONResponse(
            {"error": f"Validation failed: {e}"},
            status_code=400,
        )
    except Exception as e:
        return _map_error_to_response(e)


async def session_status(request: Request) -> JSONResponse:
    """GET /api/sessions/{session_id}/status — session metadata (contract §5.5).

    Path param: session_id
    Response: {session_id, student_id, status, turn_count, started_at, last_activity, resumable}

    Note: This is the one verb that reads ended sessions (allow_ended=True, §9 carve-out).
    """
    try:
        student_id = await _resolve_student_id(request)
        session_id = request.path_params["session_id"]

        service: SessionService = request.app.state.service
        result = await service.session_status(
            student_id=student_id,
            session_id=session_id,
        )

        # Project to contract response shape (§5.5)
        response_data = {
            "session_id": result.session_id,
            "student_id": result.student_id,
            "status": result.status,
            "turn_count": result.turn_count,
            "started_at": result.started_at.isoformat(),
            "last_activity": result.last_activity.isoformat(),
            "resumable": result.resumable,
        }

        return JSONResponse(response_data, status_code=200)

    except (SessionNotFoundError, SessionForbidden, Unauthenticated) as e:
        return _map_error_to_response(e)
    except Exception as e:
        return _map_error_to_response(e)


async def end_session(request: Request) -> JSONResponse:
    """POST /api/sessions/{session_id}/end — transition to ended (contract §5.6).

    Path param: session_id
    Response: {session_id, status: "ended"}

    Note: completion parameter is None here (wiring in TASK-APP1-04).
    """
    try:
        student_id = await _resolve_student_id(request)
        session_id = request.path_params["session_id"]

        service: SessionService = request.app.state.service
        result = await service.end_session(
            student_id=student_id,
            session_id=session_id,
            completion=None,  # Wiring deferred to TASK-APP1-04
        )

        # Project to contract response shape (§5.6)
        response_data = {
            "session_id": result.session_id,
            "status": result.status,
        }

        return JSONResponse(response_data, status_code=200)

    except (SessionNotFoundError, SessionEnded, SessionForbidden, Unauthenticated) as e:
        return _map_error_to_response(e)
    except Exception as e:
        return _map_error_to_response(e)


async def healthz(request: Request) -> JSONResponse:
    """GET /healthz — READY health check (TASK-APP1-04 AC-001).

    Returns:
        JSON response with status "ok" when server is ready.
    """
    return JSONResponse({"status": "ok"}, status_code=200)


async def dev_reset(request: Request) -> JSONResponse:
    """POST /__dev__/reset — Dev-only session reset (TASK-APP1-05).

    Truncates session + session_turn tables only. Learner-state tables
    (student, topic_confidence, misconception, achievement, quest) are
    untouched — banked XP/streak/confidence survive.

    This route is mounted ONLY when STUDY_TUTOR_HTTP_DEV_RESET is set.

    Returns:
        JSON response with deleted counts: {"deleted": {"sessions": N, "turns": M}}
    """
    try:
        student_store = request.app.state.student_store

        # Call truncate_sessions on the store
        deleted_counts = await student_store.truncate_sessions()

        logger.info(
            "event=dev_reset_executed sessions=%d turns=%d",
            deleted_counts["sessions"],
            deleted_counts["turns"],
        )

        return JSONResponse(
            {"deleted": deleted_counts},
            status_code=200,
        )

    except Exception as e:
        logger.exception("Dev reset failed: %s", e)
        return JSONResponse(
            {"error": "Dev reset failed"},
            status_code=500,
        )


# -------------------- App factory --------------------


def create_app(
    *,
    service: SessionService,
    reply_fn: ReplyFn,
    auth_config: HTTPAuthConfig,
    student_store: Any,
) -> Starlette:
    """Create Starlette app with the six session routes.

    Args:
        service: SessionService instance (injected, can be fake for tests).
        reply_fn: Injected tutor reply function (mirrors SessionService.turn signature).
        auth_config: HTTPAuthConfig with token→student_id mapping.
        student_store: StudentStore instance for unseeded-student guard.

    Returns:
        Configured Starlette application.
    """
    # Route table exactly per binding doc §2 (frozen contract)
    routes = [
        Route("/healthz", healthz, methods=["GET"]),  # TASK-APP1-04: READY health check
        Route("/api/sessions/start", start_session, methods=["POST"]),
        Route("/api/sessions", list_sessions, methods=["GET"]),
        Route("/api/sessions/{session_id:str}/resume", resume_session, methods=["GET"]),
        Route("/api/sessions/{session_id:str}/turn", turn, methods=["POST"]),
        Route("/api/sessions/{session_id:str}/status", session_status, methods=["GET"]),
        Route("/api/sessions/{session_id:str}/end", end_session, methods=["POST"]),
    ]

    # TASK-APP1-05: Mount /__dev__/reset ONLY when dev_reset flag is set
    # When flag is off, route does not exist (unknown route 404, not 403)
    if auth_config.dev_reset:
        routes.append(Route("/__dev__/reset", dev_reset, methods=["POST"]))

    app = Starlette(debug=False, routes=routes)

    # Inject dependencies into app.state for handlers to access
    app.state.service = service
    app.state.reply_fn = reply_fn
    app.state.auth_config = auth_config
    app.state.student_store = student_store

    return app


__all__ = [
    "create_app",
]
