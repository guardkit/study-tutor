"""Wave 3 — Live-graphiti smoke test (TASK-GR-SMOK).

Two-layer regression-prevention test against the silent-OpenAI-default failure
mode that shipped in Phase 1 (see F5 + F7 in the TASK-REV-GR1A review report):

1. **Constructor-shape assertion (always-on, runs in CI)** — boots a real
   ``Graphiti`` instance with the wired clients but stubs the FalkorDB driver.
   Asserts ``Graphiti.__init__`` was called with non-None ``llm_client``,
   non-None ``embedder``, and a ``cross_encoder`` that raises on access. This
   catches the next graphiti-core kwarg drift (the parent's ``@regression`` BDD
   scenario explicitly targets this).

2. **Live FalkorDB round-trip (env-gated)** — only runs when
   ``STUDY_TUTOR_LIVE_GRAPHITI_SMOKE=1`` is set (Tailscale-only). Round-trips
   one ``add_episode(group_id="student-test", ...)`` →
   ``EntityNode.get_by_group_ids(...)`` → asserts the episode is reachable, then
   cleans up the test group.

CI contract (AC-SMOK-07):
    The constructor-shape, kwarg-drift, and OPENAI_API_KEY-poison tests run on
    every CI invocation (no env-var gate). The live FalkorDB round-trip
    (``test_live_falkordb_roundtrip``) is gated on
    ``STUDY_TUTOR_LIVE_GRAPHITI_SMOKE=1`` because it requires Tailscale access
    to the Synology NAS. CI configuration (GitHub Actions, Conductor, local
    pre-commit) MUST NOT set ``STUDY_TUTOR_LIVE_GRAPHITI_SMOKE=1``; the live
    test is intentionally a developer-only Tailscale-gated check.

Cross-references:
    - AC-SMOK-01 through AC-SMOK-07 in
      ``tasks/design_approved/TASK-GR-SMOK-graphiti-runtime-smoke-test.md``
    - F5 + F7 in ``.claude/reviews/TASK-REV-GR1A-review-report.md``
    - ``tests/unit/knowledge/test_graphiti_client_wiring.py`` — same fake-driver
      stubbing pattern reused here for path-level consistency
"""
from __future__ import annotations

import inspect
import os
from typing import Any
from unittest.mock import patch

import pytest

pytestmark = [pytest.mark.smoke]


# ---------------------------------------------------------------------------
# Fakes — match the existing ``test_graphiti_client_wiring.py`` shape so a
# graphiti-core kwarg drift fails *here* with the same diagnostic field
# names that the wiring tests use. Re-defining locally rather than importing
# keeps this file self-contained per AC-SMOK-01 (single test file).
# ---------------------------------------------------------------------------


class _CapturingGraphiti:
    """Stand-in for ``graphiti_core.Graphiti`` that records init kwargs.

    Sets ``self.driver`` from the captured ``graph_driver`` so the wrapper's
    healthcheck path (which probes ``inner.driver.execute_query``) finds a
    ping-green driver and ``get_client`` returns a wrapper rather than
    None.
    """

    last_kwargs: dict[str, Any] | None = None

    def __init__(self, **kwargs: Any) -> None:
        self.driver = kwargs.get("graph_driver")
        type(self).last_kwargs = kwargs

    async def close(self) -> None:  # pragma: no cover - close path tested elsewhere
        pass


class _FakeFalkorDriver:
    """Stand-in for ``graphiti_core.driver.falkordb_driver.FalkorDriver``.

    ``execute_query`` returns a non-empty result so the healthcheck path
    classifies the driver as healthy (see ``GraphitiClient._ping``).
    """

    def __init__(self, host: str, port: int, database: str) -> None:
        self.host = host
        self.port = port
        self.database = database

    async def execute_query(self, query: str) -> list[dict[str, int]]:
        return [{"v": 1}]

    async def close(self) -> None:  # pragma: no cover
        pass


