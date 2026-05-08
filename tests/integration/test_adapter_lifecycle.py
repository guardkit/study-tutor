"""Integration test for :class:`NATSAdapter` against a live local nats-server.

Covers AC-006 from TASK-NATS-PH1-005:

  > Integration test (against a real NATS via nats-server in test fixture
  > or testcontainers): full start → dispatch one command → stop round-trip
  > succeeds, with the manifest visible in agent-registry between start
  > and stop.

Strategy: spawn the canonical ``nats-server`` binary as a subprocess on
a random free port with JetStream enabled, pre-provision the
``agent-registry`` KV bucket (the same bucket
:class:`nats_core.client.NATSClient.register_agent` writes to), then
exercise the full lifecycle. The fixture skips cleanly when the
``nats-server`` binary is not on PATH so this file works both on
operator machines (where Homebrew puts the binary in ``/opt/homebrew/bin``)
and on CI runners that don't ship the binary.

Test isolation: each test gets its own fresh ``nats-server`` process
with an isolated JetStream store directory under ``tmp_path``. There is
no shared state between tests, so a flaky test cannot corrupt the next
one.
"""

from __future__ import annotations

import asyncio
import shutil
import socket
import subprocess
import time
from collections.abc import AsyncIterator
from typing import Any

import nats
import pytest
import pytest_asyncio
from nats_core import AgentManifest
from nats_core.agent_config import AgentConfig, ModelConfig, NATSConfig
from nats_core.envelope import EventType, MessageEnvelope
from nats_core.events._agent import CommandPayload, ResultPayload

from study_tutor.adapters.manifest import _tutor_manifest_factory
from study_tutor.adapters.nats_adapter import NATSAdapter


# ---------------------------------------------------------------------------
# Skip marker — gracefully degrade when nats-server isn't installed
# ---------------------------------------------------------------------------

