---
id: TASK-DTL-005
title: Session-end summary, F3 episode write, session.completed emit, lifecycle race, and shutdown drain
task_type: feature
parent_review: TASK-REV-DTL3
feature_id: FEAT-PH1-003
wave: 3
implementation_mode: task-work
complexity: 6
estimated_minutes: 90
dependencies:
  - TASK-DTL-003
  - TASK-DTL-004
status: backlog
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
priority: high
tags: [feat-ph1-003, session-end, F3, session-completed, events, drain, lifecycle, FEAT-PH1-003]
related_features:
  - FEAT-PH1-003
related_tasks:
  - TASK-GSM-002  # Episode types — SessionCompletedEpisode shape
  - TASK-GSM-004  # Async write helper — consumed for write_session_episode + drain
  - TASK-DTL-003  # Orchestrator — needed for in-flight-turn detection at session end
  - TASK-DTL-004  # Per-observation write dispatch shape — symmetric for F3
consumer_context:
  - task: TASK-GSM-004
    consumes: GraphitiWriteHelper
    framework: "Python asyncio + deepagents in-process events bus (CC-11)"
    driver: "graphiti-core add_episode (median 78.98s) — fire-and-forget; helper.drain() coroutine for graceful shutdown"
    format_note: "Helper MUST expose: write_session_episode(student_id, episode: SessionCompletedEpisode) -> None (coroutine, called via asyncio.create_task) and drain(timeout: float = GRAPHITI_DRAIN_WINDOW) -> None (coroutine awaited at shutdown). The drain window default is 5.0 seconds (ASSUM-011 resolution). The drain MUST be awaitable from the runtime shutdown hook; it returns when either all in-flight tasks finish or the timeout elapses."
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Session-end summary, F3 episode write, session.completed emit, lifecycle race, and shutdown drain

## Description

Implement `tutor_session_end` end-to-end:

1. Resolve any in-flight turn (3s inner timeout — F4 lifecycle race
   resolution per TASK-REV-DTL3 review).
2. Generate the session-end narrative summary (1-2 sentences, topics,
   AOs, turns, duration, misconceptions surfaced).
3. Transition session state `active → ended` (with the I-T6 zero-turn
   guard).
4. Emit `session.completed` on the in-process events bus, **before**
   the F3 Graphiti write task is scheduled (DDR-003).
5. Schedule the F3 write via `asyncio.create_task(write_helper.
   write_session_episode(...))` — fire-and-forget per CC-13.
6. Return the caller-facing acknowledgement within the 2s budget per
   ASSUM-004.
7. Wire `write_helper.drain(timeout=GRAPHITI_DRAIN_WINDOW)` into the
   runtime shutdown hook (ASSUM-011 resolution).

## Scope

- `tutor_session_end(session_id)` MCP handler implementation:
  - Inner timeout (3s) awaiting any in-flight `tutor_turn` for this
    session (F4 lifecycle race resolution); on timeout, the in-flight
    turn is discarded with no append to `TutorSession.turns` (per
    @edge-case @concurrency @lifecycle scenario at .feature line
    452-457)
  - Generate session-end summary: topics covered, AOs exercised,
    turn count, duration, narrative summary (1-2 sentences per
    ASSUM-010), misconceptions surfaced
  - I-T6 guard: if `len(session.turns) == 0`, do **NOT** emit
    `session.completed` and do **NOT** schedule the F3 write (per
    @edge-case @events @invariant scenario at .feature line 333-339)
  - Otherwise, on the same code path inside the handler, in this exact
    order:
    1. Transition state to `ended`
    2. Emit `session.completed` on the in-process bus
    3. `asyncio.create_task(write_helper.write_session_episode(...))`
    4. Return `{ session_id, status: "ended" }` to the MCP caller
  - The handler does **not** await the F3 write task
- `SessionCompletedEpisode` payload generation in
  `src/study_tutor/tutoring/session/summary.py`:
  - Pulls topics, AOs, turn count, duration from the live
    `TutorSession` instance
  - Pulls misconception list from the per-session aggregator that
    accumulates Coach observations (in-memory only — the F1 writes are
    independent of this aggregation per DDR-002 §Consequences "no
    session-scoped misconception list... for batched flush" — the in-
    memory list here is only for the **summary** field, not for
    deferred persistence)
  - Generates the narrative summary (LLM call or template — concrete
    choice during implementation)
