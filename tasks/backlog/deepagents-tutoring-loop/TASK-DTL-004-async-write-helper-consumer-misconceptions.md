---
id: TASK-DTL-004
title: Async write helper consumer for per-misconception writes (F1)
task_type: feature
parent_review: TASK-REV-DTL3
feature_id: FEAT-PH1-003
wave: 1
implementation_mode: task-work
complexity: 5
estimated_minutes: 75
dependencies: []
status: in_review
created: 2026-04-29 00:00:00+00:00
updated: 2026-04-29 00:00:00+00:00
priority: high
tags:
- feat-ph1-003
- async
- graphiti
- misconception
- F1
- fire-and-forget
- FEAT-PH1-003
related_features:
- FEAT-PH1-003
related_tasks:
- TASK-GSM-002
- TASK-GSM-003
- TASK-GSM-004
consumer_context:
- task: TASK-GSM-004
  consumes: GraphitiWriteHelper
  framework: Python asyncio (helper exposes coroutine methods called via asyncio.create_task
    per CC-13)
  driver: "graphiti-core add_episode (median 78.98s) \u2014 fire-and-forget"
  format_note: "Helper MUST expose: write_misconception(student_id: str, observation:\
    \ MisconceptionObservation) -> None (coroutine). Sanitisation of misconception\
    \ text is the CALLER's responsibility (Coach AsyncSubAgent), NOT the helper's.\
    \ Helper accepts ONE misconception per call (NOT a list) \u2014 per-observation\
    \ ownership per DDR-002."
test_results:
  status: pending
  coverage: null
  last_run: null
autobuild_state:
  current_turn: 2
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-PH1-003
  base_branch: main
  started_at: '2026-04-30T06:53:39.397408'
  last_updated: '2026-04-30T07:27:40.478354'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Advisory (non-blocking): task-work produced a report with 2 of 3
      expected agent invocations. Missing phases: 3 (Implementation). Consider invoking
      these agents via the Task tool to strengthen stack-specific quality:

      - Phase 3: `the stack-specific Phase-3 specialist` (Implementation)

      - BDD oracle: 1 scenario(s) failed during pytest-bdd execution. Implementation
      does not satisfy the Gherkin specification.'
    timestamp: '2026-04-30T06:53:39.397408'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-04-30T07:14:10.538334'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Task: Async write helper consumer for per-misconception writes (F1)

## Description

Wire the Coach AsyncSubAgent (built in TASK-DTL-001) to the shared
Graphiti write helper (TASK-GSM-004) for F1 misconception writes.
Implements the per-observation dispatch shape per DDR-002 — one
`asyncio.create_task` per misconception, never batched. Adds the
sanitisation pass for learner-derived misconception text BEFORE
dispatch (per @edge-case @security @async scenario at .feature line
372-376).

Per Finding F9 of TASK-REV-DTL3: sanitisation lives **inside the Coach
AsyncSubAgent**, not inside the helper. The helper is the dispatch
surface; it is not a content layer.

## Scope

- `Coach._dispatch_misconception(observation)` method on the Coach
  AsyncSubAgent that:
  - Sanitises the misconception payload (strip prompt-injection markers,
    escape newlines/control chars, cap length) — `sanitise_misconception(...)`
  - Calls `asyncio.create_task(self._write_helper.write_misconception(
    student_id, sanitised_observation))` — fire-and-forget
  - Logs a structured line if `create_task` fails to schedule (extreme
    edge — typically only on shutdown)
- `sanitise_misconception(text: str) -> str` pure function in
  `src/study_tutor/tutoring/coach/sanitise.py`:
  - Strips control characters and zero-width chars
  - Escapes potential prompt-injection markers (e.g.
    `<|im_start|>`-style tokens, leading instruction-shaped tokens)
  - Caps length at a sensible upper bound (e.g. 4000 chars; configurable)
- Per-observation dispatch invariant: when the Coach observes N
  misconceptions in a single turn, N independent `create_task` calls
  fire — never one batched call with a list (per @edge-case @async
  @misconception scenario "Two misconceptions observed in the same turn
  are written as two independent episodes")
- Helper-failure isolation: a `write_misconception(...)` failure inside
  the helper is logged with structured fields and does not raise into
  the Coach AsyncSubAgent's task surface (per @negative @async
  @misconception scenario at .feature line 264-270)
- Simultaneous dispatch handling: when the Coach is about to dispatch a
  misconception write and the Tutor handler is about to dispatch a
  topic-confidence-update write at the same moment, both writes are
  scheduled as independent fire-and-forget tasks; structured-log lines
  do not conflate (per @edge-case @concurrency @async scenario at
  .feature line 460-468)

## Out of Scope

- The shared write helper itself (TASK-GSM-004 — this task is the
  Coach-side consumer)
- F2 planner topic-confidence dispatch (Tutor handler concern, not
  Coach concern)
- F3 session-end episode dispatch (TASK-DTL-005)
- The drain surface for shutdown (also TASK-DTL-005, where it's wired
  into the session-end / shutdown path)

## Acceptance Criteria

- [ ] `sanitise_misconception(text)` strips control chars, escapes
      prompt-injection markers, and caps length; persisted episode does
      not contain unescaped injection markers (covers @edge-case
      @security @async scenario at .feature line 372-376)
