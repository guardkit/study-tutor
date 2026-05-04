---
id: TASK-GSM-009
title: "Refactor seed_student_model.py to write typed entities directly (Path 1B implementation, post-ADR-ARCH-021)"
task_type: implementation
status: backlog
created: 2026-05-04T12:00:00Z
updated: 2026-05-04T12:00:00Z
priority: high
complexity: 5
estimated_minutes: 240
tags:
  - seed
  - refactor
  - graphiti
  - typed-entities
  - falkordb
  - phase-1-gate-flip
  - g2-g3-unblock
parent_task: TASK-GR-SEED
parent_review: TASK-GSM-007
parent_decision: TASK-GSM-008
related:
  - TASK-GSM-001  # Pydantic entity models (consumed here)
  - TASK-GSM-002  # Episode types (TopicConfidenceUpdated/Misconception/SessionCompleted stay; SeedBaselineEpisode deleted under R10)
  - TASK-GSM-006  # Original seed-script implementation (this supersedes its add_episode-based write path)
  - TASK-GSM-007  # Accepted-with-revisions design review (in completed/)
  - TASK-GSM-008  # Design-resolution task that produced ADR-ARCH-021
  - TASK-FORK-PATCH  # Graphiti fork v0.29.5-guardkit.2 already pinned in pyproject.toml
  - FEAT-FD32  # Runtime integration repair feature
context_files:
  - docs/architecture/decisions/ADR-ARCH-021-typed-entity-seed-design-resolutions.md
  - .claude/reviews/TASK-GSM-007-review-report.md
  - tasks/completed/TASK-GSM-007-typed-entity-seed-refactor.md
  - scripts/seed_student_model.py
  - scripts/probes/probe_cross_group_edges.py
  - src/study_tutor/knowledge/student_model.py
  - src/study_tutor/knowledge/async_write.py
  - src/study_tutor/knowledge/episodes.py
  - src/study_tutor/knowledge/queries.py
  - tests/unit/seeding/test_seed_student_model.py
  - tests/integration/test_lilymay_seed_seam.py
  - docs/research/ideas/phase-1-validation.md
  - .guardkit/autobuild/TASK-GR-SEED/verify_lilymay.py
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Refactor seed_student_model.py to write typed entities directly (Path 1B)

## Why this exists

The TASK-GSM-007 design review (2026-05-04, [report](../../.claude/reviews/TASK-GSM-007-review-report.md)) approved Path 1B (typed-entity writes via `EntityNode.save` / `EntityEdge.save`) over Path 1A (`add_episode` with entity-type hints) for the Lilymay seed, but flagged three load-bearing under-specifications (G1 read-scope, G2 cross-group edges, G3 TopicConfidence baseline). TASK-GSM-008 resolved them and produced [ADR-ARCH-021](../../docs/architecture/decisions/ADR-ARCH-021-typed-entity-seed-design-resolutions.md):

- **G1 → denormalise** `enrolled_subjects: list[str]` onto the Student node. Subject nodes still live under `subject-<slug>` for curriculum-level structure, but `_build_student_state` populates `state.subjects` from the Student node's attribute, not via cross-group edge traversal.
- **G2 → defer** all cross-group edges. The probe (`scripts/probes/probe_cross_group_edges.py`, run 2026-05-04) confirmed silent-dangle behaviour: `EntityEdge.save()` returns ok but the persisted state is unreadable via the typed API and invisible to Cypher traversal. The seed writes only intra-group edges (`Student → HAS_CONFIDENCE → TopicConfidence` within `student-<id>`).
- **G3 → epoch sentinel** `EPOCH_NEVER_REVISED: Final[datetime] = datetime(1970, 1, 1, tzinfo=timezone.utc)` added to `student_model.py` and used as `last_revised_at` for every baseline `TopicConfidence`. Zero schema change, zero `planner/rules.py` changes, zero existing test-fixture migration.

