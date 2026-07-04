---
id: TASK-SMP3-01
title: "create_session (resume-if-active, one txn) + get_session"
task_type: feature
feature_id: FEAT-SMP-003
wave: 1
implementation_mode: task-work
complexity: 5
dependencies: []
parent_feature_spec: features/durable-cross-device-sessions/durable-cross-device-sessions_summary.md
---

## Objective

Fill `PostgresStudentStore.create_session` and `get_session`
(`src/study_tutor/knowledge/store/postgres.py:436-447`, currently `NotImplementedError`)
over the merged W1 `session` table. `FakeStudentStore` (`tests/unit/knowledge/store/fakes.py:289-374`)
is the reference behaviour.

Signatures are fixed by the port (`store/port.py:130-149`) — do not change them:

```python
async def create_session(self, *, student_id, subject, topic=None, resume_if_active=False) -> tuple[SessionRecord, bool]
async def get_session(self, session_id) -> SessionRecord | None
```

## Scope

**In scope**
- `create_session`: in ONE transaction (ASSUM-003) —
  - when `resume_if_active` is True: `SELECT ... FROM session WHERE student_id=:sid AND subject=:subj
    AND status='active' ORDER BY last_activity DESC LIMIT 1`; if found, return `(record, created=False)`.
  - otherwise INSERT a new row: `session_id = uuid4()`, `status='active'`, `started_at=last_activity=now(UTC)`,
    `turn_count=0`, `xp_awarded=0`, `aos_scaffolded='[]'`, `topic` as given; return `(record, created=True)`.
- `get_session`: `SELECT * FROM session WHERE session_id=:sid`; map to `SessionRecord`; `None` if absent.
- Map rows → `store.entities.SessionRecord` (`entities.py:137-149`): session_id, student_id, subject, topic,
  status, started_at, last_activity, turn_count, aos_scaffolded, summary. NOTE `SessionRecord` does NOT carry
  `xp_awarded` — do not add it.

**Out of scope**
- `list_sessions`/`get_turns` → TASK-SMP3-02; `append_turn`/`end_session` → TASK-SMP3-03 (leave raising).
- Adding a partial unique index / migration for single-active enforcement (ASSUM-003 — transaction only).
- The learner-state write methods are DONE (W1) and reads DONE (W2) — do not touch.

## Acceptance Criteria

- [ ] `create_session(resume_if_active=False)` INSERTs a new active session (uuid session_id, status='active',
      turn_count=0, aos_scaffolded=[], started_at==last_activity in UTC) and returns `(record, True)`.
- [ ] `create_session(resume_if_active=True)` with an existing active session for `(student_id, subject)`
      returns that session as `(record, False)` — no new row created; with none, creates one and returns `(record, True)`.
- [ ] The resume check + insert happen in ONE transaction (no list-then-create round-trip; ASSUM-003).
- [ ] `get_session(id)` returns the matching `SessionRecord`; an unknown id returns `None` (does NOT raise).
- [ ] `SessionRecord` fields map from the row (no `xp_awarded` on the record); timestamps are tz-aware UTC.
- [ ] Creating a session for a `student_id` with no `student` row is rejected by the FK (IntegrityError), nothing inserted.
- [ ] All identifiers/values are bound parameters; DB errors propagate (not swallowed).
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
docker run -d --rm --name smp3-01-pg -e POSTGRES_USER=study_tutor \
  -e POSTGRES_PASSWORD=test -e POSTGRES_DB=study_tutor -p 55432:5432 postgres:16
export STUDY_TUTOR_PG_DSN="postgresql://study_tutor:test@localhost:55432/study_tutor"
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m pytest tests/integration/knowledge/store/test_postgres_create_get_session.py -v
.venv/bin/python -m pytest tests/unit/knowledge/store/ -v
.venv/bin/ruff check src/study_tutor/knowledge/store/postgres.py
docker stop smp3-01-pg
```

## Implementation Notes

- uuid4 for `session_id` (matches the retired in-memory store + FakeStudentStore).
- Compute `now = datetime.now(timezone.utc)` app-side and bind it (deterministic/testable, tz-aware).
- Reuse the engine-acquisition shape the write methods already use (`if self._pool ... elif self._engine ...`).
- `resume_if_active` correctness for single-user is last-writer-wins (contract §4); a transaction with the
  SELECT + conditional INSERT is sufficient — do NOT add advisory locks or a unique index.

## Boundary-test discipline (read the retro)

Scope-guard tests may assert `NotImplementedError` ONLY for the session methods NOT implemented yet in THIS
feature — but note SMP3-02/03 implement the rest, so do NOT assert NotImplementedError for
list_sessions/get_turns/append_turn/end_session (a later task in THIS feature implements them). No
transient-state assertions. (docs/retros/2026-07-03-autobuild-self-defeating-boundary-tests.md)

## BDD Scenarios

From features/durable-cross-device-sessions/durable-cross-device-sessions.feature:
- Starting a session creates a durable session keyed to the learner
- Starting with resume-if-active creates or resumes depending on existing state *(Scenario Outline)*
- Acting on an unknown session reports the session as not found *(get_session None → adapter maps not-found)*
