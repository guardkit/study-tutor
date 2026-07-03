---
id: TASK-SMP-05
title: "record_misconception (F1): synchronous insert + text hygiene"
task_type: feature
feature_id: FEAT-SMP-001
wave: 3
implementation_mode: task-work
complexity: 4
dependencies: [TASK-SMP-02, TASK-SMP-03]
parent_feature_spec: features/student-model-postgres-store/student-model-postgres-store_summary.md
---

# Task: record_misconception (F1) — synchronous insert + text hygiene

## Objective

Fill `PostgresStudentStore.record_misconception(*, student_id, topic_name, text) -> None`
(`src/study_tutor/knowledge/store/postgres.py` L98-101; port contract `port.py` L110-119).
One **synchronous** INSERT of a single `misconception` row `(student_id, topic_name, text,
observed_at)` with `observed_at = now (UTC)`, replacing the retired F1 fire-and-forget dispatch.

Text hygiene is ported from the retired sanitiser but **reduced**: strip ASCII control chars
and cap length at 500 (ASSUM-004/007). The prompt-injection rejection is **dropped** — there is
no extraction LLM on the Postgres path, so the text is stored as opaque data (ASSUM-005).
Append-only, **no dedup** (ASSUM-006) — only `record_session_completion` is idempotent. An
unknown learner is rejected by the FK.

## Scope

**In scope**
- The `record_misconception` body only (one method).
- A text-hygiene helper: strip ASCII control chars + cap at 500 chars.
- Payload validation: reject a blank `topic_name` or blank `text`.
- A single parameterised INSERT, awaited inline, `observed_at = datetime.now(timezone.utc)`.

**Out of scope**
- Reads (`get_recent_misconceptions`) → FEAT-SMP-002.
- `record_session_completion` (TASK-SMP-04) and `apply_confidence_update` (TASK-SMP-06) —
  sibling W1 write methods, planned separately; the batched misconceptions inside
  `record_session_completion` are that task's concern, not this one.
- Session CRUD (`create_session`/`append_turn`/…) → FEAT-SMP-003 (leave `NotImplementedError`).
- Dedup / idempotency for standalone F1 (ASSUM-006: append-only in W1).
- NFKC normalisation, zero-width stripping, injection escaping/rejection (dropped — ASSUM-005;
  do **not** carry these over from `coach/sanitise.py`).

## Acceptance Criteria

- [ ] `record_misconception(*, student_id, topic_name, text)` INSERTs exactly one `misconception`
  row `(student_id, topic_name, text, observed_at)` with `observed_at = datetime.now(timezone.utc)`
  (tz-aware, TIMESTAMPTZ — ASSUM-011), then returns `None`.
- [ ] The write is awaited **inline** (single `engine.begin()` transaction); there is **no**
  `asyncio.create_task` / fire-and-forget dispatch anywhere in the method.
- [ ] Text hygiene strips ASCII control chars `\x00-\x08, \x0B-\x0C, \x0E-\x1F, \x7F` while
  preserving `\t \n \r`, before persistence (ASSUM-007; ref `coach/sanitise.py` L87-89 for the
  exact char class).
- [ ] The stored `text` is at most **500** characters (ASSUM-004); text longer than 500 is
  truncated so the persisted value never exceeds 500.
- [ ] Prompt-injection rejection is **not** applied — instruction-like text is stored verbatim as
  opaque content (ASSUM-005), and the call touches **only** the `misconception` table (never reads
  or writes `topic_confidence`, so no confidence band changes as a side effect).
- [ ] A blank `topic_name` (None / empty / whitespace-only) is rejected (`ValueError`); no row is
  inserted.
- [ ] A blank `text` — including text that becomes empty **after** control-char stripping — is
  rejected (`ValueError`); no row is inserted.
- [ ] Append-only: recording the identical `(student_id, topic_name, text)` twice yields **two**
  distinct rows (BIGSERIAL `id`); there is no `ON CONFLICT` / dedup key (ASSUM-006).
