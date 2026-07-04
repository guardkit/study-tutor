---
id: TASK-SMP3-03
title: "append_turn (atomic turn_count/last_activity bump) + end_session"
task_type: feature
feature_id: FEAT-SMP-003
wave: 3
implementation_mode: task-work
complexity: 5
dependencies: [TASK-SMP3-02]
parent_feature_spec: features/durable-cross-device-sessions/durable-cross-device-sessions_summary.md
---

## Objective

Fill `PostgresStudentStore.append_turn` and `end_session`
(`src/study_tutor/knowledge/store/postgres.py:458-472`, currently `NotImplementedError`) — completing the 6
session methods. FakeStudentStore (`fakes.py:407-480`) is the reference.

Signatures (port `store/port.py:163-184`) — do not change:

```python
async def append_turn(self, *, session_id, role, content, ao_scaffolded=None) -> SessionTurn
async def end_session(self, session_id) -> SessionRecord
```

## Scope

**In scope**
- `append_turn`: ONE transaction (ASSUM-012) —
  - read the session's current `turn_count` (this is the new `turn_index`, 0-based);
  - `INSERT INTO session_turn (session_id, turn_index, role, content, ts, ao_scaffolded)`;
  - `UPDATE session SET turn_count = turn_count + 1, last_activity = :now WHERE session_id = :sid`;
  - return the `SessionTurn`. Unknown session → the FK on `session_turn` rejects the insert (surface the error).
- `end_session`: `UPDATE session SET status='ended', last_activity=:now WHERE session_id=:sid RETURNING *`
  → `SessionRecord`. Unknown session → RETURNING yields no row; raise `SessionNotFoundError`
  (`study_tutor.session.errors.SessionNotFoundError`) OR return per the port contract — match FakeStudentStore
  (it raises ValueError on unknown; prefer the typed SessionNotFoundError so the service/adapter map is clean).

**Out of scope**
- Session-end learner-state completion (confidence/XP write) → TASK-SMP3-05/06 (this method only flips status).
- The other 4 session methods DONE (SMP3-01/02).

## Acceptance Criteria

- [ ] `append_turn` inserts one `session_turn` at `turn_index == the session's current turn_count`, and bumps
      `turn_count` (+1) and `last_activity` in the SAME transaction; returns the `SessionTurn`.
- [ ] The first turn is at index 0, the second at index 1 (monotonic, gap-free).
- [ ] `ao_scaffolded` is persisted when supplied and null otherwise.
- [ ] `append_turn` on an unknown session is rejected (session_turn FK to session) — no partial write.
- [ ] `end_session(id)` flips `status` to `ended`, stamps `last_activity`, and returns the updated `SessionRecord`.
- [ ] `end_session` on an unknown session raises `SessionNotFoundError` (typed; do not silently succeed).
- [ ] `ts`/`last_activity` are tz-aware UTC; identifiers/values are bound parameters; DB errors propagate.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
docker run -d --rm --name smp3-03-pg -e POSTGRES_USER=study_tutor \
  -e POSTGRES_PASSWORD=test -e POSTGRES_DB=study_tutor -p 55432:5432 postgres:16
export STUDY_TUTOR_PG_DSN="postgresql://study_tutor:test@localhost:55432/study_tutor"
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m pytest tests/integration/knowledge/store/test_postgres_append_turn_end_session.py -v
.venv/bin/python -m pytest tests/unit/knowledge/store/ -v
.venv/bin/ruff check src/study_tutor/knowledge/store/postgres.py
docker stop smp3-03-pg
```

## Implementation Notes

- `append_turn`'s turn_index derivation MUST be inside the transaction to avoid a read-then-write race
  (single-user last-writer-wins is acceptable, but do it in one txn per the port's atomic-bump contract).
  Simplest: `INSERT ... SELECT turn_count FROM session WHERE session_id=:sid FOR UPDATE` then the UPDATE — or
  read turn_count into Python inside the `engine.begin()` block, insert, then update. Either is fine; keep it atomic.
- `end_session` RETURNING lets you map the post-update row directly; check `fetchone() is None` → raise.
- `SessionNotFoundError` also subclasses `KeyError` (errors.py) so any residual `except KeyError` still catches it.

## Boundary-test discipline (read the retro)

All 6 session methods are implemented after this task — do NOT leave/add any `NotImplementedError` boundary
assertion for session methods. Test invariants (0-based monotonic index, atomic bump, ended transition).

## BDD Scenarios

- Taking a turn durably records the learner message and the tutor reply
- The first turn is recorded at index zero and the count advances by one per turn
- A session and its turns survive a process restart *(append_turn durability half)*
- Ending a session marks it ended and records the learner-state deltas *(end_session transition half)*
