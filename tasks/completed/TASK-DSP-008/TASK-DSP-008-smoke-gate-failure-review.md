---
id: TASK-DSP-008
title: Review smoke-gate failure for FEAT-PH1-002 autobuild run
task_type: review
feature_id: FEAT-PH1-002
status: completed
created: '2026-04-29T22:30:00Z'
updated: '2026-04-29T23:30:00Z'
completed: '2026-04-29T23:30:00Z'
completed_location: tasks/completed/TASK-DSP-008/
organized_files:
- TASK-DSP-008-smoke-gate-failure-review.md
priority: high
complexity: 4
decision_required: true
tags:
- review
- smoke-gate
- autobuild
- feat-ph1-002
- post-mortem
dependencies: []
estimated_minutes: 45
actual_minutes: 30
test_results:
  status: not_applicable
  coverage: null
  last_run: null
  note: Review task — no code under test. Reproduction commands evidenced in report.
review_results:
  mode: post-mortem
  depth: standard
  findings_count: 6
  recommendations_count: 4
  decision: pass-with-followup
  followup_tasks:
  - id: TASK-DSP-009
    repo: study-tutor
    path: tasks/completed/TASK-DSP-009/TASK-DSP-009.md
    status: completed
    scope: R2 — author smoke tests + register pytest markers for FEAT-PH1-002
    note: Gate now exits 0; implementer chose the `feat_ph1_002` (underscore) marker variant.
  - id: TASK-FIX-SG05
    repo: guardkit
    path: tasks/backlog/TASK-FIX-SG05-smoke-gates-distinguish-exit-5-from-exit-1.md
    status: backlog
    scope: R3 — smoke_gates module: distinguish pytest exit 5 (no tests collected) from exit 1 (tests failed)
  report_path: .claude/reviews/TASK-DSP-008-review-report.md
  completed_at: '2026-04-29T23:30:00Z'
---

# Task: Review smoke-gate failure for FEAT-PH1-002 autobuild run

## Context

The autobuild run for FEAT-PH1-002 (Deterministic Session Planner) reported
`FEATURE RESULT: FAILED` even though **all six implementation tasks
(TASK-DSP-001 through TASK-DSP-006) completed with `decision: approved` and
all five waves passed**. The failure surfaced exclusively at the smoke gate
that runs after Wave 5.

Evidence: [autobuild-FEAT-PH1-002-history.md](../../../docs/history/autobuild-FEAT-PH1-002-history.md)

Key log lines:
- [autobuild-FEAT-PH1-002-history.md:1591](../../../docs/history/autobuild-FEAT-PH1-002-history.md#L1591) — Smoke gate command:
  `pytest -m "feat-ph1-002 and smoke" -x --no-cov` (cwd=worktree, timeout=60s, expected_exit=0)
- [autobuild-FEAT-PH1-002-history.md:1592-1594](../../../docs/history/autobuild-FEAT-PH1-002-history.md#L1592-L1594) —
  `Smoke gate failed after wave 5 (exit=5, expected=0)`. Worktree preserved.
- [autobuild-FEAT-PH1-002-history.md:1611-1635](../../../docs/history/autobuild-FEAT-PH1-002-history.md#L1611-L1635) —
  Wave Summary shows 5/5 waves PASS, Task Details shows 6/6 tasks SUCCESS / approved.

Smoke-gate config (source of truth): [FEAT-PH1-002.yaml](../../../.guardkit/features/FEAT-PH1-002.yaml)
```yaml
smoke_gates:
  after_wave: [5, 6]
  command: pytest -m "feat-ph1-002 and smoke" -x --no-cov
  expected_exit: 0
  timeout: 60
```

## Initial Hypothesis (to validate)

**Pytest exit code 5 = "no tests were collected"**, not a test failure. A
spot-check of the preserved worktree at
`.guardkit/worktrees/FEAT-PH1-002/` shows:
- No `@pytest.mark.smoke` or `pytestmark` declarations under `tests/`.
- No `[tool.pytest.ini_options].markers` block in `pyproject.toml` registering
  either `smoke` or `feat-ph1-002`.

If confirmed, the smoke gate failed because the marker expression
`feat-ph1-002 and smoke` matches zero tests — i.e., the gate was configured
but never wired to any actual smoke test. The implementation tasks were not
asked to author smoke-tagged tests, so this is a **gate-setup gap, not a
regression in the planner code**.

## Goals

Produce a written analysis that answers, with evidence:

1. **What is the literal cause of the smoke-gate failure?**
   Confirm the exit-code-5 / no-tests-collected hypothesis (or refute it with
   the alternative cause).
2. **Whose responsibility was it to author the smoke tests?**
   Was a smoke test expected from any of TASK-DSP-001..006, or was the
   smoke-gate config added without a corresponding "author smoke tests" task?
   Cross-reference each task's acceptance criteria.
3. **Should FEAT-PH1-002 be considered actually-passing or actually-failing?**
   Given all six tasks were approved and the only red signal is a misconfigured
   gate, what is the correct disposition for the feature?
4. **What is the minimum fix?** Options to weigh:
   - (a) Add smoke tests + register markers, then re-run the gate.
   - (b) Remove/relax the smoke-gate config until smoke tests exist.
   - (c) Treat this as a gap-discovery task and create a follow-up
     `TASK-DSP-009` to author the smoke tests.
5. **Process improvement.** Should the autobuild orchestrator distinguish
   "exit 5 / no tests collected" from "exit 1 / tests failed" when reporting
   smoke-gate failures? File a note for the GuardKit smoke_gates module.

## Acceptance Criteria

- [ ] Cause confirmed (or refuted) by running the exact smoke command in the
      worktree and capturing the full output.
- [ ] Marker registration and `@pytest.mark` usage audited across the worktree
      `tests/` tree; findings documented.
- [ ] Each of TASK-DSP-001..006 reviewed for any smoke-test acceptance
      criterion; gaps listed.
- [ ] Disposition recommendation written: pass / fail / pass-with-followup,
      with justification.
- [ ] Concrete next-action chosen from {a, b, c} above and a follow-up task
      stub drafted if applicable.
- [ ] Note logged for the orchestrator about distinguishing exit-5 from
      exit-1 in smoke-gate reporting.

## Inputs / Artefacts

- History log: [docs/history/autobuild-FEAT-PH1-002-history.md](../../../docs/history/autobuild-FEAT-PH1-002-history.md)
- Feature spec: [.guardkit/features/FEAT-PH1-002.yaml](../../../.guardkit/features/FEAT-PH1-002.yaml)
- Review summary: [.guardkit/autobuild/FEAT-PH1-002/review-summary.md](../../../.guardkit/autobuild/FEAT-PH1-002/review-summary.md)
- Preserved worktree: `.guardkit/worktrees/FEAT-PH1-002/`
- Implementation tasks: [TASK-DSP-001](TASK-DSP-001-session-plan-and-baseline.md) through
  [TASK-DSP-006](TASK-DSP-006-mcp-adapter-and-degradation.md)

## Out of Scope

- Re-implementing planner logic. The 6 approved tasks are not under review here.
- Fixing the gate inside this task — this is a *review*. Implementation goes
  into a follow-up task.

## Suggested Workflow

This is a review/analysis task, not implementation. Use:

```bash
/task-review TASK-DSP-008 --mode=post-mortem
```

After the review checkpoint, the chosen path becomes a separate
implementation task (likely `TASK-DSP-009-author-feat-ph1-002-smoke-tests`).
