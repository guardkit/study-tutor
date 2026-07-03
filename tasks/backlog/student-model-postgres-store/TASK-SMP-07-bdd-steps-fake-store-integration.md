---
id: TASK-SMP-07
title: BDD step definitions + in-memory fake store + ephemeral-Postgres integration tests
task_type: testing
feature_id: FEAT-SMP-001
wave: 5
implementation_mode: task-work
complexity: 6
dependencies: [TASK-SMP-06]
parent_feature_spec: features/student-model-postgres-store/student-model-postgres-store_summary.md
---

# Task: BDD step definitions + in-memory fake store + ephemeral-Postgres integration tests

## Objective

Make the FEAT-SMP-001 write-path `.feature` executable. Deliver three test assets:

1. **pytest-bdd step definitions** binding every WRITE-PATH scenario in
   `features/student-model-postgres-store/student-model-postgres-store.feature` (migration, `ping`,
   F1, F2, `record_session_completion`, idempotency, atomicity, and the security / data-integrity
   edge cases) to executable steps.
2. **`FakeStudentStore`** — an in-memory implementation of the **full** `StudentStore` Protocol
   (`src/study_tutor/knowledge/store/port.py`, all 13 methods) for fast, DB-free caller tests.
3. **Ephemeral-Postgres integration tests** that run the Alembic migration + the three write methods
   against a throwaway Postgres (testcontainers or a local container on a **non-5434** port), proving
   the real transactional / migration behaviour the fake cannot. The harness is **hermetic**: a guard
   test asserts no test ever points at the NAS durable instance (host `whitestocks…` / port `5434` /
   `STUDY_TUTOR_PG_DSN`).

This is the test seam that verifies TASK-SMP-06's filled `PostgresStudentStore` (`ping` +
`record_session_completion` + `record_misconception` + `apply_confidence_update`) and the first
migration.

## Scope

**In scope**

- `FakeStudentStore` implementing every method on the `StudentStore` Protocol
  (`ping`, `get_student_state`, `get_topic_confidences`, `get_recent_misconceptions`,
  `record_session_completion`, `record_misconception`, `apply_confidence_update`,
  `create_session`, `get_session`, `list_sessions`, `append_turn`, `get_turns`, `end_session`) —
  dict-backed, reusable by later FEAT-SMP-002/003 caller tests. Write-path methods must reproduce the
  contracted behaviour (band derivation via `student_model.confidence_band_for`, idempotency on
  `session_id`, unknown-learner rejection, ±range validation, append-only F1).
- pytest-bdd step defs (`scenarios(...)` bound to the feature file) resolving the store under test
  from a `store` fixture, so the same steps drive both the fake (fast subset) and the ephemeral
  Postgres (full suite).
- Ephemeral-Postgres fixture: spin up a throwaway container, `alembic upgrade head`, hand back an
  engine/DSN on a **non-5434** port; tear down after the session. Skip with a clear reason when
  Docker/testcontainers is unavailable (so a Docker-less CI leg stays green) — but the suite MUST
  pass where Docker is available.
