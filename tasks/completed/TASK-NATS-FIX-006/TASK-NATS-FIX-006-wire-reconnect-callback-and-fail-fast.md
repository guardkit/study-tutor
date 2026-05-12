---
id: TASK-NATS-FIX-006
title: "Add _on_reconnect handler + wire reconnect/closed callbacks (study-tutor consumer of TASK-NC10)"
status: completed
previous_state: in_review
state_transition_reason: "User-approved completion via /task-complete; AC-01..AC-05 + AC-08 unit-test gates green; AC-06/AC-07 are manual GB10 probes deferred per task body"
completed: 2026-05-12T00:00:00Z
completed_location: tasks/completed/TASK-NATS-FIX-006/
organized_files:
  - TASK-NATS-FIX-006-wire-reconnect-callback-and-fail-fast.md
task_type: bug
feature_id: FEAT-NATS
implementation_mode: task-work
priority: high
complexity: 3
wave: null
created: 2026-05-12T00:00:00Z
updated: 2026-05-12T00:00:00Z
implementation:
  plan: docs/state/TASK-NATS-FIX-006/implementation_plan.md
  audit_report: docs/state/TASK-NATS-FIX-006/plan_audit_report.md
  gb10_probe_results: docs/state/TASK-NATS-FIX-006/RESULTS-ac06-ac07-gb10-probes.md
  files_modified:
    - src/study_tutor/adapters/nats_adapter.py
    - src/study_tutor/cli/main.py
  test_files_modified:
    - tests/unit/adapters/test_nats_adapter.py
    - tests/unit/cli/test_serve_nats.py
  test_results:
    touched_files_pass_rate: "45/45 (100%)"
    full_unit_suite: "999 passed, 10 pre-existing failures in unrelated modules confirmed via stash-baseline"
    coverage_nats_adapter: "94%"
  gb10_probe_results_summary:
    ac06_reregistration_after_15s_bounce: "PASS (tutor reappeared in agent-registry T+22s)"
    ac07_terminal_close_after_180s_outage: "PASS (exitCode=1 at T+120s, structured ERROR emitted, Docker restart loop recovered)"
  audit_severity: medium
  audit_severity_reason: "+58% LOC vs plan; 0 extra files, 0 extra deps, 0 scope creep"
dependencies:
  - TASK-NC10
tags:
  - nats
  - fleet-hygiene
  - reconnect
  - demo-blocker
  - fleet-consumer
parent_review: null
related_tasks:
  - TASK-NATS-PH1-005
cross_repo_origin:
  triggered_by: jarvis FEAT-JARVIS-006 GB10 verification rerun (2026-05-12)
  library_dependency: nats-core TASK-NC10 (must land first — adds the callback API)
  parallel_consumer: specialist-agent TASK-NATS-009 (same fix, peer repo)
  jarvis_results_evidence:
    - jarvis/docs/runbooks/RESULTS-FEAT-JARVIS-006-serve-nats-first-run-2026-05-12-rerun-post-J006-009-010.md (§"Specialist reconnect gap")
---

# Task: Add _on_reconnect handler + wire reconnect/closed callbacks (study-tutor consumer of TASK-NC10)

## Severity / impact

**High — demo-blocker for 2026-05-16 DDD Southwest.**

`study-tutor`'s `NATSAdapter` at `src/study_tutor/adapters/nats_adapter.py` has **no
reconnect handling at all** — strictly worse exposure than the parallel specialist-agent
gap (which at least defines a dead `_on_reconnect` we can wire). When the broker is bounced
while the tutor container is running, nats-py reconnects at the TCP layer but the agent
never re-publishes its manifest to `agent-registry` KV. The container stays `Up`; fleet
orchestration (jarvis dispatch) can't reach it.

Same demo risk as specialist-agent: any broker hiccup in the 24h before demo silently
drops the tutor from the fleet with no operator-visible signal.

## Evidence

