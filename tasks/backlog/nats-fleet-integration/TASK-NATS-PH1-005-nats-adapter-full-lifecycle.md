---
id: TASK-NATS-PH1-005
title: Implement NATSAdapter with full lifecycle (subscribe, register, heartbeat,
  deregister)
task_type: feature
parent_review: TASK-REV-NATS-001
feature_id: FEAT-NATS
wave: 4
implementation_mode: task-work
complexity: 8
estimated_minutes: 180
status: in_review
priority: critical
created: 2026-05-08 00:00:00+00:00
updated: 2026-05-08 00:00:00+00:00
dependencies:
- TASK-NATS-PH1-002
- TASK-NATS-PH1-004
consumer_context:
- task: TASK-NATS-PH1-002
  consumes: AgentManifest
  framework: nats_core.NATSClient.register_agent
  driver: NATS KV (agent-registry bucket)
  format_note: 'Manifest must be a fully-validated nats_core.manifest.AgentManifest
    with len(intents) >= 1 (Bug #5 guard).'
- task: TASK-NATS-PH1-004
  consumes: CommandRouter
  framework: nats_core.NATSClient.subscribe_with_reply
  driver: asyncio NATS subscription
  format_note: 'Adapter MUST call subscribe_with_reply (NOT subscribe) so the reply_to
    inbox propagates to CommandRouter._publish_result (Bug #1 guard).'
tags:
- nats
- feature
- adapter
- lifecycle
- phase-1
- bug-1
- bug-5
- decision-1
autobuild_state:
  current_turn: 2
  max_turns: 7
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-39E1
  base_branch: main
  started_at: '2026-05-08T23:17:29.282226'
  last_updated: '2026-05-08T23:42:51.267480'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Advisory (non-blocking): task-work produced a report with 2 of 3\
      \ expected agent invocations. Missing phases: 3 (Implementation). Consider invoking\
      \ these agents via the Task tool to strengthen stack-specific quality:\n- Phase\
      \ 3: `the stack-specific Phase-3 specialist` (Implementation)\n- Not all acceptance\
      \ criteria met:\n  \u2022 Integration test (against a real NATS via `nats-server`\
      \ in test fixture or `testcontainers`): full s"
    timestamp: '2026-05-08T23:17:29.282226'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-05-08T23:32:33.612209'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Task: Implement NATSAdapter with full lifecycle (subscribe, register, heartbeat, deregister)

## Description

The lifecycle manager. Connects to NATS, registers the manifest in the `agent-registry` KV bucket, starts the heartbeat loop, subscribes to the command subject (with reply_to propagation — Bug #1 fix), and on shutdown drains in-flight commands, cancels the heartbeat, deregisters, and closes the connection cleanly.

This task collapses the review doc's TASK-NATS-PH1-005/006/007 into a single cohesive adapter (per Decision 1 — Phase 1 includes live registration + heartbeat from day one, no stub-yaml fallback).

Reference: [specialist-agent/src/specialist_agent/adapters/nats_adapter.py:42-312](/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/adapters/nats_adapter.py). Mirror its structure closely — the architect's adapter is the canonical template.

## Scope

Create `src/study_tutor/adapters/nats_adapter.py` with:

- `NATSAdapter(config: AgentConfig, manifest: AgentManifest, command_router: CommandRouter)`
- `start()`:
  1. Connect to NATS via `NATSClient(config)`.
  2. Register manifest: `await client.register_agent(manifest)`.
  3. Subscribe to `agents.command.<agent_id>` via `client.subscribe_with_reply(subject, command_router.on_command)` — **NOT** `subscribe` (Bug #1 fix).
  4. Start heartbeat task: `asyncio.create_task(self._heartbeat_loop(), name=f"heartbeat-{agent_id}")`.
  5. Set `self._ready` event.
- `stop()`:
  1. Unsubscribe from command subject.
  2. Wait for in-flight tasks to drain (with `_shutdown_timeout=30.0` matching architect).
  3. Cancel heartbeat task.
  4. Deregister: `await client.deregister_agent(agent_id, reason="shutdown")`.
  5. Disconnect.
  6. Clear `_ready`.
- `_heartbeat_loop()` — periodic `client.heartbeat(agent_id)` at `config.heartbeat_interval_seconds` (default 30).

## Acceptance criteria

- [ ] `await adapter.start()` connects to NATS, registers the manifest in `agent-registry`, subscribes to the command subject, starts the heartbeat loop, and sets `_ready` — verified via mocked `NATSClient` in unit tests.
- [ ] Subscription uses `subscribe_with_reply`, **not** `subscribe` (Bug #1 regression guard — assert via mock call inspection).
- [ ] `await adapter.stop()` deregisters, cancels heartbeat, drains in-flight (within 30s shutdown_timeout), and closes the connection.
- [ ] Heartbeat publishes at the configured interval (test with a stub clock or short interval).
- [ ] Active-task counter increments on `on_command` start and decrements on completion (so `stop()` knows when to wait).
- [ ] Integration test (against a real NATS via `nats-server` in test fixture or `testcontainers`): full start → dispatch one command → stop round-trip succeeds, with the manifest visible in `agent-registry` between start and stop.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation notes

- The architect's adapter has `_shutdown_timeout: float = 30.0` hardcoded ([nats_adapter.py:72](/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/adapters/nats_adapter.py)). Match this value for parity.
- Heartbeat interval comes from `AgentConfig.heartbeat_interval_seconds` (default 30) — read it from config, do not hardcode.
- For the active-task counter: the architect tracks this in `self._active_tasks: int` and decrements in a `try/finally` around `command_router.on_command`. Mirror exactly.
- See [nats-core/src/nats_core/client.py:177-223](/Users/richardwoollcott/Projects/appmilla_github/nats-core/src/nats_core/client.py) for `subscribe_with_reply` signature.

## Coach validation

```bash
pytest tests/unit/adapters/test_nats_adapter.py tests/integration/test_adapter_lifecycle.py -v
ruff check src/study_tutor/adapters/nats_adapter.py tests/unit/adapters/test_nats_adapter.py tests/integration/test_adapter_lifecycle.py
```
