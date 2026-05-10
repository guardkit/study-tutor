"""Unit tests for :class:`study_tutor.adapters.nats_adapter.NATSAdapter`.

Covers acceptance criteria AC-001..AC-005 and AC-007 from
TASK-NATS-PH1-005. AC-006 (live nats-server round-trip) lives in
``tests/integration/test_adapter_lifecycle.py``.

Strategy: every test patches :class:`nats_core.client.NATSClient` with an
:class:`unittest.mock.AsyncMock` so the lifecycle is exercised without
touching the network. Mock call inspection asserts the Bug #1 contract
(``subscribe_with_reply``, never plain ``subscribe``) and the
deregistration cleanup.
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from nats_core import AgentManifest
from nats_core.agent_config import AgentConfig, ModelConfig, NATSConfig
from nats_core.events._fleet import AgentHeartbeatPayload
from nats_core.manifest import IntentCapability

from study_tutor.adapters.nats_adapter import NATSAdapter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def agent_config() -> AgentConfig:
    """Default config — heartbeat interval is overridden per-test as needed."""
    return AgentConfig(
        models=ModelConfig(reasoning_model="test-model"),
        nats=NATSConfig(url="nats://localhost:4222"),
        heartbeat_interval_seconds=30,
        heartbeat_timeout_seconds=60,
    )


@pytest.fixture()
def manifest() -> AgentManifest:
    """Minimal manifest — non-empty intents satisfies the Bug #5 guard."""
    return AgentManifest(
        agent_id="gcse-tutor",
        name="GCSE Tutor",
        version="0.1.0",
        template="study-tutor-phase-1",
        intents=[
            IntentCapability(
                pattern="tutoring.*",
                signals=["help"],
                confidence=0.9,
                description="Tutoring sessions.",
            )
        ],
        tools=[],
    )


@pytest.fixture()
def mock_router() -> AsyncMock:
    """Stand-in for CommandRouter — only ``on_command`` is awaited."""
    router = AsyncMock()
    router.on_command = AsyncMock(return_value=None)
    return router


@pytest.fixture()
def mock_client_factory():
    """Patch NATSClient at import site so every adapter instance gets a mock."""
    with patch("study_tutor.adapters.nats_adapter.NATSClient") as cls:
        instance = AsyncMock()
        # Subscription handle returned by subscribe_with_reply.
        sub_handle = AsyncMock()
        sub_handle.unsubscribe = AsyncMock(return_value=None)
        instance.connect = AsyncMock(return_value=None)
        instance.disconnect = AsyncMock(return_value=None)
        instance.register_agent = AsyncMock(return_value=None)
        instance.deregister_agent = AsyncMock(return_value=None)
        instance.subscribe_with_reply = AsyncMock(return_value=sub_handle)
        instance.subscribe = AsyncMock(return_value=sub_handle)
        instance.heartbeat = AsyncMock(return_value=None)
        cls.return_value = instance
        yield cls, instance, sub_handle


@pytest.fixture()
def adapter(
    agent_config: AgentConfig,
    manifest: AgentManifest,
    mock_router: AsyncMock,
    mock_client_factory: tuple[MagicMock, AsyncMock, AsyncMock],
) -> NATSAdapter:
    """Construct an adapter with a mocked NATSClient."""
    return NATSAdapter(
        config=agent_config,
        manifest=manifest,
        command_router=mock_router,
    )


# ---------------------------------------------------------------------------
# AC-001 — start() lifecycle
# ---------------------------------------------------------------------------


