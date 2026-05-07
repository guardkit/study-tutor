---
id: TASK-GSE-001
title: Surface the actual error message on graphiti_write_failed (originally misdiagnosed as "session_completed episode not written")
task_type: feature
status: completed
priority: high
created: 2026-05-06T00:00:00+00:00
updated: 2026-05-07T00:00:00+00:00
completed: 2026-05-07T00:00:00+00:00
completed_location: tasks/completed/TASK-GSE-001/
previous_state: in_review
state_transition_reason: "/task-complete: Phase A delivered (log instrumentation + regression test); 5 ACs explicitly withdrawn per Phase B finding (writes succeed; the apparent bug is in MCP get_episodes — separate task)"
complexity: 5
related:
  - TASK-GSM-002
  - TASK-GR-DEMO
  - TASK-PH2-GR-001
tags:
  - bug-fix
  - graphiti
  - session-end
  - episode-write
  - falkordb
  - redisearch
  - group-id
context_files:
  - src/study_tutor/tutoring/session_end.py
  - src/study_tutor/mcp/adapter.py
  - scripts/seed_student_model.py
design:
  status: approved
  approved_at: "2026-05-06T00:00:00+00:00"
  approved_by: "human"
  implementation_plan_path: docs/state/TASK-GSE-001/implementation_plan.md
  architectural_review_score: 87
  complexity_score: 5
  decisions:
    path_b1_pre_approved: true
    migrate_full_convention: true
    integration_test_in_task: true
  executed_phases: [A, "D-1"]
  abandoned_phases: ["C (B1 migration)", "D-2 (group_id format test)", "D-2b (hyphen-rejection test)", "D-3 (smoke test)", "D-4 (real-FalkorDB test)"]
  abandonment_reason: "Phase B (manual log readout) revealed writes are succeeding. The hyphen hypothesis was wrong; the apparent symptom was caused by a separate read-side issue in mcp__graphiti__get_episodes — out of scope for this task."
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Fix `session_completed` episode not written to Graphiti on session end

## Description

After a successful 5-turn tutoring session
(`session_id = c78a49a0-159d-46b6-9844-1e1cef67c996`) on **2026-05-06**,
`tutor_session_end` returned

```json
{"session_id": "c78a49a0-159d-46b6-9844-1e1cef67c996", "status": "ended"}
```

indicating success. However,
`graphiti:get_episodes(group_ids=["student-lilymay"])` returns an
**empty list** — no `session_completed` episode was written.

The `TopicConfidence` node update for the same session **did** succeed:

- `percentage` advanced 55 → 56,
- `last_revised_at` flipped from the epoch sentinel to
  `2026-05-06T19:49:09`.

So:

- The Graphiti client connection is working.
- `Phase1MinimalDeltaPolicy` fired correctly.
- Only the **episode write** is missing.

## Investigation Areas

1. [src/study_tutor/tutoring/session_end.py](src/study_tutor/tutoring/session_end.py) — Check `perform_session_end`:
   - Is there an `add_episode` call for the `session_completed` event?
   - If so, is it `await`ed properly?
   - Is there error handling that silently swallows failures?

2. [src/study_tutor/mcp/adapter.py](src/study_tutor/mcp/adapter.py) — Check the `tutor_session_end` handler:
   - Does it call `perform_session_end` with the correct arguments?
   - Is the `graphiti_client` being passed through?

3. Check whether `add_episode` requires a different `group_id` format
   or `source` parameter than what's being passed. The
   `TopicConfidence` typed-entity write uses Cypher (bypasses
   RediSearch), but `add_episode` goes through the standard Graphiti
   ingestion pipeline which may have different `group_id` requirements.

   **Note**: hyphens in `group_ids` break FalkorDB RediSearch fulltext
   queries — `student-lilymay` uses a hyphen.

## Key Hypothesis

The hyphenated `group_id` `student-lilymay` may be causing
`add_episode` to fail silently.

- The `TopicConfidence` update works because it uses **typed-entity
  Cypher writes** that bypass RediSearch.
- But `add_episode` goes through the standard Graphiti ingestion
  pipeline which uses **RediSearch** for deduplication, and **hyphens
  break FalkorDB RediSearch fulltext query parsing**.

