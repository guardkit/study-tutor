---
id: TASK-SMP-04
title: "apply_confidence_update (F2): upsert topic_confidence with derived band"
task_type: feature
feature_id: FEAT-SMP-001
wave: 3
implementation_mode: task-work
complexity: 4
dependencies: [TASK-SMP-02, TASK-SMP-03]
parent_feature_spec: features/student-model-postgres-store/student-model-postgres-store_summary.md
---

## Objective

Fill `PostgresStudentStore.apply_confidence_update` (F2 write path) — replace the
`NotImplementedError` skeleton at `src/study_tutor/knowledge/store/postgres.py:103-106`
with a single-row UPSERT into `topic_confidence`, keyed by `(student_id, topic_name)`,
that persists the resolved percentage, derives its band at write time via
`student_model.confidence_band_for`, and stamps `last_revised_at` in UTC.

Signature is fixed by the port (`store/port.py:121-126`) — do not change it:

```python
async def apply_confidence_update(
    self, *, student_id: str, update: ConfidenceUpdate
) -> None:
```

`ConfidenceUpdate` (`store/entities.py:124-134`) carries `topic_name: str` and
`percentage: int` (Pydantic `Field(ge=0, le=100)`). The store persists the *resolved*
value, not a delta (idempotent on replay for a given topic — last write wins).

## Scope

**In scope**
- `apply_confidence_update` body only: build and execute the UPSERT inside one
  transaction on the shared async engine from TASK-SMP-02.
- Band derivation via `confidence_band_for(update.percentage)` (40/60/80 taxonomy).
- `last_revised_at` = `datetime.now(timezone.utc)` (app-side, tz-aware UTC — matches
  `student_model` discipline; bound as a parameter, never SQL-interpolated).
- Range validation: reject `percentage` outside `[0, 100]` with `ValueError` before
  any SQL is issued.
- FK rejection for an unknown `student_id` (ASSUM-003) — surface the DB error, insert
  nothing.

**Out of scope**
- `ping` + engine/pool bootstrap + the Alembic migration → TASK-SMP-02 (dependency).
- `record_session_completion` / `record_misconception` transaction + upsert helpers →
  TASK-SMP-03 (dependency; reuse its parameterised-write / `postgresql.insert` helper
  rather than duplicating it).
- Reads (`get_topic_confidences` etc.) → FEAT-SMP-002; session CRUD → FEAT-SMP-003.
  Leave all of those raising `NotImplementedError`.
- Cumulative `total_xp` / `level` / `streak` → Phase 2.

## Acceptance Criteria

- [ ] `apply_confidence_update` issues one `INSERT ... ON CONFLICT (student_id, topic_name)
      DO UPDATE SET percentage = EXCLUDED.percentage, band = EXCLUDED.band,
      last_revised_at = EXCLUDED.last_revised_at` against `topic_confidence`, committed in
      one transaction (SQLAlchemy 2.0 async Core `postgresql.insert(...).on_conflict_do_update`,
      asyncpg driver — NOT ORM).
- [ ] `band` is derived at write time via `student_model.confidence_band_for(update.percentage)`
      and matches the 40/60/80 taxonomy: `0..39`→`struggling`, `40..59`→`developing`,
      `60..79`→`secure`, `80..100`→`mastered` (verified at boundaries 0/39/40/59/60/79/80/100).
- [ ] `percentage` outside `[0, 100]` (e.g. `-1`, `101`) is rejected with `ValueError`
      before any SQL is issued, and no `topic_confidence` row is created or mutated by the
      attempt (Pydantic `ConfidenceUpdate.percentage` bound + `confidence_band_for`'s
      `ValueError` give defence-in-depth; note `pydantic.ValidationError` is a `ValueError`).
- [ ] `last_revised_at` is written as a timezone-aware UTC instant (`datetime.now(timezone.utc)`),
      stored in the `TIMESTAMPTZ` column, and is unaffected by the caller's local timezone.
- [ ] A first real update on a topic whose baseline `last_revised_at` is the
      `EPOCH_NEVER_REVISED` sentinel (`1970-01-01T00:00:00Z`) overwrites the sentinel with the
      actual update instant (stored value `> EPOCH_NEVER_REVISED`).
- [ ] A write for a `student_id` with no `student` row is rejected via the FK
      (`ON DELETE CASCADE` reference in `topic_confidence`) — surfaces the integrity error
      (`sqlalchemy.exc.IntegrityError` wrapping asyncpg `ForeignKeyViolationError`), inserts
      nothing (ASSUM-003).
