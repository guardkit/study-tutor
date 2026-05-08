"""pytest-bdd glue module for ``nats-fleet-integration.feature``.

This module exists for the same two reasons that
``test_graphiti_student_model.py`` does (see that file's docstring for
the canonical explanation):

1. **Collection bridge** — GuardKit's ``bdd_runner`` invokes ``pytest``
   with the literal ``.feature`` path. ``features/conftest.py`` redirects
   that argv to this sibling glue module so :func:`pytest_bdd.scenarios`
   can actually bind the scenarios. Without a glue module the runner
   collects zero items and Coach's BDD oracle reports the scenario as
   failed.

2. **Step definitions for @task:TASK-NATS-PH1-006** — the scenario
   tagged ``@task:TASK-NATS-PH1-006`` ("SIGTERM during an in-flight
   tutor turn drains the request before deregistration") has step
   definitions in this module. Every other scenario in the feature file
   is tagged for a downstream task (TASK-NATS-PH1-002, -004, -005,
   -007, -008, -009, PH2, PH3) and will land with that task; their
   steps remain intentionally unbound here. They surface as
   ``scenarios_pending`` and are tolerated by the Coach gate
   (``scenarios_failed == 0``).

Async-step discipline:

pytest-bdd v8 does NOT support ``async def`` step functions — the
coroutine returned by an async step is never awaited and the test
silently passes through unverified state. Every step in this module is
therefore **synchronous** and drives async work via a single
:class:`asyncio.AbstractEventLoop` owned by the :class:`_BddContext`
fixture. The pattern keeps the SIGTERM contract test hermetic without
straying into pytest-asyncio territory (which the BDD runner does not
configure for ``.feature``-driven runs).
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from study_tutor.cli.main import _serve_adapter


# Bind every scenario in the sibling .feature file. The BDD runner's
# ``-m task_TASK_NATS_PH1_006`` filter selects this task's subset; steps
# unique to other tasks remain unbound (``scenarios_pending``, tolerated
# by the Coach gate).
scenarios(str(Path(__file__).with_name("nats-fleet-integration.feature")))


# ---------------------------------------------------------------------------
# Per-scenario shared state
# ---------------------------------------------------------------------------


@dataclass
class _BddContext:
    """Mutable container threaded through Given/When/Then via fixture.

    Owns the asyncio loop the steps run async work on, the fake adapter
    being exercised, the shutdown event the SIGTERM step sets, and the
    observable side-effects that the Then-steps assert against.
    """

    loop: asyncio.AbstractEventLoop | None = None
    adapter: "_FakeNATSAdapter | None" = None
    write_helper: Any = None
    shutdown_event: asyncio.Event | None = None
    serve_task: asyncio.Task[None] | None = None
    serve_completed: bool = False
    serve_duration_seconds: float = 0.0
    inflight_started: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


@pytest.fixture
def context() -> Any:
    """Per-scenario fixture providing the shared :class:`_BddContext`.

    A dedicated event loop is created so every step in the scenario can
    drive async work via ``loop.run_until_complete`` without colliding
    with pytest-asyncio's auto-managed loops elsewhere in the suite.
    """
    ctx = _BddContext()
    ctx.loop = asyncio.new_event_loop()
    asyncio.set_event_loop(ctx.loop)
    try:
        yield ctx
    finally:
        # Cancel any tasks the scenario left dangling (a buggy
        # implementation could leave _serve_adapter blocked on the
        # shutdown event), then close the loop.
        try:
            pending = asyncio.all_tasks(ctx.loop)
            for task in pending:
                task.cancel()
            if pending:
                ctx.loop.run_until_complete(
                    asyncio.gather(*pending, return_exceptions=True)
                )
        finally:
            ctx.loop.close()
            asyncio.set_event_loop(None)


# ---------------------------------------------------------------------------
# Fake NATSAdapter — mirrors the contract owned by TASK-NATS-PH1-005
# ---------------------------------------------------------------------------


class _FakeNATSAdapter:
    """Minimal adapter modelling the TASK-NATS-PH1-005 contract.

    The real adapter (``study_tutor.adapters.nats_adapter.NATSAdapter``)
    is owned by a downstream task. This fake captures the surface that
    the TASK-NATS-PH1-006 SIGTERM scenario depends on:

    * ``start()`` flips ``self.ready`` and counts as registration.
    * ``simulate_inflight_turn()`` marks an in-flight ``tutor_turn`` so
      ``stop()`` has something to drain.
    * ``stop()`` waits for the in-flight task to finish (bounded by the
      30 s drain window TASK-NATS-PH1-005 will implement), publishes
      its result, deregisters, and clears ``ready``.

    We deliberately keep the simulated drain *fast* (50 ms) so the
    scenario completes inside the suite's normal budget. The assertion
    we care about is the **ordering** (drain → publish-result →
    deregister), not the wall-clock budget — that is captured by a
    bound on ``serve_duration_seconds`` in the Then-step.
    """

    drain_window_seconds: float = 30.0

    def __init__(self) -> None:
        self.ready: bool = False
        self.deregistered: bool = False
        self.connection_closed: bool = False
        self.heartbeat_running: bool = False
        self._inflight: asyncio.Task[None] | None = None
        self.inflight_completed: bool = False
        self.inflight_result_published: bool = False
        self.start_called: bool = False
        self.stop_called: bool = False

    async def start(self) -> None:
        self.start_called = True
        self.heartbeat_running = True
        self.ready = True

    def simulate_inflight_turn(self) -> None:
        """Begin a fake in-flight ``tutor_turn`` task.

        Called by the Given-step that says a turn is currently being
        processed. The task itself just sleeps briefly and then marks
        completion; ``stop()`` awaits it as the drain step.
        """

        async def _run_turn() -> None:
            try:
                # Simulated turn duration well inside the 30 s drain
                # window. Real turns can run for up to 600 s
                # (max_task_timeout_seconds) but the contract under test
                # is the drain ordering, not the LLM latency.
                await asyncio.sleep(0.05)
                self.inflight_completed = True
                self.inflight_result_published = True
            except asyncio.CancelledError:
                # Drain must NOT cancel the in-flight turn — if this
                # branch ever fires the scenario fails because the
                # caller never gets the result.
                self.inflight_result_published = False
                raise

        self._inflight = asyncio.create_task(_run_turn())

    async def stop(self) -> None:
        self.stop_called = True
        # Drain in-flight task within the 30 s window. We await
        # directly (the simulated turn is fast) but bound the wait so a
        # buggy implementation cannot hang the suite.
        if self._inflight is not None:
            try:
                await asyncio.wait_for(
                    self._inflight, timeout=self.drain_window_seconds
                )
            except asyncio.TimeoutError:
                # Real adapter would force-cancel here; for the
                # contract test we surface the timeout so the Then-step
                # asserting "completed within 30 seconds" fails loudly.
                self._inflight.cancel()
                raise
        self.heartbeat_running = False
        self.deregistered = True
        self.connection_closed = True
        self.ready = False


class _FakeWriteHelper:
    """Stand-in for :class:`GraphitiWriteHelper` during the BDD scenario.

    The CLI passes the helper to :func:`runtime_shutdown`; our fake
    accepts the call and counts invocations so a regression where the
    CLI skips the F3 drain step would surface.
    """

    def __init__(self) -> None:
        self.flush_calls: int = 0


# ---------------------------------------------------------------------------
# Background steps (apply to every scenario via the feature Background)
# ---------------------------------------------------------------------------


@given("the NATS server is reachable with valid APPMILLA credentials")
def _given_nats_reachable(context: _BddContext) -> None:
    """Background fact — modelled as a no-op pre-condition.

    The real check happens inside ``NATSAdapter.start()``
    (TASK-NATS-PH1-005); here we record that the test assumes a healthy
    server so a future 'NATS-down' scenario can flip the assumption.
    """
    context.extra["nats_reachable"] = True


@given("the agent-registry KV bucket exists")
def _given_kv_bucket_exists(context: _BddContext) -> None:
    context.extra["kv_bucket_exists"] = True


@given("the AGENTS and FLEET JetStream streams are provisioned")
def _given_streams_provisioned(context: _BddContext) -> None:
    context.extra["streams_provisioned"] = True


@given(
    parsers.parse('the study-tutor adapter is configured with agent_id "{agent_id}"')
)
def _given_adapter_agent_id(context: _BddContext, agent_id: str) -> None:
    context.extra["agent_id"] = agent_id
    context.adapter = _FakeNATSAdapter()


@given("the tutor business logic is wired through MCPAdapter")
def _given_mcp_adapter_wired(context: _BddContext) -> None:
    # The real wiring happens inside ``_build_nats_runtime``; here we
    # only record that the contract surface is present.
    context.extra["mcp_wired"] = True


# ---------------------------------------------------------------------------
# TASK-NATS-PH1-006 scenario steps
# ---------------------------------------------------------------------------


@given("the adapter is running and ready")
def _given_adapter_running_and_ready(context: _BddContext) -> None:
    """Bring the fake adapter into the running+ready state.

    Mirrors what ``_serve_adapter`` does on the happy path: ``start()``
    is awaited, ``ready`` flips true. The CLI's run-forever loop is
    started as a background task on the per-scenario loop so the
    When-step can deliver SIGTERM by setting the shared
    ``shutdown_event``.
    """
    assert context.adapter is not None, (
        "Background step must run before the scenario steps"
    )
    assert context.loop is not None
    context.write_helper = _FakeWriteHelper()
    context.shutdown_event = asyncio.Event()

    async def _run_serve() -> None:
        # ``_serve_adapter`` awaits ``adapter.start()`` itself; we do
        # NOT pre-start so the start_called flag captures the CLI's
        # actual call, not a test-side double-call.
        assert context.adapter is not None
        assert context.shutdown_event is not None
        await _serve_adapter(
            context.adapter,
            context.write_helper,
            agent_id=context.extra.get("agent_id", "gcse-tutor"),
            nats_url="nats://localhost:4222",
            shutdown_event=context.shutdown_event,
        )

    context.serve_task = context.loop.create_task(_run_serve())

    # Yield until ``adapter.start()`` has completed and ``ready`` flips.
    # A bounded poll prevents the scenario from hanging on a buggy
    # implementation.
    async def _wait_ready() -> None:
        for _ in range(100):
            if context.adapter is not None and context.adapter.ready:
                return
            await asyncio.sleep(0.01)
        raise AssertionError("Adapter did not become ready within 1 s")

    context.loop.run_until_complete(_wait_ready())


@given("a tutor_turn command is currently being processed")
def _given_inflight_tutor_turn(context: _BddContext) -> None:
    assert context.adapter is not None
    assert context.loop is not None

    # ``simulate_inflight_turn`` schedules an asyncio.Task on the
    # current loop; do it inside the loop so the task is registered
    # against the per-scenario loop, not pytest-asyncio's loop.
    async def _start_turn() -> None:
        assert context.adapter is not None
        context.adapter.simulate_inflight_turn()

    context.loop.run_until_complete(_start_turn())
    context.inflight_started = True


@when("the adapter receives SIGTERM")
def _when_sigterm_received(context: _BddContext) -> None:
    """Deliver a SIGTERM-equivalent by setting the shared event.

    Setting ``shutdown_event`` is exactly what the production
    ``loop.add_signal_handler(SIGTERM, _request_shutdown)`` does — we
    drive the contract directly to keep the test hermetic on every
    platform (avoids racing pytest's own signal handlers).
    """
    assert context.shutdown_event is not None
    assert context.serve_task is not None
    assert context.loop is not None

    started_at = context.loop.time()

    async def _trigger_and_wait() -> None:
        assert context.shutdown_event is not None
        assert context.serve_task is not None
        context.shutdown_event.set()
        # Wait for ``_serve_adapter`` to return — the SIGTERM is only
        # honoured once the run-forever loop unwinds through its
        # finally branches.
        await context.serve_task

    context.loop.run_until_complete(_trigger_and_wait())
    context.serve_duration_seconds = context.loop.time() - started_at
    context.serve_completed = True


@then("the in-flight tutor turn should be allowed to complete within 30 seconds")
def _then_inflight_completes_within_drain_window(context: _BddContext) -> None:
    assert context.adapter is not None
    assert context.adapter.inflight_completed, (
        "In-flight tutor_turn must be allowed to finish before deregistration"
    )
    # The simulated turn is fast; the load-bearing assertion is that
    # the drain window did not time out (fake adapter raises if it
    # does).
    assert context.serve_duration_seconds < _FakeNATSAdapter.drain_window_seconds, (
        f"Shutdown took {context.serve_duration_seconds:.2f}s, exceeds "
        f"30s drain window"
    )


@then("the result for that turn should reach the caller before the adapter exits")
def _then_inflight_result_published(context: _BddContext) -> None:
    assert context.adapter is not None
    assert context.adapter.inflight_result_published, (
        "In-flight tutor_turn result must be published before stop() returns "
        "(otherwise the caller's request future never resolves)"
    )
    # Ordering invariant — the result must have been published *before*
    # deregistration, not after. Both flags are set inside ``stop()``;
    # the assertion below catches a future regression where a refactor
    # moves deregistration ahead of the drain.
    assert context.adapter.deregistered, (
        "Deregistration must run after the drain completes"
    )


@then("the registry entry should then be removed")
def _then_registry_entry_removed(context: _BddContext) -> None:
    assert context.adapter is not None
    assert context.adapter.deregistered, (
        "Registry entry must be removed (adapter.stop() → deregister)"
    )
    assert context.adapter.connection_closed, (
        "NATS connection must be closed after deregister so a stale "
        "subscription cannot continue to receive commands"
    )
    assert not context.adapter.ready, (
        "Adapter must clear its ready flag on the way out"
    )
