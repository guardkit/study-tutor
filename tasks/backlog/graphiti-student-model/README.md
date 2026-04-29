# FEAT-1773: Graphiti Student Model

**Phase 1 — FEAT-PH1-001**
**Generated from:** [TASK-REV-7DC0](../../in_review/TASK-REV-7DC0-plan-graphiti-student-model.md)

A persistent knowledge-graph-backed student model. Learner profile, three core query helpers,
async fire-and-forget write-back at every Graphiti write site, and a one-off seeding script.

## Quick Reference

- **Total subtasks:** 6
- **Aggregate effort:** 9.5h work / ~7.5h elapsed (with parallelism)
- **Aggregate complexity:** 6/10
- **Wave count:** 4 (Wave 1 + 2 parallel; Wave 3 + 4 sequential)

## Subtasks

| # | ID | Title | Wave | Type | Mode | Complexity |
|---|----|-------|------|------|------|------------|
| 1 | [TASK-GSM-001](TASK-GSM-001-pydantic-entities-relationships.md) | Define Pydantic entities and relationships | 1 | declarative | direct | 3 |
| 2 | [TASK-GSM-002](TASK-GSM-002-episode-types.md) | Define Pydantic episode types | 1 | declarative | direct | 2 |
| 3 | [TASK-GSM-003](TASK-GSM-003-graphiti-client-wrapper.md) | Implement Graphiti client wrapper (lazy import + degradation) | 2 | feature | task-work | 4 |
| 4 | [TASK-GSM-004](TASK-GSM-004-async-write-back-helper.md) | Implement shared async fire-and-forget Graphiti write helper | 2 | feature | task-work | 6 |
| 5 | [TASK-GSM-005](TASK-GSM-005-query-helpers.md) | Implement student-model query helpers | 3 | feature | task-work | 5 |
| 6 | [TASK-GSM-006](TASK-GSM-006-seeding-script.md) | Write Lilymay baseline seeding script | 4 | scaffolding | direct | 3 |

## Architectural Anchors

- **ADR-ARCH-019** — fire-and-forget Graphiti write-back at every write point
- **DDR-002** — Coach AsyncSubAgent owns its own writes; single shared helper
- **DDR-003** — `session.completed` emits on state transition, not on write success
- **CC-13** — every Graphiti write site fire-and-forget (cross-cutting concern)
- **LES1 §3** — graceful module load when graphiti-core absent

## Documents in this folder

- [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) — full design with §4 contracts, data flow, sequence, and dependency diagrams
- 6 task markdown files (above)

## Execution

Wave-by-wave. Conductor recommended for Waves 1 and 2.

```
Wave 1 (parallel):  TASK-GSM-001 + TASK-GSM-002
Wave 2 (parallel):  TASK-GSM-003 + TASK-GSM-004
Wave 3 (single):    TASK-GSM-005
Wave 4 (single):    TASK-GSM-006  ← seeds Lilymay's baseline; integration gate for the feature
```

Once Wave 4 succeeds and `get_student_state(client, "lilymay")` returns the seeded baseline,
FEAT-1773 is functionally complete and unblocks FEAT-PH1-002 (planner) and FEAT-PH1-003
(Player-Coach loop).
