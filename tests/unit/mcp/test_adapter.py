"""Smoke tests for MCPAdapter handler shape (TASK-PO02-005).

Deeper stdio-discipline and SR-01/SR-02 parity tests live in
TASK-PO02-006's ``tests/unit/mcp/test_stdio_discipline.py``.
"""
from __future__ import annotations

import asyncio
from datetime import datetime
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


# ---------------------------------------------------------------------------
# TASK-GR-CONF BLOCK-3b — record_topic_confidence_update wiring (AC-CONF-08)
# ---------------------------------------------------------------------------


async def test_session_end_dispatches_topic_confidence_update(
    role_config: RoleConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-CONF-08: after ``perform_session_end`` returns,
    ``tutor_session_end`` schedules :func:`record_topic_confidence_update`
    as a fire-and-forget task with the cached plan's ``topic_name`` and
    a session_summary derived from the live :class:`TutorSession`.

    The helper itself is patched at the adapter's import site so this
    test surfaces the kwarg-shape contract — not the internal
    typed-entity load+save plumbing (those have unit coverage in
    ``tests/unit/knowledge/test_queries.py``).
    """
    from study_tutor.knowledge.async_write import GraphitiWriteHelper
    from study_tutor.mcp import adapter as adapter_mod
    from study_tutor.tutoring.session_end import EventBus

    # Stub perform_session_end so we don't run the real session-end path.
    async def fake_perform_session_end(**kwargs: object) -> dict[str, object]:
        ts = kwargs.get("transition_state")
        assert callable(ts)
        ts()  # type: ignore[operator]
        return {"session_id": "x", "status": "ended"}

    monkeypatch.setattr(
        adapter_mod, "perform_session_end", fake_perform_session_end
    )

    captured: dict[str, object] = {}
    record_called = asyncio.Event()

    async def fake_record_topic_confidence_update(**kwargs: object) -> None:
        captured.update(kwargs)
        record_called.set()

    monkeypatch.setattr(
        adapter_mod,
        "record_topic_confidence_update",
        fake_record_topic_confidence_update,
    )

    write_helper = GraphitiWriteHelper(client=None)
    event_bus = EventBus()
    store = SessionStore()
    sentinel_client = object()  # any non-None graphiti_client triggers dispatch
    adapter = MCPAdapter(
        role_config=role_config,
        store=store,
        write_helper=write_helper,
        event_bus=event_bus,
        graphiti_client=sentinel_client,
    )

    started = await adapter.tutor_start_session(
        student_id="lilymay", topic_override="Macbeth"
    )
    session_id = started["session_id"]
    await _drain_warmups(adapter)

    # Two user turns + one tutor turn → student_turn_count must be 2.
    store.append_turn(session_id, "user", "hi")
    store.append_turn(session_id, "tutor", "hello")
    store.append_turn(session_id, "user", "tell me about ambition")

    await adapter.tutor_session_end(session_id=session_id)

    # Wait briefly for the fire-and-forget task to run.
    await asyncio.wait_for(record_called.wait(), timeout=1.0)

    # Wired through correctly.
    assert captured["client"] is sentinel_client
    assert captured["write_helper"] is write_helper
    assert captured["student_id"] == "lilymay"
    # The planner-resolved topic; topic_override="Macbeth" goes through
    # rule 1 short-circuit, so plan.topic_name should be "Macbeth".
    assert captured["topic_ref"] == "Macbeth"

    summary = captured["session_summary"]
    assert isinstance(summary, dict)
    assert summary["student_turn_count"] == 2
    assert summary["misconceptions_per_topic"] == {}
    assert summary["triggering_session_id"] == session_id
    assert isinstance(summary["ended_at"], datetime)

    # Phase-1 stub policy is supplied by the adapter.
    policy = captured["policy"]
    assert getattr(policy, "name", None) == "phase1_minimal_policy"


async def test_session_end_skips_topic_confidence_when_no_graphiti_client(
    role_config: RoleConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When ``graphiti_client`` is None the adapter must NOT schedule the
    confidence update task — graceful degradation for Phase 0 / test
    paths where Graphiti isn't wired."""
    from study_tutor.mcp import adapter as adapter_mod

    async def fake_perform_session_end(**kwargs: object) -> dict[str, object]:
        ts = kwargs.get("transition_state")
        assert callable(ts)
        ts()  # type: ignore[operator]
        return {"session_id": "x", "status": "ended"}

    monkeypatch.setattr(
        adapter_mod, "perform_session_end", fake_perform_session_end
    )

    record_called = False

    async def fake_record_topic_confidence_update(**kwargs: object) -> None:
        nonlocal record_called
        record_called = True

    monkeypatch.setattr(
        adapter_mod,
        "record_topic_confidence_update",
        fake_record_topic_confidence_update,
    )

    store = SessionStore()
    adapter = MCPAdapter(
        role_config=role_config,
        store=store,
        graphiti_client=None,  # explicit
    )

    started = await adapter.tutor_start_session(student_id="lilymay")
    session_id = started["session_id"]
    await _drain_warmups(adapter)
    store.append_turn(session_id, "user", "hi")

    await adapter.tutor_session_end(session_id=session_id)
    # Yield once so any erroneously-scheduled task could fire.
    await asyncio.sleep(0)
    assert record_called is False


# ---------------------------------------------------------------------------
# TASK-LCA-004 — boot-time smoke check (AC-LCA-02 / AC-LCA-08)
# ---------------------------------------------------------------------------


@pytest.mark.feat_lca
class TestMCPAdapterBootSmokeCheck:
    """Verify ``MCPAdapter.__init__`` invokes the orchestrator factory once
    at boot when one is supplied, propagates any structural-invariant
    exception verbatim (so server boot fails fast), and is a no-op for the
    Phase-0 backward-compatible ``orchestrator_factory=None`` path.
    """

    def test_factory_invoked_once_at_init_when_supplied(
        self, role_config: RoleConfig
    ) -> None:
        """AC-LCA-02 boot path: the factory is invoked exactly once and the
        result is discarded.

        Adapter construction must not retain the factory's return value;
        the smoke check exists solely to surface configuration errors at
        boot. A subsequent ``tutor_turn`` will call the factory again —
        per-turn isolation invariant — so caching here would silently
        share orchestrator state across turns.
        """
        invocations: list[int] = []

        def factory() -> object:
            invocations.append(1)
            return object()

        adapter = MCPAdapter(
            role_config=role_config,
            store=SessionStore(),
            orchestrator_factory=factory,
        )

        assert len(invocations) == 1
        # Factory return value is NOT stored on the adapter — only the
        # callable itself.
        assert adapter._orchestrator_factory is factory

    def test_factory_exception_propagates_from_init(
        self, role_config: RoleConfig
    ) -> None:
        """AC-LCA-02: when the factory raises ``CoachConfigurationError``
        the exception escapes ``__init__`` so the MCP server boot fails
        before serving begins. We use the real exception class so the
        propagation surface includes any subclass-aware ``except``
        handlers a future caller might write.
        """
        from study_tutor.tutoring.coach.factory import CoachConfigurationError

        def factory() -> object:
            raise CoachConfigurationError(
                "test: same provider rejected (D3 invariant)"
            )

        with pytest.raises(CoachConfigurationError, match="D3 invariant"):
            MCPAdapter(
                role_config=role_config,
                store=SessionStore(),
                orchestrator_factory=factory,
            )

    def test_factory_llm_provider_error_propagates_from_init(
        self, role_config: RoleConfig
    ) -> None:
        """AC-LCA-02: an ``LLMProviderError`` raised during factory
        invocation (e.g. unset ``AGENT_MODELS__COACH_MODEL`` surfaced via
        :func:`_default_coach_model`) must also propagate from
        ``__init__`` rather than being swallowed.
        """
        from study_tutor.llm.client import LLMProviderError

        def factory() -> object:
            raise LLMProviderError(
                "AGENT_MODELS__COACH_MODEL is not set."
            )

        with pytest.raises(LLMProviderError, match="AGENT_MODELS__COACH_MODEL"):
            MCPAdapter(
                role_config=role_config,
                store=SessionStore(),
                orchestrator_factory=factory,
            )

    def test_no_smoke_check_when_factory_is_none(
        self, role_config: RoleConfig
    ) -> None:
        """Phase-0 backward compatibility: ``orchestrator_factory=None``
        path must construct cleanly with no factory invocation, no
        exception, and no observable change to the existing constructor
        contract. The Phase-0 fixture-based tests in this file rely on
        that.
        """
        adapter = MCPAdapter(role_config=role_config, store=SessionStore())
        # Constructor completes cleanly and the factory slot is None.
        assert adapter._orchestrator_factory is None

    def test_same_provider_rejection_via_real_validate_coach_config(
        self, role_config: RoleConfig
    ) -> None:
        """AC-LCA-08: when both ``AGENT_MODELS__REASONING_MODEL`` and
        ``AGENT_MODELS__COACH_MODEL`` resolve to the same provider, the
        orchestrator factory's call to :func:`validate_coach_config`
        raises ``CoachConfigurationError`` whose message names both
        providers and references the D3 invariant.

        This test wires a stub factory that drives the real
        :func:`validate_coach_config` so we catch any drift between the
        validator's error contract and the AC text — relying on a hand-
        crafted exception would let the validator silently change
        message format.
        """
        from study_tutor.tutoring.coach.factory import (
            CoachConfig,
            CoachConfigurationError,
            PlayerConfig,
            validate_coach_config,
        )

        # Factory mirrors the real cli/main.py:serve closure shape:
        # resolve player + coach providers from the env, build configs,
        # and invoke the validator. A same-provider scenario exercises
        # the D3 branch.
        def factory() -> object:
            player_cfg = PlayerConfig(provider="anthropic")
            coach_cfg = CoachConfig(provider="anthropic")
            validate_coach_config(
                player_config=player_cfg,
                coach_config=coach_cfg,
                system_prompt="non-empty system prompt",
                tools=None,
            )
            return object()  # never reached

        with pytest.raises(CoachConfigurationError) as exc_info:
            MCPAdapter(
                role_config=role_config,
                store=SessionStore(),
                orchestrator_factory=factory,
            )

        # Message must name both providers and reference the D3 / two-
        # provider invariant per AC-LCA-08.
        msg = str(exc_info.value)
        assert "anthropic" in msg
        # The validator's message uses repr() so 'anthropic' appears
        # twice — once for Coach.provider, once for Player.provider.
        assert msg.count("anthropic") >= 2
        assert "two-provider" in msg.lower() or "ASSUM-009" in msg


async def test_session_end_skips_topic_confidence_for_zero_turn_session(
    role_config: RoleConfig, monkeypatch: pytest.MonkeyPatch
) -> None:
    """I-T6 zero-turn invariant: no user turns → no F2 episode candidate.

    The adapter must skip ``record_topic_confidence_update`` entirely
    when ``len(session.turns) == 0`` so we don't dispatch a temporally-
    orphaned F2 write after ``perform_session_end`` already suppressed
    ``session.completed`` and the F3 write.
    """
    from study_tutor.knowledge.async_write import GraphitiWriteHelper
    from study_tutor.mcp import adapter as adapter_mod
    from study_tutor.tutoring.session_end import EventBus

    async def fake_perform_session_end(**kwargs: object) -> dict[str, object]:
        ts = kwargs.get("transition_state")
        assert callable(ts)
        ts()  # type: ignore[operator]
        return {"session_id": "x", "status": "ended"}

    monkeypatch.setattr(
        adapter_mod, "perform_session_end", fake_perform_session_end
    )

    record_called = False

    async def fake_record_topic_confidence_update(**kwargs: object) -> None:
        nonlocal record_called
        record_called = True

    monkeypatch.setattr(
        adapter_mod,
        "record_topic_confidence_update",
        fake_record_topic_confidence_update,
    )

    store = SessionStore()
    adapter = MCPAdapter(
        role_config=role_config,
        store=store,
        write_helper=GraphitiWriteHelper(client=None),
        event_bus=EventBus(),
        graphiti_client=object(),
    )
    started = await adapter.tutor_start_session(student_id="lilymay")
    session_id = started["session_id"]
    await _drain_warmups(adapter)
    # Deliberately do not append any turns.

    await adapter.tutor_session_end(session_id=session_id)
    await asyncio.sleep(0)
    assert record_called is False
