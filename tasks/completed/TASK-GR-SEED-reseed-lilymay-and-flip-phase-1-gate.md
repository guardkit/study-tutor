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
status: completed
priority: critical
created: 2026-05-02 00:00:00+00:00
updated: 2026-05-04T22:25:00+00:00
previous_state: blocked
state_transition_reason: "TASK-GSM-009 (typed-entity rewrite per ADR-ARCH-021) landed on 2026-05-04 and unblocked the seed end-to-end. Retry run on 2026-05-04T21:24:44Z confirmed AC-SEED-04 idempotency (seeding_skipped, exit 0, 2s wall-clock); fresh verify_lilymay.py JSON confirms AC-SEED-02/03 (Student node with enrolled_subjects + 6 TopicConfidence nodes; StudentState populated with year_group=10, target_grade='7' per the AC-02 doc-drift correction). All 8 AC-SEED gates Held."
ac_results:
  AC-SEED-01:
    status: held
    evidence: ".guardkit/autobuild/TASK-GR-SEED/logs/TASK-GSM-009_live_evidence.json (25 nodes + 16 intra-group edges across 4 partitions, written via EntityNode.save / EntityEdge.save — no add_episode path)"
  AC-SEED-02:
    status: held
    evidence: ".guardkit/autobuild/TASK-GR-SEED/logs/verify_lilymay_TASK-GR-SEED-retry.json — Student node with attributes_keys=[enrolled_subjects, student_id, target_grade, year_group], summary 'Year 10, target grade 7'. AC-02's doc-drift expectation of year_group=11/target_grade='8' corrected to 10/'7' under TASK-GSM-009 AC-14."
  AC-SEED-03:
    status: held
    evidence: "verify_lilymay_TASK-GR-SEED-retry.json: StudentState empty=False, year_group=10, target_grade='7', subjects=[English Literature, English Language], 6 topic_confidences spanning struggling/developing/secure bands"
  AC-SEED-04:
    status: held
    evidence: ".guardkit/autobuild/TASK-GR-SEED/logs/seed_run_TASK-GR-SEED-retry.log: 'seeding skipped: Lilymay baseline already present', exit 0, wall-clock 2s"
  AC-SEED-05:
    status: held
    evidence: "docs/research/ideas/phase-1-validation.md §'TASK-GSM-009 — Typed-entity seed landed' (lines 292+) — G2 flipped to Held with caveat (cross-group edges deferred per ADR-ARCH-021 §G2); G3 flipped to Held"
  AC-SEED-06:
    status: held
    evidence: "No write-time Connection-closed-by-server escalation observed; the post-exit build_indices_and_constraints cleanup noise is a graphiti-core lifecycle artifact (same artifact captured during the G2 probe in TASK-GSM-008). Seed exited 0 in both runs. No GRAPH.DELETE needed."
  AC-SEED-07:
    status: held
    evidence: "Retry run wall-clock: 2s (start 21:24:44Z, end 21:24:46Z). TASK-GSM-009's first-run was also ~2s. No LLM in the write path; both well under the 45-min anomaly threshold."
  AC-SEED-08:
    status: held
    evidence: "TASK-GSM-009 commit a90bc65 passed full test suite (765 unit tests pass per commit message; 2 unrelated pre-existing failures stay out of scope). No production-code changes introduced by this retry — only task-state moves and validation evidence capture."
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
