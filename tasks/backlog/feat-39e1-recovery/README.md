# feat-39e1-recovery

Recovery cluster from [TASK-REV-F30A](../TASK-REV-F30A-analyse-feat-39e1-autobuild-run-3-failure.md). Six tasks across two repos to unblock the FEAT-39E1 GB10 demo and add upstream defence-in-depth so the same failure mode can't recur invisibly.

## Problem statement

FEAT-39E1 autobuild run-3 (2026-05-10) failed at PH1-004 (CommandRouter) with `max_turns_exceeded`. The Coach honesty score collapsed `0.86 → 0.66 → 0.47 → 0.11 → 0.07` across five turns and a context-pollution rollback fired twice but failed to recover. Surface symptom: every Coach validation logged "Checkpoint claim audit failed: Player claimed a file that 'git add -A' would not...".

## Root cause

The FEAT-39E1 worktree branch (`autobuild/FEAT-39E1`, base commit `246f73b`) was forked **before** the gitignore fix in commit `12df1a9` ("fix(gitignore): re-include src/study_tutor/adapters/ + tests/unit/adapters/ (FEAT-39E1 silent file drop)"). The worktree's `.gitignore` therefore lacked the `!src/study_tutor/adapters/` re-include while keeping the unanchored `adapters/` ML-artefact rule on line 284. Every Player Write to `src/study_tutor/adapters/command_router.py` and `tests/unit/adapters/test_command_router.py` succeeded locally but `git status --porcelain --untracked-files=all` silently filtered them out — and the Coach's claim audit (which is the literal mechanism for catching this exact scenario, see `coach_verification.py:362-521`) flagged them as critical-severity discrepancies.

Two amplifiers turned a single configuration drift into a five-turn loss-of-recoverability:
- `rollback_on_pollution` restored the worktree filesystem to `0a6f9192` (a 2-day-old `from_prior_run` checkpoint) but did not reset the Player's SDK session, so the next turn re-emitted authoring claims into a wiped worktree.
- `git reset --hard` wiped the run's per-turn coach JSONs (coach_turn_2..5.json), destroying the audit trail of the very turns that triggered the rollback.

## Solution approach

**Three in-repo recovery tasks** (sequential, demo-blocking):
1. Hand-author `command_router.py` + tests on `main` from the prior-run's preserved AC evidence — bypass the autobuild for this one task because the worktree it would run in is broken.
2. Delete the polluted worktree and the autobuild branch — let the next autobuild create a fresh one from current `main`.
3. Resume autobuild from Wave 5+ on the recreated worktree to land the remaining 13 tasks.

**Three upstream guardkit tasks** (parallel, defence-in-depth):
4. **TASK-FIX-IGNR**: Coach claim audit should classify gitignored-but-present paths as `should_fix` warnings (with the matched ignore rule reported), not `critical` fabrications. The audit's docstring already explains the scenario; this task tightens the classification.
5. **TASK-FIX-RBSS**: `rollback_on_pollution` should reset the Player SDK session AND archive per-turn audit JSONs to a `_rollback_archive/` directory before `git reset --hard`.
6. **TASK-FIX-HEAB**: honesty early-abort exits the loop when 3-turn rolling average drops below threshold (default 0.3), with a diagnostic message naming the most-flagged path and recommending `git check-ignore -v`.

After all three upstream tasks ship, a future stale-worktree-gitignore situation surfaces as a single warning on turn 1 with the matching `.gitignore` rule named — instead of a 5-turn SDK burn followed by a forensic post-mortem.

## Subtask summary

| ID                                                                                          | Repo         | Wave / parallel | Mode      | Complexity | Effort           |
|---------------------------------------------------------------------------------------------|--------------|-----------------|-----------|------------|------------------|
| [TASK-NATS-FIX-004](TASK-NATS-FIX-004-manual-implement-command-router.md)                   | study-tutor  | Wave 1          | manual    | 4          | ~1 hour          |
| [TASK-NATS-FIX-005](TASK-NATS-FIX-005-recreate-feat-39e1-worktree.md)                       | study-tutor  | Wave 2          | direct    | 1          | ~5 minutes       |
| [TASK-NATS-FIX-006](TASK-NATS-FIX-006-resume-autobuild-from-wave-5.md)                      | study-tutor  | Wave 3          | manual    | 2          | ~3-6h unattended |
| [TASK-FIX-IGNR](../../../../guardkit/tasks/backlog/TASK-FIX-IGNR-classify-gitignored-vs-fabricated-in-coach-claim-audit.md) | guardkit     | parallel        | task-work | 5          | ~0.5 day         |
| [TASK-FIX-RBSS](../../../../guardkit/tasks/backlog/TASK-FIX-RBSS-rollback-should-reset-sdk-session-and-preserve-audit-trail.md) | guardkit     | parallel        | task-work | 6          | ~0.5 day         |
| [TASK-FIX-HEAB](../../../../guardkit/tasks/backlog/TASK-FIX-HEAB-honesty-rolling-average-early-abort.md) | guardkit     | parallel        | task-work | 3          | ~1-2 hours       |

## Demo readiness

ON TRACK. Critical path is ~half-day focused work. No predictable run-4 failure mode visible from current evidence. Upstream guardkit improvements are a separate workstream and do not block the demo.

## See also

- Review report (full forensic analysis + Mermaid diagrams + source-line citations): [.claude/reviews/TASK-REV-F30A-review-report.md](../../../.claude/reviews/TASK-REV-F30A-review-report.md)
- Implementation guide (waves + execution strategy + failure-mode watch list): [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md)
- Prior reviews in the FEAT-39E1 series:
  - [TASK-REV-CC40](../TASK-REV-CC40-analyse-feat-39e1-autobuild-failure.md) — run-1 (BDD oracle scope)
  - [TASK-REV-D509](../TASK-REV-D509-analyse-feat-39e1-autobuild-run-2-failure.md) — run-2 (deferred-dependency crash)
- Failure log: [docs/history/autobuild-FEAT-39E1-fail-run-3.md](../../../docs/history/autobuild-FEAT-39E1-fail-run-3.md)
- The `.gitignore` fix that the worktree branch never picked up: commit `12df1a9`
