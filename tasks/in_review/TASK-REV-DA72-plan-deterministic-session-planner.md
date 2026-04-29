---
id: TASK-REV-DA72
title: "Plan: Deterministic Session Planner"
task_type: review
status: review_complete
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
priority: high
tags: [feature-plan, planner, phase-1, deterministic, mcp]
complexity: 7
context_files:
  - features/deterministic-session-planner/deterministic-session-planner_summary.md
  - features/deterministic-session-planner/deterministic-session-planner.feature
  - features/deterministic-session-planner/deterministic-session-planner_assumptions.yaml
clarification:
  context_a:
    timestamp: 2026-04-29T00:00:00Z
    decisions:
      review_focus: all
      tradeoff_priority: quality
      assumption_flags: [ASSUM-006, ASSUM-007, ASSUM-008]
      phase2_stubs: contract_only
      graceful_degradation: spot_check
review_results:
  mode: decision
  depth: standard
  recommended_option: "Option A — Sequential short-circuit pipeline of typed Rule objects (Strategy pattern)"
  options_count: 4
  subtask_count: 7
  estimated_effort_hours: "18-22 (wave-parallel ceiling ~14h elapsed)"
  confidence: medium-high
  pre_implementation_signoffs:
    - ASSUM-006 (2s handler budget)
    - ASSUM-007 (5s read timeout)
    - "ASSUM-008 (cross-feature: SessionCompletedEpisode.topics_covered field on TASK-GSM-002)"
  report_path: .guardkit/reviews/TASK-REV-DA72-review-report.md
  completed_at: 2026-04-29T00:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Plan: Deterministic Session Planner

## Description

Plan FEAT-PH1-002 — the Phase 1 deterministic session planner for study-tutor.

This is a `/feature-plan` review task. It precedes implementation and produces:

1. A technical-options analysis covering ranking-rule design, `SessionPlan`
   shape, MCP-adapter integration with `tutor_start_session`, the rule-6
   fallback, Phase 2 stub contracts (rules 2 and 5), and graceful
   degradation when FEAT-PH1-001 query helpers cannot return state.
2. A recommended approach plus a subtask breakdown ready for [I]mplement.
3. Explicit risk callouts for ASSUM-006, ASSUM-007, and ASSUM-008.

## Scope

- `SessionPlan` shape (selected topic, fallback flag, focus AOs,
  suggested duration, deterministic ranking trace).
- Active ranking rules: 1 (learner override), 3 (weakest stale topic),
  4 (topic with recent unrevisited misconception).
- Rule-6 fallback (random selection from the developing band, seeded for
  determinism).
- Phase 2 stubs: rule 2 (active-quest) and rule 5 (achievement-near-unlock)
  must exist with the rule interface but never select a topic.
- MCP integration: `tutor_start_session` calls the planner and returns a
  `SessionPlan`-derived response.
- Read path: FEAT-PH1-001 query helpers; baseline-plan degradation when
  helpers cannot return state.

## Acceptance Criteria

- [ ] Technical-options analysis covers all four review focus areas
      (technical, architecture, integration, edge-cases) at standard depth.
- [ ] Trade-offs surface correctness wins over simpler-but-loose
      alternatives where the two conflict.
- [ ] ASSUM-006 (2-second handler budget) and ASSUM-007 (5-second read
      timeout) are flagged with explicit pre-implementation sign-off
      asks.
- [ ] ASSUM-008 ("unrevisited" misconception definition) is flagged with
      an explicit dependency on the FEAT-PH1-001 `session_completed`
      payload shape.
- [ ] Phase 2 stubs (rules 2 and 5) are reviewed at contract level only —
      the plan confirms they exist, never select, and expose the correct
      interface; internal logic is deferred.
- [ ] Graceful-degradation path is spot-checked against negative-case
      scenarios; gaps are surfaced if the existing 6 negative scenarios
      do not exercise it.
- [ ] Recommended approach includes a deterministic tie-break order
      (ASSUM-004) and seeded randomness for rule-6.
- [ ] Subtask breakdown is ready for [I]mplement, with task_type fields
      set per the feature-plan rules and waves identified for parallel
      execution.

## Review Scope (from Context A)

| Category            | Decision                                                   |
|---------------------|------------------------------------------------------------|
| Review focus        | All areas (technical + architecture + integration + edge) |
| Trade-off priority  | Quality / correctness                                      |
| Assumptions to flag | ASSUM-006, ASSUM-007, ASSUM-008                            |
| Phase 2 stubs       | Contract verification only                                 |
| Graceful degradation| Spot-check via negative cases                              |

## Open Risks (medium-confidence assumptions to validate)

- **ASSUM-006** — 2-second `tutor_start_session` handler budget is parity
  with ADR-ARCH-019 / SR-08 but not formally specified for the start
  path. Verify before fixing the budget in code.
- **ASSUM-007** — 5-second student-model read timeout reuses the
  specialist-agent precedent. Confirm precedent applies here.
- **ASSUM-008** — "unrevisited" misconception definition depends on the
  FEAT-PH1-001 `session_completed` episode payload shape. Resolve with
  the FEAT-PH1-001 owner before implementation.

## Implementation Notes

[Populated by /task-review during decision-mode analysis]

## Test Execution Log

[Populated by /task-work or /feature-plan implementation phase]
