---
id: TASK-SMP3-04
title: "Config single-user identity + build_session_service() wiring (both main.py sites)"
task_type: feature
feature_id: FEAT-SMP-003
wave: 4
implementation_mode: task-work
complexity: 4
dependencies: [TASK-SMP3-03]
parent_feature_spec: features/durable-cross-device-sessions/durable-cross-device-sessions_summary.md
---

## Objective

Give the runtime a server-resolved single-user identity and wire the (already-built) `SessionService`
into the runtime via a `build_session_service()` helper at BOTH `MCPAdapter` construction sites — so
TASK-SMP3-06's adapter cutover can resolve the service. Mirrors `build_student_store()`
(`src/study_tutor/knowledge/store/wiring.py:28-68`).

## Scope

**In scope**
- **Identity config (ASSUM-001):** a single configured `student_id` resolved server-side, default `"lilymay"`,
  from an env var (e.g. `STUDY_TUTOR_STUDENT_ID`). Expose a small resolver (e.g.
  `session/identity.py: resolve_student_id() -> str`). This is the OWNERSHIP key — kept SEPARATE from the
  `tutor_start_session` planner-slug arg. No new MCP tool arg (ASSUM-002).
- **`build_session_service()`** (new, `session/wiring.py` mirroring store wiring): constructs
  `SessionService()` (which resolves the store via the provider) and calls
  `session.provider.set_session_service(...)`. Wire it CONDITIONALLY — only when `STUDY_TUTOR_PG_DSN` is set
  (so DSN-less dev/CI stays unwired and the adapter degrades / injects a fake in tests).
- **Wire both `cli/main.py` sites:** `serve` (~`main.py:380`) and `_build_nats_runtime` (~`main.py:525`).
  `_build_nats_runtime` currently has NO student-store wiring — add the conditional `build_student_store()`
  there too (so the session service has a store on the NATS path), then `build_session_service()`. In `serve`
  the conditional `build_student_store()` already exists (SMP-002); just add `build_session_service()` after it.

**Out of scope**
- Swapping the MCP tools onto SessionService → TASK-SMP3-06.
- The session-end completion producer → TASK-SMP3-05.

## Acceptance Criteria

- [ ] `resolve_student_id()` returns the configured id (env `STUDY_TUTOR_STUDENT_ID`), defaulting to `"lilymay"`;
      it is independent of the planner-slug tool arg.
- [ ] `build_session_service()` constructs a `SessionService` and registers it via `set_session_service`, and is
      called at BOTH `serve` and `_build_nats_runtime` — only when `STUDY_TUTOR_PG_DSN` is set (no DSN → not wired,
      no raise; `get_session_service()` stays None).
- [ ] `_build_nats_runtime` also calls the conditional `build_student_store()` (it had none), so the wired
      SessionService resolves a real store on the NATS path.
- [ ] A structured log line records session-service wiring (wired / skipped-no-dsn) without logging the DSN.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
# Boot-wiring is unit-testable without a live DB (SessionService resolves the store lazily).
.venv/bin/python -m pytest tests/unit/cli/test_serve_session_service_wiring.py -v
.venv/bin/python -m pytest tests/unit/session/ -v
.venv/bin/ruff check src/study_tutor/cli/main.py src/study_tutor/session/
```

## Implementation Notes

- Mirror `store/wiring.py` + the SMP-002 conditional-wiring call site pattern (`os.environ.get("STUDY_TUTOR_PG_DSN")`).
- Keep `build_session_service()` side-effect-only (returns None), like `build_student_store()`.
- The unit test monkeypatches `build_session_service` and asserts it is called iff the DSN is set at each site.
- Do NOT resolve identity from the planner slug — the split is the whole point of ASSUM-001.

## Boundary-test discipline (read the retro)

This task adds wiring/config; it changes no adapter tool behaviour yet. Do NOT assert the adapter still uses the
in-memory store (SMP3-06 changes that) — test only the wiring/identity invariants.

## BDD Scenarios

Supports the cutover scenarios in SMP3-06 (a wired SessionService is the precondition for durable tools).
