---
id: TASK-NATS-PH1-001
title: Add nats-core dependency and study_tutor.adapters package skeleton
task_type: scaffolding
parent_review: TASK-REV-NATS-001
feature_id: FEAT-NATS
wave: 1
implementation_mode: direct
complexity: 2
estimated_minutes: 30
status: in_review
priority: critical
created: 2026-05-08 00:00:00+00:00
updated: 2026-05-10 00:00:00+00:00
reopened_reason: 'FEAT-39E1 autobuild approved this task on 2026-05-08 but src/study_tutor/adapters/__init__.py
  was never created in any commit (verified: `git log --all -- src/study_tutor/adapters/__init__.py`
  returns no output). The nats-core dep half of the deliverable did land in pyproject.toml.
  Re-opened on 2026-05-10 alongside PH1-002/004/005/008/009 for autobuild re-run;
  root-cause investigation tracked under TASK-INV-AB1.'
dependencies: []
tags:
- nats
- scaffolding
- phase-1
- foundation
autobuild_state:
  current_turn: 3
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-39E1
  base_branch: main
  started_at: '2026-05-10T16:23:04.366149'
  last_updated: '2026-05-10T16:31:39.274214'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Checkpoint claim audit failed: Player claimed a file that 'git add\
      \ -A' would not stage. Player claimed file pyproject.toml. Path would not be\
      \ staged by 'git add -A' (absent from 'git status --porcelain'). Most common\
      \ cause: an unanchored .gitignore rule silently filters the file. Other causes:\
      \ sparse-checkout, assume-unchanged, pathspec attribute filters, or the file\
      \ is tracked but unchanged (Player claimed modified but didn't). Investigate\
      \ before approving the turn \u2014 most common cause is an unanchored .gitignore\
      \ rule silently filtering the file out of the per-turn checkpoint commit."
    timestamp: '2026-05-10T16:23:04.366149'
    player_summary: "Task was reopened (per the front-matter `reopened_reason`) because\
      \ the original 2026-05-08 autobuild run approved this task without ever committing\
      \ src/study_tutor/adapters/__init__.py \u2014 only the pyproject half of the\
      \ deliverable shipped. On entry to this turn I confirmed: (a) `nats-core>=0.4`\
      \ was already present in [project] dependencies and `[tool.uv.sources]` already\
      \ pinned `path = '../nats-core', editable = true` (AC-001 \u2713 from prior\
      \ run); (b) `from nats_core import Topics, AgentConfig` and "
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: "- Checkpoint claim audit failed: Player claimed a file that 'git add\
      \ -A' would not stage. Player claimed file tests/unit/test_adapters_skeleton.py.\
      \ Path would not be staged by 'git add -A' (absent from 'git status --porcelain').\
      \ Most common cause: an unanchored .gitignore rule silently filters the file.\
      \ Other causes: sparse-checkout, assume-unchanged, pathspec attribute filters,\
      \ or the file is tracked but unchanged (Player claimed modified but didn't).\
      \ Investigate before approving the turn \u2014 most common cause is an unanchored\
      \ .gitignore rule silently filtering the file out of the per-turn checkpoint\
      \ commit."
    timestamp: '2026-05-10T16:26:28.271959'
    player_summary: "Turn 2 addresses Coach feedback only \u2014 no functional code\
      \ change. The Coach's checkpoint claim audit correctly flagged that turn 1's\
      \ report listed `pyproject.toml` in implementation_files for AC-001 and AC-002,\
      \ but `git status --porcelain` had no entry for it (verified in this turn \u2014\
      \ only .guardkit/* files are dirty). Root cause: the `nats-core>=0.4` dep +\
      \ `[tool.uv.sources] nats-core = {path='../nats-core', editable=true}` stanza\
      \ was already in pyproject.toml when this re-opened task started \u2014 "
    player_success: true
    coach_success: true
  - turn: 3
    decision: approve
    feedback: null
    timestamp: '2026-05-10T16:27:54.751754'
    player_summary: "Turn 3 addresses the Coach's repeated checkpoint-claim audit\
      \ failure. Turn 1 was flagged for claiming pyproject.toml (unchanged in that\
      \ turn's diff); turn 2 was flagged for claiming tests/unit/test_adapters_skeleton.py\
      \ as test_file (unchanged in that turn's diff). Both flags were correct: the\
      \ audit checks that any file claimed by the player appears in `git status --porcelain`\
      \ for the per-turn checkpoint. ROOT CAUSE: turns 1 and 2 inherited (rather than\
      \ authored) the wiring \u2014 the nats-core dep wa"
    player_success: true
    coach_success: true
---

# Task: Add nats-core dependency and study_tutor.adapters package skeleton

## Description

Foundation task for the NATS fleet integration. Adds the `nats-core` sibling library as an editable dependency to `study-tutor` and creates the empty `study_tutor.adapters` package that the rest of Phase 1 will populate.

`nats-core` is the canonical contract library: subjects (`Topics`), payload models (`MessageEnvelope`, `CommandPayload`, `ResultPayload`), the NATS client wrapper (`NATSClient`), and the agent config schema (`AgentConfig`). All other Phase 1 tasks import from it.

## Scope

- Add `nats-core` editable dependency to [pyproject.toml](pyproject.toml) (path: `../nats-core` relative to study-tutor repo root, matching specialist-agent's pattern).
- Create empty package `src/study_tutor/adapters/__init__.py`.

## Acceptance criteria

- [ ] `nats-core` appears in `pyproject.toml` `[project] dependencies` (or `[tool.uv.sources]`) as an editable sibling install.
- [ ] `uv sync` (or `pip install -e .`) succeeds without errors.
- [ ] `python -c "from nats_core import Topics, AgentConfig; from nats_core.events._agent import CommandPayload, ResultPayload"` runs without ImportError.
- [ ] `python -c "import study_tutor.adapters"` runs without ImportError.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation notes

Reference: specialist-agent's `pyproject.toml` lines pointing at `../nats-core`. Mirror the same pattern.

## Coach validation

```bash
uv sync && python -c "from nats_core import Topics, AgentConfig; from nats_core.events._agent import CommandPayload, ResultPayload; import study_tutor.adapters; print('OK')"
ruff check src/study_tutor/adapters/ pyproject.toml
```
