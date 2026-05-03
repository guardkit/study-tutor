---
id: TASK-GR-WIRE
title: "Wave 2 \u2014 Build LLM client + embedder via OpenAIGenericClient/OpenAIEmbedder;\
  \ install cross-encoder sentinel"
task_type: feature
parent_review: TASK-REV-GR1A
parent_task: TASK-PH2-GR-001
feature_id: FEAT-FD32
wave: 2
implementation_mode: task-work
complexity: 5
estimated_minutes: 60
dependencies:
- TASK-GR-LOAD
status: in_review
priority: critical
created: 2026-05-02 00:00:00+00:00
updated: 2026-05-02 00:00:00+00:00
tags:
- graphiti
- llm-wiring
- embedder
- llama-swap
- cross-encoder
- decision-df-001
- phase-2
related:
- TASK-PH2-GR-001
consumer_context:
- task: TASK-GR-LOAD
  consumes: GraphitiConnectionConfig
  framework: graphiti-core 0.29 (OpenAI-compatible local inference)
  driver: OpenAIGenericClient + OpenAIEmbedder (graphiti_core.llm_client.openai_generic
    + graphiti_core.embedder.openai)
  format_note: config.llm_provider in ('vllm','ollama') and config.embedding_provider
    in ('vllm','ollama'); cloud providers must already have been rejected at load
    time.
autobuild_state:
  current_turn: 2
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-FD32
  base_branch: main
  started_at: '2026-05-02T13:13:40.777257'
  last_updated: '2026-05-02T13:37:07.684157'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Advisory (non-blocking): task-work produced a report with 2 of 3\
      \ expected agent invocations. Missing phases: 3 (Implementation). Consider invoking\
      \ these agents via the Task tool to strengthen stack-specific quality:\n- Phase\
      \ 3: `the stack-specific Phase-3 specialist` (Implementation)\n- Not all acceptance\
      \ criteria met:\n  \u2022 AC-WIRE-01** \u2014 `_build_llm_client(config: GraphitiConnectionConfig)\
      \ -> OpenAIGenericClient` returns \n  \u2022 AC-WIRE-02** \u2014 `_build_embedder(config:\
      \ GraphitiConnectionConfig) -> OpenAIEmbedder` returns `OpenAI\n  \u2022 AC-WIRE-03**\
      \ \u2014 `_build_cross_encoder_sentinel()` returns an object whose every attribute\
      \ access rais\n  \u2022 AC-WIRE-04** \u2014 `get_client(config)` is updated\
      \ to:\n  \u2022 AC-WIRE-06** \u2014 graphiti-core version pinned in `pyproject.toml`\
      \ to `>=0.29,<0.30` (per parent-task r\n  (3 more)"
    timestamp: '2026-05-02T13:13:40.777257'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-05-02T13:28:06.549118'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Wave 2 — Build LLM client + embedder + cross-encoder sentinel

## Why this exists

The actual bug fix. Mirrors the GuardKit-canonical wiring pattern from [`guardkit/guardkit/knowledge/graphiti_client.py:_build_llm_client`](../../../../guardkit/guardkit/knowledge/graphiti_client.py) / `_build_embedder` so [`get_client()`](../../../src/study_tutor/knowledge/graphiti_client.py#L262-L341) constructs `Graphiti(graph_driver=driver, llm_client=..., embedder=..., cross_encoder=...)` instead of the bare `Graphiti(graph_driver=driver)` that defaults to OpenAI.

Per F4 in the review report, the cross-encoder gets a sentinel object that raises on access — strictly stronger than AC-003's WARN log because it converts a silent £30/week budget leak into a loud `RuntimeError`.

Producer for [Contract 2](../../../tasks/backlog/graphiti-runtime-integration-repair/IMPLEMENTATION-GUIDE.md#contract-2-wired-graphiti-client). Consumer of [Contract 1](../../../tasks/backlog/graphiti-runtime-integration-repair/IMPLEMENTATION-GUIDE.md#contract-1-graphiticonnectionconfig).

## Acceptance Criteria

- [ ] **AC-WIRE-01** — `_build_llm_client(config: GraphitiConnectionConfig) -> OpenAIGenericClient` returns `OpenAIGenericClient(config=LLMConfig(base_url=config.llm_base_url, model=config.llm_model, api_key="local-key"), max_tokens=config.llm_max_tokens)` for `config.llm_provider in ("vllm","ollama")`. Raises `NotImplementedError` for any other provider value (loader already rejected `openai`/`gemini`, so this is a defensive belt-and-braces gate).
- [ ] **AC-WIRE-02** — `_build_embedder(config: GraphitiConnectionConfig) -> OpenAIEmbedder` returns `OpenAIEmbedder(config=OpenAIEmbedderConfig(base_url=config.embedding_base_url, embedding_model=config.embedding_model, api_key="local-key", embedding_dim=config.embedding_dimensions if set else not_passed))`. Same defensive gate.
- [ ] **AC-WIRE-03** — `_build_cross_encoder_sentinel()` returns an object whose every attribute access raises `RuntimeError("cross_encoder not wired; reranker calls disabled per DECISION-DF-001 — wire a local cross-encoder before enabling search reranking")`. Implement via `__getattr__` so the sentinel is opaque to graphiti-core's internals until something tries to call it.
- [ ] **AC-WIRE-04** — `get_client(config)` is updated to:
    1. Build `llm_client = _build_llm_client(config)`
    2. Build `embedder = _build_embedder(config)`
    3. Build `cross_encoder = _build_cross_encoder_sentinel()`
    4. Pass all three into `graphiti_cls(graph_driver=driver, llm_client=llm_client, embedder=embedder, cross_encoder=cross_encoder)`.
- [ ] **AC-WIRE-05** — `OPENAI_API_KEY` environment variable is **never** read by any code path under `src/study_tutor/knowledge/`. Verified by adding a regression test that sets `OPENAI_API_KEY=poison-this-must-not-be-used` and asserts `get_client()` succeeds against a stubbed driver — if any code path under test tries to use the env var as a real key, the stubbed transport would observe a request with that header and the test would fail.
- [ ] **AC-WIRE-06** — graphiti-core version pinned in `pyproject.toml` to `>=0.29,<0.30` (per parent-task risk register). Document the rationale inline: the `OpenAIGenericClient` constructor surface drifted between 0.28 and 0.29, and Wave 3's smoke test catches the next drift.
- [ ] **AC-WIRE-07** — `ImportError` for `graphiti_core.llm_client.openai_generic.OpenAIGenericClient` or `graphiti_core.embedder.openai.OpenAIEmbedder` falls into the existing `_log_degraded("ImportError", ...)` path in `get_client()` — does NOT raise. The existing graceful-degradation contract (return `None`) is preserved for the case where graphiti-core is uninstalled in the venv.
- [ ] **AC-WIRE-08** — Unit tests cover: client construction with vllm provider, client construction with ollama provider, embedder with explicit `embedding_dim`, embedder without explicit dim, cross-encoder sentinel raises on first attribute access (not at construction), full `get_client()` with stubbed `_load_graphiti_core` returning a fake `Graphiti` class that captures kwargs.
- [ ] **AC-WIRE-09** — All modified files pass project-configured lint/format checks with zero errors.

## Test Requirements

Standard quality gates (per-complexity default for complexity 5 → standard).

- Test file: `tests/unit/knowledge/test_graphiti_client_wiring.py`
- Critical assertions:
  - `Graphiti.__init__` called with `llm_client is not None`
  - `Graphiti.__init__` called with `embedder is not None`
  - `Graphiti.__init__` called with `cross_encoder` being the sentinel
  - `OpenAIGenericClient.config.api_key == "local-key"` (placeholder, not env var)
  - Cross-encoder sentinel: `with pytest.raises(RuntimeError, match="DECISION-DF-001"): sentinel.predict(...)`
- Coverage target: ≥80% line coverage on the new builder functions.

## Implementation Notes

### Why a sentinel object, not just `cross_encoder=None`

graphiti-core 0.29's `Graphiti.__init__` instantiates a default cross-encoder if `cross_encoder is None`. Passing `None` reintroduces the original OpenAI-default bug at the cross-encoder slot. The sentinel bypasses graphiti-core's default-construction by *being* an object — graphiti-core never instantiates its default — and raises only if someone actually tries to use it.

```python
class _CrossEncoderSentinel:
    """Opaque object that raises on any access; documents the disabled-reranker contract."""
    def __getattr__(self, name: str) -> object:
        raise RuntimeError(
            "cross_encoder not wired; reranker calls disabled per DECISION-DF-001 — "
            "wire a local cross-encoder before enabling search reranking"
        )