- [ ] One `asyncio.create_task` call per misconception observation —
      assertable via mocking `asyncio.create_task` and counting
      invocations in a two-misconception-per-turn test (covers
      @edge-case @async @misconception scenario "Two misconceptions
      observed in the same turn are written as two independent
      episodes")
- [ ] Helper write failure is logged with structured fields, not
      raised into the Coach task surface or up to the Tutor handler
      (covers @negative @async @misconception scenario)
- [ ] Misconception persisted within the per-turn budget (turn returns
      to caller within 30s p95 regardless of write completion) — write
      MAY complete after turn return (covers @key-example @smoke @async
      @misconception scenario)
- [ ] Coach dispatcher of the misconception write is the Coach
      AsyncSubAgent itself, not the Tutor handler (DDR-002 conformance
      check; assertable by inspecting call site location)
- [ ] Simultaneous Coach-misconception + handler-confidence-update
      dispatches are independent; neither blocks or is blocked by the
      other; log lines do not conflate (covers @edge-case @concurrency
      @async scenario)
- [ ] All modified files pass project-configured lint/format checks
      with zero errors

## Test Requirements

- [ ] Unit tests for `sanitise_misconception` covering control-char
      stripping, prompt-injection marker escaping, and length capping
- [ ] Property test: sanitiser is idempotent
      (`sanitise(sanitise(x)) == sanitise(x)`)
- [ ] Property test: sanitiser preserves the semantic content of
      ordinary misconception text (round-trip should not destructively
      mangle reasonable English)
- [ ] Mock test: 2 misconceptions in a single turn → 2 independent
      `create_task` invocations
- [ ] Failure-injection test: helper raises mid-write → structured log
      line emitted, no exception surfaces to Coach task or to handler
- [ ] Concurrency test: simultaneous Coach + handler dispatches run
      independently (no shared state interleaving)

## Seam Tests

The following seam test validates the integration contract with the
TASK-GSM-004 producer (shared write helper). The contract is the
single load-bearing one for this task.

```python
"""Seam test: verify per-observation write dispatch contract with
TASK-GSM-004 (shared write helper)."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.seam
@pytest.mark.integration_contract("GraphitiWriteHelper")
async def test_coach_dispatches_one_create_task_per_misconception():
    """Verify Coach AsyncSubAgent dispatches exactly one
    asyncio.create_task per misconception observation.

    Contract: per-observation ownership per DDR-002. Helper accepts
    ONE misconception per call, NEVER a list.
    Producer: TASK-GSM-004
    """
    helper_mock = AsyncMock()
    helper_mock.write_misconception = AsyncMock()

    with patch("asyncio.create_task") as create_task_mock:
        # Build Coach with helper injected; run an evaluator pass that
        # produces TWO distinct misconception observations.
        # ... (test scaffold — concrete imports during implementation)

        # Seam assertions:
        # 1. create_task called exactly twice (once per observation)
        # 2. Each call is a coroutine targeting helper.write_misconception
        # 3. write_misconception NEVER called with a list argument
        assert create_task_mock.call_count == 2
        for call in helper_mock.write_misconception.call_args_list:
            args, kwargs = call
            assert not isinstance(args[1], list), (
                "DDR-002 violation: write_misconception called with list "
                "(per-observation ownership requires one call per misconception)"
            )


@pytest.mark.seam
@pytest.mark.integration_contract("GraphitiWriteHelper")
async def test_coach_sanitises_misconception_before_helper_dispatch():
    """Verify sanitisation happens BEFORE the helper sees the payload.

    Contract: helper does NOT sanitise; Coach AsyncSubAgent does
    (Finding F9 of TASK-REV-DTL3 — helper is dispatch surface only).
    Producer: TASK-GSM-004
    """
    helper_mock = AsyncMock()
    helper_mock.write_misconception = AsyncMock()

    # Inject a misconception with embedded injection markers; verify
    # the helper receives a sanitised version, not the raw learner text.
    # ... (test scaffold — concrete imports during implementation)
```

The two seam assertions above are the load-bearing contract:
(a) one create_task per observation, (b) sanitisation happens caller-
side, not helper-side.

## Implementation Notes

**Why sanitisation is caller-side, not helper-side (Finding F9):**
The shared write helper is the dispatch surface — it knows about
`asyncio.create_task`, structured logging on failure, and the F-id
log dimension. It does **not** know about misconception payloads vs
session episodes vs topic-confidence deltas. Putting content-aware
sanitisation in the helper would force it to switch on payload type,
which breaks the symmetry DDR-002 protects. Sanitisation lives
adjacent to the Coach (where the misconception originates) instead.

**Why per-observation, not per-turn:**
DDR-002 §Decision is unambiguous: "Each Coach observation flushes
independently from inside the Coach's task surface." Batching N
misconceptions into one helper call would re-introduce the session-
scoped buffering DDR-002 explicitly rejects.

**Why the helper accepts a single misconception, not a list:**
This is the API-shape consequence of per-observation ownership. If the
helper accepted a list, the per-observation rule would be a caller-side
discipline that's easy to drift away from. Hard-coding singular at the
helper interface makes drift impossible without an interface change.

## Test Execution Log

[Populated by /task-work]