def _make_local_inference_config():
    """Build a ``GraphitiConnectionConfig`` pointing at local inference.

    Mirrors the fixture used by ``test_graphiti_client_wiring.py`` — vllm
    provider on a local llama-swap so DECISION-DF-001's cloud-provider
    rejection cannot accidentally fire during these tests.
    """
    from study_tutor.knowledge.graphiti_client import GraphitiConnectionConfig

    return GraphitiConnectionConfig(
        falkor_host="whitestocks",
        falkor_port=6379,
        database="study_tutor_smoke",
        llm_provider="vllm",
        llm_base_url="http://promaxgb10-41b1:9000/v1",
        llm_model="qwen-graphiti",
        llm_max_tokens=4096,
        embedding_provider="vllm",
        embedding_base_url="http://promaxgb10-41b1:9000/v1",
        embedding_model="nomic-embed",
        embedder_url="http://promaxgb10-41b1:9000/v1",
    )


# ---------------------------------------------------------------------------
# AC-SMOK-02 — constructor-shape assertion (always-on)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_constructor_shape_no_cloud_defaults(monkeypatch):
    """``Graphiti.__init__`` must receive real local-inference clients.

    AC-SMOK-02: with ``OPENAI_API_KEY`` poisoned, the captured ``llm_client``
    must be an ``OpenAIGenericClient`` carrying ``api_key="local-key"``, and
    the captured ``embedder`` must be an ``OpenAIEmbedder`` carrying the same
    placeholder. ``cross_encoder`` must be the DECISION-DF-001 sentinel —
    attribute access raises ``RuntimeError`` so a downstream reranker call
    converts a silent OpenAI fallback into a loud failure.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "poison-must-not-leak")

    # Lazy import inside the function so module import works even when
    # graphiti-core is uninstalled. The wiring test guards the lazy-import
    # contract this relies on.
    from graphiti_core.embedder import OpenAIEmbedder  # type: ignore[import-not-found]
    from graphiti_core.llm_client.openai_generic_client import (  # type: ignore[import-not-found]
        OpenAIGenericClient,
    )

    from study_tutor.knowledge import graphiti_client as gc

    # Reset the class-level capture so a previous test cannot leak kwargs in.
    _CapturingGraphiti.last_kwargs = None

    config = _make_local_inference_config()

    with patch.object(
        gc,
        "_load_graphiti_core",
        return_value=(_CapturingGraphiti, _FakeFalkorDriver),
    ):
        wrapper = await gc.get_client(config)

    assert wrapper is not None, "stubbed driver pings green; wrapper must exist"

    captured = _CapturingGraphiti.last_kwargs
    assert captured is not None, "Graphiti.__init__ must have been called"

    # 1. llm_client is an OpenAIGenericClient instance
    assert isinstance(captured["llm_client"], OpenAIGenericClient), (
        "AC-SMOK-02.1: kwargs['llm_client'] must be an OpenAIGenericClient — "
        f"got {type(captured['llm_client']).__name__}"
    )

    # 2. llm_client.config.api_key == "local-key" (NOT the poisoned env var)
    assert captured["llm_client"].config.api_key == "local-key", (
        "AC-SMOK-02.2: api_key must be the placeholder 'local-key', never "
        f"OPENAI_API_KEY — got {captured['llm_client'].config.api_key!r}"
    )
    assert captured["llm_client"].config.api_key != os.environ["OPENAI_API_KEY"], (
        "AC-SMOK-02.2: api_key must not equal OPENAI_API_KEY even when set"
    )

    # 3. embedder is an OpenAIEmbedder instance
    assert isinstance(captured["embedder"], OpenAIEmbedder), (
        "AC-SMOK-02.3: kwargs['embedder'] must be an OpenAIEmbedder — "
        f"got {type(captured['embedder']).__name__}"
    )

    # 4. embedder.config.api_key == "local-key"
    assert captured["embedder"].config.api_key == "local-key", (
        "AC-SMOK-02.4: embedder api_key must be 'local-key', never "
        f"OPENAI_API_KEY — got {captured['embedder'].config.api_key!r}"
    )

    # 5. cross_encoder is the sentinel that raises on attribute access
    assert captured["cross_encoder"] is not None, (
        "AC-SMOK-02.5: cross_encoder must NOT be None — None re-triggers "
        "graphiti-core's default OpenAI cross-encoder construction"
    )
    with pytest.raises(RuntimeError, match="DECISION-DF-001"):
        captured["cross_encoder"].predict(["q"], ["d"])


# ---------------------------------------------------------------------------
# AC-SMOK-03 — kwarg-drift detection (always-on)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_kwarg_drift_detection():
    """Fail loudly if any of the four required kwarg names disappear.

    AC-SMOK-03 / parent ``@regression`` BDD scenario: graphiti-core 0.30
    (or any future minor) renaming ``graph_driver`` / ``llm_client`` /
    ``embedder`` / ``cross_encoder`` must surface here as a clear missing-
    kwarg failure rather than a silent OpenAI re-default.
    """
    from study_tutor.knowledge import graphiti_client as gc

    _CapturingGraphiti.last_kwargs = None
    config = _make_local_inference_config()

    with patch.object(
        gc,
        "_load_graphiti_core",
        return_value=(_CapturingGraphiti, _FakeFalkorDriver),
    ):
        wrapper = await gc.get_client(config)

    assert wrapper is not None
    captured = _CapturingGraphiti.last_kwargs
    assert captured is not None

    expected_kwargs = ("graph_driver", "llm_client", "embedder", "cross_encoder")
    missing = [name for name in expected_kwargs if name not in captured]
    assert not missing, (
        f"AC-SMOK-03 / @regression: graphiti-core kwarg drift detected — "
        f"missing kwargs {missing!r}. If graphiti-core renamed any of these "
        f"in a minor bump, update study_tutor.knowledge.graphiti_client."
        f"get_client to match the new constructor surface. Captured kwargs: "
        f"{sorted(captured.keys())!r}"
    )


# ---------------------------------------------------------------------------
# AC-SMOK-05 — OPENAI_API_KEY must never be read by the builders
# ---------------------------------------------------------------------------


def test_openai_api_key_never_read(monkeypatch):
    """``_build_llm_client`` and ``_build_embedder`` must ignore OPENAI_API_KEY.

    AC-SMOK-05 / AC-LOAD-03 / AC-WIRE-05: setting the env var to a poison
    value and constructing both clients directly must yield ``api_key !=
    "poison-must-not-leak"`` — the canonical local-inference placeholder
    ``"local-key"`` is the only acceptable value.
    """
    monkeypatch.setenv("OPENAI_API_KEY", "poison-must-not-leak")

    from study_tutor.knowledge import graphiti_client as gc

    config = _make_local_inference_config()

    llm_client = gc._build_llm_client(config)
    embedder = gc._build_embedder(config)

    assert llm_client.config.api_key != "poison-must-not-leak", (
        "AC-SMOK-05: _build_llm_client must not consume OPENAI_API_KEY"
    )
    assert llm_client.config.api_key == "local-key", (
        "AC-SMOK-05: _build_llm_client must use the 'local-key' placeholder"
    )
    assert embedder.config.api_key != "poison-must-not-leak", (
        "AC-SMOK-05: _build_embedder must not consume OPENAI_API_KEY"
    )
    assert embedder.config.api_key == "local-key", (
        "AC-SMOK-05: _build_embedder must use the 'local-key' placeholder"
    )


# ---------------------------------------------------------------------------
# AC-SMOK-06 — CC-13 single-add_episode-call-site invariant (always-on)
# ---------------------------------------------------------------------------


def test_cc_13_single_add_episode_call_site():
    """Re-run the CC-13 audit at test time so a regression fails the suite.

    AC-SMOK-06: the project invariant is that ``src/`` contains exactly one
    ``add_episode(`` call site (in ``async_write.py::_perform_write``). A new
    call site anywhere else under ``src/`` re-introduces the failure mode CC-13
    exists to prevent — every flush point must funnel through the single
    helper. We re-run the audit here so the smoke gate fails immediately on
    drift, rather than waiting for a separate lint pass.
    """
    import re
    from pathlib import Path

    src_root = Path(__file__).resolve().parents[2] / "src"
    assert src_root.is_dir(), f"src tree not found at {src_root}"

    pattern = re.compile(r"add_episode\s*\(")
    findings: list[tuple[Path, int, str]] = []
    for py_file in src_root.rglob("*.py"):
        text = py_file.read_text(encoding="utf-8")
        for lineno, line in enumerate(text.splitlines(), start=1):
            # Skip comments / docstrings: the audit is for actual call sites.
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            if pattern.search(line) and "await" in line:
                findings.append((py_file.relative_to(src_root), lineno, line.strip()))

    assert len(findings) == 1, (
        "AC-SMOK-06 / CC-13: expected exactly one ``await ... add_episode(`` "
        f"call site in src/, found {len(findings)}: {findings!r}"
    )
    rel_path, _, _ = findings[0]
    assert rel_path == Path("study_tutor/knowledge/async_write.py"), (
        "AC-SMOK-06 / CC-13: the lone add_episode call site must live in "
        f"async_write.py — found it in {rel_path}"
    )


# ---------------------------------------------------------------------------
# AC-SMOK-04 — live FalkorDB round-trip (env-gated, Tailscale-only)
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    os.environ.get("STUDY_TUTOR_LIVE_GRAPHITI_SMOKE") != "1",
    reason=(
        "live FalkorDB requires Tailscale; set "
        "STUDY_TUTOR_LIVE_GRAPHITI_SMOKE=1 to enable"
    ),
)
@pytest.mark.asyncio
async def test_live_falkordb_roundtrip():
    """Round-trip one episode through real FalkorDB and assert recall.

    AC-SMOK-04: this is the developer-only Tailscale-gated check. CI must
    leave ``STUDY_TUTOR_LIVE_GRAPHITI_SMOKE`` unset (AC-SMOK-07).

    Uses ``group_id="student-test"`` so repeated runs do not pollute the
    real Lilymay graph. Cleans up by dropping the group after the assertion
    via the same driver the wrapper holds.
    """
    from datetime import datetime, timezone

    # Lazy imports — graphiti-core is only required when this test actually runs.
    from graphiti_core.nodes import EntityNode, EpisodeType  # type: ignore[import-not-found]

    from study_tutor.knowledge.graphiti_client import (
        DEFAULT_GRAPHITI_YAML_PATH,
        get_client,
        load_graphiti_config_from_yaml,
    )

    config = load_graphiti_config_from_yaml(DEFAULT_GRAPHITI_YAML_PATH)
    wrapper = await get_client(config)
    assert wrapper is not None, (
        "AC-SMOK-04: live FalkorDB unreachable — check Tailscale + NAS state"
    )

    inner = wrapper.client_or_none
    assert inner is not None, "wrapper must expose live graphiti-core client"

    test_group_id = "student-test"
    driver = getattr(inner, "driver", None)
    assert driver is not None, "graphiti client must expose a driver attribute"

    try:
        await inner.add_episode(
            name="smoke",
            episode_body='{"smoke": "live-graphiti-smoke-test"}',
            source=EpisodeType.json,
            source_description="smoke-test",
            reference_time=datetime.now(timezone.utc),
            group_id=test_group_id,
        )

        nodes = await EntityNode.get_by_group_ids(driver, group_ids=[test_group_id])
        assert nodes, (
            "AC-SMOK-04: EntityNode.get_by_group_ids returned empty after "
            "add_episode — episode is not reachable, round-trip failed"
        )
    finally:
        # Clean up the test group: delete every node + edge tagged with the
        # test group_id so repeated runs stay idempotent. Use the driver's
        # raw query path rather than the Graphiti facade so the cleanup runs
        # even if a higher-level helper is unavailable.
        cleanup_query = (
            "MATCH (n {group_id: $group_id}) DETACH DELETE n"
        )
        try:
            execute = getattr(driver, "execute_query", None) or getattr(
                driver, "query", None
            )
            if execute is not None:
                result = execute(cleanup_query, {"group_id": test_group_id})
                # graphiti-core 0.29 drivers return either a coroutine or a
                # plain list — await the coroutine, drop the list.
                if inspect.iscoroutine(result):
                    await result
        finally:
            await wrapper.close()