```

### Embedder dimensions handling

The YAML has `embedding_dimensions` only when explicit (nomic-embed-v1.5 = 768). graphiti-core 0.29 accepts the field as optional; pass it through only when the loader populated it. Don't synthesise a dimension default — that's how silent shape-mismatch bugs creep in.

### Existing graceful-degradation path is load-bearing

Per [`graphiti_client.py:282-297`](../../../src/study_tutor/knowledge/graphiti_client.py#L282-L297), the current `get_client()` returns `None` if graphiti-core can't be imported. That's a feature, not a bug — it lets the rest of the tutor boot without a knowledge graph in offline-development scenarios. The new `_build_llm_client` / `_build_embedder` imports must wrap into the existing try/except block, NOT add a new one. Don't widen the boundary.

## Cross-references

- [IMPLEMENTATION-GUIDE.md §4 Contract 1 + Contract 2](./IMPLEMENTATION-GUIDE.md#section-4-integration-contracts)
- `guardkit/guardkit/knowledge/graphiti_client.py:_build_llm_client` — canonical reference
- TASK-GR-LOAD — producer of Contract 1 (this task's input)
- TASK-GR-SMOK — first consumer of Contract 2 (this task's output)
- F4 in `.claude/reviews/TASK-REV-GR1A-review-report.md` — sentinel rationale

## Seam Tests

The following seam test validates the integration contract with consumer tasks (TASK-GR-SMOK, TASK-GR-SEED, TASK-GR-DEMO).

```python
"""Seam test: verify wired Graphiti client contract from TASK-GR-WIRE."""
import pytest

from study_tutor.knowledge.graphiti_client import (
    GraphitiConnectionConfig,
    _build_cross_encoder_sentinel,
    _build_embedder,
    _build_llm_client,
)


@pytest.mark.seam
@pytest.mark.integration_contract("WiredGraphitiClient")
def test_wired_client_uses_local_endpoints_only():
    """Verify wired client points at local endpoints; cloud paths impossible.

    Contract: llm_client.config.base_url and embedder.config.base_url both
              point at local llama-swap (or ollama fallback); cross_encoder
              is the sentinel that raises on attribute access.
    Producer: TASK-GR-WIRE
    """
    config = GraphitiConnectionConfig(
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

    llm = _build_llm_client(config)
    assert llm.config.api_key == "local-key", "Must use placeholder, never OPENAI_API_KEY"
    assert "9000" in llm.config.base_url or "ollama" in llm.config.base_url

    embedder = _build_embedder(config)
    assert embedder.config.api_key == "local-key"

    sentinel = _build_cross_encoder_sentinel()
    with pytest.raises(RuntimeError, match="DECISION-DF-001"):
        sentinel.predict(["query"], ["doc"])
```
