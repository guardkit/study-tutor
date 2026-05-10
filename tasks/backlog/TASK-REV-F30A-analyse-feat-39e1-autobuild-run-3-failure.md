---
id: TASK-REV-F30A
title: Analyse FEAT-39E1 autobuild run-3 failure (PH1-004 max_turns_exceeded, checkpoint-audit honesty collapse)
task_type: review
decision_required: true
created: 2026-05-10T17:30:00Z
updated: 2026-05-10T17:30:00Z
priority: high
tags: [autobuild, post-mortem, nats-fleet, command-router, checkpoint-audit, honesty-score, max-turns, task-work-mode]
complexity: 6
feature: FEAT-39E1
related_tasks:
  - TASK-NATS-PH1-004
  - TASK-NATS-PH1-001
  - TASK-REV-CC40
  - TASK-REV-D509
inputs:
  failure_log: docs/history/autobuild-FEAT-39E1-fail-run-3.md
  prior_reviews:
    - tasks/backlog/TASK-REV-CC40-analyse-feat-39e1-autobuild-failure.md
    - tasks/backlog/TASK-REV-D509-analyse-feat-39e1-autobuild-run-2-failure.md
  feature_yaml: .guardkit/features/FEAT-39E1.yaml
  worktree: .guardkit/worktrees/FEAT-39E1
  events_log: .guardkit/autobuild/FEAT-39E1/events.jsonl
  review_summary: .guardkit/autobuild/FEAT-39E1/review-summary.md
  failed_task_dir: .guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-004
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: decision
  depth: standard
  decision: implement
  findings_count: 6
  recommendations_count: 6
  unblocks_feat_39e1: true
  root_cause: gitignore_drop_in_stale_worktree_base
  report_path: .claude/reviews/TASK-REV-F30A-review-report.md
  completed_at: 2026-05-10T18:00:00Z
  graphiti_episode: adr_review-report-task-rev-f30a
  child_tasks:
    - TASK-NATS-FIX-004
    - TASK-NATS-FIX-005
    - TASK-NATS-FIX-006
    - TASK-FIX-IGNR  # in guardkit repo
    - TASK-FIX-RBSS  # in guardkit repo
    - TASK-FIX-HEAB  # in guardkit repo
status: review_complete
---

# Task: Analyse FEAT-39E1 autobuild run-3 failure (PH1-004 max_turns_exceeded, checkpoint-audit honesty collapse)

## Description

After the run-2 fixes (TASK-REV-D509: dependency-resolver remediation), FEAT-39E1 was re-run with `--resume` on **2026-05-10 15:23 UTC** and **failed again**, this time with a new signature: [TASK-NATS-PH1-004](../../.guardkit/worktrees/FEAT-39E1/tasks/design_approved/TASK-NATS-PH1-004-command-router.md) (CommandRouter implementation) hit **max_turns_exceeded after all 5 turns**, with Coach repeatedly emitting the same feedback:

```
Checkpoint claim audit failed: Player claimed a file that 'git add -A' would not...
```

The Player's honesty score collapsed across the run — **turn 1: 0.88 (1 discrepancy) → turn 5: 0.07 (200 discrepancies)**, average 0.22 over the last 3 turns (threshold 0.8). Scope ballooned from 6 created files in turn 1 to 12 created + 199 modified by turn 4. Context-pollution detection fired and a rollback was issued to turn 1 (commit `0a6f9192`), but the rollback came **after** max_turns was already exceeded, so it had no recovery effect.

This is a **review/analysis task** to:

