# Implementation Plan — TASK-GSE-001

**Title**: Fix `session_completed` episode not written to Graphiti on session end
**Complexity**: 5/10 (medium)
**Mode**: design-only → implement-only
**Generated**: 2026-05-06

---

## 1. Problem Statement

After a successful 5-turn session (`c78a49a0...`), `tutor_session_end`
returned `{status: "ended"}` but `graphiti:get_episodes(group_ids=["student-lilymay"])`
returns an empty list. The `TopicConfidence` typed-entity update succeeded,
proving the Graphiti connection is healthy — only the `add_episode` ingestion
path is failing.

## 2. Code Walk-through (where the bug lives)

The F3 episode write traverses:

```
adapter.tutor_session_end()
  → perform_session_end()                      [tutoring/session_end.py:334]
    → _f3_write_coroutine()                    [tutoring/session_end.py:496]
      → write_helper.schedule_write()          [knowledge/async_write.py:290]
        → asyncio.create_task(_perform_write)  [knowledge/async_write.py:383]
          → await client.add_episode(**kwargs) [knowledge/async_write.py:440]
            ↑ this is the only call site of add_episode in src/ (CC-13)
```

Inside `_perform_write` the try/except catches **`BaseException`** (line 441)
and emits a `graphiti_write_failed` log line that captures `error_class` but
**not the exception message** (`extra={..., "error_class": ...}` — no
`"error": str(exc)`). That gap is why the failure is invisible: the symptom
is logged but its cause is not.

Production wiring is present (`cli/main.py:202` — `GraphitiWriteHelper(client=inner)`
with a real graphiti-core client), so `write_helper is None` is **not** the cause.

## 3. Hypotheses (ordered by prior probability)

| # | Hypothesis                                                           | How to confirm                                |
|---|----------------------------------------------------------------------|-----------------------------------------------|
| 1 | RediSearch fulltext parse failure on hyphenated `student-lilymay`    | Read the `error` message once it's logged    |
| 2 | graphiti-core extraction-LLM call failing (env, model, rate limit)   | Same — error message tells us                |
| 3 | Episode payload validation failure (Pydantic / `extra="forbid"`)     | Same                                          |
| 4 | Some other failure mode entirely                                     | Same                                          |

**The plan does not commit to a fix path until Hypothesis 1 (or another) is
confirmed.** This matches the task description's explicit instruction:

> "The task-work phase should confirm the root cause first (silent-swallow vs.
> RediSearch parse failure vs. missing call site) before committing to a fix path."

## 4. Implementation Phases

### Phase A — Instrumentation (always runs, ~30 min)

**Goal**: surface enough information from the silent-swallow site to identify
the root cause on the next session-end run.

**File**: `src/study_tutor/knowledge/async_write.py`

1. Extend the `graphiti_write_failed` log block (line 443-453) to include:
   - `"error": str(exc)` — the actual exception message
   - `"error_repr": repr(exc)` — the typed repr (defensive, for graphiti-core
     errors that override `__str__` poorly)
2. Same treatment for the `graphiti_write_dropped_invalid` and
   `graphiti_write_dropped_injection` paths so all three failure surfaces
   carry identical structured fields.
3. No behavioural change — log-only — preserves ADR-ARCH-019 fire-and-forget
   contract.

**This change alone satisfies the AC item:**
> "Any silent error handling around the episode write is replaced with a logged
> warning [...] so future failures of this kind are visible rather than invisible."

The error class **was** logged; the message **wasn't**. Adding the message
closes the gap without adding a propagation path that would violate the
fire-and-forget contract.

### Phase B — Confirm root cause (manual, ~10 min)

1. Restart the MCP server (so the new log fields are active).
2. Run `tutor_start_session` → `tutor_turn` ×5 → `tutor_session_end`.
3. Inspect server stderr for `graphiti_write_failed`. Read the new `error`
   field.
4. Categorise:
   - Contains "RediSearch" / "syntax" / "fulltext" → **Path B1** (group-id fix)
   - Contains "extraction" / "LLM" / API-key terms → **Path B2** (LLM env fix, likely out of scope for this task — would file a follow-up)
   - Contains "validation" / "extra fields" → **Path B3** (episode payload fix)
   - Anything else → write findings into the task and reassess

**Decision gate**: the implement-only run pauses here for a human read-out.
The remainder of the plan branches based on what the log says.

### Phase C — Apply the fix

**Path B1 — RediSearch hyphen confirmed (most likely)**

The hyphen is baked into multiple constants
(`STUDENT_GROUP_PREFIX`, `SUBJECT_GROUP_PREFIX`, `FLEET_GROUP_ID`). Migrating
to underscores has wide blast radius (≥15 tests + ≥5 source files + a re-seed
of all existing student data). **Recommend: migrate.** Rationale:

- graphiti-core's RediSearch fulltext query is upstream code we don't own; a
  local "escape the group-id" patch would be brittle and lose visibility on
  upstream-version bumps.
- The hyphen convention was a stylistic choice — underscores are Pythonically
  identical and idempotent under RediSearch tokenisation.

Files to change (Path B1):

| File                                                   | Change                                                                                |
|--------------------------------------------------------|---------------------------------------------------------------------------------------|
| `src/study_tutor/knowledge/student_model.py`           | `student-` → `student_`, `subject-` → `subject_`, `fleet-appmilla` → `fleet_appmilla` |
| `src/study_tutor/knowledge/async_write.py`             | `_validate_group_ids` already reads constants — no string change                      |
| `scripts/seed_student_model.py`                        | Update string literals + add a one-shot delete-old-data block (see below)             |
| `tests/unit/knowledge/test_async_write.py`             | Update expected group-id values                                                       |
| `tests/unit/knowledge/test_student_model.py` (if exists)| Same                                                                                  |
| `tests/unit/tutoring/test_session_end.py`              | Same                                                                                  |
| `tests/integration/test_mcp_session_end_smoke.py`      | Same                                                                                  |
| Any other tests that hardcode `student-` / `subject-` / `fleet-appmilla` | Find via `git grep "student-\|subject-\|fleet-appmilla"`                              |

**Re-seed plumbing in `scripts/seed_student_model.py`:** inline a Cypher
`MATCH (n {group_id: 'student-lilymay'}) DETACH DELETE n` (and likewise for
edges) at the top of `seed_lilymay`, guarded by a check that hyphenated
nodes still exist. No flag — this is a one-time migration; a flag would be
YAGNI. Keeps the script re-runnable and removes orphan hyphenated data
from FalkorDB.

**Docstring fix on `_validate_group_ids`:** the docstring on
`async_write.py:151-153` currently reads `student:<id>` / `subject:<slug>` /
`fleet:appmilla` (colon form), which has never matched the actual
implementation (the validator already uses the dash-form constants). Update
it to the post-migration underscore form as part of this commit. Fixing a
pre-existing doc drift while the file is open is the right call — leaving
it would make a future reader trust the wrong spec.

**Path B2 — LLM extraction failure**

Surface area: usually env-config (model name unset, rate-limited, etc.).
Fix is configuration, not code. **Likely out of scope** for this task —
file follow-up TASK if observed.

**Path B3 — Episode payload validation**

Surface area: `SessionCompletedEpisode` fields don't match what graphiti-core
expects in the `episode_body` JSON. Fix in `knowledge/episodes.py` (likely
narrow). Re-test.

### Phase D — Regression tests (always runs)

**File**: `tests/unit/knowledge/test_async_write.py`

1. **New unit test** — `test_perform_write_logs_actual_error_message`:
   monkeypatch `client.add_episode` to raise `ValueError("redis fulltext: ...")`,
   capture the log via `caplog`, assert the log record contains both
   `error_class == "ValueError"` **and** `error == "redis fulltext: ..."`.
   This locks in the Phase A instrumentation so it can't regress.

2. **New unit test** — `test_perform_write_uses_corrected_group_id_format`
   (only on Path B1): construct an episode, schedule write with
   `group_ids=["student_lilymay"]`, assert the call to `add_episode` received
   `group_id="student_lilymay"` and `_validate_group_ids` did not raise.

2b. **New unit test** — `test_validate_group_ids_rejects_old_hyphen_form`
    (only on Path B1): assert `_validate_group_ids(["student-foo"])` raises
    `ValueError`. One-liner; pins the migration permanently in the test
    suite so a future revert to the hyphen convention is caught immediately.

**File**: `tests/integration/test_mcp_session_end_smoke.py`

3. **Expand existing smoke test** to assert that after a non-zero-turn
   `tutor_session_end`, the mock `client.add_episode` was called exactly once
   with `source_description="flush:F3:session_completed"` (or whatever
   episode_kind is canonical). This locks in the F3 dispatch path end-to-end.

4. **Optional integration test** (behind a `requires_falkordb` marker):
   real-FalkorDB roundtrip — start session, run 5 turns, end session, then
   `client.search_nodes(group_ids=[...])` returns ≥1 episode node. Skipped
   in CI by default; run-on-demand for the manual verification AC item.

**File**: `tests/unit/tutoring/test_session_end.py`

5. **No new test required** — existing tests already cover `perform_session_end`
   ordering and the `create_task_fn` indirection. The F3 *write* contract is
   tested at the helper level (above), not here, to keep responsibilities
   separated.

### Phase E — Documentation

1. Update task file's Implementation Notes with:
   - The actual error message read in Phase B
   - Which path (B1/B2/B3) was taken
   - Any caveats discovered during migration
