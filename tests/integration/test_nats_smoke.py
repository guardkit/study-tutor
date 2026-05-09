"""Integration smoke test (TASK-NATS-PH1-008) — all 4 tutor commands round-trip
through the NATS adapter without PubAck leakage.

This is the gate that proves the canonical NATS contract is wired correctly
before TASK-NATS-PH1-010 (the operator-driven E2E demo).

Specifically guards against:

* **Bug #1** — PubAck leakage on the request inbox. The router's
  ``_publish_result`` dual-publish path must raw-publish the
  :class:`ResultPayload` to ``msg.reply`` so jarvis's ``nc.request()``
  future resolves with the actual result, not the JetStream
  ``{"stream":..., "seq":...}`` PubAck. Both the inbox raw-publish AND the
  canonical ``agents.result.<agent_id>`` envelope publish must fire on
  every dispatch.
* **Bug #2** — ``tool_to_command`` alias miss. Incoming command names like
  ``tutor_start_session`` (the MCP tool name) must resolve to canonical
  commands (``start_session``) before the router's dispatch table is
  consulted. Both alias and canonical forms must succeed.

Strategy: spawn a per-test ``nats-server`` subprocess (mirrors
:mod:`tests.integration.test_adapter_lifecycle`), provision the
``agent-registry`` KV bucket, then boot a real :class:`NATSAdapter` with a
real :class:`CommandRouter` wrapping a stub MCP adapter. The stub returns
canned dicts so the smoke test does not depend on an LLM provider or
Graphiti — the contract under test is the **NATS wire path**, not the
tutoring business logic.
"""

from __future__ import annotations

import asyncio
import json
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

from study_tutor.adapters.command_router import CommandRouter
from study_tutor.adapters.manifest import _tutor_manifest_factory
from study_tutor.adapters.nats_adapter import NATSAdapter
from study_tutor.roles.tutor import TOOL_TO_COMMAND


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
# Constants — agent_id is hardcoded so the wire-tap subject matches the
# canonical FEAT-NATS topic shape exactly. Using the flat subject (not
# the wildcard `agents.result.gcse-tutor.>`) per the task implementation
# note: the wildcard pattern returns 0 envelopes (Bug #4).
# ---------------------------------------------------------------------------

AGENT_ID = "gcse-tutor"
RESULT_SUBJECT = f"agents.result.{AGENT_ID}"


# ---------------------------------------------------------------------------
# Stub MCP adapter — returns canned dicts so the smoke test never touches
# an LLM provider or Graphiti. The CommandRouter only requires that the
# adapter expose four awaitable methods with matching names; Python's
# duck typing means a real :class:`MCPAdapter` subclass is unnecessary.
# ---------------------------------------------------------------------------


class _StubMCPAdapter:
    """Minimal stand-in for :class:`study_tutor.mcp.adapter.MCPAdapter`.

    Records every invocation so the test can audit which canonical
    command name the router dispatched into. Returns canned dicts that
    mirror the real adapter's return shape closely enough for the smoke
    gate (``ResultPayload`` doesn't validate the inner ``result`` dict —
    it accepts arbitrary key/value content).
    """

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    async def tutor_start_session(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("tutor_start_session", kwargs))
        return {
            "session_id": "stub-session-id",
            "plan_summary": {"topic_name": "stub-topic"},
        }

    async def tutor_turn(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("tutor_turn", kwargs))
        return {"tutor_response": "stub response"}

    async def tutor_session_status(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("tutor_session_status", kwargs))
        return {
            "session_id": kwargs.get("session_id", "stub"),
            "status": "active",
            "turn_count": 0,
            "started_at": "2026-05-08T00:00:00+00:00",
        }

    async def tutor_session_end(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("tutor_session_end", kwargs))
        return {
            "session_id": kwargs.get("session_id", "stub"),
            "status": "ended",
        }


