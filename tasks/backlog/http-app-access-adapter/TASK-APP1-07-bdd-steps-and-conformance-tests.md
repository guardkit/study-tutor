---
id: TASK-APP1-07
title: "BDD step definitions + binding-conformance + MCP-freeze regression + full-suite gate"
task_type: testing
feature_id: FEAT-APP-001
wave: 7
implementation_mode: task-work
complexity: 5
dependencies: [TASK-APP1-06]
parent_feature_spec: features/http-app-access-adapter/http-app-access-adapter_summary.md
consumer_context:
  - task: TASK-APP1-01
    consumes: API-session-http-binding.md
    framework: "pytest (conformance assertions)"
    driver: "pytest-bdd"
    format_note: "The conformance test parses the doc's verb table and asserts the served route set matches it exactly"
---

## Objective

Make the 34-scenario spec executable and hold the implementation to the frozen
binding doc. An undefined BDD step is a FAILURE, not `pending` (guardkit retro
`54ab79fd`).

## Scope

**In scope**
- pytest-bdd step definitions for
  `features/http-app-access-adapter/http-app-access-adapter.feature` —
  hermetic where possible (TestClient + fakes), DB-backed steps behind the
  ephemeral-DSN skip guard. The concurrency scenario ("Simultaneous
  resume-if-active starts converge") is hermetic-tier ONLY.
- Binding-conformance test: parse the doc's verb table; assert the served
  route set (paths, methods) and the status-per-error_type mapping match it
  exactly (the "Every served endpoint matches the published binding table"
  scenario).
- MCP-freeze regression: assert the four MCP tools' names + descriptions are
  byte-for-byte unchanged (contract §10).
- Full-suite gate: `pytest tests/` green minus ONLY the 3 pre-existing
  NATS-smoke failures (`tests/integration/test_nats_smoke.py` — known,
  unrelated); `pytest features/http-app-access-adapter` green with zero
  undefined steps.

**Out of scope**
- The Mac-side live suite (`app/test_live/` — Mac-built, runs attended in
  TASK-APP1-08); any production code change beyond test fixtures (defects
  found here are fixed in place but scope-checked by the Coach).

## Acceptance Criteria

- [ ] `pytest features/http-app-access-adapter` — all tagged scenarios pass;
      ZERO undefined/pending steps
- [ ] Binding-conformance test green and would fail on any route/status drift
      from the doc
- [ ] MCP tool surface asserted byte-for-byte unchanged
- [ ] `pytest tests/` (ephemeral DSN exported) — 0 new failures vs the
      baseline (full minus NATS ≈ 1252 passed on `main` pre-feature)
- [ ] No test targets host `whitestocks` or port `5434` (scope-guard stays
      green)

## Test Requirements

This IS the test task. Runner notes: DB-backed steps skip without
`STUDY_TUTOR_PG_DSN`; export an ephemeral throwaway Postgres to run them.

## Coach Validation

- `pytest features/http-app-access-adapter -q` → no undefined steps.
- `pytest tests/ --ignore=tests/integration/test_nats_smoke.py -q` → green.
- Verify the conformance test actually reads the doc (not a hardcoded copy of
  the table).
