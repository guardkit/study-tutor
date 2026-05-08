---
id: TASK-NATS-PH1-006
title: Add study-tutor serve-nats CLI subcommand
task_type: feature
parent_review: TASK-REV-NATS-001
feature_id: FEAT-NATS
wave: 3
implementation_mode: task-work
complexity: 4
estimated_minutes: 60
status: pending
priority: critical
created: 2026-05-08 00:00:00+00:00
updated: 2026-05-08 00:00:00+00:00
dependencies:
  - TASK-NATS-PH1-001
tags:
  - nats
  - feature
  - cli
  - phase-1
---

# Task: Add study-tutor serve-nats CLI subcommand

## Description

Wire the existing CLI surface to launch the NATSAdapter as a long-running process. Mirrors specialist-agent's `serve-nats` subcommand at [cli/main.py:1515-1670, 1712-1769](/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/cli/main.py).

The subcommand is the entry point used by Phase 3's Docker image and by anyone running the tutor against a local NATS for development.

## Scope

Update `src/study_tutor/cli/main.py` to add:

- `study-tutor serve-nats` subcommand with flags:
  - `--nats <url>` — NATS server URL (default from `NATS_URL` env)
  - `--agent-id <id>` — agent_id override (default `gcse-tutor`)
  - `--log-level <level>` — log level (default INFO)
- Body: load `AgentConfig` from environment, build manifest via `_tutor_manifest_factory`, instantiate `MCPAdapter` (existing) → `CommandRouter` → `NATSAdapter`, call `await adapter.start()`, install SIGTERM/SIGINT handlers that call `await adapter.stop()`, then `await adapter._stop_event.wait()` (or equivalent run-forever loop).

## Acceptance criteria

- [ ] `study-tutor serve-nats --help` prints flag surface matching `--nats`, `--agent-id`, `--log-level`.
- [ ] `study-tutor serve-nats --nats nats://localhost:4222` starts the adapter, blocks until SIGTERM, then shuts down cleanly.
- [ ] SIGTERM during a running tutor process triggers `adapter.stop()` and the process exits with code 0 within the drain window (30s).
- [ ] If `nats-core`'s `AgentConfig` validation fails (e.g. invalid `NATS_URL`), the CLI exits 1 with a clear error message.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation notes

- The architect uses `argparse` subparsers. Match study-tutor's existing CLI pattern (look at `cli/main.py` for the convention).
- For signal handlers, see specialist-agent's pattern: `loop.add_signal_handler(signal.SIGTERM, partial(asyncio.create_task, adapter.stop()))`.
- Do not re-implement adapter wiring — instantiate the components from this task and let TASK-NATS-PH1-005 own the lifecycle.

## Coach validation

```bash
pytest tests/unit/cli/test_serve_nats.py -v
study-tutor serve-nats --help | grep -E '(--nats|--agent-id|--log-level)'
ruff check src/study_tutor/cli/main.py tests/unit/cli/test_serve_nats.py
```
