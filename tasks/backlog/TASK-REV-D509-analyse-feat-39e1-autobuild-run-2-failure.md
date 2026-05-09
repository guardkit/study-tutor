---
id: TASK-REV-D509
title: Analyse FEAT-39E1 autobuild run-2 failure (operator_handoff dependency block)
status: review_complete
task_type: review
decision_required: true
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
priority: high
tags: [autobuild, post-mortem, nats-fleet, operator-handoff, dependency-resolver, deferred-task]
complexity: 5
feature: FEAT-39E1
related_tasks:
  - TASK-NATS-PH1-010
  - TASK-NATS-PH2-001
  - TASK-NATS-PH2-003
  - TASK-REV-CC40
inputs:
  failure_log: docs/history/autobuild-FEAT-39E1-fail-run-2.md
  prior_review: tasks/backlog/TASK-REV-CC40-analyse-feat-39e1-autobuild-failure.md
  feature_yaml: .guardkit/features/FEAT-39E1.yaml
  worktree: .guardkit/worktrees/FEAT-39E1
  events_log: .guardkit/autobuild/FEAT-39E1/events.jsonl
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: decision
  depth: standard
  decision: pending_user_checkpoint
  findings_count: 5
  recommendations_count: 2
  report_path: .claude/reviews/TASK-REV-D509-review-report.md
  completed_at: 2026-05-09T00:00:00Z
  primary_root_cause: "GuardKit orchestrator semantics gap: `_dependencies_satisfied` (feature_orchestrator.py:3429-3433) hard-codes `status != 'completed'` as unsatisfied. TASK-FPTC-003 introduced `status='deferred'` as a terminal-but-not-failed state for operator_handoff skips but did not extend the dependency predicate, so `deferred` predecessors crash the wave dispatcher."
  contributing_causes:
    - "FEAT-39E1.yaml encodes PH1-010 as a hard dependency of PH2-001 and PH2-003, but neither task has a real code-level dependency on PH1-010 (PH2-001's real deps are PH1-004/PH1-005; PH2-003 is pure documentation). Feature schema has no soft-vs-hard dependency distinction."
    - "Wave-level dep check raises before dispatching any task in the wave, so PH3-004 (which has no PH1-010 link) is collateral damage."
  recommendations:
    - "TASK-NATS-FIX-003 (in-repo, ~10 min, direct mode): rewrite PH2-001 dependency to PH1-005 and clear PH2-003 dependencies in FEAT-39E1.yaml + task frontmatter. Unblocks the autobuild re-run today."
    - "TASK-FIX-DEFD (upstream guardkit repo, ~30 min, task-work): teach `_dependencies_satisfied` that `status in {completed, deferred}` is satisfied; emit warning when proceeding against a deferred predecessor. Durable fix for the next FEAT in this situation. Not required for the FEAT-39E1 re-run. File: `~/Projects/appmilla_github/guardkit/tasks/backlog/TASK-FIX-DEFD-treat-deferred-as-satisfied-in-dependency-resolver.md`."
  demo_readiness: "ON TRACK for 2026-05-11. PH1-010 IS the demo (operator runs it on GB10 with Open WebUI). Keeping it deferred is consistent with the demo plan. After in-repo fix, autobuild lands all artefacts the operator needs (Dockerfile/compose/build script/runbook/GB10 smoke); operator runs PH1-010 manually as the demo."
---

# Task: Analyse FEAT-39E1 autobuild run-2 failure (operator_handoff dependency block)

## Description

After the run-1 fixes ([TASK-REV-CC40](TASK-REV-CC40-analyse-feat-39e1-autobuild-failure.md), TASK-NATS-FIX-001, TASK-NATS-FIX-002) were applied, the FEAT-39E1 autobuild was re-run with `--resume` on **2026-05-08 21:24 UTC**. This second run made meaningful progress — TASK-NATS-PH1-006 (the run-1 blocker) approved in 4 turns; Waves 3–7 produced 9 fresh approvals — but then **crashed before Wave 8** with:

