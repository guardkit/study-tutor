# Review Report: TASK-REV-D509 — FEAT-39E1 autobuild run-2 post-mortem

**Mode:** decision (post-mortem + remediation planning)
**Depth:** standard
**Generated:** 2026-05-09
**Subject:** FEAT-39E1 (study-tutor NATS Fleet Integration), Wave 8 dispatch / `operator_handoff` dependency block
**Outcome of run:** `DependencyError` — 17 of 18 tasks reached terminal state (15 completed + 1 deferred + 1 already-completed-pre-resume), Wave 8 never dispatched, Wave 9 unreachable
**Prior review:** [TASK-REV-CC40](../../tasks/backlog/TASK-REV-CC40-analyse-feat-39e1-autobuild-failure.md) — run-1 fixes confirmed working

## Executive Summary

The TASK-REV-CC40 fixes worked: PH1-006 approved in 4 turns (was the run-1 blocker), Waves
3–7 produced 9 fresh approvals with no parallel-contention false positives. Then the orchestrator
crashed before Wave 8 with `DependencyError: TASK-NATS-PH2-001 has unsatisfied dependencies:
['TASK-NATS-PH1-010']`.

PH1-010 is `task_type: operator_handoff` (E2E demo gate that requires GB10 hardware, an Open
WebUI browser session, wire-tap inspection, and an operator-written RESULTS file). The
orchestrator correctly skipped it at Wave 7 with `status=deferred` — that path was added by
TASK-FPTC-003 and is by design. The bug is downstream: the dependency resolver does not know
about the `deferred` terminal state.

