---
id: TASK-SMP2-06
title: "Remove the Graphiti read surface from queries.py + rework read tests + seed-script disposition"
task_type: refactor
feature_id: FEAT-SMP-002
wave: 6
implementation_mode: task-work
complexity: 6
dependencies: [TASK-SMP2-05]
parent_feature_spec: features/student-model-postgres-store-reads/student-model-postgres-store-reads_summary.md
---

## Objective

Delete the now-superseded Graphiti READ surface from `src/study_tutor/knowledge/queries.py`
(surgically — the WRITE surface stays for a later cutover, FEAT-SMP-004), and rework or retire the
tests and the seed-script verification that depended on it, so `pytest tests/` stays fully green.

## Surgical removal boundary (ASSUM-009)

**Remove from `queries.py`:**
- Read functions: `get_student_state`, `get_topic_recommendations`.
- Read models: `StudentState`, `TopicConfidenceSnapshot`, `MisconceptionSnapshot`,
  `TopicRecommendation`, `RecommendationReason`.
- Read-only helpers: `_read_student_partition`, `_build_student_state`, `_entity_type`
  (verify not used by the write path first).
- Read-only constants: `READ_TIMEOUT_SEC`, `MISCONCEPTION_WINDOW_DAYS`,
  `DEFAULT_STALE_THRESHOLD_DAYS`, `DEFAULT_COOLDOWN_HOURS`, `DEFAULT_RECOMMENDATION_COUNT`.
- The corresponding `__all__` entries.

**RETAIN in `queries.py` (write path — FEAT-SMP-004 removes it later):**
- `record_topic_confidence_update`, `Phase1MinimalDeltaPolicy`, `ConfidenceDeltaPolicyLike`,
  the fire-and-forget `record_session_completion`, and the SHARED helpers they use
  (`_inner_client`, `_coerce_datetime`, `_attr`, `_coerce_node_attribute`, `_driver_for_group_id`,
  `_now_utc`). Before deleting any helper, grep the retained write functions to confirm it is
  read-only. `mcp/adapter.py:47` imports write symbols from `queries` — keep those working.

## Seed-script disposition (ASSUM-010 — the main risk)

`scripts/seed_student_model.py` imports `queries.get_student_state` (`:142`) and calls it for
post-seed verification (`:615`, `:884`). It SEEDS THE GRAPH and has no Postgres seeding counterpart,
so it must NOT be repointed to the (empty) Postgres store. Resolve by removing its dependency on the
deleted symbol: replace the post-seed `get_student_state` verification with a direct graph read
(node/edge count via the existing `_read_student_partition` logic inlined locally, or a simpler graph
probe) OR gate/skip the verification with a clear `TODO(FEAT-SMP-004)` note that the graph seed path
is being retired. Do NOT resurrect the deleted read verbatim into a shared module. Update
`tests/integration/test_lilymay_seed_seam.py:43,69` to match.

## Test rework (per the self-defeating-tests retro — do the whole suite)

- `tests/unit/knowledge/test_queries.py`: delete the read-path tests (`get_student_state` projection/
  timeout/stale, `get_topic_recommendations`) and their imports; keep the write-path tests.
- `tests/unit/planner/test_pipeline.py`, `tests/unit/seeding/test_seed_student_model.py`,
  `tests/unit/seeding/test_seam_seeding_script.py`: repoint imports of `StudentState`/
  `TopicConfidenceSnapshot` from `queries` to `store.entities` (or the store-backed harness from
  TASK-SMP2-05/07). Update the `test_seam_seeding_script` expected-import assertion to the new target.
- Run the FULL `pytest tests/` (not just `tests/unit`) before declaring done — the W1
  self-defeating-boundary-tests retro exists because `tests/`-only stale tests slipped a per-task gate.

## Scope

**In scope:** the surgical removal, the seed-script fix, and the test rework above.

**Out of scope:** removing the graph WRITE path (`record_topic_confidence_update` etc.) →
FEAT-SMP-004. Changing adapter read behaviour → TASK-01/02/03. The planner call site → TASK-05.

## Acceptance Criteria

- [ ] `queries.py` no longer defines `get_student_state`, `get_topic_recommendations`, the four read
      models, the read-only helpers, or the five read-only constants; `__all__` is updated to match.
- [ ] The retained write symbols (`record_topic_confidence_update`, `Phase1MinimalDeltaPolicy`,
      `record_session_completion`, `ConfidenceDeltaPolicyLike`) and their shared helpers still import
      and work; `mcp/adapter.py` imports resolve; `python -c "import study_tutor.knowledge.queries"` succeeds.
- [ ] `scripts/seed_student_model.py` imports cleanly (no reference to the deleted `get_student_state`)
      and its post-seed verification either reads the graph directly or is explicitly gated with a
      `TODO(FEAT-SMP-004)` note.
- [ ] `tests/unit/knowledge/test_queries.py` retains only write-path tests; all read-path tests and
      their `queries`-read imports are removed.
- [ ] Every test importing read models/functions from `queries` is repointed to `store.entities` /
      the store harness or removed; no test imports a deleted `queries` symbol.
- [ ] `pytest tests/` (the WHOLE suite) is green — no red from the removal (composition guard).
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
export STUDY_TUTOR_PG_DSN="postgresql://study_tutor:test@localhost:55432/study_tutor"  # ephemeral (see TASK-01)
.venv/bin/python -c "import study_tutor.knowledge.queries; import study_tutor.mcp.adapter"  # import guard
.venv/bin/python -m pytest tests/unit/knowledge/test_queries.py -v
.venv/bin/python -m pytest tests/unit/planner tests/unit/seeding -v
.venv/bin/python -m pytest tests/ -q   # WHOLE suite — must be green
.venv/bin/ruff check src/study_tutor/knowledge/queries.py scripts/seed_student_model.py
```

## Implementation Notes

- Grep before every helper delete: `grep -n "_read_student_partition\|_entity_type\|_build_student_state"
  src/study_tutor/knowledge/queries.py` and confirm no RETAINED write function calls it. `_coerce_datetime`,
  `_inner_client`, `_attr`, `_coerce_node_attribute`, `_driver_for_group_id`, `_now_utc` ARE used by the
  write path — keep them.
- The 3 pre-existing NATS failures (`tests/integration/test_nats_smoke.py`) are unrelated and may remain
  red on `main`; do not chase them, but do not let this task ADD any new red.

## Boundary-test discipline (read the retro)

This is the task the self-defeating-boundary-tests retro warns about most: a removal is only "done"
when the WHOLE suite is green, because a per-task gate over `tests/unit` cannot see a stale test in
`tests/` that references a deleted symbol. Run `pytest tests/` and fix every red the removal causes.

## BDD Scenarios

- Planning a session no longer consults the retired graph read path *(the removal makes this literally true)*
