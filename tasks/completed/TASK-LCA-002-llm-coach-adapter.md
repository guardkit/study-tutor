---
id: TASK-LCA-002
title: Implement LLMCoachAdapter (Path C hybrid) + coach.md prompt asset + JSON parsing
task_type: feature
parent_review: TASK-REV-LCA1
feature_id: FEAT-6CC5
feature_slug: mcp-llm-player-coach-adapters
wave: 1
implementation_mode: task-work
complexity: 6
dependencies: []
status: completed
priority: high
created: 2026-05-06 01:00:00+00:00
updated: 2026-05-06 01:00:00+00:00
tags:
- feat-lca
- tutoring
- coach-adapter
- phase-1
- prompt-engineering
related:
- TASK-REV-LCA1
- TASK-LCA-001
- TASK-LCA-003
- TASK-LCA-004
- TASK-LCA-005
context_files:
- features/mcp-llm-player-coach-adapters/mcp-llm-player-coach-adapters_summary.md
- docs/research/ideas/llm-player-coach-adapters-brief.md
- src/study_tutor/tutoring/orchestrator.py
- src/study_tutor/tutoring/coach/rubric.py
- src/study_tutor/tutoring/coach/factory.py
- src/study_tutor/llm/client.py
- roles/tutor/prompts/player.md
- roles/tutor/role.yaml
consumer_context:
- task: TASK-LCA-003
  consumes: SessionState
  framework: Python @dataclass(frozen=True)
  driver: stdlib dataclasses
  format_note: SessionState exposes session_id (required), student_id (required),
    text_name (optional), topic (optional), focus_aos (tuple), mode (str). Adapter
    signature must accept SessionState; topic and text_name are used to ground the
    Coach prompt.
- task: TASK-LCA-004
  consumes: AGENT_MODELS__COACH_MODEL
  framework: study_tutor.llm.client.LLMClient (sync, string-in/string-out)
  driver: _default_coach_model()
  format_note: _default_coach_model() returns a provider-name string (e.g. 'bedrock',
    'anthropic', 'openai') accepted by LLMClient(provider=...). Raises LLMProviderError
    naming AGENT_MODELS__COACH_MODEL if the env var is unset/empty. Adapter must call
    _default_coach_model() at evaluate() time (call-time resolution per SR-03), not
    at construction time.
test_results:
  status: pending
