---
id: TASK-DSP-006
title: Wire plan_session into tutor_start_session and graceful-degradation boundary
task_type: feature
parent_review: TASK-REV-DA72
feature_id: FEAT-PH1-002
wave: 4
implementation_mode: task-work
complexity: 6
dependencies: [TASK-DSP-005]
estimated_minutes: 120
priority: high
tags: [phase-1, planner, mcp, tutor-start-session, latency, graceful-degradation]
consumer_context:
  - task: TASK-DSP-005
    consumes: plan_session
    framework: "MCP server adapter (study_tutor.mcp.tools)"
    driver: "MCP Python SDK over stdio"
    format_note: >
      plan_session is awaited inside asyncio.wait_for with a 2s outer
      guard at the MCP adapter (ASSUM-006, signed off 2026-04-29). The
      inner 5s read timeout in plan_session (ASSUM-007, signed off
      2026-04-29) wraps the FEAT-PH1-001 reads. Outer 2s is the binding
      constraint by design.
---

# Task: Wire plan_session into tutor_start_session and graceful-degradation boundary

## Description

Connect the planner pipeline (TASK-DSP-005) to the MCP `tutor_start_session`
tool. This task owns the entire **graceful-degradation boundary**:
every failure mode in the planner must surface as a baseline-plan
response, never as a propagated exception. `session_id` is minted
*before* `plan_session` is invoked so a planner failure never blocks
session creation.

This task is the binding constraint for both signed-off latency
budgets:
- ASSUM-006 (2s MCP handler budget) — enforced as
  `asyncio.wait_for(plan_session(...), timeout=2.0)` at the adapter.
- ASSUM-007 (5s student-model read timeout) — enforced inside
  `_build_planner_context` for the FEAT-PH1-001 reads.

**Both signed off 2026-04-29 with measured Graphiti read latencies:
search_nodes 0.07s median, search_memory_facts 0.08s median —
0.15s total observed, 1.85s headroom on the outer guard.**

## Scope

- Update `tutor_start_session(student_id, topic_override=None)` MCP
  tool handler:

  ```python
  async def tutor_start_session(student_id: str,
                                topic_override: str | None = None):
      session_id = uuid.uuid4().hex   # always issued
      try:
          plan = await asyncio.wait_for(
              plan_session(student_id, topic_override),
              timeout=PLANNER_HANDLER_BUDGET_SEC,    # 2.0 — ASSUM-006
          )
      except asyncio.TimeoutError:
          log.warning(event="planner_handler_budget_exceeded",
                      student_id=student_id, session_id=session_id)
          plan = _baseline_plan(learner_state_available=False)
      except Exception as exc:
          log.exception(event="planner_internal_error",
                        student_id=student_id, session_id=session_id,
                        error=str(exc))
          plan = _baseline_plan(learner_state_available=False)

      _SESSIONS[session_id] = plan   # in-memory store
      return {
          "session_id": session_id,
          "plan_summary": _plan_summary(plan),
      }
  ```

- Inside `_build_planner_context` (TASK-DSP-005), wrap the
  FEAT-PH1-001 read calls in
  `asyncio.wait_for(timeout=STUDENT_MODEL_READ_TIMEOUT_SEC)` (5.0 —
  ASSUM-007). On timeout: log at the read boundary, return an empty
  `PlannerContext` with `learner_state_available=False`. The pipeline
  in TASK-DSP-005 then immediately routes to `_baseline_plan(False)`.

- Configuration:
  - `PLANNER_HANDLER_BUDGET_SEC` env var, default 2.0
  - `STUDENT_MODEL_READ_TIMEOUT_SEC` env var, default 5.0
  - Both are independently configurable so tests can patch one without
    affecting the other.

- In-memory session store: `_SESSIONS: dict[str, SessionPlan]`. No
  lock required — UUID4 collision probability is effectively zero, and
  `SessionPlan` is `frozen=True`. Document this concurrency reasoning
  at the module docstring.

