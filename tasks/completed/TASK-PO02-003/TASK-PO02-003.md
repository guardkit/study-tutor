---
id: TASK-PO02-003
title: LLM client with provider resolution (Ollama + Bedrock stub)
status: completed
created: 2026-04-20T00:00:00Z
updated: 2026-04-20T00:00:00Z
completed: 2026-04-20T00:00:00Z
completed_location: tasks/completed/TASK-PO02-003/
previous_state: in_review
state_transition_reason: "All acceptance criteria met; 7/7 tests passing; 100% coverage on client.py"
priority: high
task_type: feature
tags: [phase-0, llm, provider-resolution, sr-03]
complexity: 4
parent_review: TASK-REV-PO02
feature_id: FEAT-PO-002
wave: 2
implementation_mode: task-work
dependencies: [TASK-PO02-001]
estimated_minutes: 75
consumer_context:
  - task: TASK-PO02-001
    consumes: AGENT_MODELS__REASONING_MODEL
    framework: "python-dotenv + os.environ (read at factory instantiation, not at import time)"
    driver: "os.environ"
    format_note: "String ∈ {'local', 'bedrock', 'openai', 'anthropic', 'gemini'}. Phase 0 supports 'local' (Ollama on GB10, default) and 'bedrock' (raises NotImplementedError). Other values reserved for Phase 1+. Factory MUST read at instantiation — any handler-level hard-coding violates SR-03."
test_results:
  status: passed
  coverage: 100
  last_run: 2026-04-20T00:00:00Z
  passed: 7
  failed: 0
  module: study_tutor.llm.client
---

# LLM client with provider resolution (Ollama + Bedrock stub)

## Description

Implement `src/study_tutor/llm/client.py` with a factory that routes requests to the configured provider based on the `AGENT_MODELS__REASONING_MODEL` env var. Phase 0 wires the Ollama path (against GB10 over Tailscale) and stubs Bedrock (`NotImplementedError`, filled in by FEAT-PO-004).

This task is the **SR-03 locus**. All MCP handlers receive `player_model=params.get("player_model") or _default_player_model()`; nothing hard-codes a provider.

## Acceptance Criteria

- [ ] `src/study_tutor/llm/client.py` exposes `LLMClient` class and `_default_player_model()` helper.
- [ ] `_default_player_model()` reads `AGENT_MODELS__REASONING_MODEL` from `os.environ` at call time; falls back to `"local"` if unset. Implementation MUST read env at instantiation (per SR-03) — not at module import.
- [ ] `LLMClient(provider: str).generate(prompt: str, system: str | None = None) -> str` — synchronous, string-in / string-out.
- [ ] `provider="local"` → calls Ollama HTTP endpoint (default `http://gb10.tailnet:11434` — configurable via `OLLAMA_HOST` env var). Model name configurable via `OLLAMA_MODEL` env var (default `gcse-tutor-gemma4-31b:Q4_K_M` or whatever name the existing Ollama deployment exposes — confirm against GB10 state).
- [ ] `provider="bedrock"` → raises `NotImplementedError("Bedrock provider wired by FEAT-PO-004")`. Do NOT import `boto3` or `langchain-aws` in the stub path to keep the import graph minimal.
- [ ] No handler, helper, or test hard-codes `provider="local"` or any other provider value. Every call path reads via `_default_player_model()` or an explicit param.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Seam Tests

The following seam test validates the integration contract with TASK-PO02-001 (`AGENT_MODELS__REASONING_MODEL`). Place in `tests/unit/llm/test_provider_resolution.py` — this is ALSO the SR-03 parity-surface unit test (covered in depth by TASK-PO02-006).

```python
"""Seam test: verify AGENT_MODELS__REASONING_MODEL contract from TASK-PO02-001."""
import os
import pytest
from unittest.mock import patch


@pytest.mark.seam
@pytest.mark.integration_contract("AGENT_MODELS__REASONING_MODEL")
def test_agent_models_reasoning_model_format():
    """Verify AGENT_MODELS__REASONING_MODEL matches the expected format.

    Contract: string ∈ {'local', 'bedrock', 'openai', 'anthropic', 'gemini'};
              Phase 0 supports 'local' (default) and 'bedrock' (NotImplementedError).
    Producer: TASK-PO02-001 (.env.example)
    """
    from study_tutor.llm.client import _default_player_model

    # Factory must read env at call time, not import time (SR-03)
    with patch.dict(os.environ, {"AGENT_MODELS__REASONING_MODEL": "local"}, clear=False):
        assert _default_player_model() == "local"

    with patch.dict(os.environ, {"AGENT_MODELS__REASONING_MODEL": "bedrock"}, clear=False):
        assert _default_player_model() == "bedrock"

    # Fallback when unset
    env_without = {k: v for k, v in os.environ.items() if k != "AGENT_MODELS__REASONING_MODEL"}
    with patch.dict(os.environ, env_without, clear=True):
        assert _default_player_model() == "local"


@pytest.mark.seam
def test_bedrock_provider_raises_not_implemented():
    """Phase 0 Bedrock stub must raise NotImplementedError, not silently fail."""
    from study_tutor.llm.client import LLMClient

    client = LLMClient(provider="bedrock")
    with pytest.raises(NotImplementedError, match="FEAT-PO-004"):
        client.generate("test prompt")
```

## Implementation Notes

- **Pattern source:** `specialist-agent/src/specialist_agent/llm/client.py`. Copy the factory shape and provider-routing dict. Strip provider implementations we don't need in Phase 0.
- **Do NOT** instantiate the client at module-import time anywhere (SR-03). Instantiation belongs inside handlers or `_default_player_model()`.
- **Ollama HTTP client:** either use `langchain-ollama` or direct `httpx.post(f"{OLLAMA_HOST}/api/generate", json={...})`. The direct-HTTP path is simpler for a sync interface and has no LangChain dependency on this module — recommended unless LangChain is already in the dependency chain for future Coach work.

## Reference Files

- Pattern source: `../specialist-agent/src/specialist_agent/llm/client.py`
- Scope: [docs/research/ideas/phase-0-scope.md §SR-03, §2. Ollama-backed LLM client](../../../docs/research/ideas/phase-0-scope.md)
- Plan: [docs/research/ideas/phase-0-build-plan.md:144, :191-193](../../../docs/research/ideas/phase-0-build-plan.md#L144)
