---
id: TASK-NATS-PH1-011
title: "Bug #8: CommandRouter._client constructed but never connected — no result envelopes emitted"
status: completed
task_type: bugfix
implementation_mode: task-work
parent_review: TASK-REV-NATS-001
feature_id: FEAT-39E1
feature_slug: feat-39e1-recovery
wave: 5
priority: critical
created: 2026-05-10T22:00:00Z
updated: 2026-05-10T23:10:00Z
completed: 2026-05-10T23:10:00Z
completed_location: tasks/completed/TASK-NATS-PH1-011/
previous_state: in_review
state_transition_reason: "Option (A) fix landed, unit tests green, ready for operator runbook re-run"
followup_task: TASK-NATS-PH1-012
complexity: 4
estimated_minutes: 90
tags:
  - nats
  - command-router
  - nats-adapter
  - phase-1
  - bug-8
  - demo-blocker
  - dddsw-2026
  - feat-39e1
dependencies:
  - TASK-NATS-PH1-005
related_tasks:
  - TASK-NATS-PH2-001
  - TASK-NATS-PH3-005
  - TASK-NATS-PH3-006
blocks:
  - TASK-NATS-PH3-005
source: docs/runbooks/RESULTS-study-tutor-nats-fleet-demo-2026-05-10-run-1.md
evidence:
  traceback: docs/runbooks/evidence/dddsw-tutor-demo-2026-05-10-run-1/container.log
  inbound_captured: docs/runbooks/evidence/dddsw-tutor-demo-2026-05-10-run-1/wire-command.log
  result_absent: docs/runbooks/evidence/dddsw-tutor-demo-2026-05-10-run-1/wire-result.log
patch_status: applied
test_results:
  status: passed
  coverage: null  # unit-only run; integration round-trip deferred to operator runbook
  last_run: 2026-05-10T23:00:00Z
  details:
    unit_tests: "61/61 passed in tests/unit/adapters/ (3 new Bug-#8 regression guards)"
    bug_1_regression_guard: "passed (subscribe_with_reply used, plain subscribe not used)"
    ruff: "All checks passed!"
    single_connection_invariant: "grep '\\.connect()' src/study_tutor/cli/main.py returns 0 lines"
    integration_round_trip: "deferred - operator to run runbook §3/§4 wire-tap pre-demo"
---

# Task: Bug #8 — CommandRouter._client constructed but never connected

## Description