This task implements those resolutions plus the original review's R4-R12 polish recommendations. The original TASK-GSM-007 stays in `tasks/completed/` as the design-review historical record (operator chose option β in TASK-GSM-008's §"Naming for the refreshed implementation task").

## Decision context (from ADR-ARCH-021)

- LLM removed from the seed write path entirely. The seed runs in ~1s instead of 30+ minutes; same input → same graph state.
- The CC-13 single-call-site invariant (ADR-ARCH-019) narrows from "all `add_episode` calls go through `GraphitiWriteHelper`" to "all **live tutor session** `add_episode` calls go through `GraphitiWriteHelper`; the seed writes typed entities directly". Documented in `async_write.py` per AC-09.
- Group-id discipline carries forward: `student-<id>` for student-scoped (Student node + TopicConfidence), `subject-<slug>` for curriculum-scoped (Subject + Text + Topic), `fleet-appmilla` for cross-fleet AOs.

## Acceptance Criteria

### Inherits + supersedes from TASK-GSM-007 (R1-R3 resolved per ADR-ARCH-021)

- [ ] **AC-GSM-009-01** — `python scripts/seed_student_model.py` runs successfully against live FalkorDB at `whitestocks:6379` and persists the full Lilymay baseline. **No `add_episode` calls anywhere in [scripts/seed_student_model.py](../../scripts/seed_student_model.py)** (grep enforces). All typed-entity writes succeed; 429 retries are absent from the log because no LLM endpoint is hit.

- [ ] **AC-GSM-009-02** — `mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"])` (or its `_read_student_partition` equivalent) returns the Student entity with `labels` including `"Student"` (graphiti-core may also include `"Entity"`) and structured attributes including `year_group=10`, `target_grade="7"`, **and** `enrolled_subjects=["English Literature", "English Language"]` (the G1 denormalisation). The current `summary` field may be omitted; the load-bearing assertion is the structured `attributes` dict.

- [ ] **AC-GSM-009-03** — `get_student_state(client, "lilymay")` returns a populated `StudentState` with `year_group=10`, `target_grade="7"`, **non-empty `subjects` derived from the Student node's `enrolled_subjects` attribute** (per ADR-ARCH-021 §G1), and **non-empty `topic_confidences`** read from TopicConfidence nodes within the `student-<id>` partition. The projection in `_build_student_state` may need a small addition to read the `enrolled_subjects` attribute off the Student node — that change is in scope and documented in the implementation. Texts/Topics/AOs population in `StudentState` is not required (deferred per ADR-ARCH-021).

- [ ] **AC-GSM-009-04** — Re-running the seed is byte-idempotent: `python scripts/seed_student_model.py` a second time produces no new nodes/edges in FalkorDB. UUID-keyed entities make this automatic via per-class deterministic UUID derivation (per AC-13). No `seeding_skipped` event-emit needed, though one can be kept for log-parity if cheap. **Live evidence (R12)**: `verify_lilymay.py` (or a sister snippet documented inline) captures `MATCH (n) RETURN count(n)` (or per-group equivalent) before and after the second run; counts must be identical.

- [ ] **AC-GSM-009-05** — [docs/research/ideas/phase-1-validation.md](../../docs/research/ideas/phase-1-validation.md) is updated:
  - **G2** flips from "Falsified" to "Held with caveat". Evidence: `verify_lilymay.py` JSON output showing typed Student node with `enrolled_subjects` attribute + populated TopicConfidence nodes (paste the live JSON). Caveat: documents that cross-group edges are *not* exercised by the Phase-1 seed (per ADR-ARCH-021 §G2 deferral).
  - **G3** flips from "Falsified" to "Held". Evidence: `get_student_state(client, "lilymay")` returns populated `StudentState` with the planner immediately producing recommendations on day 1 (paste live JSON; reference `recommend_planner_topics` output).
  - **AC-SEED-* statuses** in the existing TASK-GR-SEED status table get a "superseded by TASK-GSM-009" annotation; the AC-SEED-02 expected `year_group=11, target_grade="8"` is corrected to `year_group=10, target_grade="7"` (drift was in the doc, not the seed).
  - A new entry references ADR-ARCH-021 for the design rationale and links to the G2 probe outcome.

