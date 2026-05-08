---
id: TASK-NATS-PH1-010
title: E2E demo gate - Open WebUI to NATS Pipe to jarvis to tutor session created
task_type: operator_handoff
parent_review: TASK-REV-NATS-001
feature_id: FEAT-NATS
wave: 6
implementation_mode: task-work
complexity: 7
estimated_minutes: 120
status: pending
priority: critical
created: 2026-05-08 00:00:00+00:00
updated: 2026-05-08 00:00:00+00:00
dependencies:
  - TASK-NATS-PH1-008
  - TASK-NATS-PH1-009
tags:
  - nats
  - e2e
  - demo
  - phase-1
  - operator-handoff
  - demo-critical
---

# Task: E2E demo gate - Open WebUI to NATS Pipe to jarvis to tutor session created

## Description

The Phase 1 demo gate. Operator-driven validation that exercises the full path from a browser chat in Open WebUI through the NATS Pipe Function, jarvis's intent router, and into a live study-tutor session. Generates the RESULTS file that becomes evidence for the 2026-05-11 demo.

This task is `task_type: operator_handoff` because it requires live infrastructure (GB10), human-in-the-loop interaction (Open WebUI chat), and wall-clock observation that AutoBuild's Player ↔ Coach loop cannot satisfy.

## Scope

Operator runs through this checklist on GB10 against a live deployment:

1. Bring up the NATS server, llama-swap (with `gemma4-tutor` loaded), jarvis container, study-tutor container (will be Phase 3, but for Phase 1 demo, run the tutor process directly via `study-tutor serve-nats` from a host shell).
2. Open Open WebUI, select the NATS-fleet pipe, send a tutoring prompt (e.g. "Help me revise GCSE English Lit Macbeth Act 1").
3. Watch jarvis dispatch via wire-tap on `agents.command.>` and `agents.result.>` — confirm:
   - jarvis calls `dispatch_by_capability(tool_name="tutor_start_session", ...)`.
   - The reply lands on the inbox with a valid `ResultPayload` (Bug #1 — not a PubAck).
   - The same `ResultPayload` is observable on `agents.result.gcse-tutor` (Bug #1 — both paths).
4. Continue the conversation through 3-5 turns; confirm `tutor_turn` round-trips successfully each time.
5. Check `tutor_session_status` returns the live transcript.
6. End the session via `tutor_session_end`; confirm a `SessionCompletedEpisode` lands in Graphiti.
7. Capture: chat transcript, wire-tap logs (command + result), routing-history traces, container logs, llama-swap request log.
8. Write `docs/runbooks/RESULTS-FEAT-NATS-001-phase-1-demo-{YYYY-MM-DD}.md` mirroring the jarvis runbook RESULTS structure (HEAD shas, phase × gate table, "Demo blocking?" line, bug catalogue if any).

## Required operator follow-up

This task is `task_type: operator_handoff` — AutoBuild will not attempt it. The operator must verify the runtime acceptance criteria below manually, then mark the task complete via `/task-complete`.

- **AC-PH1-010-1**: A live MCP-adjacent tutor session is conducted from Open WebUI through the NATS Pipe → jarvis → study-tutor on GB10. Session reaches at least 3 user turns and ends cleanly via `tutor_session_end`.
- **AC-PH1-010-2**: Wire-tap evidence on `agents.command.>` and `agents.result.>` shows valid `ResultPayload` envelopes for every dispatch (no `{"stream":"AGENTS","seq":N}` PubAck leakage). Logs captured under `docs/runbooks/evidence/feat-nats-001/`.
- **AC-PH1-010-3**: jarvis routing-history traces show `outcome_type=success` (or equivalent) for each tutor command.
- **AC-PH1-010-4**: A `SessionCompletedEpisode` is visible in Graphiti for the demo session.
- **AC-PH1-010-5**: `docs/runbooks/RESULTS-FEAT-NATS-001-phase-1-demo-{YYYY-MM-DD}.md` exists, contains all participating-repo HEAD shas, a phase × gate table, and a clear "Demo blocking?" line.

## Implementation notes

The runbook structure is documented in [docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md § Runbook artifact pattern](../../../docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md). Use the jarvis runbooks as the canonical template:

- [jarvis/docs/runbooks/RUNBOOK-jarvis-architect-align-dddsw-demo.md](/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/runbooks/RUNBOOK-jarvis-architect-align-dddsw-demo.md) — procedure
- [jarvis/docs/runbooks/RESULTS-jarvis-architect-align-dddsw-demo-2026-05-08.md](/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/runbooks/RESULTS-jarvis-architect-align-dddsw-demo-2026-05-08.md) — RESULTS shape
- [jarvis/docs/runbooks/evidence/dddsw-demo/](/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/runbooks/evidence/dddsw-demo/) — evidence directory shape

If anything blocks (PubAck leakage, dispatch timeout, registry missing), file a bug with the same shape as the jarvis runbook's bug catalogue (symptom / cause / fix / where-it-must-live).
