---
id: TASK-GR-SMOK
title: "Wave 3 \u2014 Live-graphiti smoke test (constructor-shape always-on + env-gated\
  \ FalkorDB round-trip)"
task_type: testing
parent_review: TASK-REV-GR1A
parent_task: TASK-PH2-GR-001
feature_id: FEAT-FD32
wave: 3
implementation_mode: task-work
complexity: 4
estimated_minutes: 45
dependencies:
- TASK-GR-WIRE
status: in_review
priority: critical
created: 2026-05-02 00:00:00+00:00
updated: 2026-05-02 00:00:00+00:00
tags:
- graphiti
- smoke-test
- integration-test
- regression-prevention
- phase-2
related:
- TASK-PH2-GR-001
consumer_context:
- task: TASK-GR-WIRE
  consumes: WiredGraphitiClient
  framework: pytest + graphiti-core 0.29 (real client, optional FalkorDB transport)
  driver: pytest fixtures with stubbed graphiti_core + env-gated live FalkorDB
  format_note: Real Graphiti instance with non-None llm_client (OpenAIGenericClient),
    non-None embedder (OpenAIEmbedder), and cross_encoder being the DECISION-DF-001
    sentinel (RuntimeError on any attribute access).
autobuild_state:
  current_turn: 2
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-FD32
  base_branch: main
  started_at: '2026-05-02T17:13:56.379063'
  last_updated: '2026-05-02T17:26:43.700419'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Advisory (non-blocking): task-work produced a report with 2 of 3\
      \ expected agent invocations. Missing phases: 3 (Implementation). Consider invoking\
      \ these agents via the Task tool to strengthen stack-specific quality:\n- Phase\
      \ 3: `the stack-specific Phase-3 specialist` (Implementation)\n- Not all acceptance\
      \ criteria met:\n  \u2022 AC-SMOK-01** \u2014 Test file exists at `tests/smoke/test_graphiti_live_smoke.py`.\
      \ Conventional `tests/sm\n  \u2022 AC-SMOK-02** \u2014 `test_constructor_shape_no_cloud_defaults`\
      \ runs unconditionally (no env-var gate). St\n  \u2022 AC-SMOK-03** \u2014 `test_kwarg_drift_detection`\
      \ \u2014 same fake-Graphiti capture pattern, but explicitly ass\n  \u2022 AC-SMOK-04**\
      \ \u2014 `test_live_falkordb_roundtrip` is decorated with `@pytest.mark.skipif(os.environ.get(\n\
      \  \u2022 AC-SMOK-05** \u2014 `test_openai_api_key_never_read` \u2014 sets `OPENAI_API_KEY=poison-must-not-leak`,\
      \ calls \n  (2 more)"
    timestamp: '2026-05-02T17:13:56.379063'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-05-02T17:19:24.876695'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Wave 3 — Live-graphiti smoke test

## Why this exists

Closes the regression hole that let Phase 1 ship with a 401-on-every-write client. Per F5 + F7 in the review report, this is a two-layer test:

1. **Constructor-shape assertion (always-on, runs in CI)** — boots a real `Graphiti` instance with the wired clients but stubs the FalkorDB driver. Asserts `Graphiti.__init__` was called with non-None `llm_client`, non-None `embedder`, and a `cross_encoder` that raises on access. This catches the next graphiti-core kwarg drift (the parent's `@regression` BDD scenario explicitly targets this).
2. **Live FalkorDB round-trip (env-gated)** — only runs when `STUDY_TUTOR_LIVE_GRAPHITI_SMOKE=1` is set (Tailscale-only). Round-trips one `add_episode(group_id="student-test", ...)` → `EntityNode.get_by_group_ids(...)` → asserts the episode is reachable.

Consumer of [Contract 2](../../../tasks/backlog/graphiti-runtime-integration-repair/IMPLEMENTATION-GUIDE.md#contract-2-wired-graphiti-client).

## Acceptance Criteria

- [ ] **AC-SMOK-01** — Test file exists at `tests/smoke/test_graphiti_live_smoke.py`. Conventional `tests/smoke/` location aligns with the existing project layout (see `tests/` siblings).
- [ ] **AC-SMOK-02** — `test_constructor_shape_no_cloud_defaults` runs unconditionally (no env-var gate). Stubs `_load_graphiti_core` to return a fake `Graphiti` class that captures init kwargs. Asserts:
    1. `kwargs["llm_client"]` is an `OpenAIGenericClient` instance
    2. `kwargs["llm_client"].config.api_key == "local-key"` (and crucially NOT the value of `OPENAI_API_KEY`, even when set to a poisoned value)
    3. `kwargs["embedder"]` is an `OpenAIEmbedder` instance
    4. `kwargs["embedder"].config.api_key == "local-key"`
    5. `kwargs["cross_encoder"]` is the sentinel — `with pytest.raises(RuntimeError, match="DECISION-DF-001"): kwargs["cross_encoder"].predict(...)`.
- [ ] **AC-SMOK-03** — `test_kwarg_drift_detection` — same fake-Graphiti capture pattern, but explicitly asserts the four kwarg *names* are present: `graph_driver`, `llm_client`, `embedder`, `cross_encoder`. If graphiti-core 0.30 renames any of these, this test fails immediately with a clear message naming the missing kwarg. (Closes the parent's `@regression` BDD scenario.)
- [ ] **AC-SMOK-04** — `test_live_falkordb_roundtrip` is decorated with `@pytest.mark.skipif(os.environ.get("STUDY_TUTOR_LIVE_GRAPHITI_SMOKE") != "1", reason="live FalkorDB requires Tailscale; set STUDY_TUTOR_LIVE_GRAPHITI_SMOKE=1 to enable")`. When enabled, the test:
    1. Loads `.guardkit/graphiti.yaml` via `load_graphiti_config_from_yaml()`.
    2. Calls `await get_client(config)` to get the real wrapper.
    3. Calls `await client._inner.add_episode(name="smoke", episode_body="{...}", source=EpisodeType.json, source_description="smoke-test", reference_time=now(), group_id="student-test")`.
    4. Calls `await EntityNode.get_by_group_ids(driver, group_ids=["student-test"])` and asserts the result is non-empty.
    5. Cleans up: deletes the test group via the helper drain pattern from `async_write.py`.
- [ ] **AC-SMOK-05** — `test_openai_api_key_never_read` — sets `OPENAI_API_KEY=poison-must-not-leak`, calls `_build_llm_client(config)` and `_build_embedder(config)`, asserts `client.config.api_key != "poison-must-not-leak"`. (Direct AC-LOAD-03 / AC-WIRE-05 enforcement at the test layer.)
- [ ] **AC-SMOK-06** — CC-13 regex audit (the existing single-`add_episode(`-call-site invariant) re-run via the project's lint/audit harness — passes with zero new findings.
- [ ] **AC-SMOK-07** — CI configuration (whether GitHub Actions, Conductor, or local pre-commit) does NOT set `STUDY_TUTOR_LIVE_GRAPHITI_SMOKE=1`. The constructor-shape test runs in every CI invocation; the live test stays env-gated. Document this contract in the smoke test file's module docstring.

## Test Requirements

This task IS the testing wave; the "tests" here are the test files themselves. Self-validation criteria:

- The constructor-shape test fails on the current `main` (before TASK-GR-WIRE ships).
- The constructor-shape test passes after TASK-GR-WIRE ships.
- Both test paths run in <5 seconds each on local hardware (no slow imports).

## Implementation Notes

### Stubbing pattern — match the existing `_FakeInner` style

The existing `tests/unit/knowledge/test_queries.py:_FakeInner` and `tests/unit/knowledge/test_async_write.py:FakeClient` show the project's preferred stubbing pattern. Reuse the shape — don't introduce a new mocking framework. Patch via `monkeypatch.setattr("study_tutor.knowledge.graphiti_client._load_graphiti_core", lambda: (FakeGraphiti, FakeDriver))`.

### Why `tests/smoke/` and not `tests/integration/`

`tests/smoke/` signals "must run before merge but tolerates env-gating". `tests/integration/` is for unconditional integration with stubbed externals. The constructor-shape test is technically a unit test, but co-locating it with the live test makes the intent (regression-prevention against graphiti-core drift) clear at the path level.

### Don't seed real Lilymay data

The live test uses `group_id="student-test"` and cleans up after itself. Lilymay seeding is Wave 4's job; this test must be runnable repeatedly without polluting Lilymay's graph.

### Constructor-shape test — the regression-prevention argument

Per F7: graphiti-core 0.28 → 0.29 already drifted constructor surfaces (one of the three in-flight fixes — `async_write.py:_add_episode_kwargs` — was a casualty). The constructor-shape test is what catches the next drift. Without it, the next minor-version bump would silently re-default to OpenAI exactly as Phase 1 did. The cost-benefit is overwhelmingly favourable: ~30 lines of test code prevents a £30+ Gemini/OpenAI accidental spend.

## Cross-references

- [IMPLEMENTATION-GUIDE.md §4 Contract 2](./IMPLEMENTATION-GUIDE.md#contract-2-wired-graphiti-client)
- F5 + F7 in `.claude/reviews/TASK-REV-GR1A-review-report.md`
- `tests/unit/knowledge/test_async_write.py:FakeClient` — stubbing pattern reference
- `features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair.feature` — the `@regression` scenario this test closes

## Seam Tests

This task IS the seam test for Contract 2. The unit-of-work pattern below is what `test_constructor_shape_no_cloud_defaults` codifies (see AC-SMOK-02 for the full assertion list).

```python
"""Seam test: verify Wired Graphiti client contract — captured kwargs shape."""
import os
from typing import Any
from unittest.mock import MagicMock

import pytest

from study_tutor.knowledge.graphiti_client import (
    GraphitiConnectionConfig,
    get_client,
)


@pytest.mark.seam
@pytest.mark.integration_contract("WiredGraphitiClient")
@pytest.mark.asyncio
async def test_wired_client_constructor_kwargs_shape(monkeypatch):
    """Verify Graphiti.__init__ receives non-None llm_client + embedder + sentinel.

    Contract: graphiti-core 0.29 must be initialised with all four kwargs
              wired — graph_driver, llm_client, embedder, cross_encoder.
    Producer: TASK-GR-WIRE
    """
    monkeypatch.setenv("OPENAI_API_KEY", "poison-must-not-leak")

    captured: dict[str, Any] = {}

    class FakeGraphiti:
        def __init__(self, **kwargs):
            captured.update(kwargs)
            self.driver = MagicMock()

    class FakeDriver:
        def __init__(self, **kwargs):
            pass

    monkeypatch.setattr(
        "study_tutor.knowledge.graphiti_client._load_graphiti_core",
        lambda: (FakeGraphiti, FakeDriver),
    )

    config = GraphitiConnectionConfig(
        falkor_host="test", falkor_port=6379, database="test",
        llm_provider="vllm", llm_base_url="http://local:9000/v1",
        llm_model="qwen-graphiti", llm_max_tokens=4096,
        embedding_provider="vllm",
        embedding_base_url="http://local:9000/v1",
        embedding_model="nomic-embed",
        embedder_url="http://local:9000/v1",
    )

    await get_client(config)

    assert captured.get("llm_client") is not None
    assert captured["llm_client"].config.api_key == "local-key"
    assert captured["llm_client"].config.api_key != os.environ["OPENAI_API_KEY"]
    assert captured.get("embedder") is not None
    assert captured["embedder"].config.api_key == "local-key"
    assert captured.get("cross_encoder") is not None
    with pytest.raises(RuntimeError, match="DECISION-DF-001"):
        captured["cross_encoder"].predict(["q"], ["d"])
```
