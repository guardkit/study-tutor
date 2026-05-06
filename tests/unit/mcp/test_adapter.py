"""Smoke tests for MCPAdapter handler shape (TASK-PO02-005).

Deeper stdio-discipline and SR-01/SR-02 parity tests live in
TASK-PO02-006's ``tests/unit/mcp/test_stdio_discipline.py``.
"""
from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from study_tutor.mcp.adapter import MCPAdapter
from study_tutor.mcp.server import create_mcp_server
from study_tutor.roles.loader import RoleConfig
from study_tutor.session.tutor_session import SessionStore


@pytest.fixture
def role_config(tmp_path: Path) -> RoleConfig:
    prompt_path = tmp_path / "player.md"
    prompt_path.write_text("You are a tutor.")
    return RoleConfig(
        id="tutor",
        name="Tutor Agent",
        description="test",
        player_prompt_path=prompt_path,
        criteria_path=None,
    )


@pytest.fixture
def adapter(role_config: RoleConfig) -> MCPAdapter:
    return MCPAdapter(role_config=role_config, store=SessionStore())


async def _drain_warmups(adapter: MCPAdapter) -> None:
    tasks = list(adapter._warmup_tasks)
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


async def test_start_session_returns_session_id(adapter: MCPAdapter) -> None:
    result = await adapter.tutor_start_session(
        student_id="lilymay", topic_override="Macbeth"
    )
    assert "session_id" in result
    # Phase 0 minted via ``str(uuid.uuid4())`` (36 chars including hyphens).
    # TASK-DSP-006 keeps that format because the existing SessionStore
    # owns id minting; the constraint that matters is "minted before the
    # planner runs" (AC-002), not the textual format.
    assert len(result["session_id"]) == 36
    # TASK-DSP-006 — response gains a plan_summary alongside session_id.
    assert "plan_summary" in result
    await _drain_warmups(adapter)


async def test_turn_rejects_unknown_session(adapter: MCPAdapter) -> None:
    result = await adapter.tutor_turn(session_id="nope", user_message="hi")
    assert result["error_type"] == "SessionNotFoundError"