- [ ] **AC-GSM-009-06** (R6 expanded) — **All unit tests in [tests/unit/seeding/test_seed_student_model.py](../../tests/unit/seeding/test_seed_student_model.py)** are rewritten to use a `_FakeDriver` fixture that records `EntityNode.save` / `EntityEdge.save` calls instead of `helper.schedule_write` / `helper.drain` calls. The current ~30 references to `helper.calls`, `helper.drain_call_count`, `_FakeHelper`, and `schedule_write` are replaced with assertions over the typed-write surface. Replacement assertions cover: typed-entity writes succeed against the mock driver, every Student/Subject/Text/Topic/AO/TopicConfidence is written with its expected `labels` and `attributes`, idempotency holds (second-run produces identical UUIDs / no new save calls), and the seed exits with the documented exit codes under each failure mode.

- [ ] **AC-GSM-009-07** — The full test suite passes at the same baseline or better than today. The 2 currently-failing seed tests pass under their replacements; the unrelated `test_cross_encoder_sentinel_raises_on_arbitrary_method_name` and `test_mypy_strict_accepts_structurally_conforming_rule` failures stay out of scope.

- [ ] **AC-GSM-009-08** — All modified files pass project-configured lint/format checks with zero errors. No new dependencies added to [pyproject.toml](../../pyproject.toml) — `graphiti-core[falkordb]` (already pinned at the fork tag) provides `EntityNode`, `EntityEdge`, and `GraphProvider.FALKORDB`.

### Architectural / documentation

- [ ] **AC-GSM-009-09** — [src/study_tutor/knowledge/async_write.py](../../src/study_tutor/knowledge/async_write.py) docstring / module header documents the CC-13 scope narrowing: `GraphitiWriteHelper.schedule_write` is the **single call site for live tutor session `add_episode` writes**. Seed writes are a separate path. A 1-2 line note suffices; no behavioural change to `schedule_write` itself. Cross-link to ADR-ARCH-019 + ADR-ARCH-021.

- [ ] **AC-GSM-009-10** — [scripts/seed_student_model.py](../../scripts/seed_student_model.py) module docstring is updated to describe the typed-entity write approach + cross-link to TASK-GSM-001's Pydantic models and ADR-ARCH-021. Removes any stale references to `schedule_write`, `flush_id="SEED"`, or `SeedBaselineEpisode`.

- [ ] **AC-GSM-009-11** (R10) — [src/study_tutor/knowledge/episodes.py](../../src/study_tutor/knowledge/episodes.py) — `SeedBaselineEpisode` is **deleted** (not deprecated). The two failing seed tests being rewritten under AC-06 will remove the only remaining references; no zombie code.

### R4-R12 polish (from TASK-GSM-007 review §Should-fix and §Nice-to-have)

- [ ] **AC-GSM-009-12** (R4) — Per-class UUID derivation is specified inline in a small helper module (e.g. `src/study_tutor/knowledge/seed_uuids.py` or as private helpers in `seed_student_model.py`):
  - Student / Subject / Topic / AssessmentObjective: `uuid5(NAMESPACE_OID, f"{group_id}:{label}:{name}")` (entities with stable `name`).
  - Text: `uuid5(NAMESPACE_OID, f"{group_id}:Text:{subject_slug}:{name}")` (Text names may collide across subjects; subject_slug disambiguates).
  - TopicConfidence: `uuid5(NAMESPACE_OID, f"{group_id}:TopicConfidence:{student_ref}:{topic_ref}")` (no `name` field; identity is `student_ref + topic_ref`).
  - Misconception: `uuid5(NAMESPACE_OID, f"{group_id}:Misconception:{topic_ref}:{observed_at_iso}")` — not seeded in Phase 1 baseline but the helper is in place for future use.
  - Edges: `uuid5(NAMESPACE_OID, f"{relationship_name}:{source_uuid}:{target_uuid}")`.
  - Each derivation has a unit test asserting (i) determinism (same inputs → same UUID across runs) and (ii) collision-freedom across the entity types we seed today.

