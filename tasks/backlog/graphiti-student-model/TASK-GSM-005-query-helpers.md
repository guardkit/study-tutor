---
id: TASK-GSM-005
title: "Implement student-model query helpers"
task_type: feature
parent_review: TASK-REV-7DC0
feature_id: FEAT-1773
wave: 3
implementation_mode: task-work
complexity: 5
estimated_minutes: 150
status: backlog
priority: high
created: 2026-04-27T00:00:00Z
updated: 2026-04-27T00:00:00Z
dependencies:
  - TASK-GSM-003
  - TASK-GSM-004
tags: [graphiti, queries, recommendations, scoping, ddr-003, planner]
consumer_context:
  - task: TASK-GSM-003
    consumes: GraphitiClient
    framework: "graphiti-core async client"
    driver: "graphiti-core"
    format_note: "Helpers receive GraphitiClient | None. When client is None, all read helpers return empty/safe defaults; record_session_completion is a no-op (returns immediately)."
  - task: TASK-GSM-003
    consumes: FalkorDBConnection
    framework: "graphiti-core (FalkorDB driver)"
    driver: "graphiti-core"
    format_note: "Search calls use search_nodes / search_memory_facts via the wrapped client; group_ids are mandatory positional argument"
  - task: TASK-GSM-004
    consumes: SharedAsyncWriteHelper
    framework: "asyncio fire-and-forget"
    driver: "asyncio"
    format_note: "record_session_completion calls helper.schedule_write(group_ids, episode, flush_id='F3') — does NOT await the returned task. Caller-facing path returns within 2s per ADR-ARCH-019."
  - task: TASK-GSM-001
    consumes: GroupIdConstants
    framework: "string constants"
    driver: "stdlib"
    format_note: "All search calls construct group_ids from STUDENT_GROUP_PREFIX / SUBJECT_GROUP_PREFIX / FLEET_GROUP_ID — no raw string literals"
---

# Task: Implement student-model query helpers

## Description

Implement the three query helpers the Tutor handler and planner call into the student model with. Per `phase-1-scope.md §FEAT-PH1-001` query helpers and the build plan (Saturday afternoon, step 7).

These helpers form the **read side** of FEAT-1773 and the **write side** of flush point F3 (session-end episode), per DDR-002. F1 (misconception) and F2 (confidence delta) writes are owned by the Coach AsyncSubAgent and the planner-handler path respectively (out of scope for this task — they consume `GraphitiWriteHelper` directly in FEAT-PH1-002 / FEAT-PH1-003).

## Scope

**Module** (`src/study_tutor/knowledge/queries.py`):

1. `async def get_student_state(client, student_id, *, stale_threshold_days=180) -> StudentState | None`
   - Returns `StudentState` containing: identity, year_group, target_grade, subjects, current_texts, per-topic confidence bands, recent misconceptions (last 30d), most recent completed session (or None)
   - Reads via `search_nodes` scoped to `[f"{STUDENT_GROUP_PREFIX}{student_id}"]`
   - Per ASSUM-006: facts older than `stale_threshold_days` are flagged on the result (`stale: bool`) but still returned
   - Honours read-path timeout: if the call exceeds 5s (ASSUM-005) → returns `None` and logs `event=student_state_read_timeout`
   - When `client is None` → returns an empty `StudentState(empty=True)`

2. `async def get_topic_recommendations(client, student_id, count=3, cooldown_hours=48) -> list[TopicRecommendation]`
   - Returns up to `count` topics (default 3 per ASSUM-002), prioritised by:
     - Struggling-band topics not revised in last `cooldown_hours` (ASSUM-003)
     - Developing-band topics with a misconception observed in the last 30d
     - Developing-band topics not revised in last `cooldown_hours`
     - (rule 5 — random developing-band fallback) — stubbed `# TODO(phase-2)` per build plan
   - Excludes topics revised within `cooldown_hours` from the head of the list (per `@boundary` scenario)
   - Returns `[]` (not None) when no candidates exist
   - Each `TopicRecommendation` carries: `topic_name`, `reason` (`struggling_stale` / `developing_misconception` / `developing_stale`), `confidence_band`, `last_revised_at`

3. `async def record_session_completion(client, write_helper, student_id, session_summary) -> None`
   - **F3 flush point.** Per DDR-002 + DDR-003: emits the `session.completed` event on the in-process bus *before* scheduling the Graphiti write (event-emit decoupled from write success). For Phase 1, the bus is not yet wired; this helper just constructs the `SessionCompletedEpisode` and dispatches via `write_helper.schedule_write(..., flush_id="F3")`.
   - **Fire-and-forget**: returns within 50ms even when the underlying `add_episode` would take 80s+
   - **Caller-facing**: handler `tutor_session_end` calls this and returns; never awaits the task
   - When `client is None` → no-op, returns immediately

**Result types** (in same module or separate `query_results.py`):
- `StudentState(BaseModel)` — full read-path payload
- `TopicRecommendation(BaseModel)` — single recommendation entry

## Acceptance Criteria

