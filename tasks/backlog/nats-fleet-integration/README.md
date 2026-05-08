# Feature: study-tutor NATS Fleet Integration (FEAT-NATS)

Three-phase build that makes study-tutor a first-class NATS fleet member alongside specialist-agent and forge. Replaces the MCP-only deployment with a NATS adapter so jarvis (and future fleet callers) can dispatch tutoring commands through the canonical request/reply contract.

**Demo deadline:** 2026-05-11 (Phase 1)
**DDD Southwest demo:** 2026-05-16 (Phases 2 & 3)

## Phases at a glance

| Phase | Tasks | Outcome | Deadline |
|---|---|---|---|
| 1 — Minimum viable adapter (with live registration + heartbeat) | 10 (PH1-001 → PH1-010) | jarvis can dispatch all 4 tutor commands; live KV discovery works; demo runs from a host process | **2026-05-11** |
| 2 — Hardening | 3 (PH2-001 → PH2-003) | Readiness gating; KV-watch test; stale registry runbook | post-demo |
| 3 — Docker / GB10 deployment | 5 (PH3-001 → PH3-005) | Containerised tutor running alongside specialist-agent on GB10 | by 2026-05-16 |

Plus 5 risk-tracked follow-ups (TASK-NATS-FU-001 through TASK-NATS-FU-005) for post-demo work.

## Where to read what

- **Strategy & decisions** → [`IMPLEMENTATION-GUIDE.md`](IMPLEMENTATION-GUIDE.md). Mermaid diagrams (data flow, sequence, dependencies), §4 Integration Contracts, wave plan, bug regression guard mapping.
- **Each task** → individual `TASK-NATS-PH*-NNN-*.md` files. Scope, acceptance criteria, implementation notes, Coach validation commands, seam tests where applicable.
- **Behaviour spec** → [`features/nats-fleet-integration/nats-fleet-integration.feature`](../../../features/nats-fleet-integration/nats-fleet-integration.feature). 31 Gherkin scenarios across 8 groups.
- **Canonical research** → [`docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md`](../../../docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md). 951 lines, file:line cited across specialist-agent, jarvis, forge, nats-core, nats-infrastructure.
- **Historical scope doc (superseded)** → [`features/nats-fleet-integration/nats-fleet-scope-and-build-plan.md`](../../../features/nats-fleet-integration/nats-fleet-scope-and-build-plan.md). Kept for reference; do not act on its task list.

## Decisions log (2026-05-08)

1. **Phase 1 includes live registration + heartbeat** — no stub-yaml fallback.
2. **Session durability uses hybrid Graphiti** (not JetStream KV) — TASK-NATS-FU-001, post-demo.
3. **Stale-agent reaper deferred to jarvis** — TASK-NATS-FU-002, jarvis repo, post-demo.
4. **ASSUM-007 deferred (Option C)** — jarvis MUST NOT duplicate-dispatch; tutor-side dedup contingent on real runbook observation (TASK-NATS-FU-005).

## Bug regression guards from day one

All four bugs documented in the [jarvis 2026-05-08 runbook](../../../../jarvis/docs/runbooks/RESULTS-jarvis-architect-align-dddsw-demo-2026-05-08-followup-post-W2.md) plus a predicted Bug #5 are wired into Coach validation:

- **Bug #1** PubAck race → PH1-004 (`_publish_result` raw-publish to inbox) + PH1-005 (`subscribe_with_reply`) + PH1-008 (smoke test asserts both paths)
- **Bug #2** `on_command` mapping miss → PH1-003 (declares map) + PH1-004 (`tool_to_command.get(c, c)` line) + PH1-008 (alias dispatch test)
- **Bug #3** `OPENAI_BASE_URL` /v1 → PH1-007 (.env.example) + PH3-002 (compose env block)
- **Bug #4** wire-tap subject pattern → PH3-004 (runbook documents flat pattern)
- **Bug #5** empty intents → PH1-002 (factory ships >= 1 intent + seam test)

## Operator follow-up tasks: 2

- **PH1-010** — E2E demo gate (Open WebUI → jarvis → tutor, 2026-05-11)
- **PH3-005** — GB10 E2E smoke test (containerised tutor, by 2026-05-16)

Both are `task_type: operator_handoff`. AutoBuild's Player ↔ Coach loop cannot satisfy them; the operator runs them manually with the runbook (TASK-NATS-PH3-004) as the procedure.

## Quick start

```bash
# Pick up the first task
/task-work TASK-NATS-PH1-001

# Or check what's ready (no blocked dependencies)
/task-status --filter=feature:nats-fleet-integration
```
