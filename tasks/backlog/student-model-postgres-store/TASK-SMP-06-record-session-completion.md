---
id: TASK-SMP-06
title: "record_session_completion: single-transaction, idempotent session-end write"
task_type: feature
feature_id: FEAT-SMP-001
wave: 4
implementation_mode: task-work
complexity: 6
dependencies: [TASK-SMP-04, TASK-SMP-05]
parent_feature_spec: features/student-model-postgres-store/student-model-postgres-store_summary.md
---

# Task: record_session_completion — atomic, idempotent session-end write

## Objective

Fill the `record_session_completion` body in
`src/study_tutor/knowledge/store/postgres.py` (currently
`raise NotImplementedError`). This is the headline write of ADR-ARCH-023 D2: the
`active → ended` session-end write that persists per-session **XP**, the batch of
per-topic **confidence** updates, and observed **misconceptions** as **one**
synchronous transaction — replacing the retired 79-second fire-and-forget
`GraphitiWriteHelper` F1/F2/F3 flush points.

Exact signature (already declared in `port.py` / `postgres.py`, do not change):

```python
async def record_session_completion(
    self,
    *,
    student_id: str,
    session_id: str,
    topic: str | None,
    aos_scaffolded: list[str],
    xp_awarded: int,
    confidence_updates: list[ConfidenceUpdate],
    misconceptions: list[Misconception],
) -> None: ...
```

The three properties this method must guarantee:

- **ATOMIC** — every row (session + confidence upserts + misconception inserts)
  commits or none does; any mid-write error rolls back all of it, leaving prior
  state intact.
- **IDEMPOTENT on `session_id`** — re-running the identical completion (serially
  or concurrently) yields the same row set and does **not** double-count XP or
  duplicate child rows.
- **SYNCHRONOUS** — awaited inline; a commit failure **surfaces** to the caller
  (ASSUM-008), unlike the retired log-and-drop writer.

## Scope

### In scope
- Implement `record_session_completion` end-to-end against Postgres.
- Session-row upsert keyed on the `session_id` PK (`status='ended'`, `topic`,
  `aos_scaffolded` → JSONB, `xp_awarded` **SET**, not incremented).
- Reuse SMP-04's confidence upsert and SMP-05's misconception insert **at the
  open-connection level** so all statements share this method's single
  transaction.
- Idempotency gate that makes the append-only misconception insert (ASSUM-006)
  a no-op on replay/concurrent re-delivery — see Implementation Notes.
- Ephemeral-Postgres integration tests + the mapped BDD scenarios.

### Out of scope
- The read methods `get_student_state` / `get_topic_confidences` /
  `get_recent_misconceptions` (FEAT-SMP-002) — leave raising
  `NotImplementedError`.
- Session-CRUD `create_session` / `get_session` / `list_sessions` /
  `append_turn` / `get_turns` / `end_session` (FEAT-SMP-003, gated by G-CON) —
  leave raising `NotImplementedError`. This method does **not** depend on
  `create_session`: per ASSUM-009 it upserts the session row itself and is
  independent of the SMP-003 lifecycle.
- Engine/pool construction and the `STUDY_TUTOR_PG_DSN` wiring (scaffolding
  task) — this method receives an already-built shared engine/pool.
- Cumulative `total_xp` / `level` / `streak` on `student` (Phase 2). W1 persists
  per-session XP on `session.xp_awarded` only (ASSUM-002).

## Acceptance Criteria

- [ ] `record_session_completion` is implemented in
  `src/study_tutor/knowledge/store/postgres.py` (replaces the
  `NotImplementedError` body) and runs entirely inside **one** transaction
  (`async with <conn>.begin():`) on a connection checked out from the shared
  engine/pool — no per-statement autocommit.
- [ ] **Combined write** — a completion carrying XP + one `ConfidenceUpdate` +
  one `Misconception` persists all three together: `session.xp_awarded` +
  `status='ended'` + `topic` + `aos_scaffolded` (JSONB), the `topic_confidence`
  upsert, and the `misconception` insert, committed as a single transaction and
  completing synchronously within the caller's flow. *(BDD: "Recording a
  completed session persists its XP, confidence updates, and misconceptions
  together")*
