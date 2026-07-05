---
id: TASK-APP1-04
title: "serve-http CLI subcommand + production wiring (store, tutor loop, events, READY health)"
task_type: feature
feature_id: FEAT-APP-001
wave: 4
implementation_mode: task-work
complexity: 6
dependencies: [TASK-APP1-03]
parent_feature_spec: features/http-app-access-adapter/http-app-access-adapter_summary.md
---

## Objective

The production wiring: a `serve-http` click subcommand beside `serve` /
`serve-nats` in `src/study_tutor/cli/main.py` that boots the TASK-APP1-03 app
on uvicorn with everything real attached — the Postgres store, the same tutor
loop the MCP adapter uses, and the pinned event emission. This is where the
call-site-drift retro bites hardest: **injected-dependency unit tests are not
production-wiring coverage — test the wired path.**

## Scope

**In scope**
- `serve-http` subcommand: `--port` (default **8100**), `--host`, log-level;
  runs uvicorn over the app factory.
- Store wiring via `knowledge.store.provider` from `STUDY_TUTOR_PG_DSN` —
  **fail fast** when the DSN is missing or the store is unreachable at boot:
  refuse to report ready, exit non-zero, error message names the store as the
  cause. Never serve requests that can only fail.
- Tutor loop: reuse the exact `reply_fn` construction the MCP `serve` path
  uses (shared helper — do NOT re-implement the loop). A tutor-loop failure
  mid-turn returns the server-error envelope; session stays active/resumable.
- Events: wire the EventBus so `session.started` / `session.turn_completed` /
  `session.completed` are emitted with the same pinned payloads as the MCP
  path (contract §8; one vocabulary for all transports).
- `GET /healthz` route + **READY boot smoke**: a test that starts the real
  `serve-http` entrypoint (subprocess or server-in-thread against an ephemeral
  DSN) and asserts the bound port answers `/healthz` — asserting READY, not
  "no crash within N seconds" (SIGTERM-accepted-as-success is the exact retro
  failure).

**Out of scope**
- Reset endpoint + seed (TASK-APP1-05); compose (TASK-APP1-06).
- ANY change to `serve` / `serve-nats` behaviour — this task is additive to
  `cli/main.py`; sweep and leave every existing call site intact (FEAT-SMP-004
  will renovate that file after this feature lands).

## Acceptance Criteria

- [ ] `study-tutor serve-http` boots on :8100 with a valid DSN and answers
      `GET /healthz` (READY smoke green against an ephemeral Postgres)
- [ ] Boot with missing/unreachable store exits non-zero before binding
      traffic, error names the store
- [ ] A `turn` over the wired path uses the shared tutor-loop builder (no
      duplicated LLM/orchestration code — verified by import, not copy)
- [ ] Tutor-loop failure mid-turn: server-error envelope returned, session
      still active and resumable, retried turn succeeds (fake failing reply_fn)
- [ ] The three session events are emitted with the pinned payload shape
- [ ] `serve` and `serve-nats` untouched: existing
      `tests/unit/mcp/test_stdio_discipline.py` and adapter/router suites green
- [ ] All modified files pass project-configured lint/format checks with zero
      errors

## Test Requirements

READY boot smoke (ephemeral DSN; skip when `STUDY_TUTOR_PG_DSN` unset, per the
repo's CI-safe convention); fail-fast boot test; wired-path turn test with a
stubbed reply_fn; event-payload assertions. NEVER point tests at the NAS — the
scope-guard test (no `whitestocks`/`5434` in test config) applies.

## Coach Validation

- `pytest tests/unit/ -q` green + the new boot smoke with DSN exported.
- Verify `cli/main.py` diff is additive (new subcommand + shared-helper
  extraction only; `serve`/`_build_nats_runtime` call sites unchanged).
