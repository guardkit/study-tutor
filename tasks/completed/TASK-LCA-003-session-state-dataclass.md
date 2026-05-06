---
id: TASK-LCA-003
title: Add SessionState typed dataclass and update MCP adapter construction site
task_type: declarative
parent_review: TASK-REV-LCA1
feature_id: FEAT-6CC5
feature_slug: mcp-llm-player-coach-adapters
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
status: completed
priority: high
created: 2026-05-06 01:00:00+00:00
updated: 2026-05-06 14:35:00+00:00
completed: 2026-05-06 14:35:00+00:00
tags:
- feat-lca
- tutoring
- data-model
- phase-1
- declarative
related:
- TASK-REV-LCA1
- TASK-LCA-001
- TASK-LCA-002
- TASK-LCA-005
context_files:
- features/mcp-llm-player-coach-adapters/mcp-llm-player-coach-adapters_summary.md
- docs/research/ideas/llm-player-coach-adapters-brief.md
- src/study_tutor/mcp/adapter.py
- src/study_tutor/tutoring/orchestrator.py
- src/study_tutor/planner/types.py
- src/study_tutor/session/tutor_session.py
test_results:
  status: pending
previous_state: completed
state_transition_reason: 'Re-opened 2026-05-06: prior FEAT-6CC5 autobuild approved
  this task with zero implementation files (see TASK-INV-AB1). The src/study_tutor/tutoring/adapters/
  package and its modules were never written despite coach approval; merged feature
  broke `pytest --collect-only` with `ModuleNotFoundError: study_tutor.tutoring.adapters`.
  Restored to backlog so /feature-build can re-run from a clean slate. The previous
  autobuild_state block was stripped to avoid resume-mode carryover; the historical
  record lives in .guardkit/archive/FEAT-6CC5/feature_state.yaml.'
autobuild_state:
  current_turn: 0
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/TASK-LCA-003
  base_branch: main
  started_at: '2026-05-06T13:56:00.260899'
  last_updated: '2026-05-06T13:56:00.260914'
  turns: []
---

# Task: SessionState typed dataclass + MCP adapter construction site

## Description

