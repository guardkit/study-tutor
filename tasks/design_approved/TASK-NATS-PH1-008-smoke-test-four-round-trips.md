---
complexity: 5
created: 2026-05-08 00:00:00+00:00
dependencies:
- TASK-NATS-PH1-005
- TASK-NATS-PH1-006
estimated_minutes: 90
feature_id: FEAT-NATS
id: TASK-NATS-PH1-008
implementation_mode: task-work
parent_review: TASK-REV-NATS-001
priority: critical
status: design_approved
tags:
- nats
- testing
- smoke
- phase-1
- bug-1
- bug-2
task_type: testing
title: Smoke test - all 4 commands round-trip through NATS adapter (no PubAck leakage)
updated: 2026-05-08 00:00:00+00:00
wave: 5
---

# Task: Smoke test - all 4 commands round-trip through NATS adapter (no PubAck leakage)

## Description

Integration smoke test that exercises each of the 4 tutor commands end-to-end through a real NATS server. This is the gate that proves the canonical contract is wired correctly before TASK-NATS-PH1-010 (the operator-driven E2E demo).

Specifically guards against Bugs #1 (PubAck leakage on the request inbox) and #2 (`tool_to_command` alias miss).

## Scope

Create `tests/integration/test_nats_smoke.py` with:

- A pytest fixture `nats_server` that spins up a real NATS server (via `testcontainers` or a `nats-server -js` subprocess fixture) with the AGENTS, FLEET, and `agent-registry` KV bucket provisioned.
- A pytest fixture `tutor_adapter` that boots `study_tutor.adapters.nats_adapter.NATSAdapter` against the test NATS, waits for `_ready`, and tears down on cleanup.
- A parametrised test that, for each of `tutor_start_session`, `tutor_turn`, `tutor_session_status`, `tutor_session_end`:
  - Builds a valid `MessageEnvelope` wrapping `CommandPayload(command=<name>, args=...)`
  - Publishes via `nats_client.request(subject, envelope, timeout=30)` (NOT `client.publish` — must use request/reply to exercise the inbox path)
  - Asserts the reply parses as `ResultPayload` (NOT a JetStream PubAck like `{"stream":"AGENTS","seq":N}` — Bug #1 regression guard)
  - Asserts `result.success is True`
  - Asserts a copy of the result envelope is observable on `agents.result.gcse-tutor` via wire-tap (Bug #1 — both inbox AND topic must receive)

## Acceptance criteria

- [ ] All 4 commands round-trip through NATS and return `ResultPayload(success=True)`.
- [ ] No reply parses as a `{"stream":...,"seq":...}` PubAck (Bug #1 regression guard — explicit assertion).
- [ ] Wire-tap on `agents.result.gcse-tutor` captures one envelope per dispatch (Bug #1 — topic path also exercised).
- [ ] Test using `tool_to_command` alias (`command="tutor_start_session"`) succeeds — proves Bug #2 fix is wired (regression guard).
- [ ] Test using canonical name (`command="start_session"`) also succeeds — proves passthrough behaviour.
- [ ] Tests are deterministic and CI-runnable (no manual setup beyond the fixture-provided NATS).
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation notes

- For the NATS fixture, two viable options: `testcontainers-python` with the `nats:2-alpine` image, or a `pytest_asyncio` fixture that subprocesses `nats-server -js -p <random_port>`. Either works; pick the lighter-weight option.
- The wire-tap assertion needs a separate `client.subscribe("agents.result.gcse-tutor", ...)` set up *before* the dispatch — see jarvis runbook patterns at [jarvis/docs/runbooks/evidence/dddsw-demo/](/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/runbooks/evidence/dddsw-demo/) for the wire-tap shape.
- Do NOT use `agents.result.gcse-tutor.>` for the wire-tap subject — that pattern returns 0 envelopes (Bug #4). Use the flat subject.
- Guard against flakiness: use explicit `await asyncio.sleep(0.05)` after dispatch before reading the wire-tap, or better, use a `nats_client.subscribe` with an `asyncio.Event` set on first message.

## Coach validation

```bash
pytest tests/integration/test_nats_smoke.py -v --timeout=60
ruff check tests/integration/test_nats_smoke.py
```