autobuild_state:
  current_turn: 4
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-6CC5
  base_branch: main
  started_at: '2026-05-06T12:03:04.715237'
  last_updated: '2026-05-06T12:45:11.228409'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Advisory (non-blocking): task-work produced a report with 2 of 3\
      \ expected agent invocations. Missing phases: 3 (Implementation). Consider invoking\
      \ these agents via the Task tool to strengthen stack-specific quality:\n- Phase\
      \ 3: `the stack-specific Phase-3 specialist` (Implementation)\n- Not all acceptance\
      \ criteria met:\n  \u2022 AC-LCA-05** `evaluate(session_state, learner_message,\
      \ player_response)` invokes `LLMClient(provider=\n  \u2022 LLM output is passed\
      \ to `parse_coach_output(raw)`; returned `CoachVerdict` is fully-shaped (decision\n\
      \  \u2022 AC-LCA-06** when LLM returns non-JSON output, `MalformedCoachOutputError`\
      \ is raised (via `parse_coac\n  \u2022 `roles/tutor/prompts/coach.md` exists\
      \ with <300 words and:\n  \u2022 ASSUM-LCA-005** `parse_coach_output` test suite\
      \ includes a discard-extra-criteria case asserting tha\n  (4 more)"
    timestamp: '2026-05-06T12:03:04.715237'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
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
      \ by peer:\n  - TASK-LCA-001: .claude/task-plans/TASK-LCA-001-implementation-plan.md,\
      \ .claude/task-plans/TASK-LCA-002-implementation-plan.md, .claude/task-plans/TASK-LCA-003-implementation-plan.md,\
      \ .claude/task-plans/TASK-LCA-004-implementation-plan.md, .env.example, .guardkit/autobuild/TASK-LCA-001/checkpoints.json,\
      \ .guardkit/autobuild/TASK-LCA-001/coach_feedback_for_turn_2.json, .guardkit/autobuild/TASK-LCA-001/coach_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-001/phase_4_summary.json, .guardkit/autobuild/TASK-LCA-001/player_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-001/player_turn_2.json, .guardkit/autobuild/TASK-LCA-001/specialist_results.json,\
      \ .guardkit/autobuild/TASK-LCA-001/task_work_results.json, .guardkit/autobuild/TASK-LCA-001/turn_context.json,\
      \ .guardkit/autobuild/TASK-LCA-001/turn_state_turn_1.json, .guardkit/autobuild/TASK-LCA-002/checkpoints.json,\
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
      \ .guardkit/autobuild/TASK-LCA-001/phase_4_summary.json, .guardkit/autobuild/TASK-LCA-001/player_turn_1.json,\
      \ .guardkit/autobuild/TASK-LCA-001/player_turn_2.json, .guardkit/autobuild/TASK-LCA-001/specialist_results.json,\
      \ .guardkit/autobuild/TASK-LCA-001/task_work_results.json, .guardkit/autobuild/TASK-LCA-001/turn_context.json,\
      \ .guardkit/autobuild/TASK-LCA-001/turn_state_turn_1.json, .guardkit/autobuild/TASK-LCA-002/checkpoints.json,\
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
    timestamp: '2026-05-06T12:18:40.079314'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: "- Advisory (non-blocking): task-work produced a report with 2 of 3\
      \ expected agent invocations. Missing phases: 3 (Implementation). Consider invoking\
      \ these agents via the Task tool to strengthen stack-specific quality:\n- Phase\
      \ 3: `the stack-specific Phase-3 specialist` (Implementation)\n- Not all acceptance\
      \ criteria met:\n  \u2022 AC-LCA-05** `evaluate(session_state, learner_message,\
      \ player_response)` invokes `LLMClient(provider=\n  \u2022 LLM output is passed\
      \ to `parse_coach_output(raw)`; returned `CoachVerdict` is fully-shaped (decision\n\
      \  \u2022 AC-LCA-06** when LLM returns non-JSON output, `MalformedCoachOutputError`\
      \ is raised (via `parse_coac\n  \u2022 `roles/tutor/prompts/coach.md` exists\
      \ with <300 words and:\n  \u2022 ASSUM-LCA-005** `parse_coach_output` test suite\
      \ includes a discard-extra-criteria case asserting tha\n  (4 more)"
    timestamp: '2026-05-06T12:26:44.608381'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 4
    decision: approve
    feedback: null
    timestamp: '2026-05-06T12:35:46.773879'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Task: Implement LLMCoachAdapter (Path C hybrid)

## Description

Create the production `LLMCoachAdapter` implementing the `CoachLike` Protocol
at `src/study_tutor/tutoring/orchestrator.py:152-170`. Uses **Path C
(hybrid)**: the LLM emits per-criterion JSON; deterministic post-processing
via `parse_coach_output` (`src/study_tutor/tutoring/coach/rubric.py:597`)
assembles the `CoachVerdict`.

Includes:
- `src/study_tutor/tutoring/adapters/llm_coach_adapter.py` (new file)
- `roles/tutor/prompts/coach.md` (new asset; <300 words for Phase-1 demo)
- `RoleConfig.load_coach_prompt()` method (mirrors `load_player_prompt()`)

The adapter uses `_default_coach_model()` (TASK-LCA-004) for provider
resolution. The two-provider invariant (D3) is enforced at boot in
TASK-LCA-004's smoke check, not here.

## Acceptance Criteria

- [ ] **AC-LCA-05** `evaluate(session_state, learner_message, player_response)` invokes `LLMClient(provider=_default_coach_model()).generate(prompt=..., system=coach_system_prompt)`
- [ ] LLM output is passed to `parse_coach_output(raw)`; returned `CoachVerdict` is fully-shaped (decision, weighted_total, per-criterion scores, rubric_feedback list, misconceptions list)
- [ ] **AC-LCA-06** when LLM returns non-JSON output, `MalformedCoachOutputError` is raised (via `parse_coach_output`); the exception is NOT caught inside the adapter so the orchestrator can route to `decision=fallback`
- [ ] `roles/tutor/prompts/coach.md` exists with <300 words and:
  - Instructs the LLM to score against the six rubric criteria with 0.0–1.0 numeric values + 1-sentence evidence each
  - Forbids free-text rubric_feedback (must be structured per `RubricFeedback` schema)
  - Returns JSON matching the `CoachVerdict` schema (or per-criterion subset; deterministic code completes the verdict)
