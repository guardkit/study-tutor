"""Unit tests for Wave 2 wiring builders (TASK-GR-WIRE).

Covers AC-WIRE-01 through AC-WIRE-09 from
``tasks/design_approved/TASK-GR-WIRE-...md``:

- LLM client construction with vllm + ollama providers (AC-WIRE-01)
- Embedder construction with / without explicit embedding dim (AC-WIRE-02)
- Cross-encoder sentinel attribute-access raise behaviour (AC-WIRE-03)
- Full ``get_client()`` integration test that captures the kwargs passed
  to a stubbed ``Graphiti`` class (AC-WIRE-04)
- ``OPENAI_API_KEY`` poison regression test (AC-WIRE-05)
- ``ImportError`` from the LLM/embedder loaders falls into the existing
  ``_log_degraded("ImportError", ...)`` graceful-degradation path
  (AC-WIRE-07)
- ``NotImplementedError`` for unsupported providers (AC-WIRE-01/02
  defensive gates)

All graphiti-core imports are mocked via the ``_load_*`` helper indirection
so this test file runs in any venv — the ``test_graphiti_client.py``
module-load test guards the lazy-import contract that makes this safe.
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Helpers / fakes
# ---------------------------------------------------------------------------


def _make_config(**overrides: Any):
    """Build a minimum-valid ``GraphitiConnectionConfig`` for wiring tests.

    Defaults point at the canonical local-inference fixture used by the
    seam test in the task spec — vllm provider on a local llama-swap.
    """
    from study_tutor.knowledge.graphiti_client import GraphitiConnectionConfig

    base = dict(
        falkor_host="whitestocks",
        falkor_port=6379,
        database="study_tutor",
        llm_provider="vllm",
        llm_base_url="http://promaxgb10-41b1:9000/v1",
        llm_model="qwen-graphiti",
        llm_max_tokens=4096,
        embedding_provider="vllm",
        embedding_base_url="http://promaxgb10-41b1:9000/v1",
        embedding_model="nomic-embed",
        embedder_url="http://promaxgb10-41b1:9000/v1",
    )
    base.update(overrides)
    return GraphitiConnectionConfig(**base)


class _FakeLLMConfig:
    """Stand-in for graphiti-core's ``LLMConfig`` dataclass.

    Captures the kwargs the builder passes through so tests can assert on
    ``base_url``, ``model``, and ``api_key`` directly.
    """

    def __init__(self, **kwargs: Any) -> None:
        self.base_url = kwargs.get("base_url")
        self.model = kwargs.get("model")
        self.api_key = kwargs.get("api_key")


class _FakeOpenAIGenericClient:
    """Stand-in for graphiti-core's ``OpenAIGenericClient``."""

    def __init__(self, *, config: _FakeLLMConfig, **kwargs: Any) -> None:
        self.config = config
        self.max_tokens = kwargs.get("max_tokens")


class _FakeOpenAIEmbedderConfig:
    """Stand-in for graphiti-core's ``OpenAIEmbedderConfig``."""

    def __init__(self, **kwargs: Any) -> None:
        self.base_url = kwargs.get("base_url")
        self.embedding_model = kwargs.get("embedding_model")
        self.api_key = kwargs.get("api_key")
        # Distinguish explicit-None from never-passed: tests inspect
        # ``has_embedding_dim`` to verify AC-WIRE-02's contract.
        self.has_embedding_dim = "embedding_dim" in kwargs
        self.embedding_dim = kwargs.get("embedding_dim")


class _FakeOpenAIEmbedder:
    """Stand-in for graphiti-core's ``OpenAIEmbedder``."""

    def __init__(self, *, config: _FakeOpenAIEmbedderConfig) -> None:
        self.config = config


class _CapturingGraphiti:
    """Captures kwargs passed to ``Graphiti.__init__``.

    Used by the AC-WIRE-04 integration test to assert that
    ``get_client()`` actually wires ``llm_client``, ``embedder``, and
    ``cross_encoder`` through to the constructor.
    """

    last_kwargs: dict[str, Any] | None = None

    def __init__(self, **kwargs: Any) -> None:
        # Mirror the live ``driver`` attribute so the wrapper's
        # healthcheck path (which probes ``inner.driver``) can find it.
        self.driver = kwargs.get("graph_driver")
        type(self).last_kwargs = kwargs

    async def close(self) -> None:  # pragma: no cover - close path tested elsewhere
        pass


