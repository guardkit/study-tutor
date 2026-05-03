"""Graphiti client wrapper with lazy import and graceful degradation.

FEAT-1773 / TASK-GSM-003 — owns the lifecycle of a ``graphiti-core`` client
talking to FalkorDB on the Synology NAS. The module has two load-bearing
properties:

1. **Lazy import** (LES1 §3 + Group D ``@module-load`` scenario in the
   feature spec) — the module loads successfully even when ``graphiti-core``
   is not installed. ``import graphiti_core`` happens *inside* the
   ``_load_graphiti_core`` helper, never at module top level. A top-level
   ``try: import graphiti_core`` would still execute at import time and
   could surface import-side-effect failures into every caller that just
   wanted to introspect ``GraphitiConnectionConfig``.

2. **Graceful degradation** — when the wrapped client cannot be constructed
   (library absent, FalkorDB unreachable, healthcheck times out, config
   rejected), :func:`get_client` returns ``None`` and emits a structured
   warning log with ``event=graphiti_client_degraded``. Callers MUST handle
   the ``None`` case without raising. This is the same shape used by the
   sibling ``specialist-agent`` repo's
   ``specialist_agent/tools/graphiti_client.py`` lazy-import pattern, which
   is the canonical reference for this module.

Scope (per task):

- :class:`GraphitiConnectionConfig` — Pydantic v2 config dataclass for
  FalkorDB host/port/database, LLM provider/model, embedder URL, and
  ``timeout_seconds`` (default ``5.0`` per ASSUM-005).
- :class:`GraphitiClient` — thin wrapper exposing only ``healthcheck()``,
  ``close()``, and the ``client_or_none`` property. Domain operations such
  as ``add_episode`` / ``search_*`` are deliberately **out of scope** —
  TASK-GSM-004 owns the write path and TASK-GSM-005 owns the query helpers.
- :func:`get_client` — async factory implementing the four-step degradation
  path: import → construct → healthcheck → return wrapper.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)


# Structured-log event identifiers. Kept as module constants so call sites
# (and downstream log-grepping) reference a single source of truth.
EVENT_DEGRADED = "graphiti_client_degraded"
EVENT_READY = "graphiti_client_ready"
EVENT_CLOSE_ERROR = "graphiti_client_close_error"
EVENT_CLOUD_PROVIDER_REJECTED = "cloud_provider_rejected"


# Default path to the GuardKit-canonical Graphiti config file. Resolved
# relative to the process working directory so callers running from the
# repo root pick up ``.guardkit/graphiti.yaml`` without further plumbing.
DEFAULT_GRAPHITI_YAML_PATH = Path(".guardkit/graphiti.yaml")


# DECISION-DF-001 cloud-provider blocklist. The dark-factory line of
# reasoning (see DECISION-DF-001) is that learner conversations must never
# leave local infrastructure, so any caller that tries to point Graphiti at
# OpenAI / Gemini for entity extraction or embedding is rejected at
# load-time with a structured log line. Note that ``gemini`` is rejected
# only on the LLM path — embedding via Gemini is not supported by
# graphiti-core today, so we omit it from the embedding blocklist to keep
# the rejection set tight.
_REJECTED_LLM_PROVIDERS = frozenset({"openai", "gemini"})
_REJECTED_EMBEDDING_PROVIDERS = frozenset({"openai"})


class GraphitiConnectionConfig(BaseModel):
    """Pydantic v2 config for the Graphiti/FalkorDB client.

    Strict (``extra="forbid"``) so that typos in caller code surface as
    ``ValidationError`` rather than silently dropped fields. Defaults for
    LLM provider/model/timeout encode the ASSUM-005 contract; callers may
    override but the canonical Phase-1 values live here.

    Fields:
        falkor_host: FalkorDB hostname (Synology NAS IP or DNS name).
        falkor_port: FalkorDB Redis-protocol port. Must be ``> 0``.
        database: FalkorDB graph name.
        llm_provider: Backing LLM provider for graphiti-core. Default is
            ``"vllm"`` per AC-LOAD-05 / DECISION-DF-001 — a bare
            ``GraphitiConnectionConfig()`` must not silently route through
            a cloud provider, so the default points at the local vLLM
            stack. Cloud providers (``"openai"``, ``"gemini"``) are
            rejected at load-time by
            :func:`load_graphiti_config_from_yaml`.
        llm_base_url: HTTP base URL for the LLM provider (required when
            ``llm_provider`` is ``"vllm"`` or ``"ollama"``; ``None`` for
            providers that infer their own endpoint).
        llm_model: LLM model identifier. Default ``"qwen-graphiti"`` per
            AC-LOAD-05 — points at the local vLLM-served Qwen model
            rather than a Gemini model so a bare-default construction
            cannot silently leak Gemini.
        llm_max_tokens: Optional cap on output tokens for chunked
            extraction. ``None`` defers to the provider's own default.
        embedder_url: Legacy HTTP URL of the local embedder service.
            Preserved for backwards compatibility with the in-flight
            Phase-1 fixes (commits ``a210472``, ``78d3498``, ``732672c``)
            that constructed configs by hand. New callers should use
            ``embedding_base_url`` instead;
            :func:`load_graphiti_config_from_yaml` derives this field
            from ``embedding_base_url`` when only the latter is set.
        embedding_provider: Backing embedding provider. Default
            ``"vllm"`` for the same DECISION-DF-001 reasoning as
            ``llm_provider``.
        embedding_base_url: HTTP base URL for the embedding provider.
        embedding_model: Embedding model identifier (e.g.
            ``"nomic-embed"``).
        embedding_dimensions: Optional explicit embedding vector
            dimensions. Set only when overriding the model's native
            dimension (e.g. Matryoshka truncation).
        chunk_extraction_concurrency: Max concurrent chunk-extraction
            calls graphiti-core may issue. Mirrors the YAML field of the
            same name; default ``4``.
        timeout_seconds: Healthcheck timeout in seconds. Default ``5.0``
            per ASSUM-005. Must be strictly positive.
    """

    model_config = ConfigDict(extra="forbid")

    falkor_host: str = Field(min_length=1)
    falkor_port: int = Field(gt=0)
    database: str = Field(min_length=1)
    # AC-LOAD-05: defaults migrated from gemini → vllm / qwen-graphiti so a
    # bare ``GraphitiConnectionConfig()`` cannot silently leak Gemini even
    # if a caller bypasses :func:`load_graphiti_config_from_yaml`.
    llm_provider: str = "vllm"
    llm_base_url: str | None = None
    llm_model: str = "qwen-graphiti"
    llm_max_tokens: int | None = None
    embedder_url: str = Field(min_length=1)
    embedding_provider: str = "vllm"
    embedding_base_url: str | None = None
    embedding_model: str | None = None
    embedding_dimensions: int | None = None
    chunk_extraction_concurrency: int = Field(default=4, gt=0)
    timeout_seconds: float = Field(default=5.0, gt=0)


# ---------------------------------------------------------------------------
# YAML loader (TASK-GR-LOAD)
# ---------------------------------------------------------------------------


# Mapping from YAML field name → ``GraphitiConnectionConfig`` field name
# for keys whose names diverge between the GuardKit-canonical YAML schema
# and the Phase-1 runtime model. Keys that match on both sides are handled
# by ``_DIRECT_YAML_KEYS`` below.
_YAML_TO_MODEL_RENAMES: dict[str, str] = {
    "falkordb_host": "falkor_host",
    "falkordb_port": "falkor_port",
    "timeout": "timeout_seconds",
    # ``project_id`` in the YAML doubles as the FalkorDB graph name in the
    # runtime model — single source of truth at the YAML layer.
    "project_id": "database",
}

# YAML keys that map 1:1 to model fields with the same name.
_DIRECT_YAML_KEYS: tuple[str, ...] = (
    "llm_provider",
    "llm_base_url",
    "llm_model",
    "llm_max_tokens",
    "embedding_provider",
    "embedding_base_url",
    "embedding_model",
    "embedding_dimensions",
    "chunk_extraction_concurrency",
)


# Environment variable → (model field name, type coercer). Mirrors the
# documented contract in the YAML header and the sibling GuardKit loader so
# operators get the same override shape across both repos.
_ENV_OVERRIDES: dict[str, tuple[str, type]] = {
    "FALKORDB_HOST": ("falkor_host", str),
    "FALKORDB_PORT": ("falkor_port", int),
    "GRAPHITI_TIMEOUT": ("timeout_seconds", float),
    "LLM_PROVIDER": ("llm_provider", str),
    "LLM_BASE_URL": ("llm_base_url", str),
    "LLM_MODEL": ("llm_model", str),
    "LLM_MAX_TOKENS": ("llm_max_tokens", int),
    "EMBEDDING_PROVIDER": ("embedding_provider", str),
    "EMBEDDING_BASE_URL": ("embedding_base_url", str),
    "EMBEDDING_MODEL": ("embedding_model", str),
    "EMBEDDING_DIMENSIONS": ("embedding_dimensions", int),
    "CHUNK_EXTRACTION_CONCURRENCY": ("chunk_extraction_concurrency", int),
}


def _enforce_decision_df_001(config: dict[str, Any]) -> None:
    """Reject cloud LLM/embedding providers per DECISION-DF-001.

    Raises ``ValueError`` with the canonical message and emits a
    structured ``event=cloud_provider_rejected`` log line so the
    rejection is observable in production logs without having to grep for
    a specific traceback shape. The guard runs at load time — *before*
    the ``GraphitiConnectionConfig`` constructor — so callers cannot
    accidentally hold a cloud-pointing config object even transiently.
    """
    llm_provider = config.get("llm_provider")
    if isinstance(llm_provider, str) and llm_provider in _REJECTED_LLM_PROVIDERS:
        logger.error(
            "cloud LLM provider rejected per DECISION-DF-001: %s",
            llm_provider,
            extra={
                "event": EVENT_CLOUD_PROVIDER_REJECTED,
                "llm_provider": llm_provider,
                "rejected_field": "llm_provider",
            },
        )
        raise ValueError("cloud LLM providers disabled per DECISION-DF-001")

    embedding_provider = config.get("embedding_provider")
    if (
        isinstance(embedding_provider, str)
        and embedding_provider in _REJECTED_EMBEDDING_PROVIDERS
    ):
        logger.error(
            "cloud embedding provider rejected per DECISION-DF-001: %s",
            embedding_provider,
            extra={
                "event": EVENT_CLOUD_PROVIDER_REJECTED,
                "embedding_provider": embedding_provider,
                "rejected_field": "embedding_provider",
            },
        )
        raise ValueError("cloud LLM providers disabled per DECISION-DF-001")


def _coerce_env_value(raw: str, target_type: type, env_var: str) -> Any:
    """Coerce a string env-var value into ``target_type``.

    Boundary helper for env overrides. Raises ``ValueError`` with a
    contextual message when the conversion is impossible — operators
    should see *which* env var is broken, not just a bare ``int()``
    traceback.
    """
    try:
        if target_type is int:
            return int(raw)
        if target_type is float:
            return float(raw)
        return raw
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"environment variable {env_var}={raw!r} cannot be coerced to "
            f"{target_type.__name__}: {exc}"
        ) from exc


def _apply_env_overrides(config: dict[str, Any]) -> None:
    """Merge documented env-var overrides on top of YAML/defaults.

    Env-var precedence beats YAML by design — operators tweaking a single
    box (FalkorDB host, model name) shouldn't have to edit the
    project-checked-in YAML. Unknown env vars are silently ignored so
    unrelated environment noise doesn't blow up config load.
    """
    for env_var, (field_name, target_type) in _ENV_OVERRIDES.items():
        raw = os.environ.get(env_var)
        if raw is None:
            continue
        config[field_name] = _coerce_env_value(raw, target_type, env_var)


def load_graphiti_config_from_yaml(
    path: Path = DEFAULT_GRAPHITI_YAML_PATH,
) -> GraphitiConnectionConfig:
    """Load a :class:`GraphitiConnectionConfig` from the canonical YAML.

    Bridges the GuardKit-canonical ``.guardkit/graphiti.yaml`` schema (the
    source of truth for both the GuardKit and study-tutor projects) into
    the Phase-1 runtime model. Env vars listed in
    :data:`_ENV_OVERRIDES` take precedence over YAML values.

    DECISION-DF-001 is enforced *before* the model constructor runs:
    ``llm_provider in {"openai", "gemini"}`` or
    ``embedding_provider == "openai"`` raises ``ValueError`` with the
    canonical message and emits an ``event=cloud_provider_rejected`` log
    line. The same loader cannot be used to construct a cloud-pointing
    config — that's the whole point of the guard living here rather than
    at the call site.

    Args:
        path: Path to the YAML file. Defaults to
            ``Path(".guardkit/graphiti.yaml")`` resolved against the
            process cwd.

    Returns:
        A fully validated :class:`GraphitiConnectionConfig`.

    Raises:
        FileNotFoundError: When ``path`` does not exist. Deliberately
            loud — silently defaulting to a baked-in config is exactly
            the failure mode that motivated this task (Phase-1's silent
            OpenAI fallback). See AC-LOAD-06 for the rationale.
        ValueError: When the YAML deserialises to anything other than a
            mapping, or when a cloud provider is configured.
        pydantic.ValidationError: When required fields are missing or
            field-level validators reject the projected config.
    """
    if not path.exists():
        raise FileNotFoundError(
            f"graphiti config not found at {path!s}. Refusing to silently "
            "fall back to defaults — see DECISION-DF-001 / AC-LOAD-06. "
            "Run from the project root or pass an explicit path."
        )

    raw_yaml = yaml.safe_load(path.read_text()) or {}
    if not isinstance(raw_yaml, dict):
        raise ValueError(
            f"graphiti config at {path!s} must deserialise to a YAML "
            f"mapping; got {type(raw_yaml).__name__}"
        )

    config: dict[str, Any] = {}

    for yaml_key, model_key in _YAML_TO_MODEL_RENAMES.items():
        if yaml_key in raw_yaml and raw_yaml[yaml_key] is not None:
            config[model_key] = raw_yaml[yaml_key]

    for key in _DIRECT_YAML_KEYS:
        if key in raw_yaml and raw_yaml[key] is not None:
            config[key] = raw_yaml[key]

    # Env vars override YAML values.
    _apply_env_overrides(config)

    # DECISION-DF-001 guard fires before the model constructor — callers
    # never see a cloud-pointing config object, even transiently.
    _enforce_decision_df_001(config)

    # Backwards-compat: the legacy ``embedder_url`` field is required
    # (min_length=1). When the YAML only specifies ``embedding_base_url``
    # (the canonical name), mirror it into ``embedder_url`` so existing
    # Phase-1 call sites continue to work without modification. Tests
    # that need divergent values can still set both explicitly.
    if "embedder_url" not in config and config.get("embedding_base_url"):
        config["embedder_url"] = config["embedding_base_url"]

    return GraphitiConnectionConfig(**config)


def _log_degraded(
    error_class: str,
    host: str,
    *,
    latency_ms: int | None = None,
    error_message: str | None = None,
) -> None:
    """Emit the canonical ``graphiti_client_degraded`` warning record.

    All degradation paths in this module funnel through this helper so that
    log-line shape (``event``, ``error_class``, ``falkor_host``,
    ``degraded``, optional ``latency_ms``) stays uniform — that uniformity
    is what makes the Group-D ``@module-load`` scenario observable in
    production logs.
    """
    extra: dict[str, Any] = {
        "event": EVENT_DEGRADED,
        "error_class": error_class,
        "falkor_host": host,
        "degraded": True,
    }
    if latency_ms is not None:
        extra["latency_ms"] = latency_ms
    if error_message is not None:
        extra["error_message"] = error_message
    logger.warning("graphiti client degraded: %s", error_class, extra=extra)


def _load_graphiti_core() -> tuple[Any, Any]:
    """Lazy-import ``graphiti-core`` symbols at call time.

    Pulled out as a named helper so unit tests can patch it cleanly without
    monkey-patching ``builtins.__import__``. Returning a tuple keeps the
    factory's call site flat. A real call returns
    ``(Graphiti, FalkorDriver)``; tests may inject fakes with the same
    constructor signature.

    Raises:
        ImportError: When ``graphiti-core`` is not installed in the active
            interpreter, or when its falkordb driver path is unavailable.
    """
    from graphiti_core import Graphiti  # type: ignore[import-not-found]
    from graphiti_core.driver.falkordb_driver import (  # type: ignore[import-not-found]
        FalkorDriver,
    )

    return Graphiti, FalkorDriver


# ---------------------------------------------------------------------------
# Wave 2 builders (TASK-GR-WIRE)
# ---------------------------------------------------------------------------


# Provider whitelist for the LLM/embedder builders. Cloud providers are
# already rejected at YAML-load time by :func:`_enforce_decision_df_001`
# (see DECISION-DF-001); this whitelist is the defensive belt-and-braces
# gate AC-WIRE-01/02 require, so a caller that hand-constructs a config
# (bypassing the YAML loader) still cannot route through cloud providers.
_LOCAL_INFERENCE_PROVIDERS = frozenset({"vllm", "ollama"})


def _load_llm_client_classes() -> tuple[Any, Any]:
    """Lazy-import ``OpenAIGenericClient`` + ``LLMConfig`` at call time.

    Mirrors :func:`_load_graphiti_core`'s patch-friendly contract — unit
    tests under :mod:`tests.unit.knowledge.test_graphiti_client_wiring`
    monkey-patch this helper to inject doubles with the same constructor
    surface graphiti-core 0.29 ships.

    Raises:
        ImportError: When ``graphiti-core`` is not installed, or when the
            ``openai_generic_client`` module path drifted in a
            graphiti-core minor bump (AC-WIRE-06's pin guards against
            this; the ImportError still falls into ``get_client``'s
            graceful-degradation path per AC-WIRE-07).
    """
    from graphiti_core.llm_client import (  # type: ignore[import-not-found]
        LLMConfig,
    )
    from graphiti_core.llm_client.openai_generic_client import (  # type: ignore[import-not-found]
        OpenAIGenericClient,
    )

    return OpenAIGenericClient, LLMConfig


def _load_embedder_classes() -> tuple[Any, Any]:
    """Lazy-import ``OpenAIEmbedder`` + ``OpenAIEmbedderConfig`` at call time.

    Same patch-friendly shape as :func:`_load_llm_client_classes`. The
    embedder package re-exports both symbols at the package root in
    graphiti-core 0.29, so we import from ``graphiti_core.embedder``
    rather than the deeper ``graphiti_core.embedder.openai`` module path
    that AC-WIRE-02 names — the package re-export is the canonical
    surface used by GuardKit's reference implementation and is the path
    most resilient to internal module renames.

    Raises:
        ImportError: When ``graphiti-core`` is not installed.
    """
    from graphiti_core.embedder import (  # type: ignore[import-not-found]
        OpenAIEmbedder,
        OpenAIEmbedderConfig,
    )

    return OpenAIEmbedder, OpenAIEmbedderConfig


def _build_llm_client(config: GraphitiConnectionConfig) -> Any:
    """Construct the ``OpenAIGenericClient`` that drives entity extraction.

    Mirrors GuardKit's
    ``guardkit/guardkit/knowledge/graphiti_client.py::_build_llm_client``
    canonical pattern. The placeholder ``api_key="local-key"`` is required
    by the OpenAI SDK's parameter validation but is never sent on the
    wire by the local inference stack (vLLM / Ollama / llama-swap ignore
    Authorization headers). AC-WIRE-05 forbids reading
    ``OPENAI_API_KEY`` here — using the env var would re-introduce
    exactly the cloud-leak failure mode this feature exists to close.

    Args:
        config: The validated :class:`GraphitiConnectionConfig`. Only
            ``llm_provider`` ∈ ``{"vllm", "ollama"}`` is accepted; the
            YAML loader already rejected ``openai`` / ``gemini`` per
            DECISION-DF-001, but the guard repeats defensively here so a
            hand-constructed config cannot bypass the policy.

    Returns:
        A graphiti-core ``OpenAIGenericClient`` instance configured to
        talk to the local inference base URL.

    Raises:
        NotImplementedError: When ``config.llm_provider`` is anything
            other than ``"vllm"`` or ``"ollama"``. This is the
            belt-and-braces gate AC-WIRE-01 specifies.
        ImportError: Propagated from :func:`_load_llm_client_classes`
            when graphiti-core is uninstalled. :func:`get_client`
            catches and routes through ``_log_degraded`` per AC-WIRE-07.
    """
    if config.llm_provider not in _LOCAL_INFERENCE_PROVIDERS:
        raise NotImplementedError(
            f"llm_provider={config.llm_provider!r} is not supported by "
            "_build_llm_client; only local OpenAI-compatible providers "
            "(vllm, ollama) are wired. Cloud providers are rejected at "
            "load time per DECISION-DF-001."
        )

    openai_generic_client_cls, llm_config_cls = _load_llm_client_classes()

    llm_config = llm_config_cls(
        base_url=config.llm_base_url,
        model=config.llm_model,
        # ``"local-key"`` is the canonical placeholder used by GuardKit's
        # reference implementation. Never read OPENAI_API_KEY here —
        # AC-WIRE-05's regression test poisons that env var to prove no
        # code path under ``src/study_tutor/knowledge/`` consumes it.
        api_key="local-key",
    )

    # ``max_tokens`` is only set when the YAML/env path populated it.
    # graphiti-core's default cap is conservative; passing ``None`` would
    # be rejected by the constructor's ``int``-typed signature.
    builder_kwargs: dict[str, Any] = {}
    if config.llm_max_tokens is not None:
        builder_kwargs["max_tokens"] = config.llm_max_tokens

    return openai_generic_client_cls(config=llm_config, **builder_kwargs)


def _build_embedder(config: GraphitiConnectionConfig) -> Any:
    """Construct the ``OpenAIEmbedder`` that drives vector embeddings.

    Same defensive provider gate as :func:`_build_llm_client`. The
    explicit-dimension handling (AC-WIRE-02) is load-bearing: passing a
    dimension when the YAML didn't specify one (e.g. synthesising a
    "default" 1536) is exactly how silent shape-mismatch bugs creep into
    a FalkorDB-backed vector index. We pass ``embedding_dim`` only when
    the loader populated it.

    Args:
        config: The validated :class:`GraphitiConnectionConfig`.

    Returns:
        A graphiti-core ``OpenAIEmbedder`` instance.

    Raises:
        NotImplementedError: When ``config.embedding_provider`` is
            anything other than ``"vllm"`` or ``"ollama"``.
        ImportError: Propagated from :func:`_load_embedder_classes`.
    """
    if config.embedding_provider not in _LOCAL_INFERENCE_PROVIDERS:
        raise NotImplementedError(
            f"embedding_provider={config.embedding_provider!r} is not "
            "supported by _build_embedder; only local OpenAI-compatible "
            "providers (vllm, ollama) are wired. Cloud providers are "
            "rejected at load time per DECISION-DF-001."
        )

    openai_embedder_cls, openai_embedder_config_cls = _load_embedder_classes()

    embedder_config_kwargs: dict[str, Any] = {
        "base_url": config.embedding_base_url,
        "embedding_model": config.embedding_model,
        # Same placeholder rationale as ``_build_llm_client``.
        "api_key": "local-key",
    }
    # Pass ``embedding_dim`` through only when the YAML populated it.
    # graphiti-core's ``OpenAIEmbedderConfig`` accepts the field as
    # optional; synthesising a default here would trade a loud
    # config-error for a silent vector-shape-mismatch in FalkorDB.
    if config.embedding_dimensions is not None:
        embedder_config_kwargs["embedding_dim"] = config.embedding_dimensions

    embedder_config = openai_embedder_config_cls(**embedder_config_kwargs)
    return openai_embedder_cls(config=embedder_config)


def _resolve_cross_encoder_base() -> type:
    """Resolve graphiti-core's ``CrossEncoderClient`` ABC at import time.

    TASK-GR-SEED follow-up: graphiti-core 0.29's ``GraphitiClients``
    pydantic model validates ``cross_encoder`` with
    ``isinstance(value, CrossEncoderClient)``, so the sentinel must
    inherit from that ABC or construction blows up at the boundary.
    Imported lazily inside a helper (rather than at module top) so the
    rest of this module still loads when graphiti-core is absent — the
    same graceful-degradation envelope every other graphiti import in
    this file already lives inside.
    """
    try:
        from graphiti_core.cross_encoder.client import (  # type: ignore[import-not-found]
            CrossEncoderClient,
        )
    except ImportError:
        # When graphiti-core is missing the sentinel is never actually
        # constructed (``get_client`` short-circuits earlier via
        # ``_load_graphiti_core``), so falling back to ``object`` keeps
        # the module importable in offline-tooling scenarios.
        return object
    return CrossEncoderClient


_CROSS_ENCODER_BASE = _resolve_cross_encoder_base()


class _CrossEncoderSentinel(_CROSS_ENCODER_BASE):  # type: ignore[misc,valid-type]
    """Opaque cross-encoder that raises ``RuntimeError`` on any use.

    AC-WIRE-03 / F4 in TASK-REV-GR1A: graphiti-core 0.29's
    ``Graphiti.__init__`` instantiates a default OpenAI-backed
    cross-encoder when ``cross_encoder is None``, which would
    re-introduce the silent £30/week budget leak this feature exists to
    close at the cross-encoder slot. Passing this sentinel bypasses the
    default-construction (graphiti-core sees a non-``None`` object) and
    raises only if a downstream caller actually attempts to invoke a
    reranker method — converting a silent network egress into a loud
    ``RuntimeError`` with the canonical DECISION-DF-001 remediation
    pointer.

    Inherits from :class:`graphiti_core.cross_encoder.client.CrossEncoderClient`
    so pydantic validation in ``GraphitiClients`` (graphiti-core 0.29+)
    accepts the instance — without inheritance the construction call
    fails with ``ValidationError: Input should be an instance of
    CrossEncoderClient`` and ``get_client`` degrades to ``None``,
    falsifying the wired-client contract this sentinel exists to
    enforce. The concrete ``rank`` override and ``__getattr__`` fallback
    both raise the canonical DECISION-DF-001 ``RuntimeError`` so any
    downstream caller — known or unknown method name — gets the same
    loud failure.
    """

    _ERROR_MESSAGE = (
        "cross_encoder not wired; reranker calls disabled per "
        "DECISION-DF-001 — wire a local cross-encoder before enabling "
        "search reranking"
    )

    async def rank(  # type: ignore[override]
        self, query: str, passages: list[str]
    ) -> list[tuple[str, float]]:
        """Concrete override of the ABC's ``rank`` method that always raises.

        graphiti-core's ``CrossEncoderClient`` declares ``rank`` as the
        sole abstract method; instantiating the sentinel without this
        override would fail with ``TypeError: Can't instantiate abstract
        class``. The body raises rather than returning a benign empty
        list because the whole purpose of the sentinel is to surface
        accidental reranker traffic loudly — silent ``[]`` would
        re-introduce the same class of bug the sentinel exists to
        prevent.
        """
        raise RuntimeError(self._ERROR_MESSAGE)

    def __getattr__(self, name: str) -> Any:
        raise RuntimeError(self._ERROR_MESSAGE)

    def __repr__(self) -> str:
        # Defined explicitly so debug logging / error tracebacks don't
        # accidentally trip the ``__getattr__`` raise via repr() lookups
        # on the instance's ``__class__`` / ``__dict__``.
        return "<_CrossEncoderSentinel: reranker disabled per DECISION-DF-001>"


def _build_cross_encoder_sentinel() -> _CrossEncoderSentinel:
    """Return a fresh :class:`_CrossEncoderSentinel`.

    Returned as a plain factory function (rather than a module-level
    singleton) so each :func:`get_client` call gets its own instance —
    keeps the construction story symmetric with
    :func:`_build_llm_client` / :func:`_build_embedder` and avoids any
    surprise where a test that mutated the sentinel's ``__dict__``
    leaked state into a sibling test.
    """
    return _CrossEncoderSentinel()


class GraphitiClient:
    """Thin lifecycle wrapper around a ``graphiti-core`` client.

    Intentionally narrow: this object owns construction, healthcheck, and
    close — nothing else. ``add_episode`` and search helpers are layered on
    top of ``client_or_none`` by sibling modules (TASK-GSM-004 /
    TASK-GSM-005) so the boundary between "the wrapper" and "the domain
    operations" stays auditable.
    """

    def __init__(
        self,
        inner: Any | None,
        config: GraphitiConnectionConfig,
    ) -> None:
        self._inner = inner
        self._config = config

    @property
    def client_or_none(self) -> Any | None:
        """The underlying ``graphiti-core`` client, or ``None`` after close."""
        return self._inner

    async def healthcheck(self) -> bool:
        """Cheap liveness probe against the wrapped driver.

        Honours :attr:`GraphitiConnectionConfig.timeout_seconds` (5s default
        per ASSUM-005) via :func:`asyncio.wait_for`. Never raises — any
        timeout, driver exception, or missing-driver state resolves to
        ``False`` plus a structured ``graphiti_client_degraded`` warning.
        """
        if self._inner is None:
            return False

        started = time.monotonic()
        try:
            await asyncio.wait_for(
                self._ping(),
                timeout=self._config.timeout_seconds,
            )
            return True
        except asyncio.TimeoutError:
            elapsed_ms = int((time.monotonic() - started) * 1000)
            _log_degraded(
                "TimeoutError",
                self._config.falkor_host,
                latency_ms=elapsed_ms,
                error_message=(f"healthcheck exceeded {self._config.timeout_seconds}s"),
            )
            return False
        except Exception as exc:  # noqa: BLE001 — boundary to external lib
            elapsed_ms = int((time.monotonic() - started) * 1000)
            _log_degraded(
                exc.__class__.__name__,
                self._config.falkor_host,
                latency_ms=elapsed_ms,
                error_message=str(exc),
            )
            return False

    async def _ping(self) -> None:
        """Run ``RETURN 1`` via the wrapped driver.

        graphiti-core exposes its underlying driver on the ``driver``
        attribute. Different driver implementations name the query method
        differently (``execute_query`` on the falkordb driver, ``query`` on
        some others) — we probe both rather than hard-coding so that a
        graphiti-core minor-version bump that renames the method doesn't
        silently turn every healthcheck into a hard failure.
        """
        driver = getattr(self._inner, "driver", None)
        if driver is None:
            raise RuntimeError(
                "graphiti client missing 'driver' attribute; cannot healthcheck"
            )

        for attr in ("execute_query", "query"):
            fn = getattr(driver, attr, None)
            if fn is None:
                continue
            result = fn("RETURN 1")
            if asyncio.iscoroutine(result):
                await result
            return

        raise RuntimeError(
            "graphiti driver exposes neither 'execute_query' nor 'query'"
        )

    async def close(self) -> None:
        """Idempotent close. Safe to call when the wrapper is already empty.

        After the first call ``client_or_none`` returns ``None`` and any
        further ``close()`` is a no-op — that property is what lets
        :func:`get_client`'s degradation path call ``close()`` on a
        partially-constructed wrapper without juggling try/finally.
        """
        if self._inner is None:
            return

        inner = self._inner
        # Zero state before awaiting so re-entrant or concurrent callers
        # can't race two close() awaits onto the same underlying driver.
        self._inner = None

        close_fn = getattr(inner, "close", None)
        if close_fn is None:
            return

        try:
            result = close_fn()
            if asyncio.iscoroutine(result):
                await result
        except Exception as exc:  # noqa: BLE001 — boundary to external lib
            logger.warning(
                "graphiti close raised: %s",
                exc.__class__.__name__,
                extra={
                    "event": EVENT_CLOSE_ERROR,
                    "error_class": exc.__class__.__name__,
                    "falkor_host": self._config.falkor_host,
                    "error_message": str(exc),
                },
            )


async def get_client(
    config: GraphitiConnectionConfig,
) -> GraphitiClient | None:
    """Construct a :class:`GraphitiClient` or return ``None`` on any failure.

    Degradation gates (each logs ``graphiti_client_degraded`` and returns
    ``None`` — no exception escapes):

    1. ``graphiti-core`` import fails (library not installed / broken).
    2. FalkorDB driver / Graphiti construction raises (host unreachable,
       auth rejected, invalid database name, etc.).
    3. :meth:`GraphitiClient.healthcheck` returns ``False`` (driver
       constructed but not actually serving queries within
       ``timeout_seconds``).

    On success the wrapper is returned and an ``graphiti_client_ready``
    info-level log records latency.
    """
    started = time.monotonic()

    try:
        graphiti_cls, driver_cls = _load_graphiti_core()
    except ImportError as exc:
        _log_degraded(
            "ImportError",
            config.falkor_host,
            error_message=str(exc),
        )
        return None
    except Exception as exc:  # noqa: BLE001 — graphiti-core import side effects
        _log_degraded(
            exc.__class__.__name__,
            config.falkor_host,
            error_message=str(exc),
        )
        return None

    # TASK-GR-WIRE: build the LLM client / embedder / cross-encoder sentinel
    # *inside* the existing graceful-degradation envelope. Per AC-WIRE-07 a
    # missing graphiti-core sub-module (e.g. an upstream rename of
    # ``openai_generic_client``) must funnel through ``_log_degraded`` — the
    # same gate that already handles the bare ``import graphiti_core``
    # failure — so the rest of the tutor still boots in offline mode.
    # Don't widen the boundary by adding a second try/except branch with a
    # different error code; this is the same envelope.
    try:
        llm_client = _build_llm_client(config)
        embedder = _build_embedder(config)
        cross_encoder = _build_cross_encoder_sentinel()
    except ImportError as exc:
        _log_degraded(
            "ImportError",
            config.falkor_host,
            error_message=str(exc),
        )
        return None
    except NotImplementedError as exc:
        # Defensive belt-and-braces gate (AC-WIRE-01/02): the YAML loader
        # already rejected cloud providers, so this branch fires only when
        # a caller hand-constructs a config with a bogus provider value.
        # Treated as a degradation — the tutor boots without a knowledge
        # graph rather than crashing the whole process.
        _log_degraded(
            "NotImplementedError",
            config.falkor_host,
            error_message=str(exc),
        )
        return None
    except Exception as exc:  # noqa: BLE001 — boundary to external lib
        _log_degraded(
            exc.__class__.__name__,
            config.falkor_host,
            error_message=str(exc),
        )
        return None

    try:
        driver = driver_cls(
            host=config.falkor_host,
            port=config.falkor_port,
            database=config.database,
        )
        inner = graphiti_cls(
            graph_driver=driver,
            llm_client=llm_client,
            embedder=embedder,
            cross_encoder=cross_encoder,
        )
    except Exception as exc:  # noqa: BLE001 — boundary to external lib
        _log_degraded(
            exc.__class__.__name__,
            config.falkor_host,
            error_message=str(exc),
        )
        return None

    wrapper = GraphitiClient(inner=inner, config=config)

    healthy = await wrapper.healthcheck()
    elapsed_ms = int((time.monotonic() - started) * 1000)

    if not healthy:
        # Healthcheck already logged the underlying cause; emit a second
        # ``HealthcheckFailed`` line so log readers can grep for the
        # gate-level outcome without having to correlate timestamps.
        _log_degraded(
            "HealthcheckFailed",
            config.falkor_host,
            latency_ms=elapsed_ms,
        )
        await wrapper.close()
        return None

    logger.info(
        "graphiti client ready in %dms",
        elapsed_ms,
        extra={
            "event": EVENT_READY,
            "falkor_host": config.falkor_host,
            "degraded": False,
            "latency_ms": elapsed_ms,
        },
    )
    return wrapper


__all__ = [
    "DEFAULT_GRAPHITI_YAML_PATH",
    "EVENT_CLOSE_ERROR",
    "EVENT_CLOUD_PROVIDER_REJECTED",
    "EVENT_DEGRADED",
    "EVENT_READY",
    "GraphitiClient",
    "GraphitiConnectionConfig",
    "_build_cross_encoder_sentinel",
    "_build_embedder",
    "_build_llm_client",
    "get_client",
    "load_graphiti_config_from_yaml",
]
