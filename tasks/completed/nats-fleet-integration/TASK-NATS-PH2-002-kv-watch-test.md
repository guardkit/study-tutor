---
complexity: 5
created: 2026-05-08 00:00:00+00:00
dependencies:
- TASK-NATS-PH1-005
estimated_minutes: 90
feature_id: FEAT-NATS
id: TASK-NATS-PH2-002
implementation_mode: task-work
parent_review: TASK-REV-NATS-001
priority: medium
status: completed
tags:
- nats
- testing
- kv-watch
- phase-2
task_type: testing
title: Add NATSKVManifestRegistry-backed Phase 2 KV-watch test for reg/dereg events
updated: 2026-05-08 00:00:00+00:00
wave: 8
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