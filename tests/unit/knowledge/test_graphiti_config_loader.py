"""Unit tests for ``load_graphiti_config_from_yaml`` (TASK-GR-LOAD).

Covers AC-LOAD-01 .. AC-LOAD-06: YAML happy-path, env-var precedence,
DECISION-DF-001 cloud-provider rejection (LLM + embedding paths),
loud missing-file failure, and schema-tolerance for unknown YAML keys.

The tests are hermetic — they write tiny YAML fixtures into ``tmp_path``
and invoke the loader directly. The single test that asserts the
real on-disk ``.guardkit/graphiti.yaml`` parses cleanly (AC-LOAD-06
happy-path / seam contract) reads the canonical project-checked-in file
because that file IS the contract this loader honours.
"""
from __future__ import annotations

import logging
from pathlib import Path

import pytest
from pydantic import ValidationError

from study_tutor.knowledge.graphiti_client import (
    DEFAULT_GRAPHITI_YAML_PATH,
    EVENT_CLOUD_PROVIDER_REJECTED,
    GraphitiConnectionConfig,
    load_graphiti_config_from_yaml,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_yaml(path: Path, body: str) -> Path:
    """Write a YAML fixture to ``path`` and return the path."""
    path.write_text(body)
    return path


_BASE_YAML = """\
project_id: study_tutor
enabled: true
graph_store: falkordb
falkordb_host: whitestocks
falkordb_port: 6379
timeout: 30.0
chunk_extraction_concurrency: 4
llm_provider: vllm
llm_base_url: http://promaxgb10-41b1:9000/v1
llm_model: qwen-graphiti
llm_max_tokens: 4096
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:9000/v1
embedding_model: nomic-embed
"""


# ---------------------------------------------------------------------------
# AC-LOAD-01 / AC-LOAD-06 — happy path against the real on-disk YAML
# ---------------------------------------------------------------------------


def test_load_from_yaml_happy_path() -> None:
    """The project-checked-in ``.guardkit/graphiti.yaml`` parses cleanly.

    AC-LOAD-01: loader projects every documented YAML field into the
    runtime model. The on-disk YAML is the source of truth; if this test
    breaks, either the YAML or the loader is out of step with the
    canonical schema.
    """
    cfg = load_graphiti_config_from_yaml(DEFAULT_GRAPHITI_YAML_PATH)

    assert isinstance(cfg, GraphitiConnectionConfig)
    assert cfg.falkor_host == "whitestocks"
    assert cfg.falkor_port == 6379
    # database derives from project_id per the YAML→model rename map.
    assert cfg.database == "study_tutor"
    # llm_provider / embedding_provider must be local-only per
    # DECISION-DF-001 — the on-disk YAML must not configure cloud.
    assert cfg.llm_provider in ("vllm", "ollama")
    assert cfg.embedding_provider in ("vllm", "ollama")
    assert cfg.llm_base_url, "llm_base_url must be populated by the YAML"
    assert cfg.embedding_base_url, "embedding_base_url must be populated"
    # Backwards-compat embedder_url is mirrored from embedding_base_url.
    assert cfg.embedder_url == cfg.embedding_base_url


def test_load_from_yaml_synthetic_happy_path(tmp_path: Path) -> None:
    """Synthetic YAML fixture exercises every renamed + direct field."""
    yaml_path = _write_yaml(tmp_path / "graphiti.yaml", _BASE_YAML)

    cfg = load_graphiti_config_from_yaml(yaml_path)

    assert cfg.falkor_host == "whitestocks"
    assert cfg.falkor_port == 6379
    assert cfg.timeout_seconds == 30.0
    assert cfg.database == "study_tutor"
    assert cfg.llm_provider == "vllm"
    assert cfg.llm_base_url == "http://promaxgb10-41b1:9000/v1"
    assert cfg.llm_model == "qwen-graphiti"
    assert cfg.llm_max_tokens == 4096
    assert cfg.embedding_provider == "vllm"
    assert cfg.embedding_model == "nomic-embed"
    assert cfg.chunk_extraction_concurrency == 4


# ---------------------------------------------------------------------------
# AC-LOAD-02 — env-var precedence
# ---------------------------------------------------------------------------


def test_env_override_falkor_host(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """``FALKORDB_HOST`` env override beats the YAML value."""
    yaml_path = _write_yaml(tmp_path / "graphiti.yaml", _BASE_YAML)
    monkeypatch.setenv("FALKORDB_HOST", "test.example.com")

    cfg = load_graphiti_config_from_yaml(yaml_path)

    assert cfg.falkor_host == "test.example.com"
    # YAML port survives because no FALKORDB_PORT override is set.
    assert cfg.falkor_port == 6379


def test_env_override_falkor_port_coerces_to_int(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Env vars are coerced to the model field's type before validation."""
    yaml_path = _write_yaml(tmp_path / "graphiti.yaml", _BASE_YAML)
    monkeypatch.setenv("FALKORDB_PORT", "12345")

    cfg = load_graphiti_config_from_yaml(yaml_path)

    assert cfg.falkor_port == 12345


# ---------------------------------------------------------------------------
# AC-LOAD-03 — DECISION-DF-001 cloud-provider guard
# ---------------------------------------------------------------------------


def test_cloud_llm_provider_rejected(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """``llm_provider: openai`` raises with the canonical message + log."""
    yaml_body = _BASE_YAML.replace("llm_provider: vllm", "llm_provider: openai")
    yaml_path = _write_yaml(tmp_path / "graphiti.yaml", yaml_body)

    with caplog.at_level(logging.ERROR, logger="study_tutor.knowledge.graphiti_client"):
        with pytest.raises(
            ValueError, match="cloud LLM providers disabled per DECISION-DF-001"
        ):
            load_graphiti_config_from_yaml(yaml_path)

    matched = [
        rec for rec in caplog.records
        if getattr(rec, "event", None) == EVENT_CLOUD_PROVIDER_REJECTED
        and getattr(rec, "llm_provider", None) == "openai"
    ]
    assert matched, (
        "expected a structured cloud_provider_rejected log line; "
        f"records={[r.getMessage() for r in caplog.records]!r}"
    )


def test_gemini_provider_rejected(tmp_path: Path) -> None:
    """``llm_provider: gemini`` raises (DECISION-DF-001 explicit case)."""
    yaml_body = _BASE_YAML.replace("llm_provider: vllm", "llm_provider: gemini")
    yaml_path = _write_yaml(tmp_path / "graphiti.yaml", yaml_body)

    with pytest.raises(
        ValueError, match="cloud LLM providers disabled per DECISION-DF-001"
    ):
        load_graphiti_config_from_yaml(yaml_path)


def test_cloud_embedding_provider_rejected(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    """``embedding_provider: openai`` raises with structured log."""
    yaml_body = _BASE_YAML.replace(
        "embedding_provider: vllm", "embedding_provider: openai"
    )
    yaml_path = _write_yaml(tmp_path / "graphiti.yaml", yaml_body)

    with caplog.at_level(logging.ERROR, logger="study_tutor.knowledge.graphiti_client"):
        with pytest.raises(
            ValueError, match="cloud LLM providers disabled per DECISION-DF-001"
        ):
            load_graphiti_config_from_yaml(yaml_path)

    matched = [
        rec for rec in caplog.records
        if getattr(rec, "event", None) == EVENT_CLOUD_PROVIDER_REJECTED
        and getattr(rec, "embedding_provider", None) == "openai"
    ]
    assert matched, "expected structured cloud_provider_rejected log for embedding"


def test_env_var_cloud_provider_also_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Env-var-supplied cloud provider is rejected (env beats YAML)."""
    yaml_path = _write_yaml(tmp_path / "graphiti.yaml", _BASE_YAML)
    monkeypatch.setenv("LLM_PROVIDER", "openai")

    with pytest.raises(
        ValueError, match="cloud LLM providers disabled per DECISION-DF-001"
    ):
        load_graphiti_config_from_yaml(yaml_path)


# ---------------------------------------------------------------------------
# AC-LOAD-06 — missing file fails loudly + schema tolerance
# ---------------------------------------------------------------------------


def test_missing_file_raises(tmp_path: Path) -> None:
    """Missing YAML must raise ``FileNotFoundError`` — not silently default.

    The whole reason this loader exists is the Phase-1 silent OpenAI
    fallback. Symmetric reasoning: a missing config must fail loudly so
    the silent-default class of bug cannot be re-introduced.
    """
    nonexistent = tmp_path / "absent.yaml"

    with pytest.raises(FileNotFoundError, match="graphiti config not found"):
        load_graphiti_config_from_yaml(nonexistent)


def test_unknown_yaml_keys_ignored(tmp_path: Path) -> None:
    """Extra YAML keys (e.g. ``group_ids``) don't break the loader."""
    yaml_body = _BASE_YAML + (
        "max_concurrent_episodes: 3\n"
        "group_ids:\n"
        "- product_knowledge\n"
        "- command_workflows\n"
        "totally_unknown_future_key: value\n"
    )
    yaml_path = _write_yaml(tmp_path / "graphiti.yaml", yaml_body)

    cfg = load_graphiti_config_from_yaml(yaml_path)

    assert cfg.falkor_host == "whitestocks"
    assert cfg.chunk_extraction_concurrency == 4


def test_missing_required_keys_raises_validation_error(tmp_path: Path) -> None:
    """A YAML missing required model fields raises ``ValidationError``."""
    # Omits falkordb_host (→ falkor_host) and embedding_base_url so the
    # legacy ``embedder_url`` cannot be derived either.
    yaml_path = _write_yaml(
        tmp_path / "graphiti.yaml",
        "project_id: study_tutor\nfalkordb_port: 6379\n",
    )

    with pytest.raises(ValidationError):
        load_graphiti_config_from_yaml(yaml_path)


def test_non_mapping_yaml_raises_value_error(tmp_path: Path) -> None:
    """A YAML list (not mapping) raises ``ValueError``, not a cryptic crash."""
    yaml_path = _write_yaml(tmp_path / "graphiti.yaml", "- a\n- b\n")

    with pytest.raises(ValueError, match="must deserialise to a YAML mapping"):
        load_graphiti_config_from_yaml(yaml_path)