- [ ] **Session upsert** is keyed on the `session_id` PK
  (`INSERT ... ON CONFLICT (session_id) DO UPDATE`), sets `status='ended'`, and
  **SETs** `xp_awarded` to the passed value (never `+=`) so replay is
  value-idempotent.
- [ ] **Idempotent replay (single)** — recording the identical completion twice
  under the same `session_id` leaves exactly one session row, XP counted once,
  and **no** duplicated confidence or misconception rows; the learner's
  persisted state is unchanged by the repeat. *(BDD: "Re-delivering the same
  completed session records it only once")*
- [ ] **Idempotent replay (concurrent)** — two concurrent deliveries of the
  identical completion under one `session_id` yield exactly one session row, XP
  counted once, and exactly one set of child records. *(BDD: "Two concurrent
  deliveries of the same session completion are recorded once")*
- [ ] **Atomic rollback (misconception failure)** — if inserting a misconception
  fails mid-write, neither the XP, nor the confidence update, nor the
  misconception is persisted; the learner's prior state remains intact. *(BDD:
  "A partial failure while recording a completed session rolls back every
  change")*
- [ ] **Atomic rollback (invalid percentage in batch)** — if any
  `ConfidenceUpdate` in `confidence_updates` carries a percentage outside
  `[0, 100]` (rejected by `Field` validation / `confidence_band_for` /
  schema `CHECK`), the whole write is rejected and none of the session's XP,
  confidence, or misconception changes are persisted. *(BDD: "A session
  completion whose confidence batch contains an invalid percentage records
  nothing")*
- [ ] **Empty lists** — a completion with `confidence_updates == []` and
  `misconceptions == []` still records the session row with its XP; no
  `topic_confidence` or `misconception` rows are created for it. *(BDD:
  "Recording a completed session with no confidence updates and no
  misconceptions still records the session")*
- [ ] **Write-failure surfaces (ASSUM-008)** — a completion that cannot commit
  **raises** to the caller (awaited inline) rather than being logged-and-dropped;
  none of the session's changes remain persisted. *(BDD: "A session-completion
  write that cannot commit surfaces the failure instead of silently dropping
  it")*
- [ ] **Fail-fast when unreachable** — a completion attempted while the database
  is unreachable raises promptly (does not hang the caller), leaving prior state
  unchanged. *(BDD: "A write attempted while the database is unreachable fails
  fast and leaves prior state intact")*
- [ ] **Connection-drop atomicity** — a connection dropped mid-transaction
  leaves no partial session data; the learner's prior state is intact. *(BDD: "A
  connection dropped mid-transaction leaves no partial session recorded")*
- [ ] **Unknown-learner rejected (ASSUM-003)** — a completion for a `student_id`
  with no `student` row is rejected by the `session.student_id` FK; the whole
  transaction rolls back, leaving no orphaned session or child rows.
- [ ] **Child writes are reused at the connection level** — the confidence
  upsert (SMP-04) and misconception insert (SMP-05) are invoked via helpers that
  accept the already-open `AsyncConnection` so they enlist in this method's
  single transaction. The public `apply_confidence_update` / `record_misconception`
  methods are **not** called from here (they open their own transactions).
- [ ] All modified files pass project-configured lint/format checks with zero
  errors.

## Coach Validation

```bash
# Ephemeral-Postgres adapter/transaction tests (testcontainers or a throwaway
# local container on a NON-5434 port — NEVER the NAS durable instance).
.venv/bin/python -m pytest \
  tests/integration/test_postgres_record_session_completion.py -v

# The mapped BDD scenarios (session-end write path) via the feature glue module.
.venv/bin/python -m pytest \
  features/student-model-postgres-store/test_student_model_postgres_store.py \
  -v -k "completed_session or concurrent or partial_failure or invalid_percentage \
         or cannot_commit or unreachable or connection_dropped"

# Full feature suite must stay green.
.venv/bin/python -m pytest \
  features/student-model-postgres-store/ tests/integration/ -q

# Lint/format (project-configured; W1 scaffolding wires the linter):
.venv/bin/ruff check src/study_tutor/knowledge/store/postgres.py
.venv/bin/ruff format --check src/study_tutor/knowledge/store/postgres.py
```

## Implementation Notes

- **One transaction.** Check out a connection from the shared engine/pool and
  wrap the whole body in `async with conn.begin():`. Order: (1) session upsert,
  (2) each confidence upsert, (3) each misconception insert. Any raise inside the
  block aborts the transaction; the caller sees the exception (ASSUM-008). Do not
  swallow/log — this is not the fire-and-forget writer.

- **Session upsert (idempotency root).** SQLAlchemy Core `pg_insert(session)...
  .on_conflict_do_update(index_elements=["session_id"], set_=...)` with
  `status='ended'`, `topic`, `aos_scaffolded` bound as JSONB, and `xp_awarded`
  **assigned** (not summed). Because `xp_awarded` is SET on conflict, a serial
  replay is naturally value-idempotent and never double-counts XP.

- **Making the append-only misconception insert idempotent within a
  completion.** SMP-05's standalone `record_misconception` is append-only with no
  natural key (ASSUM-006), so blindly re-inserting on replay would duplicate
  rows and break "records it only once" / "only one set of records should exist".
  Gate the child writes on the session's first `active/absent → ended`
  transition **inside the transaction**: make the session upsert conditional
  (e.g. `... DO UPDATE SET ... WHERE session.status <> 'ended' RETURNING
  session_id`, or `ON CONFLICT DO NOTHING` then re-check) and only run the
  confidence upserts + misconception inserts when *this* call is the one that
  performed the transition. A replay (or the losing side of a concurrent race)
  sees `status='ended'` already committed and skips the children — a no-op. The
  row-level lock the conflicting `DO UPDATE` takes serialises the two concurrent
  deliveries so exactly one writes children.

- **Confidence reuse (SMP-04).** Factor SMP-04's upsert into a helper taking the
  open `AsyncConnection` (e.g. `_upsert_confidence(conn, student_id, update)`)
  that derives the band via `student_model.confidence_band_for` at write time and
  stamps `last_revised_at` in UTC. `record_session_completion` loops the batch
  through it; the public `apply_confidence_update` is a thin wrapper that opens
  its own transaction around the same helper.

- **Misconception reuse (SMP-05).** Same pattern — a connection-level
  `_insert_misconception(conn, student_id, topic_name, text)` helper carrying
  SMP-05's 500-char cap (ASSUM-004) and control-char neutralisation (ASSUM-007).

- **Unknown learner.** Do not pre-check `student` existence; let the
  `session.student_id` FK reject it — the failing INSERT rolls the whole
  transaction back (ASSUM-003). Auto-create is explicitly not W1.

- **Parameterisation / security.** All values (incl. `topic`, misconception
  `text`) are bound parameters via Core — never string-interpolated — which is
  what keeps the inherited "DROP TABLE topic_confidence" and control-char
  scenarios inert; no extra sanitisation of DB-control characters is added here.

- **Timestamps.** UTC-aware throughout (`TIMESTAMPTZ`; ASSUM-011).

- **Fail-fast / drop.** Rely on the driver + a bounded pool/connect timeout so an
  unreachable DB raises promptly rather than hanging; a dropped connection
  mid-`begin()` aborts the transaction (no partial commit). Assert both leave
  prior state intact.

## BDD Scenarios

Scenarios in `features/student-model-postgres-store/student-model-postgres-store.feature`
this task makes pass (exact titles):

- Recording a completed session persists its XP, confidence updates, and misconceptions together
- Re-delivering the same completed session records it only once
- Recording a completed session with no confidence updates and no misconceptions still records the session
- A session-completion write that cannot commit surfaces the failure instead of silently dropping it
- A partial failure while recording a completed session rolls back every change
- Two concurrent deliveries of the same session completion are recorded once
- A session completion whose confidence batch contains an invalid percentage records nothing
- A write attempted while the database is unreachable fails fast and leaves prior state intact
- A connection dropped mid-transaction leaves no partial session recorded