class _FakeFalkorDriver:
    """Stand-in for graphiti-core's ``FalkorDriver`` with a green ping."""

    def __init__(self, host: str, port: int, database: str) -> None:
        self.host = host
        self.port = port
        self.database = database

    async def execute_query(self, query: str) -> list[dict[str, int]]:
        return [{"v": 1}]

    async def close(self) -> None:  # pragma: no cover
        pass


# ---------------------------------------------------------------------------
# AC-WIRE-01: _build_llm_client
# ---------------------------------------------------------------------------


def test_build_llm_client_vllm_provider_returns_configured_client():
    """vllm provider → OpenAIGenericClient with placeholder api_key."""
    from study_tutor.knowledge import graphiti_client as gc

    config = _make_config(llm_provider="vllm")
    with patch.object(
        gc,
        "_load_llm_client_classes",
        return_value=(_FakeOpenAIGenericClient, _FakeLLMConfig),
    ):
        client = gc._build_llm_client(config)

    assert isinstance(client, _FakeOpenAIGenericClient)
    assert client.config.api_key == "local-key", (
        "AC-WIRE-05: api_key must be the placeholder, never OPENAI_API_KEY"
    )
    assert client.config.base_url == "http://promaxgb10-41b1:9000/v1"
    assert client.config.model == "qwen-graphiti"
    assert client.max_tokens == 4096


def test_build_llm_client_ollama_provider_returns_configured_client():
    """ollama provider also accepted; same builder path."""
    from study_tutor.knowledge import graphiti_client as gc

    config = _make_config(
        llm_provider="ollama",
        llm_base_url="http://localhost:11434/v1",
        llm_model="llama3",
        llm_max_tokens=None,  # exercise the "max_tokens omitted" branch
    )
    with patch.object(
        gc,
        "_load_llm_client_classes",
        return_value=(_FakeOpenAIGenericClient, _FakeLLMConfig),
    ):
        client = gc._build_llm_client(config)

    assert client.config.base_url == "http://localhost:11434/v1"
    assert client.config.model == "llama3"
    assert client.max_tokens is None, (
        "max_tokens must NOT be passed when llm_max_tokens is None — "
        "graphiti-core's signature would reject None"
    )


def test_build_llm_client_rejects_unknown_provider():
    """Defensive gate: unsupported provider → NotImplementedError."""
    from study_tutor.knowledge import graphiti_client as gc

    # Bypass model_config validators by mutating after construction —
    # the YAML loader rejects cloud providers, so the only way to
    # reach this branch is a hand-constructed config with a bogus
    # provider value.
    config = _make_config()
    object.__setattr__(config, "llm_provider", "anthropic")

    with pytest.raises(NotImplementedError, match="anthropic"):
        gc._build_llm_client(config)


# ---------------------------------------------------------------------------
# AC-WIRE-02: _build_embedder
# ---------------------------------------------------------------------------


def test_build_embedder_with_explicit_embedding_dim():
    """When YAML sets embedding_dimensions, embedder_config gets embedding_dim."""
    from study_tutor.knowledge import graphiti_client as gc

    config = _make_config(embedding_dimensions=768)
    with patch.object(
        gc,
        "_load_embedder_classes",
        return_value=(_FakeOpenAIEmbedder, _FakeOpenAIEmbedderConfig),
    ):
        embedder = gc._build_embedder(config)

    assert embedder.config.has_embedding_dim is True
    assert embedder.config.embedding_dim == 768
    assert embedder.config.api_key == "local-key"


def test_build_embedder_without_explicit_embedding_dim():
    """When YAML omits embedding_dimensions, embedding_dim is NOT passed."""
    from study_tutor.knowledge import graphiti_client as gc

    config = _make_config(embedding_dimensions=None)
    with patch.object(
        gc,
        "_load_embedder_classes",
        return_value=(_FakeOpenAIEmbedder, _FakeOpenAIEmbedderConfig),
    ):
        embedder = gc._build_embedder(config)

    assert embedder.config.has_embedding_dim is False, (
        "AC-WIRE-02: must pass embedding_dim ONLY when explicitly set; "
        "synthesising a default would risk silent shape mismatch"
    )


def test_build_embedder_rejects_unknown_provider():
    """Defensive gate on the embedder path mirrors the LLM path."""
    from study_tutor.knowledge import graphiti_client as gc

    config = _make_config()
    object.__setattr__(config, "embedding_provider", "voyage")

    with pytest.raises(NotImplementedError, match="voyage"):
        gc._build_embedder(config)


