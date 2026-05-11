---
id: TASK-NATS-PH1-012
title: "Architectural follow-up: CommandRouter should not own a NATSClient (Option C from PH1-011)"
status: backlog
task_type: refactor
implementation_mode: task-work
parent_task: TASK-NATS-PH1-011
feature_id: FEAT-39E1
feature_slug: feat-39e1-recovery
wave: 6
priority: medium
created: 2026-05-10T22:45:00Z
updated: 2026-05-10T22:45:00Z
complexity: 6
estimated_minutes: 180
tags:
  - nats
  - command-router
  - nats-adapter
  - phase-1
  - refactor
  - post-demo
  - feat-39e1
dependencies:
  - TASK-NATS-PH1-011
related_tasks:
  - TASK-NATS-PH2-001
source: docs/runbooks/RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-1.md
---

# Task: Refactor — CommandRouter should not own a NATSClient (Option C)

## Background

TASK-NATS-PH1-011 landed Option (A) before the 2026-05-16 DDDSW demo:
`NATSAdapter.start()` injects its own connected client into the router
immediately after `await self._client.connect()`. That fix is one line
and pins the bug closed, but the underlying construction pattern —
`_build_nats_runtime` constructing a *second* `NATSClient` solely to
hand to `CommandRouter` at construction time — is still wrong and will
re-trip the same class of bug under future refactors.

The demo is now unblocked, so this task tracks the proper architectural
fix.

## Goal

`CommandRouter` should not own a `NATSClient` at all. The publish path
should be an injected publish helper (bound coroutine, gateway, or the
adapter's own client passed by reference at adapter-construction time),
and the dual-client construction pattern in `cli/main.py:_build_nats_runtime`
should be deleted.

## Two acceptable end-states

### (1) Adapter owns construction of the router

`NATSAdapter` accepts the router's *ingredients* (`mcp_adapter`,
`tool_to_command`, `agent_id`, `adapter_ready`) and constructs the
router internally after `connect()`. `_build_nats_runtime` stops
constructing a `NATSClient` or a `CommandRouter` — it only builds the
adapter.

Pros: smallest API surface; one place owns lifecycle.
Cons: leaks router-construction details into the adapter constructor.

### (2) Router receives a publish gateway, not a client

Extract `CommandRouter.client.publish` / `publish_raw` calls behind a
narrow protocol (e.g. `ResultPublisher`) with two methods:

```python
class ResultPublisher(Protocol):
    async def publish_raw(self, subject: str, data: bytes) -> None: ...
    async def publish_envelope(
        self,
        topic: str,
        payload: BaseModel,
        event_type: EventType,
        source_id: str,
        correlation_id: str | None,
    ) -> None: ...
```

`NATSAdapter` supplies an implementation backed by its own `_client`
after `connect()`. `_build_nats_runtime` builds the router with this
gateway (never a raw `NATSClient`).

Pros: clearer dependency contract; easier to fake in router tests.
Cons: one extra abstraction; mild churn in the existing router tests.

## Acceptance criteria

- [ ] `_build_nats_runtime` in `src/study_tutor/cli/main.py` no longer
      constructs a `NATSClient`. Exactly one `NATSClient` instance
      exists per process — the one constructed inside `NATSAdapter`.
- [ ] `CommandRouter` either no longer takes a `client` argument, or
      takes a narrow publish-gateway protocol (not a `NATSClient`).
- [ ] The Option (A) hand-off in `NATSAdapter.start()` (the
      `self._command_router.client = self._client` line introduced in
      PH1-011) is deleted — the router no longer needs the assignment
      because it never owned a client in the first place.
- [ ] All existing unit tests in `tests/unit/adapters/` pass without
      logic changes (signature updates only where needed).
- [ ] The Bug-#1 regression guard (`subscribe_with_reply`, not
      `subscribe`) still passes unchanged.
- [ ] The Bug-#8 regression guard from PH1-011
      (`TestRouterClientShareAfterConnect`) is updated to assert the
      new contract (router has no client OR router's publisher is the
      adapter's gateway), not deleted — the underlying invariant
      "router can publish after adapter.start() returns" must survive.
- [ ] Integration test `tests/integration/test_adapter_lifecycle.py`
      passes end-to-end against a real local NATS server.
- [ ] `ruff check` clean on all modified files.

## Out of scope

- Any changes to the wire-level Bug-#1 dual-publish behaviour (both
  the reply-inbox and `agents.result.<agent_id>` legs must still fire).
- Any changes to the PH2-001 readiness gate semantics.
- Any changes to MCP adapter, role registry, or manifest construction.

## Notes

- Do not attempt this until the 2026-05-16 demo has shipped from Option (A).
- Recommend pairing the refactor with a quick design-only run
  (`/task-work TASK-NATS-PH1-012 --design-only`) to pick between
  end-state (1) and (2) before implementation.
- Track in FEAT-39E1.yaml as `refactor_followup` if that field exists,
  else leave this task as the canonical record.
