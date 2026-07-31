"""Stage 2 — ``GET /api/sessions/{id}/turns/stream`` (SSE mirror, binding §2.5).

Hermetic: a fake ``SessionService`` plus the **real** :class:`TurnNotifier` — no
DB, no live model, no broker (the notifier is pure ``asyncio`` by design).

Two harnesses, because an SSE stream is unbounded:

* **TestClient** for everything that terminates — the rejection postures (a
  rejected caller never opens a stream) and the already-ended session, whose
  stream is catch-up + ``session_ended`` + close. That last one is also where
  the byte-identity check against the Stage-1 route lives.
* **:class:`SSEProbe`**, which drives the ASGI app directly, for the live cases —
  it reads frame by frame while the stream is still open and hangs up like a real
  client. (``httpx``'s ASGI transport buffers the whole body, so it cannot see an
  open stream.)
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest
from starlette.testclient import TestClient

from study_tutor.knowledge.store.entities import SessionTurn
from study_tutor.session.errors import SessionForbidden, SessionNotFoundError
from study_tutor.session.notifier import TurnNotifier
from study_tutor.session.service import TurnsSinceResult

SESSION_ID = "sess-mirror-1"
STUDENT_ID = "test-student"
AUTH = {"Authorization": "Bearer token-test"}
STREAM_PATH = f"/api/sessions/{SESSION_ID}/turns/stream"
# Microsecond-bearing + tz-aware, exactly as in the Stage-1 route test: the ts
# projection must round-trip identically on both surfaces.
T0 = datetime(2026, 7, 31, 10, 15, 0, 123456, tzinfo=timezone.utc)

# A poll interval long enough that a frame arriving promptly can ONLY have come
# from the notifier, never from a timeout tick.
NEVER = 30.0


# -------------------- Fakes --------------------


def _row(index: int) -> SessionTurn:
    return SessionTurn(
        session_id=SESSION_ID,
        turn_index=index,
        role="user" if index % 2 == 0 else "tutor",
        content=f"row-{index}",
        ts=T0 + timedelta(seconds=index),
    )


class FakeMirrorService:
    """The read side of ``SessionService`` as the stream sees it."""

    def __init__(
        self,
        *,
        rows: int = 0,
        status: str = "active",
        error: Exception | None = None,
    ) -> None:
        self.rows: list[SessionTurn] = [_row(i) for i in range(rows)]
        self.status = status
        self.error = error
        self.since_calls: list[int] = []

    async def turns_since(
        self, *, student_id: str, session_id: str, since: int
    ) -> TurnsSinceResult:
        self.since_calls.append(since)
        if self.error is not None:
            raise self.error
        return TurnsSinceResult(
            session_id=session_id,
            student_id=student_id,
            status=self.status,  # type: ignore[arg-type]
            turns=tuple(self.rows[since:]),
            total=len(self.rows),
        )

    def append(self, notifier: TurnNotifier | None = None) -> None:
        """Persist one more row — the write the robot's turn makes."""
        self.rows.append(_row(len(self.rows)))
        if notifier is not None:
            notifier.notify(SESSION_ID)

    def end(self, notifier: TurnNotifier | None = None) -> None:
        self.status = "ended"
        if notifier is not None:
            notifier.notify(SESSION_ID)


def _build_app(
    service: Any,
    *,
    turn_notifier: TurnNotifier | None = None,
    poll_interval: float | None = None,
    heartbeat_interval: float | None = None,
):
    """An app with NO voice config and NO dev flags — the stream route must still
    be mounted (it is deliberately not behind the voice flag that gates /ws)."""
    from study_tutor.http.app import create_app
    from study_tutor.http.auth import HTTPAuthConfig, TableTokenResolver

    token_to_student = {"token-test": STUDENT_ID}
    auth_config = HTTPAuthConfig(
        token_to_student=token_to_student,
        dev_reset=False,
        resolver=TableTokenResolver(token_to_student=token_to_student),
    )
    student_store = AsyncMock()
    student_store.student_exists.return_value = True

    app = create_app(
        service=service,
        reply_fn=AsyncMock(),
        auth_config=auth_config,
        student_store=student_store,
        turn_notifier=turn_notifier,
    )
    if poll_interval is not None:
        app.state.turn_stream_poll_interval = poll_interval
    if heartbeat_interval is not None:
        app.state.turn_stream_heartbeat_interval = heartbeat_interval
    return app


