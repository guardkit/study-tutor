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
status: completed
priority: critical
created: 2026-05-08 00:00:00+00:00
updated: 2026-05-08 00:00:00+00:00
dependencies: []
tags:
- nats
- scaffolding
- phase-1
- foundation
autobuild_state:
  current_turn: 1
  max_turns: 7
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-39E1
  base_branch: main
  started_at: '2026-05-08T20:30:21.926457'
  last_updated: '2026-05-08T20:35:19.002256'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-05-08T20:30:21.926457'
    player_summary: Added nats-core>=0.4 to [project] dependencies and wired the editable
      sibling install via [tool.uv.sources] (nats-core = { path = '../nats-core',
      editable = true }), mirroring specialist-agent's pattern. The TOML comments
      document the PyPI namespace conflict (an unrelated 'nats-core' on PyPI exposes
      the 'nats' module, not 'nats_core') so the next maintainer understands why the
      path source is non-optional. Created src/study_tutor/adapters/__init__.py with
      a docstring describing it as the home for
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