## Acceptance Criteria

- [ ] `tutor_start_session` always returns `{"session_id": ...,
      "plan_summary": ...}` even when `plan_session(...)` raises
      `RuntimeError`, `asyncio.TimeoutError`, or any other exception
      (`@negative` planner-internal-error scenario).
- [ ] `session_id` is minted **before** `plan_session` is awaited
      (verified by mocking `plan_session` to raise immediately and
      asserting the response still contains `session_id`).
- [ ] MCP response `plan_summary` includes `topic_name` and
      `rule_selected`.
- [ ] In-memory session record at `_SESSIONS[session_id]` holds the
      full `SessionPlan` for subsequent turns
      (`@key-example @mcp-integration`).
- [ ] Outer guard reads from `PLANNER_HANDLER_BUDGET_SEC` env var,
      default 2.0 (`@edge-case @latency` scenario).
- [ ] Inner read timeout reads from `STUDENT_MODEL_READ_TIMEOUT_SEC`
      env var, default 5.0.
- [ ] **Slow-read scenario**: when `_build_planner_context` sleeps for
      4 seconds, `tutor_start_session` returns within 2.1 seconds with
      `rule_selected="baseline"`, `learner_state_available=False`, and
      the slow read is abandoned without blocking the response
      (`@edge-case @latency`).
- [ ] **Concurrent scenario**: two concurrent invocations for the same
      learner produce two distinct `session_id`s, each holding its own
      `SessionPlan`; neither overwrites the other
      (`@edge-case @concurrency`).
- [ ] **Async post-write scenario (TASK-REV-DA72 §5 Gap 2)**: when a
      fire-and-forget session-completion write is in-flight, a new
      `tutor_start_session` invocation returns within 2.1 seconds and
      does not block waiting for the dispatched write
      (`@edge-case @concurrency @async`).
- [ ] **Unknown learner**: `tutor_start_session` for an unseeded
      learner returns a plan with `learner_state_available=False` and
      no exception propagates (`@negative` unknown-learner scenario).
- [ ] All modified files pass project-configured lint/format checks
      with zero errors.

## Seam Tests

The following seam test validates the integration contract with
TASK-DSP-005 (the producer). Implement this test to verify the boundary
before the MCP adapter ships.

```python
"""Seam test: verify plan_session contract from TASK-DSP-005."""
import asyncio
import inspect

import pytest

from study_tutor.planner.pipeline import plan_session


@pytest.mark.seam
@pytest.mark.integration_contract("plan_session")
def test_plan_session_signature_and_async():
    """Verify plan_session is awaitable and accepts (student_id, override).

    Contract (TASK-REV-DA72 §3): plan_session is async, takes
    student_id: str and topic_override: str | None, and returns a
    SessionPlan. The MCP adapter wraps it in asyncio.wait_for with a
    2s outer guard.
    """
    sig = inspect.signature(plan_session)
    params = list(sig.parameters)

    assert "student_id" in params, \
        "plan_session must accept student_id"
    assert "topic_override" in params, \
        "plan_session must accept topic_override"
    assert asyncio.iscoroutinefunction(plan_session), \
        "plan_session must be async (the adapter wraps it in await)"
```

## Implementation Notes

- Place adapter changes in `src/study_tutor/mcp/tools.py` (or wherever
  `tutor_start_session` currently lives — confirm by reading the
  Phase 0 implementation).
- The `_SESSIONS` dict is shared with `tutor_session_end` and
  `tutor_turn` — make sure those still work against the new
  `SessionPlan` shape (or write a compatibility adapter for Phase 0
  callers if they were using the older shape).
- Document the **intentional inversion** in the module docstring:
  "The 2s outer guard is always the binding constraint in the default
  configuration; the 5s inner read timeout fires first only when
  PLANNER_HANDLER_BUDGET_SEC is enlarged for testing."
- All log lines at the boundary use structured logging
  (`event=`, `student_id=`, `session_id=`) — no f-strings into a
  single message.
