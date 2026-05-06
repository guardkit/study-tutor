---
id: TASK-GR-DEMO
title: "Wave 5 \u2014 End-to-end MCP tutor session via Claude Desktop; close G3/G4/G5/G6/G13\
  \ with live evidence"
task_type: feature
parent_review: TASK-REV-GR1A
parent_task: TASK-PH2-GR-001
feature_id: FEAT-FD32
wave: 5
implementation_mode: task-work
complexity: 3
estimated_minutes: 45
dependencies:
- TASK-GR-SEED
unblocked_by:
- TASK-GR-PMT
- TASK-GR-WIRE
- TASK-GR-CONF
status: blocked
priority: critical
created: 2026-05-02 00:00:00+00:00
updated: 2026-05-05T22:45:00+00:00
previous_state: backlog
state_transition_reason: "Live MCP demo attempted 2026-05-05. Transport layer works (7-turn session completed) but three implementation gaps prevent gate closure: (1) orchestrator_factory not wired — MCP runs Phase 0 single-LLM path, no Coach invocation; (2) player prompt is placeholder stub — no Socratic behaviour; (3) Graphiti write-back in tutor_session_end is a TODO — no session episode or confidence update. See docs/reviews/REVIEW-TASK-GR-DEMO-2026-05-05.md for full findings. TASK-REV-GRD5 (2026-05-05) reviewed and spawned three unblockers via /task-review [I]mplement: TASK-GR-PMT (BLOCK-2), TASK-GR-WIRE (BLOCK-1+3a), TASK-GR-CONF (BLOCK-3b). All three live at tasks/backlog/wave5-mcp-blockers/. Re-attempt this task (autobuild_state.current_turn carries forward; no reset) once the three unblockers ship."
tags:
- graphiti
- mcp
- tutor-session
- phase-1-gate-closure
- human-in-the-loop
- phase-2
related:
- TASK-PH2-GR-001
consumer_context:
- task: TASK-GR-WIRE
  consumes: WiredGraphitiClient
  framework: MCP server (study-tutor) consumed by Claude Desktop
  driver: tutor_start_session / tutor_turn / tutor_session_end MCP handlers
  format_note: MCP handlers obtain their Graphiti client via load_graphiti_config_from_yaml()
    + get_client(); the wired client must succeed against the same .guardkit/graphiti.yaml
    the seed used in Wave 4.
- task: TASK-GR-SEED
  consumes: LilymaySeed
  framework: MCP tutor handlers reading from the same FalkorDB
  driver: get_student_state(client, 'lilymay') called inside tutor_start_session
  format_note: Live FalkorDB rows in group_id='student-lilymay' written by Wave 4;
    Wave 5 reads them at session start.
