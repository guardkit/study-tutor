# Review Report: TASK-REV-CC40 — FEAT-39E1 autobuild failure post-mortem

**Mode:** decision (post-mortem + remediation planning)
**Depth:** standard
**Generated:** 2026-05-08
**Subject:** FEAT-39E1 (study-tutor NATS Fleet Integration), Wave 2 / TASK-NATS-PH1-006
**Outcome of run:** `timeout_budget_exhausted`, 4/18 tasks completed

## Executive Summary

Wave 2's TASK-NATS-PH1-006 (Add `serve-nats` CLI subcommand) was not actually broken.
It was killed by a **mis-scoped BDD oracle** combined with a **mis-classified contention
signal** that tied up the turn budget on retries that could never have succeeded.

- **The BDD oracle ran the *whole* feature file** instead of the one scenario the task owns
  (`@task:TASK-NATS-PH1-006`). pytest-bdd v8 fails (rather than skips) scenarios whose step
  definitions are not bound, so 30+ scenarios meant for downstream tasks (PH1-002, -004, -005,
  -008, -009, PH2, PH3) all reported `FAILED`, and Coach's gate `bdd_results.scenarios_failed > 0`
  rejected turn 1 deterministically. The step-defs file even *documents* this design
  ("they surface as scenarios_pending and are tolerated by the Coach gate") — the design
  intent and runtime behaviour disagree.
- **The classifier flagged this as `parallel_contention/high`** because peer tasks (003, 007)
  had legitimately edited overlapping files in the shared worktree. That label is false: 006
  doesn't own those files, and once 003 and 007 finished the wave was effectively serialised,
  but the oracle still ran the full feature file and still got the same failure.
- **`conditional_approval` did not fire** even with `parallel_contention=high, all_gates_passed=true`
  because the rule additionally requires `docker_available=true` — which is irrelevant to this
  failure class. So the orchestrator kept burning turns instead of moving on.
- **Turn 1 alone consumed ~25 min** (670s player + 567s coach specialists). With `max_turns=7`
  and a global budget that left only 511s before turn 4, the run was over after three retries.
- **Coach SDK test execution fails with exit code 1 every turn** and falls back to subprocess
  (~30s extra/turn). Not the proximate cause but a systemic latency tax.

The failure is **not** a defect in the implementation written by TASK-NATS-PH1-006 — turn 3's
own validation (`tests_passed=true, coverage_met=true, all_gates_passed=true`) shows the player
satisfied its acceptance criteria. The wave plan is also defensible as designed; the oracle
was the unsatisfiable gate.

**Recommended decision:** [I]mplement — three concrete child fixes (one to unblock the run,
two to harden the orchestrator), then `--resume` rather than `--fresh`.

---

## Failure Timeline

| Turn | Phase | Duration | Outcome | Notable |
|------|-------|----------|---------|---------|
| 1 | Player | 670s (56 SDK turns) | success: 7 created, 31 modified, 1 test passing | Wrote `cli/main.py` serve-nats body, `tests/unit/cli/test_serve_nats.py`, the BDD step-defs glue, and the feature file copy. |
| 1 | Coach specialists | 567s | tests=pass, coverage=pass, arch=pass, audit=pass | All hard gates green. |
| 1 | Coach BDD oracle | — | **rejected** | `bdd_runner: passed=0 failed=1 pending=0` for `not found: features/nats-fleet-integration/nats-fleet-integration.feature` *(file existed; collection bridge issue, see below)*. |
| 2 | Player | ~530s (resume) | success: 6 created, 39 modified | Player added the explicit feature file path so collection found it. |
| 2 | Coach independent tests | 1.6s | **failed** | `pytest features/nats-fleet-integration/test_nats_fleet_integration.py …` collected ALL 30+ scenarios; 3+ explicitly listed as failed (deregister/max-msg-size/llm-unrea…). |
| 2 | Classifier | — | `parallel_contention/high` | Peer overlap correctly observed (003 → roles/, 007 → .env.example) but mis-attributed as the cause. |
| 2 | `conditional_approval` | — | NOT triggered | `docker_available=False` predicate failed, despite `all_gates_passed=true, wave_size=4`. |
| 3 | Player | 152s (19 SDK turns) | success: 2 created, 46 modified, 0 tests | Smaller delta — player ran out of meaningful edits to make against an oracle it couldn't satisfy. |
| 3 | Coach independent tests | 1.6s | **failed** | Same scenarios fail; classifier still says `parallel_contention/high`. |
| 4 | Orchestrator | — | `timeout_budget_exhausted` | `remaining=511.2s < min=600s` ⇒ task killed. |