class TestStartLifecycle:
    """``start()`` connects, registers, subscribes, heartbeats, sets ready."""

    async def test_start_calls_connect(
        self, adapter: NATSAdapter, mock_client_factory: Any
    ) -> None:
        _, instance, _ = mock_client_factory
        await adapter.start()
        instance.connect.assert_awaited_once()
        await adapter.stop()

    async def test_start_registers_manifest(
        self,
        adapter: NATSAdapter,
        manifest: AgentManifest,
        mock_client_factory: Any,
    ) -> None:
        _, instance, _ = mock_client_factory
        await adapter.start()
        instance.register_agent.assert_awaited_once_with(manifest)
        await adapter.stop()

    async def test_start_subscribes_to_command_subject(
        self,
        adapter: NATSAdapter,
        manifest: AgentManifest,
        mock_client_factory: Any,
    ) -> None:
        _, instance, _ = mock_client_factory
        await adapter.start()
        instance.subscribe_with_reply.assert_awaited_once()
        subject = instance.subscribe_with_reply.await_args.args[0]
        assert subject == f"agents.command.{manifest.agent_id}"
        await adapter.stop()

    async def test_start_spawns_heartbeat_task(
        self, adapter: NATSAdapter
    ) -> None:
        await adapter.start()
        assert adapter._heartbeat_task is not None
        assert not adapter._heartbeat_task.done()
        await adapter.stop()

    async def test_start_sets_ready(self, adapter: NATSAdapter) -> None:
        assert adapter.is_ready is False
        await adapter.start()
        assert adapter.is_ready is True
        await adapter.stop()

    async def test_start_records_start_time(
        self, adapter: NATSAdapter
    ) -> None:
        assert adapter._start_time == 0.0
        await adapter.start()
        assert adapter._start_time > 0.0
        await adapter.stop()


# ---------------------------------------------------------------------------
# AC-002 — Bug #1 regression guard: subscribe_with_reply, NOT subscribe
# ---------------------------------------------------------------------------


class TestSubscribeWithReplyContract:
    """The adapter MUST use ``subscribe_with_reply`` for the command subject."""

    async def test_start_uses_subscribe_with_reply(
        self, adapter: NATSAdapter, mock_client_factory: Any
    ) -> None:
        _, instance, _ = mock_client_factory
        await adapter.start()
        instance.subscribe_with_reply.assert_awaited_once()
        await adapter.stop()

    async def test_start_does_not_use_plain_subscribe(
        self, adapter: NATSAdapter, mock_client_factory: Any
    ) -> None:
        """Bug #1: plain subscribe() drops msg.reply — must never be used here."""
        _, instance, _ = mock_client_factory
        await adapter.start()
        instance.subscribe.assert_not_awaited()
        await adapter.stop()

    async def test_subscribe_with_reply_receives_on_command_callback(
        self, adapter: NATSAdapter, mock_client_factory: Any
    ) -> None:
        _, instance, _ = mock_client_factory
        await adapter.start()
        # second positional arg is the callback
        callback = instance.subscribe_with_reply.await_args.args[1]
        assert callback == adapter._on_command
        await adapter.stop()


# ---------------------------------------------------------------------------
# AC-003 — stop() lifecycle
# ---------------------------------------------------------------------------


