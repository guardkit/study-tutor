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
        subject="English Literature", topic="Macbeth"
    )
    assert "session_id" in result
    assert len(result["session_id"]) == 36  # UUID4
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

    started = await adapter.tutor_start_session(subject="English")
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
    started = await adapter.tutor_start_session(subject="English")
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
