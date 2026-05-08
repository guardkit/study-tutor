"""Phase 2 KV-watch lifecycle test for ``NATSKVManifestRegistry``.

Covers TASK-NATS-PH2-002 (FEAT-NATS, wave 8). Phase 1's discovery test
(``tests/integration/test_adapter_lifecycle.py``) only verifies the KV
*state* mid-lifecycle. This file verifies that subscribers to the
``agent-registry`` KV bucket see ``PUT`` / ``DEL`` *events* synchronously
when the tutor adapter registers and deregisters — important because
jarvis's :class:`LiveCapabilitiesRegistry` caches resolution decisions
and a stale cache combined with a missed dereg event = ghost agent.

The KV-watch path is exercised via ``nats-py``'s ``kv.watch()`` directly
(per the task's implementation notes — ``nats_core.NATSClient`` exposes
``watch_fleet`` for the callback-style API but the test prefers the
underlying iterator so we can collect events into a list and assert on
ordering and timing without smuggling state through callback closures).

Coverage map:

* AC-001: PUT event observed within 5s of ``adapter.start()``
* AC-002: DEL/PURGE event observed within 5s of ``adapter.stop()``
* AC-003: SIGKILL-equivalent abandonment leaves the KV row present
  (no TTL cleanup) — this is the documentation-of-known-limitation that
  justifies TASK-NATS-FU-002 (jarvis-side reaper). The test does **not**
  use ``os.kill`` because the adapter runs in-process: instead we cancel
  the heartbeat task and forcibly close the underlying NATS connection
  without invoking ``stop()``. This is semantically equivalent to the
  external SIGKILL path — neither sends ``fleet.deregister`` nor deletes
  the KV entry — and is safer to run inside the pytest process. The
  task's reference to ``os.kill`` against a subprocess pid is the
  prescribed shape *if* the adapter is run out-of-process; the
  in-process equivalent is captured in :meth:`_simulate_sigkill`.

Test isolation: each test gets its own per-process ``nats-server`` with
an isolated JetStream store under ``tmp_path``, so a flaky test cannot
poison the next one's KV bucket.
"""

from __future__ import annotations

import asyncio
import contextlib
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

from study_tutor.adapters.manifest import _tutor_manifest_factory
from study_tutor.adapters.nats_adapter import NATSAdapter

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Agent id used by every test in this file. Matches the production
#: tutor manifest so the watcher predicate is identical to what jarvis
#: would see in real life.
_TUTOR_AGENT_ID = "gcse-tutor"

#: Per-acceptance-criteria event-observation budget. AC-001 / AC-002
#: both stipulate "within 5s"; we honour that exactly. The local
#: nats-server fixture typically delivers KV-watch events in <100ms so
#: this is a generous ceiling, not a target.
_EVENT_TIMEOUT_SECONDS = 5.0

#: Set of KV-watch operations that count as "deregistration" for the
#: purposes of AC-002. nats-py emits ``DEL`` for ``kv.delete()`` and
#: ``PURGE`` for ``kv.purge()`` — the manifest registry uses
#: ``kv.delete()`` today, but we accept both so a future tightening of
#: the registry's cleanup semantics (purge to remove tombstones) does
#: not break this test.
_DEREGISTRATION_OPS: frozenset[str] = frozenset({"DEL", "PURGE"})

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
# Fixtures (mirrors test_adapter_lifecycle.py — shared shape, isolated state)
# ---------------------------------------------------------------------------