- [ ] **ASSUM-LCA-005** `parse_coach_output` test suite includes a discard-extra-criteria case asserting that unknown criterion IDs are silently dropped (locks down the policy)
- [ ] `RoleConfig.load_coach_prompt()` exists and returns the contents of `roles/tutor/prompts/coach.md` (mirrors `load_player_prompt()` shape)
- [ ] `LLMCoachAdapter` implements `CoachLike` (validated via `isinstance(adapter, CoachLike)` runtime_checkable assertion)
- [ ] Adapter accepts `SessionState`; uses `session_state.text_name` and `session_state.topic` to ground the Coach prompt (passed via prompt template)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

- Unit tests in `tests/unit/tutoring/adapters/test_llm_coach_adapter.py`
- Mark scenario class with `@pytest.mark.feat_lca` for smoke gate inclusion
- Cover: happy-path verdict shape, malformed-output → `MalformedCoachOutputError`, extra-criteria discard policy (ASSUM-LCA-005)
- Mock `LLMClient.generate` to return canned JSON / non-JSON
- Add a unit test in `tests/unit/roles/test_loader.py` (or similar) for `RoleConfig.load_coach_prompt()` (loads file, returns string, raises if missing)

## Implementation Notes

**Coach prompt template constraints** (per ASSUM-LCA-010):
- Keep <300 words; calibration is Phase-2
- Six rubric criteria: `curriculum_accuracy`, `ao_alignment`, `scaffolding_depth`, `grade_appropriate_language`, `constructive_feedback`, `quote_fidelity`
- Output format: JSON matching the `CoachVerdict` schema (or per-criterion subset; the deterministic post-processor fills in defaults)

**Adapter shape**:
```python
# src/study_tutor/tutoring/adapters/llm_coach_adapter.py

class LLMCoachAdapter:
    """Production CoachLike implementation — Path C hybrid."""

    def __init__(self, role_config: RoleConfig) -> None:
        self._coach_prompt = role_config.load_coach_prompt()

    async def evaluate(
        self,
        *,
        session_state: SessionState,
        learner_message: str,
        player_response: str,
    ) -> CoachVerdict:
        prompt = self._assemble_coach_prompt(
            session_state, learner_message, player_response,
        )
        client = LLMClient(provider=_default_coach_model())
        raw = client.generate(prompt=prompt, system=self._coach_prompt)
        return parse_coach_output(raw)  # raises MalformedCoachOutputError on bad JSON
```

**Don't catch `MalformedCoachOutputError`** inside the adapter — the orchestrator's bounded-revision loop has explicit handling for this exception that routes to `decision=fallback` (the unevaluated-turn fallback path).

**Don't dispatch misconception writes here** — that's a Coach handover responsibility wired in a follow-up subtask (ASSUM-LCA-015).

## Seam Tests

The following seam tests validate the integration contracts with producer tasks. Implement these to verify the boundaries before integration.

```python
"""Seam test: verify SessionState + _default_coach_model() contracts."""
import os
import pytest

from study_tutor.tutoring.adapters.session_state import SessionState
from study_tutor.tutoring.adapters.llm_coach_adapter import LLMCoachAdapter
from study_tutor.llm.client import _default_coach_model
from study_tutor.llm.errors import LLMProviderError


@pytest.mark.seam
@pytest.mark.integration_contract("SessionState")
def test_session_state_contract_for_coach_adapter():
    """Verify SessionState exposes the fields LLMCoachAdapter consumes.

    Contract: text_name and topic are optional and used by Coach prompt
    grounding; default to None.
    Producer: TASK-LCA-003
    """
    state = SessionState(session_id="abc", student_id="lilymay")
    assert hasattr(state, "text_name")
    assert hasattr(state, "topic")
    assert state.text_name is None
    assert state.topic is None


@pytest.mark.seam
@pytest.mark.integration_contract("AGENT_MODELS__COACH_MODEL")
def test_default_coach_model_contract(monkeypatch):
    """Verify _default_coach_model() shape matches LLMCoachAdapter usage.

    Contract: returns a provider name string; raises LLMProviderError
    naming AGENT_MODELS__COACH_MODEL when unset.
    Producer: TASK-LCA-004
    """
    # Set: returns provider string
    monkeypatch.setenv("AGENT_MODELS__COACH_MODEL", "bedrock")
    assert _default_coach_model() == "bedrock"

    # Unset: raises LLMProviderError naming the env var
    monkeypatch.delenv("AGENT_MODELS__COACH_MODEL", raising=False)
    with pytest.raises(LLMProviderError) as exc_info:
        _default_coach_model()
    assert "AGENT_MODELS__COACH_MODEL" in str(exc_info.value)
```