- [ ] **AC-GSM-009-13** (R5) — A smoke test verifies `EntityNode.save` is MERGE-by-uuid in the FalkorDB driver: write a node twice with the same UUID, assert `MATCH (n {uuid: $u}) RETURN count(n)` returns 1 (not 2). Pins fork behaviour against possible drift. Lives in `tests/integration/test_typed_entity_writes.py` (new file) and is gated on FalkorDB being reachable (skip-if-unreachable, mirroring `test_lilymay_seed_seam.py` conventions).

- [ ] **AC-GSM-009-14** (R7 / AC-GSM-008-05) — [tests/integration/test_lilymay_seed_seam.py](../../tests/integration/test_lilymay_seed_seam.py) drift fix: `year_group=11 → 10`, `target_grade="8" → "7"`. Two-line change. Pre-existed TASK-GSM-007 but surfaces under Path 1B because the seed will actually populate these fields end-to-end.

- [ ] **AC-GSM-009-15** (R8) — The seed uses the relationship constants from [src/study_tutor/knowledge/student_model.py](../../src/study_tutor/knowledge/student_model.py) (`HAS_CONFIDENCE`, `STUDIES`, `WORKING_ON`, `HAS_TEXT`, `COVERS`, `ASSESSED_BY`) — never bare string literals like `"ENROLLED_IN"`. Note: per ADR-ARCH-021 §G2, only intra-group edges are written, so `STUDIES` / `WORKING_ON` (which would be cross-group) are *not* used by the Phase-1 seed; they remain available in `student_model.py` for future use.

- [ ] **AC-GSM-009-16** (R9) — `seed_lilymay(client, helper)` signature drops the `helper` parameter — it becomes vestigial under typed-entity writes (every write goes through `EntityNode.save(driver)` directly). `main()` and the unit tests are updated. The post-finally drain is removed (no helper to drain). One-line signature change + cascading callsite updates.

- [ ] **AC-GSM-009-17** (R11) — Structured-log event types are audited and pruned:
  - **KEEP**: `seeding_failed`, `seeding_skipped`, `seeding_completed`, `seeding_verification_warning`, `seeding_failed_unhandled` (operationally meaningful regardless of write strategy).
  - **DROP**: `seeding_pending_writes_abandoned`, `seeding_batch_drained`, `seeding_batch_drain_env_invalid` (no batching, no abandonment under typed-entity writes — `EntityNode.save` is sequential and synchronous-like).
  - **ADD**: `seeding_node_written` per node at debug level, structured with `entity_kind`, `name`, `group_id`, `uuid`, so post-mortem diagnosis is possible without a graph dump.
  - The log-shape contract is documented in the seed-module docstring under "Exit-code contract".
  - Update existing exit-code-3 (`EXIT_PENDING_WRITES_ABANDONED`) — under typed-entity writes there's no abandonment surface; either repurpose the exit code (e.g. for "verification-gate failed-hard") or remove it cleanly. Recommend remove; document the contract change in the seed-module docstring.

## Implementation Notes

### Add the EPOCH_NEVER_REVISED constant

Per ADR-ARCH-021 §G3, in [src/study_tutor/knowledge/student_model.py](../../src/study_tutor/knowledge/student_model.py):

```python
from datetime import datetime, timezone
from typing import Final

#: Sentinel timestamp for ``TopicConfidence.last_revised_at`` baseline writes.
#:
#: A baseline TopicConfidence has, by construction, never been revised — but
#: the field is non-Optional and the planner cooldown logic compares it
#: against ``now()``. Writing ``now()`` would put every baseline topic inside
#: the 24h cooldown and break AC-GSM-009-03 (planner has bands to plan
#: against day 1). The far-past sentinel keeps the topic comfortably outside
#: the 48h stale-bonus boundary forever (until a real revision overwrites
#: this value with the actual revised-at timestamp).
#:
#: Anyone reading ``last_revised_at = 1970-01-01`` in raw graph queries
#: should follow this constant back to ADR-ARCH-021 §G3.
EPOCH_NEVER_REVISED: Final[datetime] = datetime(1970, 1, 1, tzinfo=timezone.utc)
```