```
DependencyError: Task TASK-NATS-PH2-001 has unsatisfied dependencies: ['TASK-NATS-PH1-010']
```

`TASK-NATS-PH1-010` (E2E demo gate, complexity 7) was **deliberately skipped** by the orchestrator at Wave 7 with `status=deferred`, `deferred_reason="operator follow-up — runtime verification required"`. The skip itself is by design (no Player/Coach burn). The crash is what's wrong: dependent tasks PH2-001 and PH2-003 declare PH1-010 as a hard dependency, and the wave dispatcher (`feature_orchestrator.py:2059`) raises `DependencyError` when it cannot find a `completed` predecessor.

This is a **review/analysis task** to:

1. Confirm the root cause (orchestrator semantics gap, not a task-spec defect).
2. Decide remediation: orchestrator behaviour change (upstream GuardKit), feature-yaml dependency rewrite (in-repo), implement PH1-010 properly, or some combination.
3. Produce a concrete action plan and child tasks so the autobuild can finish FEAT-39E1.

Full failure log: [docs/history/autobuild-FEAT-39E1-fail-run-2.md](../../docs/history/autobuild-FEAT-39E1-fail-run-2.md)
Prior review (run-1):  [TASK-REV-CC40](TASK-REV-CC40-analyse-feat-39e1-autobuild-failure.md)

## Observed Failure Signature

### Run-2 wave outcomes (success picture before the crash)

| Wave | Tasks | Result | Notes |
|------|-------|--------|-------|
| 1 | PH1-001 | ✓ skipped (resume) | already completed in run-1 |
| 2 | PH1-002, 003, 007 | ✓ skipped (resume) | already completed in run-1 |
| 3 | PH1-006 | ✓ **approved (4 turns)** | run-1 blocker — TASK-NATS-FIX-001 worked |
| 4 | PH1-004 | ✓ approved (1 turn) |  |
| 5 | PH1-005 | ✓ approved (2 turns) |  |
| 6 | PH1-008, PH1-009, PH2-002, PH3-001 | ✓ all approved (1 turn each, parallel: 4) | clean parallel run |
| 7 | PH1-010, PH3-002, PH3-003 | ⚠ PH1-010 **DEFERRED**; PH3-002/003 approved (1 turn each) | operator_handoff skip |
| 8 | (PH2-001) | ❌ **DependencyError** before any task ran | orchestration aborted |

### The crash

Log line 1808–1810:
```
[2026-05-08T23:00:23.915Z] ⏭ TASK-NATS-PH1-010: SKIPPED - DEFERRED — operator follow-up — runtime verification required
[TASK-NATS-PH1-010] operator_handoff skip: deferred (no Player/Coach invocation, no SDK budget burn).
   reason='operator follow-up — runtime verification required'
```

Log line 2079–2087:
```
ERROR:guardkit.orchestrator.feature_orchestrator:Feature orchestration failed:
   Task TASK-NATS-PH2-001 has unsatisfied dependencies: ['TASK-NATS-PH1-010']
Traceback (most recent call last):
  File "guardkit/orchestrator/feature_orchestrator.py", line 774, in orchestrate
    wave_results = self._wave_phase(feature, worktree)
  File "guardkit/orchestrator/feature_orchestrator.py", line 2059, in _wave_phase
    raise DependencyError(...)
```

### Feature-yaml state (post-run-2)

Reading `.guardkit/features/FEAT-39E1.yaml`:

- **PH1-010** → `status: deferred`, `result.final_decision: deferred`, `result.deferred_reason: "operator follow-up — runtime verification required"`, `turns_completed: 0`
- **PH2-001** (Readiness gating in command router, complexity 3, mode `direct`, est 33 min) → `status: pending`, `dependencies: [TASK-NATS-PH1-010]`
- **PH2-003** (Stale registry runbook documentation, complexity 2, mode `direct`, est 22 min) → `status: pending`, `dependencies: [TASK-NATS-PH1-010]`

So two pending tasks (PH2-001 + PH2-003, both small / direct mode) are blocked by a single deferred task. Wave 9 (whatever it contains) was never reached.

