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
status: in_review
priority: high
created: 2026-05-06 01:00:00+00:00
updated: 2026-05-06 01:00:00+00:00
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
autobuild_state:
  current_turn: 3
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-6CC5
  base_branch: main
  started_at: '2026-05-06T12:03:04.715725'
  last_updated: '2026-05-06T12:41:45.061190'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- BDD oracle: 1 scenario(s) failed during pytest-bdd execution. Implementation
      does not satisfy the Gherkin specification.'
    timestamp: '2026-05-06T12:03:04.715725'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: "- Tests failed due to source-file contention with peer task(s) in this\
      \ parallel wave (wave_size=4). Both this task and the peer(s) below edited the\
      \ same source file(s); the resulting shared-branch state is inconsistent and\
      \ an isolation-snapshot retry cannot recover it. Resolve the conflict on the\
      \ next turn \u2014 by then the peer(s) will have completed and the wave is effectively\
      \ serialised.\nOverlapping files by peer:\n  - TASK-LCA-001: .claude/task-plans/TASK-LCA-001-implementation-plan.md,\
      \ .claude/task-plans/TASK-LCA-002-implementation-plan.md, .claude/task-plans/TASK-LCA-003-implementation-plan.md,\
      \ .claude/task-plans/TASK-LCA-004-implementation-plan.md, .env.example, .guardkit/autobuild/TASK-LCA-001/checkpoints.json,\
      \ .guardkit/autobuild/TASK-LCA-001/coach_feedback_for_turn_2.json, .guardkit/autobuild/TASK-LCA-001/coach_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-001/phase_4_summary.json, .guardkit/autobuild/TASK-LCA-001/player_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-001/player_turn_2.json, .guardkit/autobuild/TASK-LCA-001/specialist_results.json,\
      \ .guardkit/autobuild/TASK-LCA-001/task_work_results.json, .guardkit/autobuild/TASK-LCA-001/turn_context.json,\
      \ .guardkit/autobuild/TASK-LCA-001/turn_state_turn_1.json, .guardkit/autobuild/TASK-LCA-002/checkpoints.json,\
      \ .guardkit/autobuild/TASK-LCA-002/coach_feedback_for_turn_2.json, .guardkit/autobuild/TASK-LCA-002/coach_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-002/phase_4_summary.json, .guardkit/autobuild/TASK-LCA-002/player_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-002/specialist_results.json, .guardkit/autobuild/TASK-LCA-002/task_work_results.json,\
      \ .guardkit/autobuild/TASK-LCA-002/turn_context.json, .guardkit/autobuild/TASK-LCA-002/turn_state_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-003/checkpoints.json, .guardkit/autobuild/TASK-LCA-003/coach_feedback_for_turn_2.json,\
      \ .guardkit/autobuild/TASK-LCA-003/coach_turn_1.json, .guardkit/autobuild/TASK-LCA-003/phase_4_summary.json,\
      \ .guardkit/autobuild/TASK-LCA-003/player_turn_1.json, .guardkit/autobuild/TASK-LCA-003/player_turn_2.json,\
      \ .guardkit/autobuild/TASK-LCA-003/specialist_results.json, .guardkit/autobuild/TASK-LCA-003/task_work_results.json,\
      \ .guardkit/autobuild/TASK-LCA-003/turn_context.json, .guardkit/autobuild/TASK-LCA-003/turn_state_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-004/checkpoints.json, .guardkit/autobuild/TASK-LCA-004/coach_feedback_for_turn_2.json,\
      \ .guardkit/autobuild/TASK-LCA-004/coach_turn_1.json, .guardkit/autobuild/TASK-LCA-004/coach_turn_2.json,\
      \ .guardkit/autobuild/TASK-LCA-004/phase_4_summary.json, .guardkit/autobuild/TASK-LCA-004/player_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-004/player_turn_2.json, .guardkit/autobuild/TASK-LCA-004/specialist_results.json,\
      \ .guardkit/autobuild/TASK-LCA-004/task_work_results.json, .guardkit/autobuild/TASK-LCA-004/turn_context.json,\
      \ .guardkit/autobuild/TASK-LCA-004/turn_state_turn_1.json, .guardkit/autobuild/TASK-LCA-004/turn_state_turn_2.json,\
      \ .guardkit/bdd/TASK-LCA-001_junit.xml, .guardkit/bdd/TASK-LCA-002_junit.xml,\
      \ .guardkit/bdd/TASK-LCA-003_junit.xml, .guardkit/bdd/TASK-LCA-004_junit.xml,\
      \ .guardkit/bootstrap_state.json, features/mcp-llm-player-coach-adapters/test_mcp_llm_player_coach_adapters.py,\
      \ pyproject.toml, roles/tutor/prompts/coach.md, roles/tutor/role.yaml, src/study_tutor/llm/client.py,\
      \ src/study_tutor/mcp/adapter.py, src/study_tutor/roles/loader.py, tasks/backlog/TASK-LCA-005-cli-factory-closure-and-integration-smokes.md,\
      \ tasks/design_approved/TASK-LCA-001-llm-player-adapter.md, tasks/design_approved/TASK-LCA-002-llm-coach-adapter.md,\
      \ tasks/design_approved/TASK-LCA-003-session-state-dataclass.md, tasks/design_approved/TASK-LCA-004-coach-model-env-and-boot-smoke.md,\
      \ tests/unit/llm/test_client.py, tests/unit/mcp/test_adapter.py, tests/unit/roles/__init__.py,\
      \ tests/unit/roles/test_loader.py\n  - TASK-LCA-002: .claude/task-plans/TASK-LCA-001-implementation-plan.md,\
      \ .claude/task-plans/TASK-LCA-002-implementation-plan.md, .claude/task-plans/TASK-LCA-003-implementation-plan.md,\
      \ .claude/task-plans/TASK-LCA-004-implementation-plan.md, .env.example, .guardkit/autobuild/TASK-LCA-001/checkpoints.json,\
      \ .guardkit/autobuild/TASK-LCA-001/coach_feedback_for_turn_2.json, .guardkit/autobuild/TASK-LCA-001/coach_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-001/phase_4_summary.json, .guardkit/autobuild/TASK-LCA-001/player_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-001/player_turn_2.json, .guardkit/autobuild/TASK-LCA-001/specialist_results.json,\
      \ .guardkit/autobuild/TASK-LCA-001/task_work_results.json, .guardkit/autobuild/TASK-LCA-001/turn_context.json,\
      \ .guardkit/autobuild/TASK-LCA-001/turn_state_turn_1.json, .guardkit/autobuild/TASK-LCA-002/checkpoints.json,\
      \ .guardkit/autobuild/TASK-LCA-002/coach_feedback_for_turn_2.json, .guardkit/autobuild/TASK-LCA-002/coach_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-002/phase_4_summary.json, .guardkit/autobuild/TASK-LCA-002/player_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-002/specialist_results.json, .guardkit/autobuild/TASK-LCA-002/task_work_results.json,\
      \ .guardkit/autobuild/TASK-LCA-002/turn_context.json, .guardkit/autobuild/TASK-LCA-002/turn_state_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-003/checkpoints.json, .guardkit/autobuild/TASK-LCA-003/coach_feedback_for_turn_2.json,\
      \ .guardkit/autobuild/TASK-LCA-003/coach_turn_1.json, .guardkit/autobuild/TASK-LCA-003/phase_4_summary.json,\
      \ .guardkit/autobuild/TASK-LCA-003/player_turn_1.json, .guardkit/autobuild/TASK-LCA-003/player_turn_2.json,\
      \ .guardkit/autobuild/TASK-LCA-003/specialist_results.json, .guardkit/autobuild/TASK-LCA-003/task_work_results.json,\
      \ .guardkit/autobuild/TASK-LCA-003/turn_context.json, .guardkit/autobuild/TASK-LCA-003/turn_state_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-004/checkpoints.json, .guardkit/autobuild/TASK-LCA-004/coach_feedback_for_turn_2.json,\
      \ .guardkit/autobuild/TASK-LCA-004/coach_turn_1.json, .guardkit/autobuild/TASK-LCA-004/coach_turn_2.json,\
      \ .guardkit/autobuild/TASK-LCA-004/phase_4_summary.json, .guardkit/autobuild/TASK-LCA-004/player_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-004/player_turn_2.json, .guardkit/autobuild/TASK-LCA-004/specialist_results.json,\
      \ .guardkit/autobuild/TASK-LCA-004/task_work_results.json, .guardkit/autobuild/TASK-LCA-004/turn_context.json,\
      \ .guardkit/autobuild/TASK-LCA-004/turn_state_turn_1.json, .guardkit/autobuild/TASK-LCA-004/turn_state_turn_2.json,\
      \ .guardkit/bdd/TASK-LCA-001_junit.xml, .guardkit/bdd/TASK-LCA-002_junit.xml,\
      \ .guardkit/bdd/TASK-LCA-003_junit.xml, .guardkit/bdd/TASK-LCA-004_junit.xml,\
      \ .guardkit/bootstrap_state.json, features/mcp-llm-player-coach-adapters/test_mcp_llm_player_coach_adapters.py,\
      \ pyproject.toml, roles/tutor/prompts/coach.md, roles/tutor/role.yaml, src/study_tutor/llm/client.py,\
      \ src/study_tutor/mcp/adapter.py, src/study_tutor/roles/loader.py, tasks/backlog/TASK-LCA-005-cli-factory-closure-and-integration-smokes.md,\
      \ tasks/design_approved/TASK-LCA-001-llm-player-adapter.md, tasks/design_approved/TASK-LCA-002-llm-coach-adapter.md,\
      \ tasks/design_approved/TASK-LCA-003-session-state-dataclass.md, tasks/design_approved/TASK-LCA-004-coach-model-env-and-boot-smoke.md,\
      \ tests/unit/llm/test_client.py, tests/unit/mcp/test_adapter.py, tests/unit/roles/__init__.py,\
      \ tests/unit/roles/test_loader.py\n  - TASK-LCA-004: .claude/task-plans/TASK-LCA-001-implementation-plan.md,\
      \ .claude/task-plans/TASK-LCA-002-implementation-plan.md, .claude/task-plans/TASK-LCA-003-implementation-plan.md,\
      \ .claude/task-plans/TASK-LCA-004-implementation-plan.md, .env.example, .guardkit/autobuild/TASK-LCA-001/checkpoints.json,\
      \ .guardkit/autobuild/TASK-LCA-001/coach_feedback_for_turn_2.json, .guardkit/autobuild/TASK-LCA-001/coach_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-001/phase_4_summary.json, .guardkit/autobuild/TASK-LCA-001/player_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-001/player_turn_2.json, .guardkit/autobuild/TASK-LCA-001/specialist_results.json,\
      \ .guardkit/autobuild/TASK-LCA-001/task_work_results.json, .guardkit/autobuild/TASK-LCA-001/turn_context.json,\
      \ .guardkit/autobuild/TASK-LCA-001/turn_state_turn_1.json, .guardkit/autobuild/TASK-LCA-002/checkpoints.json,\
      \ .guardkit/autobuild/TASK-LCA-002/coach_feedback_for_turn_2.json, .guardkit/autobuild/TASK-LCA-002/coach_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-002/phase_4_summary.json, .guardkit/autobuild/TASK-LCA-002/player_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-002/specialist_results.json, .guardkit/autobuild/TASK-LCA-002/task_work_results.json,\
      \ .guardkit/autobuild/TASK-LCA-002/turn_context.json, .guardkit/autobuild/TASK-LCA-002/turn_state_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-003/checkpoints.json, .guardkit/autobuild/TASK-LCA-003/coach_feedback_for_turn_2.json,\
      \ .guardkit/autobuild/TASK-LCA-003/coach_turn_1.json, .guardkit/autobuild/TASK-LCA-003/phase_4_summary.json,\
      \ .guardkit/autobuild/TASK-LCA-003/player_turn_1.json, .guardkit/autobuild/TASK-LCA-003/player_turn_2.json,\
      \ .guardkit/autobuild/TASK-LCA-003/specialist_results.json, .guardkit/autobuild/TASK-LCA-003/task_work_results.json,\
      \ .guardkit/autobuild/TASK-LCA-003/turn_context.json, .guardkit/autobuild/TASK-LCA-003/turn_state_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-004/checkpoints.json, .guardkit/autobuild/TASK-LCA-004/coach_feedback_for_turn_2.json,\
      \ .guardkit/autobuild/TASK-LCA-004/coach_turn_1.json, .guardkit/autobuild/TASK-LCA-004/coach_turn_2.json,\
      \ .guardkit/autobuild/TASK-LCA-004/phase_4_summary.json, .guardkit/autobuild/TASK-LCA-004/player_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-004/player_turn_2.json, .guardkit/autobuild/TASK-LCA-004/specialist_results.json,\
      \ .guardkit/autobuild/TASK-LCA-004/task_work_results.json, .guardkit/autobuild/TASK-LCA-004/turn_context.json,\
      \ .guardkit/autobuild/TASK-LCA-004/turn_state_turn_1.json, .guardkit/autobuild/TASK-LCA-004/turn_state_turn_2.json,\
      \ .guardkit/bdd/TASK-LCA-001_junit.xml, .guardkit/bdd/TASK-LCA-002_junit.xml,\
      \ .guardkit/bdd/TASK-LCA-003_junit.xml, .guardkit/bdd/TASK-LCA-004_junit.xml,\
      \ .guardkit/bootstrap_state.json, features/mcp-llm-player-coach-adapters/test_mcp_llm_player_coach_adapters.py,\
      \ pyproject.toml, roles/tutor/prompts/coach.md, roles/tutor/role.yaml, src/study_tutor/llm/client.py,\
      \ src/study_tutor/mcp/adapter.py, src/study_tutor/roles/loader.py, tasks/backlog/TASK-LCA-005-cli-factory-closure-and-integration-smokes.md,\
      \ tasks/design_approved/TASK-LCA-001-llm-player-adapter.md, tasks/design_approved/TASK-LCA-002-llm-coach-adapter.md,\
      \ tasks/design_approved/TASK-LCA-003-session-state-dataclass.md, tasks/design_approved/TASK-LCA-004-coach-model-env-and-boot-smoke.md,\
      \ tests/unit/llm/test_client.py, tests/unit/mcp/test_adapter.py, tests/unit/roles/__init__.py,\
      \ tests/unit/roles/test_loader.py\nTest command: pytest features/mcp-llm-player-coach-adapters/test_mcp_llm_player_coach_adapters.py\
      \ tests/unit/llm/test_client.py tests/unit/mcp/test_adapter.py tests/unit/roles/test_loader.py\
      \ -v --tb=short. Error detail: Error detail:\n____________ test_a_learner_turn_returns_the_phase1_metadata_shape\
      \ _____________\nE   pytest_bdd.exceptions.StepDefinitionNotFoundError: Step\
      \ definition is not found: Given \"the MCP server has booted with a working\
      \ orchestrator_factory\". Line 41 in scenario \"A learner turn returns the Phase-1\
      \ metadata shape\" in the feature \"/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-6CC5/features/mcp-llm-player-coach-adapters/mcp-llm-player-coach-adapter...:\n\
      \  Error detail:\n____________ test_a_learner_turn_returns_the_phase1_metadata_shape\
      \ _____________\nE   pytest_bdd.exceptions.StepDefinitionNotFoundError: Step\
      \ definition is not found: Given \"the MCP server has booted with a working\
      \ orchestrator_factory\". Line 41 in scenario \"A learner turn returns the Phase-1\
      \ metadata shape\" in the feature \"/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-6CC5/features/mcp-llm-player-coach-adapters/mcp-llm-player-coach-adapters.feature\"\
      \nAll traceback entries are hidden. Pass `--full-trace` to see hidden and internal\
      \ frames.\n________ test_each_turn_is_served_by_a_freshlyconstructed_orchestrator\
      \ _________\nE   pytest_bdd.exceptions.StepDefinitionNotFoundError: Step definition\
      \ is not found: Given \"the MCP server has booted with a working orchestrator_factory\"\
      . Line 57 in scenario \"Each turn is served by a freshly-constructed orchestrator\"\
      \ in the feature \"/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guard..."
    timestamp: '2026-05-06T12:15:00.814319'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 3
    decision: approve
    feedback: null
    timestamp: '2026-05-06T12:28:15.125270'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
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
