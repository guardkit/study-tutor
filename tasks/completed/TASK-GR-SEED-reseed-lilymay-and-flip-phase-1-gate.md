---
id: TASK-GR-SEED
title: "Wave 4 \u2014 Re-seed Lilymay against live FalkorDB; flip Phase 1 G2/G3/G4/G5/G6/G13\
  \ from Falsified to Held"
task_type: feature
parent_review: TASK-REV-GR1A
parent_task: TASK-PH2-GR-001
feature_id: FEAT-FD32
wave: 4
implementation_mode: task-work
complexity: 4
estimated_minutes: 60
dependencies:
- TASK-GR-SMOK
status: blocked
priority: critical
created: 2026-05-02 00:00:00+00:00
updated: 2026-05-02 00:00:00+00:00
tags:
- graphiti
- seed
- falkordb
- phase-1-gate-flip
- phase-2
related:
- TASK-PH2-GR-001
- TASK-GSM-006
consumer_context:
- task: TASK-GR-WIRE
  consumes: WiredGraphitiClient
  framework: scripts/seed_student_model.py + graphiti-core 0.29
  driver: FalkorDB on Synology (whitestocks:6379) via wired Graphiti instance
  format_note: Seed script consumes a wired Graphiti client (non-None llm_client +
    embedder, sentinel cross_encoder); uses helper.drain() for serial writes; group_id
    format 'student-lilymay' (post-a210472 normalisation).