`CommandRouter._client` is a second `NATSClient` instance constructed
in `_build_nats_runtime` ([`src/study_tutor/cli/main.py:518`](../../src/study_tutor/cli/main.py#L518))
and passed into the router at construction time:

```python
nats_client = NATSClient(config.nats, source_id=agent_id)   # line 518
router = CommandRouter(
    mcp_adapter=mcp_adapter,
    tool_to_command=role_entry.tool_to_command,
    agent_id=agent_id,
    client=nats_client,                                       # line 523
)
adapter = NATSAdapter(config, manifest, command_router=router)  # line 525
```

`NATSAdapter` constructs and connects its *own* internal client in
`start()`. The router's `nats_client` is **never** `connect()`ed.

The first time any command is received and processed, the router hits
the Bug-#1 dual-publish path at
[`src/study_tutor/adapters/command_router.py:234`](../../src/study_tutor/adapters/command_router.py#L234):

```python
await self.client.publish_raw(reply_to, ...)
```

This raises:

```
RuntimeError: client is not connected
```

Net effect: the container boots successfully, registers in `agent-registry`,
heartbeats correctly, and the inbound `agents.command.gcse-tutor` envelope
is received and parsed — but **no result envelope is ever emitted** on
`agents.result.gcse-tutor`. The wire-level failure mode is identical to
Reference Bug #1 (which the dual-publish path was meant to fix), but via
a different root cause: a disconnected second client rather than a missing
reply-to propagation.

This is almost certainly an incomplete piece of the recent FEAT-39E1
salvage work (commits `7c21475` — "salvage PH1-005 NATSAdapter
implementation from autobuild run-5 worktree" and `b83151b` — "add
PH2-001 readiness gating to CommandRouter"). The dual-client wiring
slipped through that salvage without a connected-client assertion.

### Evidence (2026-05-10 run-1)

- **Traceback** —
  [`docs/runbooks/evidence/dddsw-tutor-demo-2026-05-10-run-1/container.log`](../../docs/runbooks/evidence/dddsw-tutor-demo-2026-05-10-run-1/container.log):
  full `RuntimeError: client is not connected` traceback at the bottom,
  rooted at `command_router.py:234 → publish_raw`.
- **Inbound captured** —
  [`docs/runbooks/evidence/dddsw-tutor-demo-2026-05-10-run-1/wire-command.log`](../../docs/runbooks/evidence/dddsw-tutor-demo-2026-05-10-run-1/wire-command.log):
  one envelope on `agents.command.gcse-tutor`
  (correlation_id `demo-runbook-1778441600-start`) — proof the agent
  received the command.
- **Result absent** —
  [`docs/runbooks/evidence/dddsw-tutor-demo-2026-05-10-run-1/wire-result.log`](../../docs/runbooks/evidence/dddsw-tutor-demo-2026-05-10-run-1/wire-result.log):
  empty (0 bytes) — proof no result envelope was emitted.

The phase/gate table in the RESULTS file shows Phase 3 / Gate "Dispatch
fires + result rendered" as RED and Phase 4.2 / Gate "Wire tap on
`agents.result.>`" as RED with zero envelopes captured. This is the
only code-level bug in the batch; Bugs #5–#7 were all configuration.

## Fix options

Three shapes, two of which the operator has already chosen:

### (A) — Minimal demo-unblock [CHOSEN for 2026-05-16 demo]

In `NATSAdapter.start()`, immediately after `await self._client.connect()`,
inject the adapter's already-connected client into the router:

```python
self._command_router.client = self._client
```

One line. Reuses the adapter's single connection. Smallest blast radius.
Preserves the existing construction signature of `CommandRouter` and
`_build_nats_runtime`. Add a unit test asserting that
`router.client.is_connected` is `True` after `adapter.start()` returns.

**This is the fix to land before 2026-05-16.**

### (B) — Connect the second client at construction time [NOT recommended]

Make `_build_nats_runtime` async (or wrap an `asyncio.run`) and
`await nats_client.connect()` before passing the client to
`CommandRouter`. This results in two live NATS connections per process
and duplicates lifecycle management across `NATSAdapter` and
`_build_nats_runtime`. Do not choose this option.

### (C) — Proper architectural fix [CHOSEN as FEAT-39E1 follow-up after demo]

Refactor so `CommandRouter` does not own a client at all. `NATSAdapter`
constructs the router internally and supplies whatever publish helper it
needs (a bound coroutine, a thin gateway object, or the adapter's own
client). This eliminates the dual-client construction pattern entirely
and is the correct end-state for the FEAT-39E1 architecture. Biggest
blast radius; best done after the demo with full test coverage.

**Option (C) should be tracked as a follow-up under FEAT-39E1 once the
demo is behind us. This task covers landing Option (A) before 2026-05-16
and recording Option (C) as the intended destination.**

## Scope

1. **Apply Option (A)** in `NATSAdapter.start()`:
   after `await self._client.connect()`, add
   `self._command_router.client = self._client`.
2. **Add unit test** in `tests/unit/adapters/test_nats_adapter.py`
   (or a new sibling) asserting that `router.client.is_connected` is
   `True` immediately after `adapter.start()` returns. Use a mocked
   `NATSClient` that sets `is_connected = True` on `connect()`.
3. **Confirm Bug-#1 dual-publish path still works** end-to-end: publish
   a `MessageEnvelope` to `agents.command.gcse-tutor` (via
   `nats request` or the integration test fixture); assert both:
   - a `ResultPayload` envelope appears on `agents.result.gcse-tutor`
     with `success: true`, AND
   - the inbound `reply` inbox receives the result (the Bug-#1 fix must
     still hold after this change).
4. **Do not break** the existing PH1-005 / PH1-007 unit tests. Run them
   as part of the coach-validation step.
5. **Create a follow-up task** (or update FEAT-39E1.yaml) to track
   Option (C) as the proper architectural fix.

## Acceptance criteria

- [ ] After `NATSAdapter.start()` returns, `CommandRouter._client.is_connected`
      (or equivalent `NATSClient.is_connected` property) is `True` — verified
      by a unit test using a mock `NATSClient`.
- [ ] End-to-end round-trip integration test passes: publish a
      `MessageEnvelope{event_type=command, payload=CommandPayload{command="tutor_start_session", args={student_id: "test-001"}}}`
      to `agents.command.gcse-tutor`; assert a `ResultPayload` envelope
      appears on `agents.result.gcse-tutor` with `success: true` **and** on
      the inbound `reply` inbox (both legs of the Bug-#1 dual-publish must
      work after the fix).
- [ ] The Bug-#1 regression guard in the existing test suite (assert that
      `subscribe_with_reply` is used, not `subscribe`) still passes
      without modification.
- [ ] Re-running the runbook's §3 / §4 wire-tap experiment
      (`nats request agents.command.gcse-tutor <envelope>`) produces a
      non-empty result envelope on `agents.result.gcse-tutor` — the
      `wire-result.log` from the next run must be non-empty (contrast with
      the 0-byte file in evidence above).
- [ ] All modified files pass project-configured lint/format checks
      (`ruff check`) with zero errors.
- [ ] No new NATS connections are introduced — the process must hold
      exactly one live NATS connection (the adapter's) after `start()`.

## Implementation notes

- `NATSAdapter.start()` is in
  `src/study_tutor/adapters/nats_adapter.py`. The one-line fix goes
  immediately after `await self._client.connect()`, before the
  `register_agent` call — order matters so that if `register_agent`
  raises the router's client assignment is still atomic with the connect.
- The `CommandRouter.client` property setter may need to be exposed if
  it is currently read-only. Check the `CommandRouter` implementation
  before writing the adapter fix; if the attribute is a plain instance
  variable (not a `@property`), direct assignment works without changes.
  If it is `@property` with no setter, add a minimal setter.
- The unit test should mock `NATSClient` via `unittest.mock.AsyncMock`
  or `pytest-asyncio` fixtures, consistent with the existing
  `tests/unit/adapters/test_nats_adapter.py` style.
- Demo deadline: **2026-05-16 (DDDSW)**. This is THE demo blocker —
  Bugs #5–#7 are configuration patches already in tree; Bug #8 is the
  code change required before the runbook can go green end-to-end.
- For Option (C) tracking: after landing Option (A), either open a new
  `TASK-NATS-PH1-012` or add a `refactor_followup` field to FEAT-39E1.yaml
  describing the CommandRouter/NATSAdapter decoupling. Do not attempt
  Option (C) in the same PR as Option (A).

## Coach validation

```bash
# Unit tests (must all pass)
pytest tests/unit/adapters/test_nats_adapter.py -v

# Bug-#1 regression guard
pytest tests/unit/adapters/ -k "subscribe_with_reply" -v

# Integration round-trip (requires local NATS server)
pytest tests/integration/test_adapter_lifecycle.py -v

# Lint
ruff check src/study_tutor/adapters/nats_adapter.py \
           src/study_tutor/adapters/command_router.py \
           tests/unit/adapters/

# Confirm single connection (no second NATSClient.connect call)
grep -n "\.connect()" src/study_tutor/cli/main.py
# Expected: zero lines (connect must only happen inside NATSAdapter.start)
```
