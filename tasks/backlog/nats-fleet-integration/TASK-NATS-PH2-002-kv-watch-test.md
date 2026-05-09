---
id: TASK-NATS-PH2-002
title: Add NATSKVManifestRegistry-backed Phase 2 KV-watch test for reg/dereg events
task_type: testing
parent_review: TASK-REV-NATS-001
feature_id: FEAT-NATS
wave: 8
implementation_mode: task-work
complexity: 5
estimated_minutes: 90
status: in_review
priority: medium
created: 2026-05-08 00:00:00+00:00
updated: 2026-05-08 00:00:00+00:00
dependencies:
- TASK-NATS-PH1-005
tags:
- nats
- testing
- kv-watch
- phase-2
autobuild_state:
  current_turn: 1
  max_turns: 7
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-39E1
  base_branch: main
  started_at: '2026-05-08T23:42:51.338234'
  last_updated: '2026-05-08T23:56:18.534401'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-05-08T23:42:51.338234'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Task: Add NATSKVManifestRegistry-backed Phase 2 KV-watch test for reg/dereg events

## Description

Phase 1's discovery test (TASK-NATS-PH1-009) verifies KV state at points in time. This test verifies that jarvis's KV-watch sees registration *and* deregistration *events* synchronously — important because jarvis's CapabilitiesRegistry caches resolution decisions and stale cache + missed dereg event = ghost agent.

## Scope

Create `tests/integration/test_kv_watch_lifecycle.py` with:

- A pytest fixture for NATS with `agent-registry` KV bucket.
- A test that:
  1. Subscribes to KV bucket changes via `nats-py`'s KV watch API (or `nats_core`'s wrapper).
  2. Boots the tutor adapter — asserts a "put" event for `gcse-tutor` is observed within 5s.
  3. Triggers `adapter.stop()` (graceful) — asserts a "delete" or "purge" event is observed within 5s.
  4. Boots a fresh adapter, then SIGKILLs it (no graceful stop) — asserts the row is **still present** (no automatic TTL cleanup), documenting the stale-row condition that justifies TASK-NATS-FU-002 (jarvis-side reaper).

## Acceptance criteria

- [ ] Test observes a KV put event for `gcse-tutor` within 5s of `adapter.start()` completing.
- [ ] Test observes a KV delete event for `gcse-tutor` within 5s of `adapter.stop()` completing.
- [ ] Test confirms SIGKILL leaves a stale row (no TTL cleanup) — this is documentation-of-known-limitation, not a failure mode (Decision 3, 2026-05-08).
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation notes

- Use `nats_core.NATSClient.kv_watch()` if it exists, or the underlying `nats-py` `kv.watch()` directly.
- For SIGKILL, use `os.kill(adapter._task.pid, signal.SIGKILL)` against a subprocess fixture. Do NOT call `os.kill` against the test process itself.

## Coach validation

```bash
pytest tests/integration/test_kv_watch_lifecycle.py -v --timeout=60
ruff check tests/integration/test_kv_watch_lifecycle.py
```
