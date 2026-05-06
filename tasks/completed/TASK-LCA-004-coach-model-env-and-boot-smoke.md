---
id: TASK-LCA-004
title: Add _default_coach_model() helper, AGENT_MODELS__COACH_MODEL env var, and MCPAdapter
  boot smoke check
task_type: feature
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
updated: 2026-05-06 01:00:00+00:00
tags:
- feat-lca
- configuration
- safety-invariant
- phase-1
- boot-time
related:
- TASK-REV-LCA1
- TASK-LCA-001
- TASK-LCA-002
- TASK-LCA-003
- TASK-LCA-005
context_files:
- features/mcp-llm-player-coach-adapters/mcp-llm-player-coach-adapters_summary.md
- docs/research/ideas/llm-player-coach-adapters-brief.md
- src/study_tutor/llm/client.py
- src/study_tutor/mcp/adapter.py
- src/study_tutor/tutoring/coach/factory.py
- .env.example
test_results:
  status: pending
autobuild_state:
  current_turn: 4
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-6CC5
  base_branch: main
  started_at: '2026-05-06T12:03:04.713924'
  last_updated: '2026-05-06T12:44:21.014303'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Advisory (non-blocking): task-work produced a report with 2 of 3\
      \ expected agent invocations. Missing phases: 3 (Implementation). Consider invoking\
      \ these agents via the Task tool to strengthen stack-specific quality:\n- Phase\
      \ 3: `the stack-specific Phase-3 specialist` (Implementation)\n- Not all acceptance\
      \ criteria met:\n  \u2022 AC-LCA-07** when `AGENT_MODELS__COACH_MODEL` is unset\
      \ or empty string, `_default_coach_model()` rais\n  \u2022 AC-LCA-02** when\
      \ boot smoke check is invoked and the factory raises (`OrchestratorConfigurationError\n\
      \  \u2022 AC-LCA-08** when both `AGENT_MODELS__REASONING_MODEL` and `AGENT_MODELS__COACH_MODEL`\
      \ are set to the"
    timestamp: '2026-05-06T12:03:04.713924'
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
    timestamp: '2026-05-06T12:11:51.637965'
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
      \ by peer:\n  - TASK-LCA-001: .claude/task-plans/TASK-LCA-001-implementation-plan.md,\
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
    timestamp: '2026-05-06T12:19:38.835448'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 4
    decision: approve
    feedback: null
    timestamp: '2026-05-06T12:29:15.710171'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

# Task: _default_coach_model() + env var + boot smoke check

## Description

Three closely-related changes that together enforce the D3 two-provider
invariant and the env-var snapshot semantics (ASSUM-LCA-008):

1. **`_default_coach_model()`** — new helper in
   `src/study_tutor/llm/client.py` mirroring `_default_player_model()`
   (lines 47–53). Reads `AGENT_MODELS__COACH_MODEL` from the environment
   at call time. **No fallback default** — unset/empty must raise a clear
   `LLMProviderError` naming the missing env var (per D-COACH-05).
2. **`.env.example` documentation** — add the `AGENT_MODELS__COACH_MODEL=`
   placeholder with an inline comment explaining the D3 invariant and the
   boot-time snapshot semantics (rotation requires server restart).
3. **`MCPAdapter.__init__` boot smoke check** — when
   `orchestrator_factory` is supplied, invoke it once at the end of
   `__init__` and discard the result. This surfaces
   `OrchestratorConfigurationError` / `CoachConfigurationError` /
   `LLMProviderError` at server boot rather than at first user turn.

This is the **producer** for the §4 `_default_coach_model()` integration
contract consumed by TASK-LCA-002.

## Acceptance Criteria

- [ ] `_default_coach_model()` exists in `src/study_tutor/llm/client.py`, signature `() -> str`
- [ ] **AC-LCA-07** when `AGENT_MODELS__COACH_MODEL` is unset or empty string, `_default_coach_model()` raises `LLMProviderError` with a message naming the env var literally (`"AGENT_MODELS__COACH_MODEL"`)
- [ ] When `AGENT_MODELS__COACH_MODEL` is set, `_default_coach_model()` returns the env-var value verbatim (no canonicalisation)
- [ ] `.env.example` includes:
  ```
  AGENT_MODELS__REASONING_MODEL=local       # Player (Phase 0 default)
  AGENT_MODELS__COACH_MODEL=                 # Coach — must differ from REASONING_MODEL (D3 invariant); env-var snapshot at boot, server restart required after rotation
  ```
- [ ] `MCPAdapter.__init__` (`src/study_tutor/mcp/adapter.py:129`) invokes `self._orchestrator_factory()` once at end of `__init__` when `_orchestrator_factory is not None`; the result is discarded
- [ ] **AC-LCA-02** when boot smoke check is invoked and the factory raises (`OrchestratorConfigurationError`, `CoachConfigurationError`, `LLMProviderError`), the exception propagates from `__init__` (i.e. server boot fails fast, before serving begins)
- [ ] **AC-LCA-08** when both `AGENT_MODELS__REASONING_MODEL` and `AGENT_MODELS__COACH_MODEL` are set to the same provider, the factory's call to `validate_coach_config` raises `CoachConfigurationError` whose message names both providers and references the D3 invariant
- [ ] When `_orchestrator_factory is None`, `__init__` behaviour is unchanged (Phase-0 path remains backward-compatible)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

- Unit test in `tests/unit/llm/test_client.py` for `_default_coach_model()`:
  - env var set → returns value
  - env var unset → raises `LLMProviderError` naming the var
  - env var empty string → raises `LLMProviderError` naming the var
- Unit test in `tests/unit/mcp/test_adapter.py` for boot smoke check:
  - factory supplied + factory succeeds → adapter constructs cleanly
  - factory supplied + factory raises `CoachConfigurationError` → `MCPAdapter(...)` raises (boot fails)
  - `_orchestrator_factory=None` → no smoke-check invocation, behaviour unchanged
  - Same-provider scenario via real `validate_coach_config` invocation through a stubbed factory
- Mark scenario class with `@pytest.mark.feat_lca` for smoke gate inclusion

## Implementation Notes

**Pattern to mirror** (`src/study_tutor/llm/client.py:47-53`):

```python
def _default_player_model() -> str:
    """Resolve the player provider name at call time (SR-03)."""
    return os.environ.get("AGENT_MODELS__REASONING_MODEL", "local")
```

**`_default_coach_model()` shape** (note: NO default — must raise if unset):

```python
def _default_coach_model() -> str:
    """Resolve the coach provider name at call time.

    Per D-COACH-05, there is no fallback default — the operator MUST set
    AGENT_MODELS__COACH_MODEL to a provider distinct from the player's
    AGENT_MODELS__REASONING_MODEL (the D3 two-provider invariant is
    enforced at orchestrator factory time via validate_coach_config).
    """
    value = os.environ.get("AGENT_MODELS__COACH_MODEL", "").strip()
    if not value:
        raise LLMProviderError(
            "AGENT_MODELS__COACH_MODEL is not set. "
            "Phase-1 requires the Coach provider to be explicitly configured "
            "and to differ from AGENT_MODELS__REASONING_MODEL (D3 invariant)."
        )
    return value
```

**MCPAdapter `__init__` smoke check addition** (after line 165 in current
adapter.py):

```python
# Boot-time smoke check: invoke factory once and discard the result.
# This surfaces same-provider rejection (D3) and missing env vars
# (AGENT_MODELS__COACH_MODEL) at server boot rather than first user turn.
if self._orchestrator_factory is not None:
    self._orchestrator_factory()  # discarded; smoke-check invocation only
```

**Existing constraints**:
- `validate_coach_config` (`coach/factory.py:326-397`) already enforces the
  D3 invariant — this task does NOT modify it. The smoke check just makes
  sure that validation runs at boot.
- `LLMProviderError` is the existing exception type in `llm/client.py`. Use
  the existing class — do not introduce a new one.
