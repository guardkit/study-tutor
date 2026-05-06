# TASK-GR-CONF — Completion Report

**Title:** Wave 5 — BLOCK-3b: TopicConfidence node update on session end (typed-entity write + pluggable policy)
**Completed:** 2026-05-06
**Complexity:** 5/10
**Estimated:** 240 min · **Actual:** ~120 min (single sitting; design pre-baked in TASK-REV-GRD5 §R1.3)

## Outcome

Phase-1 BLOCK-3b infrastructure landed. `tutor_session_end` now updates the `TopicConfidence` node attributes (`percentage`, `band`, `last_revised_at`) and dispatches an F2 episode on every non-zero delta. Implementation is split between **infrastructure** (UUID derivation → load → mutate → save → episode) and **policy** (deferred to FEAT-PH2-001 via the `ConfidenceDeltaPolicyLike` Protocol seam).

## Approach

- **Mirrored the seed's typed-entity write pattern** (ADR-ARCH-021): UUID via `seed_uuids.topic_confidence_uuid`, `EntityNode.get_by_uuid` to load, in-place attribute mutation, `EntityNode.save` to persist. Bypasses graphiti-core's LLM extraction path entirely → ms-latency, R-WAVE5-03 immune.
- **Per-group named-graph clone** (TASK-FORK-PATCH bug #8): added `_driver_for_group_id` mirroring the seed's helper so the load/save targets the `student-<id>` named graph rather than the default `study_tutor` database.
- **Fire-and-forget posture** (ADR-ARCH-019): `EntityNode.save` wrapped in `create_task_fn`; `schedule_write` is itself sync. Adapter-side dispatch via `asyncio.create_task` so `tutor_session_end` returns within the ASSUM-004 2 s budget regardless of FalkorDB latency.
- **Protocol seam** (TASK-REV-GRD5 §R1.3): `Phase1MinimalDeltaPolicy` ships as a deliberately-weak stub (`-3 * misc_count`, `+1` engagement bonus, clamped to ±10) so FEAT-PH2-001 has a clean substitution surface. Policy `name` attribute → episode `confidence_source` field for downstream filtering of heuristic-era data.
- **Phase-1 fallback for misconception aggregation:** `TutorSession` doesn't currently track per-turn `CoachVerdict` payloads, so the adapter passes `misconceptions_per_topic={}`. The stub then produces `+1` for engagement-only sessions (turns ≥ 5) and `0` otherwise — both satisfy AC-DEMO-03.

## Files changed (vs. parent commit `f6fb3ed`)

```
src/study_tutor/knowledge/queries.py     +332   -0
src/study_tutor/mcp/adapter.py             +86   -1
tests/unit/knowledge/test_async_write.py    +2   -0   (fixture: confidence_source required)
tests/unit/knowledge/test_queries.py     +611   -0   (AC-CONF-10)
tests/unit/mcp/test_adapter.py           +197   -0   (AC-CONF-08 wiring)
tests/integration/test_topic_confidence_update_smoke.py   +159 -0  (new, AC-CONF-11)
```

`episodes.py` and `test_episodes.py` were already at the desired state in `f6fb3ed` (the prep commit shipped the schema bump). My edits were idempotent.

## Acceptance criteria

| AC | Status | Notes |
|---|---|---|
| AC-CONF-01 | ✅ | `record_topic_confidence_update` in `queries.py` with the spec's signature. |
| AC-CONF-02 | ✅ | `ConfidenceDeltaPolicyLike` Protocol + `Phase1MinimalDeltaPolicy` stub; FEAT-PH2-001 named in docstring. |
| AC-CONF-03 | ✅ | UUID via `topic_confidence_uuid`, `EntityNode.get_by_uuid`, clamp `[0, 100]`, band recompute, `last_revised_at` flip, `EntityNode.save`. |
| AC-CONF-04 | ✅ | Delta != 0 → entity update + F2 episode; delta == 0 → entity update only (`last_revised_at` flip), F2 suppressed. |
| AC-CONF-05 | ✅ | `EntityNode.save` wrapped in `create_task_fn`; `schedule_write` synchronous fire-and-forget. |
| AC-CONF-06 | ✅ | `node_not_found`, `load_failed`, `save_dispatch_failed` — all logged, never raised. |
| AC-CONF-07 | ✅ | `confidence_source: str` (`min_length=1`, `extra="forbid"` makes it a contract change) — schema in `f6fb3ed`, body projection + required-field test added here. |
| AC-CONF-08 | ✅ | Adapter wiring with skip-conditions (zero turns / no helper / no plan / no graphiti_client). |
| AC-CONF-09 | ⏳ | **Operator step.** Live MCP session against Lilymay's "Lady Macbeth's ambition"; `mcp__graphiti__search_nodes` JSON pasted into PR. |
| AC-CONF-10 | ✅ | 7 unit cases: clamp ±10, delta-0 (no episode), delta != 0 with band crossing (69→70 dev→secure), delta != 0 without band crossing (50→51 dev), `node_not_found` logging, Protocol-surface seam, per-group `clone(database=...)` invocation. |
| AC-CONF-11 | ✅ | `tests/integration/test_topic_confidence_update_smoke.py` — gated by `STUDY_TUTOR_LIVE_GRAPHITI_SMOKE`, fake `+2` policy, asserts `percentage` move + `last_revised_at` flip. |
| AC-CONF-12 | ⏳ | **Operator step.** PR description must call out the `confidence_source` schema bump and the `confidence_source != "phase1_minimal_policy"` Phase-2 dashboard filter. |

## Test results

- **Unit:** 783 passed, 1 skipped (live-only), 2 deselected.
- **Deselected (pre-existing failures, unrelated to this task, confirmed failing on clean `main`):**
  - `tests/unit/planner/test_protocols.py::test_mypy_strict_accepts_structurally_conforming_rule` (mypy environment; mentioned in the task spec as "the pre-existing mypy env failure unchanged").
  - `tests/unit/knowledge/test_graphiti_client_wiring.py::test_cross_encoder_sentinel_raises_on_arbitrary_method_name` (DECISION-DF-001 sentinel — separate bug).
- **Coverage:** 80% across `knowledge.queries` + `knowledge.episodes` + `mcp.adapter`.
- **Integration:** smoke test exists; operator-run only (live FalkorDB required).

## Lessons / decisions worth remembering

- **The episodes.py + test_episodes.py schema bump landed in `f6fb3ed` ahead of /task-work.** Be wary of double-edits when prep commits exist; check `git diff --stat HEAD` before writing duplicate code. My Edits matched the *post-prep* state idempotently, but the wasted effort would have been visible in a less benign diff.
- **`EntityNode.get_by_uuid` is the right load primitive.** Direct Cypher works too (the existing typed-entity smoke uses it for counting), but the typed API is what the seed ecosystem standardised on, so using it here keeps the two write paths symmetrical.
- **Phase-1 misconception aggregation deferred:** `TutorSession.turns` doesn't carry `CoachVerdict` payloads in Phase 1. Extending it would have pushed complexity past 6; the spec explicitly authorised the `misc_count = 0` fallback, and the stub policy still produces a non-zero positive delta on engagement so AC-DEMO-03 stays demoable.
- **The Protocol seam is the load-bearing artefact for FEAT-PH2-001**, not the stub. The stub's heuristic is throwaway; the Protocol contract (`name: str`, `compute(*, student_id, topic_ref, session_summary) -> int`) is what FEAT-PH2-001 will need to honour. Tests pin this via the `_FakePolicy` Protocol-surface case.

## Follow-ups for the operator

1. **AC-CONF-09 evidence.** Run a live MCP session against Lilymay's "Lady Macbeth's ambition" and paste the post-session `mcp__graphiti__search_nodes` JSON into the PR description.
2. **AC-CONF-11 smoke run.** `STUDY_TUTOR_LIVE_GRAPHITI_SMOKE=1 .venv/bin/python -m pytest tests/integration/test_topic_confidence_update_smoke.py` against the live FalkorDB. The test reads-modifies-rereads, so the post-condition leaves the graph non-baseline; reseed via `scripts.seed_student_model` after.
3. **AC-CONF-12 PR description.** Call out (a) `confidence_source` is a deliberate Pydantic schema bump (`extra="forbid"`), and (b) `confidence_source != "phase1_minimal_policy"` is the Phase-2 dashboard filter for real-signal data.
4. **TASK-GR-DEMO unblock.** With BLOCK-3b infrastructure landed, the parent demo task should be re-runnable end-to-end. Verify AC-DEMO-03 and close the BLOCK-3 series.

## Cross-references

- Parent review: `.claude/reviews/TASK-REV-GRD5-review-report.md` §R1.3 (Coach-signal taxonomy + Protocol-seam decision)
- ADR-ARCH-019 — fire-and-forget posture
- ADR-ARCH-021 — typed-entity write pattern (mirrored here)
- TASK-GR-WIRE — supplied the `write_helper` / `graphiti_client` injection seam consumed by AC-CONF-08
- FEAT-PH2-001 — owner of the `Phase1MinimalDeltaPolicy` replacement
