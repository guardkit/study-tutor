---
id: TASK-APP1-03
title: "Six JSON endpoints over SessionService + §9 error envelope mapping"
task_type: feature
feature_id: FEAT-APP-001
wave: 3
implementation_mode: task-work
complexity: 6
dependencies: [TASK-APP1-02]
parent_feature_spec: features/http-app-access-adapter/http-app-access-adapter_summary.md
consumer_context:
  - task: TASK-APP1-01
    consumes: API-session-http-binding.md
    framework: "starlette (Route table + JSONResponse)"
    driver: "starlette"
    format_note: "Every route path, method, and status-per-error_type is fixed by the binding doc — implementation conforms to the doc, never the reverse"
---

## Objective

The core of the feature: the six contract §5 verbs as plain JSON starlette
routes, each a thin projection over the existing `SessionService`
(`src/study_tutor/session/service.py` — wired and proven over MCP since
`ea7c135`). No WS, no streaming: `turn_stream` stays `NotImplementedError` and
gets NO route.

## Scope

**In scope**
- A starlette app factory in `src/study_tutor/http/` with routes exactly per
  the binding doc: `start_session` (incl. `resume_if_active` passthrough),
  `list_sessions` (status filter + limit, default 20), `resume_session`,
  `turn`, `session_status`, `end_session`. `student_id` always comes from the
  TASK-APP1-02 auth resolution.
- Error boundary: catch the `session/errors.py` closed set and map 1:1 onto the
  §9 flat envelope with the binding doc's status codes. Malformed/unparseable
  bodies → the transport-level validation response (no state change).
  Unexpected exceptions → the server-error posture (clear envelope, session
  state intact, service keeps serving).
- `turn` runs the injected `reply_fn` (wiring itself is TASK-APP1-04; here the
  factory takes it as a parameter, mirroring `SessionService.turn`).
- Event emission hooks (`session.started` / `turn_completed` / `completed`)
  with the same pinned payloads the MCP path emits (factory parameter; wiring
  in TASK-APP1-04).
- **pyproject**: add `starlette` and `uvicorn` as DIRECT dependencies (they are
  transitive via `mcp` today; the served stack must be pinned) + `uv lock`.

**Out of scope**
- CLI entrypoint / uvicorn serving (TASK-APP1-04); reset endpoint
  (TASK-APP1-05); any MCP surface change (contract §10 — the four tools stay
  byte-for-byte); any `SessionService` behaviour change — in particular the
  `resume_if_active` pick order (`ORDER BY last_activity DESC LIMIT 1`,
  `store/postgres.py:706`) is pinned by the app's contract test.

## Acceptance Criteria

- [ ] All six routes match the binding doc exactly (method, path, status codes)
      and no streaming route exists
- [ ] Closed-set errors map 1:1 (`SessionNotFoundError`, `SessionEnded`,
      `SessionForbidden`, `Unauthenticated`) — asserted per error type
- [ ] Ownership refusal wins over ended-state for another student's ended
      session (guard order regression — the service already orders it; a test
      pins it at the HTTP boundary)
- [ ] Malformed body → validation response, session state untouched
- [ ] `resumed`/`turns` semantics of `start_session(resume_if_active)` and the
      ordered transcript of `resume_session` surface unchanged from the service
      DTOs
- [ ] `starlette` + `uvicorn` are direct deps in `pyproject.toml`; `uv.lock`
      regenerated; MCP tool surface untouched (existing adapter tests green)
- [ ] All modified files pass project-configured lint/format checks with zero
      errors

## Test Requirements

Unit tests with starlette's TestClient over an injected fake
store/SessionService (no DB): per-verb happy path, per-error_type mapping,
guard-order pin, malformed-body, no-token/unknown-token passthrough from the
auth layer.

## Seam Tests

The following seam test validates the integration contract with the producer task. Implement this test to verify the boundary before integration.

```python
"""Seam test: verify API-session-http-binding.md contract from TASK-APP1-01."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("API-session-http-binding.md")
def test_api_session_http_binding_md_format():
    """Verify served routes match the binding doc.

    Contract: every route path, method, and status-per-error_type is fixed by
    docs/design/contracts/API-session-http-binding.md.
    Producer: TASK-APP1-01
    """
    from pathlib import Path

    doc = Path("docs/design/contracts/API-session-http-binding.md").read_text()
    assert doc, "binding doc must exist and be non-empty"
    # Consumer side: each of the six verbs' paths parsed from the doc appears
    # in the starlette app's route table (full conformance test in TASK-APP1-07):
    # e.g. assert route_path("start_session", doc) in {r.path for r in app.routes}
```

## Coach Validation

- `pytest tests/unit/http/ tests/unit/mcp/ -q` green (HTTP new + MCP frozen).
- Verify no route beyond the binding doc's set (+ healthz later); no
  `turn_stream` route.
- Verify pyproject diff adds only the two pins.
