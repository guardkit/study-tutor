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
from starlette.routing import BaseRoute, Route, WebSocketRoute

from study_tutor.gamification import build_student_model_response
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

#: Per-request reply builder: (session_id=, student_id=) → ReplyFn. Lets the
#: transport hand the tutor loop its typed SessionState context (the MCP
#: adapter builds the same boundary object per turn).
ReplyFnFactory = Callable[..., ReplyFn]


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
    Response: {session_id, student_id, resumed, turns?, topic?, opening_prompt?,
    focus_aos?}

    S-R3 §2.3 (binding §2.3): the response gains the three **additive** plan
    fields — ``topic`` (the planned/persisted topic), ``opening_prompt`` (the
    planner's first-turn prompt, not persisted), and ``focus_aos`` (the plan's
    focus AOs, ``[]`` when the planner produced none / degraded). Existing fields
    keep their exact names and semantics.
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

        # Project to contract response shape (§5.1 + §2.3 additive plan fields).
        response_data: dict[str, Any] = {
            "session_id": result.session_id,
            "student_id": result.student_id,
            "resumed": result.resumed,
            # Additive (binding §2.3): the planned topic (persisted) plus the
            # plan's opening_prompt (not persisted) and focus_aos. ``plan`` is
            # None only for legacy/direct construction — degrade to nulls/[].
            "topic": result.topic,
            "opening_prompt": (
                result.plan.opening_prompt if result.plan is not None else None
            ),
            "focus_aos": (
                list(result.plan.focus_aos) if result.plan is not None else []
            ),
        }

        # Include turns only if resumed (AC-005: resumed semantics surface unchanged)
        if result.turns is not None:
            response_data["turns"] = [
                {
                    "role": turn.role,
                    "content": turn.content,
                    "ts": turn.ts.isoformat(),
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
                # Store turn_count is raw transcript rows (learner + tutor row
                # per exchange); the contract's turn_count is (user, tutor)
                # PAIRS — binding §5 + scope §3.6 ("two turns → turn_count: 2").
                # Halve, mirroring the MCP adapter's
                # student_turn_count = turn_count // 2 (mcp/adapter.py).
                "turn_count": s.turn_count // 2,
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
                    "ts": turn.ts.isoformat(),
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
        reply_fn: ReplyFn = request.app.state.reply_fn_factory(
            session_id=session_id, student_id=student_id
        )

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
            # Rows → (user, tutor) pairs per binding §5 + scope §3.6
            # (see list_sessions).
            "turn_count": result.turn_count // 2,
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

    S-R3 §2.4 / D14: the transport no longer passes ``completion`` — completion
    assembly lives in ``SessionService.end_session``, which builds it from the
    persisted session row for ALL transports (HTTP and MCP write identically).

    S-E3 (contract Revision 2 §5): the response gains a **nullable** ``gamification``
    settlement block, present once the engine settles the session and absent while
    unsettled. It is built in the service (D14); the handler only surfaces it.
    """
    try:
        student_id = await _resolve_student_id(request)
        session_id = request.path_params["session_id"]

        service: SessionService = request.app.state.service
        result = await service.end_session(
            student_id=student_id,
            session_id=session_id,
        )

        # Project to contract response shape (§5.6 + Revision 2 §5). The
        # gamification block is nullable: included only when settlement produced it.
        response_data: dict[str, object] = {
            "session_id": result.session_id,
            "status": result.status,
        }
        if result.gamification is not None:
            response_data["gamification"] = result.gamification

        return JSONResponse(response_data, status_code=200)

    except (SessionNotFoundError, SessionEnded, SessionForbidden, Unauthenticated) as e:
        return _map_error_to_response(e)
    except Exception as e:
        return _map_error_to_response(e)


async def student_model(request: Request) -> JSONResponse:
    """GET /api/student-model — durable learner record (FEAT-VOICE-004 R05).

    Serves the Reachy robot's ``query_student_model`` tool over the same
    bearer-authenticated binding. Query params: ``subject`` (required),
    ``student_name`` (optional hint, ignored — identity is derived server-side
    from the token, never client-asserted).

    Response is the original R05 shape (``{student_name, streak_days, level_name,
    recent_xp, near_achievements, topic_confidence, data_available}``) plus the
    §2.2.1 enrichment over banked settlement facts: ``total_xp``, ``level_number``
    + within-level progress, ``longest_streak``, ``recent_achievements`` (last 5),
    ``near_achievements`` (now top-3 objects), and ``next_unlock``. The projection
    (``study_tutor.gamification``) sums banked XP; nothing is re-derived here.

    Errors: unseeded/invalid token → 401 (never 500, ASSUM-001); a
    seeded-but-empty record → 200 with ``data_available: false`` (never 500 for
    "nothing logged"); malformed request (missing ``subject``) → 400 (no
    error_type, §4.2).
    """
    try:
        student_id = await _resolve_student_id(request)

        # subject is required by the binding (§2.2). It is not yet used to filter
        # server-side — the Phase-1 record is single-subject — but it is a hard
        # contract param, so its absence is a 400, consistent with other verbs.
        subject = request.query_params.get("subject")
        if not subject:
            raise ValueError("subject query parameter is required")

        store = request.app.state.student_store
        gamification = await store.get_gamification_state(student_id)
        topic_confidences = await store.get_topic_confidences(student_id)

        response_data = build_student_model_response(
            gamification,
            topic_confidences,
            fallback_student_id=student_id,
        )
        return JSONResponse(response_data, status_code=200)

    except Unauthenticated as e:
        return _map_error_to_response(e)
    except (ValueError, KeyError, TypeError) as e:
        # Missing/malformed required param → 400 (no error_type, §4.2)
        logger.warning("Validation error in student_model: %s", e)
        return JSONResponse(
            {"error": f"Validation failed: {e}"},
            status_code=400,
        )
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
    reply_fn: ReplyFn | None = None,
    auth_config: HTTPAuthConfig,
    student_store: Any,
    reply_fn_factory: ReplyFnFactory | None = None,
    reply_stream_fn_factory: Callable[..., Any] | None = None,
    voice_config: Any | None = None,
    voice_service: Any | None = None,
    chunk_store: Any | None = None,
) -> Starlette:
    """Create Starlette app with the six session routes and optional voice routes.

    Args:
        service: SessionService instance (injected, can be fake for tests).
        reply_fn: Session-agnostic tutor reply function (tests). Ignored when
            reply_fn_factory is supplied.
        auth_config: HTTPAuthConfig with token→student_id mapping.
        student_store: StudentStore instance for unseeded-student guard.
        reply_fn_factory: Per-request reply builder receiving the turn's
            session_id/student_id (production — threads the typed
            SessionState into the tutor loop). Exactly one of reply_fn /
            reply_fn_factory is required.
        reply_stream_fn_factory: Per-request streaming reply builder for the
            WS turn path (S-R4 §2.7 — an async-iterator ``ReplyStreamFn``).
            When omitted, a default adapts the non-streaming reply into a
            single-chunk stream so the WS route stays functional.
        voice_config: Optional VoiceConfig (TASK-VOX-006). When enabled, voice routes
            are mounted.
        voice_service: Optional VoiceTurnService for voice routes.
        chunk_store: Optional ChunkStore for voice audio retrieval.

    Returns:
        Configured Starlette application.
    """
    if reply_fn_factory is None:
        if reply_fn is None:
            raise ValueError(
                "create_app requires reply_fn or reply_fn_factory"
            )
        _session_agnostic_reply = reply_fn

        def reply_fn_factory(**_context: str) -> ReplyFn:
            return _session_agnostic_reply

    # S-R4 §2.7: the WS turn path needs a streaming ReplyStreamFn factory.
    # When production wires a real one (serve-http), use it; otherwise adapt
    # the non-streaming reply into a single-chunk stream so the WS route
    # (and its tests) stay functional.
    if reply_stream_fn_factory is None:
        _resolved_reply_fn_factory = reply_fn_factory

        def reply_stream_fn_factory(**context: str) -> Any:
            _reply_fn = _resolved_reply_fn_factory(**context)

            async def _single_chunk_stream(user_message: str) -> Any:
                reply = await _reply_fn(user_message)
                text = getattr(reply, "response", "") or ""
                if text:
                    yield text

            return _single_chunk_stream

    # Route table exactly per binding doc §2 (frozen contract). Typed as
    # list[BaseRoute] so the conditional voice WebSocketRoute append typechecks
    # alongside the Route entries (both subclass BaseRoute).
    routes: list[BaseRoute] = [
        Route("/healthz", healthz, methods=["GET"]),  # TASK-APP1-04: READY health check
        Route("/api/sessions/start", start_session, methods=["POST"]),
        Route("/api/sessions", list_sessions, methods=["GET"]),
        Route("/api/sessions/{session_id:str}/resume", resume_session, methods=["GET"]),
        Route("/api/sessions/{session_id:str}/turn", turn, methods=["POST"]),
        Route("/api/sessions/{session_id:str}/status", session_status, methods=["GET"]),
        Route("/api/sessions/{session_id:str}/end", end_session, methods=["POST"]),
        # FEAT-VOICE-004 R05: additive read verb — durable student-model
        # projection for the Reachy query_student_model tool. Always mounted and
        # bearer-authed like the six session verbs (binding §2.2). Does NOT touch
        # the frozen voice CONTRACT_SHA/BINDING_SHA.
        Route("/api/student-model", student_model, methods=["GET"]),
    ]

    # TASK-APP1-05: Mount /__dev__/reset ONLY when dev_reset flag is set
    # When flag is off, route does not exist (unknown route 404, not 403)
    if auth_config.dev_reset:
        routes.append(Route("/__dev__/reset", dev_reset, methods=["POST"]))

    # TASK-VOX-006: Mount voice routes ONLY when voice_config.enabled is True
    # When flag is off, routes do not exist (unknown route 404, not 403)
    if voice_config is not None and voice_config.enabled:
        from study_tutor.voice.routes import voice_turn, voice_audio

        routes.append(
            Route("/api/sessions/{session_id:str}/voice-turn", voice_turn, methods=["POST"])
        )
        routes.append(
            Route("/api/sessions/{session_id:str}/voice-audio/{chunk_id:str}", voice_audio, methods=["GET"])
        )

        # TASK-VS2-004: Mount WebSocket route for streaming turns
        from study_tutor.http.ws import websocket_endpoint

        routes.append(
            WebSocketRoute("/api/sessions/{session_id:str}/ws", websocket_endpoint)
        )

    app = Starlette(debug=False, routes=routes)

    # Inject dependencies into app.state for handlers to access
    app.state.service = service
    app.state.reply_fn = reply_fn
    app.state.reply_fn_factory = reply_fn_factory
    app.state.reply_stream_fn_factory = reply_stream_fn_factory
    app.state.auth_config = auth_config
    app.state.student_store = student_store

    # TASK-VOX-006: Inject voice dependencies when available
    if voice_config is not None and voice_config.enabled:
        app.state.voice_config = voice_config
        app.state.voice_service = voice_service
        app.state.chunk_store = chunk_store

    return app


__all__ = [
    "create_app",
]
