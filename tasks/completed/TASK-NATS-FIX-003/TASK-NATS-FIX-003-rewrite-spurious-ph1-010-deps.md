---
id: TASK-NATS-FIX-003
title: Rewrite spurious PH1-010 dependency edges in FEAT-39E1.yaml (unblock autobuild re-run)
task_type: fix
parent_review: TASK-REV-D509
feature_id: FEAT-39E1
implementation_mode: direct
complexity: 1
estimated_minutes: 15
status: completed
priority: critical
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T08:00:00Z
completed: 2026-05-09T08:00:00Z
completed_location: tasks/completed/TASK-NATS-FIX-003/
dependencies: []
tags:
  - nats
  - fix
  - autobuild-blocker
  - feature-yaml
  - phase-2
related_tasks:
  - TASK-REV-D509       # parent review
  - TASK-NATS-PH1-010   # the deferred operator_handoff that was treated as failure
  - TASK-NATS-PH2-001   # spurious dep removed
  - TASK-NATS-PH2-003   # spurious dep removed
  - TASK-FIX-DEFD       # upstream guardkit fix (independent, not blocking this) — lives in ~/Projects/appmilla_github/guardkit/tasks/backlog/
---

# Task: Rewrite spurious PH1-010 dependency edges in FEAT-39E1.yaml

## Description

Run-2 of the FEAT-39E1 autobuild crashed at Wave 8 dispatch with:

```
DependencyError: Task TASK-NATS-PH2-001 has unsatisfied dependencies: ['TASK-NATS-PH1-010']
```

Per [TASK-REV-D509](TASK-REV-D509-analyse-feat-39e1-autobuild-run-2-failure.md) and the
[full review](../../.claude/reviews/TASK-REV-D509-review-report.md), the root cause is a
GuardKit semantics gap (predecessor `status="deferred"` not accepted as satisfied) — but the
in-repo fix is even simpler: **PH2-001 and PH2-003 don't actually depend on PH1-010**.

- **PH2-001** ("Readiness gating in command router") modifies `command_router.py` and
  consumes `_adapter_ready` from `NATSAdapter`. Real code deps: PH1-004 (CommandRouter)
  + PH1-005 (NATSAdapter `_ready` event). PH1-010 is the operator-driven E2E demo gate;
  it produces no code or contract that PH2-001 consumes.
- **PH2-003** ("Stale registry runbook documentation") is pure documentation. The PH1-010
  edge is a temporal/soft hint, not a real ordering constraint.

Drop both edges. The autobuild can then `--resume` and finish Waves 8–9.

This is a **demo-deadline blocker** (2026-05-11). The upstream GuardKit fix
(TASK-FIX-DEFD, in `~/Projects/appmilla_github/guardkit/tasks/backlog/TASK-FIX-DEFD-treat-deferred-as-satisfied-in-dependency-resolver.md`)
is the durable correction, but is **not required** for this re-run.

## Scope

Three small edits, all in this repo:

### 1. `.guardkit/features/FEAT-39E1.yaml`

For PH2-001 (around lines 205-218):
```yaml
- id: TASK-NATS-PH2-001
  ...
  dependencies:
  - TASK-NATS-PH1-010   # <-- remove this
  + TASK-NATS-PH1-005   # <-- replace with the real code dep
```

For PH2-003 (around lines 239-252):
```yaml
- id: TASK-NATS-PH2-003
  ...
  dependencies:
  - TASK-NATS-PH1-010   # <-- remove this; documentation has no real predecessor
```
(leave the `dependencies:` list empty: `dependencies: []`)

Do NOT touch the `orchestration.parallel_groups` section — Wave 8 = `[PH2-001, PH2-003,
PH3-004]` is still the right grouping; only the dep-graph metadata changes.

### 2. `tasks/backlog/nats-fleet-integration/TASK-NATS-PH2-001-readiness-gating.md`

Frontmatter:
```yaml
dependencies:
  - TASK-NATS-PH1-010   # <-- remove
  + TASK-NATS-PH1-005   # <-- replace
```

Add a one-liner under "Implementation notes":
> Dependency on PH1-010 (operator_handoff demo gate) was a temporal/soft ordering hint, not a
> code dependency. Removed per [TASK-REV-D509](../../TASK-REV-D509-analyse-feat-39e1-autobuild-run-2-failure.md).
> Real code deps are PH1-004 (CommandRouter) and PH1-005 (NATSAdapter `_ready` event).

### 3. `tasks/backlog/nats-fleet-integration/TASK-NATS-PH2-003-stale-registry-runbook.md`

Frontmatter:
```yaml
dependencies:
  - TASK-NATS-PH1-010   # <-- remove
```
(leave `dependencies: []`)

Add a one-liner under "Implementation notes":
> Dependency on PH1-010 was a temporal hint ("don't write Phase 2 docs until Phase 1 demo
> evidence exists"), not a real ordering constraint. Removed per
> [TASK-REV-D509](../../TASK-REV-D509-analyse-feat-39e1-autobuild-run-2-failure.md).
> Pure documentation task with no code touchpoints.

## Acceptance Criteria

- [ ] `python -c "import yaml; yaml.safe_load(open('.guardkit/features/FEAT-39E1.yaml'))"` exits 0.
- [ ] `grep -n 'TASK-NATS-PH1-010' .guardkit/features/FEAT-39E1.yaml` shows the PH1-010
      task entry only — no occurrences inside any other task's `dependencies` list.
- [ ] PH2-001 task file frontmatter `dependencies:` matches feature yaml (`[TASK-NATS-PH1-005]`).
- [ ] PH2-003 task file frontmatter `dependencies:` matches feature yaml (`[]`).
- [ ] Both task files have an "Implementation notes" entry citing TASK-REV-D509.
- [ ] No other task's `dependencies` list changed.

## Verification

```bash
# Schema sanity
python -c "import yaml; f = yaml.safe_load(open('.guardkit/features/FEAT-39E1.yaml')); \
  ph2_001 = next(t for t in f['tasks'] if t['id'] == 'TASK-NATS-PH2-001'); \
  ph2_003 = next(t for t in f['tasks'] if t['id'] == 'TASK-NATS-PH2-003'); \
  assert ph2_001['dependencies'] == ['TASK-NATS-PH1-005'], ph2_001['dependencies']; \
  assert ph2_003['dependencies'] == [], ph2_003['dependencies']; \
  print('OK')"

# No stray PH1-010 deps anywhere
! grep -B1 'TASK-NATS-PH1-010' .guardkit/features/FEAT-39E1.yaml | grep -q 'dependencies'
```

## Out of Scope

- The upstream GuardKit fix — separate task TASK-FIX-DEFD, lives in `~/Projects/appmilla_github/guardkit/tasks/backlog/TASK-FIX-DEFD-treat-deferred-as-satisfied-in-dependency-resolver.md`.
- Re-running the autobuild — happens after this lands.
- Implementing PH1-010 (it's the operator-driven 2026-05-11 demo, by design).
- PH3-005 task-type re-classification — that's a separate decision at dispatch time.

## Re-run after this lands

```bash
guardkit autobuild feature FEAT-39E1 --resume
```

Expected: Waves 1-7 skip via checkpoint, Wave 8 dispatches PH2-001 + PH2-003 + PH3-004 in
parallel, Wave 9 dispatches PH3-005, PH1-010 stays `deferred` for the operator to run as the
2026-05-11 demo.
