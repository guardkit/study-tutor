---
id: TASK-SMP2-07
title: "BDD step defs + fake-store read tests + ephemeral-PG read integration tests"
task_type: testing
feature_id: FEAT-SMP-002
wave: 7
implementation_mode: task-work
complexity: 6
dependencies: [TASK-SMP2-06]
parent_feature_spec: features/student-model-postgres-store-reads/student-model-postgres-store-reads_summary.md
---

## Objective

Wire the FEAT-SMP-002 BDD feature file to executable step definitions, add fast fake-store read
tests for caller behaviour, and add ephemeral-Postgres integration tests that exercise the three
read methods and the planner repoint against real SQL. This is the feature's oracle and its
composition guard.

## Scope

**In scope**
- pytest-bdd step definitions for
  `features/student-model-postgres-store-reads/student-model-postgres-store-reads.feature`
  (all 19 scenarios / 2 outlines). Steps drive the store methods and `store.reads` /
  `load_planner_inputs` + `plan_session`, using the `FakeStudentStore` and/or an ephemeral PG.
- Fake-store read tests (`tests/unit/knowledge/store/`): the read methods on `FakeStudentStore`
  already exist — add/extend caller tests through `store.reads.get_student_state` /
  `load_planner_inputs` for the degradation matrix (no store wired → empty/unavailable; reachable
  but recordless → empty/available; read raises → empty/unavailable).
- Ephemeral-PG integration tests (`tests/integration/knowledge/store/`) for the real adapter:
  `get_topic_confidences`, `get_recent_misconceptions` (window edge + band-at-obs join),
  `get_student_state` (empty sentinel, snapshots, most_recent_session_id, subjects/texts empty),
  seed→read round-trips using the W1 write methods to populate, then read back.
- A guard test asserting no test targets host `whitestocks` / port `5434` (NAS scope rule),
  mirroring the W1 guard.

**Out of scope**
- New adapter logic (belongs to TASK-01/02/03); the planner repoint (TASK-05); the removal (TASK-06).
- Session-CRUD tests → FEAT-SMP-003.

## Acceptance Criteria

- [ ] Every scenario in the feature file resolves to a step definition and passes (no `pending`
      steps left for the read-path scenarios); the file's `@task:` tags route scenarios to
      TASK-SMP2-01..05 as the per-task oracle.
- [ ] Fake-store degradation matrix is covered: (no store wired → `StudentState(empty=True)` /
      `PlannerInputs(available=False)`), (reachable + recordless → `empty=True` but
      `available=True` for planner inputs), (read raises → degrade, no exception).
- [ ] Ephemeral-PG integration tests populate via the W1 write methods and read back through all
      three read methods, asserting: band read-back at boundaries; inclusive 30-day window edge;
      band-at-observation LEFT-JOIN default `"struggling"`; `most_recent_session_id` = latest
      session; `subjects`/`current_texts` empty; `stale is False`; unknown learner → empty.
- [ ] The planner repoint is exercised end-to-end: with a wired store, `plan_session` produces a
      plan whose context carried store-backed inputs; with the store unreachable, a baseline plan.
- [ ] A scope guard asserts no test connects to host `whitestocks` or port `5434`.
- [ ] `pytest tests/` (whole suite) is green (DB tests skip cleanly when `STUDY_TUTOR_PG_DSN` unset — CI-safe).

## Coach Validation

```bash
docker run -d --rm --name smp2-07-pg -e POSTGRES_USER=study_tutor \
  -e POSTGRES_PASSWORD=test -e POSTGRES_DB=study_tutor -p 55432:5432 postgres:16
export STUDY_TUTOR_PG_DSN="postgresql://study_tutor:test@localhost:55432/study_tutor"
.venv/bin/python -m alembic upgrade head

# BDD oracle (pytest-bdd) + fake + integration
.venv/bin/python -m pytest features/ tests/unit/knowledge/store tests/integration/knowledge/store -v
# Whole suite (composition guard) — DB tests live because the DSN is exported
.venv/bin/python -m pytest tests/ -q
docker stop smp2-07-pg
```

## Implementation Notes

- Reuse `FakeStudentStore` (`tests/unit/knowledge/store/fakes.py`) — its read methods are already
  implemented and match the contract; add `add_student` + write calls to seed fixtures.
- For "store unreachable" scenarios against the fake, use `set_unreachable(True)` (ping) and/or a
  fake whose read raises; for the real adapter, point the DSN at a stopped container or an invalid
  port and assert `store.reads` degrades (never let the raw asyncpg error escape).
- Integration tests must run against the EPHEMERAL container only (non-5434 port). The guard test
  is not optional — it is what enforces the runbook scope rule for the whole suite.
- Keep DB-backed tests skippable when `STUDY_TUTOR_PG_DSN` is unset (parity with W1's CI-safe suite).

## Boundary-test discipline (read the retro)

Assert lasting invariants, not transient state. Do NOT assert "method X raises NotImplementedError"
for any read or write method (all implemented) — only session-CRUD methods may carry that assertion,
and only in the adapter scope-guard test, since they are out of scope for the WHOLE feature.

## BDD Scenarios

All 19 in `student-model-postgres-store-reads.feature` (this task makes them executable).