def _free_port() -> int:
    """Allocate an OS-assigned free TCP port for the nats-server subprocess.

    Bind ``0`` to an ephemeral socket, read the assigned port, then
    close. There is a small race between us closing and nats-server
    binding, but it's adequate for a per-test fixture and the
    alternative — a hardcoded port — breaks parallel pytest-xdist runs.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest_asyncio.fixture()
async def nats_server(tmp_path) -> AsyncIterator[str]:  # type: ignore[no-untyped-def]
    """Spawn a per-test ``nats-server`` subprocess with JetStream enabled.

    Yields the connection URL. Tears down the subprocess (SIGTERM, then
    SIGKILL after 5s) on exit so a hung server cannot block the suite.
    """
    if _NATS_SERVER_BIN is None:
        pytest.skip("nats-server binary not on PATH")

    port = _free_port()
    store_dir = tmp_path / "jetstream"
    store_dir.mkdir()

    proc = subprocess.Popen(
        [
            _NATS_SERVER_BIN,
            "-js",  # JetStream is mandatory — KV is built on it
            "--store_dir",
            str(store_dir),
            "-a",
            "127.0.0.1",
            "-p",
            str(port),
            "-l",
            str(tmp_path / "nats-server.log"),
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    url = f"nats://127.0.0.1:{port}"

    # Wait for the listener to come up (~50–200ms typically).
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
    not create it. Production bootstrap is performed by
    ``nats-infrastructure/kv/provision-kv.sh``; this fixture replays
    that idempotent provisioning step against the ephemeral test
    server so the adapter's KV writes have somewhere to land.
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
    """:class:`AgentConfig` pointed at the live test server.

    The heartbeat interval is held at 1s — KV-watch events fire on
    register / deregister regardless, so a short heartbeat doesn't
    affect the AC, but keeping it shortish ensures any sidecar
    consumers that gate on heartbeat freshness don't time out
    spuriously during the (~few-second) test.
    """
    return AgentConfig(
        models=ModelConfig(reasoning_model="test-model"),
        nats=NATSConfig(url=bootstrapped_server),
        heartbeat_interval_seconds=1,
        heartbeat_timeout_seconds=2,
    )


@pytest.fixture()
def manifest() -> AgentManifest:
    """Real study-tutor manifest — same intents/tools as production."""
    return _tutor_manifest_factory(agent_id=_TUTOR_AGENT_ID)


class _NoopRouter:
    """Stub :class:`CommandRouter` for tests that exercise lifecycle only.

    The KV-watch tests don't dispatch commands — they observe
    registration / deregistration events — so this no-op handler is
    sufficient. Mirrors the ``_NoopRouter`` pattern from the heartbeat
    test in ``test_adapter_lifecycle.py`` rather than the recording
    router (which would be dead-letter weight here).
    """

    async def on_command(
        self,
        _envelope: Any,
        reply_to: str | None = None,
    ) -> None:
        return None


# ---------------------------------------------------------------------------
# KV-watch helper — collects events into a list with a background task
# ---------------------------------------------------------------------------


class _KVEventCollector:
    """Background-task wrapper around ``kv.watch()`` that records events.

    nats-py's ``kv.watch()`` returns an async iterator that yields
    :class:`KeyValue.Entry` objects (and ``None`` once initial state
    has been delivered — the "init done" marker). This helper drives
    the iterator on a background task, filters out the init marker,
    and exposes the list of recorded events under an asyncio.Event so
    tests can wait for the next event without busy-looping.

    Why a class and not an inline coroutine: the tests need to assert
    on event ordering (PUT before DEL), so we keep an in-order list
    and a "wait until at least N events" primitive. A bare callback
    would force every test to roll its own predicate loop.
    """

    def __init__(self, kv: Any, key_filter: str) -> None:
        self._kv = kv
        self._key_filter = key_filter
        self._events: list[tuple[str, str, bytes | None]] = []
        self._wakeup = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._watcher: Any | None = None

    @property
    def events(self) -> list[tuple[str, str, bytes | None]]:
        """Snapshot of recorded ``(operation, key, value)`` tuples."""
        return list(self._events)

    async def start(self) -> None:
        """Begin watching the bucket on a background task.

        Returns once the watcher is created — but the watcher's "init
        done" marker may not have arrived yet. Tests that need a clean
        baseline should call :meth:`drain_initial_state` after start.
        """
        # Watch all keys (">" wildcard) and ignore the init-done marker
        # via filtering inside the loop. Watching all keys (instead of
        # ``self._key_filter``) ensures the test would catch a
        # cross-talk regression where some other agent_id leaks into
        # the bucket.
        self._watcher = await self._kv.watch(">")
        self._task = asyncio.create_task(self._consume(), name="kv-watch-collector")

    async def _consume(self) -> None:
        """Drain the watcher iterator into ``self._events`` until cancelled."""
        assert self._watcher is not None
        try:
            async for entry in self._watcher:
                # nats-py yields ``None`` exactly once after initial
                # state has been delivered. Skip — we only care about
                # subsequent live events.
                if entry is None:
                    self._wakeup.set()
                    continue
                # Operation is one of "PUT", "DEL", "PURGE".
                op = getattr(entry, "operation", "PUT") or "PUT"
                value = getattr(entry, "value", None)
                self._events.append((op, entry.key, value))
                # Wake any waiting test thread.
                self._wakeup.set()
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001 — boundary catch
            # The watcher disconnects when the connection closes; the
            # test owns the lifetime of both, so we treat any other
            # exception as benign loop exit. Tests assert on
            # self.events directly.
            return

    async def wait_for(
        self,
        predicate: Any,
        timeout: float,
    ) -> tuple[str, str, bytes | None] | None:
        """Wait up to ``timeout`` seconds for an event matching ``predicate``.

        Args:
            predicate: ``Callable[[tuple[str, str, bytes | None]], bool]``
                — returns ``True`` for the desired event.
            timeout: Wall-clock seconds to wait.

        Returns:
            The matching event tuple, or ``None`` if the deadline
            elapses without a match.
        """
        deadline = time.monotonic() + timeout
        # Walk previously-recorded events first (the event of interest
        # may have already arrived between the call site and us).
        scanned = 0
        while True:
            current = self.events
            for event in current[scanned:]:
                if predicate(event):
                    return event
            scanned = len(current)

            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return None

            self._wakeup.clear()
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._wakeup.wait(), timeout=remaining)

    async def stop(self) -> None:
        """Cancel the background task and tear down the watcher."""
        if self._task is not None:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
            self._task = None
        if self._watcher is not None:
            with contextlib.suppress(Exception):
                await self._watcher.stop()
            self._watcher = None


# ---------------------------------------------------------------------------
# Tests — AC-001, AC-002, AC-003
# ---------------------------------------------------------------------------


@_skip_no_server
@pytest.mark.integration_contract("NATSKVManifestRegistry")
@pytest.mark.smoke
class TestKVWatchLifecycleEvents:
    """KV-watch sees register *and* deregister events synchronously."""

    async def test_register_emits_put_event_within_budget(
        self,
        agent_config: AgentConfig,
        manifest: AgentManifest,
        bootstrapped_server: str,
    ) -> None:
        """AC-001: PUT for ``gcse-tutor`` arrives within 5s of ``start()``.

        Subscribes to KV-watch *before* the adapter starts so the
        register is observed live (not as a replay of the bucket's
        initial state). Then asserts the first PUT event for the
        tutor's agent_id arrives within ``_EVENT_TIMEOUT_SECONDS``.
        """
        observer_nc = await nats.connect(bootstrapped_server, connect_timeout=5)
        try:
            js = observer_nc.jetstream()
            kv = await js.key_value("agent-registry")
            collector = _KVEventCollector(kv=kv, key_filter=_TUTOR_AGENT_ID)
            await collector.start()
            try:
                adapter = NATSAdapter(
                    config=agent_config,
                    manifest=manifest,
                    command_router=_NoopRouter(),  # type: ignore[arg-type]
                )
                await adapter.start()
                try:
                    event = await collector.wait_for(
                        lambda evt: evt[0] == "PUT" and evt[1] == _TUTOR_AGENT_ID,
                        timeout=_EVENT_TIMEOUT_SECONDS,
                    )
                    assert event is not None, (
                        f"no PUT event for '{_TUTOR_AGENT_ID}' observed "
                        f"within {_EVENT_TIMEOUT_SECONDS}s of start(); "
                        f"events seen: {collector.events}"
                    )
                    op, key, value = event
                    assert op == "PUT"
                    assert key == _TUTOR_AGENT_ID
                    # The value must round-trip through AgentManifest —
                    # an empty / corrupt PUT would let jarvis cache a
                    # broken manifest.
                    assert value is not None and value != b""
                    parsed = AgentManifest.model_validate_json(value)
                    assert parsed.agent_id == _TUTOR_AGENT_ID
                finally:
                    await adapter.stop()
            finally:
                await collector.stop()
        finally:
            await observer_nc.drain()
            await observer_nc.close()

    async def test_graceful_stop_emits_delete_event_within_budget(
        self,
        agent_config: AgentConfig,
        manifest: AgentManifest,
        bootstrapped_server: str,
    ) -> None:
        """AC-002: DEL/PURGE for ``gcse-tutor`` arrives within 5s of ``stop()``.

        Boots the adapter, waits for the PUT to settle, then calls
        ``stop()`` and asserts a deregistration-class event arrives
        within ``_EVENT_TIMEOUT_SECONDS``.
        """
        observer_nc = await nats.connect(bootstrapped_server, connect_timeout=5)
        try:
            js = observer_nc.jetstream()
            kv = await js.key_value("agent-registry")
            collector = _KVEventCollector(kv=kv, key_filter=_TUTOR_AGENT_ID)
            await collector.start()
            try:
                adapter = NATSAdapter(
                    config=agent_config,
                    manifest=manifest,
                    command_router=_NoopRouter(),  # type: ignore[arg-type]
                )
                await adapter.start()

                # Settle PUT first so the DEL assertion isn't ambiguous.
                put_event = await collector.wait_for(
                    lambda evt: evt[0] == "PUT" and evt[1] == _TUTOR_AGENT_ID,
                    timeout=_EVENT_TIMEOUT_SECONDS,
                )
                assert put_event is not None, (
                    "PUT event must precede graceful stop test"
                )

                # Snapshot the count so we don't match the prior PUT.
                events_before_stop = len(collector.events)

                await adapter.stop()

                del_event = await collector.wait_for(
                    lambda evt: evt[0] in _DEREGISTRATION_OPS
                    and evt[1] == _TUTOR_AGENT_ID,
                    timeout=_EVENT_TIMEOUT_SECONDS,
                )
                assert del_event is not None, (
                    f"no DEL/PURGE event for '{_TUTOR_AGENT_ID}' observed "
                    f"within {_EVENT_TIMEOUT_SECONDS}s of stop(); "
                    f"events since stop(): "
                    f"{collector.events[events_before_stop:]}"
                )
                assert del_event[0] in _DEREGISTRATION_OPS
                assert del_event[1] == _TUTOR_AGENT_ID
            finally:
                await collector.stop()
        finally:
            await observer_nc.drain()
            await observer_nc.close()

    async def test_sigkill_equivalent_leaves_stale_row(
        self,
        agent_config: AgentConfig,
        manifest: AgentManifest,
        bootstrapped_server: str,
    ) -> None:
        """AC-003: abandoning the adapter (SIGKILL-equivalent) leaves the row.

        Documents Decision 3 (2026-05-08): there is no automatic TTL
        cleanup on the ``agent-registry`` bucket. A jarvis-side reaper
        (TASK-NATS-FU-002) is required to evict stale rows. This test
        is the regression guard that catches a future change which
        accidentally introduces TTL — at which point this test would
        fail and force a cross-fleet design review.

        Implementation note: the task spec mentions
        ``os.kill(adapter._task.pid, signal.SIGKILL)`` against a
        subprocess fixture. We run the adapter in-process here; the
        in-process equivalent of "no graceful stop" is to cancel the
        heartbeat task and forcibly close the underlying NATS
        connection without invoking ``adapter.stop()`` (which is what
        publishes ``fleet.deregister`` and deletes the KV entry). The
        end state — a bucket entry with no corresponding live process
        — is identical to the SIGKILL case.
        """
        adapter = NATSAdapter(
            config=agent_config,
            manifest=manifest,
            command_router=_NoopRouter(),  # type: ignore[arg-type]
        )
        await adapter.start()

        # Sanity check: the row must be present after start(), otherwise
        # the AC-003 assertion is vacuous.
        assert _TUTOR_AGENT_ID in await adapter._client.get_fleet_registry()

        try:
            await self._simulate_sigkill(adapter)

            # After abandonment, the row must STILL be present — there
            # is no TTL cleanup. Read with a fresh observer connection
            # because the adapter's connection is now closed.
            observer_nc = await nats.connect(bootstrapped_server, connect_timeout=5)
            try:
                js = observer_nc.jetstream()
                kv = await js.key_value("agent-registry")
                # Brief settle window so the registry's last write is
                # durable on disk before we read. JetStream's KV is
                # usually consistent within a single round-trip but we
                # don't want a transient flake on a loaded CI node to
                # mask a real regression.
                await asyncio.sleep(0.2)
                entry = await kv.get(_TUTOR_AGENT_ID)
                assert entry is not None, (
                    "stale row must remain after SIGKILL-equivalent abandonment "
                    f"(Decision 3, 2026-05-08); got entry={entry!r}"
                )
                assert entry.value not in (b"", None), (
                    "stale row value must be the original manifest payload, "
                    f"not a tombstone; got value={entry.value!r}"
                )
                stale_manifest = AgentManifest.model_validate_json(entry.value)
                assert stale_manifest.agent_id == _TUTOR_AGENT_ID
            finally:
                await observer_nc.drain()
                await observer_nc.close()
        finally:
            # Defence-in-depth cleanup: even though the connection is
            # already closed, ensure no asyncio task leaks.
            if (
                adapter._heartbeat_task is not None
                and not adapter._heartbeat_task.done()
            ):
                adapter._heartbeat_task.cancel()
                with contextlib.suppress(asyncio.CancelledError, Exception):
                    await adapter._heartbeat_task

    @staticmethod
    async def _simulate_sigkill(adapter: NATSAdapter) -> None:
        """Force-kill an in-process adapter without invoking ``stop()``.

        Cancels the heartbeat task (so it doesn't keep publishing into
        a doomed connection and spam the test log) and closes the
        underlying NATS connection abruptly. The deregister path is
        deliberately NOT taken — that's the whole point of the test.
        """
        # 1. Stop the heartbeat task so it doesn't try to publish onto
        #    a torn-down connection during teardown.
        if adapter._heartbeat_task is not None:
            adapter._heartbeat_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await adapter._heartbeat_task
            adapter._heartbeat_task = None

        # 2. Forcibly close the NATS connection with no drain — the
        #    nats-py ``close()`` call mirrors what happens when the
        #    process dies abruptly (kernel reclaims the socket; no
        #    final messages flushed).
        client = adapter._client
        nc = getattr(client, "_nc", None)
        if nc is not None:
            with contextlib.suppress(Exception):
                await nc.close()