class TestStopLifecycle:
    """``stop()`` unsubscribes, drains, cancels heartbeat, deregisters, disconnects."""

    async def test_stop_unsubscribes(
        self, adapter: NATSAdapter, mock_client_factory: Any
    ) -> None:
        _, _, sub_handle = mock_client_factory
        await adapter.start()
        await adapter.stop()
        sub_handle.unsubscribe.assert_awaited_once()

    async def test_stop_deregisters(
        self,
        adapter: NATSAdapter,
        manifest: AgentManifest,
        mock_client_factory: Any,
    ) -> None:
        _, instance, _ = mock_client_factory
        await adapter.start()
        await adapter.stop()
        instance.deregister_agent.assert_awaited_once_with(
            manifest.agent_id, reason="shutdown"
        )

    async def test_stop_cancels_heartbeat_task(
        self, adapter: NATSAdapter
    ) -> None:
        await adapter.start()
        hb = adapter._heartbeat_task
        await adapter.stop()
        assert hb is not None
        assert hb.cancelled() or hb.done()
        assert adapter._heartbeat_task is None

    async def test_stop_disconnects(
        self, adapter: NATSAdapter, mock_client_factory: Any
    ) -> None:
        _, instance, _ = mock_client_factory
        await adapter.start()
        await adapter.stop()
        instance.disconnect.assert_awaited_once()

    async def test_stop_clears_ready(self, adapter: NATSAdapter) -> None:
        await adapter.start()
        assert adapter.is_ready is True
        await adapter.stop()
        assert adapter.is_ready is False

    async def test_stop_continues_on_deregister_failure(
        self, adapter: NATSAdapter, mock_client_factory: Any
    ) -> None:
        _, instance, _ = mock_client_factory
        instance.deregister_agent.side_effect = RuntimeError("boom")
        await adapter.start()
        # stop() must swallow the boundary failure and still complete cleanup.
        await adapter.stop()
        instance.disconnect.assert_awaited_once()
        assert adapter.is_ready is False

    async def test_stop_default_shutdown_timeout_is_30_seconds(
        self, adapter: NATSAdapter
    ) -> None:
        """Mirror the architect's adapter (specialist_agent/.../nats_adapter.py:72)."""
        assert adapter._shutdown_timeout == 30.0

    async def test_stop_waits_for_active_tasks_to_drain(
        self,
        agent_config: AgentConfig,
        manifest: AgentManifest,
        mock_client_factory: Any,
    ) -> None:
        """``stop()`` must observe active_tasks dropping to 0 before tearing down."""
        gate = asyncio.Event()
        observed: list[int] = []

        async def slow_handler(_envelope: Any, _reply: Any = None) -> None:
            observed.append(1)
            await gate.wait()

        router = MagicMock()
        router.on_command = slow_handler
        adapter = NATSAdapter(
            config=agent_config, manifest=manifest, command_router=router
        )
        # Short drain timeout so the test stays fast.
        adapter._shutdown_timeout = 1.0

        await adapter.start()

        # Kick off an in-flight command directly through the wrapped handler.
        task = asyncio.create_task(adapter._on_command(MagicMock(), "reply"))
        # Yield once so the handler can run and bump active_tasks.
        await asyncio.sleep(0)
        assert adapter.active_tasks == 1

        # Start stop() — it should be blocked waiting for the active task.
        stop_task = asyncio.create_task(adapter.stop())
        await asyncio.sleep(0.05)
        assert not stop_task.done(), "stop() should be waiting for drain"

        # Let the handler finish — stop() can now complete.
        gate.set()
        await task
        await asyncio.wait_for(stop_task, timeout=2.0)
        assert adapter.active_tasks == 0


# ---------------------------------------------------------------------------
# AC-004 — heartbeat at configured interval
# ---------------------------------------------------------------------------


