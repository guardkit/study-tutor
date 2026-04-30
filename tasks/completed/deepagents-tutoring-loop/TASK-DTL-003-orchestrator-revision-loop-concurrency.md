---
id: TASK-DTL-003
title: Player-Coach orchestrator with bounded revision loop and concurrency isolation
task_type: feature
parent_review: TASK-REV-DTL3
feature_id: FEAT-PH1-003
wave: 2
implementation_mode: task-work
complexity: 7
estimated_minutes: 120
dependencies:
- TASK-DTL-001
status: in_review
created: 2026-04-29 00:00:00+00:00
updated: 2026-04-29 00:00:00+00:00
priority: high
tags:
- feat-ph1-003
- orchestrator
- player-coach
- revision-loop
- concurrency
- latency
- fallback
- FEAT-PH1-003
related_features:
- FEAT-PH1-003
related_tasks:
- TASK-DTL-001
- TASK-DTL-002
test_results:
  status: pending
  coverage: null
  last_run: null
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-PH1-003
  base_branch: main
  started_at: '2026-04-30T07:28:37.755579'
  last_updated: '2026-04-30T07:41:52.418259'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-30T07:28:37.755579'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Task: Player-Coach orchestrator with bounded revision loop and concurrency isolation

## Description

Implement the `PlayerCoachOrchestrator` class that owns a single
Player-Coach turn end-to-end: quote-verifier → Player → Coach →
branch on score → optionally request bounded revisions → return the
accepted reply (or lowest-scoring on exhaustion). Wire the orchestrator
into `tutor_turn`. Honour the per-turn 30s p95 latency budget, the
Coach-unreachable fallback, the Player-unreachable mid-revision fallback,
and the per-session isolation invariant.

## Scope

- `PlayerCoachOrchestrator` class with a single public coroutine
  `run_turn(session_state, learner_message) -> TurnResult`. The class:
  - Holds no session-scoped state (per-turn instance)
  - Calls quote verifier → Player → Coach in order
  - On `decision == "accept"`: returns immediately with the accepted
    reply
  - On `decision == "revise"`: builds `RubricFeedback` from
    `CoachVerdict`, requests a revision from the Player, re-evaluates,
    repeats up to `MAX_REVISION_ATTEMPTS = 3` (per ASSUM-002)
  - On exhaustion (3 failed revisions): returns the **lowest-scoring**
    reply observed across the attempts and writes a silent log marker
    for session-end review (per @boundary @revision-loop scenario)
- Revision-feedback channel: only `RubricFeedback` (structured) is
  passed to the Player on revision. **No** Coach free-text reasoning
  is pasted into the Player's system prompt or user message
  (ASSUM-008 + @edge-case @security @revision-loop scenario)
- Coach-unreachable fallback: if Coach raises (or returns no response
  within its evaluation budget), the Player's response is returned
  under the documented unevaluated-turn fallback policy; the turn is
  flagged for session-end review; **no revision attempts** are made
  against an absent Coach evaluation (per @negative @fallback scenario)
- Player-unreachable mid-revision fallback: if the Player provider
  becomes unavailable between the first response and a requested
  revision, the loop falls back to the unevaluated-turn policy; turn
  flagged with provider-unavailable reason (per @edge-case @integration
  @fallback scenario)
- Misconfigured-loop guard: at session start, validate that no loop
  configuration would route Coach reasoning into the learner-facing
  response path; refuse session start with a clear error if it does
  (per @negative @invariant scenario at .feature line 293-296)
- Per-session isolation: two concurrent sessions get two independent
  `PlayerCoachOrchestrator` instances; misconception writes from one
  session can never be attributed to another learner (per @edge-case
  @concurrency scenario)
- Stable-turn guarantee: if a turn has already been accepted at one
  revision level, no subsequent revision is emitted in its place
  (per @edge-case @revision-loop scenario at .feature line 400-404)
- Wire `PlayerCoachOrchestrator.run_turn` into the `tutor_turn` MCP
  handler

## Out of Scope

- Coach factory (TASK-DTL-001) and rubric scoring (TASK-DTL-002) —
  consumed
- Session-end summary / F3 / `session.completed` emit (TASK-DTL-005)
- Shared write helper internals (TASK-GSM-004) — consumed via Coach
  AsyncSubAgent's injected helper
- Quote-verifier internals (FEAT-PH1-004) — consumed via TASK-DTL-002

## Acceptance Criteria

