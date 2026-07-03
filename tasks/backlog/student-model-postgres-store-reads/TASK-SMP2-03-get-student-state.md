---
id: TASK-SMP2-03
title: "get_student_state: aggregate learner snapshot over the Postgres schema"
task_type: feature
feature_id: FEAT-SMP-002
wave: 3
implementation_mode: task-work
complexity: 6
dependencies: [TASK-SMP2-02]
parent_feature_spec: features/student-model-postgres-store-reads/student-model-postgres-store-reads_summary.md
---

## Objective

Fill `PostgresStudentStore.get_student_state`
(`src/study_tutor/knowledge/store/postgres.py:253-254`, currently `NotImplementedError`)
with the aggregate learner snapshot the handlers read. Returns the
`store.entities.StudentState` (`store/entities.py:88-107`), NOT the graph `queries.StudentState`.

Signature is fixed by the port (`store/port.py:68-72`) — do not change it:

```python
async def get_student_state(self, student_id: str) -> StudentState:
```

## Field-by-field contract

Build `store.entities.StudentState` as follows:

| Field | Source |
|---|---|
| `empty` | `True` when NO `student` row for `student_id` (return `StudentState(empty=True)` immediately). Else `False`. |
| `stale` | Always `False` — the Graphiti-era stale-fact flag is retired (ASSUM-005). |
| `student_id` | the argument |
| `year_group`, `target_grade` | from the `student` row |
| `subjects`, `current_texts` | always `[]` — the Postgres schema models neither (ASSUM-002). |
| `topic_confidences` | one `TopicConfidenceSnapshot(topic_name, band, percentage, last_revised_at)` per `topic_confidence` row (NOTE: Snapshot uses `topic_name`, not `topic_ref`). |
| `recent_misconceptions` | one `MisconceptionSnapshot(topic_name, text, observed_at)` per `misconception` row within the 30-day window (`MisconceptionSnapshot` has NO band field). |
| `most_recent_session_id` | `session_id` of the student's latest session by `last_activity` (ASSUM-004); `None` when the student has no sessions. |

`TopicConfidenceSnapshot` / `MisconceptionSnapshot` are the read-projection models in
`store/entities.py:71-85` — distinct from the domain `TopicConfidence`/`Misconception` that
TASK-01/02 return. Same rows, different shape.

## Scope

**In scope**
- `get_student_state` body: (1) fetch the `student` row → early `empty=True` return if absent;
  (2) read `topic_confidence` rows → `TopicConfidenceSnapshot[]`; (3) read `misconception` rows
  within the 30-day window → `MisconceptionSnapshot[]`; (4) read latest `session.session_id` by
  `last_activity DESC LIMIT 1` → `most_recent_session_id`; assemble the `StudentState`.
- Reuse the row-reading logic from TASK-01/02 where natural (e.g. a private `_select_confidence_rows`
  / `_select_recent_misconception_rows` helper) rather than duplicating SQL — but project to the
  Snapshot shape here, not the domain entity.

**Out of scope**
- Session CRUD → FEAT-SMP-003 (leave raising `NotImplementedError`). Write methods DONE.
- Do NOT populate `subjects`/`current_texts` from anywhere (no source exists) — leave `[]`.
- Do NOT compute `stale` — leave `False`.

## Acceptance Criteria

- [ ] A known learner returns `StudentState(empty=False)` with `student_id`, `year_group`,
      `target_grade` from the `student` row.
- [ ] `topic_confidences` is a list of `TopicConfidenceSnapshot` (one per row, `topic_name`
      field) and `recent_misconceptions` is a list of `MisconceptionSnapshot` (one per in-window
      row, no band field), both matching what `get_topic_confidences`/`get_recent_misconceptions`
      would return for the same data.
- [ ] `recent_misconceptions` uses the SAME inclusive 30-day window as `get_recent_misconceptions`.
- [ ] `most_recent_session_id` is the `session_id` of the student's session with the greatest
      `last_activity`; `None` when the student has no sessions.
- [ ] `subjects == []`, `current_texts == []`, and `stale is False` for every known learner
      (regardless of data).
- [ ] An unknown `student_id` returns `StudentState(empty=True)` (and callers can branch on
      `empty` without inspecting other fields) — the method does NOT raise for unknown learner.
- [ ] All timestamps are timezone-aware UTC; all identifiers are bound parameters.
- [ ] DB/connection errors propagate (not swallowed) so `knowledge.store.reads.get_student_state`
      degrades to `StudentState(empty=True)`.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
docker run -d --rm --name smp2-03-pg -e POSTGRES_USER=study_tutor \
  -e POSTGRES_PASSWORD=test -e POSTGRES_DB=study_tutor -p 55432:5432 postgres:16
export STUDY_TUTOR_PG_DSN="postgresql://study_tutor:test@localhost:55432/study_tutor"
.venv/bin/python -m alembic upgrade head

.venv/bin/python -m pytest tests/integration/knowledge/store/test_postgres_get_student_state.py -v
.venv/bin/python -m pytest tests/unit/knowledge/store/ -v
.venv/bin/ruff check src/study_tutor/knowledge/store/postgres.py
docker stop smp2-03-pg
```

## Implementation Notes

- Do the `student`-row existence check FIRST and short-circuit to `empty=True` — avoids running
  three more queries for a non-existent learner and matches the FakeStudentStore contract
  (`tests/unit/knowledge/store/fakes.py:84-124`).
- The three child reads can run on one connection; a single `async with engine.connect()` for
  all four SELECTs is fine (read-only, no txn). Do not open four engines.
- `most_recent_session_id`: `SELECT session_id FROM session WHERE student_id = :sid ORDER BY
  last_activity DESC LIMIT 1` — this is where the Postgres adapter improves on FakeStudentStore
  (which returns `None`); the session rows exist because W1's `record_session_completion` writes them.
- Watch the projection shapes: `TopicConfidenceSnapshot.topic_name` (NOT `topic_ref`) and
  `MisconceptionSnapshot` has only `topic_name`/`text`/`observed_at` (NO
  `confidence_band_at_observation`). Do not reuse the domain entity here.

## Boundary-test discipline (read the retro)

Scope-guard tests may assert `NotImplementedError` ONLY for the SESSION-CRUD methods. Do NOT
assert it for any read method (all three are now implemented across TASK-01/02/03). No
transient-state assertions ("subjects source not wired yet" etc.).

## BDD Scenarios

- Reading the snapshot for a known learner returns her profile, confidences, and recent misconceptions
- Reading a learner who has no records yet returns an empty-but-available snapshot
- Reading the snapshot for an unknown learner returns the empty snapshot
- The snapshot reports no subjects or current texts because the store does not model them
- The snapshot reports the learner's most recent session
