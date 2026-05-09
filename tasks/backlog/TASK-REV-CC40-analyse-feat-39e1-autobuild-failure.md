---
id: TASK-REV-CC40
title: Analyse and fix FEAT-39E1 autobuild failure (TASK-NATS-PH1-006)
status: backlog
task_type: review
decision_required: true
created: 2026-05-08T00:00:00Z
updated: 2026-05-08T00:00:00Z
priority: high
tags: [autobuild, post-mortem, nats-fleet, parallel-contention, coach-validator, timeout-budget]
complexity: 6
feature: FEAT-39E1
related_tasks:
  - TASK-NATS-PH1-006
inputs:
  failure_log: docs/history/autobuild-FEAT-39E1-fail-run-1.md
  review_summary: .guardkit/autobuild/FEAT-39E1/review-summary.md
  worktree: .guardkit/worktrees/FEAT-39E1
  feature_yaml: .guardkit/features/FEAT-39E1.yaml
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: decision
  depth: standard
  decision: implement
  findings_count: 7
  recommendations_count: 6
  report_path: .claude/reviews/TASK-REV-CC40-review-report.md
  completed_at: 2026-05-08T00:00:00Z
  primary_root_cause: "BDD oracle runs entire feature file instead of @task:TASK-NATS-PH1-006 scope; pytest-bdd v8 emits unbound scenarios as FAILED, not pending — making the gate unsatisfiable for any single-task feature-file cohort"
  contributing_causes:
    - classifier mis-labels BDD oracle failure as parallel_contention
    - conditional_approval rule requires docker_available even for non-infra failure classes
    - SDK→subprocess test fallback adds ~30s/turn (cosmetic)
---

# Task: Analyse and fix FEAT-39E1 autobuild failure (TASK-NATS-PH1-006)

## Description

The autobuild run for **FEAT-39E1 (study-tutor NATS Fleet Integration)** failed in Wave 2.
Of 18 planned tasks across 8 waves, only 4/18 completed before `--stop-on-failure` halted execution
when **TASK-NATS-PH1-006 (Add serve-nats CLI subcommand)** exhausted its timeout budget after 3 turns.

This is a review/analysis task to:

1. Diagnose the *root cause(s)* of the TASK-NATS-PH1-006 failure (it is not just one cause).
2. Decide on remediation: change the wave/parallelism plan, change the task spec, fix orchestrator
   behaviour, or some combination.
3. Produce a concrete action plan (and child implementation task(s)) so a re-run can succeed.

Full failure log: [docs/history/autobuild-FEAT-39E1-fail-run-1.md](docs/history/autobuild-FEAT-39E1-fail-run-1.md)
Review summary:   [.guardkit/autobuild/FEAT-39E1/review-summary.md](.guardkit/autobuild/FEAT-39E1/review-summary.md)

## Observed Failure Signature

From the log:

| Turn | Player | Coach decision | Notable lines |
|------|--------|----------------|---------------|
| 1    | success — 7 created, 31 modified, 1 test | rejected (`bdd_results.scenarios_failed > 0`) | BDD oracle: 1 scenario failed during pytest-bdd execution |
| 2    | success — 6 created, 39 modified, 1 test | feedback (`parallel_contention`, high confidence) | SDK coach test exec failed → fell back to subprocess; subprocess tests failed in 1.6s |
| 3    | success — 2 created, 46 modified, 0 tests | feedback (`parallel_contention`, high confidence) | Same SDK fallback; same subprocess failure |
| 4    | —      | — | `Timeout budget exhausted ... remaining=511.2s < min=600s` |

Final state: `decision=timeout_budget_exhausted`, status `FAILED`, worktree preserved at
`.guardkit/worktrees/FEAT-39E1`.

Wave 2 ran 4 tasks in parallel (002, 003, 006, 007) all writing into the **same shared worktree**.
The orchestrator already detected `parallel_contention` with `wave_size=4` and high confidence,
but `conditional_approval` did not trigger (`docker_available=False`) and the loop kept retrying.

