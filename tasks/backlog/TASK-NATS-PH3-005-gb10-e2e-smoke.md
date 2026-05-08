---
id: TASK-NATS-PH3-005
title: GB10 E2E smoke test - full path Open WebUI through containerised tutor
task_type: operator_handoff
parent_review: TASK-REV-NATS-001
feature_id: FEAT-NATS
wave: 11
implementation_mode: task-work
complexity: 8
estimated_minutes: 120
status: pending
priority: high
created: 2026-05-08 00:00:00+00:00
updated: 2026-05-08 00:00:00+00:00
dependencies:
  - TASK-NATS-PH3-002
  - TASK-NATS-PH3-004
tags:
  - nats
  - e2e
  - phase-3
  - operator-handoff
  - gb10
---

# Task: GB10 E2E smoke test - full path Open WebUI through containerised tutor

## Description

The Phase 3 closer. Operator-driven validation that the containerised tutor on GB10 (running alongside specialist-agent) survives the same E2E path validated in TASK-NATS-PH1-010, but now from a Docker deployment rather than a host process. Generates the second RESULTS file under the new template.

This task is `task_type: operator_handoff` — live infrastructure (GB10), human-in-the-loop (Open WebUI), wall-clock observation. AutoBuild's Player ↔ Coach loop cannot satisfy these.

## Scope

Operator runs through the runbook (TASK-NATS-PH3-004) on GB10:

1. `./scripts/docker-build.sh` from study-tutor repo root → builds `study-tutor:latest`.
2. `docker compose -f docker-compose.study-tutor.yml up -d` against the live GB10 NATS.
3. Verify tutor container is up: `docker ps | grep gcse-tutor`, container logs show `nats_connect_success`, `capability_registry_loaded`, `agent_registered`.
4. Verify KV: `nats kv get agent-registry gcse-tutor` returns the manifest.
5. Verify heartbeat: `nats sub fleet.heartbeat.gcse-tutor` (timeout 60s) shows ≥1 envelope.
6. Run the same Open WebUI flow as TASK-NATS-PH1-010 (3-5 turns, end session, Graphiti episode).
7. Capture all artefacts to `docs/runbooks/evidence/feat-nats-001-gb10-{YYYY-MM-DD}/`.
8. Write `docs/runbooks/RESULTS-FEAT-NATS-003-gb10-{YYYY-MM-DD}.md` from the template.
9. Verify no Bug #1-#5 symptoms in any captured envelope or trace.

## Required operator follow-up

This task is `task_type: operator_handoff` — AutoBuild will not attempt it. The operator must verify the runtime acceptance criteria below manually, then mark the task complete via `/task-complete`.

- **AC-PH3-005-1**: study-tutor container runs alongside specialist-agent's dual-role stack on GB10. `docker ps` shows both healthy.
- **AC-PH3-005-2**: KV registration visible: `nats kv get agent-registry gcse-tutor` returns the full manifest within 10s of `compose up`.
- **AC-PH3-005-3**: Heartbeat envelopes observable on `fleet.heartbeat.gcse-tutor` at the configured 30s interval.
- **AC-PH3-005-4**: A live Open WebUI session through NATS Pipe → jarvis → containerised tutor reaches at least 3 user turns and ends cleanly.
- **AC-PH3-005-5**: No Bug #1-#5 symptoms observed in any captured envelope, log, or trace.
- **AC-PH3-005-6**: `docs/runbooks/RESULTS-FEAT-NATS-003-gb10-{YYYY-MM-DD}.md` exists, all gates green, "Demo blocking?" = NO.
- **AC-PH3-005-7**: Evidence archive under `docs/runbooks/evidence/feat-nats-001-gb10-{YYYY-MM-DD}/` contains chat log, wire-command log, wire-result log, container logs, jarvis traces.

## Implementation notes

Use the runbook from TASK-NATS-PH3-004 verbatim. If anything diverges, the runbook is wrong — fix the runbook, then re-run. Every divergence becomes a runbook bug or a Bug #N in the catalogue.

If GB10 is unavailable on the day, run on a local Docker setup as a degraded validation (note this clearly in the RESULTS file).
