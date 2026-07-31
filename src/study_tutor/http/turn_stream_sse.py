"""Stage 2 — ``GET /api/sessions/{id}/turns/stream``: the mirror's live push.

Server-Sent Events for the phone's **read-only** view of the tutoring session
the Reachy Mini robot is driving. Stage 1 gave the phone a delta read it polls;
this route pushes the same delta the instant a row is persisted, so the robot's
question is on the phone with no poll lag.

Why SSE and not the existing WebSocket: ``/api/sessions/{id}/ws`` is mounted
**only** behind ``STUDY_TUTOR_VOICE_ENABLED`` and carries the frozen contract-§7
streamed-*write* frame vocabulary. The mirror is a one-way reader and must work
with voice off, so it gets its own always-mounted read route. Like Stage 1 this
is **additive**: the six session verbs, the voice routes and their status codes
are untouched, so there is no ``CONTRACT_SHA``/``BINDING_SHA`` re-pin.

Event vocabulary (binding §2.5):

* ``turn_appended`` — data is the **Stage-1 envelope verbatim**
  (``{session_id, status, turns:[{role,content,ts}], next}``, built by the same
  :func:`~study_tutor.http.app.turns_since_payload`), so the app parses a pushed
  delta with the identical code it uses for a polled one.
* ``session_ended`` — data ``{session_id, status: "ended"}``; the last frame,
  then the server closes.
* ``: keepalive`` SSE comments while idle, so proxies do not reap the connection.

Auth and ownership are resolved **before** a single byte streams: a rejected
caller gets the ordinary JSON 401/403/404 envelope with its ordinary status
code, never a 200 stream carrying an error. ``SessionEnded`` (410) is impossible
here for the same reason as Stage 1 — the mirror reads active *and* ended
sessions, and an ended one is a normal, terminal stream.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

from starlette.requests import Request
from starlette.responses import JSONResponse, Response, StreamingResponse

from study_tutor.http.app import (
    _map_error_to_response,
    _resolve_student_id,
    parse_since,
    turns_since_payload,
)
from study_tutor.session.errors import (
    SessionForbidden,
    SessionNotFoundError,
    Unauthenticated,
)
from study_tutor.session.notifier import TurnNotifierPort

logger = logging.getLogger(__name__)

#: Longest a live loop parks before re-reading anyway. The notifier wakes it
#: sooner for in-process writes; this tick is what surfaces a write made by
#: another worker process (the notifier is deliberately in-process only).
DEFAULT_POLL_INTERVAL_SECONDS = 3.0

#: Longest an idle stream stays silent before emitting a keepalive comment.
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 15.0

EVENT_TURN_APPENDED = "turn_appended"
EVENT_SESSION_ENDED = "session_ended"
KEEPALIVE_FRAME = ": keepalive\n\n"


def _sse_event(name: str, data: dict[str, Any]) -> str:
    """One SSE frame: ``event: <name>\\ndata: <json>\\n\\n``.

    ``json.dumps`` emits no newlines, so the payload is always exactly one
    ``data:`` line — no multi-line continuation to parse on the client.
    """
    return f"event: {name}\ndata: {json.dumps(data)}\n\n"


async def _wait_for_change(
    notifier: TurnNotifierPort | None, session_id: str, timeout: float
) -> None:
    """Park for a change signal, or just tick when nothing is wired.

    With ``turn_notifier`` absent from ``app.state`` (a degraded/DSN-less boot,
    or a test that injects nothing) the stream keeps working — it falls back to
    pure timeout ticking, which is exactly the Stage-1 poll cadence.
    """
    if notifier is None:
        await asyncio.sleep(timeout)
        return
    await notifier.wait_for_change(session_id, timeout=timeout)


async def _mirror_events(
    *,
    service: Any,
    student_id: str,
    session_id: str,
    first: Any,
    notifier: TurnNotifierPort | None,
    poll_interval: float,
    heartbeat_interval: float,
) -> AsyncIterator[str]:
    """The frame sequence: one catch-up, then live deltas until the session ends."""
    loop = asyncio.get_running_loop()
    try:
        # Catch-up: everything at index ≥ since, in the Stage-1 envelope. Emitted
        # unconditionally so the client's first frame always carries the current
        # status and cursor, even when it reconnected with nothing new to fetch.
        yield _sse_event(EVENT_TURN_APPENDED, turns_since_payload(first))
        cursor = first.total

        if first.status == "ended":
            # Already over at connect: catch-up, then the terminal frame.
            yield _sse_event(
                EVENT_SESSION_ENDED, {"session_id": first.session_id, "status": "ended"}
            )
            return

        next_heartbeat_at = loop.time() + heartbeat_interval

        while True:
            remaining = next_heartbeat_at - loop.time()
            wait = poll_interval if remaining <= 0 else min(poll_interval, remaining)
            await _wait_for_change(notifier, session_id, wait)

            try:
                result = await service.turns_since(
                    student_id=student_id,
                    session_id=session_id,
                    since=cursor,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # The stream is already 200 with headers flushed, so there is no
                # status code left to correct — close quietly and let the client
                # reconnect (or fall back to the Stage-1 poll).
                logger.warning(
                    "event=turn_stream_read_failed session_id=%s error=%s",
                    session_id,
                    exc,
                )
                return

            emitted = False
            if result.turns:
                yield _sse_event(EVENT_TURN_APPENDED, turns_since_payload(result))
                cursor = result.total
                emitted = True

            if result.status == "ended":
                yield _sse_event(
                    EVENT_SESSION_ENDED,
                    {"session_id": result.session_id, "status": "ended"},
                )
                return

            now = loop.time()
            if emitted:
                next_heartbeat_at = now + heartbeat_interval
            elif now >= next_heartbeat_at:
                yield KEEPALIVE_FRAME
                next_heartbeat_at = now + heartbeat_interval

    except asyncio.CancelledError:
        # The viewer closed the phone / lost the connection. An ordinary end for
        # a read-only stream — debug, never an error log.
        logger.debug("event=turn_stream_disconnected session_id=%s", session_id)
        raise


async def turns_stream(request: Request) -> Response:
    """GET /api/sessions/{session_id}/turns/stream — SSE mirror of the transcript.

    Always mounted, never flag-gated; bearer-authed like the six session verbs.
    Query param ``since`` is the same 0-based ROW offset Stage 1 takes.

    Nothing streams until auth, ownership and ``since`` have all passed: the
    first ``turns_since`` read runs inside the request so its closed-set errors
    still map to the ordinary JSON envelope (401/403/404) with the ordinary
    status code. 410 cannot occur — ended sessions stream too, and simply end
    with ``session_ended``.
    """
    try:
        student_id = await _resolve_student_id(request)
        session_id = request.path_params["session_id"]
        since = parse_since(request.query_params.get("since", "0"))

        service = request.app.state.service
        first = await service.turns_since(
            student_id=student_id,
            session_id=session_id,
            since=since,
        )
    except (SessionNotFoundError, SessionForbidden, Unauthenticated) as e:
        return _map_error_to_response(e)
    except (ValueError, KeyError, TypeError) as e:
        # Malformed since → 400 validation error (no error_type, §4.2)
        logger.warning("Validation error in turns_stream: %s", e)
        return JSONResponse({"error": f"Validation failed: {e}"}, status_code=400)
    except Exception as e:
        return _map_error_to_response(e)

    state = request.app.state
    events = _mirror_events(
        service=service,
        student_id=student_id,
        session_id=session_id,
        first=first,
        notifier=getattr(state, "turn_notifier", None),
        poll_interval=getattr(
            state, "turn_stream_poll_interval", DEFAULT_POLL_INTERVAL_SECONDS
        ),
        heartbeat_interval=getattr(
            state, "turn_stream_heartbeat_interval", DEFAULT_HEARTBEAT_INTERVAL_SECONDS
        ),
    )

    return StreamingResponse(
        events,
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )


__all__ = ["turns_stream"]
