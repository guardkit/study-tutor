---
id: TASK-SMP-01
title: "Add SQLAlchemy-async/asyncpg/Alembic deps + async Alembic scaffolding"
task_type: scaffolding
feature_id: FEAT-SMP-001
wave: 1
implementation_mode: direct
complexity: 3
dependencies: []
parent_feature_spec: features/student-model-postgres-store/student-model-postgres-store_summary.md
consumer_context:
  env_var: STUDY_TUTOR_PG_DSN
  read_at: alembic command time (env.py); never at module import
  form_expected: "postgresql://study_tutor:<pw>@<host>:5434/study_tutor — the sync form stored in study-tutor .env (runbook §DSN); env.py coerces the scheme to postgresql+asyncpg:// for the async engine"
  never: "point alembic current/upgrade at the NAS durable instance (5434) from a test — ephemeral / non-5434 throwaway only (RUNBOOK-study-tutor-postgres-deploy scope rule)"
---

# Task: Add SQLAlchemy-async/asyncpg/Alembic deps + async Alembic scaffolding

## Objective

Stand up the dependency + Alembic infrastructure the rest of FEAT-SMP-001 hangs
on, wired for **async** end to end (SQLAlchemy 2.0 async Core + asyncpg), without
creating any schema. This is pure plumbing: after this task the tree still imports
cleanly, `alembic` is a runnable console script in `.venv`, and `env.py` resolves
its engine from `STUDY_TUTOR_PG_DSN` and targets a shared (empty) `MetaData` that
SMP-02 will populate via the first migration. No tables, no `PostgresStudentStore`
bodies, no reads.

## Scope

### In scope

- **Dependencies** (`pyproject.toml` `[project.dependencies]`):
  add `sqlalchemy[asyncio]>=2.0`, `asyncpg`, and `alembic`; regenerate `uv.lock`
  so the lockfile is in sync (`uv add …` / `uv lock`).
- **Async Alembic scaffolding** (`alembic init -t async alembic`, then edit):
  - `alembic.ini` at repo root, `script_location = alembic`, with `sqlalchemy.url`
    left blank/commented (env.py owns DSN resolution — do NOT hardcode a URL).
  - `alembic/` dir with `env.py`, `script.py.mako`, and an empty `versions/`
    (zero revisions — SMP-02 adds the first migration).
  - `env.py` builds an **async** engine via
    `sqlalchemy.ext.asyncio.create_async_engine`, reads the DSN from
    `STUDY_TUTOR_PG_DSN`, coerces a bare `postgresql://` scheme to
    `postgresql+asyncpg://`, and runs migrations through `asyncio.run(...)` /
    `connection.run_sync(context.run_migrations)` (the async template shape).
    Keep an offline path (`run_migrations_offline`) too.
- **Placeholder metadata module** — `src/study_tutor/knowledge/store/metadata.py`
  exposing a single shared `metadata = MetaData()` (empty for now); `env.py` sets
  `target_metadata = metadata`. Import-light: no DB driver imported, no connection
  opened at import.

### Out of scope

- Any `CREATE TABLE` / DDL — the schema in `schema_reference.sql` is encoded by
  **SMP-02**'s first migration, not here.
- Filling `PostgresStudentStore` bodies (`ping` + the three writes) — SMP-02.
- Read methods (FEAT-SMP-002) and session CRUD (FEAT-SMP-003).
- Populating `metadata` with `Table(...)` definitions — SMP-02 owns table shape.
- `.env` / `.env.example` edits for `STUDY_TUTOR_PG_DSN` (runbook/W0 territory);
  this task only *reads* the var if present.

## Acceptance Criteria

- [ ] `pyproject.toml` `[project.dependencies]` lists `sqlalchemy[asyncio]>=2.0`,
      `asyncpg`, and `alembic`.
- [ ] `uv.lock` is regenerated and in sync — `.venv/bin/uv lock --check` (or
      `uv sync --locked`) passes and the lock pins sqlalchemy / asyncpg / alembic.
- [ ] `.venv/bin/alembic --version` runs and prints a version (console script
      installed into the venv).
- [ ] `alembic.ini` exists at repo root with `script_location = alembic` and does
      NOT hardcode `sqlalchemy.url` (env.py resolves the DSN).
- [ ] `alembic/env.py` exists, builds the online engine with
      `create_async_engine`, and reads `STUDY_TUTOR_PG_DSN`, coercing a bare
      `postgresql://` DSN to `postgresql+asyncpg://` before engine construction.
- [ ] `env.py` sets `target_metadata` to the shared `metadata` object from
      `src/study_tutor/knowledge/store/metadata.py`; that module defines an empty
      `MetaData()`, imports no DB driver, and opens no connection at import.
- [ ] `alembic/versions/` exists and contains **no** revision files.
- [ ] `.venv/bin/alembic history` runs without error (empty — zero revisions).
- [ ] `.venv/bin/alembic current` runs without error against a **reachable
      ephemeral** DSN (throwaway local container on a non-5434 port, or a
      testcontainer) and reports base / no applied revision — NEVER the NAS
      durable instance on 5434.