async def test_turn_generates_response(
    adapter: MCPAdapter, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Stub the LLM so the test doesn't hit Ollama.
    from study_tutor.llm import client as llm_client

    def fake_generate(self, prompt, system=None):  # type: ignore[no-untyped-def]
        assert system == "You are a tutor."
        return f"tutor-reply:{prompt}"

    monkeypatch.setattr(llm_client.LLMClient, "generate", fake_generate)

    started = await adapter.tutor_start_session(student_id="lilymay")
    session_id = started["session_id"]
    await _drain_warmups(adapter)

    result = await adapter.tutor_turn(
        session_id=session_id, user_message="Tell me about Act 1"
    )
    assert result == {"tutor_response": "tutor-reply:Tell me about Act 1"}

    status = await adapter.tutor_session_status(session_id=session_id)
    assert status["turn_count"] == 2
    assert status["status"] == "active"


async def test_session_end_flips_status(adapter: MCPAdapter) -> None:
    started = await adapter.tutor_start_session(student_id="lilymay")
    session_id = started["session_id"]
    await _drain_warmups(adapter)

    end_result = await adapter.tutor_session_end(session_id=session_id)
    assert end_result == {"session_id": session_id, "status": "ended"}

    status = await adapter.tutor_session_status(session_id=session_id)
    assert status["status"] == "ended"


async def test_session_end_unknown_returns_error(adapter: MCPAdapter) -> None:
    result = await adapter.tutor_session_end(session_id="nope")
    assert result["error_type"] == "SessionNotFoundError"


async def test_server_registers_four_tools(
    role_config: RoleConfig, adapter: MCPAdapter
) -> None:
    server = create_mcp_server(role_config, adapter)
    tools = await server.list_tools()
    names = {t.name for t in tools}
    assert names == {
        "tutor_start_session",
        "tutor_turn",
        "tutor_session_status",
        "tutor_session_end",
    }

    end_tool = next(t for t in tools if t.name == "tutor_session_end")
    # SR-07: description MUST NOT leak Phase 1 Graphiti behaviour.
    assert "graphiti" not in end_tool.description.lower()
    assert "async" not in end_tool.description.lower()
    assert "marks session ended" in end_tool.description.lower()


# ---------------------------------------------------------------------------
# TASK-GR-WIRE BLOCK-3a — perform_session_end delegation
# ---------------------------------------------------------------------------


async def test_session_end_delegates_to_perform_session_end(
    role_config: RoleConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``tutor_session_end`` must delegate to ``perform_session_end``.

    AC-WIRE-06 contract check: the adapter must (1) resolve the session,
    (2) extract topics_covered/aos_exercised from the cached SessionPlan,
    (3) thread a transition_state closure that calls store.end, and
    (4) return perform_session_end's value verbatim. We patch
    ``perform_session_end`` at the adapter's import site so the assertion
    surface is the keyword-argument shape, not the underlying
    bus/write-helper plumbing (that is tested in
    ``tests/unit/tutoring/test_session_end.py``).
    """
    from study_tutor.knowledge.async_write import GraphitiWriteHelper
    from study_tutor.mcp import adapter as adapter_mod
    from study_tutor.tutoring.session_end import EventBus

    captured: dict[str, object] = {}
    sentinel_return = {"session_id": "sentinel", "status": "ended"}

    async def fake_perform_session_end(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        # Honour the contract: transition_state is the closure that flips
        # store state. Calling it here mirrors the real path so the
        # subsequent status check returns "ended".
        ts = kwargs.get("transition_state")
        assert callable(ts)
        ts()  # type: ignore[operator]
        return sentinel_return

    monkeypatch.setattr(
        adapter_mod, "perform_session_end", fake_perform_session_end
    )

    write_helper = GraphitiWriteHelper(client=None)
    event_bus = EventBus()
    store = SessionStore()
    adapter = MCPAdapter(
        role_config=role_config,
        store=store,
        write_helper=write_helper,
        event_bus=event_bus,
    )

    # Start a session so ``_plan_sessions`` has an entry — drives the
    # topics_covered / aos_exercised extraction branch.
    started = await adapter.tutor_start_session(
        student_id="lilymay", topic_override="Macbeth"
    )
    session_id = started["session_id"]
    await _drain_warmups(adapter)

    # Append a turn so the session has non-zero turns (the I-T6 guard
    # branch is exercised separately by perform_session_end's own tests).
    store.append_turn(session_id, "user", "hi")

    result = await adapter.tutor_session_end(session_id=session_id)

    # Verbatim return.
    assert result is sentinel_return

    # Delegation kwargs match the contract: perform_session_end takes
    # ``session=...`` (the TutorSession object), not a bare session_id.
    assert "session_id" not in captured
    session_arg = captured["session"]
    assert getattr(session_arg, "session_id") == session_id
    assert captured["student_id"] == "lilymay"
    assert captured["write_helper"] is write_helper
    assert captured["event_bus"] is event_bus
    # topics_covered comes from the planner's plan; deterministic planner
    # may degrade to a baseline plan whose topic_name is the override or
    # a fallback string. We only assert the *shape* — list of one string —
    # because the planner internals are not this test's surface.
    topics = captured["topics_covered"]
    assert isinstance(topics, list) and len(topics) == 1
    assert isinstance(topics[0], str)
    aos = captured["aos_exercised"]
    assert isinstance(aos, list)
    # transition_state must be a callable; fake_perform_session_end
    # already invoked it, so the store should now report status=ended.
    assert callable(captured["transition_state"])
    assert store.get(session_id).status == "ended"


async def test_session_end_unknown_session_short_circuits_before_delegation(
    role_config: RoleConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unknown session_id must NOT reach perform_session_end.

    Defence-in-depth: the SessionNotFoundError path returns
    ``_session_not_found(...)`` directly so we never construct a
    transition_state closure or compute topics for a session that
    doesn't exist.
    """
    from study_tutor.mcp import adapter as adapter_mod

    called = False

    async def fake_perform_session_end(**kwargs: object) -> dict[str, object]:
        nonlocal called
        called = True
        return {"session_id": "x", "status": "ended"}

    monkeypatch.setattr(
        adapter_mod, "perform_session_end", fake_perform_session_end
    )

    adapter = MCPAdapter(role_config=role_config, store=SessionStore())
    result = await adapter.tutor_session_end(session_id="nope")

    assert result["error_type"] == "SessionNotFoundError"
    assert called is False


async def test_session_end_missing_plan_uses_empty_topics_and_aos(
    role_config: RoleConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stale-lookup branch: cold ``_plan_sessions`` cache → empty defaults.

    When ``tutor_session_end`` is called for a session_id that exists in
    the SessionStore but was never minted via this adapter instance's
    ``tutor_start_session`` (e.g. server restart between endpoints), the
    plan cache is cold and topics_covered / aos_exercised default to
    empty lists rather than raising. perform_session_end /
    build_session_completed_episode handles the empty case by falling
    back to ``[session.topic]``.
    """
    from study_tutor.mcp import adapter as adapter_mod

    captured: dict[str, object] = {}

    async def fake_perform_session_end(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"session_id": "x", "status": "ended"}

    monkeypatch.setattr(
        adapter_mod, "perform_session_end", fake_perform_session_end
    )

    store = SessionStore()
    adapter = MCPAdapter(role_config=role_config, store=store)

    # Bypass tutor_start_session — go straight to the store, simulating
    # a session minted by a prior process.
    session = store.create(subject="lilymay", topic="Romeo and Juliet")
    store.append_turn(session.session_id, "user", "hi")

    await adapter.tutor_session_end(session_id=session.session_id)

    assert captured["topics_covered"] == []
    assert captured["aos_exercised"] == []
