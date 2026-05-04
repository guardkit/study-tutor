---
id: TASK-FIX-AB7A-005
title: Resume FEAT-70A4 autobuild from wave 3 in fixed configuration
task_type: feature
parent_review: TASK-REV-AB7A
feature_id: FEAT-FIX-AB7A
wave: 4
implementation_mode: manual
complexity: 1
estimated_minutes: 25
dependencies:
  - TASK-FIX-AB7A-001
  - TASK-FIX-AB7A-001b
  - TASK-FIX-AB7A-002
  - TASK-FIX-AB7A-003
  - TASK-FIX-AB7A-004
status: backlog
priority: high
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
tags: [autobuild, resume, FEAT-70A4, operator-run]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Resume FEAT-70A4 autobuild from wave 3 in fixed configuration

## Description

Operator-run final step of FEAT-FIX-AB7A. After tasks 001–004 are complete and the pre-resume verification gates have all passed, run `guardkit autobuild feature FEAT-70A4 --resume` to continue the original autobuild from wave 3 onward (PRV-004, PRV-005, PRV-006, PRV-007).

The worktree at `.guardkit/worktrees/FEAT-70A4` is preserved on branch `autobuild/FEAT-70A4` with five `[guardkit-checkpoint]` commits from the original run. `--resume` reuses this worktree, re-bootstraps the venv idempotently (per `feature_orchestrator.py:892-913`), and picks up the wave plan from `FEAT-70A4.yaml` — which now reflects the wave-3 serialisation from TASK-FIX-AB7A-004.

## Scope

- Run `guardkit autobuild feature FEAT-70A4 --resume` from the repo root.
- Monitor for: smoke-gate exit code, `parallel_contention` recurrence, Coach SDK reader fatal errors (informational only — non-blocking).
- Capture the run transcript to `docs/history/autobuild-FEAT-70A4-resume-history.md` (mirroring the failed-run transcript pattern at `docs/history/autobuild-FEAT-70A4-failed-history.md`).

## Out of Scope

- Code changes (none — all production code in worktree was already approved or is to be written by Player turns inside the autobuild).
- Restarting from wave 1 (the conditional-approval safety net was tested by TASK-FIX-AB7A-002 and 003; PRV-002/003 work is preserved).

## Acceptance Criteria

- [ ] **All pre-resume gates exit 0** (re-verify the 5 commands from `IMPLEMENTATION-GUIDE.md §"Pre-Resume Verification"` immediately before invoking the resume).
- [ ] `guardkit autobuild feature FEAT-70A4 --resume` exits with feature `status: completed`.
- [ ] All four remaining tasks reach `approved`: TASK-PRV-004, TASK-PRV-005, TASK-PRV-006, TASK-PRV-007.
- [ ] Smoke gate after wave 3 exits 0 (validates TASK-FIX-AB7A-001's pin).
- [ ] Smoke gate after wave 4 exits 0.
- [ ] No `parallel_contention` conditional approval fires for any of waves 3–6 (validates TASK-FIX-AB7A-004's serialisation). If any fires, capture context and re-open the diagnostic.
- [ ] Run transcript saved to `docs/history/autobuild-FEAT-70A4-resume-history.md`.
- [ ] Worktree merged into `main` (or held for manual review per operator preference).

## Test Requirements

- The autobuild's own quality gates (Player phases + Coach validation + smoke gates) ARE the verification.
- No additional tests in this task.

## Implementation Notes

**Command:**
```bash
cd /home/richardwoollcott/Projects/appmilla_github/study-tutor
guardkit autobuild feature FEAT-70A4 --resume --verbose 2>&1 \
  | tee docs/history/autobuild-FEAT-70A4-resume-history.md
```

**Expected wall-clock:** ~25 minutes for waves 3–6 (PRV-004 ~15m, PRV-005 ~20m, PRV-006 ~10m, PRV-007 ~6m, sequential). Originals had been allocated 75+113+50+33 = 271 min budget but the actual cadence was much faster on waves 1 and 2.

**If anything regresses (especially smoke-gate exit≠0 or another `parallel_contention`):**
1. Capture the relevant transcript section.
2. Halt — do not retry blindly.
3. Open a follow-up review task referencing this one. The diagnostic flow (TASK-REV-AB7A → FEAT-FIX-AB7A → TASK-FIX-AB7A-005) is the template.

**Why `manual` not `task-work`:** `/task-work` is for code-implementation flows; this task is a single operator-run command with no code change. Mark `status: completed` after operator verifies acceptance criteria.

## Test Execution Log

[Populated by operator after run completes]
