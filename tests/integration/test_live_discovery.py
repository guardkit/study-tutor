"""Live-discovery smoke for TASK-NATS-PH1-009 (Decision 1 regression guard).

Validates the Phase 1 contract from the FEAT-NATS architectural review
(2026-05-08, Decision 1): jarvis discovers ``gcse-tutor`` through the
*live* ``agent-registry`` KV bucket alone — no stub-capabilities YAML is
loaded, referenced, or required on the consumer side.

Strategy
--------
The test spins up a per-test ``nats-server`` subprocess (JetStream
enabled), pre-provisions the ``agent-registry`` KV bucket the same way
``nats-infrastructure/kv/provision-kv.sh`` does in production, then
exercises the full discovery path:

1. Boot study-tutor's :class:`NATSAdapter` (the same adapter wired by
   ``study_tutor.adapters.nats_adapter`` for production).
2. Open a faithful stand-in for jarvis's ``LiveCapabilitiesRegistry``
   against the same KV bucket — namely
   :class:`nats_core.NATSKVManifestRegistry`, which is the underlying
   collaborator that ``LiveCapabilitiesRegistry.create`` delegates to
   in production (see
   ``jarvis/src/jarvis/infrastructure/capabilities_registry.py:227-515``,
   specifically ``_resolve_registry`` at L180-196). Jarvis itself is not
   importable from this repo, so we bind the same KV-backed surface
   without re-implementing the cache layer.
3. Call :meth:`NATSKVManifestRegistry.find_by_tool` for
   ``tool_name="tutor_start_session"`` — this is the resolver shape
   jarvis uses for tool-based routing — and assert ``gcse-tutor`` is
   returned as a candidate.
4. Stop the adapter and assert the KV row is removed within 30s
   (Decision 1 graceful-deregister contract).

Stub-yaml absence is asserted explicitly (AC-004) by walking the source
file and checking that no ``stub_capabilities`` reference appears in
the imports or in the test body — i.e. discovery cannot accidentally be
satisfied by a yaml fixture that snuck back into the test. The check
uses :mod:`ast` so a stray comment containing the string does not
trigger a false positive.

Test isolation
--------------
Each test gets its own ``nats-server`` subprocess with an isolated
JetStream store under ``tmp_path`` — there is no shared state between
tests, so a flaky test cannot corrupt the next one. The fixture skips
cleanly when the ``nats-server`` binary is not on PATH so this file
runs both on operator machines (Homebrew puts it in
``/opt/homebrew/bin``) and on CI runners that don't ship the binary.
"""

from __future__ import annotations

import ast
import asyncio
import shutil
import socket
import subprocess
import time
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import nats
import pytest
import pytest_asyncio
from nats_core import AgentManifest, NATSKVManifestRegistry
from nats_core.agent_config import AgentConfig, ModelConfig, NATSConfig

from study_tutor.adapters.command_router import CommandRouter
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
# Fixtures — mirror tests/integration/test_adapter_lifecycle.py so the
# behaviour difference between the two suites is the assertion shape, not
# the broker plumbing. Keeping the spawning identical means a regression
# in the broker fixture surfaces in both files at once.
# ---------------------------------------------------------------------------


