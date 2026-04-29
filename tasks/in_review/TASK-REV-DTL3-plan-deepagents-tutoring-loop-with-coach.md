---
id: TASK-REV-DTL3
title: "Plan: DeepAgents Tutoring Loop with Coach"
task_type: review
status: review_complete
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
priority: high
tags: [feature-plan, deepagents, coach, player-coach, rubric, graphiti, async, phase-1, FEAT-PH1-003]
complexity: 8
context_files:
  - features/deepagents-tutoring-loop/deepagents-tutoring-loop_summary.md
  - features/deepagents-tutoring-loop/deepagents-tutoring-loop.feature
  - features/deepagents-tutoring-loop/deepagents-tutoring-loop_assumptions.yaml
  - docs/design/decisions/DDR-002-coach-async-subagent-owns-graphiti-writes.md
  - docs/design/decisions/DDR-003-session-completed-emits-on-state-transition.md
  - docs/design/contracts/API-tutoring.md
  - docs/research/ideas/phase-1-scope.md
  - docs/research/ideas/phase-1-build-plan.md
clarification:
  context_a:
    timestamp: 2026-04-29T00:00:00Z
    decisions:
      review_focus: all
      tradeoff_priority: balanced
      assumption_resolution: recommend_both
      specific_concerns: spec_driven
      task_slice_readiness: partial
    directives:
      - "Produce explicit recommended resolutions for ASSUM-006 and ASSUM-011"
      - "Flag obvious task-slice sequencing risks; do not produce a full slice plan"
      - "Cover all review dimensions equally"
      - "Weight speed/quality/maintainability/cost trade-offs equally"
      - "Let spec content drive the findings agenda"
review_results:
  mode: decision
  depth: standard
  recommended_option: "Option A — Deterministic PlayerCoachOrchestrator class + Coach AsyncSubAgent + shared Graphiti write helper"
  options_count: 4
  subtask_count: 5
  estimated_effort_hours: "22-28 sequential / ~14h elapsed with wave-2 parallelism"
  confidence: high
  pre_implementation_signoffs:
    - "ASSUM-006 (Coach reasoning > 200 word cap — recorded in full + flagged, never truncated)"
    - "ASSUM-011 (5s GRAPHITI_DRAIN_WINDOW constant on shared helper)"
    - "Cross-feature: TASK-GSM-004 helper surface (write_misconception, write_planner_topic_confidence, write_session_episode, drain)"
    - "F4 lifecycle race resolution (3s inner timeout for in-flight turn at session end)"
  report_path: .guardkit/reviews/TASK-REV-DTL3-review-report.md
  completed_at: 2026-04-29T00:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Plan: DeepAgents Tutoring Loop with Coach

## Description

Plan FEAT-PH1-003 — the Phase 1 DeepAgents Player-Coach tutoring loop for study-tutor.

This is a `/feature-plan` review task. It precedes implementation and produces:

1. A technical-options analysis covering the Coach AsyncSubAgent factory,
   the six-criterion weighted rubric, the Player-Coach revision loop wiring,
   the session-end summary generation, and the fire-and-forget Graphiti
   write-back ownership at F1/F2/F3 flush points.
2. A recommended approach plus a subtask breakdown ready for [I]mplement.
3. Explicit risk callouts and recommended resolutions for ASSUM-006 (Coach
   reasoning > 200 word cap behaviour) and ASSUM-011 (5s shutdown grace
   window for in-flight Graphiti writes).