- [ ] The tree still imports cleanly:
      `.venv/bin/python -c "import study_tutor.knowledge.store"` and
      `import study_tutor.knowledge.store.metadata` both succeed with no DB
      connection attempted.
- [ ] No tables/DDL are created by this task (schema lands in SMP-02).

## Coach Validation

```bash
# 1. Deps present in pyproject + lockfile in sync
grep -E 'sqlalchemy\[asyncio\]>=2\.0|^ *"asyncpg|^ *"alembic' pyproject.toml
.venv/bin/uv lock --check          # or: .venv/bin/uv sync --locked

# 2. alembic is a runnable console script in the venv
.venv/bin/alembic --version

# 3. env.py is async + DSN-driven (grep the wiring)
grep -q 'create_async_engine' alembic/env.py
grep -q 'STUDY_TUTOR_PG_DSN'   alembic/env.py
grep -q 'postgresql+asyncpg'   alembic/env.py           # driver coercion present
grep -q 'target_metadata'      alembic/env.py
grep -qv 'sqlalchemy.url *= *postgresql' alembic.ini    # url NOT hardcoded

# 4. Placeholder metadata module is empty + import-light
.venv/bin/python -c "from study_tutor.knowledge.store.metadata import metadata; assert len(metadata.tables) == 0"

# 5. alembic history (no DB needed) — empty, no error
.venv/bin/alembic history

# 6. alembic current against an EPHEMERAL non-5434 DB (NEVER the NAS 5434 instance)
docker run --rm -d --name smp01-ephemeral -e POSTGRES_PASSWORD=x -p 55432:5432 postgres:16
until docker exec smp01-ephemeral pg_isready -U postgres >/dev/null 2>&1; do sleep 0.5; done
STUDY_TUTOR_PG_DSN="postgresql://postgres:x@localhost:55432/postgres" .venv/bin/alembic current
docker rm -f smp01-ephemeral

# 7. Tree still imports cleanly (no DB connection at import)
.venv/bin/python -c "import study_tutor.knowledge.store"
```

## Implementation Notes

- **uv workflow**: `.venv/bin/uv add "sqlalchemy[asyncio]>=2.0" asyncpg alembic`
  edits `pyproject.toml` and refreshes `uv.lock` in one shot; follow with
  `uv sync` so the venv has the console script. Do not hand-edit `uv.lock`.
- **Async template**: scaffold with `alembic init -t async alembic` (the `-t
  async` template already emits an `env.py` using `create_async_engine` +
  `connection.run_sync(...)`), then replace its `config.get_main_option(
  "sqlalchemy.url")` DSN read with the `STUDY_TUTOR_PG_DSN` env read below.
- **DSN coercion is load-bearing**: the DSN stored in study-tutor `.env` is the
  sync form `postgresql://…@…:5434/study_tutor` (runbook §DSN / G4 uses it with
  `psql`). asyncpg needs the `postgresql+asyncpg://` scheme, so `env.py` must
  rewrite the scheme (e.g. `re.sub(r'^postgresql(\+psycopg2?)?://',
  'postgresql+asyncpg://', dsn)`) before `create_async_engine`. Read the raw var
  with `os.environ`; there is no central settings module in this repo (other
  modules read env vars directly — see `llm/client.py`, `planner/pipeline.py`),
  so match that convention rather than inventing one.
- **`sqlalchemy.url` stays blank in `alembic.ini`** so the DSN has exactly one
  source of truth (`STUDY_TUTOR_PG_DSN`) and the durable instance can never be
  accidentally baked into a committed file.
- **Import-light discipline**: mirror the store package rule — no DB driver at
  import, no connection at import. `metadata.py` is just
  `from sqlalchemy import MetaData` + `metadata = MetaData()`. `env.py` only
  connects inside `run_migrations_online`, which Alembic invokes at command time,
  never at Python import. This preserves the property that
  `import study_tutor.knowledge.store` works with or without a DB.
- **Metadata home**: `src/study_tutor/knowledge/store/metadata.py` sits beside
  `port.py` / `entities.py` / `postgres.py`; SMP-02 imports this same object to
  hang `Table(...)` defs off it and to encode the migration. Keeping it a
  standalone module (not inside `postgres.py`) keeps the adapter importable
  without SQLAlchemy loaded on the read-only paths.
- **Ephemeral-only for `current`/`upgrade`**: any command that touches a DB in
  validation/CI points at a throwaway container on a non-5434 port (55432 above)
  or a testcontainer. The NAS 5434 instance is the durable learner store and is
  out of bounds for hermetic checks (runbook scope rule).

## BDD Scenarios

Scaffolding turns **no** `.feature` scenario green on its own — it is the
precondition that lets SMP-02's migration make the `@migration` scenarios pass.
It directly unblocks (green in SMP-02, not here):

- Applying the student-model migration to an empty database creates the learner-state schema
- Re-applying the migration when already at the latest revision changes nothing
- Reversing the migration returns the database to an empty student-model schema