Add a typed `SessionState` dataclass at
`src/study_tutor/tutoring/adapters/session_state.py` that becomes the
boundary type threaded through `Player.respond`, `Player.revise`, and
`Coach.evaluate` (replacing today's `session_state: Any` opaque dict).

Update the MCP adapter call site at
`src/study_tutor/mcp/adapter.py:292` so it constructs `SessionState`
from the cached `SessionPlan` + `TutorSession` instead of passing
`{"session_id": session_id}`.

This is the **producer** for the §4 SessionState integration contract
consumed by TASK-LCA-001 and TASK-LCA-002.

## Acceptance Criteria

- [ ] `src/study_tutor/tutoring/adapters/__init__.py` exists (new package marker)
- [ ] `src/study_tutor/tutoring/adapters/session_state.py` defines a frozen dataclass `SessionState` with the following exact field shape:
  - `session_id: str` (required, no default)
  - `student_id: str` (required, no default)
  - `text_name: str | None = None`
  - `topic: str | None = None`
  - `focus_aos: tuple[str, ...] = ()`
  - `mode: str = "tutor"`
- [ ] `SessionState` is `@dataclass(frozen=True)` — mutation raises at runtime
- [ ] **ASSUM-LCA-007** optional fields default to `None` / `()` / `"tutor"` so the MCP adapter construction site can build a minimal `SessionState` even when `SessionPlan.topic_name` / `focus_aos` are absent
- [ ] `MCPAdapter.tutor_turn` (currently `adapter.py:292`) constructs and passes `SessionState(session_id=..., student_id=..., text_name=..., topic=..., focus_aos=..., mode="tutor")` to `orchestrator.run_turn(...)`
- [ ] Construction-site mapping uses cached `SessionPlan` (`self._plan_sessions[session_id]`) for `topic`, `focus_aos`; uses `TutorSession.student_id` for `student_id`; `text_name` reads from `SessionPlan` if present, else `None`
- [ ] Unit test asserts `SessionState` is hashable (consequence of `frozen=True`) and immutable
- [ ] Unit test asserts the MCP adapter passes `SessionState` to `orchestrator.run_turn` (mock the orchestrator factory)
- [ ] Existing `tutor_turn` Phase-0 path (when `_orchestrator_factory is None`) is unchanged
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

- Unit tests in `tests/unit/tutoring/adapters/test_session_state.py`
- Cover: required fields, default values, frozen-mutation rejection, hashability
- Mark with `@pytest.mark.feat_lca` for smoke gate inclusion
- Add an MCP-adapter integration test (or extend existing) asserting the construction-site behaviour: provide a stub `orchestrator_factory`, call `tutor_turn`, assert the orchestrator received a `SessionState` with the expected fields

## Implementation Notes

**Construction-site mapping** (existing `tutor_turn` body around `adapter.py:292`):

```python
# Build SessionState from cached SessionPlan + TutorSession
plan = self._plan_sessions.get(session_id)
session = self._store.get(session_id)  # TutorSession

state = SessionState(
    session_id=session_id,
    student_id=session.student_id,
    text_name=plan.text_name if plan and getattr(plan, "text_name", None) else None,
    topic=plan.topic_name if plan else None,
    focus_aos=tuple(plan.focus_aos) if plan else (),
    mode="tutor",
)

orchestrator = self._orchestrator_factory()
result = await orchestrator.run_turn(
    session_state=state,
    learner_message=learner_message,
)
```

**Cross-feature compatibility**: the `Any`-typed `session_state` in
`PlayerCoachOrchestrator.run_turn` continues to accept `SessionState` without
signature changes — the orchestrator does not dereference fields. Adapters
narrow the type internally.

**Don't add Pydantic** — this is a stdlib `@dataclass`. The project does not
use Pydantic in this layer.

**Frozen immutability** is load-bearing: per-turn factory isolation
(AC-LCA-01) requires that no Coach observation can mutate `SessionState` and
leak into another session.

## Implementation Summary

Re-implemented from clean slate after TASK-INV-AB1 reopened the task
(prior FEAT-6CC5 autobuild had approved it with zero implementation files).
Files added:

- `src/study_tutor/tutoring/adapters/__init__.py` — package marker
- `src/study_tutor/tutoring/adapters/session_state.py` — `@dataclass(frozen=True)`
  with the §4 field shape; optional fields default per ASSUM-LCA-007
- `tests/unit/tutoring/adapters/__init__.py` — test-package marker
- `tests/unit/tutoring/adapters/test_session_state.py` — 9 tests
  (`@pytest.mark.feat_lca`); covers required/optional fields, frozen-mutation
  rejection, hashability, MCP-adapter construction-site behaviour, and the
  Phase-0 backward-compat path

The MCP adapter call site at `src/study_tutor/mcp/adapter.py:285-336` was
already committed in the prior failed merge — only the dataclass it imports
was missing. Adding it resolved `pytest --collect-only`'s
`ModuleNotFoundError: study_tutor.tutoring.adapters` (821 tests now collect
cleanly, vs. previously broken).

## Notes

**Root cause of TASK-INV-AB1 ("approved with zero implementation files")**:
`.gitignore:264` had a bare `adapters/` rule under "Model artefacts"
(intended for LoRA / model adapters). Because the rule is unanchored, it
silently matched both `src/study_tutor/tutoring/adapters/` and
`tests/unit/tutoring/adapters/`. The prior autobuild Player almost
certainly *did* write the package locally — Coach approved it in the
worktree — but `git add` / merge silently dropped the files because git
was ignoring them. Coach's pytest run in the worktree passed because the
files existed *on disk*; the merged branch only got what git tracked.

**Fix landed in this task**: added explicit negation rules to `.gitignore`
for `src/study_tutor/tutoring/adapters/*.py` and
`tests/unit/tutoring/adapters/*.py`, with a comment pointing back to
TASK-INV-AB1. The bare ML-artefact rule is preserved.

**Autobuild bug worth filing separately**: neither Player nor Coach checks
`git check-ignore` on emitted files. Any future autobuild that touches a
gitignored path will repeat this silent-failure mode. Suggested mitigation:
Coach's quality-gate evaluator should assert
`git status --porcelain --untracked-files=all | grep -F <emitted_path>`
returns the file (or fail with `gitignore_silent_drop`).

**Out of scope**: `cli/main.py` still imports `LLMCoachAdapter` /
`LLMPlayerAdapter` (TASK-LCA-001 / TASK-LCA-002, separately reopened) —
those imports still fail at runtime. The 2 `test_stdio_discipline.py`
failures and the 1 `test_mcp_lca_smoke.py` failure observed during this
task's quality-gate run are pre-existing on those dependencies, not
regressions from this change.