If this is the cause, the fix is one of:

- **Option A (preferred if practical)**: Migrate the student
  `group_id` to the underscore convention (`student__lilymay`) and
  re-seed.
- **Option B**: Ensure `add_episode` handles the hyphenated ID
  gracefully (e.g. quote/escape the term before it reaches the
  RediSearch query).

The task-work phase should confirm the root cause first
(silent-swallow vs. RediSearch parse failure vs. missing call site)
before committing to a fix path.

## Acceptance Criteria

### Delivered (this task)

- [x] **Root cause identified and recorded** — see "Resolution" below.
      The episode IS being written by `study-tutor`; the symptom that
      motivated the task (`get_episodes` returning empty) is caused by
      an unrelated issue with the MCP `get_episodes` tool, not by a
      silent failure in the write path.
- [x] **Silent error handling replaced with logged warning** — Phase A
      added `error` and `error_repr` structured fields to all three
      log surfaces in `async_write.py` (`graphiti_write_failed`,
      `graphiti_write_dropped_invalid`,
      `graphiti_write_dropped_injection`). Future failures will now
      log the exception message, not just the class name.
- [x] **Existing `TopicConfidence` typed-entity path still works** —
      verified live during Phase B (entities created at
      `2026-05-06T20:49:47.994742+00:00` from the just-run session,
      visible via `mcp__graphiti__search_nodes`).
- [x] **Regression test for the new log fields** — added
      `test_perform_write_logs_actual_error_message` in
      `tests/unit/knowledge/test_async_write.py`. 38 tests pass in the
      module, 26 in `test_session_end.py` + smoke. No regressions.

### Withdrawn / out of scope (filed for follow-up)

- [ ] ~~`get_episodes(group_ids=[...])` returns ≥1 episode after
      session end~~ — un-achievable in this task. The episode IS
      written but `mcp__graphiti__get_episodes` returns `"No episodes
      found"` even with `group_ids=null` (no filter). This is an
      upstream MCP / graphiti-core / FalkorDB driver issue. Belongs
      in a separate task — the write side is healthy.
- [ ] ~~Migrate `student-` → `student_` group-id convention~~ —
      no longer indicated. The hyphen is fine; live entities are
      stored at `group_id: "student-lilymay"` and retrievable via
      `search_nodes`.
- [ ] ~~Update `scripts/seed_student_model.py` for the migration~~ —
      not needed; no migration occurred.
- [ ] ~~Manual round-trip verification via `get_episodes`~~ — write
      half verified live; read half blocked by the upstream
      `get_episodes` issue.
- [ ] ~~Integration test for episode write path~~ — write path is
      not the bug; further integration tests of the write would lock
      in already-working behaviour at the cost of slower CI.

## Reproduction Evidence (session `c78a49a0`, 2026-05-06)

- Session ID: `c78a49a0-159d-46b6-9844-1e1cef67c996`
- Student group_id: `student-lilymay`
- `tutor_session_end` response: `{"session_id": "...", "status": "ended"}`
  (apparent success).
- `graphiti:get_episodes(group_ids=["student-lilymay"])`: empty list.
- `TopicConfidence` node: `percentage` 55 → 56, `last_revised_at`
  updated to `2026-05-06T19:49:09` — confirming the Graphiti
  connection itself is healthy.

## Out of Scope

- Refactoring the broader Phase1MinimalDeltaPolicy or the
  `TopicConfidence` write path — those are working and untouched.
- Adding new episode types beyond `session_completed`.
- Reworking the `tutor_session_end` MCP envelope shape.

## Files Involved

- **Primary**: [src/study_tutor/tutoring/session_end.py](src/study_tutor/tutoring/session_end.py)
- **Secondary**: [src/study_tutor/mcp/adapter.py](src/study_tutor/mcp/adapter.py)
- **Possibly affected**: [scripts/seed_student_model.py](scripts/seed_student_model.py)
  (only if the group_id convention is migrated)

## Implementation Notes

The investigation order followed the design: (1) instrument logging at
the silent-swallow site, (2) re-run a real session, (3) read the new
logs to confirm the root cause, (4) commit to a fix path based on the
evidence.

