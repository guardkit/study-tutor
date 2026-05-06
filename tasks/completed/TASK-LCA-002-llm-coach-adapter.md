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
updated: 2026-05-06 15:00:00+00:00
completed: 2026-05-06 15:00:00+00:00
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
  status: passed
  unit_total: 70
  unit_passed: 70
  unit_failed: 0
  scoped_test_paths:
  - tests/unit/tutoring/adapters/test_llm_coach_adapter.py
  - tests/unit/tutoring/coach/test_rubric.py
  - tests/unit/roles/test_loader.py
  notes: "All 70 scoped tests pass; full unit suite 830 passing with 3 pre-existing failures unrelated to this task (graphiti_client_wiring sentinel test; mcp/stdio_discipline; planner mypy strict — confirmed via `git stash` to fail on main without these changes)."
previous_state: in_review
state_transition_reason: "Completed 2026-05-06 via /task-complete: implementation merged through /task-work (architectural review 91/100; code review APPROVED). Created src/study_tutor/tutoring/adapters/llm_coach_adapter.py and tests/unit/tutoring/adapters/test_llm_coach_adapter.py; added `_drop_unknown_criteria` filter to parse_coach_output (rubric.py) per ASSUM-LCA-005; re-exported LLMCoachAdapter from the adapters package. coach.md, RoleConfig.load_coach_prompt, role.yaml wiring, parse_coach_output, _default_coach_model, and CoachLike Protocol were already in place from the prior FEAT-6CC5 partial autobuild."
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
