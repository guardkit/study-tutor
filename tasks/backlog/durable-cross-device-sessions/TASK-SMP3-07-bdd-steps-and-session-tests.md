---
id: TASK-SMP3-07
title: "BDD step defs + fake-store parity + ephemeral-PG session integration + surface regression"
task_type: testing
feature_id: FEAT-SMP-003
wave: 7
implementation_mode: task-work
complexity: 6
dependencies: [TASK-SMP3-06]
parent_feature_spec: features/durable-cross-device-sessions/durable-cross-device-sessions_summary.md
---

## Objective

Wire the FEAT-SMP-003 feature file to executable step definitions, add fast fake-store caller tests, add
ephemeral-Postgres integration tests for the durable session lifecycle, and lock the MCP-surface regression.
This is the feature's oracle and its composition guard.

## Scope

**In scope**
- pytest-bdd step definitions for
  `features/durable-cross-device-sessions/durable-cross-device-sessions.feature` (all 22 scenarios / 1 outline),
  driving `SessionService` (+ the store) and, for the surface scenario, the MCP adapter/server. Use
  `FakeStudentStore` and/or an ephemeral PG. **Every scenario must resolve to a step definition** (no
  StepDefinitionNotFoundError — see the guardkit retro on the missing bare-form step).
- Fake-store parity tests (`tests/unit/session/`): SessionService verbs over `FakeStudentStore` — ownership
  guard (two-student `SessionForbidden`), status guard (`SessionEnded`), unknown → `SessionNotFoundError`,
  resume returns transcript, zero-turn end writes no completion.
- Ephemeral-PG integration tests (`tests/integration/knowledge/store/`) for the 6 real adapter methods:
  create/resume, get, list (order + limit), append (0-based monotonic bump), get_turns (order), end (transition),
  durability round-trip (write → re-read), and the record_session_completion idempotency on session_id.
- **MCP-surface regression**: confirm `tests/unit/mcp/test_adapter.py` + `tests/unit/adapters/test_command_router.py`
  stay green after the cutover (extend them only to inject a fake-backed SessionService; do NOT weaken their
  surface assertions).
- The NAS scope-guard test (no test targets host `whitestocks` / port `5434`) — reuse the W1/W2 guard.

**Out of scope**
- New adapter/store logic (SMP3-01..06). HTTP/WS transport tests (mobile /goal).

## Acceptance Criteria

- [ ] Every scenario in the feature file resolves to a step definition and passes (no `pending`/undefined steps
      for the in-scope scenarios); `@task:` tags route scenarios to SMP3-01..06 as the per-task oracle.
- [ ] Fake-store parity covers the guard matrix: two-student `SessionForbidden`, `SessionEnded` on ended,
      `SessionNotFoundError` on unknown, resume transcript, zero-turn end → no completion write.
- [ ] Ephemeral-PG integration exercises all 6 methods + durability round-trip + completion idempotency, asserting
      0-based monotonic turn indices, newest-first list with limit, and the ended transition.
- [ ] The MCP-surface regression tests pass unchanged in substance (4 tool names, `"Marks session ended."`,
      `{session_id, status:"ended"}` end shape, the error envelopes, the `tutor_start_session→start_session` alias).
- [ ] A scope guard asserts no test connects to host `whitestocks` or port `5434`.
- [ ] `pytest tests/` (whole suite) is green (DB tests skip cleanly when `STUDY_TUTOR_PG_DSN` unset — CI-safe).

## Coach Validation

```bash
docker run -d --rm --name smp3-07-pg -e POSTGRES_USER=study_tutor \
  -e POSTGRES_PASSWORD=test -e POSTGRES_DB=study_tutor -p 55432:5432 postgres:16
export STUDY_TUTOR_PG_DSN="postgresql://study_tutor:test@localhost:55432/study_tutor"
.venv/bin/python -m alembic upgrade head
# BDD oracle (MUST actually run — the retro: an undefined step is a FAILURE, not pending) + fake + integration
.venv/bin/python -m pytest features/durable-cross-device-sessions tests/unit/session tests/unit/mcp tests/unit/adapters tests/integration/knowledge/store -v
# Whole suite (composition guard) — DB tests live because the DSN is exported
.venv/bin/python -m pytest tests/ -q
docker stop smp3-07-pg
```

## Implementation Notes

- `FakeStudentStore` already implements all 6 session methods — build fixtures with `add_student` + create/turn/end.
- For "another learner" (SessionForbidden), add a second student (e.g. "rowan") and assert cross-access is refused.
- For durability, write via one store instance and re-read via a fresh one pointed at the same ephemeral PG.
- Run `pytest features/durable-cross-device-sessions` explicitly — a `StepDefinitionNotFoundError` fails the run
  (guardkit retro 2026-07-04: the Coach missed exactly this on SMP-002; do not repeat).
- Keep DB-backed tests skippable when `STUDY_TUTOR_PG_DSN` is unset (parity with W1/W2 CI-safe suite).

## Boundary-test discipline (read the retro)

Assert lasting invariants. Do NOT assert any session method raises `NotImplementedError` (all 6 implemented).
Verify the WHOLE suite before declaring done — the adapter cutover's blast radius spans mcp/adapters/tutoring tests.

## BDD Scenarios

All 22 in durable-cross-device-sessions.feature (this task makes them executable).
