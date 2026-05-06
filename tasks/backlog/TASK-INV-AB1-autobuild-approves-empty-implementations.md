---
id: TASK-INV-AB1
title: "Investigate autobuild approving zero-implementation turns (FEAT-6CC5 false-positive approvals)"
task_type: investigation
parent_review: null
feature_id: null
implementation_mode: investigation
complexity: 6
estimated_minutes: 120
status: backlog
priority: critical
created: 2026-05-06T00:00:00+00:00
updated: 2026-05-06T00:00:00+00:00
dependencies: []
tags:
  - autobuild
  - guardkit
  - quality-gate
  - false-positive-approval
  - regression
related:
  - TASK-LCA-001
  - TASK-LCA-002
  - TASK-LCA-003
context_files:
  - .guardkit/archive/FEAT-6CC5/feature_state.yaml
  - .guardkit/archive/FEAT-6CC5/review-summary.md
  - .guardkit/archive/FEAT-6CC5/events.jsonl
  - tasks/completed/TASK-LCA-001-llm-player-adapter.md
  - tasks/completed/TASK-LCA-002-llm-coach-adapter.md
  - tasks/completed/TASK-LCA-003-session-state-dataclass.md
---

# Task: Investigate autobuild approving zero-implementation turns

## Problem statement

During FEAT-6CC5 (MCP LLM Player and Coach Adapters), the GuardKit autobuild
Player↔Coach loop **approved 5 of 5 tasks (100% pass rate, coach decision
`approved`)** despite the fact that **3 of those tasks produced zero
production-code files**. The merged feature branch contained none of the
following modules that the approved tasks were specified to create:

- `src/study_tutor/tutoring/adapters/__init__.py`
- `src/study_tutor/tutoring/adapters/session_state.py` (TASK-LCA-003)
- `src/study_tutor/tutoring/adapters/llm_player_adapter.py` (TASK-LCA-001)
- `src/study_tutor/tutoring/adapters/llm_coach_adapter.py` (TASK-LCA-002)

The defect was only caught after the feature was merged to `main`, when
`pytest --collect-only` failed with
`ModuleNotFoundError: No module named 'study_tutor.tutoring.adapters'`.

This is a **silent quality-gate failure**: a coach approval is supposed to
guarantee that the acceptance criteria in the task .md were met. In this run
the criteria explicitly required new files (e.g., TASK-LCA-003 lists a
`@dataclass(frozen=True)` at a specific path as the first acceptance
criterion), yet the coach approved despite no files being created.

## Evidence

The most diagnostic artefact is in
`tasks/completed/TASK-LCA-003-session-state-dataclass.md` —
`autobuild_state.turns[*].player_summary` for **every turn** reads:

```
"Implementation via task-work delegation. Files planned: 0, Files actual: 0"
```

At turn 3, the coach decision is `approve` with `feedback: null` —
i.e., a clean approval — even though `Files actual: 0`. No mechanism in the
loop appears to have checked whether the player actually produced any of the
files declared in the task's acceptance criteria.

Turn 2 of the same task contains a long coach-feedback entry about
"source-file contention with peer task(s) in this parallel wave (wave_size=4)"
— a wave-isolation issue that may have suppressed retries or caused the
player to return a "skipped due to contention" report that the coach
mis-classified as success.

`.guardkit/archive/FEAT-6CC5/review-summary.md` reports:

| Metric | Value |
|---|---|
| Task success rate | 100% |
| First-turn approvals | 0/5 |
| Multi-turn tasks | 5 |
| Avg SDK turns/invocation | 24.6 |

i.e., every task took multiple coach-feedback rounds before final approval —
the loop *did* produce iterative feedback, but the terminating approval still
fired on a no-implementation state for at least 3 tasks.

## Investigation goals

1. **Root-cause the false-positive approval**: under what condition did the
   coach (or the orchestrator's approval pipeline) accept a player turn that
   produced zero files when the task spec required new files at specific
   paths?
2. **Identify whether the wave-2 file-contention path is implicated**:
   TASK-LCA-001/002/003/004 ran in the same wave-1 group and the contention
   feedback at turn 2 of TASK-LCA-003 suggests an isolation-snapshot failure
   mode. Determine whether the wave conflict caused an empty player report
   that the coach then rubber-stamped.
3. **Identify any deterministic check that should have blocked approval**:
   in particular, a "Files actual: 0 vs acceptance-criteria expected new
   files at paths X, Y, Z" cross-check before the coach decision is finalised.
4. **Determine blast radius**: scan recent feature archives
   (`.guardkit/archive/`) and prior autobuild runs for other completions where
   `Files actual: 0` appears in approved turns.

## Acceptance criteria

- [ ] Written investigation report at `docs/reviews/REVIEW-TASK-INV-AB1-autobuild-empty-approval.md` covering:
  - Root-cause hypothesis backed by the player/coach turn JSON in `.guardkit/archive/FEAT-6CC5/`
    *(plus, if recoverable from `git fsck --unreachable`, the per-task
    `coach_turn_*.json` and `player_turn_*.json` blobs from the deleted
    `autobuild/FEAT-6CC5` branch tree — see "Reference data" below)*
  - Whether the wave-isolation contention path is implicated
  - Concrete reproduction steps (minimum failing example)
  - Affected scope: how many other prior autobuild completions are likely
    false positives
- [ ] A proposed fix to the autobuild loop that would have blocked the
      FEAT-6CC5 approvals — written up as a separate `/task-create` task
      (do not implement under this investigation)
- [ ] A regression check (or written specification for one) that asserts:
      "if a task's acceptance criteria declare new files at specific paths,
      the coach cannot return `decision: approve` while `git diff` shows
      none of those paths created"
- [ ] Decision recorded on whether other recent autobuild-completed features
      (FEAT-1773, FEAT-FD32 closeouts) need to be re-audited for the same
      class of false-positive

## Reference data

**Archived FEAT-6CC5 state (committed in this repo):**
- `.guardkit/archive/FEAT-6CC5/feature_state.yaml` — final per-task results
- `.guardkit/archive/FEAT-6CC5/review-summary.md` — pass-rate and turn counts
- `.guardkit/archive/FEAT-6CC5/events.jsonl` — orchestrator event log
- `tasks/completed/TASK-LCA-{001,002,003,004,005}-*.md` — embedded
  `autobuild_state.turns[*]` for each task

**Deleted autobuild artefacts** — the per-task `player_turn_N.json` /
`coach_turn_N.json` blobs were removed from `.guardkit/autobuild/TASK-LCA-*/`
in commit `bb19903`. They are still reachable in git history via
the merge commit `d472565` (`git show d472565:.guardkit/autobuild/...`)
and the deleted branch tip `23b1a5a` (also reachable; see `git fsck`).
Read these for the full coach reasoning that preceded each approval.

## Out of scope

- Implementing the missing TASK-LCA-001/002/003 modules (handled by re-running
  `/feature-build` against those three tasks; restored to backlog separately)
- Changes to the autobuild loop itself (proposed fixes go to a follow-up task)
- Re-auditing every prior autobuild completion (this task delivers the
  decision on whether that audit is warranted, not the audit itself)

## Notes

This investigation is critical because the fundamental value proposition of
the autobuild Player↔Coach loop is that a coach approval functions as a
quality gate. A 60% false-positive rate within a single feature
(3 of 5 tasks here) materially undermines that guarantee, and any new
autobuild run completed before the bug is understood and fixed must be
treated as suspect.
