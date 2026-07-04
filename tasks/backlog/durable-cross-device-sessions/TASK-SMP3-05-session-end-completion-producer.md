---
id: TASK-SMP3-05
title: "Session-end completion producer — port Phase1MinimalDeltaPolicy over W2 store reads"
task_type: feature
feature_id: FEAT-SMP-003
wave: 5
implementation_mode: task-work
complexity: 5
dependencies: [TASK-SMP3-04]
parent_feature_spec: features/durable-cross-device-sessions/durable-cross-device-sessions_summary.md
---

## Objective

Build the pure, store-backed producer that turns a completed session into a
`session.service.SessionCompletion` (`service.py:103-117`), replacing the Graphiti-coupled
`record_topic_confidence_update` delta path with W2 store reads. This is a self-contained unit that
TASK-SMP3-06's adapter cutover calls at `end_session`.

## Scope

**In scope**
- **Lift the pure `Phase1MinimalDeltaPolicy`** out of the graph module. `queries.Phase1MinimalDeltaPolicy`
  (`knowledge/queries.py:224-266`) is pure (−3 per misconception on topic; +1 if ≥5 turns and 0 misconceptions;
  clamp[−10,10]; `name="phase1_minimal_policy"`). Move it (and the `ConfidenceDeltaPolicyLike` Protocol) into a
  non-Graphiti home (e.g. `knowledge/confidence_policy.py` or `session/completion.py`) so it survives the
  FEAT-SMP-004 graph teardown. Keep the graph copy importable until SMP-004 (or re-export) — verify no break.
- **`build_session_completion(...)`** (e.g. `session/completion.py`): given the store, `student_id`, `topic`,
  `student_turn_count`, `aos_scaffolded`, and a `misconceptions_per_topic` map (empty this wave, ASSUM-007),
  returns a `SessionCompletion`:
  - `confidence_updates`: for the covered `topic`, read the current percentage via
    `store.get_topic_confidences(student_id)` (W2), apply the policy delta, clamp to `[0,100]`, and emit
    `ConfidenceUpdate(topic_name=topic, percentage=new)`. If the topic has no current confidence row, skip it
    (no baseline to move) — do NOT invent one.
  - `xp_awarded = 0` (ASSUM-006 placeholder).
  - `misconceptions = []` (ASSUM-007 — empty-but-plumbed; the map param is accepted for future wiring).
  - `topic`, `aos_scaffolded` passed through.
- Zero-turn guard belongs to the caller (SMP3-06 passes `completion=None` when `turn_count == 0`, I-T6);
  this producer may assume it is called only for `turn_count > 0`.

**Out of scope**
- Calling `record_session_completion` / emitting `session.completed` → that is SessionService.end_session +
  the adapter (SMP3-06). This task only PRODUCES the `SessionCompletion`.
- A real XP engine / Coach-verdict→misconception wiring (Phase 2 / later).
- Deleting the Graphiti `record_topic_confidence_update` (SMP-004) — just stop depending on it.

## Acceptance Criteria

- [ ] The pure delta policy lives in a non-Graphiti module and computes the documented heuristic; importing it
      does NOT import `graphiti_core`.
- [ ] `build_session_completion` reads current confidence via the store (get_topic_confidences), applies the
      policy delta, clamps to [0,100], and emits a `ConfidenceUpdate` for the covered topic with the resolved value.
- [ ] With misconceptions empty and ≥5 turns, the covered topic's confidence is nudged +1 (engagement bonus);
      with <5 turns and no misconceptions, delta 0 (no change / no update emitted for an unchanged value is acceptable).
- [ ] A covered topic with no current confidence row yields no `ConfidenceUpdate` (skipped, not invented).
- [ ] `xp_awarded == 0`, `misconceptions == []`; `topic`/`aos_scaffolded` are carried through.
- [ ] The producer is pure w.r.t. the injected store (unit-testable with `FakeStudentStore`); no adapter/graph import.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
.venv/bin/python -m pytest tests/unit/session/test_completion_producer.py -v
.venv/bin/python -c "import importlib,sys; m=importlib.import_module('study_tutor.knowledge.confidence_policy'); assert 'graphiti_core' not in sys.modules or True; print('policy import ok')"
.venv/bin/python -m pytest tests/unit -q   # composition guard (moving the policy must not break test_queries)
.venv/bin/ruff check src/study_tutor/session/ src/study_tutor/knowledge/
```

## Implementation Notes

- `ConfidenceUpdate` is `store.entities.ConfidenceUpdate(topic_name, percentage)` (`entities.py:124-134`) — the
  RESOLVED post-session value, not a delta (W1 record_session_completion persists the value + derives the band).
- Reuse W2's `store.get_topic_confidences(student_id)` (returns `student_model.TopicConfidence` with `.topic_ref`
  and `.percentage`) to find the current percentage for `topic`.
- If you move `Phase1MinimalDeltaPolicy` out of `queries.py`, update `queries.py`'s importers/`__all__` and
  `tests/unit/knowledge/test_queries.py` accordingly (or re-export from queries to avoid churn) — run `pytest tests/unit`.

## Boundary-test discipline (read the retro)

Test the producer's behaviour (delta math, clamp, skip-unknown-topic), not transient module locations. If you
re-export the policy from queries.py for back-compat, don't assert it is ABSENT there (SMP-004 removes it, not this task).

## BDD Scenarios

- Ending a session derives the confidence update from the learner's current stored confidence
- Ending a session marks it ended and records the learner-state deltas *(the completion feeding record_session_completion)*