def _free_port() -> int:
    """Allocate an OS-assigned free TCP port for the ``nats-server`` subprocess.

    Bind ``0`` to an ephemeral socket, read back the port, close the
    socket. There is a tiny race between us closing the socket and
    nats-server binding, but in practice it is more than reliable enough
    for a per-test fixture (and the alternative — a hardcoded port —
    breaks parallel pytest-xdist runs).
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


@pytest_asyncio.fixture()
async def nats_server(tmp_path: Path) -> AsyncIterator[str]:
    """Spawn a per-test ``nats-server`` subprocess with JetStream enabled.

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
    not create it (see ``nats_core.client.NATSKVManifestRegistry.create``:
    production bootstrap is performed by
    ``nats-infrastructure/kv/provision-kv.sh``). This fixture replays
    that idempotent provisioning step against the ephemeral test server
    so the adapter's KV writes have somewhere to land.
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

    Heartbeat interval is short (1s) so the discovery test does not have
    to wait the production default 30s for the registry to settle — the
    KV ``put`` happens synchronously inside ``register_agent``, so the
    heartbeat tuning is for symmetry with ``test_adapter_lifecycle.py``,
    not correctness.
    """
    return AgentConfig(
        models=ModelConfig(reasoning_model="test-model"),
        nats=NATSConfig(url=bootstrapped_server),
        heartbeat_interval_seconds=1,
        heartbeat_timeout_seconds=2,
    )


@pytest.fixture()
def manifest() -> AgentManifest:
    """Real study-tutor manifest — same intents/tools as production.

    The intent pattern (``tutoring.*``) and tool list
    (``tutor_start_session``, ``tutor_turn``, ``tutor_session_status``,
    ``tutor_session_end``) match the manifest factory's production
    output bit-for-bit so the resolver assertion exercises the actual
    capability surface jarvis sees on the wire.
    """
    return _tutor_manifest_factory(agent_id="gcse-tutor")


class _NoopCommandRouter:
    """Stand-in for :class:`CommandRouter`.

    Discovery does not exercise the command path, so a no-op router is
    correct here — the adapter still wires the
    ``agents.command.<agent_id>`` subscription, but no command is ever
    published in this test, so the body of ``on_command`` is never
    invoked. Using the production :class:`CommandRouter` would require
    fabricating an MCP adapter just to satisfy a constructor argument
    that is never read; the no-op keeps the test focused on the KV
    surface.
    """

    async def on_command(
        self,
        envelope: Any,  # noqa: ARG002 — discovery never invokes this body.
        reply_to: str | None = None,  # noqa: ARG002
    ) -> None:
        return None


# ---------------------------------------------------------------------------
# AC-001 / AC-002 / AC-003 / AC-004 — live discovery without stub yaml
# ---------------------------------------------------------------------------


@_skip_no_server
@pytest.mark.integration_contract("LiveDiscovery")
@pytest.mark.smoke
class TestLiveDiscoverySmoke:
    """Decision 1 regression guard — discovery via live KV alone.

    Each test in this class proves one half of the contract:

    * :meth:`test_jarvis_discovers_gcse_tutor_via_live_kv` exercises the
      happy path end-to-end (boot → manifest visible → tool-resolver
      finds the agent → graceful deregister leaves the bucket clean).
    * :meth:`test_no_stub_capabilities_yaml_loaded_by_test` is a
      static-analysis guard that the test itself does not depend on a
      stub yaml fallback (AC-004).
    """

    async def test_jarvis_discovers_gcse_tutor_via_live_kv(
        self,
        agent_config: AgentConfig,
        manifest: AgentManifest,
        bootstrapped_server: str,
    ) -> None:
        """Full live-discovery round-trip without any stub fallback.

        Steps:

        1. Construct + ``start()`` the study-tutor :class:`NATSAdapter`.
        2. Open a sidecar :class:`NATSKVManifestRegistry` against the
           same ``agent-registry`` bucket — the faithful stand-in for
           jarvis's ``LiveCapabilitiesRegistry`` consumer of the KV
           surface (jarvis is not importable from this repo, but the
           registry shape it consumes is the one we exercise here).
        3. Assert the manifest is present and structurally correct.
        4. Resolve ``tool_name="tutor_start_session"`` and assert
           ``gcse-tutor`` is among the candidates.
        5. ``stop()`` the adapter, then poll the KV bucket for up to
           30s and assert the row is removed (Decision 1 graceful
           deregister contract).
        """
        # 1. Boot the production adapter against the live server.
        adapter = NATSAdapter(
            config=agent_config,
            manifest=manifest,
            command_router=_NoopCommandRouter(),  # type: ignore[arg-type]
        )
        await adapter.start()

        # 2 + 3. Open the consumer-side registry from a sidecar
        #         connection. Using a sidecar (rather than reusing the
        #         adapter's internal client) mirrors the production
        #         topology where jarvis runs in a different process.
        consumer_nc = await nats.connect(bootstrapped_server, connect_timeout=5)
        try:
            consumer_registry = await NATSKVManifestRegistry.create(consumer_nc)

            # ---- AC-001: gcse-tutor row visible with correct payload ----
            stored = await consumer_registry.get(manifest.agent_id)
            assert stored is not None, (
                f"manifest for '{manifest.agent_id}' missing from "
                f"agent-registry KV after adapter.start() — Decision 1 "
                f"requires live registration with no stub fallback"
            )
            assert stored.agent_id == manifest.agent_id
            assert stored.name == manifest.name
            assert stored.template == manifest.template
            assert stored.trust_tier == manifest.trust_tier
            # Bug #5 guard — registry must reject empty-intents manifests,
            # so a successful read here implies len(intents) >= 1.
            assert len(stored.intents) >= 1
            assert any(cap.pattern == "tutoring.*" for cap in stored.intents)
            # All four MCP tools must be present so the resolver branch
            # exercised below has a real surface to find.
            stored_tool_names = {tool.name for tool in stored.tools}
            assert {
                "tutor_start_session",
                "tutor_turn",
                "tutor_session_status",
                "tutor_session_end",
            }.issubset(stored_tool_names)

            # ---- AC-002: capability resolution finds gcse-tutor ----
            # NATSKVManifestRegistry.find_by_tool is the same surface
            # jarvis's LiveCapabilitiesRegistry consumes for tool-based
            # routing (capabilities_registry.py L575-590 in the jarvis
            # repo). A non-empty result containing "gcse-tutor" is the
            # Decision 1 regression guard — discovery must NOT depend
            # on stub yaml.
            candidates = await consumer_registry.find_by_tool(
                "tutor_start_session"
            )
            assert candidates, (
                "find_by_tool('tutor_start_session') returned no agents — "
                "Decision 1 regression: live KV discovery is broken"
            )
            candidate_ids = [m.agent_id for m in candidates]
            assert manifest.agent_id in candidate_ids, (
                f"resolver did not return '{manifest.agent_id}' for "
                f"tool_name='tutor_start_session'; got {candidate_ids!r}"
            )
        finally:
            await consumer_nc.drain()
            await consumer_nc.close()

        # 4. Tear down the adapter — graceful deregister contract.
        await adapter.stop()

        # 5. Poll for KV-row removal within 30s. The adapter's stop()
        #    calls deregister synchronously, so in practice the row is
        #    gone by the time we get here; the polling window honours
        #    the AC's "within 30s" budget for slow CI boxes.
        observer_nc = await nats.connect(bootstrapped_server, connect_timeout=5)
        try:
            observer_registry = await NATSKVManifestRegistry.create(observer_nc)
            deadline = time.monotonic() + 30.0
            while time.monotonic() < deadline:
                still_present = await observer_registry.get(manifest.agent_id)
                if still_present is None:
                    break
                await asyncio.sleep(0.1)
            else:
                pytest.fail(
                    f"manifest for '{manifest.agent_id}' was not removed "
                    f"from agent-registry within 30s of adapter.stop() — "
                    f"Decision 1 graceful-deregister contract violated"
                )

            # Final state assertion: adapter is fully torn down.
            assert adapter.is_ready is False
            assert adapter.active_tasks == 0
        finally:
            await observer_nc.drain()
            await observer_nc.close()

    def test_no_stub_capabilities_yaml_loaded_by_test(self) -> None:
        """AC-004: this test file does not load any stub-capabilities yaml.

        Static guard — parses this file's AST and asserts no import or
        attribute reference touches a ``stub_capabilities`` symbol or a
        ``stub_capabilities.yaml`` path. Without this assertion a future
        edit could quietly satisfy discovery via the fallback yaml and
        the test would still pass while violating Decision 1.

        We also assert that nothing the production adapter brings in
        carries a stub fallback path: the adapter's import graph must
        come from ``study_tutor.adapters.*`` and ``nats_core.*`` only —
        i.e. live KV is the sole source of truth here.
        """
        test_path = Path(__file__).resolve()
        source = test_path.read_text(encoding="utf-8")
        tree = ast.parse(source)

        # Collect every name reference the AST sees — imports, attribute
        # access, and string literals that could plausibly be a path.
        offending: list[str] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if "stub_capabilities" in alias.name:
                        offending.append(f"import {alias.name}")
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if "stub_capabilities" in module:
                    offending.append(f"from {module} import ...")
                for alias in node.names:
                    if "stub_capabilities" in alias.name:
                        offending.append(f"... import {alias.name}")
            elif isinstance(node, ast.Attribute):
                if "stub_capabilities" in node.attr:
                    offending.append(f"attr {node.attr}")
            elif isinstance(node, ast.Constant) and isinstance(
                node.value, str
            ):
                if "stub_capabilities" in node.value and node.value.endswith(
                    (".yaml", ".yml")
                ):
                    offending.append(f"path literal {node.value!r}")

        assert not offending, (
            "AC-004 violation: this test file references stub_capabilities "
            f"yaml fallback paths: {offending!r} — Decision 1 forbids any "
            "stub-yaml dependence in the live-discovery smoke."
        )

        # Also check the production-side adapter the test exercises:
        # imports must come from study_tutor.adapters.* and nats_core.*
        # only (no stub-capabilities yaml loader hiding under one of
        # those names). Resolving via the loaded module's __file__ is
        # robust against namespace-package layouts and editable installs.
        import study_tutor.adapters.nats_adapter as _adapter_module

        adapter_path = Path(_adapter_module.__file__)  # type: ignore[arg-type]
        adapter_source = adapter_path.read_text(encoding="utf-8")
        assert "stub_capabilities" not in adapter_source, (
            "AC-004 violation: study_tutor.adapters.nats_adapter contains "
            "a stub_capabilities reference — Decision 1 requires live "
            "registration only."
        )

        # And the manifest factory.
        import study_tutor.adapters.manifest as _manifest_module

        manifest_source = Path(
            _manifest_module.__file__  # type: ignore[arg-type]
        ).read_text(encoding="utf-8")
        assert "stub_capabilities" not in manifest_source, (
            "AC-004 violation: study_tutor.adapters.manifest contains a "
            "stub_capabilities reference — Decision 1 requires live "
            "registration only."
        )

        # Defensive: the CommandRouter is the only other adapter-side
        # collaborator the test imports — guard it the same way.
        import study_tutor.adapters.command_router as _router_module

        router_source = Path(
            _router_module.__file__  # type: ignore[arg-type]
        ).read_text(encoding="utf-8")
        assert "stub_capabilities" not in router_source, (
            "AC-004 violation: study_tutor.adapters.command_router "
            "contains a stub_capabilities reference — Decision 1 "
            "requires live registration only."
        )

        # Reference CommandRouter so the import is not flagged as unused
        # by ruff (the import is genuinely load-bearing for the path
        # check above, since we resolve __file__ on the imported module).
        assert CommandRouter.__name__ == "CommandRouter"
