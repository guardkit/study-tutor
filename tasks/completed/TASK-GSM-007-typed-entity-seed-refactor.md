---
id: TASK-GSM-007
title: "Refactor seed_student_model.py to write typed entities directly (Path 1B — no LLM in seed write path)"
task_type: review
review_mode: design
review_depth: standard
status: review_complete
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T00:00:00Z
priority: high
complexity: 5
estimated_minutes: 180
tags:
  - seed
  - refactor
  - graphiti
  - typed-entities
  - falkordb
  - phase-1-gate-flip
  - g2-g3-unblock
  - decision-point
review_results:
  mode: design
  depth: standard
  score: 75
  findings_count: 7
  recommendations_count: 12
  decision: approve-with-revisions
  report_path: .claude/reviews/TASK-GSM-007-review-report.md
  completed_at: 2026-05-04T00:00:00Z
parent_task: TASK-GR-SEED
related:
  - TASK-GSM-001  # Pydantic entity models (consumed here)
  - TASK-GSM-002  # Episode types (TopicConfidenceUpdated/Misconception/SessionCompleted stay; SeedBaselineEpisode becomes obsolete)
  - TASK-GSM-006  # Original seed-script implementation (this supersedes its add_episode-based write path)
  - TASK-FORK-PATCH  # Graphiti fork v0.29.5-guardkit.2 already pinned in pyproject.toml
  - FEAT-FD32  # Runtime integration repair feature
context_files:
  - scripts/seed_student_model.py
  - src/study_tutor/knowledge/student_model.py
  - src/study_tutor/knowledge/async_write.py
  - src/study_tutor/knowledge/episodes.py
  - src/study_tutor/knowledge/queries.py
  - tests/unit/seeding/test_seed_student_model.py
  - docs/research/ideas/phase-1-validation.md
  - .guardkit/autobuild/TASK-GR-SEED/verify_lilymay.py
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Refactor seed_student_model.py to write typed entities directly (Path 1B)

## Why this exists

[TASK-GR-SEED](../blocked/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md) ran today (2026-05-04 14:16Z) against the freshly-pinned guardkit graphiti fork (`v0.29.5-guardkit.2`). The fork's RediSearch-dash and decorator fixes are confirmed working — writes now land in per-group FalkorDB graphs (verified via `redis-cli GRAPH.LIST` and a patched `_read_student_partition` that clones the driver per group_id). But two structural issues surfaced that are independent of the fork:

1. **Rate-limit-driven write loss.** `add_episode` on each seed write fans out 3-5 parallel LLM calls inside graphiti-core's entity-extraction step. The GB10 llama-swap config has `qwen-graphiti` at `-np 2` / `concurrencyLimit: 4`, so most concurrent calls 429 and the seed exits with `succeeded_writes=6` of 25. Bumping the GB10 to `-np 6` / `concurrencyLimit: 8` (runbook updated 2026-05-04) helps live tutor sessions but doesn't address the underlying coupling: **the seed has no business depending on an LLM endpoint at all.** The data Lilymay is seeded with is deterministic — `year_group=10`, `target_grade="7"`, three subjects, etc. — and doesn't need extraction.

