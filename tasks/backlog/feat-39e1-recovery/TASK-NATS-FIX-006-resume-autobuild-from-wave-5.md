---
id: TASK-NATS-FIX-006
title: Resume FEAT-39E1 autobuild from Wave 5 against the recreated worktree to land remaining 13 tasks
status: backlog
task_type: implementation
implementation_mode: manual
parent_review: TASK-REV-F30A
feature_id: FEAT-39E1
feature_slug: feat-39e1-recovery
wave: 3
priority: high
created: 2026-05-10T18:00:00Z
updated: 2026-05-10T18:00:00Z
complexity: 2
tags: [autobuild-recovery, autobuild-operation, demo-blocker]
related_tasks:
  - TASK-NATS-PH1-005
  - TASK-NATS-PH1-008
  - TASK-NATS-PH1-009
  - TASK-NATS-PH1-010
  - TASK-NATS-PH2-001
  - TASK-NATS-PH2-002
  - TASK-NATS-PH2-003
  - TASK-NATS-PH3-001
  - TASK-NATS-PH3-002
  - TASK-NATS-PH3-003
  - TASK-NATS-PH3-004
  - TASK-NATS-PH3-005
  - TASK-REV-F30A
dependencies:
  - TASK-NATS-FIX-004
  - TASK-NATS-FIX-005
blocks: []
inputs:
  feature_yaml: .guardkit/features/FEAT-39E1.yaml
  review_report: .claude/reviews/TASK-REV-F30A-review-report.md
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Resume FEAT-39E1 autobuild from Wave 5 against the recreated worktree

## Description

After TASK-NATS-FIX-004 lands `command_router.py`+tests on `main` and flips PH1-004 to `completed` in `FEAT-39E1.yaml`, and after TASK-NATS-FIX-005 deletes the polluted worktree, this task is the operator action to re-run the autobuild on the remaining 13 tasks (wave 5 onwards) and observe the run.

## Procedure

```bash
cd ~/Projects/appmilla_github/study-tutor
GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-39E1 --verbose --resume \
    2>&1 | tee docs/history/autobuild-FEAT-39E1-run-4.md
```

Expected timeline:
- Wave 1 (PH1-001), Wave 2 (PH1-002 / 003 / 007), Wave 3 (PH1-006), Wave 4 (PH1-004) — all skipped as `already_completed`.
- Wave 5 (PH1-005 NATS adapter full-lifecycle) — first real work in the new worktree. Confirm the new worktree's `.gitignore` has the `!src/study_tutor/adapters/` re-include before any Player work hits paths in `src/study_tutor/adapters/`.
- Waves 6-7 (PH1-008 smoke / PH1-009 live discovery / PH1-010 demo-gate as `operator_handoff` deferred — same pattern as run-2; see TASK-REV-D509).
- Waves 8-9 (PH2 + PH3 — readiness-gating, runbooks, dockerfile, compose, GB10 e2e smoke).

Total expected wall-clock: ~3-6 hours unattended; PH1-005 is the longest single task (complexity 7, NATS adapter full lifecycle including reconnect/health-check/teardown).

## Watch-outs

- **Verify gitignore on the new worktree before letting Wave 5 run far**: after the first `Created shared worktree` log line, run `grep -c '!src/study_tutor/adapters/' .guardkit/worktrees/FEAT-39E1/.gitignore` in another shell — must return `>= 2`. If it returns `0`, abort the run (Ctrl-C) and recheck TASK-NATS-FIX-005.
- **PH1-010 (operator_handoff) will be deferred** — that's by design (it IS the demo). The dependency-resolver fix from TASK-REV-D509 / TASK-FIX-DEFD must be active in the guardkit version being used, otherwise PH2-001 / PH2-003 will crash on the deferred predecessor (run-2's failure mode).
- **Honesty audit on Wave 5+**: if a Wave 5+ task hits a "Checkpoint claim audit failed: Player claimed a file…" message, IMMEDIATELY pause and run `git -C .guardkit/worktrees/FEAT-39E1 check-ignore -v <claimed_file>` on the flagged path. If it matches a `.gitignore` rule, that's a same-shape-different-path recurrence and we need another targeted re-include. The new worktree should NOT exhibit this for `adapters/`, but other `adapters-like` packages might surface.

## Acceptance Criteria

- [ ] All 13 remaining tasks in FEAT-39E1.yaml flip from `not_started` to `completed` (or `deferred` for PH1-010).
- [ ] No `max_turns_exceeded` outcomes; no honesty < 0.5 turns.
- [ ] `.guardkit/autobuild/FEAT-39E1/review-summary.md` shows status `PASSED` or `PASSED_WITH_DEFERRED_OPERATOR_HANDOFF`.
- [ ] Phase 3 demo artefacts present: Dockerfile, compose, build script, runbook, GB10 e2e smoke output. Operator can complete the GB10 demo using `tasks/completed/TASK-NATS-PH3-005-gb10-e2e-smoke.md` instructions.
- [ ] `docs/history/autobuild-FEAT-39E1-run-4.md` archived for future review.

## Implementation Notes

- **Mode = manual** because this is an operator-driven autobuild run, not an autonomous task. The operator should be at the keyboard for the first 30 minutes (Wave 5 setup verification) and can let the rest run unattended.
- After completion, run `/feature-complete FEAT-39E1` to merge the autobuild branch and archive results per the GuardKit feature-complete spec.
- Keep TASK-FIX-IGNR / TASK-FIX-RBSS / TASK-FIX-HEAB (the guardkit defence-in-depth tasks) running in parallel in the guardkit repo — they don't block this task.