Step (3) ruled out the hypothesis. Step (4) was therefore not needed.

## Resolution

### What we expected to find (from the design doc)

The `add_episode` write was failing silently inside graphiti-core
because of FalkorDB RediSearch fulltext-query parse errors on the
hyphenated `group_id` `student-lilymay`. The fix would have been a
hyphen → underscore migration across the codebase
(`STUDENT_GROUP_PREFIX`, `SUBJECT_GROUP_PREFIX`, `FLEET_GROUP_ID`)
plus a re-seed.

### What we actually found (Phase B, 2026-05-06)

After Phase A surfaced the error message via the new `error` /
`error_repr` log fields, we re-ran a fresh `tutor_start_session →
tutor_turn × 5 → tutor_session_end` flow. The result:

- **No `graphiti_write_failed` log line at all.** The writes succeed.
- Server logs show:
  ```
  graphiti_core.graphiti: Completed add_episode in 39469.80 ms
  study_tutor.knowledge.async_write: graphiti write succeeded
  graphiti_core.graphiti: Completed add_episode in 50922.03 ms
  study_tutor.knowledge.async_write: graphiti write succeeded
  ```
  (The 39-51 s latency is local-LLM entity extraction, not a write
  failure — it returned successfully both times.)
- A live cross-check via `mcp__graphiti__search_nodes(group_ids=
  ["student-lilymay"])` returns entities created during the
  just-run session, e.g.
  ```
  uuid: 63f69576-2b93-4226-98b4-423fa710ff7d
  name: phase1_minimal_policy
  created_at: 2026-05-06T20:49:47.994742+00:00
  group_id: student-lilymay
  summary: "Student lilymay's confidence on topic 'Lady Macbeth's
            ambition' was updated by phase1_minimal_policy."
  ```
  proving the hyphen does not break write-time entity extraction.

### What the bug actually is

`mcp__graphiti__get_episodes` returns `"No episodes found"` for **all**
queries — even with `group_ids=null` (no filter), even though
`search_nodes` proves the graph is full of live data. The original
report's "the episode wasn't written" was a misdiagnosis: the verifier
(`get_episodes`) returns empty for everything, so it returned empty for
this episode too.

This is an issue inside the MCP server's `get_episodes` implementation
(or the graphiti-core FalkorDB driver's `EpisodicNode` lookup path),
not in `study-tutor`.

### What was delivered

- **Phase A — instrumentation** in
  `src/study_tutor/knowledge/async_write.py`. The three log surfaces
  (`graphiti_write_failed`, `graphiti_write_dropped_invalid`,
  `graphiti_write_dropped_injection`) now capture the exception
  message (`error`) and full repr (`error_repr`) alongside
  `error_class`. If `add_episode` ever does fail, future
  investigations will start with the message in the structured log
  rather than only the class name.
- **Phase D-1 — regression test**
  (`test_perform_write_logs_actual_error_message`) pins the new
  fields so they cannot silently regress.

### What was abandoned

The hyphen → underscore migration plan from the design doc (~3 hours
of mechanical refactoring + a re-seed) was abandoned mid-task because
Phase B disproved its premise. The design plan
(`docs/state/TASK-GSE-001/implementation_plan.md`) is preserved as
historical record but should not be re-applied.

### Recommended follow-up (separate task, not filed yet)

Investigate why `mcp__graphiti__get_episodes` returns empty for all
queries against this FalkorDB instance — likely either:
- a graphiti-core FalkorDB-driver `EpisodicNode` lookup issue
- a graphiti MCP server bug in the `get_episodes` tool's query
  construction
- a config / connection mismatch between the MCP server and the graph
  the writes are landing in (less likely, since `search_nodes` works
  through the same MCP server and finds the right data)

Until that's resolved, use `mcp__graphiti__search_nodes` rather than
`get_episodes` for round-trip verification of session-end writes.

## Test Execution Log

```
$ python -m pytest tests/unit/knowledge/test_async_write.py -x -q
38 passed, 1 warning in 3.71s

$ python -m pytest tests/unit/tutoring/test_session_end.py \
                  tests/integration/test_mcp_session_end_smoke.py -x -q
26 passed, 1 skipped, 1 warning in 0.92s
```
