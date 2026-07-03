# Implementation Guide — FEAT-SMP-002: Student Model Postgres Store (Wave W2 · Reads)

**Feature:** `FEAT-SMP-002` · **Spec:** [student-model-postgres-store-reads.feature](../../../features/student-model-postgres-store-reads/student-model-postgres-store-reads.feature) (19 scenarios) · **ADR:** [ADR-ARCH-023](../../../docs/architecture/decisions/ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md) · **Builds on:** FEAT-SMP-001 (write path, merged `efe4fb0`)

## Scope

W2 fills the **read path** of `PostgresStudentStore` — `get_topic_confidences`,
`get_recent_misconceptions`, `get_student_state` — over the merged W1 schema, resolved behind the
existing `knowledge.store.reads` helpers; **wires the store into the serve boot** (conditional on
`STUDY_TUTOR_PG_DSN`); **repoints the planner** off the retired Graphiti read; and **removes the
Graphiti read copies** from `queries.py`. Preserves graceful degradation throughout.

**Out of scope (later):** the graph WRITE-path removal (`record_topic_confidence_update`, the
fire-and-forget `record_session_completion`) → **FEAT-SMP-004**; session CRUD → **FEAT-SMP-003**
(gated by G-CON); the graph seed-script's Postgres counterpart.

**Three decisions resolved in spec review (build on them):** band-at-observation is approximated
from the current band (ASSUM-003); the store is wired conditionally at startup (ASSUM-007);
`most_recent_session_id` reads from the `session` table and the stale flag is retired (ASSUM-004/005).

## §1: Data Flow — Read/Write Paths (the most important diagram)

```mermaid
flowchart LR
    subgraph Writes["Write Paths (W1 — merged)"]
        W1["apply_confidence_update()"]
        W2["record_misconception()"]
        W3["record_session_completion()"]
    end
    subgraph Storage["Postgres (JSONB, no pgvector)"]
        S1[("topic_confidence")]
        S2[("misconception")]
        S3[("session")]
    end
    subgraph Reads["Read Paths (W2 — this feature)"]
        A1["get_topic_confidences()<br/>(SMP2-01)"]
        A2["get_recent_misconceptions()<br/>(SMP2-02, band-at-obs join)"]
        A3["get_student_state()<br/>(SMP2-03)"]
    end
    subgraph Callers["Callers"]
        P["planner/pipeline.py<br/>_build_planner_context (SMP2-05)"]
        RD["store.reads.load_planner_inputs<br/>+ get_student_state"]
        PROV["provider.get_student_store()<br/>wired at serve boot (SMP2-04)"]
    end

    W1 -->|upsert| S1
    W2 -->|insert| S2
    W3 -->|txn| S1
    W3 -->|txn| S2
    W3 -->|txn| S3

    S1 -->|SELECT| A1
    S1 -->|LEFT JOIN band| A2
    S2 -->|window filter| A2
    S1 --> A3
    S2 --> A3
    S3 -->|latest by last_activity| A3

    A1 --> RD
    A2 --> RD
    A3 --> RD
    PROV -.->|resolves| RD
    RD --> P

    style A1 fill:#cfc,stroke:#090
    style A2 fill:#cfc,stroke:#090
    style A3 fill:#cfc,stroke:#090
    style PROV fill:#ffd,stroke:#c90
```