2. **Untyped entities defeat `get_student_state`.** graphiti-core's `add_episode` LLM-extracts entities into generic `Entity`-labelled nodes with no structured `attributes`. Verified via `verify_lilymay.py`: every node returned has `labels: ["Entity"]` and `attributes_keys: []`. The summary text is the only place structured data lives, and it's a free-form LLM concatenation across episodes (the Lilymay node ends up with text from baseline + topic-confidence-updated + ... merged). [src/study_tutor/knowledge/queries.py:240](src/study_tutor/knowledge/queries.py#L240) `_entity_type` looks for the first non-`"Entity"` label — returns `""` — so `_build_student_state` never matches `kind == "student"` / `"subject"` / `"topicconfidence"`. Even with all 25 writes through, `get_student_state` would still return `year_group=None, subjects=[], topic_confidences=[]`.

A regex-side projection parser of the LLM-merged summaries was considered (Option 2 in the discussion). Rejected on user direction (2026-05-04): "option 2 seems like it would be problems that continually bite us in the arse". The seed should not require the live tutor session's LLM extraction path to produce evidence for AC-SEED-02/AC-SEED-03.

## Decision: Path 1B (typed-entity writes via `EntityNode.save`)

Two flavours of "typed entities" considered:

| Path | Mechanism | LLM in seed? | Determinism | Scope |
|------|-----------|--------------|-------------|-------|
| **1A** | `add_episode(..., entity_types={"Student": Student, ...})` — pass Pydantic types as schema hints; LLM still extracts but classifies into typed labels and structured attributes. | Yes | Partial (LLM may skip/mis-attribute fields) | Smaller — hint addition only |
| **1B** | Replace `add_episode` calls with `EntityNode(...).save(driver)` and `EntityEdge(...).save(driver)`. Construct each node with `labels=[<TypeName>]` and `attributes={...}` directly from the existing Pydantic models in [student_model.py](src/study_tutor/knowledge/student_model.py). | **No** | Full | Larger — write path replacement + helper API + tests |

**Selected: 1B.** Rationale (operator decision, 2026-05-04):

- Removes rate-limit dependency from the seed entirely (the GB10 `-np` bump becomes a live-session concern only).
- Removes summary-merging artefacts (each entity gets exactly the attributes we set, no LLM-driven concatenation).
- Removes determinism risk (the seed runs in ~1s instead of 30+ minutes; same input → same graph state).
- Makes [queries.py](src/study_tutor/knowledge/queries.py) `_build_student_state` projection work with no parser change — once entities have proper `labels=["Student"]` etc., the existing projection just works.
- Idempotent re-seed (AC-SEED-04) becomes trivial: typed nodes are UUID-keyed; re-running is a no-op without a separate `seeding_skipped` guard.
- Aligns with TASK-GSM-001's original Pydantic-typed entity intent.
- The "live tutor session uses `add_episode` because session content IS narrative" boundary stays clean — only the seed changes.

The CC-13 single-call-site invariant relaxes from "all `add_episode` calls go through GraphitiWriteHelper" to "all **live tutor session** `add_episode` calls go through GraphitiWriteHelper; the seed writes typed entities directly". Operator approved this scope-narrowing on 2026-05-04.

## Acceptance Criteria

### Inherits + supersedes from TASK-GR-SEED

- [ ] **AC-GSM-007-01** — `python scripts/seed_student_model.py` runs successfully against live FalkorDB at `whitestocks:6379` and persists the full Lilymay baseline. **No `add_episode` calls anywhere in [scripts/seed_student_model.py](scripts/seed_student_model.py)** (grep enforces). All 25-or-equivalent typed-entity writes succeed; 429 retries are absent from the log because no LLM endpoint is hit.
- [ ] **AC-GSM-007-02** — `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` (or its `_read_student_partition` equivalent) returns the Student entity with `labels=["Student", "Entity"]` (or just `["Student"]`, depending on graphiti-core's storage convention) **and** structured attributes including `year_group=10`, `target_grade="7"`. The current `summary` (free-form text) may stay or be omitted; the load-bearing assertion is the structured `attributes` dict.
- [ ] **AC-GSM-007-03** — `get_student_state(client, "lilymay")` returns a populated `StudentState` with `year_group=10`, `target_grade="7"`, non-empty `subjects` (English Literature + English Language), non-empty `topic_confidences` — **without any change to `_build_student_state`**. The projection should "just work" against properly-typed nodes. If a projection change IS needed, it's in scope for this task but document the why-needed.
- [ ] **AC-GSM-007-04** — Re-running the seed is byte-idempotent: `python scripts/seed_student_model.py` a second time produces no new nodes/edges in FalkorDB. UUID-keyed entities make this automatic; no `seeding_skipped` event-emit needed (though one can be kept for log-parity if cheap).
- [ ] **AC-GSM-007-05** — [docs/research/ideas/phase-1-validation.md](docs/research/ideas/phase-1-validation.md) is updated:
  - **G2** flips from "Falsified" to "Held". Evidence: `verify_lilymay.py` JSON output showing typed Student node + topic_confidences (paste the live JSON).
  - **G3** flips from "Falsified" to "Held". Evidence: `get_student_state(client, "lilymay")` returns populated `StudentState` (paste live JSON).
  - **AC-SEED-* statuses** in the existing TASK-GR-SEED status table get a "superseded by TASK-GSM-007" annotation; the AC-SEED-02 expected `year_group=11, target_grade="8"` is corrected to `year_group=10, target_grade="7"` (drift was in the doc, not the seed).
  - A new "Phase-2 ADR follow-up" entry flags the CC-13 scope-narrowing for review.
- [ ] **AC-GSM-007-06** — The 2 currently-failing seed tests in [tests/unit/seeding/test_seed_student_model.py](tests/unit/seeding/test_seed_student_model.py) (`test_seed_lilymay_fresh_run_succeeds_and_uses_seed_flush_id`, `test_seed_lilymay_returns_exit_3_when_writes_abandoned`) are rewritten or replaced. Both currently assert `flush_id="SEED"` and `add_episode`-abandonment behaviour, neither of which apply under typed-entity writes. Replacement assertions: typed-entity writes succeed against a mock driver; idempotency (re-run is no-op) holds.
- [ ] **AC-GSM-007-07** — The full test suite passes at the same baseline or better than today (`723 pass / 4 fail / 2 skip` post-fork-pin). The 2 seed tests should now pass under their replacements; the `test_cross_encoder_sentinel_raises_on_arbitrary_method_name` and `test_mypy_strict_accepts_structurally_conforming_rule` failures are unrelated and stay out of scope.
- [ ] **AC-GSM-007-08** — All modified files pass project-configured lint/format checks with zero errors. No new dependencies added to [pyproject.toml](pyproject.toml).

### Architectural / documentation

- [ ] **AC-GSM-007-09** — [src/study_tutor/knowledge/async_write.py](src/study_tutor/knowledge/async_write.py) docstring / module header documents the CC-13 scope narrowing: `GraphitiWriteHelper.schedule_write` is the **single call site for live tutor session `add_episode` writes**. Seed writes are a separate path. A 1-2 line note suffices; no behavioural change to `schedule_write` itself.
- [ ] **AC-GSM-007-10** — [scripts/seed_student_model.py](scripts/seed_student_model.py) module docstring is updated to describe the typed-entity write approach + cross-link to TASK-GSM-001's Pydantic models. Removes any stale references to "schedule_write with flush_id='SEED'" or `SeedBaselineEpisode`.
- [ ] **AC-GSM-007-11** — [src/study_tutor/knowledge/episodes.py](src/study_tutor/knowledge/episodes.py) — `SeedBaselineEpisode` deletion or deprecation. If kept (for backwards-compat with mocked tests elsewhere), add a deprecation docstring noting it's no longer used by the seed. Otherwise delete and update imports.

## Test Requirements

- Unit tests in [tests/unit/seeding/test_seed_student_model.py](tests/unit/seeding/test_seed_student_model.py) — rewritten as per AC-GSM-007-06 to assert typed-entity writes against a mock driver. Idempotency assertion via second-run-no-op.
- Integration smoke (the live re-run + `verify_lilymay.py`) is the AC-level verification — no new automated harness needed beyond what TASK-GR-SEED already specs.
- `tests/integration/test_lilymay_seed_seam.py` (the seam test pinning the runtime contract) — review for compatibility; the seed-script-uses-wired-client assertion should still hold (the client just isn't *used* for seed writes).

## Implementation Notes

### Write API surface

graphiti-core 0.29 exposes:
- `EntityNode(name=..., labels=[...], group_id=..., attributes={...}).save(driver)` — single-node persist
- `EntityEdge(source_node_uuid=..., target_node_uuid=..., name=..., fact=..., group_id=..., attributes={...}).save(driver)` — single-edge persist
- `Graphiti.add_triplet(source_node, edge, target_node)` — convenience for source→edge→target trios

For the seed, `EntityNode.save` + `EntityEdge.save` is the primitive. `add_triplet` is convenient where there's a natural triplet (e.g. Student→ENROLLED_IN→Subject); for standalone entities (the Student baseline, individual Subject baselines), direct `save` is cleaner.

### Driver-clone-per-group reminder

The fork's bug #8 fix isolates each group into its own FalkorDB named graph. The seed needs to clone the driver per group_id BEFORE calling `.save()`:

```python
from graphiti_core.driver.driver import GraphProvider

if driver.provider == GraphProvider.FALKORDB:
    target = driver.clone(database=group_id)
else:
    target = driver

await EntityNode(...).save(target)
```

This mirrors what the writer-side `handle_multiple_group_ids` decorator does for `add_episode`-routed writes. Same pattern in [.guardkit/autobuild/TASK-GR-SEED/verify_lilymay.py](.guardkit/autobuild/TASK-GR-SEED/verify_lilymay.py) — already updated 2026-05-04 to use `_read_student_partition` which handles cloning.

### Idempotency strategy

UUID-keyed entities give automatic idempotency: reuse the same UUID across runs (derive deterministically from `(group_id, label, name)`) and `save()` becomes an upsert. graphiti-core's `EntityNode.save` already MERGEs by uuid in the FalkorDB driver. Concretely:

```python
import uuid
def deterministic_uuid(group_id: str, label: str, name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_OID, f"{group_id}:{label}:{name}"))
```

This makes AC-GSM-007-04 trivially pass — second run produces identical UUIDs which MERGE no-op.

### Wave / sub-task structure (suggested for /task-work)

If `/task-work` decomposes this, a natural order:
1. Helper extraction (driver-clone-per-group + deterministic-uuid as small testable utilities)
2. Replace `_seed_student` with typed-entity write + verify against mock driver
3. Replace remaining `_seed_*` functions one by one (subjects, texts, topics, AOs, misconceptions, confidences)
4. Replace edge writes (Student→ENROLLED_IN→Subject, Topic→ASSESSES→AO, Student→HAS_CONFIDENCE→TopicConfidence per TASK-GSM-001)
5. Test rewrite + lint pass
6. Live re-seed + `verify_lilymay.py` capture + phase-1-validation.md update

### What stays unchanged

- [pyproject.toml](pyproject.toml) — fork pin already in place at `v0.29.5-guardkit.2[falkordb]`. No version change needed.
- [src/study_tutor/knowledge/queries.py](src/study_tutor/knowledge/queries.py) `_read_student_partition` — already patched today (2026-05-04) to clone driver per group_id on FalkorDB. Tests still green.
- [src/study_tutor/knowledge/async_write.py](src/study_tutor/knowledge/async_write.py) `GraphitiWriteHelper.schedule_write` — keeps current behaviour; only docstring scope-narrowing.
- The live tutor session write path — completely unchanged. `record_session_completion` still uses `schedule_write` with `add_episode` underneath.

## Cross-references

- **Parent task (blocked, this unblocks)**: [TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md](../blocked/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md)
- **Validation gate**: [docs/research/ideas/phase-1-validation.md](../../docs/research/ideas/phase-1-validation.md) §"Wave 4 retry" — the original problem capture; this task is the "code-level fix" R-WAVE5-03 mentioned needing.
- **Fork patch**: [TASK-FORK-PATCH](https://github.com/guardkit/graphiti/blob/guardkit-fixes-0.29/tasks/backlog/TASK-FORK-PATCH-apply-appmilla-bug-fix-patches.md) (in the fork repo) — already shipped at tag `v0.29.5-guardkit.2`.
- **Pydantic models** (consumed): [src/study_tutor/knowledge/student_model.py](../../src/study_tutor/knowledge/student_model.py) — `Student`, `Subject`, `Text`, `Topic`, `AssessmentObjective`, `Misconception`, `TopicConfidence`.
- **TASK-GSM-006** (superseded write path): [tasks/backlog/TASK-GSM-006-seeding-script.md](TASK-GSM-006-seeding-script.md) — original seed-script implementation. Kept in backlog as historical-spec-reference.
- **GB10 concurrency runbook update** (2026-05-04, related but separate): `guardkit/docs/research/dgx-spark/RUNBOOK-v3-production-deployment.md` `qwen-graphiti` entry now `-np 6` / `concurrencyLimit: 8`. **Independent of this task** — helps live tutor sessions, not the seed.

## Notes

- This is a `task_type: review` task per operator direction (2026-05-04). The design analysis (Option 1A vs 1B) was conducted in conversation; this file captures it for the audit trail. `/task-review TASK-GSM-007 --mode=design --depth=standard` will produce the structured findings/decision report under `.claude/reviews/TASK-GSM-007-report.md` and (assuming `[I]mplement`) spawn the implementation feature/task. The implementation itself goes via `/task-work` once the review is approved.
- DDD South West (mid-May) and Kaggle hackathon are the demo-timeline pressure. This refactor is on the critical path for both. Estimated 2-3 hours focused work; if it grows past 4 hours, reassess scope rather than push through.