There is also a recurring infrastructure signal: every Coach turn the SDK test runner died with
`Command failed with exit code 1` and fell back to subprocess. This adds latency on every turn
and contributed to the time-budget exhaustion.

## Acceptance Criteria

- [x] **Root-cause analysis written** covering at minimum:
  - [x] BDD oracle failure on turn 1 — feature file path was a red herring; oracle scope is
        the whole feature file (1 of 30+ scenarios owned by 006). pytest-bdd v8 emits unbound
        downstream scenarios as FAILED, not pending — gate is unsatisfiable. Implementation
        itself is sound (all hard gates green).
  - [x] Parallel contention on turns 2–3 — classifier false-positives. Real source-file scopes
        do not conflict (see Appendix B in report). `parallel_contention` keeps firing because
        underlying failure (RC-1) is deterministic, not transient.
  - [x] Coach SDK test execution failing every turn — env mismatch
        (`sys.executable=/usr/local/bin/python3` vs framework pytest); subprocess fallback
        works in 1.6s. ~30s/turn cosmetic tax, not causal.
  - [x] Time budget math — `max_turns=7` is adequate; turn 1 took ~25 min only because
        coach specialists chained (667s) + SDK player (670s). Under RC-1 every retry made no
        progress, so budget exhaustion is symptom not cause.
- [x] **Decision recorded** for each of:
  - [x] Wave plan: **keep** `[002, 003, 006, 007]` parallel; optional defensive split is
        TASK-NATS-FIX-002.
  - [x] Conditional-approval rule: **expand** to drop `docker_available` predicate for
        `parallel_contention/high + all_gates_passed + requires_infra=[]`. Upstream GuardKit
        change (TASK-FIX-CC-COND).
  - [x] BDD oracle wiring: per-task focused feature file (TASK-NATS-FIX-001) is the in-repo
        workaround; scope-by-tag and pending-vs-failed counting is the upstream fix
        (TASK-FIX-CC-BDD).
  - [x] SDK→subprocess fallback: accept subprocess as primary; investigate SDK regression
        later (not blocking).
- [x] **Remediation plan produced** — see `.claude/reviews/TASK-REV-CC40-review-report.md`
      §Remediation Plan. Two in-repo tasks (FIX-001 blocking, FIX-002 optional defensive),
      two upstream GuardKit tasks (CC-BDD, CC-COND, both non-blocking).
- [x] **Follow-up implementation task(s) created** (filed 2026-05-08):
  - **In-repo (study-tutor):**
    - [TASK-NATS-FIX-001](nats-fleet-integration/TASK-NATS-FIX-001-focused-bdd-feature-for-task-006.md) — focused per-task BDD feature file for TASK-NATS-PH1-006. **Load-bearing — blocks FEAT-39E1 re-run.**
    - [TASK-NATS-FIX-002](nats-fleet-integration/TASK-NATS-FIX-002-split-task-006-into-own-wave.md) — split TASK-006 into its own wave 2b in `.guardkit/features/FEAT-39E1.yaml`. **Optional defensive companion.**
  - **Upstream GuardKit:**
    - [TASK-FIX-CC-BDD](/Users/richardwoollcott/Projects/appmilla_github/guardkit/tasks/backlog/TASK-FIX-CC-BDD-coach-independent-tests-task-tag-scope.md) — coach `independent_tests` must scope BDD step-defs runs by `@task:` tag (delegate to existing `bdd_runner`, count unbound steps as `pending`).
    - [TASK-FIX-CC-COND](/Users/richardwoollcott/Projects/appmilla_github/guardkit/tasks/backlog/TASK-FIX-CC-COND-source-file-contention-false-positives.md) — `_detect_source_file_contention` must use player-authored edits (new `task_work_results.files_authored` field), not worktree-wide git diff (otherwise peer changes are false-attributed to current task).