**Disconnection resolved (this feature's whole point):** before W2, the store read paths (`A1–A3`)
raised `NotImplementedError`, `store.reads` was dead code with no importer, and the provider was
never wired at startup — the planner read the (empty) Graphiti path. W2 connects all three:
adapter methods (SMP2-01/02/03) → `store.reads` → planner (SMP2-05), with the provider wired
conditionally at boot (SMP2-04). **No write path is left without a read after this feature.**

## §2: Integration Contract — the planner read sequence (repoint)

```mermaid
sequenceDiagram
    participant P as pipeline._build_planner_context
    participant R as store.reads.load_planner_inputs
    participant Pr as provider.get_student_store
    participant St as PostgresStudentStore
    participant PG as Postgres

    P->>R: await load_planner_inputs(student_id)  [inner asyncio.wait_for timeout]
    R->>Pr: get_student_store()
    alt store wired (DSN set at boot)
        Pr-->>R: PostgresStudentStore
        R->>St: get_topic_confidences(sid)
        St->>PG: SELECT topic_confidence
        R->>St: get_recent_misconceptions(sid, window_days=30)
        St->>PG: SELECT misconception LEFT JOIN topic_confidence
        St-->>R: domain entities
        R-->>P: PlannerInputs(confidences, misconceptions, available=True)
    else no store wired OR read raises OR timeout
        Pr-->>R: None (or exception)
        R-->>P: PlannerInputs([], [], available=False)
    end
    P->>P: PlannerContext.create(... learner_state_available)
    Note over P,PG: No snapshot projection — load_planner_inputs returns domain entities directly.<br/>Graceful degradation preserved: caller never sees an exception.
```

## §3: Task Dependency Graph (serialized — one task per wave)

```mermaid
graph TD
    T1["SMP2-01<br/>get_topic_confidences<br/>(feature, cx4)"] --> T2["SMP2-02<br/>get_recent_misconceptions<br/>(feature, cx5)"]
    T2 --> T3["SMP2-03<br/>get_student_state<br/>(feature, cx6)"]
    T3 --> T4["SMP2-04<br/>conditional serve-boot wiring<br/>(feature, cx3)"]
    T4 --> T5["SMP2-05<br/>planner repoint<br/>(feature, cx6)"]
    T5 --> T6["SMP2-06<br/>remove graphiti read surface<br/>(refactor, cx6)"]
    T6 --> T7["SMP2-07<br/>BDD + fake + integration tests<br/>(testing, cx6)"]
```

_Strictly serial by design — per the [parallel-wave worktree-pollution retro](../../../docs/retros/2026-07-03-autobuild-parallel-wave-worktree-pollution.md), store/adapter tasks share `postgres.py`/`reads.py`/`queries.py`/`pipeline.py` and MUST NOT run concurrently in one worktree. Waves: `[01]→[02]→[03]→[04]→[05]→[06]→[07]`._

## §4: Integration Contracts

### Contract: STUDY_TUTOR_PG_DSN
- **Producer:** W0 deploy (`.env` → `STUDY_TUTOR_PG_DSN`); read by `build_student_store()` (SMP2-04) and the store engine.
- **Consumer task(s):** SMP2-04 (boot wiring guard), transitively SMP2-01/02/03 (the engine), SMP2-07 (ephemeral PG).
- **Artifact type:** environment variable (connection URL).
- **Format constraint:** `postgresql+asyncpg://user:pass@host:port/study_tutor` — the store coerces a plain `postgresql://` to the `+asyncpg` dialect internally (W1). The boot guard uses `os.environ.get(...)` (truthy), never `os.environ[...]`.
- **Validation method:** SMP2-04 test asserts `build_student_store()` is called iff the env var is set; SMP2-07 runs the reads against an ephemeral PG on a non-5434 port.

### Contract: PlannerInputs (in-process API, reads.py → pipeline.py)
- **Producer:** `store.reads.load_planner_inputs` (SMP2-02/03 feed it via the adapter).
- **Consumer:** `planner/pipeline.py:_build_planner_context` (SMP2-05).
- **Artifact type:** Python dataclass `PlannerInputs(topic_confidences: list[TopicConfidence], misconceptions: list[Misconception], learner_state_available: bool)`.
- **Format constraint:** returns DOMAIN entities (not snapshots), already projected — the planner passes them straight to `PlannerContext.create` with NO `_project_*` step. `available=False` iff no store wired / read raised / (in the caller) timeout.
- **Validation method:** SMP2-05 tests assert available/unavailable distinction end-to-end; SMP2-07 exercises the wired + unreachable paths.

## Assumptions carried into tasks (3 low-confidence, still open)

| Assumption | Decision | Task |
|---|---|---|
| ASSUM-003 | `confidence_band_at_observation` approximated from current band (LEFT JOIN, default `struggling`) | SMP2-02 |
| ASSUM-007 | store wired at serve boot only when `STUDY_TUTOR_PG_DSN` set | SMP2-04 |
| ASSUM-010 | planner-only repoint; seed-script reworked, not broken, by the read-copy removal | SMP2-05, SMP2-06 |

## Test strategy

- **Adapter (SQL) behaviour** → integration tests against an **ephemeral Postgres** (throwaway container, **non-5434** port). NEVER the NAS durable instance; a guard test asserts no test targets host `whitestocks`/port `5434`.
- **Caller / degradation behaviour** → the in-memory `FakeStudentStore` (its read methods already exist) through `store.reads` + `load_planner_inputs`.
- **Composition guard (critical, per the [self-defeating-tests retro](../../../docs/retros/2026-07-03-autobuild-self-defeating-boundary-tests.md)):** SMP2-06 and SMP2-07 must run the WHOLE `pytest tests/`, not just `tests/unit` — the read-copy removal breaks stale `tests/` imports a per-task gate can't see.
- The 19 BDD scenarios are wired to tasks via `@task:` tags (feature-plan Step 11).

## AutoBuild operational checklist (READ before `guardkit autobuild`)

1. **Waves are already serialized** (one task per wave) in `.guardkit/features/FEAT-SMP-002.yaml`.
2. `export STUDY_TUTOR_PG_DSN=<ephemeral PG>` (throwaway `postgres:16` on a non-5434 port, e.g. `:55432`) before launching so the Coach's DB read tests run for real. Pre-pull `postgres:16`.
3. After it finishes, **independently** run `pytest tests/` (Coach per-task green ≠ composition green), then squash-merge only the code paths (`src/.../store/*`, `src/.../planner/pipeline.py`, `src/.../knowledge/queries.py`, `src/.../cli/main.py`, `scripts/seed_student_model.py`, `tests/**`) — not `.guardkit/`/`tasks/` churn.
4. **Do NOT** start FEAT-SMP-003 (session CRUD) — gated by G-CON.

## Next after W2

The learner read path is Postgres-backed and wired. Remaining: **FEAT-SMP-004** (delete the graph
WRITE plumbing + the graph seed path) and **FEAT-SMP-003** (session CRUD, once G-CON clears).
Operator follow-up still outstanding from W0: the nightly `pg_dump` of the NAS store is **not yet scheduled**.