- F3 dispatch failure isolation: a failure inside the F3 write task is
  logged with structured fields; `session.completed` was already
  emitted on state transition; the caller observes the session as
  ended regardless (per @negative @async @session-end scenario at
  .feature line 273-280)
- Slow-helper resilience: even when the helper is configured to take
  longer than the session-end budget, the caller-facing
  acknowledgement returns within the budget; the F3 write is dispatched
  as a background task (per @boundary @latency @async scenario)
- Shutdown drain wiring: the runtime shutdown hook awaits
  `write_helper.drain(timeout=GRAPHITI_DRAIN_WINDOW)`; in-flight
  writes are allowed to finish within the 5s window (ASSUM-011
  resolution); writes that did not finish within the window are
  logged with structured fields (per @edge-case @async @lifecycle
  scenario at .feature line 379-386)
- `GRAPHITI_DRAIN_WINDOW = 5.0` constant defined in TASK-GSM-004's
  helper module (per ASSUM-011 resolution); this task **consumes** it,
  not redefines

## Out of Scope

- The shared write helper itself (TASK-GSM-004 — including
  `write_session_episode`, `drain`, `GRAPHITI_DRAIN_WINDOW`)
- F1 misconception write dispatch (TASK-DTL-004)
- The `PlayerCoachOrchestrator` (TASK-DTL-003 — consumed for in-flight
  turn detection)
- Subscriber-side handling of `session.completed` (gamification
  consumers etc. — out of scope for FEAT-PH1-003)

## Acceptance Criteria

- [ ] `tutor_session_end` emits `session.completed` on the state
      transition, before the F3 Graphiti write task is scheduled (covers
      @key-example @events @async scenario at .feature line 107-112) —
      assertable by mocking `asyncio.create_task` and asserting the
      bus emit happened first
- [ ] Subscribers observe `session.completed` regardless of whether the
      F3 Graphiti write succeeds (DDR-003 conformance)
- [ ] Session abandoned before any tutor turn does NOT emit
      `session.completed` and does NOT schedule the F3 write (covers
      @edge-case @events @invariant scenario; I-T6 invariant)
- [ ] `SessionCompletedEpisode` records: topics covered, AOs exercised,
      number of turns, duration, narrative summary (1 or 2 sentences),
      misconceptions surfaced (covers @key-example @smoke @session-end
      @summary scenario)
- [ ] Narrative summary length is 1 or 2 sentences (both acceptable
      per ASSUM-010 / @boundary @summary Scenario Outline)
- [ ] Caller-facing acknowledgement returns within the 2s session-end
      budget even when the helper is slow (covers @boundary @latency
      @async scenario)
- [ ] F3 write failure → structured-log line; `session.completed`
      already emitted; caller observes session as ended (covers
      @negative @async @session-end scenario)
- [ ] Misconception write in flight at session end coexists with the
      F3 write — both run independently to completion or failure;
      neither blocks the other (covers @edge-case @async @concurrency
      scenario at .feature line 313-320)
- [ ] In-flight turn at session-end resolves via the F4 lifecycle
      rule: complete-and-append within 3s, OR discard with no append;
      no turn is ever appended after the session is marked ended; no
      `session.completed` event is emitted before the in-flight turn
      has been resolved (covers @edge-case @concurrency @lifecycle
      scenario at .feature line 452-457)
- [ ] Runtime shutdown hook awaits `write_helper.drain(timeout=5.0)`;
      in-flight writes finish within the window or are logged with
      structured fields (covers @edge-case @async @lifecycle scenario
      at .feature line 379-386)
- [ ] All modified files pass project-configured lint/format checks
      with zero errors

## Test Requirements

- [ ] Unit test: ordering of state transition → bus emit → F3
      `create_task` call → handler return; assert order via mock
      timestamps or strict mock-call ordering
- [ ] Unit test: I-T6 zero-turn session does not emit
      `session.completed` and does not schedule F3
- [ ] Unit test: narrative summary at 1 sentence and at 2 sentences
      both pass the `SessionCompletedEpisode` validation
- [ ] Latency test: session-end p95 < 2s under simulated 78.98s helper
      latency (the helper's `add_episode` call is in a background task
      that the handler does not await)
- [ ] Failure-injection test: F3 write task raises mid-write →
      structured log line; `session.completed` already on the bus;
      session shows as ended in `tutor_session_status`
- [ ] Concurrency test: in-flight misconception write + new F3 write
      both complete independently