- [x] **Re-run readiness statement**: after TASK-NATS-FIX-001 lands, run
      `guardkit autobuild feature FEAT-39E1 --resume`. Wave 1 (TASK-001) and 4/4 Wave 2 peers
      (002, 003, 007) preserved from checkpoints; turn 1 of 006 should approve immediately
      (implementation already at checkpoint `0823395`; only the BDD oracle scope changes).
      Expected: feature build resumes into Wave 3 (TASK-004) and onward against the full
      remaining budget. Demo deadline 2026-05-11 remains achievable.

## Out of Scope

- Implementing the fixes themselves — those go into child tasks created by this review.
- Re-running the autobuild — that happens after child fixes land.
- Re-architecting NATS fleet integration beyond what's required to unblock the run.

## Investigation Notes (to be filled by /task-review)

### Evidence pointers
- Failure log lines 588–612: turn 1 player + initial BDD failure (`not found: features/nats-fleet-integration/nats-fleet-integration.feature`).
- Lines 663–675: turn 1 coach rejection on `bdd_results.scenarios_failed > 0`.
- Lines 793–820: turn 2 coach independent tests fail in 1.6s; classifier flags `parallel_contention`.
- Lines 900–930: turn 3 same pattern; checkpoint created; coach feedback again.
- Line 931: `Timeout budget exhausted for TASK-NATS-PH1-006 at turn 4: remaining=511.2s < min=600s`.
- Lines 802–804 / 914–916: `conditional_approval check: failure_class=parallel_contention,
  confidence=high, requires_infra=[], docker_available=False, all_gates_passed=True, wave_size=4`
  — gates passed but conditional approval did not fire.

### Hypotheses to test
1. **Wave-2 file contention is real**: 006 (serve-nats CLI) likely edits `study_tutor/cli/*` and
   `study_tutor/__init__.py`, which 002 (manifest factory) or 003 (roles registry) may also touch
   when wiring. Verify by diffing what each task wrote in the worktree.
2. **BDD feature file path drift**: turn 1 logged `not found: features/nats-fleet-integration/
   nats-fleet-integration.feature` — task may not be creating the feature file at the path the
   BDD runner expects, or pytest-bdd is being invoked from the wrong cwd.
3. **Coach SDK test runner regression**: every coach turn, the SDK path fails with exit code 1 and
   falls back. This pattern is consistent — looks like a deterministic env mismatch
   (`sys.executable=/usr/local/bin/python3` vs the worktree venv at `.venv/bin/python`).
4. **Conditional-approval logic is too strict**: with `parallel_contention/high` + all gates
   passed, the run *should* have moved on to other tasks instead of burning turns.

## Test Requirements

- [ ] N/A for the review itself; child implementation tasks must include their own tests.

## Implementation Notes

**Review completed 2026-05-08.** Full report:
[.claude/reviews/TASK-REV-CC40-review-report.md](../../.claude/reviews/TASK-REV-CC40-review-report.md).

### Root cause (verified)