class _BootstrapRouter:
    """Placeholder router used during :class:`NATSAdapter` construction.

    The real :class:`CommandRouter` needs ``adapter._client`` to publish
    results, but the adapter constructs that client inside its own
    ``__init__``. We bootstrap with this no-op router so the adapter
    can be built, then late-bind the real router onto
    ``adapter._command_router`` before ``start()`` arms the subscription.
    Mirrors the late-bind pattern in
    :mod:`tests.integration.test_adapter_lifecycle`.
    """

    async def on_command(
        self,
        envelope: MessageEnvelope,
        reply_to: str | None = None,
    ) -> None:  # pragma: no cover — never invoked
        return None


# ---------------------------------------------------------------------------
# Fixtures: nats-server subprocess + KV provisioning + adapter stack
# ---------------------------------------------------------------------------


def _free_port() -> int:
    """Allocate an OS-assigned free TCP port for the nats-server subprocess."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest_asyncio.fixture()
async def nats_server(tmp_path) -> AsyncIterator[str]:  # type: ignore[no-untyped-def]
    """Spawn a per-test nats-server subprocess with JetStream enabled.

    Yields the connection URL. Tears the subprocess down on exit so a
    hung server cannot block the test suite.
    """
    if _NATS_SERVER_BIN is None:
        pytest.skip("nats-server binary not on PATH")

    port = _free_port()
    store_dir = tmp_path / "jetstream"
    store_dir.mkdir()

    proc = subprocess.Popen(
        [
            _NATS_SERVER_BIN,
            "-js",
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

    # Poll until the port accepts connections (~50–200ms cold start).
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
    """Pre-provision the ``agent-registry`` KV bucket on the test server.

    :meth:`NATSClient.register_agent` *uses* the bucket — it does not
    create it — so we replay the production bootstrap step against the
    ephemeral test server before the adapter starts.
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
    return _tutor_manifest_factory(agent_id=AGENT_ID)


@pytest_asyncio.fixture()
async def tutor_adapter(
    agent_config: AgentConfig,
    manifest: AgentManifest,
) -> AsyncIterator[tuple[NATSAdapter, _StubMCPAdapter]]:
    """Boot the full NATSAdapter + CommandRouter + stub MCP stack.

    Yields ``(adapter, stub)`` so tests can both dispatch via NATS *and*
    audit which canonical command the router invoked on the underlying
    business-logic seam (the AC-004 / AC-005 alias-vs-canonical proof).

    Construction order is load-bearing:

    1. Build the adapter with a :class:`_BootstrapRouter` so the adapter
       can construct its internal :class:`NATSClient`.
    2. Build the real :class:`CommandRouter` against ``adapter._client``
       so the dual-publish path (Bug #1) shares the agent's connection.
    3. Swap ``adapter._command_router`` to the real router.
    4. ``await adapter.start()`` — by this point the router is the real
       one, so the subscription's ``_on_command`` callback will dispatch
       through the production code path.
    """
    stub = _StubMCPAdapter()
    adapter = NATSAdapter(
        config=agent_config,
        manifest=manifest,
        command_router=_BootstrapRouter(),  # type: ignore[arg-type]
    )
    real_router = CommandRouter(
        mcp_adapter=stub,  # type: ignore[arg-type]  — duck-typed stub
        tool_to_command=TOOL_TO_COMMAND,
        agent_id=manifest.agent_id,
        client=adapter._client,
    )
    adapter._command_router = real_router

    await adapter.start()
    try:
        # Defensive: wait for ``_ready`` so the subscription is armed
        # before any test publishes a command envelope.
        await asyncio.wait_for(adapter._ready.wait(), timeout=5.0)
        yield adapter, stub
    finally:
        await adapter.stop()


# ---------------------------------------------------------------------------
# Per-command argument map. Keyed by canonical command name (post alias
# resolution) so the parametrised test can look up args by the resolved
# name regardless of which on-the-wire form (alias or canonical) is being
# exercised this iteration.
# ---------------------------------------------------------------------------


