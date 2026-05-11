---
complexity: 3
created: 2026-05-08 00:00:00+00:00
dependencies:
- TASK-NATS-PH1-010
estimated_minutes: 45
feature_id: FEAT-NATS
id: TASK-NATS-PH2-001
implementation_mode: task-work
parent_review: TASK-REV-NATS-001
priority: medium
status: completed
tags:
- nats
- feature
- readiness
- phase-2
task_type: feature
title: Readiness gating - reject commands arriving before adapter is ready
updated: 2026-05-08 00:00:00+00:00
wave: 7
---

# Task: Readiness gating - reject commands arriving before adapter is ready

## Description

Tighten the boot-time race window. Today, if a command arrives between `start()` invoking subscribe and `_ready.set()` firing, it could be dispatched against half-initialised state. Solution: gate `on_command` on `_ready.is_set()` and return a clear "not ready" `ResultPayload` if not.

This is a hardening task — Phase 1 ships without it (the boot window is small enough to be statistically irrelevant for the demo), but Phase 2 closes the door.

## Scope

Update `src/study_tutor/adapters/command_router.py`:

- At the top of `on_command`, check `if not self._adapter_ready.is_set()` (or equivalent reference passed in from the adapter at construction time).
- If not ready: build `ResultPayload(success=False, error="study-tutor adapter is not ready")` and call `_publish_result` with the standard reply_to + topic publish.
- Do NOT invoke the underlying tutor business logic.
- Increment a not-ready counter for observability.

## Acceptance criteria

- [ ] Unit test: `on_command` invoked with `_adapter_ready.is_set() == False` returns `ResultPayload(success=False, error=...)` with a clear "not ready" message; underlying handler is NOT invoked.
- [ ] Unit test: same `on_command` invocation when `_adapter_ready.is_set() == True` proceeds normally.
- [ ] The Bug #1 reply path is honoured even in the not-ready case (caller still gets a clean reply on the inbox, not a hung future).
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation notes

- The adapter's `_ready` event already exists (set at end of `start()`). Either pass a reference to `CommandRouter` at construction time or add a setter the adapter calls.
- Do not block on `await _ready.wait()` — that turns a "fail fast with clear error" into a "queue commands until ready" semantic, which is the opposite of what we want.

## Coach validation

```bash
pytest tests/unit/adapters/test_command_router_readiness.py -v
ruff check src/study_tutor/adapters/command_router.py tests/unit/adapters/test_command_router_readiness.py
```