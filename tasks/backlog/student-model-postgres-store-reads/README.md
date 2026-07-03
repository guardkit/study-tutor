# FEAT-SMP-002 — Student Model Postgres Store (Wave W2 · Reads)

The read path for the study-tutor-owned Postgres StudentStore ([ADR-ARCH-023](../../../docs/architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md)). Fills the three `PostgresStudentStore` read methods over the merged W1 schema, wires the store into the serve boot (conditional on `STUDY_TUTOR_PG_DSN`), repoints the planner off the retired Graphiti read, and removes the Graphiti read copies from `queries.py`. Preserves graceful degradation throughout. Builds on FEAT-SMP-001 (write path, merged).

- **Spec:** [features/student-model-postgres-store-reads/](../../../features/student-model-postgres-store-reads/) (19 BDD scenarios, 3 open low-confidence assumptions)
- **Guide:** [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) (data-flow/sequence/dependency diagrams, §4 contracts, test strategy)
- **Feature file:** `.guardkit/features/FEAT-SMP-002.yaml`
- **Not gated by G-CON** (unlike FEAT-SMP-003, session CRUD).

## Tasks

| ID | Title | Wave | Mode | cx | Deps |
|---|---|---|---|---|---|
| TASK-SMP2-01 | `get_topic_confidences` | 1 | task-work | 4 | — |
| TASK-SMP2-02 | `get_recent_misconceptions` (+band-at-obs join) | 2 | task-work | 5 | 01 |
| TASK-SMP2-03 | `get_student_state` aggregate | 3 | task-work | 6 | 02 |
| TASK-SMP2-04 | Conditional store wiring in serve boot | 4 | task-work | 3 | 03 |
| TASK-SMP2-05 | Planner repoint → store reads | 5 | task-work | 6 | 04 |
| TASK-SMP2-06 | Remove Graphiti read surface + test/seed rework | 6 | task-work | 6 | 05 |
| TASK-SMP2-07 | BDD steps + fake/ephemeral-PG read tests | 7 | task-work | 6 | 06 |

**Waves (serialized — one task per wave, per the parallel-wave-pollution retro):** `[01]→[02]→[03]→[04]→[05]→[06]→[07]`

## Run

```bash
/task-work TASK-SMP2-01        # or, for autonomous multi-task build:
/feature-build FEAT-SMP-002
# Before autobuild: export STUDY_TUTOR_PG_DSN=<ephemeral throwaway PG, non-5434 port>
```