def _args_for(canonical_command: str) -> dict[str, Any]:
    """Build the minimal ``args`` payload for each canonical command."""
    if canonical_command == "start_session":
        return {"student_id": "lilymay"}
    if canonical_command == "tutor_turn":
        return {"session_id": "stub-session-id", "user_message": "hi"}
    if canonical_command == "session_status":
        return {"session_id": "stub-session-id"}
    if canonical_command == "end_session":
        return {"session_id": "stub-session-id"}
    raise ValueError(f"unknown canonical command: {canonical_command}")


# Mapping: canonical command (post alias resolution) -> stub method that
# CommandRouter dispatches into. Mirrors the router's ``_command_map``
# handler-to-MCPAdapter-method routing so the test can audit that the
# stub saw the correct method invocation.
_CANONICAL_TO_STUB_METHOD: dict[str, str] = {
    "start_session": "tutor_start_session",
    "tutor_turn": "tutor_turn",
    "session_status": "tutor_session_status",
    "end_session": "tutor_session_end",
}


# Parametrise: (wire_command, canonical_command). The wire form covers
# both Bug #2 alias paths AND the canonical passthrough; the canonical
# form is supplied alongside so each iteration knows which args to send
# and which stub method to expect.
_COMMANDS: list[tuple[str, str]] = [
    # AC-004 — Alias form (Bug #2 regression guard). All 4 MCP tool names.
    ("tutor_start_session", "start_session"),
    ("tutor_turn", "tutor_turn"),
    ("tutor_session_status", "session_status"),
    ("tutor_session_end", "end_session"),
    # AC-005 — Canonical form (passthrough behaviour). ``tutor_turn`` is
    # already covered above (alias and canonical names are identical),
    # so list only the three commands whose canonical form differs.
    ("start_session", "start_session"),
    ("session_status", "session_status"),
    ("end_session", "end_session"),
]


# ---------------------------------------------------------------------------
# AC-001..AC-005 — round-trip + Bug #1 + Bug #2 regression guards
# ---------------------------------------------------------------------------