class TestHeartbeatLoop:
    """Heartbeat publishes at ``config.heartbeat_interval_seconds`` cadence."""

    async def test_heartbeat_publishes_repeatedly(
        self, adapter: NATSAdapter, mock_client_factory: Any
    ) -> None:
        _, instance, _ = mock_client_factory
        # Tighten the interval to make the test fast.
        adapter._config.heartbeat_interval_seconds = 0.01
        await adapter.start()
        await asyncio.sleep(0.1)
        await adapter.stop()
        # In 100ms with a 10ms interval we expect ~10 publishes; floor at 3
        # to absorb scheduler jitter on slow CI runners.
        assert instance.heartbeat.await_count >= 3

    async def test_heartbeat_payload_uses_agent_id(
        self,
        adapter: NATSAdapter,
        manifest: AgentManifest,
        mock_client_factory: Any,
    ) -> None:
        _, instance, _ = mock_client_factory
        adapter._config.heartbeat_interval_seconds = 0.01
        await adapter.start()
        await asyncio.sleep(0.05)
        await adapter.stop()
        # First heartbeat payload is an AgentHeartbeatPayload with our agent_id.
        payload = instance.heartbeat.await_args_list[0].args[0]
        assert isinstance(payload, AgentHeartbeatPayload)
        assert payload.agent_id == manifest.agent_id

    async def test_heartbeat_status_reflects_active_tasks(
        self, adapter: NATSAdapter
    ) -> None:
        """``ready`` when idle, ``busy`` when at least one task is in flight."""
        await adapter.start()
        idle = adapter._build_heartbeat_payload()
        assert idle.status == "ready"
        adapter._active_tasks = 1
        busy = adapter._build_heartbeat_payload()
        assert busy.status == "busy"
        adapter._active_tasks = 0
        await adapter.stop()

    async def test_heartbeat_continues_after_publish_error(
        self, adapter: NATSAdapter, mock_client_factory: Any
    ) -> None:
        """A transient publish failure must not kill the heartbeat loop."""
        _, instance, _ = mock_client_factory
        # First call raises, subsequent calls succeed.
        call_count = {"n": 0}

        async def flaky_heartbeat(_payload: Any) -> None:
            call_count["n"] += 1
            if call_count["n"] == 1:
                raise RuntimeError("transient")

        instance.heartbeat.side_effect = flaky_heartbeat
        adapter._config.heartbeat_interval_seconds = 0.01
        await adapter.start()
        await asyncio.sleep(0.1)
        await adapter.stop()
        assert call_count["n"] >= 2  # loop survived and kept publishing


# ---------------------------------------------------------------------------
# AC-005 — active-task counter
# ---------------------------------------------------------------------------


class TestActiveTaskCounter:
    """``_on_command`` increments/decrements ``active_tasks`` around dispatch."""

    async def test_counter_starts_at_zero(
        self, adapter: NATSAdapter
    ) -> None:
        assert adapter.active_tasks == 0

    async def test_counter_increments_during_dispatch(
        self,
        agent_config: AgentConfig,
        manifest: AgentManifest,
        mock_client_factory: Any,
    ) -> None:
        observed: list[int] = []

        async def observer(_envelope: Any, _reply: Any = None) -> None:
            observed.append(99)  # captured below

        router = MagicMock()
        captured: list[int] = []

        async def capture(_envelope: Any, _reply: Any = None) -> None:
            captured.append(adapter_local.active_tasks)
            observed.append(1)

        router.on_command = capture
        adapter_local = NATSAdapter(
            config=agent_config, manifest=manifest, command_router=router
        )

        await adapter_local._on_command(MagicMock(), "reply")
        assert captured == [1]  # mid-dispatch the counter was 1
        assert adapter_local.active_tasks == 0  # decremented after

    async def test_counter_decrements_on_router_exception(
        self,
        agent_config: AgentConfig,
        manifest: AgentManifest,
    ) -> None:
        async def boom(_envelope: Any, _reply: Any = None) -> None:
            raise ValueError("router crashed")

        router = MagicMock()
        router.on_command = boom
        adapter_local = NATSAdapter(
            config=agent_config, manifest=manifest, command_router=router
        )

        with pytest.raises(ValueError, match="router crashed"):
            await adapter_local._on_command(MagicMock(), "reply")
        assert adapter_local.active_tasks == 0

    async def test_concurrent_dispatch_increments_counter(
        self,
        agent_config: AgentConfig,
        manifest: AgentManifest,
    ) -> None:
        gate = asyncio.Event()

        async def slow(_envelope: Any, _reply: Any = None) -> None:
            await gate.wait()

        router = MagicMock()
        router.on_command = slow
        adapter_local = NATSAdapter(
            config=agent_config, manifest=manifest, command_router=router
        )

        t1 = asyncio.create_task(
            adapter_local._on_command(MagicMock(), "r1")
        )
        t2 = asyncio.create_task(
            adapter_local._on_command(MagicMock(), "r2")
        )
        await asyncio.sleep(0)  # yield so handlers enter
        assert adapter_local.active_tasks == 2
        gate.set()
        await asyncio.gather(t1, t2)
        assert adapter_local.active_tasks == 0


