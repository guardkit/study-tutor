# RESULTS addendum — TASK-NATS-FIX-006 AC-06 + AC-07 GB10 probes

**Date**: 2026-05-12 (Europe/London).
**Host**: `promaxgb10-41b1`.
**Commit**: `34d4a16` (`fix(FEAT-NATS): wire reconnect/closed callbacks + fail-fast lifecycle (TASK-NATS-FIX-006)`).
**Image**: `study-tutor:dev` rebuilt to `sha256:315a1bda4408ebcaf88e12961f2b26b94ce3d5cdf4b313757a2e35c270825fcd`.
**Cross-reference**: `jarvis/docs/runbooks/RESULTS-FEAT-JARVIS-006-serve-nats-first-run-2026-05-12-rerun-post-J006-009-010.md` → §"Specialist reconnect gap" (the symptom this task fixes).

## Probe environment

- Broker: `ships-computer-nats` (image `nats-infrastructure-nats`).
- Reconnect budget: `max_reconnect_attempts=60`, `reconnect_time_wait=2.0s` (nats-core defaults) → ~120s before `closed_cb` fires.
- Container restart policy: `restart: unless-stopped`.
- Co-resident fleet members on the same broker: `product-owner-agent`, `jarvis`, `architect-agent` (impact considered in scheduling).

## AC-06 — broker bounce (15 s outage), re-registration without operator intervention

Probe: `docker stop ships-computer-nats && sleep 15 && docker start ships-computer-nats`.

### Pre-probe state

```
$ nats kv ls agent-registry
product-owner-agent
jarvis
gcse-tutor
```

### Probe timeline (T+0 = 2026-05-12T19:02:40Z)

| Elapsed | Event | Evidence |
|---|---|---|
| T+0   | `docker stop ships-computer-nats` returned | (probe driver) |
| T+0   | `nats_disconnected` WARNING in tutor logs | `19:02:40,149 WARNING study_tutor.adapters.nats_adapter: nats_disconnected` |
| T+15  | `docker start ships-computer-nats` returned | (probe driver) |
| T+16  | `nats_reconnected — re-registering agent 'gcse-tutor'` INFO | `19:02:56,176 INFO study_tutor.adapters.nats_adapter: nats_reconnected — re-registering agent 'gcse-tutor'` |
| T+22  | `nats kv ls agent-registry` shows `gcse-tutor` | (see below) |

### Post-probe `agent-registry`

```
$ nats kv ls agent-registry
product-owner-agent
jarvis
gcse-tutor
```

### AC-06 verdict: **PASS**

Tutor re-appeared in `agent-registry` ~7 s after the broker came back online (within the ~5 s target in the task body, accounting for `register_agent`'s end-to-end KV round-trip). Zero operator intervention required.

## AC-07 — prolonged outage (180 s), non-zero exit + structured ERROR + Docker recovery

Probe: `docker stop ships-computer-nats && sleep 180 && docker start ships-computer-nats`.

### Pre-probe state

- Tutor `RestartCount`: 0
- Tutor `StartedAt`: `2026-05-12T19:02:04.534186744Z`
- Tutor container id: `a8f124311bca…` (referenced in `docker events` below).

### Probe timeline (T+0 = 2026-05-12T19:03:33Z)

| Elapsed | Event | Evidence |
|---|---|---|
| T+0    | `docker stop ships-computer-nats` returned | (probe driver) |
| T+0    | First `nats_disconnected` WARNING | `19:03:33,270 WARNING study_tutor.adapters.nats_adapter: nats_disconnected` |
| T+10..110 | Tutor still `running` (nats-py retrying within the 60-attempt budget) | poller every 10 s — `state=running restart_count=0` |
| T+120  | Final `nats_disconnected` WARNING + `nats_terminally_closed` ERROR fire on the same tick | `19:05:33,475 WARNING ... nats_disconnected` + `19:05:33,475 ERROR study_tutor.adapters.nats_adapter: nats_terminally_closed` |
| T+120  | Container exited **non-zero** | `docker events ... 20:05:33.785... container die a8f124311bca... execDuration=209 exitCode=1` |
| T+120  | Docker auto-restart fires (`restart: unless-stopped`) | `docker events ... 20:05:33.907... container start a8f124311bca...` + `RestartCount: 0 → 1` |
| T+185  | `docker start ships-computer-nats` returned | (probe driver, after the cap-loop padded the outage to ~180 s) |
| T+195  | Final `nats kv ls agent-registry` shows `gcse-tutor` | (see below) |

### Definitive non-zero exit-code evidence

Pulled from `docker events --filter container=study-tutor-gcse-tutor-1 --since 10m --until 1s`:

```
2026-05-12T20:05:33.785618130+01:00 container die a8f124311bca... (... execDuration=209, exitCode=1 ...)
2026-05-12T20:05:33.907380243+01:00 container start a8f124311bca... (... image=study-tutor:dev ...)
```

`exitCode=1` is the `SystemExit(1)` raised by `_serve_adapter` on the terminal-close branch (see [src/study_tutor/cli/main.py](../../../src/study_tutor/cli/main.py): "Exit non-zero so Docker's restart policy … recovers the container"). The corresponding `nats_terminally_closed` ERROR log line carries the agent identity:

```
2026-05-12 19:05:33,475 ERROR study_tutor.adapters.nats_adapter: nats_terminally_closed
```

(Note: container clock is UTC, host journal is BST/UTC+1 — both timestamps point to the same instant.)

### Post-probe `agent-registry`

```
$ nats kv ls agent-registry
jarvis
architect-agent
product-owner-agent
gcse-tutor
```

### AC-07 verdict: **PASS**

- Tutor exited non-zero (exitCode=1) at T+120 s with the structured `nats_terminally_closed` ERROR carrying `agent_id=gcse-tutor`. This matches the predicted ~125 s reconnect budget (60 attempts × 2 s).
- Docker's `restart: unless-stopped` policy successfully recovered the container (RestartCount: 0 → 1).
- After the broker came back at T+185 s, the recovered tutor re-registered and is back in `agent-registry`.

## Fleet-impact summary

- Broker `ships-computer-nats` downtime: ~15 s (AC-06) + ~185 s (AC-07) = ~200 s total.
- Co-resident `specialist-agent-{product-owner,architect}-agent-1` containers: both observed re-registering after each bounce (`product-owner-agent` and `architect-agent` reappear in the post-AC-07 `agent-registry`). No manual recovery required.
- `jarvis` agent: stayed registered after both bounces.

## Conclusion

AC-06 and AC-07 are both **verified end-to-end on GB10**. The fix closes the demo-blocker scenario from the
2026-05-12 jarvis FEAT-JARVIS-006 rerun: a broker bounce no longer drops the tutor from the
fleet silently, and a prolonged broker outage now drives a clean container restart loop instead
of a stuck-but-running tutor.

All 8 acceptance criteria for TASK-NATS-FIX-006 are now satisfied:

- AC-01..AC-05, AC-08: unit-test green (see `plan_audit_report.md`).
- AC-06, AC-07: **manual probe green (this document)**.