- Hermeticity guard test (## Seam Tests below).

**Out of scope**

- Filling `PostgresStudentStore` bodies or authoring the migration — that is TASK-SMP-06 (this task
  consumes it).
- READ-path scenarios (there are none in this `.feature`; reads are FEAT-SMP-002) and session-CRUD
  step defs (FEAT-SMP-003). `FakeStudentStore` may implement those methods with in-memory behaviour
  for reuse, but no scenarios here exercise them.
- Hand-tagging scenarios with `@task:TASK-SMP-*` — those tags are applied by `/feature-plan` Step 11.
- Any write against the NAS durable instance.

## Acceptance Criteria

- [ ] pytest-bdd step definitions exist for all 28 write-path scenarios listed under **## BDD
      Scenarios**; `pytest --collect-only` on the bdd module shows zero undefined/unbound steps.
- [ ] The full write-path scenario subset **passes** against the ephemeral Postgres backend
      (migration up/no-op/down, `ping`, F1, F2, `record_session_completion`, idempotency, atomicity,
      concurrency, UTC round-trip, security/data-integrity edges).
- [ ] `FakeStudentStore` implements **every** method of the `StudentStore` Protocol; a conformance
      test asserts `isinstance(FakeStudentStore(...), StudentStore)` (runtime-checkable Protocol) and
      that each method is an awaitable coroutine — no method left unimplemented / raising
      `NotImplementedError`.
- [ ] The fast caller subset (pure-behaviour scenarios: band derivation, ±range rejection,
      unknown-learner rejection, append-only F1, idempotent completion) passes against
      `FakeStudentStore` with no database, proving fake↔adapter parity on those behaviours.
- [ ] A **hermeticity guard test** asserts no test in the suite targets the NAS host or port `5434`,
      and does not read `STUDY_TUTOR_PG_DSN` as a live target — every DB-backed test uses the ephemeral
      fixture's own DSN on a non-5434 port. (See ## Seam Tests.)
- [ ] Band-derivation scenarios assert the 40/60/80 taxonomy (`struggling`<40, `developing` 40-59,
      `secure` 60-79, `mastered` 80-100) — matching the resolved `confidence_band_for`.
- [ ] Idempotency + atomicity scenarios assert exactly-once XP and full rollback (nothing persisted on
      any partial/invalid/failed-commit path) against the real Postgres backend.
- [ ] Append-only F1 scenario asserts a replayed standalone `record_misconception` yields a **second**
      row (ASSUM-006, no dedup), distinct from `record_session_completion`'s `session_id` idempotency.

## Coach Validation

```bash
# Fast, DB-free: fake Protocol conformance + fast caller subset
.venv/bin/python -m pytest tests/unit/knowledge/store/test_fake_student_store.py -q

# Hermeticity guard — must pass with no Postgres running
.venv/bin/python -m pytest tests/integration/store/test_hermetic_guard.py -q

# Full write-path BDD suite against the ephemeral Postgres (requires Docker)
.venv/bin/python -m pytest tests/integration/store/ -q

# Confirm every scenario has bound steps (zero undefined-step warnings)
.venv/bin/python -m pytest tests/integration/store/test_write_path_bdd.py --collect-only -q

# Prove nothing in the suite references the NAS target
! grep -rInE '5434|whitestocks|STUDY_TUTOR_PG_DSN' tests/integration/store/ tests/unit/knowledge/store/ \
  | grep -v 'test_hermetic_guard'   # only the guard may name them, as forbidden literals
```

## Implementation Notes

- **Stack**: `pytest-bdd>=8.1,<9` (already in `pyproject.toml`), `pytest-asyncio` (`asyncio_mode=auto`
  is set), SQLAlchemy 2.0 async Core + asyncpg, Alembic. Add `testcontainers[postgres]` (or drive a
  throwaway `docker run` on a random high port) as a test-only dependency.
- **Store fixture**: step defs read the store from a `store` fixture. Run the full feature against the
  ephemeral Postgres (source of truth for transactional/migration behaviour); additionally run the
  pure-behaviour subset against `FakeStudentStore`. Do NOT try to parametrise the whole suite across
  both backends — the migration/atomicity/concurrency/fault-injection scenarios have no meaning on the
  fake.
- **Postgres-only scenarios** (need real DB semantics; fake cannot stand in): the three `@migration`
  scenarios, `@atomicity` rollback (partial-failure, invalid-batch, dropped-connection), `@concurrency`
  (two concurrent completions, concurrent confidence upserts), commit-failure / unreachable fast-fail,
  and the UTC `TIMESTAMPTZ` round-trip.
- **Fault injection**: simulate "cannot commit" / "connection drops mid-transaction" by monkeypatching
  the adapter's session/connection to raise on flush/commit (or closing the pool mid-write) — assert
  the exception surfaces to the caller (ASSUM-008) and a follow-up read shows prior state intact.
- **Concurrency**: drive two `asyncio.gather`'d `record_session_completion` calls under the same
  `session_id`; assert exactly one row set and XP counted once (idempotency on the `session_id` PK).
- **Migration reversibility**: exercise `alembic upgrade head` → assert all seven structures present →
  `alembic downgrade base` → assert absent (ASSUM-010); a second `upgrade head` on an at-head DB is a
  no-op (existing data preserved).
- **Band boundaries**: assert the 40/60/80 examples table exactly; out-of-range (-1, 101) rejected by
  Pydantic `ge=0/le=100` + `confidence_band_for` `ValueError` + schema CHECK, with nothing stored.
- **Security/data-integrity**: SQL-control topic name (`Macbeth'); DROP TABLE …`) stored as a literal
  via parameterised writes (all structures still present after); control/null chars neutralised
  (ASSUM-007); 500-char cap (ASSUM-004); instruction-like text stored opaque, no band change
  (ASSUM-005).
- **Unknown learner**: `apply_confidence_update` / write for `ghost` rejected (FK / fake guard),
  nothing stored (ASSUM-003).
- **Do not hand-tag** scenarios — `@task:TASK-SMP-*` tags are added by `/feature-plan` Step 11. Bind
  steps by the feature file + scenario text only.
- Suggested layout: `tests/unit/knowledge/store/fakes.py` (the `FakeStudentStore`) +
  `test_fake_student_store.py` (conformance + fast subset); `tests/integration/store/conftest.py`
  (ephemeral-pg fixture + `store` fixture), `test_write_path_bdd.py` (`scenarios(...)` + steps),
  `test_hermetic_guard.py`.

## Seam Tests

The store's real DSN (`STUDY_TUTOR_PG_DSN` → the NAS instance on `:5434`) is the one target these
tests must **never** touch (runbook scope rule: the NAS holds a minor's durable data). The guard
encodes that negative contract.

```python
"""Hermeticity guard — no test may point at the NAS durable Postgres."""
import pathlib
import re

import pytest

_FORBIDDEN = re.compile(r"5434|whitestocks|STUDY_TUTOR_PG_DSN")
_STORE_TESTS = pathlib.Path(__file__).parent            # tests/integration/store/
_THIS = pathlib.Path(__file__).name                     # this guard may name the forbidden tokens


@pytest.mark.integration_contract("STUDY_TUTOR_PG_DSN")
def test_no_store_test_targets_the_nas_instance():
    """Every DB-backed test uses the ephemeral fixture's own DSN on a non-5434
    port. Only this guard file may mention the forbidden NAS tokens (as the
    literals it forbids)."""
    offenders = []
    for path in _STORE_TESTS.rglob("*.py"):
        if path.name == _THIS:
            continue
        if _FORBIDDEN.search(path.read_text(encoding="utf-8")):
            offenders.append(path.name)
    assert not offenders, f"tests reference the NAS durable Postgres: {offenders}"


def test_ephemeral_dsn_is_not_the_nas_port(pg_dsn):
    """The ephemeral fixture's DSN must not resolve to the NAS port 5434."""
    assert ":5434/" not in pg_dsn
    assert "whitestocks" not in pg_dsn
```

## BDD Scenarios

Step definitions in this task make the following scenarios pass (exact titles from the `.feature`):

- Applying the student-model migration to an empty database creates the learner-state schema
- Recording a completed session persists its XP, confidence updates, and misconceptions together
- Recording an observed misconception attaches it to the learner and topic synchronously
- Applying a confidence update stores the resolved percentage and derives its band
- Re-delivering the same completed session records it only once
- The store reports healthy when the database is reachable
- A resolved confidence percentage is stored with the expected band
- A confidence update outside the valid percentage range is rejected
- A learner year group is accepted only within the secondary-school range
- Misconception text is stored up to the length cap and truncated beyond it
- Recording a completed session with no confidence updates and no misconceptions still records the session
- Recording learner state for an unknown learner is rejected
- Recording a misconception missing its topic or its text is rejected
- A session-completion write that cannot commit surfaces the failure instead of silently dropping it
- A partial failure while recording a completed session rolls back every change
- Two concurrent deliveries of the same session completion are recorded once
- Concurrent confidence updates for the same topic resolve to a single stored value
- Re-applying the migration when already at the latest revision changes nothing
- Reversing the migration returns the database to an empty student-model schema
- A misconception containing instruction-like text is stored as opaque content
- The first real confidence update overwrites the never-revised baseline timestamp
- A topic name containing database-control characters is stored as literal text
- Misconception text containing null and control characters is stored without corrupting the record
- A replayed standalone misconception is appended, not deduplicated, in W1
- A session completion whose confidence batch contains an invalid percentage records nothing
- Learner-state timestamps are stored and returned in UTC regardless of the caller's timezone
- A write attempted while the database is unreachable fails fast and leaves prior state intact
- A connection dropped mid-transaction leaves no partial session recorded
