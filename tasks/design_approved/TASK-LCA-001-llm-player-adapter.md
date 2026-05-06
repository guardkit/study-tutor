---
complexity: 5
consumer_context:
- consumes: SessionState
  driver: stdlib dataclasses
  format_note: SessionState exposes session_id (required), student_id (required),
    text_name (optional), topic (optional), focus_aos (tuple), mode (str). Adapter
    signatures must accept SessionState in place of the previous Any-typed dict and
    access fields via attribute access, not subscript.
  framework: Python @dataclass(frozen=True)
  task: TASK-LCA-003
context_files:
- features/mcp-llm-player-coach-adapters/mcp-llm-player-coach-adapters_summary.md
- docs/research/ideas/llm-player-coach-adapters-brief.md
- src/study_tutor/tutoring/orchestrator.py
- src/study_tutor/llm/client.py
- tests/smoke/test_tutoring_loop.py
created: 2026-05-06 01:00:00+00:00
dependencies: []
feature_id: FEAT-6CC5
feature_slug: mcp-llm-player-coach-adapters
id: TASK-LCA-001
implementation_mode: task-work
parent_review: TASK-REV-LCA1
priority: high
related:
- TASK-REV-LCA1
- TASK-LCA-002
- TASK-LCA-003
- TASK-LCA-004
- TASK-LCA-005
status: design_approved
tags:
- feat-lca
- tutoring
- player-adapter
- phase-1
task_type: feature
test_results:
  status: pending
title: Implement LLMPlayerAdapter (respond + revise) with structured-only revise prompt
updated: 2026-05-06 01:00:00+00:00
wave: 1
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