The jarvis 2026-05-12 RESULTS file documents the symptom on specialist-agent (where it was
observed in the GB10 rerun). study-tutor was not directly exercised in that run but uses
the **same `nats_core.NATSClient` instantiation pattern at**
`src/study_tutor/cli/main.py:518` (`nats_client = NATSClient(config.nats, source_id=agent_id)`),
**and** lacks even the dead-handler safety net specialist-agent has. The failure mode is
identical.

Reproduction:
1. Start the tutor; verify it appears in `nats kv ls agent-registry`.
2. `docker stop ships-computer-nats && sleep 15 && docker start ships-computer-nats`.
3. Wait ~5 s; check `nats kv ls agent-registry`. The tutor is absent.

See: `jarvis/docs/runbooks/RESULTS-FEAT-JARVIS-006-serve-nats-first-run-2026-05-12-rerun-post-J006-009-010.md`
→ §"Other findings" → "Specialist reconnect gap".

## Root cause

Two distinct gaps in `src/study_tutor/adapters/nats_adapter.py`:

### Gap 1: No `_on_reconnect` handler exists at all

Unlike specialist-agent which has a dead-but-defined `_on_reconnect` at
`adapters/nats_adapter.py:254`, study-tutor's adapter has no handler to register the
manifest on reconnect. The first task here is to **design and add the handler** before
wiring it.

### Gap 2: No callback wiring (parallel to specialist-agent)

Same as the parallel specialist-agent gap: `nats_core.NATSClient` had no API to receive
reconnect callbacks (fixed by `nats-core TASK-NC10`), and study-tutor doesn't currently
construct the client with any callbacks.

`src/study_tutor/cli/main.py:518`:
```python
nats_client = NATSClient(config.nats, source_id=agent_id)
```

No callback kwargs, no terminal-close detection, no fail-fast on prolonged broker outage.

## Recommended fix

Depends on `nats-core TASK-NC10` landing. Order of operations:

### 1. Add `_on_reconnect`, `_on_closed`, `_on_disconnect` to study-tutor's NATSAdapter

Use specialist-agent's `_on_reconnect` (at
`specialist-agent/src/specialist_agent/adapters/nats_adapter.py:254-277`) as the
implementation reference. Adapt for study-tutor's manifest re-publish path (call
`self._client.register_agent(self._manifest)` and restart the heartbeat task if needed).

```python
async def _on_reconnect(self) -> None:
    """Re-publish manifest after NATS reconnects (TASK-NATS-FIX-006).

    Called by nats-py via reconnected_cb wired in cli/main.py. Mirrors the
    behaviour study-tutor needs after a transient broker bounce so the agent
    re-appears in agent-registry KV without operator intervention.
    """
    logger.info(
        "NATS reconnected — re-registering tutor agent '%s'",
        self._manifest.agent_id,
    )
    try:
        await self._client.register_agent(self._manifest)
    except Exception as exc:
        logger.error("Failed to re-register on reconnect: %s", exc)
    # If heartbeat task died during the disconnect, restart it.
    if self._heartbeat_task is None or self._heartbeat_task.done():
        self._heartbeat_task = asyncio.create_task(
            self._heartbeat_loop(),
            name=f"heartbeat-{self._manifest.agent_id}",
        )

async def _on_closed(self) -> None:
    """Signal terminal close (max_reconnect_attempts exhausted)."""
    logger.error(
        "nats_terminally_closed",
        extra={
            "agent_id": self._manifest.agent_id,
            "nats_url": self._config.nats.url,
        },
    )
    self._terminal_close_event.set()

async def _on_disconnect(self) -> None:
    logger.warning(
        "nats_disconnected", extra={"agent_id": self._manifest.agent_id}
    )
```

Add `self._terminal_close_event = asyncio.Event()` in `__init__` and expose as a property.

### 2. Wire callbacks at NATSClient construction in cli/main.py

`src/study_tutor/cli/main.py:518` becomes:

```python
nats_client = NATSClient(
    config.nats,
    source_id=agent_id,
    reconnected_cb=adapter._on_reconnect,
    closed_cb=adapter._on_closed,
    disconnected_cb=adapter._on_disconnect,
)
```

