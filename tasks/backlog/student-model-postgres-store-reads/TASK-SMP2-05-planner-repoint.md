---
id: TASK-SMP2-05
title: "Repoint the planner read off Graphiti onto the store (load_planner_inputs)"
task_type: feature
feature_id: FEAT-SMP-002
wave: 5
implementation_mode: task-work
complexity: 6
dependencies: [TASK-SMP2-04]
parent_feature_spec: features/student-model-postgres-store-reads/student-model-postgres-store-reads_summary.md
---

## Objective

Repoint the one live production read of the learner model — `planner/pipeline.py:_build_planner_context`
(`src/study_tutor/planner/pipeline.py:335-418`) — from the Graphiti `queries.get_student_state`
onto the store-backed `knowledge.store.reads.load_planner_inputs`, preserving the
graceful-degradation contract and the inner read timeout.

## Current shape → target shape

Today (`pipeline.py:373-407`): `await asyncio.wait_for(get_student_state(client, student_id),
timeout)` returns a `queries.StudentState` of SNAPSHOTS, which are then projected via
`_project_topic_confidence` / `_project_misconception` into domain entities.

Target: `await asyncio.wait_for(load_planner_inputs(student_id), timeout)` returns a
`PlannerInputs(topic_confidences: list[TopicConfidence], misconceptions: list[Misconception],
learner_state_available: bool)` — already DOMAIN entities, ready to pass straight to
`PlannerContext.create`. `load_planner_inputs` (`store/reads.py:85-115`) resolves the wired
store via the provider and already degrades to `PlannerInputs([], [], learner_state_available=False)`
on no-store / read-failure.

## Scope

**In scope**
- `pipeline.py` import: replace `from study_tutor.knowledge.queries import get_student_state`
  (`:45`) with `from study_tutor.knowledge.store.reads import load_planner_inputs`.
- `_build_planner_context`: call `load_planner_inputs(student_id)` inside the existing
  `asyncio.wait_for(..., timeout)` guard. On `asyncio.TimeoutError`, treat as unavailable
  (`PlannerInputs([], [], learner_state_available=False)` semantics) — keep the existing
  timeout log line. Feed `inputs.topic_confidences` / `inputs.misconceptions` /
  `inputs.learner_state_available` straight into `PlannerContext.create` — no snapshot projection.
- Remove the now-dead `_project_topic_confidence` / `_project_misconception` helpers
  (`pipeline.py:283-332`) and their unit tests, since `load_planner_inputs` returns domain
  entities directly. (If any other module imports them, keep them — verify with a grep first.)
- Preserve the inner-timeout env knob (`_student_model_read_timeout_sec()` /
  `_STUDENT_MODEL_READ_TIMEOUT_ENV`) unchanged.
- Add a `store` injection seam for tests if needed (`load_planner_inputs` accepts `store=`);
  prefer wiring the provider (`set_student_store(fake)`) in tests over threading a param.

**Out of scope**
- Deleting the Graphiti read copies from `queries.py` → TASK-SMP2-06 (this task leaves
  `queries.get_student_state` present so the seed script still imports cleanly until SMP2-06).
- The `client` param on `plan_session` / `_build_planner_context`: keep it in the signature for
  backwards-compat (callers pass it), but it is no longer used for the read. Do not remove it here.
- The MCP adapter (`mcp/adapter.py`) calls `plan_session(...)` without a client already; no change needed.

## Acceptance Criteria

- [ ] `_build_planner_context` reads via `load_planner_inputs(student_id)` (store-backed), not
      `queries.get_student_state`; the `queries` read import is gone from `pipeline.py`.
- [ ] With a wired store returning confidences + a recent misconception, the built
      `PlannerContext` carries those entities and `learner_state_available=True`.
- [ ] With no store wired (provider `None`) OR a store read that raises, the context is built with
      empty inputs and `learner_state_available=False` — the planner still produces a baseline plan,
      no exception reaches the caller.
- [ ] A store read that exceeds the inner timeout is caught (`asyncio.TimeoutError`), logged with
      the existing `planner_student_model_read_timeout` event, and degrades to
      `learner_state_available=False`.
- [ ] A reachable store with a known-but-recordless learner yields empty inputs with
      `learner_state_available=True` (seeded-baseline path, NOT the unseeded path) — the
      available/unavailable distinction from `load_planner_inputs` is preserved end-to-end.
- [ ] `_project_topic_confidence` / `_project_misconception` are removed (or retained only if a
      grep proves another importer) and no dead-code references remain.
- [ ] Existing planner behaviour tests pass (rule selection unchanged); the full `pytest tests/unit`
      is green.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
# Planner tests use an injected/ wired fake store — no live DB needed for this task.
.venv/bin/python -m pytest tests/unit/planner/ -v
.venv/bin/python -m pytest tests/unit/mcp/test_adapter_planner_integration.py -v
.venv/bin/python -m pytest tests/unit -q   # full unit suite must stay green (composition guard)
.venv/bin/ruff check src/study_tutor/planner/pipeline.py
```

## Implementation Notes

- `load_planner_inputs` already does the try/except → `available=False` degradation internally;
  the ONLY failure it does not absorb is a `wait_for` timeout (that raises out of `asyncio.wait_for`
  in the caller). Keep the `try/except asyncio.TimeoutError` in `_build_planner_context` and, on
  timeout, set the same empty+unavailable inputs.
- `tests/unit/mcp/test_adapter_planner_integration.py:486-491` monkeypatches
  `pipeline_module.get_student_state` to force a slow read; after the repoint it must monkeypatch
  `pipeline_module.load_planner_inputs` instead (or wire a slow fake store). Update it here.
- `tests/unit/planner/test_pipeline.py:16` imports `StudentState, TopicConfidenceSnapshot` from
  `queries` and builds snapshot fixtures to drive `_build_planner_context` via a client wrapper.
  After the repoint the driver is a wired/ injected store returning domain `TopicConfidence` /
  `Misconception`. Rework these fixtures here (or move to a store-backed harness).
- Do NOT change `PlannerContext.create` — the field names it accepts are unchanged.

## Boundary-test discipline (read the retro)

Do not assert transient state. The repoint's invariant is behavioural ("planner reads through the
store; degrades to baseline when unavailable"), not "queries.get_student_state is still importable"
(TASK-SMP2-06 makes that false). Test the behaviour, not the momentary module surface.

## BDD Scenarios

- The session planner receives store-backed confidences and misconceptions for a seeded learner
- When the store is unreachable, the planner falls back to a baseline plan
- Planning a session no longer consults the retired graph read path
- With no store wired, reads degrade to empty *(planner-side manifestation)*
