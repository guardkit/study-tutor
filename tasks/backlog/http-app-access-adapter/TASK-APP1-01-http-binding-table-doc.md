---
id: TASK-APP1-01
title: "HTTP binding table doc — API-session-http-binding.md (THE Mac unblock)"
task_type: documentation
feature_id: FEAT-APP-001
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
parent_feature_spec: features/http-app-access-adapter/http-app-access-adapter_summary.md
---

## Objective

Author and publish `docs/design/contracts/API-session-http-binding.md` — the HTTP
binding table for the six contract §5 verbs. This document is **frozen once
pushed**: the Mac-side Flutter build consumes it at a pinned SHA
(`BINDING_SHA`), so every route, method, and status code decided here is a
commitment. It is deliberately the FIRST task so the parallel app build
unblocks before the server exists.

The transport-neutral contract is
`docs/design/contracts/API-session-cross-device.md` at
`CONTRACT_SHA=22791afbcdb3b71abbe6bd2f1b8e18218988942f` — **read-only**; this
task binds it to the wire, it must not change it.

## Scope

**In scope**
- The binding table: verb → HTTP method + path for all six verbs
  (`start_session`, `list_sessions`, `resume_session`, `turn`,
  `session_status`, `end_session`), with request/response JSON shapes by
  reference to contract §5 (do not restate shapes — bind them).
- Status-code-per-`error_type`: the four closed-set errors from
  `src/study_tutor/session/errors.py` mapped 1:1 onto the §9 flat envelope
  (`SessionNotFoundError`, `SessionEnded`, `SessionForbidden`,
  `Unauthenticated`), plus the transport-level postures: malformed-request
  validation errors (outside the closed set — document the response shape) and
  unexpected server errors.
- Auth binding: `Authorization: Bearer <token>`; token honoured from the
  credential header ONLY; server-resolved `student_id` (client-asserted
  identity ignored).
- ASSUM-001 recorded: an authenticated-but-unseeded student is refused as
  `Unauthenticated` (never a 500).
- **Dev endpoints section** (required entries):
  - Dev token table: `token-lilymay` → `lilymay`, `token-alex` → `alex`.
    These values MUST equal the app's fake-IdP constants
    (`app/lib/fakes/fake_identity_provider.dart:16,19` — read-only reference;
    NEVER edit `app/**`).
  - Reset route: `POST /__dev__/reset` (env-flag-gated, absent from prod),
    truncates `session` + `session_turn` rows only.
  - The caveat that reset is **global server state**, so the live suite must
    run `--concurrency=1`.
  - Health route: `GET /healthz`; port **8100**.
- A freeze banner: changes after push require coordination with the app side
  (same discipline as the pinned contract).

**Out of scope**
- Any edit to `API-session-cross-device.md`, `API-tutoring.md`, or `app/**`.
- Implementation (later waves conform to this doc, not vice versa).

## Acceptance Criteria

- [ ] `docs/design/contracts/API-session-http-binding.md` exists with a table
      covering all six verbs (method + path + contract §5 shape reference each)
- [ ] Every `error_type` in `session/errors.py`'s closed set has exactly one
      documented status code; transport-level validation and server-error
      postures are documented separately from the closed set
- [ ] Dev endpoints section records both dev tokens with the exact values from
      the app's fake IdP, the reset route, the `--concurrency=1` caveat, the
      health route, and port 8100
- [ ] ASSUM-001 (unseeded student → `Unauthenticated`) is recorded in the doc
- [ ] The doc carries the freeze banner and pins
      `CONTRACT_SHA=22791afbcdb3b71abbe6bd2f1b8e18218988942f`
- [ ] `git diff` for this task touches ONLY the new binding doc and task files
      (no contract edits, no `app/**`, no `src/**`)

## Test Requirements

Documentation task — no code tests. The binding-conformance test that holds the
implementation to this doc lands in TASK-APP1-07.

## Coach Validation

- Verify the six-verb table is complete and each closed-set error has one
  status code.
- Verify the dev token values against `app/lib/fakes/fake_identity_provider.dart`
  (read-only check).
- Verify no file outside `docs/design/contracts/API-session-http-binding.md`
  and `tasks/**` changed.
