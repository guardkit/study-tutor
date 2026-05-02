"""Unit + seam tests for the Graphiti client wrapper (TASK-GSM-003).

Per the minimal documentation level for this task, unit tests, the
lazy-import subprocess test, and the §4 producer-side seam tests all live
in this single file (the 2-file ceiling forbids splitting them across
``test_*.py`` modules).
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import subprocess
import sys
import textwrap
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_config(**overrides):
    """Construct a valid GraphitiConnectionConfig with test-friendly defaults."""
    from study_tutor.knowledge.graphiti_client import GraphitiConnectionConfig

    base = dict(
        falkor_host="localhost",
        falkor_port=6379,
        database="test",
        embedder_url="http://localhost:8001",
    )
    base.update(overrides)
    return GraphitiConnectionConfig(**base)


class _FakeDriverOK:
    """Fake driver whose ``execute_query`` returns immediately.

    Constructor accepts the ``host``/``port``/``database`` kwargs that the
    factory passes through to the real ``FalkorDriver``.
    """

    def __init__(self, host: str = "h", port: int = 1, database: str = "d") -> None:
        self.host = host
        self.port = port
        self.database = database
        self.calls: list[str] = []

    async def execute_query(self, q: str):
        self.calls.append(q)
        return [{"v": 1}]

    async def close(self) -> None:  # pragma: no cover - exercised via inner.close
        pass


class _FakeGraphitiOK:
    """Fake graphiti-core ``Graphiti`` whose driver responds OK."""

    def __init__(self, graph_driver) -> None:
        self.driver = graph_driver

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# AC: Module imports successfully when graphiti-core is uninstalled
# ---------------------------------------------------------------------------


def test_module_top_level_has_no_graphiti_core_import():
    """Lazy-import contract: no top-level ``graphiti_core`` import.

    A top-level import would defeat the lazy-import property — even
    introspecting ``GraphitiConnectionConfig`` would fail when graphiti-core
    is absent. Indented (function-body) imports are fine.
    """
    from study_tutor.knowledge import graphiti_client

    src = inspect.getsource(graphiti_client)
    for line_no, raw_line in enumerate(src.splitlines(), 1):
        # Top-level statements are not indented at all.
        if raw_line.startswith(("import graphiti_core", "from graphiti_core")):
            pytest.fail(
                f"line {line_no}: top-level graphiti-core import "
                f"violates lazy-import contract: {raw_line!r}"
            )


def test_module_loads_in_subprocess_with_graphiti_core_absent():
    """Subprocess-based module-load test (mirrors the integration test).

    Setting ``sys.modules['graphiti_core'] = None`` makes
    ``import graphiti_core`` raise ``ImportError``. The wrapper module must
    still import cleanly — this is the production guarantee that callers
    can introspect the config class without the optional dependency.
    """
    code = textwrap.dedent(
        """
        import sys
        sys.modules['graphiti_core'] = None  # simulate absent dependency
        import study_tutor.knowledge.graphiti_client as mod
        cfg = mod.GraphitiConnectionConfig(
            falkor_host='h', falkor_port=1, database='d',
            embedder_url='http://x',
        )
        print('OK', cfg.timeout_seconds)
        """
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"subprocess failed: stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "OK 5.0" in result.stdout


def test_module_docstring_references_lazy_import_pattern():
    """AC: docstring references the lazy-import pattern from specialist-agent."""
    from study_tutor.knowledge import graphiti_client

    doc = (graphiti_client.__doc__ or "").lower()
    assert "specialist-agent" in doc or "specialist_agent" in doc
    assert "lazy" in doc


# ---------------------------------------------------------------------------
# AC: GraphitiConnectionConfig validation
# ---------------------------------------------------------------------------


def test_config_default_timeout_matches_assum_005():
    cfg = _make_config()
    assert cfg.timeout_seconds == 5.0


def test_config_default_provider_and_model():
    cfg = _make_config()
    assert cfg.llm_provider == "gemini"
    assert cfg.llm_model == "gemini-2.5-pro"


def test_config_rejects_negative_port():
    with pytest.raises(ValidationError):
        _make_config(falkor_port=-1)


def test_config_rejects_zero_port():
    with pytest.raises(ValidationError):
        _make_config(falkor_port=0)


def test_config_rejects_zero_timeout():
    with pytest.raises(ValidationError):
        _make_config(timeout_seconds=0)


def test_config_rejects_negative_timeout():
    with pytest.raises(ValidationError):
        _make_config(timeout_seconds=-0.1)


def test_config_rejects_extra_fields():
    """``extra='forbid'`` so typos in caller code raise instead of dropping."""
    from study_tutor.knowledge.graphiti_client import GraphitiConnectionConfig

    with pytest.raises(ValidationError):
        GraphitiConnectionConfig(
            falkor_host="h",
            falkor_port=1,
            database="d",
            embedder_url="http://x",
            surprise_field=1,
        )


# ---------------------------------------------------------------------------
# AC: get_client() returns None on each degradation branch
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_client_returns_none_when_graphiti_core_import_fails(caplog):
    from study_tutor.knowledge import graphiti_client as mod

    cfg = _make_config()
    with patch.object(
        mod,
        "_load_graphiti_core",
        side_effect=ImportError("graphiti-core not installed"),
    ):
        with caplog.at_level(logging.WARNING, logger=mod.logger.name):
            result = await mod.get_client(cfg)

    assert result is None
    matched = [
        rec
        for rec in caplog.records
        if getattr(rec, "event", None) == mod.EVENT_DEGRADED
    ]
    assert matched, "expected graphiti_client_degraded log on ImportError"
    rec = matched[0]
    assert rec.error_class == "ImportError"
    assert rec.falkor_host == cfg.falkor_host
    assert rec.degraded is True


@pytest.mark.asyncio
async def test_get_client_returns_none_when_driver_construction_fails(caplog):
    """Driver constructor raising (FalkorDB unreachable) → None + log."""
    from study_tutor.knowledge import graphiti_client as mod

    cfg = _make_config()
    fake_driver_cls = MagicMock(side_effect=ConnectionRefusedError("nope"))
    fake_graphiti_cls = MagicMock()

    with patch.object(
        mod,
        "_load_graphiti_core",
        return_value=(fake_graphiti_cls, fake_driver_cls),
    ):
        with caplog.at_level(logging.WARNING, logger=mod.logger.name):
            result = await mod.get_client(cfg)

    assert result is None
    fake_driver_cls.assert_called_once()
    fake_graphiti_cls.assert_not_called()
    assert any(
        getattr(rec, "event", None) == mod.EVENT_DEGRADED
        and rec.error_class == "ConnectionRefusedError"
        and rec.falkor_host == cfg.falkor_host
        and rec.degraded is True
        for rec in caplog.records
    )


@pytest.mark.asyncio
async def test_get_client_returns_none_when_healthcheck_times_out(caplog):
    """Healthcheck exceeding ``timeout_seconds`` → None + log."""
    from study_tutor.knowledge import graphiti_client as mod

    cfg = _make_config(timeout_seconds=0.05)

    class _SlowDriver:
        def __init__(self, host: str, port: int, database: str) -> None:
            self.host = host
            self.port = port
            self.database = database

        async def execute_query(self, q: str):
            await asyncio.sleep(1.0)  # >> 0.05s timeout

        async def close(self) -> None:
            pass

    class _SlowGraphiti:
        def __init__(self, graph_driver) -> None:
            self.driver = graph_driver

        async def close(self) -> None:
            pass

    with patch.object(
        mod,
        "_load_graphiti_core",
        return_value=(_SlowGraphiti, _SlowDriver),
    ):
        with caplog.at_level(logging.WARNING, logger=mod.logger.name):
            result = await mod.get_client(cfg)

    assert result is None
    # Two degraded logs are expected: TimeoutError from healthcheck +
    # HealthcheckFailed gate. We only assert that at least one carries
    # the canonical contract fields.
    matched = [
        rec
        for rec in caplog.records
        if getattr(rec, "event", None) == mod.EVENT_DEGRADED
    ]
    assert matched, "expected degraded log lines on healthcheck timeout"
    assert all(rec.degraded is True for rec in matched)
    assert any(rec.error_class == "TimeoutError" for rec in matched)
    assert any(rec.error_class == "HealthcheckFailed" for rec in matched)


@pytest.mark.asyncio
async def test_get_client_returns_wrapper_on_success():
    """Happy path: wrapper is returned and exposes the inner client."""
    from study_tutor.knowledge import graphiti_client as mod

    cfg = _make_config()
    with patch.object(
        mod,
        "_load_graphiti_core",
        return_value=(_FakeGraphitiOK, _FakeDriverOK),
    ):
        result = await mod.get_client(cfg)

    assert result is not None
    assert result.client_or_none is not None
    await result.close()


# ---------------------------------------------------------------------------
# AC: healthcheck() honours timeout_seconds
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_healthcheck_returns_false_when_inner_is_none():
    from study_tutor.knowledge.graphiti_client import GraphitiClient

    client = GraphitiClient(inner=None, config=_make_config())
    assert await client.healthcheck() is False


@pytest.mark.asyncio
async def test_healthcheck_returns_true_when_driver_responds():
    from study_tutor.knowledge.graphiti_client import GraphitiClient

    inner = _FakeGraphitiOK(graph_driver=_FakeDriverOK())
    client = GraphitiClient(inner=inner, config=_make_config())
    assert await client.healthcheck() is True
    assert inner.driver.calls == ["RETURN 1"]


@pytest.mark.asyncio
async def test_healthcheck_returns_false_when_driver_raises(caplog):
    from study_tutor.knowledge import graphiti_client as mod
    from study_tutor.knowledge.graphiti_client import GraphitiClient

    class _BadDriver:
        async def execute_query(self, q: str):
            raise RuntimeError("driver crashed")

    cfg = _make_config()
    inner = _FakeGraphitiOK(graph_driver=_BadDriver())
    client = GraphitiClient(inner=inner, config=cfg)

    with caplog.at_level(logging.WARNING, logger=mod.logger.name):
        assert await client.healthcheck() is False
    assert any(
        getattr(rec, "event", None) == mod.EVENT_DEGRADED
        and rec.error_class == "RuntimeError"
        and rec.falkor_host == cfg.falkor_host
        for rec in caplog.records
    )


@pytest.mark.asyncio
async def test_healthcheck_respects_short_timeout():
    """Slow driver + short timeout → False within roughly the timeout window."""
    from study_tutor.knowledge.graphiti_client import GraphitiClient

    class _SlowDriver:
        async def execute_query(self, q: str):
            await asyncio.sleep(0.5)

    inner = _FakeGraphitiOK(graph_driver=_SlowDriver())
    client = GraphitiClient(inner=inner, config=_make_config(timeout_seconds=0.05))

    started = asyncio.get_event_loop().time()
    result = await client.healthcheck()
    elapsed = asyncio.get_event_loop().time() - started

    assert result is False
    # Generous upper bound to avoid flakiness; the point is that we did NOT
    # wait the full 0.5s of the slow driver.
    assert elapsed < 0.3, f"healthcheck did not honour timeout (elapsed={elapsed}s)"


# ---------------------------------------------------------------------------
# AC: close() is idempotent and safe when client is None
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_close_is_safe_when_inner_is_none():
    from study_tutor.knowledge.graphiti_client import GraphitiClient

    client = GraphitiClient(inner=None, config=_make_config())
    await client.close()
    await client.close()  # second call must also be a no-op


@pytest.mark.asyncio
async def test_close_calls_inner_close_exactly_once_then_zeros_state():
    from study_tutor.knowledge.graphiti_client import GraphitiClient

    inner = _FakeGraphitiOK(graph_driver=_FakeDriverOK())
    inner.close = AsyncMock()
    client = GraphitiClient(inner=inner, config=_make_config())

    await client.close()
    inner.close.assert_awaited_once()

    # Idempotent: re-calling close() does not re-invoke the inner.
    await client.close()
    inner.close.assert_awaited_once()
    assert client.client_or_none is None


@pytest.mark.asyncio
async def test_close_swallows_inner_close_exceptions(caplog):
    from study_tutor.knowledge import graphiti_client as mod
    from study_tutor.knowledge.graphiti_client import GraphitiClient

    inner = _FakeGraphitiOK(graph_driver=_FakeDriverOK())
    inner.close = AsyncMock(side_effect=RuntimeError("unclean shutdown"))
    client = GraphitiClient(inner=inner, config=_make_config())

    with caplog.at_level(logging.WARNING, logger=mod.logger.name):
        await client.close()  # must not propagate

    assert client.client_or_none is None
    assert any(
        getattr(rec, "event", None) == mod.EVENT_CLOSE_ERROR
        and rec.error_class == "RuntimeError"
        for rec in caplog.records
    )


# ---------------------------------------------------------------------------
# Seam tests (§4 producer-side contracts from TASK-GSM-001)
# ---------------------------------------------------------------------------


@pytest.mark.seam
@pytest.mark.integration_contract("PydanticEntities")
def test_pydantic_entities_format():
    """Verify PydanticEntities contract is honoured by the client wrapper.

    Contract: Client returns / accepts entity instances; type imports from
    student_model.py.
    Producer: TASK-GSM-001
    """
    from study_tutor.knowledge.graphiti_client import GraphitiConnectionConfig
    from study_tutor.knowledge.student_model import Student, Topic

    assert Student is not None
    assert Topic is not None
    cfg = GraphitiConnectionConfig(
        falkor_host="localhost",
        falkor_port=6379,
        database="test",
        embedder_url="http://localhost:8001",
    )
    assert cfg.timeout_seconds == 5.0  # ASSUM-005


@pytest.mark.seam
@pytest.mark.integration_contract("GroupIdConstants")
def test_group_id_constants_format():
    """Verify GroupIdConstants contract is honoured by the client wrapper.

    Contract: All search/write calls must pass group_ids constructed from
              STUDENT_GROUP_PREFIX / SUBJECT_GROUP_PREFIX / FLEET_GROUP_ID
              — no raw string literals matching these patterns elsewhere.
    Producer: TASK-GSM-001
    """
    from study_tutor.knowledge.student_model import (
        FLEET_GROUP_ID,
        STUDENT_GROUP_PREFIX,
        SUBJECT_GROUP_PREFIX,
    )

    # Dash form per graphiti-core 0.29's group-id validator. See
    # ``student_model.py`` constant comments.
    assert STUDENT_GROUP_PREFIX == "student-"
    assert SUBJECT_GROUP_PREFIX == "subject-"
    assert FLEET_GROUP_ID == "fleet-appmilla"
