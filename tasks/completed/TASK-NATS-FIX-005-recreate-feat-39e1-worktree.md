---
id: TASK-NATS-FIX-005
title: Delete and recreate FEAT-39E1 worktree on a current-main base so it picks up the .gitignore fix
status: completed
completed_at: 2026-05-10T19:15:00Z
task_type: implementation
implementation_mode: direct
parent_review: TASK-REV-F30A
feature_id: FEAT-39E1
feature_slug: feat-39e1-recovery
wave: 2
priority: high
created: 2026-05-10T18:00:00Z
updated: 2026-05-10T18:00:00Z
complexity: 1
tags: [autobuild-recovery, worktree-hygiene, vcs]
related_tasks:
  - TASK-NATS-PH1-004
  - TASK-REV-F30A
  - TASK-NATS-FIX-004
dependencies:
  - TASK-NATS-FIX-004
blocks:
  - TASK-NATS-FIX-006
inputs:
  worktree: .guardkit/worktrees/FEAT-39E1
  feature_yaml: .guardkit/features/FEAT-39E1.yaml
  review_report: .claude/reviews/TASK-REV-F30A-review-report.md
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Delete and recreate FEAT-39E1 worktree on a current-main base

## Description

The FEAT-39E1 worktree branch `autobuild/FEAT-39E1` (HEAD `0a6f919`) is forked from commit `246f73b`, which predates the `.gitignore` fix in commit `12df1a9`. `git merge-base --is-ancestor 12df1a9 246f73b` returns false. As a result, the worktree's `.gitignore` (lines 280-300) does not include the `src/study_tutor/adapters/` re-include and silently strips Player-authored files in the `adapters/` package — which caused the run-3 PH1-004 max_turns failure.

This task removes the polluted worktree and lets the next autobuild create a fresh one from current `main` (which has `12df1a9`).

## Procedure

1. Verify nothing on the worktree is uncommitted-and-needed:
   ```bash
   git -C .guardkit/worktrees/FEAT-39E1 status --porcelain
   ```
   Should be empty (the rollback already wiped any in-flight state). If anything important is here, salvage it before continuing.
2. Remove the worktree from git's worktree registry:
   ```bash
   git worktree remove .guardkit/worktrees/FEAT-39E1 --force
   ```
3. Delete the autobuild branch:
   ```bash
   git branch -D autobuild/FEAT-39E1
   ```
4. Verify the project root `.gitignore` has the fix in place (sanity check):
   ```bash
   grep -n '!src/study_tutor/adapters/' .gitignore
   ```
   Should print at least line 312 (`!src/study_tutor/adapters/`) and line 313 (`!src/study_tutor/adapters/*.py`).
5. The next `guardkit autobuild feature FEAT-39E1 --resume` will recreate the worktree from current `main`, picking up `12df1a9` and inheriting the correct re-include rules.

## Acceptance Criteria

- [ ] `.guardkit/worktrees/FEAT-39E1/` no longer exists.
- [ ] `git worktree list` does not include FEAT-39E1.
- [ ] `git branch -a | grep autobuild/FEAT-39E1` returns empty.
- [ ] Project root `.gitignore` contains `!src/study_tutor/adapters/*.py` and `!tests/unit/adapters/*.py`.
- [ ] Verification: after step 5 of TASK-NATS-FIX-006 begins, the new worktree's `.gitignore` lines 280-330 contain the `!src/study_tutor/adapters/` re-include (compare with `diff` against project root if needed).

## Implementation Notes

- **Mode = direct** because this is 4 shell commands. No reasoning needed mid-task. Could be done as a single bash one-liner: `git worktree remove .guardkit/worktrees/FEAT-39E1 --force && git branch -D autobuild/FEAT-39E1 && grep -q '!src/study_tutor/adapters/' .gitignore && echo OK`.
- `--force` on `git worktree remove` is safe here because the worktree's content is post-rollback (`git reset --hard 0a6f9192` left the working tree at the rollback target with no uncommitted changes — confirmed by `git -C ... status` returning clean).
- This task does NOT touch the autobuild metadata at `.guardkit/autobuild/FEAT-39E1/events.jsonl` or `review-summary.md` in the project root (outside the worktree). Those are run history; they should stay.
- After this task, `tasks/backlog/feat-39e1-recovery/` (this folder) survives because it lives in the project root, not the worktree.
