---
id: TASK-REV-852B
title: "Plan: FEAT-VOICE-001 server voice module"
status: completed
task_type: review
priority: high
created: 2026-07-06
clarification:
  context_a:
    timestamp: 2026-07-06T00:00:00Z
    source: "pre-ratified decisions (design Accepted 2026-07-05; contract Rev 1 at G-CON; /feature-spec owner-curated 2026-07-06) — not re-asked"
    decisions:
      focus: technical+architecture
      tradeoff: quality
      concerns: "wire-seam fidelity (LPA green-but-broken defence); ephemeral-audio invariants; no scope creep into streaming (FEAT-VOICE-002)"
---

## Why this review exists

`/feature-plan "FEAT-VOICE-001 server voice module"` orchestration record.
Unlike a normal feature plan, the **approach is not open**: it is fixed by
[voice-tutor-and-reachy-design.md §5](../../docs/design/voice-tutor-and-reachy-design.md)
(Accepted), the [blueprint](../../docs/design/voice-implementation-blueprint.md) §3
port map, contract/binding **Revision 1** (frozen at G-CON, CONTRACT_SHA `574615e9…` /
BINDING_SHA `e50897d1…`), and the owner-curated BDD spec
([features/voice-server-module/](../../features/voice-server-module/voice-server-module_summary.md),
27 scenarios, 6 confirmed assumptions). This review's job is the **task
decomposition**, not an options analysis.

## Findings → decomposition

See the decision checkpoint in the session transcript; outcome recorded below.

## Outcome

**[I]mplement** chosen at checkpoint (owner, 2026-07-06). Context B: sequential
execution, standard testing depth. Created:

- `tasks/backlog/voice-server-module/` — TASK-VOX-001..007 (7 tasks, 5 waves)
  + IMPLEMENTATION-GUIDE.md (data-flow/sequence/dependency diagrams, §4
  integration contracts) + README.md
- `.guardkit/features/FEAT-VOICE-001.yaml` — validated (`guardkit feature
  validate` ✓, smoke-gates paths ✓; gate: `uv run pytest tests/unit -x -q`
  after every wave)
- Step 11 BDD linking: all **27 scenarios** tagged `@task:` (VOX-004 ×10,
  VOX-005 ×12, VOX-006 ×5, incl. the Scenario Outline), 0 below threshold
- No operator_handoff tasks (all hermetic; the live smoke is the build plan's
  W4 TASK-VOX-SMK-T, outside this feature)

Next: `/task-work TASK-VOX-001` (or `/feature-build FEAT-VOICE-001`).
