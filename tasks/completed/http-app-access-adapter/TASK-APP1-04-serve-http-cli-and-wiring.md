---
id: TASK-APP1-04
title: serve-http CLI subcommand + production wiring (store, tutor loop, events, READY
  health)
task_type: feature
feature_id: FEAT-APP-001
wave: 4
implementation_mode: task-work
complexity: 6
dependencies:
- TASK-APP1-03
parent_feature_spec: features/http-app-access-adapter/http-app-access-adapter_summary.md
status: in_review
autobuild_state:
  current_turn: 3
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-APP-001
  base_branch: main
  started_at: '2026-07-05T09:16:54.746767'
  last_updated: '2026-07-05T09:45:43.982913'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Deterministic honesty record (claim_audit, severity=critical): Player\
      \ claim: Player claimed file /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worttrees/FEAT-APP-001/src/study_tutor/cli/main.py.\
      \ Actual: Path absent from 'git status --porcelain' so 'git add -A' would not\
      \ stage it. Probes: path_exists=False; gitignore_match=no rule matched; tracked=no.\
      \ Most likely cause: the Player claimed work on a file that does not exist on\
      \ disk..\n- Evidence gathering aborted at 'partial_honesty_abort' status before\
      \ independent test verification could run. All test/coverage/BDD oracle fields\
      \ are NULL. This is absent signal, not passing signal. Per Guard 5 (GATHERING-STATUS\
      \ GUARD), cannot approve without complete evidence.: Fix the path discrepancy\
      \ in files_modified (typo: 'worttrees' should be 'worktrees' at index 3 of files_modified\
      \ array). Ensure all claimed files exist on disk at correct paths. Re-run to\
      \ allow complete evidence gathering and independent verification.\n- Path discrepancy:\
      \ Player claimed file '/home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worttrees/FEAT-APP-001/src/study_tutor/cli/main.py'\
      \ with typo (worttrees instead of worktrees). Honesty probe found path_exists=False.\
      \ Files_modified list contains mix of absolute/relative paths and includes this\
      \ non-existent path.: Clean up files_modified and files_authored lists: (1)\
      \ Fix typo: worttrees \u2192 worktrees, (2) Use consistent path format (prefer\
      \ relative paths from repo root), (3) Remove duplicate entries for same files.\n\
      ... and 2 more issues"
    timestamp: '2026-07-05T09:16:54.746767'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: "- Deterministic honesty record (claim_audit_unmodified, severity=should_fix):\
      \ Player claim: Player claimed file src/study_tutor/cli/main.py. Actual: Path\
      \ is tracked in git but 'git status --porcelain' shows no change for it \u2014\
      \ the Player claimed work on a file it did not actually modify this turn. Most\
      \ likely cause: the report writer swept an orchestrator-managed path (e.g. a\
      \ file under .guardkit/autobuild/ or tasks/<state>/) into files_modified. Defence-in-depth\
      \ for the agent_invoker-side filter; this is a warning, not a turn-rejecting\
      \ fabrication..\n- Deterministic honesty record (claim_audit_unmodified, severity=should_fix):\
      \ Player claim: Player claimed file src/study_tutor/http/app.py. Actual: Path\
      \ is tracked in git but 'git status --porcelain' shows no change for it \u2014\
      \ the Player claimed work on a file it did not actually modify this turn. Most\
      \ likely cause: the report writer swept an orchestrator-managed path (e.g. a\
      \ file under .guardkit/autobuild/ or tasks/<state>/) into files_modified. Defence-in-depth\
      \ for the agent_invoker-side filter; this is a warning, not a turn-rejecting\
      \ fabrication..\n- Deterministic honesty record (claim_audit_unmodified, severity=should_fix):\
      \ Player claim: Player claimed file tests/unit/http/test_serve_http.py. Actual:\
      \ Path is tracked in git but 'git status --porcelain' shows no change for it\
      \ \u2014 the Player claimed work on a file it did not actually modify this turn.\
      \ Most likely cause: the report writer swept an orchestrator-managed path (e.g.\
      \ a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n... and 2 more issues"
    timestamp: '2026-07-05T09:30:10.692212'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 3
    decision: approve
    feedback: null
    timestamp: '2026-07-05T09:38:06.555657'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

## Objective

The production wiring: a `serve-http` click subcommand beside `serve` /
`serve-nats` in `src/study_tutor/cli/main.py` that boots the TASK-APP1-03 app
on uvicorn with everything real attached — the Postgres store, the same tutor
loop the MCP adapter uses, and the pinned event emission. This is where the
call-site-drift retro bites hardest: **injected-dependency unit tests are not
production-wiring coverage — test the wired path.**

## Scope

**In scope**
- `serve-http` subcommand: `--port` (default **8100**), `--host`, log-level;
  runs uvicorn over the app factory.
- Store wiring via `knowledge.store.provider` from `STUDY_TUTOR_PG_DSN` —
  **fail fast** when the DSN is missing or the store is unreachable at boot:
  refuse to report ready, exit non-zero, error message names the store as the
  cause. Never serve requests that can only fail.
- Tutor loop: reuse the exact `reply_fn` construction the MCP `serve` path
  uses (shared helper — do NOT re-implement the loop). A tutor-loop failure
  mid-turn returns the server-error envelope; session stays active/resumable.
- Events: wire the EventBus so `session.started` / `session.turn_completed` /
  `session.completed` are emitted with the same pinned payloads as the MCP
  path (contract §8; one vocabulary for all transports).
- `GET /healthz` route + **READY boot smoke**: a test that starts the real
  `serve-http` entrypoint (subprocess or server-in-thread against an ephemeral
  DSN) and asserts the bound port answers `/healthz` — asserting READY, not
  "no crash within N seconds" (SIGTERM-accepted-as-success is the exact retro
  failure).

**Out of scope**
- Reset endpoint + seed (TASK-APP1-05); compose (TASK-APP1-06).
- ANY change to `serve` / `serve-nats` behaviour — this task is additive to
  `cli/main.py`; sweep and leave every existing call site intact (FEAT-SMP-004
  will renovate that file after this feature lands).

## Acceptance Criteria

- [ ] `study-tutor serve-http` boots on :8100 with a valid DSN and answers
      `GET /healthz` (READY smoke green against an ephemeral Postgres)
- [ ] Boot with missing/unreachable store exits non-zero before binding
      traffic, error names the store
- [ ] A `turn` over the wired path uses the shared tutor-loop builder (no
      duplicated LLM/orchestration code — verified by import, not copy)
- [ ] Tutor-loop failure mid-turn: server-error envelope returned, session
      still active and resumable, retried turn succeeds (fake failing reply_fn)
- [ ] The three session events are emitted with the pinned payload shape
- [ ] `serve` and `serve-nats` untouched: existing
      `tests/unit/mcp/test_stdio_discipline.py` and adapter/router suites green
- [ ] All modified files pass project-configured lint/format checks with zero
      errors

## Test Requirements

READY boot smoke (ephemeral DSN; skip when `STUDY_TUTOR_PG_DSN` unset, per the
repo's CI-safe convention); fail-fast boot test; wired-path turn test with a
stubbed reply_fn; event-payload assertions. NEVER point tests at the NAS — the
scope-guard test (no `whitestocks`/`5434` in test config) applies.

## Coach Validation

- `pytest tests/unit/ -q` green + the new boot smoke with DSN exported.
- Verify `cli/main.py` diff is additive (new subcommand + shared-helper
  extraction only; `serve`/`_build_nats_runtime` call sites unchanged).