# ---------------------------------------------------------------------------
# AC-WIRE-03: cross-encoder sentinel
# ---------------------------------------------------------------------------


def test_cross_encoder_sentinel_construction_does_not_raise():
    """Sentinel must be constructible — only access raises."""
    from study_tutor.knowledge.graphiti_client import _build_cross_encoder_sentinel

    sentinel = _build_cross_encoder_sentinel()
    # ``isinstance`` / ``type`` / ``repr`` must remain safe so graphiti-core
    # internals can hold a reference without tripping the raise.
    assert sentinel is not None
    assert "DECISION-DF-001" in repr(sentinel)


def test_cross_encoder_sentinel_raises_on_attribute_access():
    """Any user-defined attribute access raises with the canonical message."""
    from study_tutor.knowledge.graphiti_client import _build_cross_encoder_sentinel

    sentinel = _build_cross_encoder_sentinel()
    with pytest.raises(RuntimeError, match="DECISION-DF-001"):
        sentinel.predict(["query"], ["doc"])


def test_cross_encoder_sentinel_raises_on_arbitrary_method_name():
    """Sentinel is opaque — ``rank``, ``score``, anything raises."""
    from study_tutor.knowledge.graphiti_client import _build_cross_encoder_sentinel

    sentinel = _build_cross_encoder_sentinel()
    with pytest.raises(RuntimeError, match="DECISION-DF-001"):
        sentinel.rank
    with pytest.raises(RuntimeError, match="DECISION-DF-001"):
        sentinel.some_attribute_that_does_not_exist


# ---------------------------------------------------------------------------
# AC-WIRE-04: get_client wires all three into Graphiti
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_client_passes_llm_embedder_and_sentinel_to_graphiti():
    """get_client() must construct Graphiti(graph_driver=, llm_client=, embedder=, cross_encoder=)."""
    from study_tutor.knowledge import graphiti_client as gc

    config = _make_config()

    with (
        patch.object(
            gc,
            "_load_graphiti_core",
            return_value=(_CapturingGraphiti, _FakeFalkorDriver),
        ),
        patch.object(
            gc,
            "_load_llm_client_classes",
            return_value=(_FakeOpenAIGenericClient, _FakeLLMConfig),
        ),
        patch.object(
            gc,
            "_load_embedder_classes",
            return_value=(_FakeOpenAIEmbedder, _FakeOpenAIEmbedderConfig),
        ),
    ):
        wrapper = await gc.get_client(config)

    assert wrapper is not None, "stubbed driver pings green; wrapper must exist"
    captured = _CapturingGraphiti.last_kwargs
    assert captured is not None

    assert "graph_driver" in captured
    assert isinstance(captured["graph_driver"], _FakeFalkorDriver)

    assert captured["llm_client"] is not None
    assert isinstance(captured["llm_client"], _FakeOpenAIGenericClient)

    assert captured["embedder"] is not None
    assert isinstance(captured["embedder"], _FakeOpenAIEmbedder)

    # Cross-encoder must be the sentinel (not None — that would re-trigger
    # graphiti-core's default OpenAI cross-encoder construction).
    assert captured["cross_encoder"] is not None
    with pytest.raises(RuntimeError, match="DECISION-DF-001"):
        captured["cross_encoder"].predict


# ---------------------------------------------------------------------------
# AC-WIRE-05: OPENAI_API_KEY must never be read
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_client_ignores_poisoned_openai_api_key(monkeypatch):
    """Setting OPENAI_API_KEY to a poison value must not affect wiring.

    If any code path under ``src/study_tutor/knowledge/`` consumed the env
    var, the captured ``LLMConfig.api_key`` would be the poison string
    rather than the canonical ``"local-key"`` placeholder.
    """
    from study_tutor.knowledge import graphiti_client as gc

    monkeypatch.setenv("OPENAI_API_KEY", "poison-this-must-not-be-used")
    config = _make_config()

    with (
        patch.object(
            gc,
            "_load_graphiti_core",
            return_value=(_CapturingGraphiti, _FakeFalkorDriver),
        ),
        patch.object(
            gc,
            "_load_llm_client_classes",
            return_value=(_FakeOpenAIGenericClient, _FakeLLMConfig),
        ),
        patch.object(
            gc,
            "_load_embedder_classes",
            return_value=(_FakeOpenAIEmbedder, _FakeOpenAIEmbedderConfig),
        ),
    ):
        wrapper = await gc.get_client(config)

    assert wrapper is not None
    captured = _CapturingGraphiti.last_kwargs
    assert captured["llm_client"].config.api_key == "local-key"
    assert captured["embedder"].config.api_key == "local-key"
    # Belt-and-braces: the poison value must not appear anywhere in the
    # captured constructor kwargs.
    assert "poison-this-must-not-be-used" not in repr(captured)


