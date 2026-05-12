"""NATS fleet lifecycle manager for the study-tutor (GCSE Tutor) agent.

Handles connection, registration, heartbeat, command subscription, and
graceful shutdown. The CommandRouter is supplied at construction time —
``start()`` subscribes to ``agents.command.<agent_id>`` via
:meth:`NATSClient.subscribe_with_reply` so that the requester's reply
inbox propagates to :meth:`CommandRouter.on_command` (Bug #1 fix).

Lifecycle:
    1. ``start()`` — Connect → register manifest → subscribe with reply
       → start heartbeat loop → set ``_ready``.
    2. Running — Heartbeat loop publishes at the interval configured on
       :class:`AgentConfig.heartbeat_interval_seconds` (default 30s).
       Each inbound command increments :attr:`_active_tasks` for the
       duration of routing so :meth:`stop` can wait for in-flight work.
    3. ``stop()`` — Unsubscribe → drain active tasks (within
       ``_shutdown_timeout=30.0s``) → cancel heartbeat → deregister →
       disconnect → clear ``_ready``.

All NATS subjects are resolved via :class:`nats_core.Topics` — no
hard-coded strings. All payloads are wrapped in
:class:`nats_core.MessageEnvelope` by the convenience methods on
:class:`NATSClient`.

Mirrors the architect's adapter at
``specialist-agent/src/specialist_agent/adapters/nats_adapter.py`` so the
two services share lifecycle semantics — including the 30s shutdown
timeout (TASK-NATS-PH1-005 implementation note).
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Protocol

from nats_core import AgentManifest, NATSClient, Topics
from nats_core.agent_config import AgentConfig
from nats_core.events._fleet import AgentHeartbeatPayload

if TYPE_CHECKING:
    from nats_core.envelope import MessageEnvelope

logger = logging.getLogger(__name__)


class _CommandRouterProtocol(Protocol):
    """Structural type for command-router objects accepted by :class:`NATSAdapter`.

    Anything with an awaitable ``on_command(envelope, reply_to)`` method
    satisfies the contract — the real
    :class:`study_tutor.adapters.command_router.CommandRouter`
    (TASK-NATS-PH1-004), test fakes, and the integration test's
    ``_RecordingCommandRouter`` all conform.
    """

    async def on_command(
        self,
        envelope: MessageEnvelope,
        reply_to: str | None = None,
    ) -> None: ...


class NATSAdapter:
    """NATS fleet lifecycle manager for the GCSE Tutor agent.

    Args:
        config: Agent configuration with NATS settings and heartbeat
            interval. ``config.heartbeat_interval_seconds`` (default 30)
            drives the heartbeat cadence; ``config.nats`` configures the
            underlying :class:`NATSClient`.
        manifest: The :class:`AgentManifest` to publish on registration.
            Must have at least one intent (Bug #5 regression guard
            enforced by :class:`nats_core.manifest.AgentManifest`).
        command_router: The router whose ``on_command`` handler will be
            wired to the ``agents.command.<agent_id>`` subscription via
            :meth:`NATSClient.subscribe_with_reply` so that the
            requester's reply inbox propagates through (Bug #1 fix).
    """

    def __init__(
        self,
        config: AgentConfig,
        manifest: AgentManifest,
        command_router: _CommandRouterProtocol,
    ) -> None:
        self._config = config
        self._manifest = manifest
        self._command_router = command_router
        # TASK-NATS-FIX-006: event the CLI's `_serve_adapter` awaits so the
        # process exits non-zero when nats-py exhausts its reconnect budget.
        # Constructed before the client because `_on_closed` (passed as the
        # client's closed_cb) references it.
        self._terminal_close_event = asyncio.Event()
        # TASK-NATS-FIX-006 / TASK-NC10: wire reconnect/disconnect/closed
        # callbacks so a broker bounce re-publishes the manifest to
        # `agent-registry` KV and a terminal close drives container exit.
        # Passing closed_cb deliberately overrides the client's default
        # `_default_closed_cb` — the adapter owns the terminal signal.
        self._client = NATSClient(
            config=config.nats,
            source_id=manifest.agent_id,
            reconnected_cb=self._on_reconnect,
            disconnected_cb=self._on_disconnect,
            closed_cb=self._on_closed,
        )
        self._heartbeat_task: asyncio.Task[None] | None = None
        self._command_sub: Any | None = None
        self._active_tasks: int = 0
        self._ready = asyncio.Event()
        self._start_time: float = 0.0
        # Match the architect's adapter (specialist_agent/.../nats_adapter.py:72)
        # so both services drain in-flight work on the same 30s budget.
        self._shutdown_timeout: float = 30.0

    @property
    def terminal_close_event(self) -> asyncio.Event:
        """Event set when nats-py has exhausted its reconnect budget.

        The CLI's ``_serve_adapter`` awaits this alongside ``shutdown_event``
        so a prolonged broker outage exits the process non-zero (rather than
        leaving a stale ``Up`` container in the fleet).
        """
        return self._terminal_close_event

    # ------------------------------------------------------------------
    # Public read-only state
    # ------------------------------------------------------------------

    @property
    def is_ready(self) -> bool:
        """Whether ``start()`` has completed and the adapter is accepting commands."""
        return self._ready.is_set()

    @property
    def active_tasks(self) -> int:
        """Number of command-dispatch tasks currently in flight."""
        return self._active_tasks

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Connect, register, subscribe, and begin heartbeats.

        Steps (in order):

        1. ``self._client.connect()`` — open the NATS connection.
        2. ``self._client.register_agent(self._manifest)`` — publish the
           manifest to ``fleet.register`` and store it in the
           ``agent-registry`` KV bucket.
        3. ``self._client.subscribe_with_reply(<command-subject>, self._on_command)``
           — wire the command handler with reply-inbox propagation
           (Bug #1 fix: never call plain ``subscribe`` here).
        4. Spawn the heartbeat task.
        5. Set ``self._ready``.

        Raises:
            RuntimeError: If the underlying NATS connection fails or the
                client is already connected.
        """
        self._start_time = time.monotonic()
        logger.info(
            "Starting NATSAdapter for agent '%s'",
            self._manifest.agent_id,
        )

        await self._client.connect()

        # Bug #8 fix (TASK-NATS-PH1-011): the router was constructed in
        # `_build_nats_runtime` with its own un-connected NATSClient, so its
        # first publish_raw raised "client is not connected" and no result
        # envelope was ever emitted. Share the adapter's already-connected
        # client with the router before any subscription can fire. Must run
        # before `register_agent` so the assignment is atomic with connect()
        # even if registration raises. Option (C) (router stops owning a
        # client at all) is the follow-up post-demo.
        self._command_router.client = self._client

        await self._client.register_agent(self._manifest)
        logger.info(
            "Registered agent '%s' to %s",
            self._manifest.agent_id,
            Topics.Fleet.REGISTER,
        )

        command_subject = Topics.resolve(
            Topics.Agents.COMMAND, agent_id=self._manifest.agent_id
        )
        # Bug #1 guard: subscribe_with_reply propagates msg.reply to the
        # handler so on_command can publish the ResultPayload straight to
        # the requester's _INBOX. Plain subscribe() drops the reply
        # subject and breaks request/reply.
        self._command_sub = await self._client.subscribe_with_reply(
            command_subject, self._on_command
        )
        logger.info(
            "Subscribed (with reply) to command subject '%s'",
            command_subject,
        )

        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(),
            name=f"heartbeat-{self._manifest.agent_id}",
        )

        self._ready.set()
        logger.info("NATSAdapter ready for agent '%s'", self._manifest.agent_id)

    async def stop(self) -> None:
        """Graceful shutdown.

        Order is deliberate — unsubscribe FIRST to stop accepting new
        commands, then drain in-flight work, then tear down the heartbeat
        and connection. This avoids losing commands that were mid-dispatch.

        Steps:

        1. Unsubscribe from the command subject (drop new commands).
        2. Wait up to ``self._shutdown_timeout`` (30s) for
           ``self._active_tasks`` to reach zero.
        3. Cancel the heartbeat task.
        4. ``self._client.deregister_agent(...)`` — publish deregistration
           and delete the manifest from the KV bucket.
        5. ``self._client.disconnect()``.
        6. Clear ``self._ready``.

        Errors during deregister/disconnect are logged but never re-raised
        — stop() must always succeed so callers can finish their shutdown.
        """
        logger.info("Stopping NATSAdapter for agent '%s'", self._manifest.agent_id)

        # 1. Unsubscribe so no new commands arrive while we drain.
        if self._command_sub is not None:
            try:
                await self._command_sub.unsubscribe()
            except Exception as exc:  # noqa: BLE001 — boundary: log + continue
                logger.warning(
                    "Error unsubscribing from command subject: %s", exc
                )
            self._command_sub = None

        # 2. Drain in-flight commands.
        if self._active_tasks > 0:
            logger.info(
                "Waiting for %d active tasks to drain (timeout %.1fs)",
                self._active_tasks,
                self._shutdown_timeout,
            )
            deadline = time.monotonic() + self._shutdown_timeout
            while self._active_tasks > 0 and time.monotonic() < deadline:
                await asyncio.sleep(0.05)
            if self._active_tasks > 0:
                logger.warning(
                    "Shutdown timeout: %d task(s) still active, "
                    "proceeding with deregistration anyway",
                    self._active_tasks,
                )

        # 3. Cancel the heartbeat loop.
        if self._heartbeat_task is not None:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
            except Exception as exc:  # noqa: BLE001 — boundary: log + continue
                logger.warning("Heartbeat task raised on cancel: %s", exc)
            self._heartbeat_task = None

        # 4. Deregister — best-effort.
        try:
            await self._client.deregister_agent(
                self._manifest.agent_id, reason="shutdown"
            )
            logger.info(
                "Deregistered agent '%s' from %s",
                self._manifest.agent_id,
                Topics.Fleet.DEREGISTER,
            )
        except Exception as exc:  # noqa: BLE001 — boundary: log + continue
            logger.warning(
                "Failed to deregister agent '%s': %s",
                self._manifest.agent_id,
                exc,
            )

        # 5. Disconnect.
        try:
            await self._client.disconnect()
        except Exception as exc:  # noqa: BLE001 — boundary: log + continue
            logger.warning("Error during NATS disconnect: %s", exc)

        # 6. Clear ready state.
        self._ready.clear()
        logger.info("NATSAdapter stopped for agent '%s'", self._manifest.agent_id)

    # ------------------------------------------------------------------
    # Command dispatch
    # ------------------------------------------------------------------

    async def _on_command(
        self,
        envelope: MessageEnvelope,
        reply_to: str | None = None,
    ) -> None:
        """Increment the active-task counter, dispatch to the router, decrement.

        The counter is what :meth:`stop` waits on during drain — it MUST
        be decremented in a ``finally`` so a router exception cannot leak
        the count and stall shutdown.
        """
        self._active_tasks += 1
        try:
            await self._command_router.on_command(envelope, reply_to)
        finally:
            self._active_tasks -= 1

    # ------------------------------------------------------------------
    # Heartbeat
    # ------------------------------------------------------------------

    async def _heartbeat_loop(self) -> None:
        """Publish ``AgentHeartbeatPayload`` at the configured interval.

        Reads ``self._config.heartbeat_interval_seconds`` afresh each
        iteration so tests can tighten the cadence after construction
        (see the integration test). Heartbeat publish errors are logged
        but never crash the loop — a transient NATS hiccup must not kill
        the heartbeat task.
        """
        try:
            while True:
                payload = self._build_heartbeat_payload()
                try:
                    await self._client.heartbeat(payload)
                except Exception as exc:  # noqa: BLE001 — boundary: log + continue
                    logger.warning("Failed to publish heartbeat: %s", exc)
                await asyncio.sleep(self._config.heartbeat_interval_seconds)
        except asyncio.CancelledError:
            logger.debug(
                "Heartbeat loop cancelled for '%s'", self._manifest.agent_id
            )
            raise

    def _build_heartbeat_payload(self) -> AgentHeartbeatPayload:
        """Construct a heartbeat payload reflecting current status.

        Status is ``"busy"`` while any command is in flight, else
        ``"ready"``. ``uptime_seconds`` is monotonic seconds since
        ``start()``.
        """
        uptime = (
            int(time.monotonic() - self._start_time) if self._start_time else 0
        )
        status = "busy" if self._active_tasks > 0 else "ready"
        return AgentHeartbeatPayload(
            agent_id=self._manifest.agent_id,
            status=status,
            active_tasks=self._active_tasks,
            queue_depth=0,
            uptime_seconds=uptime,
        )

    # ------------------------------------------------------------------
    # nats-py lifecycle callbacks (TASK-NATS-FIX-006 / TASK-NC10)
    # ------------------------------------------------------------------

    async def _on_reconnect(self) -> None:
        """Re-publish the manifest after nats-py reconnects.

        Without this handler the agent stays absent from ``agent-registry``
        KV after a broker bounce — the container looks ``Up`` but jarvis
        dispatch can't reach it. Re-registration restores the entry and
        the heartbeat task is restarted if it died during the disconnect.

        Registration errors are logged but never re-raised — the callback
        is invoked by nats-py and a raise here would crash the network
        loop. The next reconnect (or operator restart) gets another shot.
        """
        logger.info(
            "nats_reconnected — re-registering agent '%s'",
            self._manifest.agent_id,
        )
        try:
            await self._client.register_agent(self._manifest)
        except Exception as exc:  # noqa: BLE001 — boundary: log + continue
            logger.error(
                "Failed to re-register agent '%s' on reconnect: %s",
                self._manifest.agent_id,
                exc,
            )
        # If the heartbeat task died during the disconnect, restart it so
        # the fleet sees the agent come back to ``ready`` status.
        if self._heartbeat_task is None or self._heartbeat_task.done():
            self._heartbeat_task = asyncio.create_task(
                self._heartbeat_loop(),
                name=f"heartbeat-{self._manifest.agent_id}",
            )

    async def _on_closed(self) -> None:
        """Signal terminal close — nats-py has exhausted its reconnect budget.

        Setting ``terminal_close_event`` unblocks the CLI's race in
        ``_serve_adapter`` so the process exits non-zero and Docker's
        restart policy can recover the container.

        Overrides the client's default ``_default_closed_cb`` — the
        adapter owns the structured ERROR log so it carries agent-level
        identity (``agent_id``) in addition to connection identity.
        """
        logger.error(
            "nats_terminally_closed",
            extra={
                "agent_id": self._manifest.agent_id,
                "nats_url": self._config.nats.url,
            },
        )
        self._terminal_close_event.set()

    async def _on_disconnect(self) -> None:
        """Log each transient nats-py disconnect at WARNING level.

        Pure observability — nats-py drives the reconnect loop itself.
        Structured field on the log lets the operator correlate the
        disconnect with the subsequent ``nats_reconnected`` or
        ``nats_terminally_closed`` event in the same agent.
        """
        logger.warning(
            "nats_disconnected",
            extra={"agent_id": self._manifest.agent_id},
        )