**Confirmed root cause** ([feature_orchestrator.py:3429-3433](/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py#L3429-L3433)):

```python
def _dependencies_satisfied(self, task, feature) -> bool:
    for dep_id in task.dependencies:
        dep_task = FeatureLoader.find_task(feature, dep_id)
        if dep_task and dep_task.status != "completed":
            return False
    return True
```

The check is `status != "completed"`. TASK-FPTC-003 introduced `status="deferred"` as
"terminal-but-not-failed" but never extended the predicate. Two halves of the same orchestrator
disagree about what `deferred` means: the `_update_feature` path treats it as a successful
terminal outcome (line 3461-3466), the wave dispatcher treats it as failure-equivalent.

**Compounding factor:** the feature yaml encodes both PH2-001 and PH2-003 as depending on
PH1-010, but **neither has an actual code-level dependency** on PH1-010:

- **PH2-001** ("Readiness gating in command router", direct, ~33 min) modifies
  `command_router.py` to gate on `_adapter_ready.is_set()`. Its real code dependencies are
  PH1-004 (`CommandRouter`, ✓ completed) and PH1-005 (`NATSAdapter._ready`, ✓ completed).
- **PH2-003** ("Stale registry runbook", direct, ~22 min) is pure documentation. The
  PH1-010 dependency is a temporal hint ("don't write Phase 2 docs until Phase 1 demo
  evidence exists"), not a real ordering constraint.

So the feature spec authors used `dependencies` as a soft/temporal ordering signal while the
orchestrator interprets it as a hard prerequisite. Both interpretations are reasonable; the
schema doesn't distinguish.

**Blast radius:** Wave 8 = `[PH2-001, PH2-003, PH3-004]`. PH3-004's only dependency is
PH3-002 (✓ completed) — it should have run, but the orchestrator crashes *before* dispatching
any Wave-8 task. Wave 9 (PH3-005, GB10 E2E smoke) is transitively blocked. So one deferred
task plus a too-rigid resolver halted four pending tasks (~361 min of work).

**Demo readiness (2026-05-11):** ON TRACK. PH1-010 *is* the demo — the operator runs it on
GB10 with Open WebUI, captures evidence, writes the RESULTS file. Keeping it deferred is
consistent with the demo plan. The cheap in-repo dependency rewrite (below) lets the
autobuild finish everything that can be automated; the operator does PH1-010 manually as
planned.

**Recommended decision:** **[I]mplement** — one tiny in-repo fix to unblock the run, and one
upstream GuardKit fix to durably correct the `deferred`-as-satisfied semantics. Re-run with
`--resume`, not `--fresh`.

---

## Confirmed Findings

### Finding 1 — Orchestrator semantics gap (PRIMARY)

**Evidence:** [feature_orchestrator.py:3429-3433](/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py#L3429-L3433) (predicate); contrast [feature_orchestrator.py:3461-3466](/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py#L3461-L3466) (writer that explicitly preserves "deferred"); crash trace at log line 2079-2087.

The dependency check requires `status == "completed"` and offers no soft-vs-hard distinction.
TASK-FPTC-003 (`operator_handoff` short-circuit) added a new terminal state without updating
this predicate. The crash is mechanical: `not self._dependencies_satisfied(...)` → raise.

The contract is internally inconsistent: TASK-FPTC-003's docstring says `deferred` is
"terminal-but-not-failed" and the persistence path stores it as such, but the dispatcher
treats `!= "completed"` as failure-equivalent.

### Finding 2 — Deferral was correct, not a heuristic over-fire

**Evidence:** [TASK-NATS-PH1-010-e2e-demo-gate.md](../../tasks/backlog/nats-fleet-integration/TASK-NATS-PH1-010-e2e-demo-gate.md) line 5: `task_type: operator_handoff`; orchestrator probe at [feature_orchestrator.py:3303-3340](/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py#L3303-L3340) reads the task frontmatter directly (no complexity heuristic involved).

The skip is sourced from explicit task-author intent in the frontmatter, not from a
complexity-or-keyword heuristic. The task's acceptance criteria (AC-PH1-010-1..5) are
explicit about needing live GB10, browser-driven Open WebUI interaction, wire-tap evidence,
and a hand-written RESULTS file — none of which the Player↔Coach loop can satisfy.

**Implication:** "un-defer PH1-010 and let autobuild run it" is **not** a viable remediation.
Keep it deferred.

### Finding 3 — In-repo `dependencies` mis-encoding (CONTRIBUTING)

**Evidence:** PH2-001's [task file](../../tasks/backlog/nats-fleet-integration/TASK-NATS-PH2-001-readiness-gating.md) only references `command_router.py` (PH1-004) and the adapter's `_ready` event (PH1-005); PH2-003 [task file](../../tasks/backlog/nats-fleet-integration/TASK-NATS-PH2-003-stale-registry-runbook.md) is pure documentation with no code touchpoints.

Both feature-yaml entries declare `dependencies: [TASK-NATS-PH1-010]`, but neither task
description references any code, contract, or artefact that PH1-010 produces. The feature
author appears to have used the dependency edge as a soft "do this after the demo gate
clears" hint — perfectly reasonable as a hint, but the orchestrator has no hint-vs-hard
distinction.

**Implication:** the cheapest path to unblock FEAT-39E1 is to drop these two spurious
hard-dep edges from the feature yaml.

### Finding 4 — Blast radius

| Wave | Task | Status | Impact |
|------|------|--------|--------|
| 8 | TASK-NATS-PH2-001 | pending, blocked | Real reason: `dependencies=[PH1-010]` is spurious. Direct mode, ~33 min. |
| 8 | TASK-NATS-PH2-003 | pending, blocked | Real reason: spurious dep. Direct mode, ~22 min. |
| 8 | TASK-NATS-PH3-004 | pending, NOT blocked by deps | Collateral: orchestrator raises *before* dispatching the wave at all. Direct mode, ~50 min. |
| 9 | TASK-NATS-PH3-005 | pending, transitively blocked | Depends on PH3-002 (✓) + PH3-004 (blocked). Task-work, ~256 min. |

`TASK-NATS-PH3-004` is the most galling — it has no PH1-010 link at all but is a casualty of
the wave-level crash semantics: the resolver checks every task in a wave before dispatching
any of them, then raises on the first unsatisfied one ([feature_orchestrator.py:2055-2061](/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py#L2055-L2061)).

### Finding 5 — Run-2 success picture (validates run-1 fixes)

| Wave | Tasks | Result |
|------|-------|--------|
| 1-2 | PH1-001, 002, 003, 007 | ✓ skipped (resume) |
| 3 | PH1-006 | ✓ approved (4 turns) — run-1 blocker, TASK-NATS-FIX-001 worked |
| 4 | PH1-004 | ✓ approved (1 turn) |
| 5 | PH1-005 | ✓ approved (2 turns) |
| 6 | PH1-008, 009, PH2-002, PH3-001 | ✓ all approved (1 turn each, parallel: 4) — no contention false positives |
| 7 | PH1-010 deferred; PH3-002, PH3-003 | ✓ approved (1 turn each) — operator_handoff skip behaved correctly within the wave |
| 8 | (PH2-001, PH2-003, PH3-004) | ❌ DependencyError before dispatch |

Run-2 is in fact mostly a success story for TASK-REV-CC40's remediation plan: the BDD-oracle
rescoping, the parallel_contention classifier fix, and the conditional_approval predicate
loosening all worked. The run-2 failure is a *new* root cause, not a regression.

---

## Decisions

### Decision 1 — Orchestrator behaviour (upstream GuardKit): **propagate `deferred` as satisfied with a warning**

Of the four options framed in the task:

- **(a) crash** — the current broken behaviour. Reject.
- **(b) propagate `deferred` to dependents and continue** — but `_update_feature` already
  marks dependents `pending`, not `deferred`. Reframed: treat `deferred` as a satisfied
  predecessor in the resolver, log a warning, let dependents run on their own merits.
- **(c) honour the skip and run dependents anyway with a warning** — operationally identical
  to (b) above.
- **(d) feature yaml schema gains soft-vs-hard dep distinction** — richer fix, but YAGNI for
  the demo and adds a schema migration burden across every existing feature spec.

**Pick: (b) ≡ (c) — `_dependencies_satisfied` accepts `status in {"completed", "deferred"}`,
emit `logger.warning(...)` when a dependent proceeds against a deferred predecessor.**

Rationale:
- It completes the contract TASK-FPTC-003 started (`deferred` as terminal-but-not-failed).
- One-line change plus a unit test.
- The warning is the operator's signal to manually verify the dependent's premise still
  holds. For PH2-001 (readiness gating) and PH2-003 (stale-registry runbook), it does.
- (d) can come later if a real case ever emerges where a dependent genuinely needs PH1-010's
  *artefacts*. None exists in FEAT-39E1.

### Decision 2 — Feature-yaml in-repo workaround: **YES, drop PH1-010 from PH2-001 & PH2-003**

Both edges are spurious — neither task touches anything PH1-010 produces. PH2-001's real
prereqs (PH1-004, PH1-005) are already completed. PH2-003 is documentation.

This unblocks the autobuild today, independent of the upstream fix. After the upstream fix
ships the edges could be re-added with confidence, but there's no reason to: they were
mis-encoded in the first place.

Edit `.guardkit/features/FEAT-39E1.yaml`:
- PH2-001 `dependencies: [TASK-NATS-PH1-010]` → `dependencies: [TASK-NATS-PH1-005]`
  (real code dep on the adapter's `_ready` event).
- PH2-003 `dependencies: [TASK-NATS-PH1-010]` → `dependencies: []` (documentation).

Mirror the change in each task file's frontmatter `dependencies:` list to keep the two
sources of truth aligned, and add a one-liner in each task's Implementation notes pointing
at this review.

### Decision 3 — Should PH1-010 actually be deferred? **YES, keep deferred**

PH1-010's acceptance criteria require:
- Live NATS server + llama-swap + jarvis container + study-tutor process on GB10 (AC-1).
- Browser-driven Open WebUI session with 3+ user turns (AC-1).
- Wire-tap inspection of `agents.command.>` and `agents.result.>` for envelope correctness (AC-2).
- jarvis routing-history trace inspection (AC-3).
- Graphiti `SessionCompletedEpisode` verification (AC-4).
- Hand-written `RESULTS-FEAT-NATS-001-phase-1-demo-{date}.md` mirroring the jarvis runbook (AC-5).

The Player↔Coach loop has no GB10 access, no browser, no NATS server, no jarvis. Even a
loosened "best-effort" attempt would invent evidence rather than verify it. The `task_type:
operator_handoff` annotation is correctly applied.

### Decision 4 — Demo readiness (2026-05-11): **ON TRACK after in-repo fix**

PH1-010 *is* the demo. The operator runs it on demo day, captures the evidence, and writes
the RESULTS file. The autobuild's job is to land the deployment artefacts the operator needs
on GB10 — Dockerfile (PH3-001 ✓), docker-compose (PH3-002 ✓), build script (PH3-003 ✓),
runbook (PH3-004, blocked → unblocks with the dep rewrite), GB10 E2E smoke (PH3-005, blocked
→ unblocks).

**Open question to flag (out of scope for this review):** PH3-005 ("GB10 E2E smoke test",
complexity 8, ~256 min) may itself need to become `task_type: operator_handoff` if it
genuinely requires live GB10. Its task description should be checked when it next dispatches;
if so, re-classify and skip cleanly. Note for the operator, not a blocker for re-run.

---

## Remediation Plan

### In-repo (TODAY — unblocks the autobuild re-run)

#### TASK-NATS-FIX-003: Rewrite spurious PH1-010 dependencies in feature yaml

- **Mode:** direct, complexity 1, ~10 min, single file primarily.
- **Files:**
  - `.guardkit/features/FEAT-39E1.yaml` (lines 209-211 for PH2-001; lines 243-244 for PH2-003).
  - `tasks/backlog/nats-fleet-integration/TASK-NATS-PH2-001-readiness-gating.md` frontmatter `dependencies:` list.
  - `tasks/backlog/nats-fleet-integration/TASK-NATS-PH2-003-stale-registry-runbook.md` frontmatter `dependencies:` list.
- **Changes:**
  - PH2-001 `dependencies: [TASK-NATS-PH1-010]` → `dependencies: [TASK-NATS-PH1-005]`.
  - PH2-003 `dependencies: [TASK-NATS-PH1-010]` → `dependencies: []`.
- **Note added to each task file's Implementation notes:** "Dependency on PH1-010 (operator_handoff demo gate) was a temporal/soft ordering hint, not a code dependency. Removed per [TASK-REV-D509](../../TASK-REV-D509-analyse-feat-39e1-autobuild-run-2-failure.md). Real code dep is …"
- **Acceptance:** `python -c "import yaml; yaml.safe_load(open('.guardkit/features/FEAT-39E1.yaml'))"` parses; `grep -n PH1-010 .guardkit/features/FEAT-39E1.yaml` shows the PH1-010 task entry only, no longer in any dependents' lists.

### Upstream GuardKit (durable, can land in parallel)

#### TASK-FIX-DEFD: Treat `deferred` as a satisfied dependency in wave dispatch

> Lives in the **guardkit** repo (not study-tutor):
> `~/Projects/appmilla_github/guardkit/tasks/backlog/TASK-FIX-DEFD-treat-deferred-as-satisfied-in-dependency-resolver.md`

- **Repo:** [appmilla_github/guardkit](/Users/richardwoollcott/Projects/appmilla_github/guardkit)
- **Mode:** task-work, complexity 2, ~30 min.
- **Files:**
  - `guardkit/orchestrator/feature_orchestrator.py` — `_dependencies_satisfied` (line 3409).
  - `tests/orchestrator/test_feature_orchestrator_dependencies.py` (or wherever the existing predicate tests live).
- **Change:**
  ```python
  TERMINAL_SATISFIED = frozenset({"completed", "deferred"})

  def _dependencies_satisfied(self, task, feature) -> bool:
      for dep_id in task.dependencies:
          dep_task = FeatureLoader.find_task(feature, dep_id)
          if dep_task is None:
              continue  # unchanged behaviour
          if dep_task.status not in TERMINAL_SATISFIED:
              return False
          if dep_task.status == "deferred":
              logger.warning(
                  "[%s] Proceeding against deferred predecessor [%s] "
                  "(reason=%r). Dependent task assumes the deferred "
                  "predecessor's artefacts are not load-bearing for its "
                  "own scope.",
                  task.id, dep_id, getattr(dep_task.result, "deferred_reason", None),
              )
      return True
  ```
- **Tests:**
  - Predecessor `status="deferred"` → dependent dispatches; `WARNING` log emitted with task IDs and reason.
  - Predecessor `status="completed"` → dependent dispatches silently (no regression).
  - Predecessor `status="failed"` → dependent blocked (no regression).
  - Predecessor `status="pending"` → dependent blocked (no regression).
- **Reference TASK-FPTC-003** in the change rationale: this completes the contract that task introduced.

### Re-run command and expected behaviour

```bash
guardkit autobuild feature FEAT-39E1 --resume
```

After TASK-NATS-FIX-003 lands (TASK-FIX-DEFD is *not* required for re-run; it's the
durable fix for the next FEAT in this situation):

| Wave | Tasks | Expected |
|------|-------|----------|
| 1-7 | (all) | Skipped via checkpoint — already terminal in feature yaml. |
| 8 | PH2-001 (direct), PH2-003 (direct), PH3-004 (task-work) | Dispatch in parallel: 3. PH2-001 & PH2-003 deps now satisfied (PH1-005 ✓ / none). PH3-004 deps already satisfied (PH3-002 ✓). |
| 9 | PH3-005 (task-work, complexity 8, ~256 min) | Deps PH3-002 ✓ + PH3-004 (Wave 8) → dispatches. **Operator must verify** PH3-005 doesn't need to be re-classified `operator_handoff` first; if it does, defer it and that wave completes with one deferral. |

**Success criterion:** `feature.execution.tasks_failed == 0`, `feature.status` lands in a
terminal state (`completed` or, if PH3-005 also gets deferred, the existing
"completed-with-deferrals" equivalent), PH1-010 stays `deferred` for operator follow-up.

**PH1-010 path to closure:** operator runs the demo on GB10 against the deployed artefacts,
captures evidence under `docs/runbooks/evidence/feat-nats-001/`, writes
`RESULTS-FEAT-NATS-001-phase-1-demo-2026-05-11.md`, then `/task-complete TASK-NATS-PH1-010`.

---

## Decision Matrix

| Option | What it does | Effort | Time-to-unblock | Risk | Recommend |
|--------|--------------|--------|-----------------|------|-----------|
| **(A) In-repo dep rewrite (TASK-NATS-FIX-003)** | Drop spurious PH1-010 edges in FEAT-39E1.yaml + task frontmatter | ~10 min | immediate after merge | very low — both edges were mis-encoded; restoring them later costs nothing | ✅ **DO** |
| **(B) Upstream `deferred`-satisfies fix (TASK-FIX-DEFD, in guardkit repo)** | One-line predicate change + unit test in guardkit repo | ~30 min | doesn't unblock this run, prevents the next | low — adds a permissive case + warning, doesn't tighten anything | ✅ **DO** (parallel, post-demo OK) |
| **(C) Un-defer PH1-010** | Strip `task_type: operator_handoff` and let autobuild attempt it | minutes | (would crash differently — no GB10) | high — Player↔Coach has no GB10 access; would invent evidence | ❌ reject |
| **(D) Schema gains soft/hard dep distinction** | Add `dependency_type: hard\|soft` to feature yaml schema | hours-days | doesn't unblock this run | medium — schema migration touches every existing feature | ❌ reject for now (YAGNI) |
| **(E) Wait for operator to run PH1-010 first, then `--resume`** | Don't fix the orchestrator; demo first, `--resume` afterwards | demo-day | 2 days | medium — leaves an outstanding upstream bug; does nothing for PH3-005 collateral | ❌ reject |

---

## Re-run Readiness Checklist

After TASK-NATS-FIX-003 lands:

- [ ] `.guardkit/features/FEAT-39E1.yaml` parses; PH1-010 appears only as a task entry, not in any other task's `dependencies` list.
- [ ] PH2-001 task file frontmatter `dependencies` aligns with feature yaml.
- [ ] PH2-003 task file frontmatter `dependencies` aligns with feature yaml.
- [ ] `guardkit autobuild feature FEAT-39E1 --resume` runs Waves 1-7 as no-ops, dispatches Wave 8.
- [ ] Wave 8 produces 3 approvals (or 2 + 1 deferral if PH3-004's runbook scope picks up PH1-010 evidence requirements — review during dispatch).
- [ ] Wave 9 dispatches PH3-005; operator decides on `operator_handoff` re-classification at that point.
- [ ] Operator runs PH1-010 on 2026-05-11 against the deployed artefacts and writes the RESULTS file.

## Out of Scope (for follow-up, not blockers)

- **PH3-005 task type re-classification:** the GB10 E2E smoke is complexity 8 and likely
  needs live hardware. Decide at dispatch.
- **Feature spec authoring guidance:** "use `dependencies:` only for code/artefact prereqs,
  not for temporal hints" — worth a one-paragraph note in the GuardKit docs once
  TASK-FIX-DEFD lands.
- **Re-litigating run-1 root causes:** covered in TASK-REV-CC40, all four addressed.

## Appendix — Cross-references

- Crash trace: log line 2079-2087 in [docs/history/autobuild-FEAT-39E1-fail-run-2.md](../../docs/history/autobuild-FEAT-39E1-fail-run-2.md).
- Operator-handoff skip log: lines 1804-1810 (same file).
- Wave 7 success: lines 2065-2073 (same file).
- TASK-FPTC-003 short-circuit code: [feature_orchestrator.py:3303-3407](/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py#L3303-L3407).
- Dependency predicate: [feature_orchestrator.py:3409-3433](/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py#L3409-L3433).
- Wave dispatch dep check: [feature_orchestrator.py:2055-2061](/Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py#L2055-L2061).
- Prior review (run-1): [TASK-REV-CC40](../../tasks/backlog/TASK-REV-CC40-analyse-feat-39e1-autobuild-failure.md), [report](TASK-REV-CC40-review-report.md).
