---
id: TASK-SMP3-02
title: "list_sessions + get_turns (ordered reads)"
task_type: feature
feature_id: FEAT-SMP-003
wave: 2
implementation_mode: task-work
complexity: 4
dependencies: [TASK-SMP3-01]
parent_feature_spec: features/durable-cross-device-sessions/durable-cross-device-sessions_summary.md
---

## Objective

Fill `PostgresStudentStore.list_sessions` and `get_turns`
(`src/study_tutor/knowledge/store/postgres.py:449-469`, currently `NotImplementedError`) — the two
ordered read helpers. FakeStudentStore (`fakes.py:376-458`) is the reference.

Signatures (port `store/port.py:152-178`) — do not change:

```python
async def list_sessions(self, student_id, *, status=None, limit=DEFAULT_SESSION_LIST_LIMIT) -> list[SessionRecord]
async def get_turns(self, session_id) -> list[SessionTurn]
```

`DEFAULT_SESSION_LIST_LIMIT = 20` (`store/port.py:52`).

## Scope

**In scope**
- `list_sessions`: `SELECT * FROM session WHERE student_id=:sid [AND status=:status] ORDER BY
  last_activity DESC LIMIT :limit` → `list[SessionRecord]`. The optional `status` filter is applied only
  when provided. Uses `session_resume_idx (student_id, status, last_activity DESC)`.
- `get_turns`: `SELECT * FROM session_turn WHERE session_id=:sid ORDER BY turn_index` →
  `list[SessionTurn]` (`entities.py:152-161`: session_id, turn_index, role, content, ts, ao_scaffolded).
- Empty list for an unknown student / session with no turns (no existence pre-check needed).

**Out of scope**
- `append_turn`/`end_session` → TASK-SMP3-03 (leave raising). `create_session`/`get_session` DONE (SMP3-01).

## Acceptance Criteria

- [ ] `list_sessions(student_id)` returns the student's sessions newest `last_activity` first, capped at `limit`.
- [ ] The optional `status` filter narrows to `active` or `ended` when supplied; omitted → all statuses.
- [ ] `list_sessions` returns `[]` for a student with no sessions (not an error).
- [ ] `get_turns(session_id)` returns `SessionTurn`s ordered by `turn_index` ascending; `[]` when the session
      has no turns or is unknown.
- [ ] Timestamps (`last_activity`, `ts`) are tz-aware UTC; identifiers/limit are bound parameters.
- [ ] DB errors propagate (not swallowed).
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
docker run -d --rm --name smp3-02-pg -e POSTGRES_USER=study_tutor \
  -e POSTGRES_PASSWORD=test -e POSTGRES_DB=study_tutor -p 55432:5432 postgres:16
export STUDY_TUTOR_PG_DSN="postgresql://study_tutor:test@localhost:55432/study_tutor"
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m pytest tests/integration/knowledge/store/test_postgres_list_sessions_get_turns.py -v
.venv/bin/python -m pytest tests/unit/knowledge/store/ -v
.venv/bin/ruff check src/study_tutor/knowledge/store/postgres.py
docker stop smp3-02-pg
```

## Implementation Notes

- These are read-only — use `engine.connect()` (no transaction). Bind `:limit` (do not string-format).
- Map rows to `SessionRecord`/`SessionTurn` exactly as SMP3-01 mapped `SessionRecord` (reuse a private
  `_row_to_session_record` helper if you add one; keep it consistent).
- `ao_scaffolded` on `SessionTurn` is nullable (`TEXT`) — pass through as `str | None`.

## Boundary-test discipline (read the retro)

Do NOT assert `NotImplementedError` for `append_turn`/`end_session` — SMP3-03 implements them. Assert lasting
invariants (ordering, limit, empty-set), not transient module state.

## BDD Scenarios

- Listing sessions shows the learner's sessions most recently active first
- Listing respects the requested limit and returns the most recent
- Resuming an active session returns its full transcript *(get_turns half)*