autobuild_state:
  current_turn: 2
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-FD32
  base_branch: main
  started_at: '2026-05-03T10:32:08.626351'
  last_updated: '2026-05-03T11:10:30.129919'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Advisory (non-blocking): task-work produced a report with 2 of 3\
      \ expected agent invocations. Missing phases: 3 (Implementation). Consider invoking\
      \ these agents via the Task tool to strengthen stack-specific quality:\n- Phase\
      \ 3: `the stack-specific Phase-3 specialist` (Implementation)\n- Not all acceptance\
      \ criteria met:\n  \u2022 AC-DEMO-01** \u2014 A live MCP tutor session is conducted\
      \ from Claude Desktop with the user as the human-\n  \u2022 AC-DEMO-02** \u2014\
      \ A `session_completed` episode is written to Graphiti and is visible via `mcp__graphit\n\
      \  \u2022 AC-DEMO-03** \u2014 `mcp__graphiti__search_nodes(query=\"<topic from\
      \ session>\", group_ids=[\"student-lilyma\n  \u2022 AC-DEMO-04** \u2014 Turn-level\
      \ latency captured. Record p50 and p95 of `tutor_turn` wall-clock across all\n\
      \  \u2022 AC-DEMO-05** \u2014 `phase-1-validation.md` updated:\n  (2 more)"
    timestamp: '2026-05-03T10:32:08.626351'
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
      \ criteria met:\n  \u2022 AC-DEMO-01** \u2014 A live MCP tutor session is conducted\
      \ from Claude Desktop with the user as the human-\n  \u2022 AC-DEMO-02** \u2014\
      \ A `session_completed` episode is written to Graphiti and is visible via `mcp__graphit\n\
      \  \u2022 AC-DEMO-03** \u2014 `mcp__graphiti__search_nodes(query=\"<topic from\
      \ session>\", group_ids=[\"student-lilyma\n  \u2022 AC-DEMO-04** \u2014 Turn-level\
      \ latency captured. Record p50 and p95 of `tutor_turn` wall-clock across all\n\
      \  \u2022 AC-DEMO-05** \u2014 `phase-1-validation.md` updated:\n  (2 more)"
    timestamp: '2026-05-03T10:40:43.306852'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Wave 5 — End-to-end MCP tutor session

## Why this exists

The final close-out gate. Phase 1 G3/G4/G5/G6/G13 explicitly require a live tutor session that round-trips through the MCP boundary, exercises the Coach revision loop, and writes a `session_completed` episode back to Graphiti. With the wiring repaired (Wave 2), verified (Wave 3), and Lilymay seeded (Wave 4), this wave is the human-in-the-loop verification.

Producer for [Contract 4](../../../tasks/backlog/graphiti-runtime-integration-repair/IMPLEMENTATION-GUIDE.md#contract-4-mcp-session-episode). Consumer of [Contracts 2 + 3](../../../tasks/backlog/graphiti-runtime-integration-repair/IMPLEMENTATION-GUIDE.md#section-4-integration-contracts).

## Acceptance Criteria

- [ ] **AC-DEMO-01** — A live MCP tutor session is conducted from Claude Desktop with the user as the human-in-the-loop. Sequence:
    1. `tutor_start_session(student_id="lilymay")` returns a session id and the loaded `StudentState`.
    2. 5–7 × `tutor_turn(...)` exchanges. At least one turn produces a Coach revision (the Coach disagrees with the initial tutor reply and the corrected reply is what reaches the user).
    3. `tutor_session_end(session_id=...)` returns successfully.
- [ ] **AC-DEMO-02** — A `session_completed` episode is written to Graphiti and is visible via `mcp__graphiti__get_episodes(group_ids=["student-lilymay"])`. The episode body contains the session id, the turn count, and a summary suitable for replay.
- [ ] **AC-DEMO-03** — `mcp__graphiti__search_nodes(query="<topic from session>", group_ids=["student-lilymay"])` returns updated `topic_confidences` reflecting the in-session learning. (Confirms Graphiti round-trip: write → entity update → read.)
- [ ] **AC-DEMO-04** — Turn-level latency captured. Record p50 and p95 of `tutor_turn` wall-clock across all 5–7 turns. Append to `docs/research/ideas/phase-1-validation.md` and to `docs/research/ideas/graphiti-latency-spike-results.md` under a "Phase 2 Wave 5 measurement" subsection.
- [ ] **AC-DEMO-05** — `phase-1-validation.md` updated:
    - **G3** flips from "Falsified" to "Held" (already partially done in Wave 4 for the seed-side; Wave 5 confirms read-back through MCP).
    - **G4** flips: "Tutor session round-trips end-to-end". Evidence: pasted excerpt of the MCP session log.
    - **G5** flips: "Coach feedback observable in-session". Evidence: pasted excerpt of the Coach-revised turn.
    - **G6** flips: "session_completed episode written and queryable". Evidence: pasted `mcp__graphiti__get_episodes` JSON.
    - **G13** flips: "End-to-end MCP demo runs". Evidence: session log + p50/p95 latency.
- [ ] **AC-DEMO-06** — Phase 1 is now structurally complete on its own terms. The repair task TASK-PH2-GR-001 can be moved from `backlog/` to `completed/`, and FEAT-PH2-001 (gamification) is unblocked.
- [ ] **AC-DEMO-07** — All modified files (the validation doc + the latency-results doc) pass project-configured lint/format checks with zero errors.

## Test Requirements

Operational acceptance via live MCP transcript, not unit tests. There is no automated test harness for "Claude Desktop performs a 5–7 turn tutoring session with a real LLM at the back" — that's the AC-DEMO-01 manual verification.

The ancillary code paths (`tutor_start_session`, `tutor_turn`, `tutor_session_end`) already have unit and integration tests from prior tasks (the FEAT-PO-002 cluster). This wave does not add new tests; it consumes existing handlers as a black box and asserts the live Graphiti state at the boundaries.

## Implementation Notes

### Pre-flight before starting the session

1. Confirm Wave 4's seed is in place: `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` returns a Student entity.
2. Confirm `get_student_state(client, "lilymay")` returns non-empty (i.e. AC-SEED-03 was actually achieved).
3. Confirm Claude Desktop's MCP config points at the study-tutor server and is reachable.
4. Confirm the LLM endpoint is up: `curl http://promaxgb10-41b1:9000/v1/models` (or the MacBook fallback URL) returns the expected aliases.

If any pre-flight fails, fix and re-run before opening the session — don't push through and pollute the evidence trail.

### Conducting the session — pick a topic with measurable confidence delta

Choose a topic from Lilymay's seeded `topic_confidences` that is currently mid-range (e.g. confidence 0.5–0.7). Conduct the session about that topic. AC-DEMO-03 asserts the post-session confidence has moved — picking a topic at 0.95 makes that signal hard to detect; picking one at 0.0 risks "no movement because the student doesn't know enough to update".

### Coach revision is required, not optional

AC-DEMO-01.2 explicitly requires "at least one Coach revision observed". If the Coach never disagrees in 7 turns, that's evidence the Coach calibration is too lax — note it for the FEAT-PH2-001 follow-up but flag the wave as Held only if a revision is observed. Re-conduct the session with a more challenging topic if needed.

### Capturing latency — instrumentation already exists

The `tutor_turn` handler emits a structured-log line with elapsed wall-clock per turn (from FEAT-PO-002's instrumentation). Grep the MCP server log:
```bash
grep '"event":"tutor_turn_complete"' study-tutor-mcp.log | jq -r '.elapsed_ms' | sort -n
```
Compute p50 (median of 5–7 values) and p95 (use linear interpolation; for 7 turns, p95 = 6.7th percentile ≈ value-7). Don't bootstrap or use a stats library — these are tiny samples; report point values.

### After the session — finalising the parent task

After AC-DEMO-05 lands, move TASK-PH2-GR-001 from `tasks/backlog/` to `tasks/completed/2026-05/`, and move TASK-REV-GR1A from `tasks/in_review/` to `tasks/completed/2026-05/`. The 5 wave subtasks (TASK-GR-LOAD ... TASK-GR-DEMO) follow them as they each complete.

## Cross-references

- [IMPLEMENTATION-GUIDE.md §4 Contracts 2/3/4](./IMPLEMENTATION-GUIDE.md#section-4-integration-contracts)
- `docs/research/ideas/phase-1-validation.md` — gate file
- `docs/research/ideas/graphiti-latency-spike-results.md` — latency record
- TASK-GR-SEED (Wave 4) — produces Lilymay state this wave consumes
- TASK-PH2-GR-001 (parent) — completes on this wave's AC-DEMO-06

## Seam Tests

This wave's "seam test" is operational: the MCP session itself is the boundary verification. The closest pytest-style stub that would mock the human-in-the-loop is below — kept for traceability but NOT a substitute for AC-DEMO-01.

```python
"""Seam test stub: verify MCP handlers obtain a wired client + reach Lilymay seed."""
import pytest

from study_tutor.knowledge.graphiti_client import (
    get_client,
    load_graphiti_config_from_yaml,
)
from study_tutor.knowledge.queries import get_student_state


@pytest.mark.seam
@pytest.mark.integration_contract("LilymaySeed")
@pytest.mark.skipif(
    "STUDY_TUTOR_LIVE_GRAPHITI_SMOKE" not in __import__("os").environ,
    reason="live FalkorDB + post-Wave-4 seed required",
)
@pytest.mark.asyncio
async def test_lilymay_seed_reachable_via_wired_client():
    """Verify the wired client + Wave-4 seed compose end-to-end.

    Contract: get_student_state(client, 'lilymay') returns a non-empty
              StudentState after Wave 4 has run.
    Producer chain: TASK-GR-WIRE → TASK-GR-SEED → consumed here.
    """
    config = load_graphiti_config_from_yaml()
    wrapper = await get_client(config)
    assert wrapper is not None

    state = await get_student_state(wrapper.client_or_none, "lilymay")
    assert state is not None
    assert state.year_group == 11
    assert state.target_grade == "8"
    assert len(state.subjects) > 0
    assert len(state.topic_confidences) > 0

    await wrapper.close()
```