2. If Path B1 was taken, append a note to `scripts/seed_student_model.py`'s
   docstring explaining the new convention and how to re-seed.

## 5. Estimated Effort

| Phase                                           | Estimate    |
|-------------------------------------------------|-------------|
| A (instrumentation)                             | 30 min      |
| B (confirm root cause)                          | 10 min      |
| C — Path B1 (group-id migration + re-seed)      | 2-3 hours   |
| C — Path B2 / B3                                | 1-2 hours   |
| D (regression tests)                            | 1 hour      |
| E (docs)                                        | 15 min      |
| **Total (assuming Path B1)**                    | **4-5 hours** |
| **Total (assuming Path B2/B3)**                 | **2-3 hours** |

**LOC estimate**: ~150-300 lines net (mostly mechanical string replacement on
Path B1; ~40 lines on B3).

## 6. External Dependencies

**None added.** All changes are internal — string-constant updates, a log
field, regression tests. No package additions.

## 7. Risks & Mitigations

| Risk                                                            | Severity | Mitigation                                                                                       |
|-----------------------------------------------------------------|----------|--------------------------------------------------------------------------------------------------|
| Hyphen migration breaks an unindexed call site we don't grep    | Medium   | Pre-flight `git grep -nE 'student-\|subject-\|fleet-appmilla'`; add an `_validate_group_ids` test that rejects the old form to lock the migration in |
| FalkorDB still has hyphenated data after migration              | Low      | Phase B1 re-seed deletes hyphenated nodes; one-time cost                                         |
| Phase A instrumentation reveals the cause is **not** the hyphen | Low      | Plan explicitly forks at Phase B; Path B2/B3 are scoped                                          |
| `BaseException` catch swallows `KeyboardInterrupt` / `SystemExit` | Low    | Pre-existing behaviour required by ADR-ARCH-019 (fire-and-forget); not in scope to revisit       |
| Existing `TopicConfidence` typed-entity path regresses          | Low      | That path bypasses `add_episode` entirely; touched files don't intersect                         |

## 8. Acceptance Criteria Traceback

| AC                                                                  | Phase that satisfies it             |
|---------------------------------------------------------------------|-------------------------------------|
| Root cause identified and recorded in Implementation Notes          | Phase B + Phase E                   |
| `get_episodes` returns ≥1 `session_completed` episode after end     | Phase C (path-dependent) + manual verify |
| If group_id migrated, `seed_student_model.py` is updated/re-runnable| Phase C — Path B1                   |
| Silent error handling replaced with logged warning                  | Phase A                             |
| Manual verification of fresh session round-trip                     | Phase B for confirmation, again post-fix |
| `TopicConfidence` percentage / `last_revised_at` still works        | Untouched code path; existing tests cover it |
| Unit/integration tests added for episode write path                 | Phase D                             |

## 9. Approved Decisions (Phase 2.8 Checkpoint, 2026-05-06)

1. **Path B1 pre-approved**: if Phase B confirms RediSearch hyphen as the
   cause, `--implement-only` runs straight through to migration without
   pausing again. If Phase B finds something else (B2/B3), the run still
   pauses for re-design.

2. **Migrate the full hyphen→underscore convention**: `student-`, `subject-`,
   and `fleet-appmilla` all become underscore-form
   (`student_`, `subject_`, `fleet_appmilla`). Single convention; future
   subject-scoped episode writes won't hit the same issue silently.

3. **Real-FalkorDB integration test lives in this task**, behind a
   `requires_falkordb` pytest marker. Skipped in CI; runnable on demand for
   the AC's "manual verification" requirement.

## 10. Implementation Order

```
Phase A (instrumentation)
   └─ commit: "feat(GSE-001): surface error message on graphiti_write_failed"

Phase B (manual confirm — pause for human read-out)

Phase C (fix — path-dependent)
   └─ commit: "fix(GSE-001): <path-specific description>"
       └─ B1: "fix(GSE-001): migrate group-id convention from hyphen to underscore"
       └─ B3: "fix(GSE-001): correct SessionCompletedEpisode payload shape"

Phase D (regression tests)
   └─ commit: "test(GSE-001): lock in F3 episode write path and structured-log surface"

Phase E (docs)
   └─ no commit — task file edits land with /task-complete
```

## 11. Files Touched (summary)

**Always**:
- `src/study_tutor/knowledge/async_write.py` (Phase A — log fields)
- `tests/unit/knowledge/test_async_write.py` (Phase D)
- `tests/integration/test_mcp_session_end_smoke.py` (Phase D)
- `tasks/in_progress/TASK-GSE-001-...md` (Phase E)

**Path B1 only** (additionally):
- `src/study_tutor/knowledge/student_model.py`
- `scripts/seed_student_model.py`
- Tests grepped via `git grep "student-\|subject-\|fleet-appmilla"`
