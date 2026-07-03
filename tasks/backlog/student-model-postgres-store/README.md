# FEAT-SMP-001 — Student Model Postgres Store (Wave W1)

The write path + schema for the study-tutor-owned Postgres StudentStore that replaces the Graphiti/FalkorDB student model ([ADR-ARCH-023](../../../docs/architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md)). Fills the `PostgresStudentStore` skeleton's `ping()` + three write methods and writes the first Alembic migration. Reads (SMP-002) and session CRUD (SMP-003) are out of scope.

- **Spec:** [features/student-model-postgres-store/](../../../features/student-model-postgres-store/) (28 BDD scenarios, 3 open assumptions)
- **Guide:** [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) (diagrams, §4 contracts, test strategy)
- **Feature file:** `.guardkit/features/FEAT-SMP-001.yaml`
- **Runbook gate:** G7 (`alembic upgrade head`)

## Tasks

| ID | Title | Wave | Mode | cx | Deps |
|---|---|---|---|---|---|
| TASK-SMP-01 | Deps + async Alembic scaffolding | 1 | direct | 3 | — |
| TASK-SMP-02 | First migration (schema, G7) | 2 | task-work | 5 | 01 |
| TASK-SMP-03 | Async engine/pool + DI + `ping()` | 2 | task-work | 4 | 01 |
| TASK-SMP-04 | `apply_confidence_update` (F2) | 3 | task-work | 4 | 02, 03 |
| TASK-SMP-05 | `record_misconception` (F1) | 3 | task-work | 4 | 02, 03 |
| TASK-SMP-06 | `record_session_completion` (txn) | 4 | task-work | 6 | 04, 05 |
| TASK-SMP-07 | BDD steps + fake store + integration | 5 | task-work | 6 | 06 |

**Waves:** W1 `[01]` → W2 `[02, 03]` → W3 `[04, 05]` → W4 `[06]` → W5 `[07]`

## Run

```bash
/task-work TASK-SMP-01        # or, for autonomous multi-task build:
/feature-build FEAT-SMP-001
```