- [ ] An unknown `student_id` is rejected via the FK `misconception.student_id -> student(student_id)`
  (the driver `IntegrityError` surfaces to the caller — ASSUM-003/008); no orphan row is left.
- [ ] The INSERT is fully parameterised (bound params) — a `topic_name` or `text` containing SQL
  metacharacters is stored as literal text, never interpolated into SQL.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
# Ephemeral Postgres only — NEVER the NAS durable instance (runbook scope rule).
# Bring up a throwaway container on a NON-5434 port (or let testcontainers manage it):
docker run --rm -d --name st-pg-ephemeral -e POSTGRES_PASSWORD=test \
  -e POSTGRES_DB=study_tutor -p 55432:5432 postgres:16
export STUDY_TUTOR_PG_DSN="postgresql+asyncpg://postgres:test@localhost:55432/study_tutor"

# Stand up the schema (TASK-SMP-03 migration) so the misconception table + FK exist:
.venv/bin/alembic upgrade head

# Adapter behaviour against ephemeral Postgres (persist, 500-cap, control-char strip,
# opaque instruction text, blank-topic/text rejection, replay-appends):
.venv/bin/python -m pytest tests/integration/knowledge/store/test_postgres_record_misconception.py -v

# Fast caller-side coverage via the in-memory fake StudentStore (Protocol impl):
.venv/bin/python -m pytest tests/unit/knowledge/store/ -k record_misconception -v

# Lint / format (zero errors):
.venv/bin/ruff check src/study_tutor/knowledge/store/postgres.py
.venv/bin/ruff format --check src/study_tutor/knowledge/store/postgres.py

docker rm -f st-pg-ephemeral
```

## Implementation Notes

- **Signature is fixed** by the `StudentStore` Protocol (`port.py` L110-119) — keyword-only
  `student_id`, `topic_name`, `text`; do not add parameters.
- Reuse the shared async engine/connection built in **TASK-SMP-02**; do **not** construct a
  connection here (mirror the injection posture in `postgres.py` `__init__`).
- Use SQLAlchemy 2.0 async **Core** (not ORM): `async with engine.begin() as conn: await
  conn.execute(insert_stmt, params)` — one transaction, bound params.
  `INSERT INTO misconception (student_id, topic_name, text, observed_at) VALUES (...)`.
- **Hygiene helper** = the retired `async_write.sanitise_misconception_text` **minus** the injection
  rejection, i.e. only (1) strip ASCII control chars, (2) cap at 500. Do not port NFKC / zero-width /
  injection handling from `coach/sanitise.py`. If you keep the `[…truncated]` suffix on the cap,
  keep the suffix inside the 500 budget (same discipline as `coach/sanitise.py` L181-187) so the
  stored value is always ≤ 500.
- **Order of operations**: validate `topic_name` non-blank → strip control chars from `text` →
  validate stripped `text` non-blank → cap to 500 → INSERT. (Stripping before the blank check is
  what makes a control-char-only text reject.)
- **No dedup**: `misconception` has a BIGSERIAL PK and no natural/unique key
  (`schema_reference.sql` L35-42), so a replayed observation is a second row by construction — do
  not add an idempotency guard.
- **Unknown learner**: rely on the FK; let the driver `IntegrityError` propagate (synchronous writes
  surface failure — ASSUM-008). No pre-check SELECT.
- Leave the other skeleton methods raising `NotImplementedError` — this task fills only
  `record_misconception`.

## BDD Scenarios

This task makes the following scenarios from
`features/student-model-postgres-store/student-model-postgres-store.feature` pass:

- Recording an observed misconception attaches it to the learner and topic synchronously
- Misconception text is stored up to the length cap and truncated beyond it
- Misconception text containing null and control characters is stored without corrupting the record
- A misconception containing instruction-like text is stored as opaque content
- Recording a misconception missing its topic or its text is rejected
- A replayed standalone misconception is appended, not deduplicated, in W1
