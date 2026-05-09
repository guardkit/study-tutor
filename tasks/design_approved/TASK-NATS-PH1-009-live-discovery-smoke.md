---
complexity: 4
created: 2026-05-08 00:00:00+00:00
dependencies:
- TASK-NATS-PH1-005
estimated_minutes: 60
feature_id: FEAT-NATS
id: TASK-NATS-PH1-009
implementation_mode: task-work
parent_review: TASK-REV-NATS-001
priority: critical
status: design_approved
tags:
- nats
- testing
- smoke
- phase-1
- decision-1
- discovery
task_type: testing
title: Live-discovery smoke - jarvis sees gcse-tutor without any stub-yaml fallback
updated: 2026-05-08 00:00:00+00:00
wave: 5
---

# Task: Live-discovery smoke - jarvis sees gcse-tutor without any stub-yaml fallback

## Description

Validates Decision 1 (2026-05-08): Phase 1 includes live registration + heartbeat, no stub-yaml fallback. This smoke test proves jarvis's CapabilitiesRegistry discovers the tutor through the live KV bucket alone, with zero stub configuration on the jarvis side.

## Scope

Create `tests/integration/test_live_discovery.py` with:

- A pytest fixture that spins up NATS with the `agent-registry` KV bucket but **no** stub-capabilities config on the jarvis side.
- A test that:
  1. Boots study-tutor's NATSAdapter — asserts the `gcse-tutor` row appears in `agent-registry` KV.
  2. Instantiates jarvis's `LiveCapabilitiesRegistry` (or a faithful stand-in if jarvis isn't importable from this repo) and points it at the same KV bucket.
  3. Asserts that registry resolution for `tool_name="tutor_start_session"` returns `agent_id="gcse-tutor"` as a candidate.
  4. Tears down the tutor adapter — asserts the KV row is removed within 30s (graceful deregister).

## Acceptance criteria

- [ ] Test boots tutor adapter, queries `agent-registry` KV, finds `gcse-tutor` row with the correct manifest payload.
- [ ] Test asserts capability resolution for `tutor_start_session` returns `gcse-tutor` (Decision 1 regression guard — discovery does NOT depend on stub yaml).
- [ ] Test tears down tutor and asserts the KV row is removed within 30s.
- [ ] No stub-capabilities yaml file is loaded or referenced by the test (assert path).
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation notes

- If jarvis is not importable from this repo, mock the resolver shape: read `agent-registry` KV directly via `nats-py` and assert presence + manifest validity.
- Cross-check: see [jarvis/src/jarvis/infrastructure/capabilities_registry.py:227-515](/Users/richardwoollcott/Projects/appmilla_github/jarvis/src/jarvis/infrastructure/capabilities_registry.py) for the actual `LiveCapabilitiesRegistry` shape.

## Coach validation

```bash
pytest tests/integration/test_live_discovery.py -v --timeout=60
ruff check tests/integration/test_live_discovery.py
```