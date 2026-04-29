---
id: TASK-DSP-007
title: BDD scenario execution, gap tests, and IMPLEMENTATION-GUIDE update
task_type: testing
parent_review: TASK-REV-DA72
feature_id: FEAT-PH1-002
wave: 5
implementation_mode: task-work
complexity: 5
dependencies: [TASK-DSP-006]
estimated_minutes: 90
priority: high
tags: [phase-1, planner, bdd, pytest-bdd, scenarios, guide]
---

# Task: BDD scenario execution, gap tests, and IMPLEMENTATION-GUIDE update

## Description

Execute the full Phase 1 scenario suite for FEAT-PH1-002 against the
implemented planner, add the two coverage-gap tests identified in
TASK-REV-DA72 §5, and finalise the IMPLEMENTATION-GUIDE.md with the
mandatory diagrams and the resolved-assumption sign-off block.

## Scope

- Wire `features/deterministic-session-planner/deterministic-session-planner.feature`
  into `pytest-bdd`. Step definitions live in
  `tests/features/deterministic_session_planner/steps/`.
- All 29 scenarios (4 smoke, 7 key-example, 6 boundary, 6 negative,
  11 edge-case) pass against the implemented planner.
- The bdd-linker has tagged each scenario with `@task:TASK-DSP-XXX`
  via Step 11 of `/feature-plan` so the R2 BDD oracle can run during
  per-task `/task-work` Phase 4 verification.

- **Gap tests** added in
  `tests/planner/test_planner_gap_coverage.py`:

  - `test_all_bands_empty_returns_baseline` — rules 1/3/4 all return
    `None` AND developing band is empty → `rule_selected="baseline"`,
    `fallback_used="baseline"`, no exception (TASK-REV-DA72 §5 Gap 1).
  - `test_post_write_read_consistency_does_not_block` — with a
    fire-and-forget session-completion write task in-flight, a new
    `tutor_start_session` returns within 2.1s and does not block on
    the dispatched write (TASK-REV-DA72 §5 Gap 2).

- Update `tasks/backlog/deterministic-session-planner/IMPLEMENTATION-GUIDE.md`:
  - Confirm the three mandatory diagrams render correctly in GitHub
    markdown preview (Data Flow, Integration Contract, Task Dependency
    Graph).
  - Add a "Resolved Assumptions" section reproducing the ASSUM-006,
    ASSUM-007, ASSUM-008 sign-off wording from
    `features/deterministic-session-planner/deterministic-session-planner_assumptions.yaml`.
  - Add a "Smoke Gates" entry documenting that the four `@smoke`
    scenarios are the feature-level gate between waves (R3
    smoke-gates oracle).

## Acceptance Criteria

- [ ] `pytest --tags=feat-ph1-002` exits 0 with all 29 scenarios green.
- [ ] Smoke scenarios (`@smoke` tag, 4 scenarios) complete in under
      30 seconds total wall-clock.
- [ ] `test_all_bands_empty_returns_baseline` passes with
      `fallback_used="baseline"`, `rule_selected="baseline"`,
      `learner_state_available=True`.
- [ ] `test_post_write_read_consistency_does_not_block` returns within
      2.1 seconds with a write task in-flight (verified via
      `time.perf_counter`).
- [ ] `@determinism` scenario: identical inputs on two successive
      calls return byte-identical `SessionPlan` instances (asserted
      via `model_dump_json()` equality).
- [ ] `@phase-2-stub` scenario: source grep for `# TODO(phase-2)` in
      `Rule2ActiveQuestStub` and `Rule5AchievementNearUnlockStub`
      class bodies returns exactly one match each.
- [ ] `IMPLEMENTATION-GUIDE.md` contains the three mandatory diagrams
      from TASK-REV-DA72 §7 (Data Flow, Integration Contract, Task
      Dependency Graph).
- [ ] `IMPLEMENTATION-GUIDE.md` "Resolved Assumptions" section
      reproduces the verbatim sign-off wordings for ASSUM-006/007/008.
- [ ] All scenarios in `deterministic-session-planner.feature` carry
      a `@task:TASK-DSP-XXX` tag (R2 BDD oracle activation).
- [ ] All modified files pass project-configured lint/format checks
      with zero errors.

## Implementation Notes

- pytest-bdd step definitions are organised by Group from the feature
  file — one step file per group keeps imports manageable:
  `steps/group_a_key_examples.py`, `steps/group_b_boundary.py`,
  `steps/group_c_negative.py`, `steps/group_d_edge_cases.py`,
  `steps/group_e_edge_expansion.py`.
- The `@latency` scenario uses `monkeypatch.setenv` to set
  `STUDENT_MODEL_READ_TIMEOUT_SEC=0.1` so the inner timeout fires
  without a real 5-second wait. Outer 2s guard remains untouched.
- Smoke scenarios (`@smoke`): rule 1 override, rule 3 weakest stale,
  rule 4 misconception, MCP integration. These are the four-scenario
  feature-level smoke gate (R3) the `/feature-plan` smoke-gates nudge
  recommended in Step 10.7.
- After this task lands, run `/task-complete TASK-DSP-007` to roll up
  to feature-level completion for FEAT-PH1-002.