## Acceptance Criteria

- [ ] **Root-cause analysis written** covering at minimum:
  - [ ] Confirm orchestrator behaviour: in `_wave_phase`, what does the dependency check require? `status == 'completed'`? Or any non-failed terminal state? Why does `deferred` not satisfy?
  - [ ] Confirm whether `operator_handoff/deferred` is a documented terminal state in the orchestrator's contract (vs. an emergent shortcut). Cross-reference TASK-REV-CC40 — was this introduced by the conditional-approval / skip logic added there?
  - [ ] Determine whether PH1-010's deferral was triggered by metadata in the task file (e.g. `requires_operator_handoff: true` in frontmatter) or by an orchestrator heuristic (complexity, requires_infrastructure, etc.). Inspect [TASK-NATS-PH1-010-e2e-demo-gate.md](nats-fleet-integration/TASK-NATS-PH1-010-e2e-demo-gate.md).
  - [ ] Quantify blast radius: which downstream tasks are blocked? PH2-001, PH2-003, and anything in Wave 9 transitively dependent.

- [ ] **Decisions recorded** for each of:
  - [ ] **Orchestrator behaviour (upstream GuardKit):** when a task is skipped with `operator_handoff/deferred`, should the dispatcher (a) crash, (b) propagate `deferred` to dependents and continue with non-dependent waves, (c) honour the skip and run dependents anyway with a warning, or (d) require the feature spec to declare which dependencies are "hard" vs. "soft"? Pick one.
  - [ ] **Feature-yaml in-repo workaround:** is the PH1-010 dependency on PH2-001 / PH2-003 actually load-bearing for those small tasks? If not, drop the dependency in `.guardkit/features/FEAT-39E1.yaml` so the run can finish. (PH2-001 = 33 min direct mode; PH2-003 = 22 min docs — neither obviously needs PH1-010 wiring.)
  - [ ] **Should PH1-010 actually be deferred?** Re-evaluate: is "E2E demo gate Open WebUI to tutor" really not autobuild-able, or did the deferral heuristic over-fire? If it's runnable, un-defer it.
  - [ ] **Demo readiness:** is the 2026-05-11 demo deadline (from TASK-REV-CC40) still on track? Even if PH1-010 stays deferred, can a manual operator step + the in-repo dependency rewrite get us across the line?

- [ ] **Remediation plan produced** in `.claude/reviews/TASK-REV-D509-review-report.md`, with:
  - [ ] In-repo follow-up task(s) — minimal change to unblock FEAT-39E1 re-run.
  - [ ] Upstream GuardKit follow-up task(s) — durable orchestrator fix for `operator_handoff/deferred` semantics.
  - [ ] Re-run command and expected behaviour.

- [ ] **Follow-up implementation task(s) created** linking back to this review.

- [ ] **Re-run readiness statement**: after the in-repo fix lands, what does `guardkit autobuild feature FEAT-39E1 --resume` do? Which waves replay vs. resume from checkpoint? What does success look like?

## Out of Scope

- Implementing the fixes themselves — those go into child tasks created by this review.
- Re-running the autobuild — that happens after child fixes land.
- Implementing TASK-NATS-PH1-010 itself unless the review concludes deferral was a mistake. (The runtime-verification rationale may be legitimate.)
- Re-litigating run-1 root causes (already covered in TASK-REV-CC40).

## Investigation Notes (to be filled by /task-review)

### Evidence pointers

- **Run-2 success up to Wave 7** — confirms TASK-REV-CC40 fixes worked. Lines 36–1797.
- **PH1-010 deferral** — log lines 1804–1810. Reason string: `operator follow-up — runtime verification required`.
- **Crash site** — log lines 2079–2090. Trace points at `feature_orchestrator.py:2059` (`raise DependencyError(...)`) under `_wave_phase`.
- **Feature yaml state** — `.guardkit/features/FEAT-39E1.yaml` lines 185–253: PH1-010 deferred; PH2-001 + PH2-003 pending with PH1-010 in their `dependencies` list.