- [ ] Lifecycle test: in-flight turn at session-end completes within
      3s → appended; in-flight turn that exceeds 3s → discarded with
      no append; assertion on `len(session.turns)` in both cases
- [ ] Shutdown-drain test: 3 in-flight writes; drain called with 5s
      timeout; writes that complete within 5s are awaited; writes that
      don't are logged

## Seam Tests

The following seam tests validate two integration contracts with the
TASK-GSM-004 producer (shared write helper): (a) the
`write_session_episode` dispatch shape, (b) the `drain` shutdown
contract.

```python
"""Seam tests: validate F3 dispatch and shutdown drain contracts with
TASK-GSM-004 (shared write helper)."""
import asyncio
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.seam
@pytest.mark.integration_contract("GraphitiWriteHelper")
async def test_session_end_emits_event_before_f3_create_task():
    """Verify session.completed emits on state transition BEFORE the
    F3 Graphiti write task is scheduled.

    Contract: DDR-003 — events emit on state transition; writes
    happen on observation; never coupled.
    Producer: TASK-GSM-004
    """
    bus_mock = AsyncMock()
    helper_mock = AsyncMock()
    helper_mock.write_session_episode = AsyncMock()

    call_log = []
    bus_mock.emit = AsyncMock(side_effect=lambda *a, **kw: call_log.append("emit"))
    with patch(
        "asyncio.create_task",
        side_effect=lambda coro: call_log.append("create_task"),
    ):
        # Invoke tutor_session_end with a session that has >= 1 turn.
        # ... (test scaffold — concrete imports during implementation)

        # Seam assertion: emit happened BEFORE create_task on the same
        # code path. DDR-003 conformance.
        assert call_log.index("emit") < call_log.index("create_task")


@pytest.mark.seam
@pytest.mark.integration_contract("GraphitiWriteHelper")
async def test_shutdown_drain_uses_graphiti_drain_window_constant():
    """Verify shutdown wiring awaits helper.drain with the
    GRAPHITI_DRAIN_WINDOW constant (ASSUM-011 resolution).

    Contract: drain window is helper-side, not per-call; default 5.0s.
    Producer: TASK-GSM-004
    """
    helper_mock = AsyncMock()
    helper_mock.drain = AsyncMock()

    # Invoke the runtime shutdown hook with the helper injected.
    # ... (test scaffold — concrete imports during implementation)

    # Seam assertion: drain was called once with the helper-defined
    # default window (NOT a per-call argument from this task's code).
    helper_mock.drain.assert_awaited_once()
    args, kwargs = helper_mock.drain.call_args
    assert args == () and ("timeout" not in kwargs or kwargs["timeout"] == 5.0), (
        "ASSUM-011 violation: drain timeout should be the helper's "
        "GRAPHITI_DRAIN_WINDOW default (5.0s), not a caller-supplied value"
    )
```

## Implementation Notes

**Why the F4 lifecycle race resolution is "3s inner timeout, then
discard":**
The .feature scenario at line 452-457 deliberately permits both
outcomes ("either complete and append before the session is marked
ended, or be discarded with no append"). The 3s timeout is a
defensible upper bound: turns that are about to complete will land
within it (most are well under that); turns that aren't won't land
within any reasonable session-end budget anyway. The discard path
matches the "session.completed cannot be emitted before the in-flight
turn has been resolved one way or the other" clause.

**Why we do not buffer Coach observations into a session-end batched
flush:**
DDR-002 §Decision: "The Tutor handler does not aggregate Coach
observations across turns. No session-scoped misconception list, no
batched session-end flush of Coach output." The in-memory misconception
list this task uses for the **summary** field is read-only for that
purpose; F1 writes were already dispatched per-observation by the Coach
AsyncSubAgent in TASK-DTL-004. We do not double-write.

**Why drain timeout lives on the helper, not on each flush site:**
ASSUM-011 resolution. A per-flush-point timeout would require every
flush site to know the global shutdown contract; that proliferates
"shutdown shapes" and breaks the helper's single-dispatch-surface
property. One constant on the helper, called from one shutdown hook.

**Why I-T6 is enforced as a guard at the handler boundary, not at the
events bus:**
The I-T6 invariant is a domain rule about session lifecycle. Putting
the guard at the events bus would make the bus aware of session-
internal state (turn count). Keeping the guard at the handler keeps
the bus dumb and the handler responsible for "should I emit?"
decisions, which is the correct separation per the Shared Kernel B
design.

## Test Execution Log

[Populated by /task-work]
