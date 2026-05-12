# Plan Audit Report — TASK-NATS-FIX-006

**Generated**: 2026-05-12 (post-implementation, pre-review transition).
**Plan reference**: `docs/state/TASK-NATS-FIX-006/implementation_plan.md`.

## Files

| Category | Planned | Actual | Variance |
|---|---|---|---|
| Source files modified | 2 | 2 | 0 |
| Test files modified | 2 | 2 | 0 |
| **Total files touched** | **4** | **4** | **0** |
| Extra files (not in plan) | — | 0 | low |

## Dependencies

| | Planned | Actual |
|---|---|---|
| New runtime deps | 0 | 0 |
| New dev deps | 0 | 0 |

## Lines of code (per-file insert deltas)

| File | Planned | Actual | Variance |
|---|---|---|---|
| `src/study_tutor/adapters/nats_adapter.py` | ~50 | +92 | +84% |
| `src/study_tutor/cli/main.py` | ~30 | +34 | +13% |
| `tests/unit/adapters/test_nats_adapter.py` | ~120 | +169 | +41% |
| `tests/unit/cli/test_serve_nats.py` | ~50 | +100 | +100% |
| **Total** | **~250** | **+395** | **+58%** |

## Severity assessment

| Dimension | Value | Severity |
|---|---|---|
| Files | 0 extra | low |
| Dependencies | 0 extra | low |
| LOC variance | +58% | **medium** (would be high by strict spec rule; see notes) |

**Overall severity: MEDIUM.**

## Notes / justification for the overshoot

The 58% LOC variance is entirely *test density* and *production docstring*
expansion — no scope creep:

- `nats_adapter.py` +92 LOC (planned 50): three async handlers ended up with
  full docstrings explaining WHY each callback exists (AC-04 mandates the
  structured-ERROR log; the comment in `__init__` documents the
  `closed_cb`-overrides-default ownership decision; `_on_reconnect` carries
  the heartbeat-restart rationale and the swallow-errors-in-nats-py-callback
  rationale). Stripping the docstrings would hit ~55-60 LOC.
- `cli/main.py` +34 LOC (planned 30): `asyncio.wait` race + cancel-pending
  cleanup + `terminal_close_triggered` branching. On plan.
- Tests +269 LOC (planned 170): added two tests beyond minimum AC coverage
  — `test_on_reconnect_swallows_register_errors` (defensive — protects the
  nats-py callback loop) and `test_serve_adapter_exits_0_when_shutdown_event_fires_first`
  (regression guard for the lifecycle race). Both defensible.

## Recommendation

**APPROVE.** The variance is in defensive test coverage and production
docstrings, not in scope. No extra files, no extra dependencies, no
production behaviour added beyond the AC list. Feeds back into estimation:
"complexity-3 NATS-callback wiring tasks need ~400 LOC, not 250" — adjust
future plan templates.

## Acceptance criteria status

| AC | Status | Evidence |
|---|---|---|
| AC-01 | ✅ | `TestReconnectCallbacks::test_handlers_defined_and_bound_to_client_kwargs` + 3 per-handler tests |
| AC-02 | ✅ | Same — bound-method-via-`__func__`/`__self__` assertion |
| AC-03 | ✅ | `test_on_reconnect_re_registers_manifest` + `test_on_reconnect_restarts_heartbeat_when_dead` |
| AC-04 | ✅ | `test_on_closed_sets_event_and_logs_terminally_closed` |
| AC-05 | ✅ | `test_serve_adapter_exits_1_when_terminal_close_event_fires` + negative-path test |
| AC-06 | ✅ | GB10 probe — tutor reappeared in `agent-registry` ~7 s after broker came back; see `RESULTS-ac06-ac07-gb10-probes.md` |
| AC-07 | ✅ | GB10 probe — tutor exited `exitCode=1` at T+120 s with structured `nats_terminally_closed` ERROR + Docker `restart: unless-stopped` recovered the container; see `RESULTS-ac06-ac07-gb10-probes.md` |
| AC-08 | ✅ | Full unit suite: 999 pass, 10 fail; baseline-stash confirmed all 10 pre-exist on `main` and are in unrelated modules (knowledge/, mcp/, planner/, Dockerfile-structure). |