# ---------------------------------------------------------------------------
# AC-WIRE-07: ImportError funnels through _log_degraded
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_client_returns_none_when_llm_client_import_fails(caplog):
    """ImportError from LLM-class loader → _log_degraded("ImportError", ...) + return None."""
    import logging

    from study_tutor.knowledge import graphiti_client as gc

    config = _make_config()

    def _raise_import_error() -> tuple[Any, Any]:
        raise ImportError("graphiti_core.llm_client.openai_generic_client missing")

    with (
        patch.object(
            gc,
            "_load_graphiti_core",
            return_value=(_CapturingGraphiti, _FakeFalkorDriver),
        ),
        patch.object(
            gc, "_load_llm_client_classes", side_effect=_raise_import_error
        ),
        caplog.at_level(logging.WARNING, logger="study_tutor.knowledge.graphiti_client"),
    ):
        result = await gc.get_client(config)

    assert result is None
    # The degradation log must carry error_class=ImportError so log
    # readers grep on the same field shape regardless of which import
    # failed (AC-WIRE-07).
    degraded_records = [
        rec
        for rec in caplog.records
        if getattr(rec, "event", None) == gc.EVENT_DEGRADED
        and getattr(rec, "error_class", None) == "ImportError"
    ]
    assert degraded_records, (
        "expected an event=graphiti_client_degraded record with "
        "error_class=ImportError"
    )


@pytest.mark.asyncio
async def test_get_client_returns_none_on_unsupported_provider(caplog):
    """Hand-constructed bogus provider → NotImplementedError → degraded + None."""
    import logging

    from study_tutor.knowledge import graphiti_client as gc

    config = _make_config()
    object.__setattr__(config, "llm_provider", "anthropic")

    with (
        patch.object(
            gc,
            "_load_graphiti_core",
            return_value=(_CapturingGraphiti, _FakeFalkorDriver),
        ),
        caplog.at_level(logging.WARNING, logger="study_tutor.knowledge.graphiti_client"),
    ):
        result = await gc.get_client(config)

    assert result is None
    degraded = [
        rec
        for rec in caplog.records
        if getattr(rec, "error_class", None) == "NotImplementedError"
    ]
    assert degraded, "expected NotImplementedError degradation log"


# ---------------------------------------------------------------------------
# AC-WIRE-05 module-level audit: no os.environ.get("OPENAI_API_KEY") anywhere
# ---------------------------------------------------------------------------


def test_no_openai_api_key_lookup_in_knowledge_module_source():
    """Static check: no code path under graphiti_client.py reads OPENAI_API_KEY."""
    import inspect

    from study_tutor.knowledge import graphiti_client

    src = inspect.getsource(graphiti_client)
    # Comments and docstrings naming the env var (for explanatory
    # purposes) are fine; what we forbid is an actual lookup.
    forbidden_patterns = (
        'os.environ.get("OPENAI_API_KEY"',
        "os.environ.get('OPENAI_API_KEY'",
        'os.environ["OPENAI_API_KEY"]',
        "os.environ['OPENAI_API_KEY']",
        'os.getenv("OPENAI_API_KEY"',
        "os.getenv('OPENAI_API_KEY'",
    )
    for pattern in forbidden_patterns:
        assert pattern not in src, (
            f"AC-WIRE-05 violated: graphiti_client.py reads OPENAI_API_KEY "
            f"via {pattern!r}"
        )


# ---------------------------------------------------------------------------
# Test hygiene: ensure the env-poisoning test doesn't leak across tests
# ---------------------------------------------------------------------------


def test_env_isolation_smoke():
    """Sanity: OPENAI_API_KEY isn't lingering from an earlier monkeypatched test."""
    # Pytest's ``monkeypatch`` fixture rolls back automatically; this
    # test exists only to make a future regression in fixture handling
    # immediately visible rather than as a flaky failure of the
    # poison-key test.
    assert os.environ.get("OPENAI_API_KEY") != "poison-this-must-not-be-used"