Export it from `__all__`. The seed writer imports and uses it as the `last_revised_at` argument for every baseline `TopicConfidence`. **No change to the `TopicConfidence` field definition itself.**

### G1 denormalisation: `enrolled_subjects` on the Student node

In [scripts/seed_student_model.py](../../scripts/seed_student_model.py), the Student-node `EntityNode.save(...)` call carries:

```python
attributes={
    "year_group": STUDENT_YEAR_GROUP,
    "target_grade": STUDENT_TARGET_GRADE,
    "enrolled_subjects": [s["name"] for s in SUBJECTS],
    # other Student fields...
}
```

In [src/study_tutor/knowledge/queries.py](../../src/study_tutor/knowledge/queries.py) `_build_student_state`, where `kind == "student"` is matched (around line 322), add a single line:

```python
elif kind == "student":
    # ... existing year_group / target_grade extraction ...
    enrolled = _attr(attrs, "enrolled_subjects", _attr(node, "enrolled_subjects"))
    if isinstance(enrolled, list):
        state.subjects.extend(str(s) for s in enrolled)
```

This is the only projection-side change. The existing `kind == "subject"` branch (which currently runs against an empty source set under `student-<id>`) stays in place as a no-op for now — it will trigger naturally if a future task multi-group-reads Subject nodes from `subject-<slug>`.

### G2: only intra-group edges

Edges to write under Path 1B in this task:

| Edge | Source group | Target group | Written under | Status |
|------|--------------|--------------|---------------|--------|
| `Student → HAS_CONFIDENCE → TopicConfidence` | `student-lilymay` | `student-lilymay` | `student-lilymay` | ✅ Intra-group, write |
| `Subject → COVERS → Topic` | `subject-<slug>` | `subject-<slug>` | `subject-<slug>` | ✅ Intra-group, write |
| `Topic → ASSESSED_BY → AO` | `subject-<slug>` | `fleet-appmilla` | n/a | ❌ Cross-group, defer per ADR-ARCH-021 §G2 |
| `Subject → HAS_TEXT → Text` | `subject-<slug>` | `subject-<slug>` | `subject-<slug>` | ✅ Intra-group, write |
| `Student → STUDIES → Subject` | `student-lilymay` | `subject-<slug>` | n/a | ❌ Cross-group, defer (denormalised via `enrolled_subjects`) |
| `Student → WORKING_ON → Text` | `student-lilymay` | `subject-<slug>` | n/a | ❌ Cross-group, defer |

The two intra-group edge writes (`HAS_CONFIDENCE`, `COVERS`, `HAS_TEXT`) are sufficient for AC-GSM-009-03 (`get_student_state` returns populated `topic_confidences`). The `ASSESSED_BY` Topic→AO link is documented in the Topic node's `attributes={"ao_refs": [...]}` instead — a denormalisation that mirrors G1 for AO references and avoids the cross-group edge restriction.

### Wave / sub-task structure (suggested for /task-work)

If `/task-work` decomposes this:

1. Add `EPOCH_NEVER_REVISED` constant + per-class UUID derivation helpers + their unit tests.
2. Update `_build_student_state` projection for `enrolled_subjects` denormalisation.
3. Replace `_seed_student` with typed-entity write (carrying `enrolled_subjects` attribute) + verify against mock driver.
4. Replace remaining `_seed_*` functions one by one (subjects, texts, topics, AOs, topic-confidences).
5. Replace edge writes (intra-group only — `HAS_CONFIDENCE`, `COVERS`, `HAS_TEXT`).
6. Drop `helper` parameter from `seed_lilymay`; update `main()`.
7. Audit + prune structured-log events.
8. Delete `SeedBaselineEpisode`.
9. Test rewrite (full unit-test surface) + lint pass.
10. Add `tests/integration/test_typed_entity_writes.py` MERGE-by-uuid smoke test.
11. Fix `tests/integration/test_lilymay_seed_seam.py` drift (year_group, target_grade).
12. Live re-seed + `verify_lilymay.py` capture + phase-1-validation.md update + second-run idempotency evidence.

