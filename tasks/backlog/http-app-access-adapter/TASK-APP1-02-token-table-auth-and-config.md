---
id: TASK-APP1-02
title: "Token-table auth layer + HTTP config (interim single-user auth, server-side)"
task_type: feature
feature_id: FEAT-APP-001
wave: 2
implementation_mode: task-work
complexity: 5
dependencies: [TASK-APP1-01]
parent_feature_spec: features/http-app-access-adapter/http-app-access-adapter_summary.md
consumer_context:
  - task: TASK-APP1-01
    consumes: API-session-http-binding.md
    framework: "starlette (auth middleware/dependency)"
    driver: "n/a (contract doc)"
    format_note: "Unauthenticated status code + envelope shape and the header-only token rule are fixed by the binding doc"
---

## Objective

Build the interim auth layer for the HTTP adapter: a **static token→student
config table** (contract §3 derivation with config instead of Keycloak). This
is config, not an auth system — D9 (Keycloak) stays untouched. New code lives
in a new `src/study_tutor/http/` package; nothing existing changes.

## Scope

**In scope**
- Config loading: `STUDY_TUTOR_HTTP_TOKENS` env var — JSON object mapping
  token → student_id (e.g. `{"token-lilymay": "lilymay"}`); and
  `STUDY_TUTOR_HTTP_DEV_RESET` flag (consumed by TASK-APP1-05). Fail fast with
  a clear message on malformed/missing token config.
- Auth resolution used by every route: extract the Bearer token from the
  `Authorization` header ONLY (a token anywhere else — query string, body — is
  ignored); look up the table; unknown or missing token → `Unauthenticated`
  mapped per the binding doc. The resolved `student_id` is server-side truth —
  any client-asserted identity in a request body is ignored.
- The unseeded-student guard (ASSUM-001): when the resolved student has no
  `student` identity row, refuse as `Unauthenticated` and create nothing
  (without it, `create_session` raises `IntegrityError` → a 500;
  `session.student_id` FKs `student`, `schema_reference.sql:47`).
- `Unauthenticated` is raised at the transport auth layer, never by
  `SessionService` (see `session/errors.py` docstring — that split is already
  the design).

**Out of scope**
- The six endpoints (TASK-APP1-03); serve entrypoint (TASK-APP1-04); the seed
  itself (TASK-APP1-05).
- Any MCP adapter or `SessionService` change.

## Acceptance Criteria

- [ ] `STUDY_TUTOR_HTTP_TOKENS` JSON parsing with clear failure on malformed
      input; prod config works with a single entry, dev with two + any number
- [ ] Missing token, unknown token, and non-header token placement each resolve
      to `Unauthenticated` with the binding doc's envelope + status
- [ ] Unseeded-student requests resolve to `Unauthenticated` before any store
      write (verified with a fake store: no `create_session` call)
- [ ] Client-asserted `student_id` in a request never overrides the token's
- [ ] No import of Keycloak/JWT libraries — table lookup only
- [ ] All modified files pass project-configured lint/format checks with zero
      errors

## Test Requirements

Unit tests (injected fakes, no DB): token parse (valid/malformed/empty),
header-only extraction, reject-unknown, unseeded-student guard, envelope
shape/status per binding doc.

## Coach Validation

- `pytest tests/unit/http/ -q` green.
- Grep: no `keycloak`/`jwt` imports under `src/study_tutor/http/`.
- Verify the guard order: auth resolution happens before any service call.