autobuild_state:
  current_turn: 2
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-FD32
  base_branch: main
  started_at: '2026-05-03T07:17:55.973271'
  last_updated: '2026-05-03T08:27:38.895129'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Advisory (non-blocking): task-work produced a report with 2 of 3
      expected agent invocations. Missing phases: 3 (Implementation). Consider invoking
      these agents via the Task tool to strengthen stack-specific quality:

      - Phase 3: `the stack-specific Phase-3 specialist` (Implementation)

      - Tests did not pass during task-work execution'
    timestamp: '2026-05-03T07:17:55.973271'
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
      \ criteria met:\n  \u2022 AC-SEED-02** \u2014 `mcp__graphiti__search_nodes(query=\"\
      Lilymay\", group_ids=[\"student-lilymay\"])` returns\n  \u2022 AC-SEED-03**\
      \ \u2014 `get_student_state(client, \"lilymay\")` (the existing helper from\
      \ `student_model.py`) \n  \u2022 AC-SEED-05** \u2014 `docs/research/ideas/phase-1-validation.md`\
      \ is updated:\n  \u2022 AC-SEED-06** \u2014 Stale-index cleanup if needed: if\
      \ `Connection closed by server` warnings escalate int\n  \u2022 AC-SEED-07**\
      \ \u2014 Wall-clock for the seed run captured. Expected ~30 min on MacBook ollama\
      \ (78s/`add_ep\n  (1 more)"
    timestamp: '2026-05-03T07:43:05.474764'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Wave 4 — Re-seed Lilymay; flip Phase 1 gate

## Why this exists

With the wiring repaired (Wave 2) and verified (Wave 3), the seed can finally land. Phase 1 G2/G3 specifically verify that Lilymay's complete learner profile is reachable end-to-end. This task runs the seed script, captures evidence, and updates `phase-1-validation.md`.

Producer for [Contract 3](../../../tasks/backlog/graphiti-runtime-integration-repair/IMPLEMENTATION-GUIDE.md#contract-3-lilymay-seed). Consumer of [Contract 2](../../../tasks/backlog/graphiti-runtime-integration-repair/IMPLEMENTATION-GUIDE.md#contract-2-wired-graphiti-client).

## Acceptance Criteria

- [ ] **AC-SEED-01** — `python scripts/seed_student_model.py` runs successfully against live FalkorDB at `whitestocks:6379`, database `study_tutor`. All 25 entity writes (per `TASK-GSM-006` schema) succeed without 401s, timeouts, or `GroupIdValidationError` failures.
- [ ] **AC-SEED-02** — `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` returns the Student entity with the expected attributes — `year_group=11`, `target_grade="8"`, non-empty `subjects` list, non-empty `topic_confidences` map.
- [ ] **AC-SEED-03** — `get_student_state(client, "lilymay")` (the existing helper from `student_model.py`) returns a non-empty `StudentState` populated from the live graph (i.e. not the bootstrap-empty case from `GroupsNodesNotFoundError` swallow).
- [ ] **AC-SEED-04** — Re-running the seed is idempotent — `python scripts/seed_student_model.py` a second time emits `event=seeding_skipped` (the existing `student_model.py` skip-if-present guard fires) and exits 0 without re-issuing entity writes.
- [ ] **AC-SEED-05** — `docs/research/ideas/phase-1-validation.md` is updated:
    - **G2** flips from "Falsified" to "Held". Evidence: log excerpt of the 25-write seed run + `mcp__graphiti__search_nodes` JSON response with the Student entity.
    - **G3** flips from "Falsified" to "Held". Evidence: `get_student_state(client, "lilymay")` returns `StudentState(year_group=11, target_grade='8', subjects=[...], topic_confidences={...})` — paste the live JSON.
    - The dependent items **G4/G5/G6/G13** (which require an MCP demo session) remain "Falsified" until Wave 5 closes them.
- [ ] **AC-SEED-06** — Stale-index cleanup if needed: if `Connection closed by server` warnings escalate into actual write failures, the FalkorDB graph is dropped via `redis-cli -h whitestocks -p 6379 GRAPH.DELETE study_tutor` and the seed re-run. Document if this happens; otherwise leave in place.
- [ ] **AC-SEED-07** — Wall-clock for the seed run captured. Expected ~30 min on MacBook ollama (78s/`add_episode` median × 25 writes + helper.drain serial overhead). Anomalies (≥45 min) get a structured-log review and notes added to the risk register for Wave 5 planning.
- [ ] **AC-SEED-08** — All modified files (the validation doc + any seed-script touch-ups) pass project-configured lint/format checks with zero errors.

## Test Requirements

Operational acceptance via real-graph verification rather than unit tests. The "tests" are:

- The seed script itself (already extensively tested in TASK-GSM-006).
- The MCP-side `mcp__graphiti__search_nodes` and `get_student_state` calls used as evidence — these are read-back assertions against the live graph state.
- Re-running the seed twice (idempotency) is the regression test for the skip-if-present guard.

No new test files required — this is a verification wave.

## Implementation Notes

### Seed runtime is LLM-bound

Per F8 in the review: 78s/`add_episode` × 25 writes ≈ 32 min wall-clock. `chunk_extraction_concurrency: 4` doesn't help because the seed serialises writes via `helper.drain()` to keep ordering deterministic. Don't try to parallelise — the parent-task risk register already captured this and accepted the cost for a one-off seed.

### YAML toggle for GB10 vs MacBook ollama

If MacBook ollama is offline at seed time, edit `.guardkit/graphiti.yaml`:
```yaml
llm_provider: vllm                          # was: ollama
llm_base_url: http://promaxgb10-41b1:9000/v1  # was: http://richards-macbook-pro...
llm_model: qwen-graphiti                    # was: qwen2.5:14b-instruct-q4_K_M
```
The `qwen-graphiti` alias is always-loaded on llama-swap (zero swap latency). Single-line revert when MacBook is back.

### Phase 1 gate update — exact format

Inside `docs/research/ideas/phase-1-validation.md`, find the block listing G2 and G3 as "Falsified". Change the status marker and append an Evidence sub-block:

```markdown
**G2** — ~~Falsified~~ → **Held** (2026-05-02)
Evidence:
  - Seed run log: 25/25 writes succeeded in NNs (paste timestamp range)
  - mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"]):
    [paste JSON]
```

Same shape for G3. G4/G5/G6/G13 stay "Falsified" with a note "blocked on Wave 5 MCP demo" — Wave 5 closes them.

### Why not flip G4/G5/G6/G13 here

G4 = a tutor session round-trips. G5 = Coach feedback observable. G6 = session_completed episode written. G13 = end-to-end MCP demo runs. None of these are seed-side; they all require a live tutor session conducted from Claude Desktop. That's Wave 5's scope. Flipping them here would be a false-evidence claim.

## Cross-references

- [IMPLEMENTATION-GUIDE.md §4 Contract 2 + Contract 3](./IMPLEMENTATION-GUIDE.md#section-4-integration-contracts)
- `scripts/seed_student_model.py` — seed entry point
- `docs/research/ideas/phase-1-validation.md` — gate file
- `docs/research/ideas/graphiti-latency-spike-results.md` — `add_episode` latency context
- TASK-GSM-006 (sibling) — the original seed-script implementation

## Seam Tests

The following seam test validates that the wired client contract is honoured at the seed-script boundary.

```python
"""Seam test: verify seed script consumes wired Graphiti client correctly."""
import asyncio

import pytest

from study_tutor.knowledge.graphiti_client import (
    get_client,
    load_graphiti_config_from_yaml,
)


@pytest.mark.seam
@pytest.mark.integration_contract("WiredGraphitiClient")
@pytest.mark.skipif(
    "STUDY_TUTOR_LIVE_GRAPHITI_SMOKE" not in __import__("os").environ,
    reason="live FalkorDB required",
)
@pytest.mark.asyncio
async def test_seed_script_uses_wired_client():
    """Verify the seed-script entry point gets a wired client (non-None LLM/embedder).

    Contract: scripts/seed_student_model.py must obtain its Graphiti instance
              via load_graphiti_config_from_yaml() + get_client(); the returned
              client has non-None llm_client and embedder pointing at local
              endpoints.
    Producer: TASK-GR-WIRE → consumed here in TASK-GR-SEED.
    """
    config = load_graphiti_config_from_yaml()
    wrapper = await get_client(config)

    assert wrapper is not None, "Wired client must construct (live FalkorDB up?)"
    inner = wrapper.client_or_none
    assert inner is not None
    assert inner.llm_client is not None, "Wired LLM client expected"
    assert inner.embedder is not None, "Wired embedder expected"
    # Cross-encoder is the sentinel — accessing any attribute raises
    with pytest.raises(RuntimeError, match="DECISION-DF-001"):
        inner.cross_encoder.predict(["q"], ["d"])

    await wrapper.close()
```