# -------------------- SSE probe (drives ASGI directly) --------------------


class SSEProbe:
    """Opens the route over raw ASGI and reads frames while the stream is live."""

    def __init__(self, app: Any, path: str, *, headers: dict[str, str] | None = None):
        self._app = app
        raw_path, _, query = path.partition("?")
        self._scope = {
            "type": "http",
            "asgi": {"version": "3.0", "spec_version": "2.3"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": raw_path,
            "raw_path": raw_path.encode(),
            "query_string": query.encode(),
            "root_path": "",
            "headers": [
                (k.lower().encode(), v.encode())
                for k, v in (headers or {}).items()
            ],
            "client": ("127.0.0.1", 50000),
            "server": ("testserver", 80),
        }
        self.status: int | None = None
        self.headers_out: dict[str, str] = {}
        self.frames: asyncio.Queue[str] = asyncio.Queue()
        self.closed = asyncio.Event()
        self._started = asyncio.Event()
        self._request_sent = False
        self._disconnect = asyncio.Event()
        self._task: asyncio.Task[None] | None = None

    async def _receive(self) -> dict[str, Any]:
        if not self._request_sent:
            self._request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        await self._disconnect.wait()
        return {"type": "http.disconnect"}

    async def _send(self, message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            self.status = message["status"]
            self.headers_out = {
                k.decode().lower(): v.decode() for k, v in message["headers"]
            }
            self._started.set()
        elif message["type"] == "http.response.body":
            body = message.get("body", b"")
            if body:
                await self.frames.put(body.decode())
            if not message.get("more_body", False):
                self.closed.set()

    async def __aenter__(self) -> "SSEProbe":
        self._task = asyncio.create_task(
            self._app(self._scope, self._receive, self._send)
        )
        await asyncio.wait_for(self._started.wait(), timeout=2.0)
        return self

    async def __aexit__(self, *_exc: Any) -> None:
        self._disconnect.set()
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)

    async def next_frame(self, timeout: float = 2.0) -> str:
        return await asyncio.wait_for(self.frames.get(), timeout=timeout)

    async def next_event(self, timeout: float = 2.0) -> tuple[str, dict[str, Any]]:
        """Next non-keepalive frame, parsed into (event name, data)."""
        while True:
            frame = await self.next_frame(timeout=timeout)
            if frame.startswith(":"):
                continue
            return _parse_event(frame)


def _parse_event(frame: str) -> tuple[str, dict[str, Any]]:
    assert frame.endswith("\n\n"), f"frame not terminated by a blank line: {frame!r}"
    lines = frame.strip("\n").split("\n")
    assert len(lines) == 2, f"expected exactly event+data lines, got {lines!r}"
    assert lines[0].startswith("event: ")
    assert lines[1].startswith("data: ")
    return lines[0][len("event: ") :], json.loads(lines[1][len("data: ") :])


def _events(body: str) -> list[tuple[str, dict[str, Any]]]:
    """Parse a whole terminated stream body into its non-keepalive events."""
    return [
        _parse_event(chunk + "\n\n")
        for chunk in body.split("\n\n")
        if chunk and not chunk.startswith(":")
    ]


# -------------------- Terminating streams (TestClient) --------------------


def test_catch_up_event_carries_the_stage_1_envelope_verbatim() -> None:
    """The pushed delta parses with the app's existing Stage-1 parser."""
    service = FakeMirrorService(rows=2, status="ended")
    client = TestClient(_build_app(service))

    stream_body = client.get(STREAM_PATH, headers=AUTH).text
    polled = client.get(f"/api/sessions/{SESSION_ID}/turns?since=0", headers=AUTH)

    name, data = _events(stream_body)[0]
    assert name == "turn_appended"
    assert data == polled.json()
    assert set(data) == {"session_id", "status", "turns", "next"}
    assert [row["content"] for row in data["turns"]] == ["row-0", "row-1"]
    assert data["next"] == 2
    for row in data["turns"]:
        assert set(row) == {"role", "content", "ts"}


def test_ended_at_connect_is_catch_up_then_session_ended_then_close() -> None:
    service = FakeMirrorService(rows=2, status="ended")
    client = TestClient(_build_app(service))

    response = client.get(STREAM_PATH, headers=AUTH)

    assert response.status_code == 200
    events = _events(response.text)
    assert [name for name, _ in events] == ["turn_appended", "session_ended"]
    assert events[-1][1] == {"session_id": SESSION_ID, "status": "ended"}


def test_stream_headers_are_event_stream_and_no_cache() -> None:
    service = FakeMirrorService(rows=1, status="ended")
    client = TestClient(_build_app(service))

    response = client.get(STREAM_PATH, headers=AUTH)

    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers["cache-control"] == "no-cache"


def test_since_mid_transcript_catches_up_only_the_tail() -> None:
    service = FakeMirrorService(rows=6, status="ended")
    client = TestClient(_build_app(service))

    response = client.get(f"{STREAM_PATH}?since=4", headers=AUTH)

    _, data = _events(response.text)[0]
    assert [row["content"] for row in data["turns"]] == ["row-4", "row-5"]
    assert data["next"] == 6
    assert service.since_calls[0] == 4


def test_since_at_the_end_catches_up_an_empty_delta() -> None:
    """A reconnect with nothing new still gets its status + cursor, never a 410."""
    service = FakeMirrorService(rows=4, status="ended")
    client = TestClient(_build_app(service))

    response = client.get(f"{STREAM_PATH}?since=4", headers=AUTH)

    assert response.status_code == 200
    name, data = _events(response.text)[0]
    assert name == "turn_appended"
    assert data["turns"] == []
    assert data["next"] == 4
    assert data["status"] == "ended"


def test_route_is_mounted_with_voice_disabled() -> None:
    """The app under test has no voice config — /ws would be absent, this must not
    be (the mirror is a read-only viewer with no voice dependency)."""
    service = FakeMirrorService(rows=0, status="ended")
    client = TestClient(_build_app(service))

    response = client.get(STREAM_PATH, headers=AUTH)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")


# -------------------- Rejections: never start the stream --------------------


def test_missing_token_is_401_json_not_a_stream() -> None:
    service = FakeMirrorService(rows=2)
    client = TestClient(_build_app(service))

    response = client.get(STREAM_PATH)

    assert response.status_code == 401
    assert response.json()["error_type"] == "Unauthenticated"
    assert not response.headers["content-type"].startswith("text/event-stream")
    assert service.since_calls == []


def test_non_owner_is_403_json_with_no_stream() -> None:
    service = FakeMirrorService(rows=2, error=SessionForbidden("not yours"))
    client = TestClient(_build_app(service))

    response = client.get(STREAM_PATH, headers=AUTH)

    assert response.status_code == 403
    assert response.json()["error_type"] == "SessionForbidden"
    assert not response.headers["content-type"].startswith("text/event-stream")


def test_unknown_session_is_404_json() -> None:
    service = FakeMirrorService(error=SessionNotFoundError(SESSION_ID))
    client = TestClient(_build_app(service))

    response = client.get(STREAM_PATH, headers=AUTH)

    assert response.status_code == 404
    assert response.json()["error_type"] == "SessionNotFoundError"


@pytest.mark.parametrize("bad", ["abc", "-1", "1.5", ""])
def test_bad_since_is_400_without_error_type_and_never_reads(bad: str) -> None:
    service = FakeMirrorService(rows=2)
    client = TestClient(_build_app(service))

    response = client.get(f"{STREAM_PATH}?since={bad}", headers=AUTH)

    assert response.status_code == 400
    data = response.json()
    assert data["error"].startswith("Validation failed: ")
    assert "error_type" not in data
    assert service.since_calls == []


# -------------------- Live streams (raw-ASGI probe) --------------------


async def test_a_turn_appended_while_connected_is_pushed() -> None:
    """The notifier — not a poll tick — is what delivers this frame."""
    notifier = TurnNotifier()
    service = FakeMirrorService(rows=2)
    app = _build_app(
        service,
        turn_notifier=notifier,
        poll_interval=NEVER,
        heartbeat_interval=NEVER,
    )

    async with SSEProbe(app, STREAM_PATH, headers=AUTH) as probe:
        assert probe.status == 200
        name, catch_up = await probe.next_event()
        assert name == "turn_appended"
        assert catch_up["next"] == 2

        async def robot_writes_a_turn() -> None:
            await asyncio.sleep(0.01)
            service.append(notifier)

        asyncio.create_task(robot_writes_a_turn())

        name, data = await probe.next_event()

    assert name == "turn_appended"
    # Delta only — the already-delivered rows are not re-sent.
    assert [row["content"] for row in data["turns"]] == ["row-2"]
    assert data["next"] == 3
    assert data["status"] == "active"


async def test_end_while_connected_pushes_session_ended_and_closes() -> None:
    notifier = TurnNotifier()
    service = FakeMirrorService(rows=2)
    app = _build_app(
        service,
        turn_notifier=notifier,
        poll_interval=NEVER,
        heartbeat_interval=NEVER,
    )

    async with SSEProbe(app, STREAM_PATH, headers=AUTH) as probe:
        await probe.next_event()  # catch-up

        async def robot_ends_the_session() -> None:
            await asyncio.sleep(0.01)
            service.append()  # a final row, then the end — one signal for both
            service.end(notifier)

        asyncio.create_task(robot_ends_the_session())

        name, data = await probe.next_event()
        assert name == "turn_appended"
        assert [row["content"] for row in data["turns"]] == ["row-2"]

        name, data = await probe.next_event()
        assert name == "session_ended"
        assert data == {"session_id": SESSION_ID, "status": "ended"}

        await asyncio.wait_for(probe.closed.wait(), timeout=2.0)


async def test_an_idle_stream_carries_nothing_but_keepalives() -> None:
    notifier = TurnNotifier()
    service = FakeMirrorService(rows=2)
    app = _build_app(
        service,
        turn_notifier=notifier,
        poll_interval=0.01,
        heartbeat_interval=0.01,
    )

    async with SSEProbe(app, STREAM_PATH, headers=AUTH) as probe:
        name, _ = _parse_event(await probe.next_frame())
        assert name == "turn_appended"

        idle = [await probe.next_frame() for _ in range(4)]

    assert idle == [": keepalive\n\n"] * 4


async def test_without_a_notifier_the_timeout_tick_still_surfaces_new_rows() -> None:
    """The degrade path: no notifier wired (DSN-less boot), and a cross-process
    write still lands within ~one poll interval."""
    service = FakeMirrorService(rows=1)
    app = _build_app(
        service,
        turn_notifier=None,
        poll_interval=0.01,
        heartbeat_interval=NEVER,
    )

    async with SSEProbe(app, STREAM_PATH, headers=AUTH) as probe:
        await probe.next_event()  # catch-up
        service.append()  # nobody signals — only the tick can find this

        name, data = await probe.next_event()

    assert name == "turn_appended"
    assert [row["content"] for row in data["turns"]] == ["row-1"]


async def test_client_disconnect_ends_the_stream_without_error() -> None:
    notifier = TurnNotifier()
    service = FakeMirrorService(rows=1)
    app = _build_app(
        service,
        turn_notifier=notifier,
        poll_interval=0.01,
        heartbeat_interval=NEVER,
    )

    probe = SSEProbe(app, STREAM_PATH, headers=AUTH)
    await probe.__aenter__()
    await probe.next_event()
    await probe.__aexit__()

    # The waiter unregistered itself on the way out — no per-session state leaks
    # behind a phone that walked away.
    await asyncio.sleep(0.05)
    assert notifier._signals == {}
