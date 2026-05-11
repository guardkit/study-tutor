"""Unit tests for :class:`study_tutor.adapters.command_router.CommandRouter`.

Regression-guards the two load-bearing fixes baked into TASK-NATS-PH1-004:

- **AC-001 / AC-002 (Bug #2)**: alias resolution via ``tool_to_command`` and
  canonical passthrough hold simultaneously.
- **AC-003 / AC-004 (Bug #1)**: dual-publish to ``reply_to`` *and* the
  canonical ``agents.result.<agent_id>`` subject when the inbox is set;
  canonical-only publish when it is ``None``.

Plus AC-005 (unknown command surfaces failure ``ResultPayload``), AC-006
(handler exceptions caught at the boundary), and a combined test asserting
alias resolution + dual publish hold together.

Test count: 9 (matches the prior-run pytest output ``9 passed in 0.14s``
preserved at ``.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-004/``).
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from nats_core.envelope import EventType, MessageEnvelope
from nats_core.events._agent import CommandPayload, ResultPayload

from study_tutor.adapters.command_router import (
    CommandRouter,
    UnsupportedCommandError,
)

CANONICAL_RESULT_SUBJECT = "agents.result.gcse-tutor"
TUTOR_TOOL_TO_COMMAND: dict[str, str] = {
    "tutor_start_session": "start_session",
    "tutor_turn": "tutor_turn",
    "tutor_session_status": "session_status",
    "tutor_session_end": "end_session",
}


def _make_envelope(command: str, args: dict[str, object]) -> MessageEnvelope:
    """Wrap a ``CommandPayload`` in a ``MessageEnvelope`` for ``on_command``."""
    return MessageEnvelope(
        source_id="jarvis-test",
        event_type=EventType.COMMAND,
        payload=CommandPayload(command=command, args=args).model_dump(),
    )


def _make_router() -> tuple[CommandRouter, MagicMock, MagicMock]:
    """Build a ``CommandRouter`` with mocked adapter and client.

    The adapter exposes the four canonical tutor methods as ``AsyncMock``s
    returning empty dicts by default so ``ResultPayload`` validation passes.
    The client exposes ``publish`` and ``publish_raw`` as ``AsyncMock``s for
    awaited-call assertions.
    """
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
    )
    return router, adapter, client


# ---------------------------------------------------------------------------
# AC-001 — Bug #2 alias resolution regression guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_on_command_alias_resolves_tutor_start_session() -> None:
    """``tutor_start_session`` (MCP tool name) → ``start_session`` (canonical)."""
    router, adapter, _client = _make_router()

    envelope = _make_envelope("tutor_start_session", {"student_id": "lilymay"})
    await router.on_command(envelope)

    adapter.tutor_start_session.assert_awaited_once_with(student_id="lilymay")
    adapter.tutor_turn.assert_not_awaited()
    adapter.tutor_session_status.assert_not_awaited()
    adapter.tutor_session_end.assert_not_awaited()


# ---------------------------------------------------------------------------
# AC-002 — canonical passthrough
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_on_command_canonical_command_passes_through() -> None:
    """Canonical names absent from ``tool_to_command`` fall through unchanged."""
    router, adapter, _client = _make_router()

    envelope = _make_envelope("start_session", {"student_id": "lilymay"})
    await router.on_command(envelope)

    adapter.tutor_start_session.assert_awaited_once_with(student_id="lilymay")


# ---------------------------------------------------------------------------
# AC-003 — Bug #1 dual-publish regression guard
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_result_with_reply_to_publishes_both() -> None:
    """``reply_to`` set → raw-publish to inbox AND canonical envelope publish."""
    router, _adapter, client = _make_router()

    envelope = _make_envelope("start_session", {"student_id": "lilymay"})
    await router.on_command(envelope, reply_to="_INBOX.abc")

    client.publish_raw.assert_awaited_once()
    raw_subject, raw_body = client.publish_raw.await_args.args
    assert raw_subject == "_INBOX.abc"
    # Body is parseable as a ResultPayload directly (raw on the wire,
    # not envelope-wrapped) — the wire format jarvis's dispatch.py expects.
    parsed = ResultPayload.model_validate(json.loads(raw_body))
    assert parsed.success is True
    assert parsed.command == "start_session"

    client.publish.assert_awaited_once()
    pub_subject = client.publish.await_args.args[0]
    assert pub_subject == CANONICAL_RESULT_SUBJECT


# ---------------------------------------------------------------------------
# AC-004 — reply_to=None → canonical-only publish
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_result_without_reply_to_only_canonical() -> None:
    """``reply_to=None`` → ``publish_raw`` skipped; canonical publish runs once."""
    router, _adapter, client = _make_router()

    envelope = _make_envelope("start_session", {"student_id": "lilymay"})
    await router.on_command(envelope, reply_to=None)

    client.publish_raw.assert_not_awaited()
    client.publish.assert_awaited_once()
    pub_subject = client.publish.await_args.args[0]
    assert pub_subject == CANONICAL_RESULT_SUBJECT


# ---------------------------------------------------------------------------
# AC-005 — unknown command surfaces error ResultPayload
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_command_raises_unsupported_command_error() -> None:
    """Inner contract: unknown command → :class:`UnsupportedCommandError`."""
    router, _adapter, _client = _make_router()

    with pytest.raises(UnsupportedCommandError) as exc_info:
        await router._dispatch_command("bogus_command", {})

    assert exc_info.value.command == "bogus_command"
    assert exc_info.value.supported == sorted(
        ["start_session", "tutor_turn", "session_status", "end_session"]
    )


@pytest.mark.asyncio
async def test_on_command_unknown_command_returns_error_result() -> None:
    """Outer contract: unknown command does NOT propagate; surfaces as failure."""
    router, _adapter, client = _make_router()

    envelope = _make_envelope("bogus_command", {})
    await router.on_command(envelope)

    client.publish.assert_awaited_once()
    canonical_payload = client.publish.await_args.kwargs["payload"]
    assert isinstance(canonical_payload, ResultPayload)
    assert canonical_payload.success is False
    error_text = canonical_payload.result["error"]
    assert "bogus_command" in error_text
    for canonical in ("start_session", "tutor_turn", "session_status", "end_session"):
        assert canonical in error_text
    assert canonical_payload.result["error_type"] == "UnsupportedCommandError"


# ---------------------------------------------------------------------------
# AC-006 — handler exception caught at boundary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_on_command_handler_exception_caught() -> None:
    """Adapter raising → ``on_command`` does NOT propagate; failure published."""
    router, adapter, client = _make_router()
    adapter.tutor_start_session.side_effect = RuntimeError("boom")

    envelope = _make_envelope("tutor_start_session", {"student_id": "lilymay"})
    await router.on_command(envelope)  # must not raise

    client.publish.assert_awaited_once()
    canonical_payload = client.publish.await_args.kwargs["payload"]
    assert isinstance(canonical_payload, ResultPayload)
    assert canonical_payload.success is False
    assert "boom" in canonical_payload.result["error"]
    assert canonical_payload.result["error_type"] == "RuntimeError"


# ---------------------------------------------------------------------------
# correlation_id propagation — pins the request/reply contract
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_on_command_propagates_correlation_id_to_result() -> None:
    """``CommandPayload.correlation_id`` must round-trip onto the result."""
    router, _adapter, client = _make_router()

    envelope = MessageEnvelope(
        source_id="jarvis-test",
        event_type=EventType.COMMAND,
        payload=CommandPayload(
            command="start_session",
            args={"student_id": "lilymay"},
            correlation_id="corr-xyz",
        ).model_dump(),
    )
    await router.on_command(envelope, reply_to="_INBOX.corr")

    canonical_payload = client.publish.await_args.kwargs["payload"]
    assert canonical_payload.correlation_id == "corr-xyz"

    raw_body = client.publish_raw.await_args.args[1]
    parsed_raw = ResultPayload.model_validate(json.loads(raw_body))
    assert parsed_raw.correlation_id == "corr-xyz"


# ---------------------------------------------------------------------------
# Combined regression — AC-001 + AC-003 hold together
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_on_command_with_reply_to_dual_publishes_aliased_command() -> None:
    """Alias resolution + dual-publish must hold simultaneously."""
    router, adapter, client = _make_router()

    envelope = _make_envelope("tutor_start_session", {"student_id": "lilymay"})
    await router.on_command(envelope, reply_to="_INBOX.xyz")

    adapter.tutor_start_session.assert_awaited_once_with(student_id="lilymay")
    client.publish_raw.assert_awaited_once()
    raw_subject, _raw_body = client.publish_raw.await_args.args
    assert raw_subject == "_INBOX.xyz"
    client.publish.assert_awaited_once()
    pub_subject = client.publish.await_args.args[0]
    assert pub_subject == CANONICAL_RESULT_SUBJECT