1. Determine the root cause of the recurring "Checkpoint claim audit failed: Player claimed a file that `git add -A` would not..." rejection — orchestrator/auditor bug, Player misbehaviour, or worktree-state corruption (likely related to [.gitignore](../../.gitignore) churn fixed in commit 12df1a9 / [docs/history/autobuild-FEAT-39E1-fail-run-3.md:25](../../docs/history/autobuild-FEAT-39E1-fail-run-3.md#L25) "Previous worktree not found, creating new one").
2. Explain why the **same audit symptom** that PH1-001 saw (turns 1 & 2) self-recovered on turn 3 after the scheduled perspective reset, but PH1-004 — which also hit a turn-3 perspective reset — kept regressing instead of recovering.
3. Decide remediation: orchestrator fix (upstream guardkit), task spec change (PH1-004 frontmatter `mode: task-work` may be too heavyweight — direct mode worked for PH1-001), worktree hygiene fix, or a manual implementation handoff.
4. Produce a concrete action plan + child tasks so FEAT-39E1 can finish.

Full failure log: [docs/history/autobuild-FEAT-39E1-fail-run-3.md](../../docs/history/autobuild-FEAT-39E1-fail-run-3.md)
Prior reviews: [TASK-REV-CC40](TASK-REV-CC40-analyse-feat-39e1-autobuild-failure.md) (run-1, PH1-006 wave block), [TASK-REV-D509](TASK-REV-D509-analyse-feat-39e1-autobuild-run-2-failure.md) (run-2, dependency resolver crash).

## Observed Failure Signature

### Run-3 wave outcomes

| Wave | Tasks                                                                       | Result                       | Notes                                                                                          |
|------|-----------------------------------------------------------------------------|------------------------------|------------------------------------------------------------------------------------------------|
| 1    | PH1-001 (resume — worktree was missing, recreated)                          | ✓ approved (3 turns)          | Same checkpoint-audit feedback turns 1–2; recovered turn 3 after perspective reset            |
| 2    | PH1-002, PH1-003, PH1-007                                                   | ✓ PH1-002 approved (1 turn)   | PH1-003 / PH1-007 skipped (already_completed)                                                  |
| 3    | PH1-006                                                                     | ✓ skipped                     | already_completed                                                                              |
| 4    | **PH1-004**                                                                 | ✗ **FAILED — max_turns**      | All 5 turns produced same Coach feedback; honesty 0.88 → 0.07; rollback fired but too late     |
| —    | Wave 5+ never reached (`stop_on_failure=True`)                              | —                            | 13 tasks remain unstarted                                                                      |

Final orchestrator outcome: 5/18 tasks completed, 1 failed, 12 unreached. Duration 55m 57s.

### PH1-004 turn-by-turn signal

| Turn | Player result                                  | Coach decision     | Honesty | Files created/modified |
|------|-------------------------------------------------|--------------------|---------|------------------------|
| 1    | success — 1 tests passing                      | feedback (audit)   | 0.88    | 6 / 6                  |
| 2    | success — 1 tests passing                      | feedback (audit)   | —       | 3 / 17                 |
| 3    | success — 0 tests passing (perspective reset)  | feedback (audit)   | —       | 2 / 20                 |
| 4    | success — 1 tests passing (39 SDK turns)       | feedback (audit)   | —       | 12 / 199               |
| 5    | success — 0 tests passing (16 SDK turns)       | feedback (audit)   | 0.07 (200 discrepancies) | 2 / 205     |

Three-turn rolling average honesty at end-of-run: **0.22** (threshold 0.8). Coach short-circuited gate evaluation each turn ("Honesty verification produced N critical issue(s); short-circuiting gate evaluation."). BDD oracle reported `passed=0 failed=0 pending=8` for the linked feature file ([features/nats-fleet-integration/nats-fleet-integration.feature](../../features/nats-fleet-integration/nats-fleet-integration.feature)) — none of the 8 scenarios executed even when implementation was claimed complete.

### Run-1 vs run-2 vs run-3 — failure-mode evolution

| Run | Blocker                                                    | Type                         | Resolution applied                              |
|-----|-------------------------------------------------------------|------------------------------|--------------------------------------------------|
| 1   | PH1-006 (serve nats CLI subcommand) wave block             | Player implementation gap    | TASK-NATS-FIX-001/002 (TASK-REV-CC40)           |
| 2   | DependencyError: PH2-001 needs deferred PH1-010            | Orchestrator semantics gap   | Soft-dep fix + dependency-resolver patch        |
| 3   | PH1-004 max_turns_exceeded; checkpoint-audit honesty crash | **Adversarial-loop failure** | **This review**                                  |

The failure has *moved upstream* through the pipeline — from a single-task implementation gap (run-1) → orchestrator state machine (run-2) → adversarial Player/Coach loop (run-3). That trajectory is itself a finding worth investigating.

## Investigation Hooks

Concrete artefacts to inspect during the review:

- `.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-004/coach_turn_{1..5}.json` — exact discrepancy lists; identify which file paths the auditor flagged each turn and whether the same file is being re-claimed.
- `.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-004/player_turn_{1..5}.json` — Player's claimed file lists vs git diff baselines.
- `.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-004/task_work_results.json` — final state of completion_promises / requirements_addressed.
- `.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-004/turn_state_turn_{1..5}.json` — perspective-reset turnover.
- `.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-004/checkpoints.json` — what the rollback considered "last passing" (it claimed turn 1 / commit `0a6f9192`, but that commit's checkpoint was tagged `from_prior_run`).
- Compare against PH1-001's matching files (turn 1 & 2 had the same audit-fail pattern but turn 3 succeeded) to see what changed at the perspective-reset boundary.
- Check whether the "Previous worktree not found, creating new one" notice on resume left stale `.guardkit/autobuild/TASK-NATS-PH1-004/checkpoints.json` referencing files that no longer exist on disk.
- Cross-reference the recent `.gitignore` fix ([commit 12df1a9](../../docs/history/autobuild-FEAT-39E1-fail-run-3.md): "fix(gitignore): re-include src/study_tutor/adapters/ + tests/unit/adapters/") — the audit error message *exactly* describes the symptom of a Player Write-ing files that `.gitignore` then silently drops from `git add -A`.
- PH1-004 frontmatter declares `implementation_mode: task-work` (full task-work delegation, 160 SDK max-turns, complexity 6 ×1.6 multiplier). PH1-001 and PH1-002 use `direct` mode and approved cleanly. Question: is task-work mode at complexity 6 over-budget for the agent, allowing it to drift into "ghost-file" territory (Player reports paths the orchestrator-induced ghost-path filter then strips)? Note line: `Filtered 1 orchestrator-induced ghost path(s) for TASK-NATS-PH1-004: ['tasks/backlog/TASK-NATS-PH1-004-command-router.md']`.

## Decision Points (for /task-review checkpoint)

1. **Audit-failure root cause**: gitignore-induced Player/git-add divergence vs. orchestrator checkpoint-claim-audit bug vs. genuine Player dishonesty (over-claiming file edits)?
2. **Mode override**: should PH1-004 be downgraded from `task-work` to `direct` mode (matching PH1-001/002)? What are we losing by doing so?
3. **Recovery path**: rollback PH1-004 to its turn-1 checkpoint manually and re-run with adjusted config, or write/import the CommandRouter implementation by hand and mark the task `completed` so the autobuild can resume on Wave 5+?
4. **Upstream guardkit fix**: should the Coach checkpoint auditor distinguish between "Player wrote a gitignored file" (warning, not failure) and "Player invented a file" (failure)? File a TASK-FIX-XXX in the guardkit repo.
5. **Honesty-collapse safeguard**: should the orchestrator abort earlier (e.g. at honesty < 0.3 sustained for 2 turns) instead of burning all 5 turns?

## Acceptance Criteria

- [ ] Root-cause hypothesis stated with evidence (specific log lines, JSON artefact diffs, or git-state observations).
- [ ] Compare/contrast with PH1-001's recovery — explain why the same symptom resolved there and not here.
- [ ] Contributing causes enumerated (mode choice, gitignore state, perspective-reset timing, scope creep).
- [ ] Concrete remediation plan: list of follow-up tasks with effort estimates, target repo (study-tutor vs guardkit), and which one unblocks the FEAT-39E1 re-run.
- [ ] Decision recorded for each of the 5 decision points above.
- [ ] Demo-readiness statement (FEAT-39E1's Phase 3 is the operator GB10 demo — confirm whether the demo is still on track or needs replanning).
- [ ] Output written to `.claude/reviews/TASK-REV-F30A-review-report.md` per /task-review convention.

## Implementation Notes

This is a **review task** — execute via `/task-review TASK-REV-F30A` (not `/task-work`). Suggested mode: `--mode=decision` `--depth=standard`, matching the prior reviews CC40 and D509 in the same series. Key thing the review must verify directly (not infer): which exact paths the Coach checkpoint auditor flagged in each `coach_turn_N.json`, and whether those paths are present in the worktree, present-but-gitignored, or genuinely fabricated.

## Test Execution Log

(populated by /task-review)
