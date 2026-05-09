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
status: in_review
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
autobuild_state:
  current_turn: 4
  max_turns: 7
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-39E1
  base_branch: main
  started_at: '2026-05-08T22:24:47.488979'
  last_updated: '2026-05-08T23:04:50.353472'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Advisory (non-blocking): task-work produced a report with 2 of 3
      expected agent invocations. Missing phases: 3 (Implementation). Consider invoking
      these agents via the Task tool to strengthen stack-specific quality:

      - Phase 3: `the stack-specific Phase-3 specialist` (Implementation)

      - BDD oracle: 1 scenario(s) failed during pytest-bdd execution. Implementation
      does not satisfy the Gherkin specification.'
    timestamp: '2026-05-08T22:24:47.488979'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- Advisory (non-blocking): task-work produced a report with 2 of 3
      expected agent invocations. Missing phases: 3 (Implementation). Consider invoking
      these agents via the Task tool to strengthen stack-specific quality:

      - Phase 3: `the stack-specific Phase-3 specialist` (Implementation)

      - BDD oracle: 1 scenario(s) failed during pytest-bdd execution. Implementation
      does not satisfy the Gherkin specification.'
    timestamp: '2026-05-08T22:33:04.967773'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: '- Advisory (non-blocking): task-work produced a report with 2 of 3
      expected agent invocations. Missing phases: 3 (Implementation). Consider invoking
      these agents via the Task tool to strengthen stack-specific quality:

      - Phase 3: `the stack-specific Phase-3 specialist` (Implementation)

      - BDD oracle: 1 scenario(s) failed during pytest-bdd execution. Implementation
      does not satisfy the Gherkin specification.'
    timestamp: '2026-05-08T22:41:54.724414'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 4
    decision: approve
    feedback: null
    timestamp: '2026-05-08T22:48:31.786926'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
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
- BDD oracle is scoped to a focused per-task feature file
  (`features/nats-fleet-integration/by-task/TASK-NATS-PH1-006.feature` +
  `test_TASK-NATS-PH1-006.py`) to work around the pytest-bdd v8 unbound-step
  failure mode. See TASK-NATS-FIX-001 and TASK-REV-CC40 for context. The
  upstream GuardKit fix is tracked as TASK-FIX-CC-BDD; once that lands the
  focused pair can be deleted and validation can point back at the master.

## Coach validation

```bash
pytest features/nats-fleet-integration/by-task/test_TASK-NATS-PH1-006.py -v
pytest tests/unit/cli/test_serve_nats.py -v
study-tutor serve-nats --help | grep -E '(--nats|--agent-id|--log-level)'
ruff check src/study_tutor/cli/main.py tests/unit/cli/test_serve_nats.py
```
