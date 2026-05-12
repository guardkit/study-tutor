# Implementation Plan — TASK-NATS-FIX-006

**Task**: Add `_on_reconnect` handler + wire reconnect/closed callbacks (study-tutor consumer of TASK-NC10).
**Complexity**: 3/10 (feature subtask, MINIMAL intensity auto-detected).
**Mode**: standard.
**Generated**: 2026-05-12.

## Scope

Wire the callback API surface that nats-core TASK-NC10 added so the
study-tutor `NATSAdapter`:

- re-publishes its manifest to `agent-registry` KV when nats-py reconnects
  after a transient broker bounce (AC-01, AC-03, AC-06),
- emits a structured `nats_terminally_closed` ERROR log + sets a
  terminal-close event when the reconnect budget is exhausted (AC-04),
- drives a non-zero CLI exit on terminal-close so Docker restart policy
  recovers the container (AC-05, AC-07),
- logs a structured `nats_disconnected` WARNING on each transient
  disconnect (AC-01).

## Files to modify (2)

| File | Change |
|---|---|
| `src/study_tutor/adapters/nats_adapter.py` | Add `_terminal_close_event` + `terminal_close_event` property; add `_on_reconnect`, `_on_closed`, `_on_disconnect` async handlers; pass them as kwargs to `NATSClient(...)` in `__init__`. |
| `src/study_tutor/cli/main.py` | Modify `_serve_adapter` to race `shutdown_event.wait()` vs `adapter.terminal_close_event.wait()`; on terminal-close exit, raise `SystemExit(1)` after `adapter.stop()` + `runtime_shutdown(write_helper)`. |

## Tests to add (2)

| File | New tests |
|---|---|
| `tests/unit/adapters/test_nats_adapter.py` | `TestReconnectCallbacks` class: AC-01 (handlers exist + bound to client construction kwargs), AC-02 (NATSClient kwargs assertion), AC-03 (`_on_reconnect` re-calls `register_agent`), AC-03b (`_on_reconnect` restarts heartbeat if dead), AC-04 (`_on_closed` sets event + emits structured ERROR log), AC-01 disconnect-log assertion. |
| `tests/unit/cli/test_serve_nats.py` | `test_serve_adapter_exits_1_on_terminal_close` (AC-05 positive path), `test_serve_adapter_exits_0_on_shutdown_event_terminal_close_not_set` (AC-05 negative path — shutdown_event must still drive a clean exit). Also patch the existing two lifecycle tests to attach `adapter.terminal_close_event = asyncio.Event()` on their MagicMock adapters (AC-08 regression-safety). |

## Estimated effort

- Adapter source: ~50 lines added (5 attributes + 3 handlers + property + 3 client-construction kwargs).
- CLI source: ~30 lines net changed in `_serve_adapter` (one `asyncio.wait` race + branch on terminal_close → `SystemExit(1)`).
- Unit tests: ~170 lines added (~120 in adapter test, ~50 in serve-nats test).
- **Total estimate**: ~250 LOC.
- **Duration estimate**: ~45 min hands-on.

## External dependencies

None new. Relies on `nats-core>=0.4` (already pinned in `pyproject.toml`),
specifically the `reconnected_cb` / `disconnected_cb` / `closed_cb`
constructor kwargs added by TASK-NC10.

## Risks

- **Low — MagicMock adapter regressions**: existing serve-nats lifecycle
  tests construct `adapter = MagicMock()` and `_serve_adapter` now
  awaits `adapter.terminal_close_event.wait()`. Mitigation: assign
  `adapter.terminal_close_event = asyncio.Event()` in those tests.
- **Low — heartbeat-restart double-spawn**: `_on_reconnect` restarts the
  heartbeat task if `_heartbeat_task is None or .done()`. There is a
  theoretical race where `start()` has set the task and `_on_reconnect`
  fires before nats-py actually completes reconnect; the `.done()`
  check prevents the double-spawn. Unit test covers both paths.
- **Low — `closed_cb` overrides client default**: passing
  `closed_cb=self._on_closed` means `client.terminally_closed` (the
  client's own event) is no longer set automatically. Our consumers
  (the CLI) await `adapter.terminal_close_event`, not the client's
  event, so this is the intended ownership.

## Phases skipped (MINIMAL intensity rationale)

- Phase 1.5/1.6 clarification: task body is unambiguous, AC list specific.
- Phase 1.7 Graphiti: MCP tools not in session; CLI fallback non-blocking; skipped.
- Phase 2.1 Context7 library docs: `nats-py` API surface is captured in the
  local sibling `nats-core/src/nats_core/client.py` — authoritative.
- Phase 2.5A Pattern MCP: complexity ≤3, no architectural pattern need detected.
- Phase 2.7 Complexity Evaluation: complexity pre-declared in frontmatter (3).
- Phase 2.8 Checkpoint: AUTO_PROCEED for complexity 1-3.

## Acceptance criteria mapping

| AC | Covered by |
|---|---|
| AC-01 | New handlers in `nats_adapter.py` + `TestReconnectCallbacks::test_handlers_exist`. |
| AC-02 | `NATSClient` kwargs assertion in `TestReconnectCallbacks::test_client_constructed_with_callbacks`. |
| AC-03 | `TestReconnectCallbacks::test_on_reconnect_re_registers_manifest`. |
| AC-04 | `TestReconnectCallbacks::test_on_closed_sets_event_and_logs_error`. |
| AC-05 | `test_serve_adapter_exits_1_on_terminal_close`. |
| AC-06 | **Manual GB10 probe** — out of unit-test scope; documented in task body, captured as addendum RESULTS note post-implementation. Not gated by Phase 4. |
| AC-07 | **Manual GB10 probe** — same as AC-06. |
| AC-08 | Patch existing serve-nats lifecycle tests + run full suite. |
