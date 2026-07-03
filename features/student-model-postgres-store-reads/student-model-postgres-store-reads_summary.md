# Feature Spec Summary: Student Model Postgres Store — Reads (FEAT-SMP-002)

**Stack**: python
**Generated**: 2026-07-03T21:12:27Z
**Scenarios**: 19 total (2 Scenario Outlines → 9 example rows); 4 @smoke, 2 @regression
**Assumptions**: 11 total (5 high / 3 medium / 3 low confidence)
**Review required**: Yes (ASSUM-003, ASSUM-007, ASSUM-010)

## Scope

Implements the read path of the study-tutor-owned Postgres StudentStore over the
merged W1 schema: `get_student_state`, `get_topic_confidences`, and
`get_recent_misconceptions` on `PostgresStudentStore`, resolved behind the
existing `knowledge.store.reads` helpers (`get_student_state`,
`load_planner_inputs`). It repoints the one live production read — the session
planner (`planner/pipeline.py`) — off the retired Graphiti path onto the store,
wires the store conditionally at serve startup, and removes the Graphiti read
copies from `knowledge.queries`. It preserves the graceful-degradation contract:
an unknown learner or an unreachable store yields an empty snapshot / empty
planner inputs, never an exception.

**Out of scope**: the write path (FEAT-SMP-001, merged); session create/append/
list/end (FEAT-SMP-003, gated by G-CON); the graph WRITE-path removal and the
graph seed-script migration (a later cutover, FEAT-SMP-004).

## Scenario Counts by Category

| Group | Count |
|-------|-------|
| A — Key examples | 5 |
| B — Boundary conditions | 4 |
| C — Negative / degradation | 4 |
| D — Edge cases / migration semantics | 6 |
| **Total** | **19** |

(Scenarios carry multiple tags; @smoke=4, @regression=2, @planner-repoint=3,
@degradation=4, @edge-case=8 cut across the groups above.)

## Key design decisions (resolved in spec review)

1. **band-at-observation is approximated (ASSUM-003, low).** The `misconception`
   table does not persist `confidence_band_at_observation`; `get_recent_misconceptions`
   reconstructs it from the learner's current `topic_confidence.band` for the topic
   (default `"struggling"`). No schema/write-path change — the field has no
   downstream consumer.
2. **Store wired conditionally at startup (ASSUM-007, low).** `build_student_store()`
   is called in the serve boot **only when `STUDY_TUTOR_PG_DSN` is set**; otherwise
   the runtime stays unwired and reads degrade to empty (keeps DSN-less dev/CI green).
   Without this the repoint is inert in production (store resolves to `None`).
3. **`most_recent_session_id` from the session table; `stale` retired
   (ASSUM-004/005).** The Postgres snapshot reads the latest session by
   `last_activity`; the Graphiti-era stale-fact flag is dropped (always `False`).
4. **Surgical read-copy removal (ASSUM-009).** Only the read surface leaves
   `queries.py`; shared write-path helpers and the confidence write path are
   retained for FEAT-SMP-004.

## Deferred Items

- Graph WRITE-path removal from `queries.py` (`record_topic_confidence_update`,
  the fire-and-forget `record_session_completion`) → FEAT-SMP-004 cutover.
- The graph **seed script** (`scripts/seed_student_model.py`) and its Postgres
  seeding counterpart → its read verification must be reworked or the script
  deprecated as part of removing the `queries` read symbol (see ASSUM-010).
- `get_topic_recommendations` ranking re-homing — no production consumer; retired
  with the Graphiti read tests rather than lifted.

## Open Assumptions (low confidence — human/Coach review required)

- **ASSUM-003** — `confidence_band_at_observation` approximated from current band.
- **ASSUM-007** — conditional store wiring in the serve boot (prod will connect to
  Postgres when the DSN is set).
- **ASSUM-010** — seed-script disposition so the `queries` read-copy removal does
  not break the graph seed tool / `test_queries` / `test_lilymay_seed_seam`.

## Execution risks for /feature-plan and autobuild

- **Read-copy deletion is coupled to test rework.** `tests/unit/knowledge/test_queries.py`
  (read tests) and `tests/integration/test_lilymay_seed_seam.py` exercise the removed
  surface; `tests/unit/planner/test_pipeline.py` and the seeding tests import
  `StudentState`/`TopicConfidenceSnapshot` from `queries`. These must move to the
  store entities or be retired **in the same task** as the removal, or the full suite
  goes red (per the W1 self-defeating-boundary-tests retro — verify the whole suite,
  not just per-task).
- **Serialize the waves.** Store/adapter tasks touch the same modules
  (`postgres.py`, `reads.py`, `queries.py`, `pipeline.py`); per the parallel-wave
  worktree-pollution retro, encode one-task-per-wave in the feature YAML
  `orchestration.parallel_groups` (no `--max-parallel` flag exists).
- **Export an ephemeral `STUDY_TUTOR_PG_DSN`** (throwaway `postgres:16`, never the
  NAS) before autobuild so the Coach's DB-backed read tests run for real.

## Integration with /feature-plan

    /feature-plan "Student Model Postgres Store — Reads" \
      --context features/student-model-postgres-store-reads/student-model-postgres-store-reads_summary.md