4. A partial task-slice sequencing assessment (obvious risks only — full
   slice planning is handled by /feature-plan's [I]mplement step).

## Scope

- **Coach factory + structural invariants**: `tools=[]`, no filesystem
  backend, never-learner-facing, two-provider invariant (Coach != Player)
  enforced at construction time per D5 / agentic-dataset-factory.
- **Six-criterion weighted rubric**: curriculum accuracy, AO alignment,
  scaffolding depth, grade-appropriate language, constructive feedback,
  quote fidelity. Threshold acceptance at-or-above; otherwise drive
  bounded Player revision cycle.
- **Player-Coach revision loop**: bounded retry policy, latency budgets,
  fallback behaviour, two-session concurrency isolation.
- **Quote-fidelity integration**: cross-feature contract with
  FEAT-PH1-004 (source-typed quote verifier), including verifier-failure
  path through the rubric.
- **Session-end summary generation**: topics, AOs, turn count, duration,
  narrative, misconceptions; F3 Graphiti episode write at session end.
- **Three Graphiti flush points**:
  - **F1** — Coach AsyncSubAgent owns its own per-observation
    misconception writes (DDR-002).
  - **F2** — Tutor handler dispatches planner topic-confidence updates.
  - **F3** — Tutor handler dispatches session-end episode write.
  - All three go through a single shared Graphiti write helper
    (TASK-GSM-004 producer).
- **`session.completed` event ordering** per DDR-003: emits on
  active→ended state transition BEFORE the F3 write task is scheduled.
  No `session.persisted` follow-up event. Sessions with zero tutor turns
  must NOT emit `session.completed` (I-T6 invariant).
- **Fire-and-forget write semantics** per CC-13 / ADR-ARCH-019: every
  Graphiti write site logs failures structurally; failures never raise
  into the caller-facing handler.
- **Security surface**: prompt-injection resistance, adversarial corpus,
  sanitisation across @security and @invariant scenarios.

## Out of Scope

- Player prompt content (Player implementation owned elsewhere).
- Planner ranking logic (FEAT-PH1-002 — covered by TASK-REV-DA72).
- Retrieval / quote-verifier internals (FEAT-PH1-004).
- Gamification consumers of `session.completed` events.
- Graphiti client wrapper internals (TASK-GSM-003).
- Async write helper internals (TASK-GSM-004 — this feature consumes
  its `drain()` surface).

## Acceptance Criteria

- [ ] Technical-options analysis covers all dimensions equally
      (architectural fit, scenario completeness, boundary coverage,
      negative-case robustness, assumption quality, integration contracts).
- [ ] Recommended approach surfaces concrete trade-offs and weights
      speed / quality / maintainability / cost equally; bias is called
      out explicitly when it occurs.
- [ ] ASSUM-006 receives a recommended resolution with reasoning
      (Coach reasoning > 200 word cap behaviour).
- [ ] ASSUM-011 receives a recommended resolution with reasoning
      (5-second shutdown grace window for in-flight Graphiti writes).
- [ ] DDR-002, DDR-003, CC-13, D5, and the two-provider invariant are
      each addressed in the analysis (constraint coverage check).
- [ ] Five proposed task slices (TASK-DTL-001..005) receive a partial
      sequencing assessment — obvious dependency risks flagged
      (e.g., loop wiring TASK-DTL-003 cannot start before Coach factory
      TASK-DTL-001).
- [ ] BDD-to-task mapping is preserved as input for /feature-plan
      Step 11 (`bdd-linker`); no manual rewriting of `@task:` tags
      during this review.
- [ ] Decision checkpoint presented: [A]ccept / [R]evise / [I]mplement
      / [C]ancel.

## Pre-Implementation Sign-offs Required

Before /feature-plan [I]mplement can produce the structured FEAT YAML
and the subtask folder, the following must be confirmed by the user:

- ASSUM-006 — Coach reasoning > 200 word cap behaviour (recommended
  resolution to be proposed by this review).
- ASSUM-011 — 5-second shutdown grace for in-flight Graphiti writes
  (recommended resolution to be proposed by this review; cross-checked
  against TASK-GSM-004 `drain()` surface).
- Cross-feature dependency: TASK-GSM-004 (shared Graphiti write helper)
  must produce a `drain()` surface compatible with the F1/F2/F3 dispatch
  pattern this feature relies on. Flag if the produced surface diverges.

## Test Requirements

N/A — this is a review/decision task. Quality gates verify the analysis
artefact, not executable code.

## Implementation Notes

**Constraint anchors** (must be honoured, not re-derived):

- **DDR-002** — Coach AsyncSubAgent owns F1 misconception writes;
  Tutor handler owns F2 and F3 dispatches; both go through shared
  helper.
- **DDR-003** — `session.completed` emit BEFORE F3 task scheduled;
  zero-turn sessions skip emit (I-T6).
- **CC-13 / ADR-ARCH-019** — Fire-and-forget; failures log only,
  never raise into handler.
- **D5** — Coach `tools=[]`, no filesystem backend, never returns
  text to learner; structural enforcement at factory construction.
- **Two-provider invariant** — Coach and Player on different providers;
  enforced at Coach factory construction.

**Cross-feature dependencies to flag**:

- TASK-GSM-002 (episode types) — `SessionCompletedEpisode` shape used
  by F3.
- TASK-GSM-004 (async write helper) — the `drain()` surface ASSUM-011
  refers to.
- FEAT-PH1-004 (quote verifier) — `@quote-fidelity` rubric criterion
  integrates with the source-typed quote verifier.

**Latency context** for trade-off framing:

- Graphiti latency spike: 78.98s observed.
- Tutor turn p95 budget: 30s.
- Implication: F1/F2/F3 dispatches MUST be off the critical path
  (this is the architectural reason for fire-and-forget).

## Test Execution Log

[Populated by /task-review]
