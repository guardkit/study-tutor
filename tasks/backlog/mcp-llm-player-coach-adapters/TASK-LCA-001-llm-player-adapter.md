---
id: TASK-LCA-001
title: Implement LLMPlayerAdapter (respond + revise) with structured-only revise prompt
task_type: feature
parent_review: TASK-REV-LCA1
feature_id: FEAT-6CC5
feature_slug: mcp-llm-player-coach-adapters
wave: 1
implementation_mode: task-work
complexity: 5
dependencies: []
status: in_review
priority: high
created: 2026-05-06 01:00:00+00:00
updated: 2026-05-06 01:00:00+00:00
tags:
- feat-lca
- tutoring
- player-adapter
- phase-1
related:
- TASK-REV-LCA1
- TASK-LCA-002
- TASK-LCA-003
- TASK-LCA-004
- TASK-LCA-005
context_files:
- features/mcp-llm-player-coach-adapters/mcp-llm-player-coach-adapters_summary.md
- docs/research/ideas/llm-player-coach-adapters-brief.md
- src/study_tutor/tutoring/orchestrator.py
- src/study_tutor/llm/client.py
- tests/smoke/test_tutoring_loop.py
consumer_context:
- task: TASK-LCA-003
  consumes: SessionState
  framework: Python @dataclass(frozen=True)
  driver: stdlib dataclasses
  format_note: SessionState exposes session_id (required), student_id (required),
    text_name (optional), topic (optional), focus_aos (tuple), mode (str). Adapter
    signatures must accept SessionState in place of the previous Any-typed dict and
    access fields via attribute access, not subscript.
test_results:
  status: pending
