---
id: TASK-SMP-03
title: Async engine/pool provider + DI seam + ping()
task_type: feature
feature_id: FEAT-SMP-001
wave: 2
implementation_mode: task-work
complexity: 4
dependencies: [TASK-SMP-01]
parent_feature_spec: features/student-model-postgres-store/student-model-postgres-store_summary.md
consumer_context:
  producer: W0 runbook (RUNBOOK-study-tutor-postgres-deploy.md) / TASK-SMP-01 chain
  consumes: STUDY_TUTOR_PG_DSN
  framework: "SQLAlchemy 2.0 async (create_async_engine)"
  driver: "asyncpg"
  format_note: "DSN must use postgresql+asyncpg:// dialect for the async engine"
---

## Objective

Give `PostgresStudentStore` a real connection substrate and a health probe, and
wire it into the process at startup. Fill `__init__` to build **one shared async
engine per process** (`sqlalchemy.ext.asyncio.create_async_engine`) from
`STUDY_TUTOR_PG_DSN` when no pool is injected, implement `ping() -> bool`
(`SELECT 1`), and register the store via `set_student_store` at boot — mirroring
the DI posture `knowledge.retrieval.set_collection_provider` /
`knowledge.store.provider.set_student_store` already establish. This is the seam
every W1 write method (`record_session_completion`, `record_misconception`,
`apply_confidence_update` — other tasks) hangs its transaction on.

## Scope

**In scope**
- `PostgresStudentStore.__init__(self, dsn: str, *, pool: Any | None = None)`
  (`src/study_tutor/knowledge/store/postgres.py`): when `pool is None`, build a
  single shared `AsyncEngine` from `dsn`; when a pool/engine is injected (tests),
  use it verbatim and build nothing. Never construct a connection/engine on the
  hot path.
- Normalise the DSN to the async dialect: the producer publishes
  `postgresql://…` (W0 runbook), but the async engine requires
  `postgresql+asyncpg://…` — coerce the scheme at construction so a plain-scheme
  DSN from `.env` still yields an asyncpg engine.
- `async def ping(self) -> bool` — acquire a connection, `SELECT 1`, return
  `True` when reachable.
- Startup wiring: a boot helper that reads `STUDY_TUTOR_PG_DSN` from the
  environment, constructs `PostgresStudentStore`, and calls
  `set_student_store(store)` once (posture mirror of
  `cli/rag_wiring.build_rag_providers` → `set_collection_provider`).
