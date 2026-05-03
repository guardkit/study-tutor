---
id: TASK-GR-LOAD
title: "Wave 1 \u2014 YAML loader for .guardkit/graphiti.yaml + DECISION-DF-001 cloud-provider\
  \ guard"
task_type: feature
parent_review: TASK-REV-GR1A
parent_task: TASK-PH2-GR-001
feature_id: FEAT-FD32
wave: 1
implementation_mode: task-work
complexity: 4
estimated_minutes: 30
dependencies: []
status: blocked
priority: critical
created: 2026-05-02 00:00:00+00:00
updated: 2026-05-02 00:00:00+00:00
tags:
- graphiti
- config
- yaml-loader
- decision-df-001
- dark-factory
- phase-2
related:
- TASK-PH2-GR-001
- TASK-PH2-GR-002
autobuild_state:
  current_turn: 4
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-FD32
  base_branch: main
  started_at: '2026-05-02T11:47:19.891835'
  last_updated: '2026-05-02T12:32:03.189743'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Advisory (non-blocking): task-work produced a report with 2 of 3\
      \ expected agent invocations. Missing phases: 3 (Implementation). Consider invoking\
      \ these agents via the Task tool to strengthen stack-specific quality:\n- Phase\
      \ 3: `the stack-specific Phase-3 specialist` (Implementation)\n- Tests failed\
      \ due to infrastructure/environment issues (not code defects). Test command:\
      \ pytest tests/unit/knowledge/test_graphiti_client.py tests/unit/knowledge/test_graphiti_config_loader.py\
      \ -v --tb=short. Remediation options: (1) Add mock fixtures for external services,\
      \ (2) Use SQLite for test database, (3) Mark integration tests with @pytest.mark.integration\
      \ and exclude via -m 'not integration'. Error detail: Error detail:\n    assert\
      \ result.returncode == 0, (\nE   AssertionError: subprocess failed: stdout=''\
      \ stderr='Traceback (most recent call last):\\n  File \"<string>\", line 4,\
      \ in <module>\\n    import study_tutor.knowledge.graphiti_client as mod\\nModuleNotFoundError:\
      \ No module named \\'study_tutor\\'\\n'\nE   assert 1 == 0\nE    +  where 1\
      \ = CompletedProcess(args=['/usr/local/bin/python3', '-c', \"\\nimport sys\\\
      nsys.modules['graphiti_core'] = None  # simulate absent dependency\\nimport\
      \ study_tutor.knowledg...:\n  Error detail:\n    assert result.returncode ==\
      \ 0, (\nE   AssertionError: subprocess failed: stdout='' stderr='Traceback (most\
      \ recent call last):\\n  File \"<string>\", line 4, in <module>\\n    import\
      \ study_tutor.knowledge.graphiti_client as mod\\nModuleNotFoundError: No module\
      \ named \\'study_tutor\\'\\n'\nE   assert 1 == 0\nE    +  where 1 = CompletedProcess(args=['/usr/local/bin/python3',\
      \ '-c', \"\\nimport sys\\nsys.modules['graphiti_core'] = None  # simulate absent\
      \ dependency\\nimport study_tutor.knowledge.graphiti_client as mod\\ncfg = mod.GraphitiConnectionConfig(\\\
      n    falkor_host='h', falkor_port=1, database='d',\\n    embedder_url='http://x',\\\
      n)\\nprint('OK', cfg.timeout_seconds)\\n\"], returncode=1, stdout='', stderr='Traceback\
      \ (most recent call last):\\n  File \"<string>\", line 4, in <module>\\n   \
      \ import study_tutor.knowledge.graphiti_client as mod\\nModuleNotFoundError:\
      \ No module named \\'study_tutor\\'\\n').returncode\n===========================\
      \ short test summary info ============================\n..."
    timestamp: '2026-05-02T11:47:19.891835'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: "- Advisory (non-blocking): task-work produced a report with 2 of 3\
      \ expected agent invocations. Missing phases: 3 (Implementation). Consider invoking\
      \ these agents via the Task tool to strengthen stack-specific quality:\n- Phase\
      \ 3: `the stack-specific Phase-3 specialist` (Implementation)\n- Not all acceptance\
      \ criteria met:\n  \u2022 AC-LOAD-01** \u2014 `load_graphiti_config_from_yaml(path:\
      \ Path = Path(\".guardkit/graphiti.yaml\")) -> Grap\n  \u2022 AC-LOAD-02** \u2014\
      \ Env-var overrides honoured for the documented set: `FALKORDB_HOST`, `FALKORDB_PORT`,\
      \ \n  \u2022 AC-LOAD-03** \u2014 DECISION-DF-001 guard at load time: `llm_provider\
      \ in (\"openai\", \"gemini\")` raises `Va\n  \u2022 AC-LOAD-04** \u2014 Dataclass\
      \ extension: `GraphitiConnectionConfig` gains fields `llm_provider`, `llm_bas\n\
      \  \u2022 AC-LOAD-05** \u2014 The legacy default `llm_provider: str = \"gemini\"\
      ` is changed to `\"vllm\"`. Default `ll\n  (3 more)"
    timestamp: '2026-05-02T12:04:45.814572'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: "- Advisory (non-blocking): task-work produced a report with 2 of 3\
      \ expected agent invocations. Missing phases: 3 (Implementation). Consider invoking\
      \ these agents via the Task tool to strengthen stack-specific quality:\n- Phase\
      \ 3: `the stack-specific Phase-3 specialist` (Implementation)\n- Not all acceptance\
      \ criteria met:\n  \u2022 AC-LOAD-01** \u2014 `load_graphiti_config_from_yaml(path:\
      \ Path = Path(\".guardkit/graphiti.yaml\")) -> Grap\n  \u2022 AC-LOAD-02** \u2014\
      \ Env-var overrides honoured for the documented set: `FALKORDB_HOST`, `FALKORDB_PORT`,\
      \ \n  \u2022 AC-LOAD-03** \u2014 DECISION-DF-001 guard at load time: `llm_provider\
      \ in (\"openai\", \"gemini\")` raises `Va\n  \u2022 AC-LOAD-04** \u2014 Dataclass\
      \ extension: `GraphitiConnectionConfig` gains fields `llm_provider`, `llm_bas\n\
      \  \u2022 AC-LOAD-05** \u2014 The legacy default `llm_provider: str = \"gemini\"\
      ` is changed to `\"vllm\"`. Default `ll\n  (3 more)"
    timestamp: '2026-05-02T12:15:27.853375'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 4
    decision: feedback
    feedback: "- Advisory (non-blocking): task-work produced a report with 2 of 3\
      \ expected agent invocations. Missing phases: 3 (Implementation). Consider invoking\
      \ these agents via the Task tool to strengthen stack-specific quality:\n- Phase\
      \ 3: `the stack-specific Phase-3 specialist` (Implementation)\n- Not all acceptance\
      \ criteria met:\n  \u2022 AC-LOAD-01** \u2014 `load_graphiti_config_from_yaml(path:\
      \ Path = Path(\".guardkit/graphiti.yaml\")) -> Grap\n  \u2022 AC-LOAD-02** \u2014\
      \ Env-var overrides honoured for the documented set: `FALKORDB_HOST`, `FALKORDB_PORT`,\
      \ \n  \u2022 AC-LOAD-03** \u2014 DECISION-DF-001 guard at load time: `llm_provider\
      \ in (\"openai\", \"gemini\")` raises `Va\n  \u2022 AC-LOAD-04** \u2014 Dataclass\
      \ extension: `GraphitiConnectionConfig` gains fields `llm_provider`, `llm_bas\n\
      \  \u2022 AC-LOAD-05** \u2014 The legacy default `llm_provider: str = \"gemini\"\
      ` is changed to `\"vllm\"`. Default `ll\n  (3 more)"
    timestamp: '2026-05-02T12:23:30.867059'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Wave 1 — YAML loader + DECISION-DF-001 guard

## Why this exists

Bridges the schema gap between [`.guardkit/graphiti.yaml`](../../../.guardkit/graphiti.yaml) (GuardKit-canonical schema, the source of truth) and [`GraphitiConnectionConfig`](../../../src/study_tutor/knowledge/graphiti_client.py#L56-L84) (Phase-1 runtime model). Adds a structured-log-line `ValueError` at config-load time if any caller tries to configure a cloud LLM/embedding provider, per DECISION-DF-001.

Producer for [Contract 1](../../../tasks/backlog/graphiti-runtime-integration-repair/IMPLEMENTATION-GUIDE.md#contract-1-graphiticonnectionconfig).

## Acceptance Criteria

- [ ] **AC-LOAD-01** — `load_graphiti_config_from_yaml(path: Path = Path(".guardkit/graphiti.yaml")) -> GraphitiConnectionConfig` exists in `src/study_tutor/knowledge/graphiti_client.py`. Reads the YAML and projects the canonical fields into the runtime model: `falkordb_host`, `falkordb_port`, `timeout`, `llm_provider`, `llm_base_url`, `llm_model`, `llm_max_tokens`, `embedding_provider`, `embedding_base_url`, `embedding_model`, `embedding_dimensions` (when present), `chunk_extraction_concurrency`.
- [ ] **AC-LOAD-02** — Env-var overrides honoured for the documented set: `FALKORDB_HOST`, `FALKORDB_PORT`, `GRAPHITI_ENABLED` (and analogous LLM/embedder vars) per the YAML's documented contract. Tested with `monkeypatch.setenv`.
- [ ] **AC-LOAD-03** — DECISION-DF-001 guard at load time: `llm_provider in ("openai", "gemini")` raises `ValueError("cloud LLM providers disabled per DECISION-DF-001")` with a structured log line `event=cloud_provider_rejected llm_provider=<value>`. Same for `embedding_provider == "openai"`.
- [ ] **AC-LOAD-04** — Dataclass extension: `GraphitiConnectionConfig` gains fields `llm_provider`, `llm_base_url`, `llm_model`, `llm_max_tokens`, `embedding_provider`, `embedding_base_url`, `embedding_model`, `embedding_dimensions`, `chunk_extraction_concurrency`. Existing fields (`falkor_host`, `falkor_port`, `database`, `embedder_url`, `timeout_seconds`) preserved for backwards-compat with the in-flight Phase-1 fixes (`a210472`, `78d3498`, `732672c`).
- [ ] **AC-LOAD-05** — The legacy default `llm_provider: str = "gemini"` is changed to `"vllm"`. Default `llm_model: str = "gemini-2.5-pro"` changed to `"qwen-graphiti"`. (Cleans up F2 from the review report — defaults can no longer leak Gemini even if a caller bypasses the loader.)
- [ ] **AC-LOAD-06** — Unit tests cover: happy path (YAML loads), env-var override, cloud-provider rejection (both LLM and embedder paths), missing-file fallback (raises `FileNotFoundError` with a clear message — do NOT silently default), schema-mismatch (extra YAML keys ignored, missing required keys raises `ValidationError`).
- [ ] **AC-LOAD-07** — `seed_student_model.py` and the `tutor_session_*` MCP handlers are updated to call `load_graphiti_config_from_yaml()` instead of hand-constructing `GraphitiConnectionConfig`. (Sweep `git grep -n 'GraphitiConnectionConfig('` and update each call site.)
- [ ] **AC-LOAD-08** — All modified files pass project-configured lint/format checks with zero errors.

## Test Requirements

Standard quality gates (Q3 = D / per-complexity default; complexity 4 → standard). Minimum:

- Unit test file: `tests/unit/knowledge/test_graphiti_config_loader.py`
- Cases:
  - `test_load_from_yaml_happy_path` — current `.guardkit/graphiti.yaml` parses cleanly.
  - `test_env_override_falkor_host` — `FALKORDB_HOST=test.example.com` overrides YAML value.
  - `test_cloud_llm_provider_rejected` — `llm_provider: openai` raises `ValueError` with the canonical message and structured log captured.
  - `test_cloud_embedding_provider_rejected` — `embedding_provider: openai` raises `ValueError`.
  - `test_gemini_provider_rejected` — `llm_provider: gemini` raises `ValueError` (DECISION-DF-001 explicit).
  - `test_missing_file_raises` — non-existent path raises `FileNotFoundError`, not silent default.
  - `test_unknown_yaml_keys_ignored` — extra keys (e.g. `group_ids`) don't break the loader.
- Coverage target: ≥80% line coverage on the new loader function.

## Implementation Notes

### Mirror the GuardKit-canonical loader pattern

`guardkit/guardkit/knowledge/graphiti_client.py` has the solved version. Read it for the YAML field layout and env-override precedence.

### Why FileNotFoundError, not silent default

The whole reason this task exists is that the Phase-1 client silently defaulted to OpenAI when no client was passed. Symmetric reasoning: if the YAML is missing, raise loudly — don't let a silent default re-introduce the same class of bug.

### Why change the dataclass defaults (AC-LOAD-05)

Per F2 in the review: even with the loader doing the right thing, anyone constructing `GraphitiConnectionConfig()` directly in tests or scripts gets a Gemini-pointing config. Changing the default to `"vllm"` means the default fails at the DECISION-DF-001 guard (no `llm_base_url` set) rather than silently routing to Gemini.

### Updating call sites (AC-LOAD-07)

Currently the only direct `GraphitiConnectionConfig(...)` constructions are:
- `scripts/seed_student_model.py` (TBD — verify with `git grep`)
- The MCP handlers (`tutor_start_session`, `tutor_session_end` in the tutor package)
- Test fixtures (these may keep direct construction with explicit local-only values)

Use `git grep -n 'GraphitiConnectionConfig(' src/ scripts/` to enumerate, then update production call sites only. Test fixtures construct directly because they need local-only values without reading a YAML.

## Cross-references

- [IMPLEMENTATION-GUIDE.md §4 Contract 1](./IMPLEMENTATION-GUIDE.md#contract-1-graphiticonnectionconfig) — the contract this task produces
- `.guardkit/graphiti.yaml` — source of truth
- `guardkit/guardkit/knowledge/graphiti_client.py` — canonical reference loader
- TASK-PH2-GR-001 (parent task) — full context

## Seam Tests

The following seam test validates the integration contract with the consumer task (TASK-GR-WIRE). Implement this test to verify the boundary before Wave 2.

```python
"""Seam test: verify GraphitiConnectionConfig contract from TASK-GR-LOAD."""
from pathlib import Path

import pytest

from study_tutor.knowledge.graphiti_client import (
    GraphitiConnectionConfig,
    load_graphiti_config_from_yaml,
)


@pytest.mark.seam
@pytest.mark.integration_contract("GraphitiConnectionConfig")
def test_graphiti_connection_config_no_cloud_providers():
    """Verify GraphitiConnectionConfig matches the expected format.

    Contract: llm_provider in ("vllm","ollama") and embedding_provider in
              ("vllm","ollama"); cloud providers MUST raise at load time.
    Producer: TASK-GR-LOAD
    """
    config = load_graphiti_config_from_yaml(Path(".guardkit/graphiti.yaml"))

    assert isinstance(config, GraphitiConnectionConfig)
    assert config.llm_provider in ("vllm", "ollama"), (
        f"Expected local LLM provider, got: {config.llm_provider}"
    )
    assert config.embedding_provider in ("vllm", "ollama"), (
        f"Expected local embedding provider, got: {config.embedding_provider}"
    )
    assert config.llm_base_url, "llm_base_url must be populated"
    assert config.embedding_base_url, "embedding_base_url must be populated"
```
