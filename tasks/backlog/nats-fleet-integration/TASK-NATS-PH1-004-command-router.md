---
id: TASK-NATS-PH1-004
title: Implement CommandRouter with on_command, tool_to_command alias resolution (Bug
task_type: feature
parent_review: TASK-REV-NATS-001
feature_id: FEAT-NATS
wave: 3
implementation_mode: task-work
complexity: 6
estimated_minutes: 120
status: in_review
priority: critical
created: 2026-05-08 00:00:00+00:00
updated: 2026-05-08 00:00:00+00:00
dependencies:
- TASK-NATS-PH1-003
consumer_context:
- task: TASK-NATS-PH1-003
  consumes: tool_to_command_map
  framework: study_tutor.roles.registry.get_role
  driver: in-process Python registry
  format_note: "Map keys are MCP tool names (e.g. \"tutor_start_session\"); values\
    \ are canonical commands (e.g. \"start_session\"). Router MUST call self.tool_to_command.get(c,\
    \ c) \u2014 passthrough when not present, alias when present."
tags:
- nats
- feature
- command-router
- phase-1
- bug-1
- bug-2
autobuild_state:
  current_turn: 1
  max_turns: 7
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-39E1
  base_branch: main
  started_at: '2026-05-08T23:04:50.392149'
  last_updated: '2026-05-08T23:17:29.244800'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-05-08T23:04:50.392149'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Task: Implement CommandRouter with on_command, tool_to_command alias resolution (Bug #2), and reply_to honouring (Bug #1)

## Description

Build the dispatch layer that translates incoming `CommandPayload` envelopes into calls on the existing `MCPAdapter` business logic. Two **load-bearing** bug fixes must ship from day one:

1. **Bug #2 fix** (`tool_to_command.get(c, c)` alias resolution): incoming command names like `tutor_start_session` (the MCP tool name) must resolve to canonical commands like `start_session` before the dispatch table lookup. Without this, every jarvis dispatch fails with "command not supported".
2. **Bug #1 fix** (`reply_to` honouring): when the envelope carries a `reply_to` inbox header, the result must be **raw-published** to that inbox via `client.publish_raw(reply_to, ...)` *in addition to* the canonical envelope publish on `agents.result.<agent_id>`. Without this, jarvis's `client.request()` future resolves with the JetStream PubAck instead of the actual result.

Reference: [specialist-agent/src/specialist_agent/adapters/command_router.py:328-406](/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/adapters/command_router.py) (`on_command`), `:496-503` (Bug #2 fix line), `:1052-1103` (`_publish_result` Bug #1 fix).

## Scope

Create `src/study_tutor/adapters/command_router.py` with:

- `CommandRouter(mcp_adapter, tool_to_command, agent_id, client)`
- `on_command(envelope: MessageEnvelope)` — parses `CommandPayload`, calls `_dispatch_command`, calls `_publish_result`.
- `_dispatch_command(command, args)` — applies `command = self.tool_to_command.get(command, command)` **before** the command_map lookup (Bug #2). Raises `UnsupportedCommandError` for unknown commands with a helpful message listing supported commands.
- `_publish_result(reply_to, result_payload)` — if `reply_to` is set, `client.publish_raw(reply_to, result_payload.model_dump_json())`. Always also publish to `agents.result.<agent_id>` via the canonical envelope path (Bug #1).
- 4 dispatch handlers wrapping `MCPAdapter.tutor_start_session`, `tutor_turn`, `tutor_session_status`, `tutor_session_end` (await each, wrap return in `ResultPayload(success=True, result=...)`, catch exceptions into `ResultPayload(success=False, error=...)`).

## Acceptance criteria

- [ ] Unit test: `on_command` with `command="tutor_start_session"` resolves to `start_session` via `tool_to_command` and invokes `MCPAdapter.tutor_start_session` (Bug #2 regression guard).
- [ ] Unit test: `on_command` with `command="start_session"` (canonical) bypasses the alias map and works directly (passthrough behaviour).
- [ ] Unit test: `_publish_result` with `reply_to="_INBOX.abc"` calls `client.publish_raw("_INBOX.abc", ...)` AND publishes to `agents.result.gcse-tutor` (Bug #1 regression guard).
- [ ] Unit test: `_publish_result` with `reply_to=None` only publishes to the canonical result topic.
- [ ] Unit test: unknown command name returns `ResultPayload(success=False, error=...)` and the error message includes the list of supported commands.
- [ ] Unit test: handler exception is caught and surfaces as `ResultPayload(success=False, error=...)` (no propagation past `on_command`).
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation notes

- **DO NOT inline the `tool_to_command` map.** Read it from `get_role("tutor").tool_to_command` so it stays single-sourced.
- The architect's `command_router.py` is ~1100 lines because it handles many roles, mode inference, tool-call subjects, etc. study-tutor's router is ~150-200 lines. Match the *shape* of the canonical functions, not the full surface area.
- For the `_publish_result` raw-publish, see [`nats-core/src/nats_core/client.py:225-243`](/Users/richardwoollcott/Projects/appmilla_github/nats-core/src/nats_core/client.py) for the `publish_raw` signature.

## Coach validation

```bash
pytest tests/unit/adapters/test_command_router.py -v
ruff check src/study_tutor/adapters/command_router.py tests/unit/adapters/test_command_router.py
```