### What stays unchanged

- [pyproject.toml](../../pyproject.toml) — fork pin already in place at `v0.29.5-guardkit.2[falkordb]`. No version change needed.
- [src/study_tutor/knowledge/queries.py](../../src/study_tutor/knowledge/queries.py) `_read_student_partition` — already patched (2026-05-04) to clone driver per group_id on FalkorDB.
- [src/study_tutor/knowledge/async_write.py](../../src/study_tutor/knowledge/async_write.py) `GraphitiWriteHelper.schedule_write` — keeps current behaviour; only docstring scope-narrowing.
- [src/study_tutor/knowledge/student_model.py](../../src/study_tutor/knowledge/student_model.py) `TopicConfidence` field signature — unchanged. Only the `EPOCH_NEVER_REVISED` constant is added.
- [src/study_tutor/planner/rules.py](../../src/study_tutor/planner/rules.py) — unchanged (epoch is a valid `datetime`; sort + arithmetic both work natively).
- [src/study_tutor/planner/pipeline.py](../../src/study_tutor/planner/pipeline.py) `_project_topic_confidence` — unchanged (epoch is not `None`, so the existing `fallback_clock()` branch isn't triggered).
- The live tutor session write path — completely unchanged. `record_session_completion` still uses `schedule_write` with `add_episode` underneath.

## Cross-references

- **ADR**: [docs/architecture/decisions/ADR-ARCH-021-typed-entity-seed-design-resolutions.md](../../docs/architecture/decisions/ADR-ARCH-021-typed-entity-seed-design-resolutions.md)
- **G2 probe** (one-shot, retain in repo for ADR auditability): [scripts/probes/probe_cross_group_edges.py](../../scripts/probes/probe_cross_group_edges.py)
- **Original review**: [.claude/reviews/TASK-GSM-007-review-report.md](../../.claude/reviews/TASK-GSM-007-review-report.md) (R1-R12 origin)
- **Source design task** (in completed/): [tasks/completed/TASK-GSM-007-typed-entity-seed-refactor.md](../completed/TASK-GSM-007-typed-entity-seed-refactor.md)
- **Design-resolution task** (this task's parent): [tasks/in_progress/TASK-GSM-008-resolve-typed-entity-design-gaps.md](../in_progress/TASK-GSM-008-resolve-typed-entity-design-gaps.md)
- **Parent task (blocked)**: [TASK-GR-SEED](../blocked/TASK-GR-SEED-reseed-lilymay-and-flip-phase-1-gate.md)
- **Validation gate**: [docs/research/ideas/phase-1-validation.md](../../docs/research/ideas/phase-1-validation.md)
- **Pydantic models** (consumed): [src/study_tutor/knowledge/student_model.py](../../src/study_tutor/knowledge/student_model.py)

## Notes

- DDD South West (mid-May) and Kaggle hackathon are the demo-timeline pressure. Estimated 4 hours focused work (the test-rewrite scope expansion under AC-06 / R6 is the largest single delta vs the original TASK-GSM-007 estimate). If it grows past 6 hours, reassess scope rather than push through.
- Cross-group edges remain unimplemented after this task. If a future feature needs `Student → STUDIES → Subject` traversal (e.g. cross-learner curriculum recommendation), the choice will be: (i) wait for upstream graphiti-core support, (ii) extend the denormalisation pattern (more attributes on the Student node), or (iii) parallel-write the Subject node into `student-<id>` too. ADR-ARCH-021 documents this as future-work.
