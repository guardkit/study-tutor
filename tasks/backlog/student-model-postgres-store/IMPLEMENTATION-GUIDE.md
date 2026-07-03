# Implementation Guide — FEAT-SMP-001: Student Model Postgres Store (Wave W1)

**Feature:** `FEAT-SMP-001` · **Spec:** [student-model-postgres-store.feature](../../../features/student-model-postgres-store/student-model-postgres-store.feature) (28 scenarios) · **ADR:** [ADR-ARCH-023](../../../docs/architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md)

## Scope

W1 fills the **write path** of `PostgresStudentStore` — `ping()`, `record_session_completion`, `record_misconception` (F1), `apply_confidence_update` (F2) — plus the **first Alembic migration** encoding `schema_reference.sql`. Stack: **SQLAlchemy 2.0 async Core + asyncpg + Alembic**.

**Out of scope (later waves, leave `NotImplementedError`):** reads `get_student_state`/`get_topic_confidences`/`get_recent_misconceptions` → **FEAT-SMP-002**; session CRUD `create_session`/`get_session`/`list_sessions`/`append_turn`/`get_turns`/`end_session` → **FEAT-SMP-003** (gated by G-CON); the XP/streak/level/achievement/quest engine → **Phase 2**.

**Two conflicts already resolved in code/schema (build on them):** confidence bands = **40/60/80** (`confidence_band_for`); **`session.xp_awarded`** column added to `schema_reference.sql`.

## §1: Data Flow — Read/Write Paths

```mermaid
flowchart LR
    subgraph Writes["Write Paths (W1)"]
        W1["apply_confidence_update() F2"]
        W2["record_misconception() F1"]
        W3["record_session_completion()<br/>(one transaction)"]
    end
    subgraph Storage["Postgres (JSONB, no pgvector)"]
        S1[("topic_confidence")]
        S2[("misconception")]
        S3[("session<br/>(incl xp_awarded)")]
    end
    subgraph Reads["Read Paths"]
        R1["get_topic_confidences() / get_student_state()"]
        R2["get_recent_misconceptions()"]
    end

    W1 -->|"upsert (band via confidence_band_for)"| S1
    W2 -->|"insert (append-only)"| S2
    W3 -->|"upsert session + confidence + misconception"| S3
    W3 -->|"reuses F2"| S1
    W3 -->|"reuses F1"| S2

    S1 -.->|"FEAT-SMP-002 (not W1)"| R1
    S2 -.->|"FEAT-SMP-002 (not W1)"| R2
    style R1 fill:#fde,stroke:#999,stroke-dasharray:4
    style R2 fill:#fde,stroke:#999,stroke-dasharray:4
```

**Disconnection note (acknowledged, not a defect):** the read paths (`R1`, `R2`) are dotted because they are **deliberately deferred to FEAT-SMP-002** — the write path is W1's whole deliverable. This is a planned wave boundary, not a wiring bug. No action required in W1.

## §2: Integration Contract — session-end write sequence

```mermaid
sequenceDiagram
    participant H as Session-end handler
    participant St as PostgresStudentStore
    participant Tx as Postgres (single txn)

    H->>St: record_session_completion(session_id, xp_awarded, confidence_updates[], misconceptions[])
    St->>Tx: BEGIN
    St->>Tx: upsert session (session_id PK) status=ended, xp_awarded, aos_scaffolded
    loop each ConfidenceUpdate
        St->>Tx: upsert topic_confidence (band=confidence_band_for(pct))
    end
    loop each Misconception
        St->>Tx: insert misconception
    end
    alt all succeed
        St->>Tx: COMMIT
        St-->>H: None (durably persisted)
    else any failure (bad pct / mid-write error / conn drop)
        St->>Tx: ROLLBACK
        St-->>H: raises (synchronous failure surfaces — ASSUM-008)
    end
    Note over H,Tx: Idempotent on session_id — a replay upserts the same rows, XP counted once.
```

## §3: Task Dependency Graph

```mermaid
graph TD
    T1["TASK-SMP-01<br/>deps + Alembic scaffold<br/>(scaffolding, cx3)"] --> T2["TASK-SMP-02<br/>first migration → G7<br/>(feature, cx5)"]
    T1 --> T3["TASK-SMP-03<br/>engine + DI + ping()<br/>(feature, cx4)"]
    T2 --> T4["TASK-SMP-04<br/>apply_confidence_update F2<br/>(feature, cx4)"]
    T3 --> T4
    T2 --> T5["TASK-SMP-05<br/>record_misconception F1<br/>(feature, cx4)"]
    T3 --> T5
    T4 --> T6["TASK-SMP-06<br/>record_session_completion<br/>(feature, cx6)"]
    T5 --> T6
    T6 --> T7["TASK-SMP-07<br/>BDD steps + fake + integration<br/>(testing, cx6)"]
    style T2 fill:#cfc,stroke:#090
    style T3 fill:#cfc,stroke:#090
    style T4 fill:#cfc,stroke:#090
    style T5 fill:#cfc,stroke:#090
```

_Green = parallel-safe within a wave._ **Waves:** W1 `[01]` → W2 `[02, 03]` → W3 `[04, 05]` → W4 `[06]` → W5 `[07]`.

## §4: Integration Contracts

### Contract: STUDY_TUTOR_PG_DSN
- **Producer:** W0 runbook / deploy (`.env` → `STUDY_TUTOR_PG_DSN`), consumed by the async engine set up in `TASK-SMP-01`.
- **Consumer task(s):** `TASK-SMP-02` (Alembic env.py), `TASK-SMP-03` (`create_async_engine`), transitively `TASK-SMP-04/05/06/07`.
- **Artifact type:** environment variable (connection URL).
- **Format constraint:** `postgresql+asyncpg://user:pass@host:port/study_tutor` — the **`+asyncpg`** dialect suffix is required by SQLAlchemy's async engine and by Alembic's async `env.py`. (Note: the app-facing DSN written in W0 is `postgresql://…`; the SQLAlchemy layer must add/normalise the `+asyncpg` dialect.)
- **Validation method:** Coach verifies the engine/Alembic construction asserts a `postgresql+asyncpg://` URL; seam tests in SMP-02/03 assert the dialect.

## Assumptions carried into tasks (3 low-confidence, still open)

| Assumption | Decision | Task |
|---|---|---|
| ASSUM-003 | Write for an unknown learner is **rejected** (FK) | SMP-04/05/06 |
| ASSUM-005 | Prompt-injection rejection **dropped** (no LLM) | SMP-05 |
| ASSUM-006 | `record_misconception` (F1) is **append-only, no dedup** | SMP-05 |

## Test strategy

- **Adapter (SQL/transaction) behaviour** → integration tests against an **ephemeral Postgres** (testcontainers or a throwaway local container on a **non-5434** port). **Never** the NAS durable instance (runbook scope rule); a guard test asserts no test targets host `whitestocks`/port `5434`.
- **Caller behaviour** → an **in-memory fake `StudentStore`** (implements the full Protocol).
- **Runbook gate G7** = `alembic upgrade head` applies clean (TASK-SMP-02).
- The 28 BDD scenarios are wired to tasks via `@task:` tags (feature-plan Step 11); the write-path subset is W1's oracle.

## Next after W1

`STUDY_TUTOR_PG_DSN` is already set in `.env` (W0). After W1's G7 is green against the durable instance, proceed to **FEAT-SMP-002** (reads) — not gated by G-CON.