### Hypotheses to test

1. **Hard-dependency semantics gap (primary):** the orchestrator's wave dispatcher checks `status == 'completed'` (or equivalent) and treats every other terminal state — including `deferred` — as unsatisfied. There is no soft-vs-hard dependency distinction in the feature yaml schema, so the dispatcher cannot tell that PH2-003 (a docs runbook) does not actually need PH1-010 to be implemented.
2. **Deferral heuristic source:** PH1-010 may declare `requires_operator_handoff: true` (or similar) in its frontmatter, or the orchestrator may auto-defer based on complexity ≥ 7 + a runtime-keyword scan. Worth checking: does this match the design intent for `operator_handoff` skips?
3. **Cascading-deferral alternative:** instead of crashing, the orchestrator could mark dependents as `deferred` too (status = "deferred-by-dependency"). This is the safest behaviour — it preserves the guarantee that nothing downstream of a deferred task accidentally runs, while letting the rest of the wave plan proceed.
4. **In-repo dependency rewrite is the cheap fix:** for FEAT-39E1 specifically, PH2-001's actual code-level dependency may be PH1-005 (manifest factory) + PH1-006 (serve-nats CLI), not PH1-010. PH2-003 is a docs task and probably has no real dependency. Worth diffing what each task file says it needs vs. what's in the feature yaml.

### What's NOT in scope here

- The TASK-REV-CC40 root causes (BDD oracle scope, parallel_contention classifier, conditional_approval predicate). All four were addressed and run-2 confirms the BDD/parallelism fixes worked.

## Test Requirements

- [ ] N/A for the review itself; child implementation tasks must include their own tests.

## Implementation Notes

Review completed 2026-05-09. Full report at [.claude/reviews/TASK-REV-D509-review-report.md](../../.claude/reviews/TASK-REV-D509-review-report.md).

**Confirmed primary root cause:** GuardKit orchestrator's `_dependencies_satisfied` (at [feature_orchestrator.py:3429-3433](/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py#L3429-L3433)) only accepts `status == "completed"`. TASK-FPTC-003 added `status="deferred"` as terminal-but-not-failed but never extended the predicate. The same orchestrator's `_update_feature` writer (line 3461-3466) explicitly preserves `deferred` as terminal — internally inconsistent contract.

**Decisions recorded** (see report § Decisions for rationale):

1. **Orchestrator behaviour:** option (b)/(c) — propagate `deferred` as satisfied with a warning. Reject (a) crash, (d) soft-vs-hard schema (YAGNI).
2. **In-repo workaround:** YES — drop spurious PH1-010 edges from PH2-001 and PH2-003 in feature yaml + task frontmatter. Both edges encode temporal/soft hints, not real code deps.
3. **PH1-010 deferral:** keep deferred. AC-PH1-010-1..5 require GB10 + Open WebUI + wire-tap + hand-written RESULTS — not autobuild-able.
4. **Demo readiness:** ON TRACK. PH1-010 is the demo; operator runs it on 2026-05-11.

**Blast radius:** Wave 8 = [PH2-001, PH2-003, PH3-004] all blocked (PH3-004 is collateral — its only dep PH3-002 is completed, but the wave-level dep check raises before dispatching any task). Wave 9 (PH3-005) transitively blocked. ~361 min of work halted.

**Open question flagged for follow-up (not blocker for re-run):** PH3-005 (GB10 E2E smoke, complexity 8) may itself need `task_type: operator_handoff`. Decide at dispatch.

## Decision Checkpoint

After review, record one of:
- **[A]ccept** – findings approved, proceed to create implementation tasks.
- **[I]mplement** – findings approved AND create implementation tasks immediately.
- **[R]evise** – more analysis required (e.g. inspect orchestrator dependency-resolver code, instrument PH1-010 frontmatter).
- **[C]ancel** – discard review (not recommended; orchestration is genuinely stuck).

## Test Execution Log

[Auto-populated by `/task-review` / child `/task-work` runs]
