# FEAT-SMP-003 — Durable Cross-Device Sessions

Durable, student-keyed, resumable study sessions over the study-tutor Postgres StudentStore, with session-end
learner-state persistence moved off Graphiti onto Postgres ([ADR-ARCH-023](../../../docs/architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md) D2, [cross-device session contract](../../../docs/design/contracts/API-session-cross-device.md) — Accepted via G-CON). Fills the 6 `PostgresStudentStore` session methods, wires the already-built `SessionService` into both MCP adapter sites, and swaps the 4 MCP tools onto it with the MCP + NATS surface byte-for-byte unchanged. Builds on W1 (writes) + W2 (reads).

- **Spec:** [features/durable-cross-device-sessions/](../../../features/durable-cross-device-sessions/) (22 BDD scenarios, 3 open low-confidence assumptions)
- **Guide:** [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) (data-flow/sequence/dependency diagrams, §4 contracts, test strategy)
- **Feature file:** `.guardkit/features/FEAT-SMP-003.yaml`
- **Unblocked by G-CON** (ratified `22791af`).

## Tasks

| ID | Title | Wave | Mode | cx | Deps |
|---|---|---|---|---|---|
| TASK-SMP3-01 | `create_session` (resume txn) + `get_session` | 1 | task-work | 5 | — |
| TASK-SMP3-02 | `list_sessions` + `get_turns` | 2 | task-work | 4 | 01 |
| TASK-SMP3-03 | `append_turn` (atomic bump) + `end_session` | 3 | task-work | 5 | 02 |
| TASK-SMP3-04 | Config single-user identity + `build_session_service()` wiring (both `main.py` sites) | 4 | task-work | 4 | 03 |
| TASK-SMP3-05 | Session-end completion producer (port `Phase1MinimalDeltaPolicy` over W2 reads) | 5 | task-work | 5 | 04 |
| TASK-SMP3-06 | MCP adapter cutover — swap 4 tools onto `SessionService` (surface unchanged) | 6 | task-work | 6 | 05 |
| TASK-SMP3-07 | BDD steps + fake/ephemeral-PG integration + surface regression | 7 | task-work | 6 | 06 |

**Waves (serialized — one task per wave):** `[01]→[02]→[03]→[04]→[05]→[06]→[07]`

## Run

```bash
/task-work TASK-SMP3-01        # or, for autonomous multi-task build:
/feature-build FEAT-SMP-003
# Before autobuild: export STUDY_TUTOR_PG_DSN=<ephemeral throwaway PG, non-5434 port>
```