- Add `sqlalchemy[asyncio]` + `asyncpg` to `pyproject.toml` deps if TASK-SMP-01
  has not already (they are the migration's runtime too).

**Out of scope**
- The three write bodies (`record_session_completion`,
  `record_misconception`, `apply_confidence_update`) — separate W1 tasks; they
  only rely on the engine this task lands.
- Read methods `get_student_state` / `get_topic_confidences` /
  `get_recent_misconceptions` (FEAT-SMP-002) — leave raising `NotImplementedError`.
- Session-CRUD `create_session` / `get_session` / `list_sessions` /
  `append_turn` / `get_turns` / `end_session` (FEAT-SMP-003, gated by G-CON) —
  leave raising `NotImplementedError`.
- The Alembic migration / schema (TASK-SMP-01).

## Acceptance Criteria

- [ ] When constructed with a DSN and no `pool`, `PostgresStudentStore` builds
      exactly **one** `AsyncEngine` (`create_async_engine`) and reuses it for
      every `ping()`/connection — no per-call engine or pool creation
      (assert engine identity is stable across repeated calls).
- [ ] When a pool/engine is injected via the `pool=` kwarg, `__init__` builds no
      engine and uses the injected object as-is (test-injection path).
- [ ] A DSN with the plain `postgresql://` scheme is coerced to
      `postgresql+asyncpg://` so the engine loads the asyncpg driver; a DSN
      already using `postgresql+asyncpg://` is accepted unchanged.
- [ ] `ping()` returns `True` against a reachable ephemeral Postgres and does
      **not** raise when the database is up (`SELECT 1` round-trips).
- [ ] Boot wiring reads `STUDY_TUTOR_PG_DSN`, constructs the store, and registers
      it via `set_student_store`; `get_student_store()` then returns that
      instance.
- [ ] The read methods (`get_student_state`, `get_topic_confidences`,
      `get_recent_misconceptions`) and the session-CRUD methods
      (`create_session`, `get_session`, `list_sessions`, `append_turn`,
      `get_turns`, `end_session`) still raise `NotImplementedError` (W1 boundary
      unchanged).
- [ ] `postgres.py` imports cleanly with no eager module-load DB import beyond
      the now-added `sqlalchemy`/`asyncpg` runtime deps (no connection at import).
- [ ] All modified files pass project-configured lint/format checks with zero
      errors.

## Coach Validation

```bash
# Engine-once + injection + dialect-coercion + NotImplementedError-boundary unit tests
.venv/bin/python -m pytest tests/unit/knowledge/store/test_postgres_engine_provider.py -q

# Seam test: STUDY_TUTOR_PG_DSN contract (asyncpg dialect) — no live DB needed
.venv/bin/python -m pytest tests/integration/test_student_store_dsn_seam.py -q -m seam

# ping() smoke against an EPHEMERAL Postgres (testcontainers or a throwaway
# local container on a NON-5434 port — NEVER the NAS durable instance)
.venv/bin/python -m pytest tests/integration/test_postgres_store_ping.py -q

# Import cleanliness (no connection at import)
.venv/bin/python -c "import study_tutor.knowledge.store.postgres"

# Lint/format
.venv/bin/ruff check src/study_tutor/knowledge/store/postgres.py
```

## Implementation Notes

- **Single instance per process.** Store the engine on the instance
  (`self._engine`) and treat the store itself as the process-wide singleton the
  `provider.py` slot holds — the same "one slot, wired once at startup" discipline
  as `retrieval._collection_provider`. Do not add a second global engine cache.
- **Dialect coercion.** Prefer `sqlalchemy.engine.make_url(dsn).set(drivername="postgresql+asyncpg")`
  (or an equivalent scheme swap) so credentials/host/port survive intact; only the
  driver token changes. This keeps the `.env` value stack-agnostic per the
  consumer_context `format_note`.
- **ping semantics.** `async with engine.connect() as conn: await conn.execute(text("SELECT 1"))`
  → `True`. W1 only needs the "up ⇒ True" leg (the "reports healthy" scenario);
  the unreachable-⇒-fail-fast behaviour lands with the write path, not here.
- **Boot helper.** Site it beside the existing startup wiring (a `build_student_store()`
  in the store package or the CLI wiring module) so orchestrator boot calls it
  exactly once, exactly as `build_rag_providers` calls `set_collection_provider`.
  Read the env var with `os.environ["STUDY_TUTOR_PG_DSN"]` (missing var is a boot
  error, not a silent skip).
- **Boundary check.** Do not touch the read/session-CRUD bodies — an AC asserts
  they still raise `NotImplementedError`, which is the tripwire that this task
  stayed inside the W1 fence.

## Seam Tests

Validates the `STUDY_TUTOR_PG_DSN` consumer contract: the store must drive the
async engine with the `postgresql+asyncpg://` dialect regardless of the scheme
the producer publishes. No live database — asserts on the resolved engine URL.

```python
# tests/integration/test_student_store_dsn_seam.py
import pytest

from study_tutor.knowledge.store.postgres import PostgresStudentStore

pytestmark = [
    pytest.mark.seam,
    pytest.mark.integration_contract("StudentStorePgDsn"),
]


@pytest.mark.parametrize(
    "published_dsn",
    [
        "postgresql://study_tutor:pw@host:5432/study_tutor",       # producer (runbook) form
        "postgresql+asyncpg://study_tutor:pw@host:5432/study_tutor",  # already-async form
    ],
)
def test_dsn_is_driven_through_the_asyncpg_dialect(published_dsn: str) -> None:
    """STUDY_TUTOR_PG_DSN → async engine MUST use the postgresql+asyncpg driver."""
    store = PostgresStudentStore(published_dsn)
    url = store._engine.url  # the shared AsyncEngine built in __init__
    assert url.drivername == "postgresql+asyncpg"
    # credentials/host/port/db survive the coercion untouched
    assert url.host == "host"
    assert url.port == 5432
    assert url.database == "study_tutor"


def test_injected_pool_builds_no_engine() -> None:
    """pool= injection path constructs no engine (test/DI seam)."""
    sentinel = object()
    store = PostgresStudentStore("postgresql://x:y@h:5432/d", pool=sentinel)
    assert store._pool is sentinel
```

## BDD Scenarios

This task makes the following scenario from
`features/student-model-postgres-store/student-model-postgres-store.feature` pass:

- The store reports healthy when the database is reachable