- [ ] `get_student_state` returns a fully-populated `StudentState` for Lilymay's seeded baseline
- [ ] `get_student_state(client=None)` returns an empty `StudentState(empty=True)` without raising
- [ ] Read-path timeout: `get_student_state` returns None + logs when underlying search exceeds 5s (mocked via slow `search_nodes`)
- [ ] Stale-fact flag: facts older than 180 days are returned with `stale=True` (ASSUM-006)
- [ ] `get_topic_recommendations` returns 3 results for a learner with mixed-band topics
- [ ] `get_topic_recommendations` excludes topics revised within 48h (cooldown per ASSUM-003)
- [ ] `get_topic_recommendations` prioritises struggling-stale > developing-misconception > developing-stale
- [ ] `record_session_completion` returns within 50ms (mocked write helper for unit test; real Synology integration test)
- [ ] `record_session_completion(client=None)` is a no-op (no exception)
- [ ] All `search_*` calls in this module use `group_ids` constructed from `STUDENT_GROUP_PREFIX` etc. — never bare string literals
- [ ] Group-id discipline lint: AST scan asserts no `search_nodes(...)` or `search_memory_facts(...)` call inside this module passes a literal string for `group_ids`
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

- Unit tests in `tests/unit/knowledge/test_queries.py`:
  - `get_student_state` happy path (mock graphiti responses)
  - `get_student_state` returns empty when client is None
  - `get_student_state` returns None on timeout (mock `search_nodes` to sleep 6s)
  - `get_topic_recommendations` ranking across 4 fixture profiles (all-secure, one-struggling-stale, dev-with-misconception, mixed)
  - `get_topic_recommendations` cooldown exclusion (topic revised at now-47h excluded; at now-49h included)
  - `record_session_completion` calls `write_helper.schedule_write` with `flush_id="F3"` and the correct group_ids
  - `record_session_completion` returns < 50ms even when the helper's task hangs (use a hanging mock `add_episode`)
- Integration tests in `tests/integration/test_queries_integration.py` (gated on Synology FalkorDB + Lilymay seeded baseline):
  - Real call returns Lilymay's seeded state
  - Recording a session completion is observable via the next `get_student_state` call (after grace period)

## Implementation Notes

- These helpers are the **scoping discipline** surface: they are the only place in Phase 1 that calls `search_nodes` / `search_memory_facts` directly. Every call MUST pass `group_ids` constructed from the constants.
- Do NOT swallow exceptions silently — let them propagate from the wrapped client unless they're timeout-shaped (catch + return None).
- The `record_session_completion` helper is the F3 owner. It MUST go through `GraphitiWriteHelper.schedule_write`, never call `add_episode` directly. CC-13 conformance test (in TASK-GSM-004) will fail if this rule is broken.
- DDR-003 says event emit comes BEFORE write task scheduling. For Phase 1, the in-process bus isn't wired yet — this helper just dispatches the write. Add a `# TODO(FEAT-PH1-003): emit session.completed before schedule_write` comment so the wiring task lands the discipline correctly.

## Seam Test Recommendation

This task crosses two integration boundaries (Graphiti search API, async write helper). Mandatory seam tests:
- **Contract test** for `record_session_completion` returning < 50ms with a hanging write
- **Boundary test** for read-path timeout returning None on slow `search_nodes`
- **Mock-based seam test** for client=None graceful degradation across all three helpers

## Seam Tests

```python
"""Seam tests for query helpers — validate contracts from TASK-GSM-003 and TASK-GSM-004."""
import asyncio
from unittest.mock import AsyncMock, MagicMock
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("GraphitiClient")
def test_graphiti_client_format():
    """Verify GraphitiClient contract is honoured by query helpers.

    Contract: Helpers receive GraphitiClient | None. When client is None,
              all read helpers return empty/safe defaults; record_session_completion
              is a no-op (returns immediately).
    Producer: TASK-GSM-003
    """
    from study_tutor.knowledge.queries import (
        get_student_state,
        get_topic_recommendations,
        record_session_completion,
    )

    async def _run():
        # Format assertion: client=None must not raise
        state = await get_student_state(client=None, student_id="lilymay")
        assert state is None or getattr(state, "empty", False) is True

        recs = await get_topic_recommendations(client=None, student_id="lilymay")
        assert recs == []

        # record_session_completion is a no-op with client=None
        await record_session_completion(
            client=None,
            write_helper=MagicMock(),
            student_id="lilymay",
            session_summary={},
        )

    asyncio.run(_run())


@pytest.mark.seam
@pytest.mark.integration_contract("SharedAsyncWriteHelper")
def test_shared_async_helper_fire_and_forget():
    """Verify SharedAsyncWriteHelper contract is honoured by record_session_completion.

    Contract: record_session_completion calls helper.schedule_write(...,
              flush_id='F3') — does NOT await the returned task. Caller-facing
              path returns within 2s per ADR-ARCH-019.
    Producer: TASK-GSM-004
    """
    from study_tutor.knowledge.queries import record_session_completion

    async def _run():
        # Producer side: a write helper whose schedule_write returns a never-completing task
        helper = MagicMock()
        never_completes = asyncio.create_task(asyncio.sleep(80))
        helper.schedule_write = MagicMock(return_value=never_completes)

        # Consumer side: helper.schedule_write must be called with flush_id="F3"
        # and the function must return within 2s even when the task hangs
        async def _timed():
            await record_session_completion(
                client=MagicMock(),
                write_helper=helper,
                student_id="lilymay",
                session_summary={"topic": "Macbeth Act 1"},
            )

        await asyncio.wait_for(_timed(), timeout=2.0)
        assert helper.schedule_write.called
        # Format assertion: flush_id MUST be "F3" per DDR-002
        kwargs = helper.schedule_write.call_args.kwargs
        assert kwargs.get("flush_id") == "F3"

        never_completes.cancel()

    asyncio.run(_run())
```
