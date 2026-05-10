"""Tests for TASK-NATS-PH2-001 readiness gating in :class:`CommandRouter`.

Acceptance criteria:

- ``on_command`` invoked while ``adapter_ready.is_set() is False`` returns
  ``ResultPayload(success=False, error_type="AdapterNotReady")`` and does NOT
  invoke the underlying handler.
- Same call once ``adapter_ready.is_set() is True`` proceeds normally and the
  handler is awaited exactly once.
- Bug #1 reply path is honoured even in the not-ready case (the requester's
  inbox still gets a clean reply, not a hung future).
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from nats_core.envelope import EventType, MessageEnvelope
from nats_core.events._agent import CommandPayload, ResultPayload

from study_tutor.adapters.command_router import CommandRouter

CANONICAL_RESULT_SUBJECT = "agents.result.gcse-tutor"
TUTOR_TOOL_TO_COMMAND: dict[str, str] = {
    "tutor_start_session": "start_session",
    "tutor_turn": "tutor_turn",
    "tutor_session_status": "session_status",
    "tutor_session_end": "end_session",
}


def _make_envelope(command: str, args: dict[str, object]) -> MessageEnvelope:
    return MessageEnvelope(
        source_id="jarvis-test",
        event_type=EventType.COMMAND,
        payload=CommandPayload(command=command, args=args).model_dump(),
    )


def _make_router_with_ready(
    ready_event: asyncio.Event | None,
) -> tuple[CommandRouter, MagicMock, MagicMock]:
    adapter = MagicMock()
    adapter.tutor_start_session = AsyncMock(return_value={"session_id": "s-1"})
    adapter.tutor_turn = AsyncMock(return_value={"reply": "ok"})
    adapter.tutor_session_status = AsyncMock(return_value={"status": "active"})
    adapter.tutor_session_end = AsyncMock(return_value={"status": "ended"})

    client = MagicMock()
    client.publish = AsyncMock()
    client.publish_raw = AsyncMock()

    router = CommandRouter(
        mcp_adapter=adapter,
        tool_to_command=TUTOR_TOOL_TO_COMMAND,
        agent_id="gcse-tutor",
        client=client,
        adapter_ready=ready_event,
    )
    return router, adapter, client


@pytest.mark.asyncio
async def test_on_command_returns_not_ready_error_when_event_unset() -> None:
    """Adapter not ready → ResultPayload error_type=AdapterNotReady, handler not called."""
    not_ready = asyncio.Event()
    router, adapter, client = _make_router_with_ready(not_ready)

    await router.on_command(_make_envelope("tutor_start_session", {"student_id": "x"}))

    adapter.tutor_start_session.assert_not_awaited()
    client.publish.assert_awaited_once()
    payload = client.publish.await_args.kwargs["payload"]
    assert payload.success is False
    assert payload.result["error_type"] == "AdapterNotReady"
    assert "starting up" in payload.result["error"]


@pytest.mark.asyncio
async def test_on_command_proceeds_normally_once_ready_event_is_set() -> None:
    ready = asyncio.Event()
    ready.set()
    router, adapter, _client = _make_router_with_ready(ready)

    await router.on_command(
        _make_envelope("tutor_start_session", {"student_id": "lilymay"})
    )

    adapter.tutor_start_session.assert_awaited_once_with(student_id="lilymay")


@pytest.mark.asyncio
async def test_not_ready_path_honours_reply_to_for_bug1() -> None:
    """Bug #1 dual-publish must hold even on the not-ready short-circuit so the
    requester's ``client.request()`` inbox future resolves cleanly."""
    not_ready = asyncio.Event()
    router, adapter, client = _make_router_with_ready(not_ready)

    await router.on_command(
        _make_envelope("tutor_start_session", {"student_id": "x"}),
        reply_to="_INBOX.abc",
    )

    adapter.tutor_start_session.assert_not_awaited()
    client.publish_raw.assert_awaited_once()
    raw_subject, raw_bytes = client.publish_raw.await_args.args[:2]
    assert raw_subject == "_INBOX.abc"
    raw_payload = ResultPayload.model_validate(json.loads(raw_bytes.decode()))
    assert raw_payload.success is False
    assert raw_payload.result["error_type"] == "AdapterNotReady"
    client.publish.assert_awaited_once()
    canonical_subject = client.publish.await_args.args[0]
    assert canonical_subject == CANONICAL_RESULT_SUBJECT


@pytest.mark.asyncio
async def test_no_adapter_ready_passes_through_unchanged() -> None:
    """Backwards compat: ``adapter_ready=None`` (default) skips the gate."""
    router, adapter, _client = _make_router_with_ready(None)

    await router.on_command(
        _make_envelope("tutor_start_session", {"student_id": "lilymay"})
    )

    adapter.tutor_start_session.assert_awaited_once_with(student_id="lilymay")