Total elapsed for TASK-006: ~41 min before bail-out. Each retry took ~13–17 min and made no
progress against the gate.

## Root Cause Analysis

### RC-1 (PRIMARY) — BDD oracle scope is the whole feature file, not the task's scenario set

**Evidence:**
- `features/nats-fleet-integration/nats-fleet-integration.feature` carries scenarios tagged
  `@task:` for **9 different tasks** (TASK-NATS-PH1-002, -004, -005, -006, -008, -009, PH2-001,
  PH2-003, PH3-002, PH3-004, PH3-005). Only one scenario (line 248–256, "SIGTERM during an
  in-flight tutor turn drains the request before deregistration") is owned by TASK-006.
- The Coach test command (`coach_turn_2.json`):
  `pytest features/nats-fleet-integration/test_nats_fleet_integration.py …` — no `--bdd-tag`
  / `-k @task:TASK-NATS-PH1-006` filter.
- The generated step-defs file `test_nats_fleet_integration.py` documents the intent in its
  module docstring: "scenarios … tagged for a downstream task … will land with that task;
  their steps remain intentionally unbound here. They surface as `scenarios_pending` and are
  tolerated by the Coach gate (`scenarios_failed == 0`)."
- pytest-bdd v8 actually emits unbound scenarios as **FAILED** test functions, not pending —
  three named in the coach output (`test_a_command_arriving_during_the_deregister_phase…`
  → @task:TASK-NATS-PH1-005; `test_a_result_envelope_exceeding…` → @task:TASK-NATS-PH3-005;
  `test_llm_unrea…` → @task:TASK-NATS-PH1-004 or -005).

**Why this is a hard gate failure, not transient noise:** every retry will produce the same
deterministic failure list until those downstream tasks are implemented. The oracle is
unsatisfiable for any single-task feature-file-cohort under the canonical `/feature-spec`
pattern (one feature per epic, scenarios tagged per task).

### RC-2 — Classifier mis-labels RC-1 as `parallel_contention`

**Evidence:**
- `coach_turn_2.json: failure_classification=parallel_contention, confidence=high`,
  with `Overlapping files by peer: TASK-NATS-PH1-003 → src/study_tutor/roles/*; TASK-NATS-PH1-007 → .env.example, …`.
- TASK-006's own `Scope` (per the task spec) is `src/study_tutor/cli/main.py` plus tests under
  `tests/unit/cli/`. It does not own roles/ or .env.example. The "overlap" is detected by
  worktree-wide `git diff` (line 606: `Git detection added: 30 modified, 5 created files for
  TASK-NATS-PH1-006`), which collects peer task changes — TASK-006 was not actually authoring
  in those files.
- Even by turn 3, when 003 and 007 had completed and the wave was effectively serialised, the
  classifier kept reporting `parallel_contention/high`. A genuine contention signal would
  resolve once peers commit; this one didn't, because the underlying failure is RC-1.

The classifier is correct that there *is* peer overlap; it is wrong about that being causal.

### RC-3 — `conditional_approval` rule is too narrow

**Evidence:**
- Lines 802–804 / 914–916: `conditional_approval check: failure_class=parallel_contention,
  confidence=high, requires_infra=[], docker_available=False, all_gates_passed=True, wave_size=4`.
- All other predicates pass; `docker_available=False` blocks. But this run did not need docker
  for anything in Wave 2 (003, 007, 002 all completed without it).

The rule conflates "this failure could be infrastructure noise" with "we have docker therefore
we can verify". For `parallel_contention + all_gates_passed`, docker is irrelevant — the
specialist gates already cleared, conditional approval is the right answer.

### RC-4 — Turn budget is too tight for complexity-4 task with this overhead

**Evidence:**
- `max_turns=7`, but turn 1 burned ~25 min; turn 2 added ~17 min; the remaining budget at
  turn 4 was 511s vs minimum 600s. The orchestrator did the right thing by bailing — the
  arithmetic was already over.
- Coach specialist invocation alone took 567s (test-orchestrator + code-reviewer chained,
  17 specialist progress lines visible). That is not unusual for the SDK path.
- Compounding: SDK fallback (RC-5) costs ~30s/turn × 7 = ~3.5 min wasted per task.

This isn't really a bug in the budget — `complexity=4 × max_turns=7` is normally adequate.
But under RC-1 the loop never moves; budget exhaustion is just how the unbreakable gate kills
the task.

### RC-5 — Coach SDK test runner regression (cosmetic, but real)

**Evidence:** every coach turn:
```
DEBUG:claude_agent_sdk._internal.query:Fatal error in message reader: Command failed with exit code 1
ERROR:guardkit.orchestrator.quality_gates.coach_validator:SDK coach test execution failed (error_class=Exception)
WARNING: ... falling back to subprocess.
INFO: Independent tests failed/passed in 1.6s
```

Note the env line: `sys.executable=/usr/local/bin/python3, which pytest=/Library/Frameworks/Python.framework/Versions/3.14/bin/pytest`. Two interpreters; the SDK is invoking
`/usr/local/bin/python3 -m pytest` while the worktree's pytest is the framework one. The
subprocess fallback uses the framework path and works. Cost is ~30s/turn for the SDK to fail
and bail. Not the proximate cause; cleanup item.

### RC (non-issue) — Implementation quality

`coach_turn_2.json` reports: `tests_passed=true, coverage_met=true, arch_review_passed=true,
plan_audit_passed=true, all_gates_passed=true, honesty_score=1.0`. The player wrote correct
code. The only "must_fix" issue in the report is `test_verification` (RC-1).

## Decisions

### D-1 — Wave plan: keep TASK-006 in Wave 2 (with caveats)

Wave 2's parallel set was `[002, 003, 006, 007]`. Genuine contention check:

| File | TASK-002 | TASK-003 | TASK-006 | TASK-007 |
|------|----------|----------|----------|----------|
| `src/study_tutor/cli/main.py` | — | — | **owner** | — |
| `src/study_tutor/roles/*` | — | **owner** | reads | — |
| `src/study_tutor/__init__.py` | possibly | possibly | possibly | — |
| `.env.example` | — | — | — | **owner** |

There is no real source-file conflict. TASK-006 wires the CLI; it imports roles but does not
modify roles/. The wave plan is correct. **Keep it.**

The exception is `src/study_tutor/__init__.py`, which several tasks may touch for re-exports;
this is the only legitimate (and trivial) merge surface. We will not redesign for it.

### D-2 — `conditional_approval` rule: drop the `docker_available` predicate for `parallel_contention/high + all_gates_passed`

When the failure class is `parallel_contention/high`, all hard gates pass, and no
infrastructure is required (`requires_infra=[]`), the orchestrator should conditionally
approve. Docker has no bearing on this failure class. File as TASK-FIX-CC-COND.

### D-3 — BDD oracle wiring: filter by `@task:TASK-XXX` tag

This is the load-bearing fix. The Coach BDD runner must scope to the scenarios the task owns:

- **Preferred (orchestrator change):** `bdd_runner` invokes pytest-bdd with the task's
  `@task:TASK-XXX` tag filter, e.g. `pytest --bdd-features-base-dir=… -m "task_TASK_NATS_PH1_006"`
  or `-k "TASK_NATS_PH1_006"` against the autogenerated test IDs. The test file itself already
  documents the intent: only bind steps for the task's own scenarios; treat the rest as
  pending.
- **Required workaround for FEAT-39E1 re-run (no orchestrator change):** generate a focused
  feature copy per task at run start (`features/nats-fleet-integration/__task__/<task-id>.feature`)
  containing only that task's scenarios, and have the player point its `coach_validation`
  block at that file. Cheap, mechanical, no orchestrator code change needed.

**Bonus:** also fix the orchestrator-side counting so unbound steps in pytest-bdd v8 register
as `pending`, not `failed`. The step-defs file already says this is the intent — make the
oracle agree.

### D-4 — SDK→subprocess fallback: accept subprocess as primary

For coach test execution, the subprocess fallback is reliable and fast (~1.6s vs the SDK path
that fails in ~30s every time). Until the SDK exit-code-1 issue is diagnosed, switch
`coach_test_execution` default to `subprocess` to save ~30s/turn × every coach validation.
File as a separate orchestrator-config TODO; do not block FEAT-39E1 re-run on it.

### D-5 — Turn budget: leave at 7 for complexity-4

With RC-1 fixed, turn 1 should approve cleanly (or at most rebound once for a real adjustment).
`max_turns=7` is adequate. No change.

## Remediation Plan

Three concrete child tasks unblock the re-run; one is a follow-up improvement.

### TASK-NATS-FIX-001 — Scope BDD feature file per task (workaround)
**Owner:** TASK-NATS-PH1-006 (the failing task), but applies to every task in the feature
that has `@task:` tags.

Edit `tasks/backlog/nats-fleet-integration/TASK-NATS-PH1-006-serve-nats-cli-subcommand.md` so
the player generates a per-task feature copy at run time (or at task-spec time). One viable
shape:

- Add `features/nats-fleet-integration/by-task/TASK-NATS-PH1-006.feature` containing only the
  Background + the single `@task:TASK-NATS-PH1-006` scenario (lines 246–256 of the master
  feature).
- Update the task's `## Coach validation` block to point pytest-bdd at the focused file:
  ```
  pytest features/nats-fleet-integration/by-task/TASK-NATS-PH1-006.feature -v
  pytest tests/unit/cli/test_serve_nats.py -v
  ```
- Update `.guardkit/features/FEAT-39E1.yaml` task entry for 006 with the focused feature file
  reference if the orchestrator reads BDD feature paths from there.

This is the minimum to unblock the re-run. It does not require any GuardKit code change.

### TASK-NATS-FIX-002 — Wave plan adjustment (defensive, optional)
Move TASK-006 to a wave of its own (Wave 2b) so any future false-positive
`parallel_contention` cannot fire. Current wave 2 = `[002, 003, 006, 007]`; new layout:
```yaml
parallel_groups:
  - [TASK-NATS-PH1-001]
  - [TASK-NATS-PH1-002, TASK-NATS-PH1-003, TASK-NATS-PH1-007]   # wave 2a
  - [TASK-NATS-PH1-006]                                          # wave 2b
  - [TASK-NATS-PH1-004]
  - …
```
Cost: minimal (006 is fast); benefit: classifier can never mis-fire.

**Recommendation:** apply this only if FIX-001 alone is judged insufficient. Adds ~3 min of
serial wall-time, removes one whole risk surface for the demo deadline.

### TASK-NATS-FIX-003 — Re-run preparation
- Inspect the worktree (`.guardkit/worktrees/FEAT-39E1`). Wave 1 commit `b0ba660` and Wave 2
  partial commits `c7cee4b/48fbd86/f04fa82/ed5a837/b11a064/0823395` are present. Decide:
  `--resume` (keep checkpoints, rerun 006 only against the new feature file) or `--fresh`
  (discard worktree, re-do Wave 1 + Wave 2 from main).
- **Recommended:** `--resume`. Wave 1 (TASK-001) and Wave 2 peers (002, 003, 007) all PASSED;
  re-running them is wasted ~10 min. Resume targets only TASK-006 with the corrected feature
  file.
- Pre-run smoke-check that `study-tutor serve-nats --help` works in the worktree (it should,
  per turn 3 player output) so we are not paying for a fresh implementation pass.

### TASK-FIX-CC-COND (follow-up, GuardKit upstream)
Expand `conditional_approval` rule:
```
if failure_class == "parallel_contention" and confidence == "high"
   and all_gates_passed and not requires_infra:
    return APPROVED  # docker_available is irrelevant
```
File against the GuardKit repo, not study-tutor. Not required for FEAT-39E1 re-run.

### TASK-FIX-CC-BDD (follow-up, GuardKit upstream)
Make `bdd_runner` scope by `@task:` tag, and count unbound-step scenarios as `pending`
rather than `failed` (matching the documented design intent in the autogenerated step-defs
file). File against GuardKit. Not required for FEAT-39E1 re-run *if* FIX-001 is applied.

## Re-run Readiness Statement

After TASK-NATS-FIX-001 lands (and optionally FIX-002), run:

```bash
guardkit autobuild feature FEAT-39E1 --resume
```

Expected behaviour change: turn 1 of TASK-NATS-PH1-006 should approve on first pass.
- Player is resumed from checkpoint `0823395` (turn 3 state — implementation already in
  place); since the focused feature file changes the gate the player needs to satisfy, expect
  turn 1 to be a small adjustment ("write a focused feature file or update the coach
  validation block"), not a full re-implementation.
- Coach turn 1: `bdd_runner` collects 1 scenario (`@task:TASK-NATS-PH1-006`), step-defs are
  bound, scenario passes (the SIGTERM contract is already implemented per turn 3).
  `scenarios_failed == 0` → gate passes.
- `parallel_contention` will not fire because the failure class (`bdd_oracle`) won't trigger.
- Run continues into Wave 3 (TASK-NATS-PH1-004) and onward, recovering the remaining 14/18
  tasks against the original budget.

**Demo deadline (2026-05-11):** the only critical path that must complete is Phase 1.
TASK-001/002/003/007 are already done; TASK-006 needs FIX-001; TASK-004/005/008/009/010
remain but have realistic budgets. Demo target is achievable on a clean re-run after FIX-001.

## Findings

| # | Finding | Severity | Evidence |
|---|---------|----------|----------|
| F-1 | BDD oracle runs the entire feature file, not the task's scenario set | **Critical** | coach_turn_2.json test_command; 1 of 30+ scenarios is owned by 006 |
| F-2 | pytest-bdd v8 emits unbound scenarios as FAILED, contradicting documented design (pending) | High | step-defs module docstring; coach test_output |
| F-3 | Classifier mis-labels RC-1 as `parallel_contention` | High | coach_turn_2.json; classifier still fires after peers complete |
| F-4 | `conditional_approval` requires `docker_available` even for non-infra failure classes | Medium | log lines 802–804 |
| F-5 | Coach SDK test execution fails every turn, falls back to subprocess (~30s tax) | Low | log lines 664–668 / 796–800 / 908–912 |
| F-6 | Turn 1 of complexity-4 tasks can run ~25min under SDK; budget tight if any retry pattern | Low | log line 611 (`SDK invocation complete: 670.5s`) plus 567s coach |
| F-7 | TASK-006 implementation itself is sound (all hard gates pass) | n/a | coach_turn_2 quality_gates: all_passed=true |

## Recommendations (ranked)

1. **Apply TASK-NATS-FIX-001 (scope BDD feature file per task)** — single load-bearing fix to
   unblock FEAT-39E1 re-run.
2. **Apply TASK-NATS-FIX-002 (wave plan)** — defensive, only if FIX-001 alone feels risky.
3. **Resume the autobuild** (`--resume`) rather than `--fresh` — preserves Wave 1 + 4/4 of
   Wave 2's peers.
4. **File TASK-FIX-CC-BDD upstream** — fix the BDD runner scope + pending-vs-failed counting.
5. **File TASK-FIX-CC-COND upstream** — drop docker predicate from non-infra
   conditional-approval cases.
6. **Investigate Coach SDK test execution failure** when convenient — ~30s/turn savings.

## Decision Matrix

| Option | Cost | Risk to demo (2026-05-11) | Recommendation |
|--------|------|---------------------------|----------------|
| `--resume` after FIX-001 only | ~10 min wall-time, 1 file edit | Low | **Recommended** |
| `--resume` after FIX-001 + FIX-002 | ~10 min wall-time, 2 files | Lower | Belt-and-braces |
| `--fresh` after FIX-001 | +30 min (re-do Wave 1 + 2 peers) | Low | Wasteful |
| Skip orchestrator fixes, force-approve 006 | 5 min, manual gate-bypass | Higher (no oracle on PH1-006 SIGTERM contract) | Not recommended |

---

## Appendix A — Evidence Pointers

- Failure log: [docs/history/autobuild-FEAT-39E1-fail-run-1.md](../../docs/history/autobuild-FEAT-39E1-fail-run-1.md)
  - Turn 1 player + initial BDD failure: lines 588–612
  - Turn 1 coach rejection (`bdd_results.scenarios_failed > 0`): lines 663–675
  - Turn 2 coach independent tests fail in 1.6s, classifier `parallel_contention`: lines 793–820
  - Turn 3 same pattern; checkpoint created: lines 853–930
  - Timeout exhaustion: line 931
  - `conditional_approval` fail: lines 802–804 / 914–916
- Coach decision artefacts:
  - [.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-006/coach_turn_1.json](../../.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-006/coach_turn_1.json)
  - [.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-006/coach_turn_2.json](../../.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-006/coach_turn_2.json)
- Master feature file: [features/nats-fleet-integration/nats-fleet-integration.feature](../../.guardkit/worktrees/FEAT-39E1/features/nats-fleet-integration/nats-fleet-integration.feature)
- Step-defs glue (documents the design intent): [features/nats-fleet-integration/test_nats_fleet_integration.py](../../.guardkit/worktrees/FEAT-39E1/features/nats-fleet-integration/test_nats_fleet_integration.py) lines 1–35
- TASK-006 spec: [tasks/backlog/nats-fleet-integration/TASK-NATS-PH1-006-serve-nats-cli-subcommand.md](../../tasks/backlog/nats-fleet-integration/TASK-NATS-PH1-006-serve-nats-cli-subcommand.md)
- Feature plan: [.guardkit/features/FEAT-39E1.yaml](../../.guardkit/features/FEAT-39E1.yaml) (orchestration.parallel_groups, line 306+)

## Appendix B — File-overlap reality check

| File | Wave-2 task that *owns* it (per task spec scope) |
|------|---------------------------------------------------|
| `src/study_tutor/cli/main.py` | TASK-NATS-PH1-006 (only) |
| `src/study_tutor/roles/__init__.py`, `registry.py`, `tutor/__init__.py` | TASK-NATS-PH1-003 (only) |
| `tests/unit/roles/test_registry.py` | TASK-NATS-PH1-003 (only) |
| `.env.example` | TASK-NATS-PH1-007 (only) |
| `tests/unit/test_env_example_nats.py` | TASK-NATS-PH1-007 (only) |
| `pyproject.toml` (manifest dep) | TASK-NATS-PH1-001 (Wave 1) |
| `src/study_tutor/__init__.py` (if touched) | shared, trivial |
| `features/nats-fleet-integration/nats-fleet-integration.feature` | shared (one scenario per task, by `@task:` tag) |
| `features/nats-fleet-integration/test_nats_fleet_integration.py` (step-defs) | per-task scope: each task adds bindings for its own scenarios |

Conclusion: the only intentional shared surface is the feature file + step-defs glue, and
the design *expected* per-task scenario binding. The oracle scope is the single defect.
