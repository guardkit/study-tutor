---
id: TASK-STV1-001
title: Add GET /api/version with tests
task_type: feature
feature_id: FEAT-STV1
wave: 1
implementation_mode: task-work
complexity: 3
dependencies: []
conformance:
  ac_paths: true
  rules:
  - id: R-STV1-ROUTE
    type: token_coverage
    paths:
    - src/study_tutor/http/app.py
    require_tokens:
    - "/api/version"
  - id: R-STV1-TESTS
    type: assert_command
    command: "pytest tests/ -k 'version' -v --tb=short"
---

# TASK-STV1-001: Add GET /api/version with tests

## Objective

Add a read-only `GET /api/version` route to the session HTTP app, following the
EXACT additive-read-verb precedent already in the route table (the
`/api/student-model` route, binding §2.2): additive, read-only, mounted beside
the existing verbs, and auth-consistent with them.

## Acceptance Criteria

- **AC-001**: `GET /api/version` returns HTTP 200 with JSON
  `{"service": "study-tutor", "version": "<the pyproject version>"}`.
- **AC-002**: The version value is read from the installed package metadata
  (`importlib.metadata.version`) with the pyproject value as the source of
  truth — never a hardcoded duplicate string.
- **AC-003**: Auth posture matches the additive-read-verb precedent: the route
  is treated EXACTLY like `/api/student-model` — read its mounting and any
  bearer handling in `src/study_tutor/http/app.py` and mirror it byte-consistently.
- **AC-004**: The frozen route-table comment discipline is preserved: the new
  Route line carries a comment naming this as an additive read verb per
  binding §2.2, exactly as the student-model line does.
- **AC-005**: Non-GET methods are rejected consistently with the app's existing
  behaviour for wrong-method requests; a test asserts it.
- **AC-006**: Tests cover: 200 + shape, the version matches package metadata,
  wrong method. The full non-integration suite stays green
  (`pytest tests/ --ignore=tests/integration`).
- **AC-007**: NO other route, contract file, or frozen surface is touched. The
  binding doc itself (docs/design/contracts/API-session-http-binding.md) is NOT
  edited by this task — if the builder believes the doc must change, that is a
  STOP-and-report, not an edit.

## Implementation Notes

- Route table: `src/study_tutor/http/app.py` (~:580) — one added Route line +
  one small handler, mirroring the student-model handler's shape.
- No DB, no NATS, no session state. Read-only.

## Test Commands (Coach Validation)

```bash
pytest tests/ -k "version" -v --tb=short
```