# ---------------------------------------------------------------------------
# Bug #8 regression guard (TASK-NATS-PH1-011): router client share-after-connect
# ---------------------------------------------------------------------------


class TestRouterClientShareAfterConnect:
    """``start()`` must hand the connected adapter client to the router.

    Bug #8 (RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-1.md): the
    router was constructed in ``_build_nats_runtime`` with its own
    un-connected ``NATSClient``, so the first ``publish_raw`` on the reply
    inbox raised ``RuntimeError: client is not connected`` and no result
    envelope was ever emitted on ``agents.result.<agent_id>``. The fix
    shares the adapter's connected client with the router immediately
    after ``connect()`` returns. These tests pin that contract so a future
    refactor (Option C — router stops owning a client) cannot silently
    regress the demo wire-path again.
    """

    async def test_start_assigns_adapter_client_to_router(
        self, adapter: NATSAdapter, mock_router: AsyncMock, mock_client_factory: Any
    ) -> None:
        """After start() the router's client IS the adapter's connected client."""
        _, instance, _ = mock_client_factory
        await adapter.start()
        assert mock_router.client is instance
        assert mock_router.client is adapter._client
        await adapter.stop()

    async def test_router_client_assigned_after_connect_before_register(
        self, adapter: NATSAdapter, mock_router: AsyncMock, mock_client_factory: Any
    ) -> None:
        """Assignment must happen between connect() and register_agent().

        If ``register_agent`` raises, the router must still hold the
        connected client (so a retry of start() does not leave the router
        wired to the stale un-connected instance from construction).
        """
        _, instance, _ = mock_client_factory
        instance.register_agent.side_effect = RuntimeError("register boom")

        with pytest.raises(RuntimeError, match="register boom"):
            await adapter.start()

        # Connect ran, assignment ran, then register_agent raised.
        instance.connect.assert_awaited_once()
        assert mock_router.client is adapter._client

    async def test_only_one_nats_client_connection_after_start(
        self, adapter: NATSAdapter, mock_client_factory: Any
    ) -> None:
        """Single live connection contract: no second client.connect() call.

        AC: "No new NATS connections are introduced — the process must
        hold exactly one live NATS connection (the adapter's) after
        ``start()``."
        """
        cls, instance, _ = mock_client_factory
        await adapter.start()
        # Adapter constructs exactly one NATSClient.
        assert cls.call_count == 1
        # And connects it exactly once.
        instance.connect.assert_awaited_once()
        await adapter.stop()


# ---------------------------------------------------------------------------
# Constructor wiring
# ---------------------------------------------------------------------------


class TestConstructor:
    """The adapter wires its NATSClient from the manifest's agent_id."""

    def test_client_built_with_manifest_agent_id(
        self,
        agent_config: AgentConfig,
        manifest: AgentManifest,
        mock_router: AsyncMock,
        mock_client_factory: Any,
    ) -> None:
        cls, _, _ = mock_client_factory
        NATSAdapter(
            config=agent_config,
            manifest=manifest,
            command_router=mock_router,
        )
        cls.assert_called_once()
        kwargs = cls.call_args.kwargs
        assert kwargs["source_id"] == manifest.agent_id
        assert kwargs["config"] == agent_config.nats

    def test_initial_state(
        self,
        agent_config: AgentConfig,
        manifest: AgentManifest,
        mock_router: AsyncMock,
        mock_client_factory: Any,
    ) -> None:
        adapter = NATSAdapter(
            config=agent_config,
            manifest=manifest,
            command_router=mock_router,
        )
        assert adapter.is_ready is False
        assert adapter.active_tasks == 0
        assert adapter._heartbeat_task is None
        assert adapter._command_sub is None
        assert adapter._shutdown_timeout == 30.0
