---
id: TASK-SMP-02
title: First Alembic migration encoding the StudentStore schema (runbook gate G7)
task_type: feature
feature_id: FEAT-SMP-001
wave: 2
implementation_mode: task-work
complexity: 5
dependencies: [TASK-SMP-01]
parent_feature_spec: features/student-model-postgres-store/student-model-postgres-store_summary.md
consumer_context:
  producer: W0 runbook / TASK-SMP-01 chain
  consumes: STUDY_TUTOR_PG_DSN
  framework: "SQLAlchemy 2.0 async (create_async_engine)"
  driver: "asyncpg"
  format_note: "DSN must use postgresql+asyncpg:// dialect for the async engine"
---

## Objective

Author the **first** Alembic revision (the initial `upgrade()` from `base`) that encodes
`src/study_tutor/knowledge/store/schema_reference.sql` **exactly** — all 7 StudentStore tables, their
FKs, CHECK constraints, PKs (composite where the reference has them), and the 3 named indexes — so the
runbook's **G7** gate (`alembic upgrade head`) stands up the whole learner-state schema on an empty,
extension-free database. `downgrade()` must reverse cleanly to `base`. No pgvector, no extensions.

## Scope

**In scope**
- One versioned revision under the alembic `versions/` dir with `down_revision = None` (first migration).
- `upgrade()` creates, byte-for-byte with the reference DDL:
  - `student` — PK `student_id`; CHECK `year_group BETWEEN 7 AND 13`.
  - `topic_confidence` — composite PK `(student_id, topic_name)`; FK `student_id → student ON DELETE CASCADE`;
    CHECK `percentage BETWEEN 0 AND 100`.
  - `misconception` — PK `id BIGSERIAL`; FK `student_id → student ON DELETE CASCADE`.
  - `session` — PK `session_id`; FK `student_id → student ON DELETE CASCADE`; **includes `xp_awarded`**
    (`INTEGER NOT NULL DEFAULT 0 CHECK (xp_awarded >= 0)`); CHECK `turn_count >= 0`; `aos_scaffolded JSONB`.
  - `session_turn` — composite PK `(session_id, turn_index)`; FK `session_id → session ON DELETE CASCADE`;
    CHECK `turn_index >= 0`.
  - `achievement` — composite PK `(student_id, achievement_id)`; FK `student_id → student ON DELETE CASCADE`;
    CHECK `xp_awarded >= 0`.
  - `quest` — PK `quest_id`; FK `student_id → student ON DELETE CASCADE`; CHECK `xp_reward >= 0`.
  - Named indexes: `misconception_recent_idx (student_id, observed_at DESC)`,
    `session_resume_idx (student_id, status, last_activity DESC)`, `quest_active_idx (student_id, status)`.
  - All `TIMESTAMPTZ` columns typed as `sa.TIMESTAMP(timezone=True)`.
- `downgrade()` drops every object created above, in FK-safe order, returning the DB to `base`.
- If TASK-SMP-01 left `env.py` as the alembic default: wire it to resolve `STUDY_TUTOR_PG_DSN` via
  `create_async_engine` on the `postgresql+asyncpg://` dialect (async `run_migrations_online`).

**Out of scope**
- Any table column not in `schema_reference.sql` — cumulative `total_xp`/`level`/`current_streak`/
  `longest_streak` on `student` are **Phase 2**, NOT W1 (per-session XP lives on `session.xp_awarded`).
- pgvector or any non-`plpgsql` extension (`CREATE EXTENSION`) — explicitly forbidden (ADR-ARCH-023 D-scope).
- Adapter method bodies (`ping`, write path) — TASK-SMP-03+; the migration only lays the schema down.
- Seed data / fixtures; a second (data) migration.

## Acceptance Criteria

- [ ] A single first revision exists under alembic `versions/` with `down_revision = None`.
- [ ] `.venv/bin/alembic upgrade head` applies **clean** against an EPHEMERAL Postgres (throwaway
      container on a non-5434 port, or testcontainers) — NEVER the NAS durable instance.