(Or — preferred — move the wiring into `NATSAdapter.__init__` to mirror specialist-agent's
shape, so `cli/main.py` only constructs `NATSAdapter(config, manifest, command_router=...)`.
Choose whichever keeps the `cli/main.py` diff small.)

### 3. Wire `terminal_close_event` into the CLI shutdown path

`_serve_adapter` at `src/study_tutor/cli/main.py:529` currently awaits only
`shutdown_event.wait()`. Change to:

```python
done, pending = await asyncio.wait(
    {
        asyncio.create_task(shutdown_event.wait()),
        asyncio.create_task(adapter.terminal_close_event.wait()),
    },
    return_when=asyncio.FIRST_COMPLETED,
)
for task in pending:
    task.cancel()
# If terminal_close triggered the exit, set non-zero exit code.
terminal_close_triggered = adapter.terminal_close_event.is_set()
```

Then propagate non-zero exit via `SystemExit(1)` if `terminal_close_triggered`.

## Acceptance criteria

| AC | Description |
|---|---|
| AC-NATS-FIX-006-01 | `_on_reconnect`, `_on_closed`, `_on_disconnect` are added to study-tutor's `NATSAdapter`. Unit tests cover each path. |
| AC-NATS-FIX-006-02 | NATSClient construction in `cli/main.py` (or wherever the wiring lands) passes the three callbacks. Confirmed by unit test asserting kwargs at construction. |
| AC-NATS-FIX-006-03 | Unit test for `_on_reconnect`: invoke directly; assert `register_agent(manifest)` is called once. |
| AC-NATS-FIX-006-04 | Unit test for `_on_closed`: invoke directly; assert `terminal_close_event` is set + structured ERROR log emitted. |
| AC-NATS-FIX-006-05 | CLI lifecycle loop (`_serve_adapter`) awaits both `shutdown_event` and `adapter.terminal_close_event`; on terminal-close, process exits non-zero. Unit test drives the path. |
| AC-NATS-FIX-006-06 | **GB10 manual probe**: with tutor running + registered in `agent-registry`, `docker stop ships-computer-nats; sleep 10; docker start ships-computer-nats`. Within ~5 s after broker is back, `nats kv ls agent-registry` shows the tutor again — no `docker restart` of the tutor required. Capture as an addendum RESULTS note. |
| AC-NATS-FIX-006-07 | Same probe with **prolonged** broker outage (`sleep 180`): tutor container exits non-zero within ~125 s with a clear `nats_terminally_closed` ERROR log. Docker restart policy then recovers it. |
| AC-NATS-FIX-006-08 | Existing study-tutor tests (`tests/test_nats_adapter*.py`, `tests/integration/test_nats_fleet*.py` if any) continue to pass. |

## Out of scope

- Refactoring `NATSAdapter` into a shared cross-repo library helper. The duplicated
  handler pattern across specialist-agent and study-tutor is a known post-demo cleanup
  candidate, but extracting it now adds coordination risk under the demo timeline.
- Changing `NATSConfig` defaults (`max_reconnect_attempts`, `reconnect_time_wait`).
- Anything in `nats_core` itself — that's TASK-NC10.
- Adding KV-watch observability for stale registrations (separate concern; see
  `tasks/backlog/nats-fleet-integration/TASK-NATS-PH2-002-kv-watch-test.md`).

## Related work

- `nats-core TASK-NC10` — **hard dependency.** Adds the callback API surface to
  `NATSClient`. Must land first.
- `specialist-agent TASK-NATS-009` — parallel consumer task. Same fix, peer repo.
  specialist-agent's already-defined-but-dead `_on_reconnect` is the implementation
  reference for the handler we add here.
- `tasks/backlog/nats-fleet-integration/TASK-NATS-PH2-003-stale-registry-runbook.md` —
  related operational doc on stale registrations. Update if the new fail-fast path
  changes the operator playbook.

## Demo-day note (2026-05-16 DDD Southwest)

If this task does NOT land before the demo, the operational mitigation is to check
`nats kv ls agent-registry` shortly before the demo. If the tutor is missing, `docker
restart study-tutor-<container>` to recover. Same fragile workaround as the parallel
specialist-agent task.
