---
id: TASK-NATS-FIX-004
title: Hand-implement CommandRouter (PH1-004) from prior-run evidence and mark task completed in feature.yaml
status: completed
task_type: implementation
implementation_mode: manual
parent_review: TASK-REV-F30A
feature_id: FEAT-39E1
feature_slug: feat-39e1-recovery
wave: 1
priority: high
created: 2026-05-10T18:00:00Z
updated: 2026-05-10T18:50:00Z
completed_at: 2026-05-10T18:50:00Z
completion_commit: c0e8ab9
previous_state: in_review
complexity: 4
tags: [autobuild-recovery, nats-fleet, command-router, manual-implementation]
related_tasks:
  - TASK-NATS-PH1-004
  - TASK-REV-F30A
dependencies: []
blocks:
  - TASK-NATS-FIX-005
  - TASK-NATS-FIX-006
inputs:
  prior_run_player_report: .guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-004/player_turn_1.json
  prior_run_task_results: .guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-004/task_work_results.json
  original_task: tasks/backlog/nats-fleet-integration/TASK-NATS-PH1-004-command-router.md
  feature_yaml: .guardkit/features/FEAT-39E1.yaml
  review_report: .claude/reviews/TASK-REV-F30A-review-report.md
test_results:
  status: passed
  passed: 9
  failed: 0
  command: pytest tests/unit/adapters/test_command_router.py
  ruff: clean
  last_run: 2026-05-10T18:30:00Z
---

# Task: Hand-implement CommandRouter (PH1-004) from prior-run evidence

## Description

The 2026-05-10 FEAT-39E1 autobuild run-3 failed PH1-004 with `max_turns_exceeded` not because the implementation was hard, but because the worktree's `.gitignore` silently dropped every `src/study_tutor/adapters/*.py` file from `git add -A`. See [TASK-REV-F30A review report](../../../.claude/reviews/TASK-REV-F30A-review-report.md) for the full root-cause analysis.

The Player has effectively *already done* the implementation work twice (May 8 prior run + May 10 run-3 turn 1) and produced detailed acceptance-criterion evidence including specific code constructs and test names — but neither attempt's `.py` files reached the merged branch because the worktree's `.gitignore` had not been rebased to include the `12df1a9` fix.

This task is to **hand-author the two files directly on `main`** (NOT in the worktree, NOT via autobuild), commit, run pytest + ruff to verify, then mark `TASK-NATS-PH1-004` as `completed` in `.guardkit/features/FEAT-39E1.yaml` so the next autobuild run skips it as `already_completed` and proceeds to Wave 5.

## Implementation Spec (from Prior-Run Evidence)

The seven acceptance criteria with implementation rationale are preserved at [.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-004/player_turn_1.json:46-203](../../../.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-004/player_turn_1.json) (see also `task_work_results.json:132-203` for the same content). Key constructs the prior implementation used:

1. **AC-001 (Bug #2 alias resolution)**: in `CommandRouter._dispatch_command`, do `resolved_command = self.tool_to_command.get(command, command)` *before* the `_command_map` lookup. Pull the alias map from `get_role('tutor').tool_to_command` (the role registry's single source of truth).
2. **AC-002 (canonical passthrough)**: same `.get(c, c)` form provides passthrough — canonical names are absent from `tool_to_command` so they fall through unchanged. AC-001 and AC-002 hold simultaneously without duplicating dispatch keys.
3. **AC-003 (Bug #1 dual-publish)**: in `_publish_result`, when `reply_to` is set, `await client.publish_raw(reply_to, ResultPayload.model_dump_json().encode())` (raw bytes, not envelope-wrapped) AND `await client.publish(canonical_subject, envelope)`. Resolve canonical subject via `Topics.resolve(Topics.Agents.RESULT, agent_id='gcse-tutor')` → `agents.result.gcse-tutor`.
4. **AC-004 (reply_to=None canonical-only)**: when `reply_to is None`, skip the raw-publish entirely; only publish the canonical envelope.
5. **AC-005 (unknown command)**: `_dispatch_command` raises `UnsupportedCommandError(KeyError)` for unknown command names. `on_command` catches it and synthesises `ResultPayload(success=False, result={'error': ..., 'error_type': 'UnsupportedCommandError'})`. Error string includes the sorted list of supported command names: `start_session, tutor_turn, session_status, end_session`.
6. **AC-006 (handler exception)**: `_safe_invoke` wraps the underlying MCP method call in try/except; any exception becomes `ResultPayload(success=False, result={'error': str(exc), 'error_type': type(exc).__name__})`. Original traceback goes to `logger.exception`. Does NOT propagate past `on_command`.
7. **AC-007 (lint clean)**: `ruff check src/study_tutor/adapters/command_router.py tests/unit/adapters/test_command_router.py` passes. Both files use `from __future__ import annotations`, type hints on every public function, module-level `__all__`, and `logger = logging.getLogger(__name__)`.

## Test Spec (from prior-run evidence)

Author `tests/unit/adapters/test_command_router.py` with these named tests (signatures from prior-run's preserved test file):

- `test_on_command_alias_resolves_tutor_start_session` (AC-001): send `CommandPayload(command='tutor_start_session', ...)`, assert `mcp_adapter.tutor_start_session` is awaited once with `student_id='lilymay'`, no other handler fires.
- `test_on_command_canonical_command_passes_through` (AC-002): send `command='start_session'`, assert same call lands.
- `test_publish_result_with_reply_to_publishes_both` (AC-003): assert `client.publish_raw` and `client.publish` are both awaited; raw body is `ResultPayload`-parseable.
- `test_publish_result_without_reply_to_only_canonical` (AC-004): assert `publish_raw` NOT awaited; `publish` awaited exactly once on `agents.result.gcse-tutor`.
- `test_dispatch_command_raises_unsupported_command_error` (AC-005, inner): raises `UnsupportedCommandError` with sorted supported list.
- `test_on_command_unknown_command_returns_error_result` (AC-005, outer): `on_command(command='bogus_command')` does not propagate; `ResultPayload.success=False`; error string contains `bogus_command` AND every canonical command name.
- `test_on_command_handler_exception_caught` (AC-006): wire `mcp_adapter.tutor_start_session.side_effect = RuntimeError('boom')`; `on_command` does not raise; published `ResultPayload.success=False`, `'boom'` in error, `error_type='RuntimeError'`.
- `test_dispatch_command_raises_unsupported_command_error` (AC-005 sibling): inner contract test.
- `test_on_command_with_reply_to_dual_publishes_aliased_command`: combines AC-001 + AC-003 (alias resolution + dual publish).

The prior run pytest output confirmed `9 passed in 0.14s` — 9 tests is the reference count for completion.

## Acceptance Criteria

- [ ] `src/study_tutor/adapters/command_router.py` exists on `main` with the 7 AC behaviours above; `git ls-files src/study_tutor/adapters/command_router.py` returns the path (NOT silently gitignored).
- [ ] `tests/unit/adapters/test_command_router.py` exists on `main` with 9 named tests; `pytest tests/unit/adapters/test_command_router.py` shows `9 passed`.
- [ ] `ruff check src/study_tutor/adapters/command_router.py tests/unit/adapters/test_command_router.py` exits 0.
- [ ] `.guardkit/features/FEAT-39E1.yaml` has `TASK-NATS-PH1-004` flipped to `status: completed` (the same edit the auto-resume orchestrator does on `already_completed` skips, applied manually).
- [ ] Commit message references TASK-REV-F30A and TASK-NATS-FIX-004 in the body so future grep-archaeology can trace the recovery action.

## Implementation Notes

- **Mode = manual** by design. Do NOT route this through `/task-work` or `guardkit autobuild task TASK-NATS-FIX-004`. The autobuild was just shown to fail at this exact path; running it again on the same worktree will fail again until TASK-NATS-FIX-005 lands.
- The `nats-core` package layout (which CommandRouter constructs against) is at `~/Projects/appmilla_github/nats-core` (uv-source symlinked into the worktree at runtime). Reference but do not modify.
- Two regression guards (Bug #1 dual-publish, Bug #2 alias resolution) are explicitly named in the original task spec; the test pair must remain green even if the dispatch logic is refactored later.
- After landing this task, the worktree's empty `src/study_tutor/adapters/` and `tests/unit/adapters/` directories will still be empty until TASK-NATS-FIX-005 deletes the worktree. That's fine — the autobuild copies tracked files from `main` into the new worktree.
