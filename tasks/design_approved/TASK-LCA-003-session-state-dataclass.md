---
complexity: 4
context_files:
- features/mcp-llm-player-coach-adapters/mcp-llm-player-coach-adapters_summary.md
- docs/research/ideas/llm-player-coach-adapters-brief.md
- src/study_tutor/mcp/adapter.py
- src/study_tutor/tutoring/orchestrator.py
- src/study_tutor/planner/types.py
- src/study_tutor/session/tutor_session.py
created: 2026-05-06 01:00:00+00:00
dependencies: []
feature_id: FEAT-6CC5
feature_slug: mcp-llm-player-coach-adapters
id: TASK-LCA-003
implementation_mode: task-work
parent_review: TASK-REV-LCA1
priority: high
related:
- TASK-REV-LCA1
- TASK-LCA-001
- TASK-LCA-002
- TASK-LCA-005
status: design_approved
tags:
- feat-lca
- tutoring
- data-model
- phase-1
- declarative
task_type: declarative
test_results:
  status: pending
title: Add SessionState typed dataclass and update MCP adapter construction site
updated: 2026-05-06 01:00:00+00:00
wave: 1
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