- [ ] `topic_name` and all string/time values are passed as bound parameters, so a
      control-character / SQL-metacharacter topic name (e.g.
      `"Macbeth'); DROP TABLE topic_confidence;--"`) is stored verbatim as literal text and
      no schema damage occurs.
- [ ] Two concurrent `apply_confidence_update` calls for the same `(student_id, topic_name)`
      resolve to exactly one stored row via `ON CONFLICT` (last committed write wins), and the
      stored `band` matches the stored `percentage`.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

Adapter behaviour runs against an EPHEMERAL Postgres only — testcontainers, or a
throwaway local container on a NON-5434 port. NEVER the NAS durable instance (runbook
scope rule).

```bash
# 0. Ephemeral PG (throwaway; non-5434 port) + schema from the W1 migration (TASK-SMP-02).
docker run -d --rm --name smp04-pg -e POSTGRES_USER=study_tutor \
  -e POSTGRES_PASSWORD=test -e POSTGRES_DB=study_tutor -p 55432:5432 postgres:16
export STUDY_TUTOR_PG_DSN="postgresql://study_tutor:test@localhost:55432/study_tutor"
.venv/bin/python -m alembic upgrade head   # schema owned by Alembic (TASK-SMP-02)

# 1. Adapter tests for F2 (band sweep, out-of-range reject, FK reject, sentinel overwrite,
#    concurrency, literal topic name, UTC) against the ephemeral PG.
.venv/bin/python -m pytest tests/integration/knowledge/store/test_postgres_apply_confidence_update.py -v

# 2. Fast caller tests against the in-memory fake StudentStore (Protocol impl).
.venv/bin/python -m pytest tests/unit/knowledge/store/ -v

# 3. The other write/read/session methods must still raise NotImplementedError (scope guard).
.venv/bin/python -m pytest tests/unit/knowledge/store/test_postgres_scope_guard.py -v

# 4. Lint/format (project-configured; e.g. ruff/black if wired in pyproject).
.venv/bin/ruff check src/study_tutor/knowledge/store/postgres.py

docker stop smp04-pg
```

## Implementation Notes

- Reuse the async engine / connection acquisition and the parameterised-`postgresql.insert`
  helper introduced by TASK-SMP-02/03 — do not open a fresh engine here. Constructor already
  holds `self._dsn` / `self._pool` (`postgres.py:50-58`).
- Compute the timestamp app-side (`datetime.now(timezone.utc)`) rather than SQL `now()` so
  the value is deterministic/testable and unambiguously tz-aware UTC; bind it as a param.
- `confidence_band_for` (`student_model.py`) already raises `ValueError` outside `[0, 100]`,
  so calling it before the SQL gives the range guard for free — the row is never written on a
  bad percentage. Keep it defence-in-depth alongside the `ConfidenceUpdate` Pydantic bound.
- `EPOCH_NEVER_REVISED` sentinel lives in `student_model` (`1970-01-01T00:00:00Z`); baselines
  seed `topic_confidence.last_revised_at` with it. The overwrite is implicit in the UPSERT's
  `SET last_revised_at = EXCLUDED.last_revised_at` — no special-casing needed.
- Concurrency correctness comes from the PK `(student_id, topic_name)` + `ON CONFLICT DO
  UPDATE`; no `SELECT`-then-`INSERT` race. Do not add advisory locks.
- Do not string-format `topic_name` / `percentage` into SQL — bound params only (the security
  and control-char scenarios depend on this).

## BDD Scenarios

Scenario titles from `features/student-model-postgres-store/student-model-postgres-store.feature`
that this task makes pass (all exercise `apply_confidence_update`):

- Applying a confidence update stores the resolved percentage and derives its band
- A resolved confidence percentage is stored with the expected band  *(Scenario Outline — 0/39/40/59/60/79/80/100 → struggling/developing/secure/mastered)*
- A confidence update outside the valid percentage range is rejected  *(Scenario Outline — -1/101)*
- Recording learner state for an unknown learner is rejected  *(FK reject, ASSUM-003)*
- The first real confidence update overwrites the never-revised baseline timestamp
- Concurrent confidence updates for the same topic resolve to a single stored value
- A topic name containing database-control characters is stored as literal text
- Learner-state timestamps are stored and returned in UTC regardless of the caller's timezone