**RC-1 (primary, load-bearing):** the BDD oracle runs the entire `nats-fleet-integration.feature`
file rather than scoping to scenarios tagged `@task:TASK-NATS-PH1-006`. The feature file
contains scenarios for 9 tasks (PH1-002, -004, -005, -006, -008, -009, PH2-001, PH2-003,
PH3-002, PH3-004, PH3-005); only one scenario (line 248–256, "SIGTERM during an in-flight
tutor turn") belongs to TASK-006. pytest-bdd v8 emits unbound-step scenarios as FAILED test
functions (not pending), so 30+ scenarios meant for downstream tasks always FAIL — making
Coach's gate `bdd_results.scenarios_failed > 0` unsatisfiable for *every* re-run.

The autogenerated step-defs file (`features/nats-fleet-integration/test_nats_fleet_integration.py`)
explicitly documents the intended behaviour: "scenarios … tagged for a downstream task …
will land with that task; their steps remain intentionally unbound here. They surface as
`scenarios_pending` and are tolerated by the Coach gate (`scenarios_failed == 0`)." Design
and runtime disagree.

**RC-2 — classifier mis-attribution.** The `parallel_contention/high` label fired because
the orchestrator's worktree-wide git diff shows TASK-006 as having "modified" files owned
by peer tasks 003 and 007 (it didn't author them — that's just shared-worktree noise). Even
after peers completed, the classifier kept firing because the underlying RC-1 failure is
deterministic, not transient.

**RC-3 — conditional_approval too narrow.** With `failure_class=parallel_contention,
confidence=high, all_gates_passed=true, requires_infra=[]`, the only blocker was
`docker_available=False`. Docker is irrelevant to this failure class.

**RC-4 — turn budget arithmetic.** Turn 1 burned ~25 min (670s player + 567s coach
specialists). With `max_turns=7`, by turn 4 only 511s remained vs `min=600s` → exhausted.
Not a budget defect; just the consequence of RC-1 making each retry burn ~13–17 min for
zero progress.

**RC-5 — SDK→subprocess fallback (cosmetic).** Coach SDK test execution fails with exit
code 1 every turn (sys.executable=`/usr/local/bin/python3` vs framework pytest at
`/Library/Frameworks/Python.framework/Versions/3.14/bin/pytest`); subprocess fallback runs
in 1.6s. Adds ~30s/turn, not causal.

**Implementation quality (TASK-006 itself):** sound. `coach_turn_2.quality_gates`:
tests=pass, coverage=pass, arch=pass, audit=pass, all_gates_passed=true, honesty_score=1.0.

### Decisions

| Decision | Outcome |
|----------|---------|
| Wave plan: keep `[002, 003, 006, 007]` parallel? | **Keep** (no real source-file conflict). Optional defensive split: move 006 to its own wave. |
| Conditional-approval: drop docker predicate for `parallel_contention/high + all_gates_passed`? | **Yes**, file as upstream GuardKit improvement (TASK-FIX-CC-COND). |
| BDD oracle wiring: filter by `@task:` tag? | **Yes**. Workaround for FEAT-39E1: per-task focused feature file (TASK-NATS-FIX-001). Upstream GuardKit fix (TASK-FIX-CC-BDD) is the durable answer. |
| SDK→subprocess fallback: investigate or accept? | **Accept** for now; switch coach default to subprocess. Investigate later. |

### Re-run readiness

Apply **TASK-NATS-FIX-001** (one focused feature file `features/nats-fleet-integration/by-task/TASK-NATS-PH1-006.feature` containing only the SIGTERM scenario, plus updated `## Coach validation` block in the task spec), then:

```bash
guardkit autobuild feature FEAT-39E1 --resume
```

`--resume` (not `--fresh`) preserves Wave 1 (TASK-001 ✓) and 4/4 of Wave 2's peer tasks
(002, 003, 007 all ✓). Expected: turn 1 of TASK-006 approves on first pass — implementation
is already in place from turn 3 checkpoint `0823395`; the only delta is which feature file
the BDD oracle scopes to. Wave 3 (TASK-004) and onward then runs as planned.

### Follow-up child tasks

- **TASK-NATS-FIX-001** (in-repo, blocking re-run): focused per-task feature file for
  TASK-NATS-PH1-006 + updated coach validation command.
- **TASK-NATS-FIX-002** (in-repo, optional defensive): wave plan split — move 006 to its own
  wave 2b.
- **TASK-FIX-CC-BDD** (upstream GuardKit, not blocking): scope `bdd_runner` by `@task:` tag;
  count unbound scenarios as `pending` not `failed`.
- **TASK-FIX-CC-COND** (upstream GuardKit, not blocking): drop `docker_available` predicate
  from `conditional_approval` for non-infra failure classes.

## Decision Checkpoint

After review, record one of:
- **[A]ccept** – findings approved, proceed to implementation tasks.
- **[I]mplement** – findings approved AND create implementation tasks immediately.
- **[R]evise** – more analysis required (e.g. inspect worktree diffs, instrument orchestrator).
- **[C]ancel** – discard review (not recommended; failure is real).

## Test Execution Log

[Auto-populated by `/task-review` / child `/task-work` runs]