- [ ] First-attempt accept: Player response at-or-above threshold is
      returned to the learner; Coach reasoning recorded session-only;
      Coach reasoning never shown to learner (covers @key-example
      @smoke @player-coach scenario)
- [ ] Revision-then-accept: below-threshold response triggers a
      revision; the original below-threshold response is **never** shown
      to the learner (covers @key-example @smoke @revision-loop)
- [ ] Three-attempt exhaustion: after 3 sub-threshold attempts, the
      **lowest-scoring** reply observed is returned; a silent log
      marker is recorded for session-end review; no further revision
      attempted (covers @boundary @revision-loop)
- [ ] Latency budget: 29.99s and 30.00s are within budget; 30.01s is
      logged as over-budget for review (covers @boundary @latency
      Scenario Outline)
- [ ] Player revision input is strictly `RubricFeedback`; no part of
      Coach free-text reasoning is passed as a system-level instruction
      to the Player (covers @edge-case @security @revision-loop
      scenario "Directive-shaped Coach text on a rejected turn is not
      obeyed by the Player on revision")
- [ ] Coach-unreachable: Coach returns no response within its
      evaluation budget → Player's response returned under fallback;
      turn flagged for review; no revision attempts (covers @negative
      @fallback scenario)
- [ ] Player-unreachable mid-revision: Player provider unavailable for
      revision → unevaluated-turn fallback; turn flagged with
      provider-unavailable reason (covers @edge-case @integration
      @fallback scenario)
- [ ] Misconfigured-loop guard: session start fails if loop config
      would route Coach reasoning to the learner-facing response (covers
      @negative @invariant scenario at .feature line 293-296)
- [ ] Concurrency isolation: two concurrent sessions' Coach evaluations
      do not contaminate each other; neither session's misconception
      write is attributed to the other learner (covers @edge-case
      @concurrency scenario)
- [ ] Stable-turn guarantee: if a turn has been accepted at one
      revision level, a subsequent revision is not emitted in its place
      (covers @edge-case @revision-loop scenario at .feature line
      400-404)
- [ ] Adversarial corpus content (chunk text resembling tool-call
      instruction) does not cause the Coach to attempt a tool call —
      structurally guaranteed by D5 (`tools=[]`) but asserted as a
      regression test (covers @edge-case @security @coach-shape
      scenario)
- [ ] Learner prompt-injection against the Coach: Coach produces
      verdict as structured evaluation only; does not change decision
      shape, score schema, or output channel based on learner text
      (covers @edge-case @security @coach-shape scenario at
      .feature line 422-428)
- [ ] All modified files pass project-configured lint/format checks
      with zero errors

## Test Requirements

- [ ] Unit tests for the orchestrator's branching logic on
      accept/revise decisions (mock Player + Coach)
- [ ] Unit test for revision exhaustion: lowest-scoring reply
      selection across 3 attempts
- [ ] Unit test for `RubricFeedback`-only revision channel: assert
      that the Player.revise(...) call signature does NOT receive any
      free-text reasoning argument
- [ ] Latency test: `run_turn` p95 measured under simulated
      Player+Coach latency stays under 30s for 95% of 100 trials
- [ ] Concurrency test: two `PlayerCoachOrchestrator` instances run
      concurrently against two fake sessions; Coach observations from
      one are not visible to the other
- [ ] Failure-injection: Coach unreachable → Player response returned
      under fallback, no revision attempted
- [ ] Failure-injection: Player unreachable on revision → unevaluated-
      turn fallback applied
- [ ] Negative test: misconfigured loop attempting to route Coach
      reasoning into learner-facing response is rejected at session
      start

## Implementation Notes

**Why a class, not a function:**
The orchestrator owns enough state (attempt counter, lowest-scoring-
observed reply, accept-stable flag) that a class is the natural shape.
Per-turn instantiation keeps it stateless across turns, which is what
gives concurrency isolation for free.

**Why MAX_REVISION_ATTEMPTS is a module-level constant, not config:**
ASSUM-002 fixes the value at 3. If this becomes tuneable later, it
moves to config; for now, a constant keeps the contract explicit and
greppable.

**Why the lowest-scoring-on-exhaustion rule:**
Per the @boundary @revision-loop scenario, exhaustion releases the
**lowest-scoring** reply, not the latest. Releasing the latest would
mask a regression where the Player's revisions get progressively worse;
the lowest-scoring rule preserves the diagnostic signal of "the system
truly tried and these were the outputs."

## Test Execution Log

[Populated by /task-work]