autobuild_state:
  current_turn: 4
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-6CC5
  base_branch: main
  started_at: '2026-05-06T12:03:04.708139'
  last_updated: '2026-05-06T12:38:20.358420'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Advisory (non-blocking): task-work produced a report with 2 of 3\
      \ expected agent invocations. Missing phases: 3 (Implementation). Consider invoking\
      \ these agents via the Task tool to strengthen stack-specific quality:\n- Phase\
      \ 3: `the stack-specific Phase-3 specialist` (Implementation)\n- Not all acceptance\
      \ criteria met:\n  \u2022 AC-LCA-03** `respond(session_state, learner_message)`\
      \ invokes `LLMClient(provider=_default_player_mo\n  \u2022 Player prompt is\
      \ loaded once at adapter construction via `RoleConfig.load_player_prompt()`\
      \ (existing\n  \u2022 AC-LCA-04** `revise(...)` assembles a deterministic prompt\
      \ that contains:\n  \u2022 Assembled `revise()` prompt contains NO substring\
      \ from `RubricFeedback.suggested_focus` (asserted by\n  \u2022 Assembled `revise()`\
      \ prompt contains NO Coach evidence / verdict / reasoning text (asserted by\
      \ unit \n  (5 more)"
    timestamp: '2026-05-06T12:03:04.708139'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: "- Advisory (non-blocking): task-work produced a report with 2 of 3\
      \ expected agent invocations. Missing phases: 3 (Implementation). Consider invoking\
      \ these agents via the Task tool to strengthen stack-specific quality:\n- Phase\
      \ 3: `the stack-specific Phase-3 specialist` (Implementation)\n- Not all acceptance\
      \ criteria met:\n  \u2022 AC-LCA-03** `respond(session_state, learner_message)`\
      \ invokes `LLMClient(provider=_default_player_mo\n  \u2022 AC-LCA-04** `revise(...)`\
      \ assembles a deterministic prompt that contains:\n  \u2022 `feat_lca` pytest\
      \ marker is registered in `pyproject.toml` (`[tool.pytest.ini_options].markers`)\
      \ wit\n  \u2022 All modified files pass project-configured lint/format checks\
      \ with zero errors"
    timestamp: '2026-05-06T12:13:59.174310'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: "- Advisory (non-blocking): task-work produced a report with 2 of 3\
      \ expected agent invocations. Missing phases: 3 (Implementation). Consider invoking\
      \ these agents via the Task tool to strengthen stack-specific quality:\n- Phase\
      \ 3: `the stack-specific Phase-3 specialist` (Implementation)\n- Tests failed\
      \ due to source-file contention with peer task(s) in this parallel wave (wave_size=4).\
      \ Both this task and the peer(s) below edited the same source file(s); the resulting\
      \ shared-branch state is inconsistent and an isolation-snapshot retry cannot\
      \ recover it. Resolve the conflict on the next turn \u2014 by then the peer(s)\
      \ will have completed and the wave is effectively serialised.\nOverlapping files\
      \ by peer:\n  - TASK-LCA-002: .claude/task-plans/TASK-LCA-001-implementation-plan.md,\
      \ .claude/task-plans/TASK-LCA-002-implementation-plan.md, .claude/task-plans/TASK-LCA-003-implementation-plan.md,\
      \ .claude/task-plans/TASK-LCA-004-implementation-plan.md, .env.example, .guardkit/autobuild/TASK-LCA-001/checkpoints.json,\
      \ .guardkit/autobuild/TASK-LCA-001/coach_feedback_for_turn_2.json, .guardkit/autobuild/TASK-LCA-001/coach_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-001/coach_turn_2.json, .guardkit/autobuild/TASK-LCA-001/phase_4_summary.json,\
      \ .guardkit/autobuild/TASK-LCA-001/player_turn_1.json, .guardkit/autobuild/TASK-LCA-001/player_turn_2.json,\
      \ .guardkit/autobuild/TASK-LCA-001/player_turn_3.json, .guardkit/autobuild/TASK-LCA-001/specialist_results.json,\
      \ .guardkit/autobuild/TASK-LCA-001/task_work_results.json, .guardkit/autobuild/TASK-LCA-001/turn_context.json,\
      \ .guardkit/autobuild/TASK-LCA-001/turn_state_turn_1.json, .guardkit/autobuild/TASK-LCA-001/turn_state_turn_2.json,\
      \ .guardkit/autobuild/TASK-LCA-002/checkpoints.json, .guardkit/autobuild/TASK-LCA-002/coach_feedback_for_turn_2.json,\
      \ .guardkit/autobuild/TASK-LCA-002/coach_turn_1.json, .guardkit/autobuild/TASK-LCA-002/phase_4_summary.json,\
      \ .guardkit/autobuild/TASK-LCA-002/player_turn_1.json, .guardkit/autobuild/TASK-LCA-002/player_turn_2.json,\
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
      \ .guardkit/autobuild/TASK-LCA-004/player_turn_2.json, .guardkit/autobuild/TASK-LCA-004/player_turn_3.json,\
      \ .guardkit/autobuild/TASK-LCA-004/specialist_results.json, .guardkit/autobuild/TASK-LCA-004/task_work_results.json,\
      \ .guardkit/autobuild/TASK-LCA-004/turn_context.json, .guardkit/autobuild/TASK-LCA-004/turn_state_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-004/turn_state_turn_2.json, .guardkit/bdd/TASK-LCA-001_junit.xml,\
      \ .guardkit/bdd/TASK-LCA-002_junit.xml, .guardkit/bdd/TASK-LCA-003_junit.xml,\
      \ .guardkit/bdd/TASK-LCA-004_junit.xml, .guardkit/bootstrap_state.json, features/mcp-llm-player-coach-adapters/test_mcp_llm_player_coach_adapters.py,\
      \ pyproject.toml, roles/tutor/prompts/coach.md, roles/tutor/role.yaml, src/study_tutor/llm/client.py,\
      \ src/study_tutor/mcp/adapter.py, src/study_tutor/roles/loader.py, tasks/backlog/TASK-LCA-005-cli-factory-closure-and-integration-smokes.md,\
      \ tasks/design_approved/TASK-LCA-001-llm-player-adapter.md, tasks/design_approved/TASK-LCA-002-llm-coach-adapter.md,\
      \ tasks/design_approved/TASK-LCA-003-session-state-dataclass.md, tasks/design_approved/TASK-LCA-004-coach-model-env-and-boot-smoke.md,\
      \ tests/unit/llm/test_client.py, tests/unit/mcp/test_adapter.py, tests/unit/roles/__init__.py,\
      \ tests/unit/roles/test_loader.py\n  - TASK-LCA-003: .claude/task-plans/TASK-LCA-001-implementation-plan.md,\
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
      \ .guardkit/autobuild/TASK-LCA-001/coach_turn_2.json, .guardkit/autobuild/TASK-LCA-001/phase_4_summary.json,\
      \ .guardkit/autobuild/TASK-LCA-001/player_turn_1.json, .guardkit/autobuild/TASK-LCA-001/player_turn_2.json,\
      \ .guardkit/autobuild/TASK-LCA-001/specialist_results.json, .guardkit/autobuild/TASK-LCA-001/task_work_results.json,\
      \ .guardkit/autobuild/TASK-LCA-001/turn_context.json, .guardkit/autobuild/TASK-LCA-001/turn_state_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-001/turn_state_turn_2.json, .guardkit/autobuild/TASK-LCA-002/checkpoints.json,\
      \ .guardkit/autobuild/TASK-LCA-002/coach_feedback_for_turn_2.json, .guardkit/autobuild/TASK-LCA-002/coach_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-002/phase_4_summary.json, .guardkit/autobuild/TASK-LCA-002/player_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-002/player_turn_2.json, .guardkit/autobuild/TASK-LCA-002/specialist_results.json,\
      \ .guardkit/autobuild/TASK-LCA-002/task_work_results.json, .guardkit/autobuild/TASK-LCA-002/turn_context.json,\
      \ .guardkit/autobuild/TASK-LCA-002/turn_state_turn_1.json, .guardkit/autobuild/TASK-LCA-003/checkpoints.json,\
      \ .guardkit/autobuild/TASK-LCA-003/coach_feedback_for_turn_2.json, .guardkit/autobuild/TASK-LCA-003/coach_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-003/phase_4_summary.json, .guardkit/autobuild/TASK-LCA-003/player_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-003/player_turn_2.json, .guardkit/autobuild/TASK-LCA-003/specialist_results.json,\
      \ .guardkit/autobuild/TASK-LCA-003/task_work_results.json, .guardkit/autobuild/TASK-LCA-003/turn_context.json,\
      \ .guardkit/autobuild/TASK-LCA-003/turn_state_turn_1.json, .guardkit/autobuild/TASK-LCA-004/checkpoints.json,\
      \ .guardkit/autobuild/TASK-LCA-004/coach_feedback_for_turn_2.json, .guardkit/autobuild/TASK-LCA-004/coach_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-004/coach_turn_2.json, .guardkit/autobuild/TASK-LCA-004/phase_4_summary.json,\
      \ .guardkit/autobuild/TASK-LCA-004/player_turn_1.json, .guardkit/autobuild/TASK-LCA-004/player_turn_2.json,\
      \ .guardkit/autobuild/TASK-LCA-004/player_turn_3.json, .guardkit/autobuild/TASK-LCA-004/specialist_results.json,\
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
    timestamp: '2026-05-06T12:21:49.822735'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 4
    decision: approve
    feedback: null
    timestamp: '2026-05-06T12:29:30.770066'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Task: Implement LLMPlayerAdapter

## Description

Create the production `LLMPlayerAdapter` implementing the `PlayerLike` Protocol
at `src/study_tutor/tutoring/orchestrator.py:123-149`. The adapter wraps
`LLMClient(provider=_default_player_model())` and exposes `respond()` (first
attempt) and `revise()` (subsequent attempts driven by `RubricFeedback`).

**Critical safety invariant (ASSUM-008 / ASSUM-LCA-006):** the `revise()` prompt
must carry **only** structured criterion pointers (`criterion_id` +
`target_score`) — *never* Coach free-text reasoning, evidence strings, or
`suggested_focus`. This is the load-bearing security boundary between Coach and
Player and must be asserted at the prompt-assembly level.

Lives at `src/study_tutor/tutoring/adapters/llm_player_adapter.py` (new file in
new package). The revision prompt template is a deterministic string — no LLM
call to assemble it.

## Acceptance Criteria

- [ ] **AC-LCA-03** `respond(session_state, learner_message)` invokes `LLMClient(provider=_default_player_model()).generate(prompt=learner_message, system=player_prompt)`; returns the result string verbatim
- [ ] Player prompt is loaded once at adapter construction via `RoleConfig.load_player_prompt()` (existing method)
- [ ] **AC-LCA-04** `revise(...)` assembles a deterministic prompt that contains:
  - the original `learner_message`
  - the previous `previous_response`
  - one bullet per `RubricFeedback` entry rendered as `criterion_id: <id>; target_score: <score>` (no other RubricFeedback fields)
- [ ] Assembled `revise()` prompt contains NO substring from `RubricFeedback.suggested_focus` (asserted by unit test)
- [ ] Assembled `revise()` prompt contains NO Coach evidence / verdict / reasoning text (asserted by unit test using a fixture verdict)
- [ ] `LLMPlayerAdapter` implements `PlayerLike` (validated via `isinstance(adapter, PlayerLike)` runtime_checkable assertion)
- [ ] Adapter accepts `SessionState` as the `session_state` parameter (uses attribute access, not dict subscript)
- [ ] Unit tests cover: respond happy path, revise with empty rubric_feedback (degenerate case), revise with multiple criteria, revise security assertion (no free-text leak)
- [ ] `feat_lca` pytest marker is registered in `pyproject.toml` (`[tool.pytest.ini_options].markers`) with description `"feat_lca: tests scoped to the MCP LLM Player and Coach Adapters feature (FEAT-6CC5)"` so other Wave-1 tasks can use the marker without producing PytestUnknownMarkWarning
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

- Unit tests in `tests/unit/tutoring/adapters/test_llm_player_adapter.py`
- Use `unittest.mock.patch` to mock `LLMClient.generate` and assert prompt contents
- Mark scenario class with `@pytest.mark.feat_lca` for smoke gate inclusion
- Cover both `respond()` and `revise()` paths
- Negative test: revise with `RubricFeedback(suggested_focus="DELETE THIS TEXT", ...)` — assert "DELETE THIS TEXT" is NOT in the prompt sent to LLMClient

## Implementation Notes

**Pattern to mirror**: `_default_player_model()` at `src/study_tutor/llm/client.py:47-53` — call-time provider resolution per SR-03.

**Structure**:
```python
# src/study_tutor/tutoring/adapters/llm_player_adapter.py

class LLMPlayerAdapter:
    """Production PlayerLike implementation backed by LLMClient."""

    def __init__(self, role_config: RoleConfig) -> None:
        self._player_prompt = role_config.load_player_prompt()

    async def respond(
        self,
        *,
        session_state: SessionState,
        learner_message: str,
    ) -> str:
        client = LLMClient(provider=_default_player_model())
        return client.generate(prompt=learner_message, system=self._player_prompt)

    async def revise(
        self,
        *,
        session_state: SessionState,
        learner_message: str,
        previous_response: str,
        rubric_feedback: list[RubricFeedback],
    ) -> str:
        prompt = self._assemble_revise_prompt(
            learner_message, previous_response, rubric_feedback,
        )
        client = LLMClient(provider=_default_player_model())
        return client.generate(prompt=prompt, system=self._player_prompt)

    @staticmethod
    def _assemble_revise_prompt(...) -> str:
        # CRITICAL: only criterion_id + target_score from each RubricFeedback.
        # NEVER include suggested_focus or any Coach-side text.
        ...
```

**LLMClient is sync, string-in/string-out**, but `respond`/`revise` are async per the Protocol. Use `asyncio.to_thread(client.generate, ...)` to bridge.

**Reference**: existing inline stubs in `tests/smoke/test_tutoring_loop.py:65-146` show the shape expected.

## Seam Tests

The following seam test validates the integration contract with the producer task. Implement this test to verify the boundary before integration.

```python
"""Seam test: verify SessionState contract from TASK-LCA-003."""
import pytest

from study_tutor.tutoring.adapters.session_state import SessionState
from study_tutor.tutoring.adapters.llm_player_adapter import LLMPlayerAdapter


@pytest.mark.seam
@pytest.mark.integration_contract("SessionState")
def test_session_state_contract_for_player_adapter():
    """Verify SessionState shape matches what LLMPlayerAdapter expects.

    Contract: SessionState is a frozen dataclass with required (session_id,
    student_id) and optional (text_name, topic, focus_aos, mode) fields,
    accessed via attribute access, not subscript.
    Producer: TASK-LCA-003
    """
    state = SessionState(session_id="abc", student_id="lilymay")

    # Contract assertions (derived from §4 format note)
    assert state.session_id == "abc"
    assert state.student_id == "lilymay"
    # Optional fields default per ASSUM-LCA-007
    assert state.text_name is None
    assert state.topic is None
    assert state.focus_aos == ()
    assert state.mode == "tutor"

    # Frozen — must reject mutation
    with pytest.raises((AttributeError, Exception)):
        state.session_id = "different"  # type: ignore[misc]
```