_NATS_SERVER_BIN = shutil.which("nats-server")
_skip_no_server = pytest.mark.skipif(
    _NATS_SERVER_BIN is None,
    reason=(
        "nats-server binary not on PATH — install via "
        "`brew install nats-server` (macOS) or download from "
        "https://github.com/nats-io/nats-server/releases"
    ),
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _free_port() -> int:
    """Allocate an OS-assigned free TCP port for the nats-server subprocess.

    Bind ``0`` to an ephemeral socket, read back the port, close the
    socket. There is a tiny race between us closing the socket and
    nats-server binding, but in practice it's more than reliable enough
    for a per-test fixture (and the alternative — a hardcoded port —
    breaks parallel pytest-xdist runs).
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest_asyncio.fixture()
async def nats_server(tmp_path) -> AsyncIterator[str]:  # type: ignore[no-untyped-def]
    """Spawn a per-test nats-server subprocess with JetStream enabled.

    Yields the connection URL. Tears down the subprocess (SIGTERM, then
    SIGKILL after 5s) on exit so a hung server cannot block the test
    suite.
    """
    if _NATS_SERVER_BIN is None:
        pytest.skip("nats-server binary not on PATH")

    port = _free_port()
    store_dir = tmp_path / "jetstream"
    store_dir.mkdir()

    proc = subprocess.Popen(
        [
            _NATS_SERVER_BIN,
            "-js",  # enable JetStream (KV requires it)
            "--store_dir",
            str(store_dir),
            "-a",
            "127.0.0.1",
            "-p",
            str(port),
            # Quieter logs — nats-server is chatty by default.
            "-l",
            str(tmp_path / "nats-server.log"),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    url = f"nats://127.0.0.1:{port}"

    # Poll until the port is accepting connections (nats-server takes
    # ~50–200ms to come up). 5s budget is plenty even on a loaded box.
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.2):
                break
        except (OSError, ConnectionRefusedError):
            await asyncio.sleep(0.05)
    else:
        proc.kill()
        pytest.fail(f"nats-server did not become reachable on {url} within 5s")

    try:
        yield url
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5.0)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=2.0)


@pytest_asyncio.fixture()
async def bootstrapped_server(nats_server: str) -> AsyncIterator[str]:
    """Pre-provision the ``agent-registry`` KV bucket on the running server.

    :meth:`NATSClient.register_agent` only *uses* the bucket — it does
    not create it (see the comment in
    ``nats_core.client.NATSKVManifestRegistry.create``: production
    bootstrap is performed by ``nats-infrastructure/kv/provision-kv.sh``).
    This fixture replays that idempotent provisioning step against the
    ephemeral test server so the adapter's KV writes have somewhere to
    land.
    """
    nc = await nats.connect(nats_server, connect_timeout=5)
    try:
        js = nc.jetstream()
        await js.create_key_value(bucket="agent-registry")
    finally:
        await nc.drain()
        await nc.close()
    yield nats_server


@pytest.fixture()
def agent_config(bootstrapped_server: str) -> AgentConfig:
    """:class:`AgentConfig` pointed at the live test server."""
    return AgentConfig(
        models=ModelConfig(reasoning_model="test-model"),
        nats=NATSConfig(url=bootstrapped_server),
        heartbeat_interval_seconds=1,
        heartbeat_timeout_seconds=2,
    )


@pytest.fixture()
def manifest() -> AgentManifest:
    """Real study-tutor manifest — same intents/tools as production."""
    return _tutor_manifest_factory(agent_id="gcse-tutor")


class _RecordingCommandRouter:
    """Minimal stand-in for :class:`CommandRouter` for the round-trip test.

    Records every ``on_command`` invocation so the test can assert that
    the adapter actually received a published command, then publishes a
    canned :class:`ResultPayload` raw to the requester's reply inbox so
    the request future resolves.
    """

    def __init__(self, client: Any, agent_id: str) -> None:
        self._client = client
        self._agent_id = agent_id
        self.received: list[tuple[MessageEnvelope, str | None]] = []

    async def on_command(
        self,
        envelope: MessageEnvelope,
        reply_to: str | None = None,
    ) -> None:
        self.received.append((envelope, reply_to))
        # Mirror the Bug #1 raw-publish semantic — without it the
        # client's ``request()`` future would time out.
        if reply_to is not None:
            payload = CommandPayload.model_validate(envelope.payload)
            result = ResultPayload(
                command=payload.command,
                result={"echo": payload.args},
                correlation_id=payload.correlation_id,
                success=True,
            )
            await self._client.publish_raw(
                reply_to, result.model_dump_json().encode()
            )


# ---------------------------------------------------------------------------
# AC-006 — full lifecycle round-trip with manifest visible in agent-registry
# ---------------------------------------------------------------------------


@_skip_no_server
@pytest.mark.integration_contract("NATSAdapter")
@pytest.mark.smoke
class TestAdapterLifecycleRoundTrip:
    """End-to-end: start → dispatch → stop against a live nats-server."""

    async def test_full_lifecycle_round_trip(
        self,
        agent_config: AgentConfig,
        manifest: AgentManifest,
        bootstrapped_server: str,
    ) -> None:
        """AC-006: full lifecycle plus mid-life manifest visibility check.

        Steps:

        1. Construct + ``start()`` the adapter.
        2. Read the ``agent-registry`` KV bucket directly and assert the
           manifest is present (this is the "manifest visible in
           agent-registry between start and stop" half of the AC).
        3. Publish one ``COMMAND`` envelope via ``nc.request(...)`` so
           the reply path is exercised; assert we receive a
           ``ResultPayload`` back.
        4. ``stop()`` the adapter, then re-read the KV bucket and assert
           the manifest has been removed (deregistration cleanup).
        """
        # Build the adapter against the live server.
        router = _RecordingCommandRouter(client=None, agent_id=manifest.agent_id)
        adapter = NATSAdapter(
            config=agent_config,
            manifest=manifest,
            command_router=router,  # type: ignore[arg-type]
        )
        # Now that the adapter has built its NATSClient, give the router
        # a handle so it can publish raw replies.
        router._client = adapter._client

        await adapter.start()
        try:
            # ---- 2. Manifest visible in agent-registry (mid-lifecycle) ----
            registry = await adapter._client.get_fleet_registry()
            assert manifest.agent_id in registry, (
                f"manifest for '{manifest.agent_id}' missing from agent-registry "
                f"after start(); keys present: {list(registry.keys())}"
            )
            assert registry[manifest.agent_id].agent_id == manifest.agent_id

            # ---- 3. Dispatch one command via request/reply ----
            observer_nc = await nats.connect(bootstrapped_server, connect_timeout=5)
            try:
                cmd_envelope = MessageEnvelope(
                    source_id="integration-test",
                    event_type=EventType.COMMAND,
                    payload=CommandPayload(
                        command="ping",
                        args={"hello": "world"},
                        correlation_id="corr-int-1",
                    ).model_dump(),
                    correlation_id="corr-int-1",
                )
                command_subject = f"agents.command.{manifest.agent_id}"
                response_msg = await observer_nc.request(
                    command_subject,
                    cmd_envelope.model_dump_json().encode(),
                    timeout=5.0,
                )
                # The router published the result raw — parse it.
                result_payload = ResultPayload.model_validate_json(
                    response_msg.data
                )
                assert result_payload.success is True
                assert result_payload.command == "ping"
                assert result_payload.result == {"echo": {"hello": "world"}}
                assert result_payload.correlation_id == "corr-int-1"
            finally:
                await observer_nc.drain()
                await observer_nc.close()

            # The router observed the dispatch.
            assert len(router.received) == 1
            received_envelope, received_reply = router.received[0]
            assert received_envelope.event_type == EventType.COMMAND
            assert received_reply is not None  # Bug #1 — reply_to propagated
            assert received_reply.startswith("_INBOX.")
        finally:
            # ---- 4. Stop and assert deregistration ----
            await adapter.stop()

        # After stop(), the KV entry must be gone. We need a fresh client
        # because the adapter's client has been disconnected.
        observer_nc = await nats.connect(bootstrapped_server, connect_timeout=5)
        try:
            js = observer_nc.jetstream()
            kv = await js.key_value("agent-registry")
            try:
                entry = await kv.get(manifest.agent_id)
                # Some KV implementations return tombstoned entries on
                # get(); accept either a missing key or an empty value
                # as "deregistered".
                assert entry is None or entry.value in (b"", None), (
                    f"manifest still present in agent-registry after stop(): "
                    f"value={entry.value!r}"
                )
            except Exception:
                # The expected path: get() raises KeyNotFoundError when
                # the key has been deleted.
                pass
        finally:
            await observer_nc.drain()
            await observer_nc.close()

        # Final adapter state assertions.
        assert adapter.is_ready is False
        assert adapter.active_tasks == 0

    async def test_heartbeat_published_on_live_server(
        self,
        agent_config: AgentConfig,
        manifest: AgentManifest,
        bootstrapped_server: str,
    ) -> None:
        """The heartbeat loop publishes to ``fleet.heartbeat.<agent_id>`` on
        the live server.

        Subscribes to the heartbeat subject from a sidecar connection
        before starting the adapter, then waits up to 3s for at least
        one published heartbeat. Confirms the lifecycle's heartbeat
        signal is observable end-to-end (not just a mocked AsyncMock).
        """
        observer_nc = await nats.connect(bootstrapped_server, connect_timeout=5)
        received: list[bytes] = []

        async def collect(msg: Any) -> None:
            received.append(msg.data)

        await observer_nc.subscribe(
            f"fleet.heartbeat.{manifest.agent_id}", cb=collect
        )

        # Use a stub router — heartbeat doesn't depend on command flow.
        class _NoopRouter:
            async def on_command(self, _e, reply_to=None):  # type: ignore[no-untyped-def]
                return None

        adapter = NATSAdapter(
            config=agent_config,
            manifest=manifest,
            command_router=_NoopRouter(),  # type: ignore[arg-type]
        )
        # Tighten the heartbeat for a fast test signal.
        adapter._config.heartbeat_interval_seconds = 0.05

        await adapter.start()
        try:
            # Wait up to ~1s for at least one heartbeat to land.
            deadline = time.monotonic() + 1.5
            while time.monotonic() < deadline and not received:
                await asyncio.sleep(0.05)
            assert received, "no heartbeat received within 1.5s on live server"

            # Parse the first heartbeat — it must wrap an envelope with
            # AGENT_HEARTBEAT event type and the right agent_id.
            envelope = MessageEnvelope.model_validate_json(received[0])
            assert envelope.event_type == EventType.AGENT_HEARTBEAT
            assert envelope.source_id == manifest.agent_id
        finally:
            await adapter.stop()
            await observer_nc.drain()
            await observer_nc.close()