@_skip_no_server
@pytest.mark.smoke
@pytest.mark.integration_contract("NATSAdapter")
class TestSmokeFourCommands:
    """End-to-end smoke for the FEAT-NATS Phase-1 tutor wire path."""

    @pytest.mark.parametrize(
        ("wire_command", "canonical_command"),
        _COMMANDS,
        ids=[f"{w}->{c}" for w, c in _COMMANDS],
    )
    async def test_command_round_trip(
        self,
        wire_command: str,
        canonical_command: str,
        tutor_adapter: tuple[NATSAdapter, _StubMCPAdapter],
        bootstrapped_server: str,
    ) -> None:
        """Dispatch one command via ``nc.request`` and assert the contract.

        Asserts (per the task's acceptance criteria):

        * **AC-001** — The reply parses as :class:`ResultPayload` with
          ``success=True``.
        * **AC-002** — The reply is NOT a JetStream PubAck. The raw JSON
          must not match the ``{"stream":..., "seq":...}`` shape (Bug #1
          regression guard, explicit assertion).
        * **AC-003** — The wire-tap on ``agents.result.gcse-tutor``
          captured exactly one envelope per dispatch (Bug #1 — the
          canonical topic publish path is also exercised).
        * **AC-004 / AC-005** — The stub MCP adapter saw the *canonical*
          command method, proving the router applied alias resolution
          for the ``tutor_*`` form and the passthrough for the canonical
          form.
        """
        adapter, stub = tutor_adapter
        agent_id = adapter._manifest.agent_id

        # Wire-tap: subscribe to the canonical result topic *before*
        # dispatch so we never miss the publish. ``asyncio.Event`` lets
        # us wait deterministically for the first envelope rather than
        # arbitrary sleeps (per the task implementation note).
        observer_nc = await nats.connect(bootstrapped_server, connect_timeout=5)
        wiretap_received: list[bytes] = []
        wiretap_event = asyncio.Event()

        async def _on_result(msg: Any) -> None:
            wiretap_received.append(msg.data)
            wiretap_event.set()

        await observer_nc.subscribe(RESULT_SUBJECT, cb=_on_result)

        try:
            # ---- Build and dispatch the COMMAND envelope ----
            envelope = MessageEnvelope(
                source_id="integration-smoke",
                event_type=EventType.COMMAND,
                payload=CommandPayload(
                    command=wire_command,
                    args=_args_for(canonical_command),
                    correlation_id=f"corr-{wire_command}",
                ).model_dump(),
                correlation_id=f"corr-{wire_command}",
            )
            command_subject = f"agents.command.{agent_id}"
            response_msg = await observer_nc.request(
                command_subject,
                envelope.model_dump_json().encode(),
                timeout=10.0,
            )

            # ---- AC-002 — Bug #1 PubAck regression guard ----
            # Parse as raw JSON first and assert the response is NOT a
            # JetStream PubAck. The PubAck shape is exactly
            # ``{"stream": str, "seq": int, "domain": str?}`` — we
            # reject any reply whose top-level keys are a subset of
            # that envelope. ResultPayload has many more keys (command,
            # success, result, ...), so this check is conservative.
            raw_reply = json.loads(response_msg.data)
            assert isinstance(raw_reply, dict), (
                f"reply not a JSON object: {raw_reply!r}"
            )
            puback_keys = {"stream", "seq", "domain"}
            assert not (set(raw_reply.keys()) <= puback_keys), (
                f"reply parsed as a JetStream PubAck — Bug #1 regression: "
                f"{raw_reply!r}. Expected a ResultPayload."
            )
            # Belt-and-braces: explicit "result-payload-shape" check.
            assert "success" in raw_reply and "command" in raw_reply, (
                f"reply does not look like a ResultPayload: {raw_reply!r}"
            )

            # ---- AC-001 — ResultPayload(success=True) ----
            result = ResultPayload.model_validate_json(response_msg.data)
            assert result.success is True, (
                f"command {wire_command!r} returned failure: {result}"
            )
            # The router preserves the (alias-resolved) canonical name
            # in ResultPayload.command — sanity-check the round-trip
            # didn't drop it.
            assert result.command == canonical_command, (
                f"ResultPayload.command was {result.command!r}, "
                f"expected canonical {canonical_command!r} after alias resolution"
            )

            # ---- AC-004 / AC-005 — alias vs canonical reach the same
            # stub method (proves Bug #2 fix is wired AND the canonical
            # passthrough behaviour) ----
            assert len(stub.calls) == 1, (
                f"stub MCP adapter saw {len(stub.calls)} calls, expected 1 per dispatch"
            )
            invoked_method, _invoked_args = stub.calls[0]
            expected_method = _CANONICAL_TO_STUB_METHOD[canonical_command]
            assert invoked_method == expected_method, (
                f"router invoked stub method {invoked_method!r}, "
                f"expected {expected_method!r} after resolving "
                f"wire command {wire_command!r}"
            )

            # ---- AC-003 — wire-tap captured exactly one envelope on
            # agents.result.<agent_id> ----
            try:
                await asyncio.wait_for(wiretap_event.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                pytest.fail(
                    f"wire-tap on {RESULT_SUBJECT!r} received no envelope "
                    f"within 2s — Bug #1 regression on the canonical "
                    f"publish path"
                )
            # Single dispatch must yield exactly one canonical publish.
            assert len(wiretap_received) == 1, (
                f"wire-tap captured {len(wiretap_received)} envelopes "
                f"on {RESULT_SUBJECT!r}, expected exactly 1 per dispatch"
            )
            tap_envelope = MessageEnvelope.model_validate_json(wiretap_received[0])
            assert tap_envelope.event_type == EventType.RESULT, (
                f"wire-tap envelope event_type was {tap_envelope.event_type!r}, "
                f"expected RESULT"
            )
            assert tap_envelope.source_id == agent_id, (
                f"wire-tap envelope source_id was {tap_envelope.source_id!r}, "
                f"expected {agent_id!r}"
            )
        finally:
            await observer_nc.drain()
            await observer_nc.close()