- [ ] After `upgrade head`, all **7** tables exist: `student`, `topic_confidence`, `misconception`,
      `session`, `session_turn`, `achievement`, `quest` (assert via `information_schema.tables`).
- [ ] After `upgrade head`, all **3** named indexes exist: `misconception_recent_idx`,
      `session_resume_idx`, `quest_active_idx` (assert via `pg_indexes`).
- [ ] `session.xp_awarded` column is present as `INTEGER NOT NULL DEFAULT 0` with a `>= 0` CHECK.
- [ ] The composite PKs match the reference: `topic_confidence (student_id, topic_name)`,
      `session_turn (session_id, turn_index)`, `achievement (student_id, achievement_id)`.
- [ ] Every child FK targets `student` (or `session` for `session_turn`) with `ON DELETE CASCADE`.
- [ ] The four CHECK families are enforced: `year_group BETWEEN 7 AND 13`, `percentage BETWEEN 0 AND 100`,
      `turn_count >= 0` / `turn_index >= 0`, `xp_awarded >= 0` / `xp_reward >= 0` (a violating INSERT raises).
- [ ] `SELECT extname FROM pg_extension` returns **only** `plpgsql` — no extension beyond the default
      procedural language was created.
- [ ] Re-running `.venv/bin/alembic upgrade head` when already at head is a **no-op** (no error; schema
      unchanged) — restart-safe.
- [ ] `.venv/bin/alembic downgrade base` reverses cleanly: none of the 7 tables remain
      (`information_schema.tables` shows zero of them).
- [ ] `env.py` resolves `STUDY_TUTOR_PG_DSN` and constructs the engine on the `postgresql+asyncpg://`
      dialect (see Seam Tests).
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
# --- Ephemeral Postgres (throwaway; NEVER the NAS 5434 durable instance) ------
docker run -d --name st_pg_ephemeral \
  -e POSTGRES_USER=study_tutor -e POSTGRES_PASSWORD=pw -e POSTGRES_DB=study_tutor \
  -p 55432:5432 postgres:16
until docker exec st_pg_ephemeral pg_isready -U study_tutor >/dev/null 2>&1; do sleep 1; done
export STUDY_TUTOR_PG_DSN="postgresql+asyncpg://study_tutor:pw@localhost:55432/study_tutor"

# --- G7: apply the migration to head -----------------------------------------
.venv/bin/alembic upgrade head

# --- Assert 7 tables + 3 named indexes + no extra extension -------------------
PSQL="docker exec -e PGPASSWORD=pw st_pg_ephemeral psql -U study_tutor -d study_tutor -tA"
$PSQL -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'
          AND table_name IN ('student','topic_confidence','misconception','session',
                             'session_turn','achievement','quest');"   # expect 7
$PSQL -c "SELECT count(*) FROM pg_indexes WHERE schemaname='public'
          AND indexname IN ('misconception_recent_idx','session_resume_idx','quest_active_idx');"  # expect 3
$PSQL -c "SELECT string_agg(extname,',') FROM pg_extension;"           # expect: plpgsql

# --- Idempotent re-apply (already at head → no-op) ---------------------------
.venv/bin/alembic upgrade head

# --- Reverse to base and assert the schema is gone ---------------------------
.venv/bin/alembic downgrade base
$PSQL -c "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'
          AND table_name IN ('student','topic_confidence','misconception','session',
                             'session_turn','achievement','quest');"   # expect 0

# --- Migration + seam tests (uses ephemeral/testcontainers PG) ---------------
.venv/bin/python -m pytest tests/knowledge/store/test_migration_schema.py -q

# --- Teardown ----------------------------------------------------------------
docker rm -f st_pg_ephemeral
```

## Seam Tests

A pytest stub validating the `STUDY_TUTOR_PG_DSN` contract this task consumes — the async engine (and thus
alembic `env.py`) must drive the `postgresql+asyncpg://` dialect, not bare `postgresql://` (which asyncpg's
`create_async_engine` cannot bind). Place at `tests/knowledge/store/test_dsn_seam.py`:

```python
import os
import pytest
from sqlalchemy.engine import make_url


def _resolved_dsn() -> str:
    """The DSN as env.py / the store normalise it before create_async_engine.

    Producer contract (W0 runbook / TASK-SMP-01 chain): STUDY_TUTOR_PG_DSN.
    The runbook's .env ships bare `postgresql://`; the async engine REQUIRES the
    `postgresql+asyncpg://` dialect, so env.py normalises the scheme on read.
    """
    from study_tutor.knowledge.store import migration_env  # env.py helper (TASK-SMP-01/02)

    raw = os.environ["STUDY_TUTOR_PG_DSN"]
    return migration_env.async_dsn(raw)


@pytest.mark.skipif(
    "STUDY_TUTOR_PG_DSN" not in os.environ, reason="DSN not wired (producer: W0 runbook)"
)
def test_dsn_uses_asyncpg_dialect() -> None:
    url = make_url(_resolved_dsn())
    assert url.drivername == "postgresql+asyncpg", (
        f"async engine needs postgresql+asyncpg dialect, got {url.drivername!r}"
    )
    assert url.database == "study_tutor"


def test_bare_postgresql_dsn_is_normalised_to_asyncpg() -> None:
    from study_tutor.knowledge.store import migration_env

    normalised = migration_env.async_dsn("postgresql://study_tutor:pw@localhost:55432/study_tutor")
    assert make_url(normalised).drivername == "postgresql+asyncpg"
```

## Implementation Notes

- **Reference is authoritative.** `schema_reference.sql` is REFERENCE ONLY — do not apply it by hand;
  this revision is the encoding. Diff column-by-column against it; the migration is the single source
  of truth for the applied schema from here on.
- **Async env.py.** Alembic runs offline/online; online must use `create_async_engine` +
  `connection.run_sync(context.run_migrations)`. Resolve the DSN from `STUDY_TUTOR_PG_DSN` and coerce the
  scheme to `postgresql+asyncpg` (the runbook/.env ships bare `postgresql://` for libpq/psql; the async
  engine cannot use it). Keep the coercion in one helper (`migration_env.async_dsn`) reused by the seam test.
- **Column types.** All `TIMESTAMPTZ` → `sa.TIMESTAMP(timezone=True)`; `aos_scaffolded` → `postgresql.JSONB`
  with server default `'[]'::jsonb`; `misconception.id` → `sa.BigInteger` with `autoincrement=True` (BIGSERIAL);
  `year_group` → `sa.SmallInteger`; `percentage` → `sa.SmallInteger`.
- **Named constraints.** Give CHECKs and FKs explicit names so `downgrade()` and future autogenerate diffs are
  stable (Alembic cannot drop an unnamed CHECK on some backends).
- **Downgrade order.** Drop children before parents: `session_turn`, `topic_confidence`, `misconception`,
  `achievement`, `quest`, `session`, then `student` (or rely on `DROP TABLE ... CASCADE`). Drop the 3 named
  indexes if they are not auto-dropped with their tables.
- **No extensions.** Do not emit `CREATE EXTENSION` for anything — `plpgsql` is the only (default) one, and the
  `pg_extension` assertion guards it. Semantic recall stays on ChromaDB, not this DB (ADR-ARCH-023).
- **Ephemeral only.** Every test/validation run targets a throwaway Postgres (testcontainers or a local
  non-5434 container). NEVER point alembic or a test at the NAS durable instance on 5434 (runbook scope rule).

## BDD Scenarios

Scenarios from `features/student-model-postgres-store/student-model-postgres-store.feature` this task makes pass:

- Applying the student-model migration to an empty database creates the learner-state schema
  (includes the step "no database extension beyond the default procedural language should be required")
- Re-applying the migration when already at the latest revision changes nothing
- Reversing the migration returns the database to an empty student-model schema

Schema-underpinned constraints laid down here (CHECK families) are exercised end-to-end by the write-path
tasks (TASK-SMP-03+): "A learner year group is accepted only within the secondary-school range",
"A confidence update outside the valid percentage range is rejected".
