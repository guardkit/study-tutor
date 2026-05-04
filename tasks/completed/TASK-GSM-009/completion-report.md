# TASK-GSM-009 — Completion Report

**Task**: Refactor `seed_student_model.py` to write typed entities directly (Path 1B implementation, post-ADR-ARCH-021)
**Completed**: 2026-05-04T21:40:00Z
**Duration**: ~3.5 hours focused work (estimated 240 min — within budget)
**Complexity**: 5/10
**Workflow mode**: STANDARD, driven directly in main thread (no sub-agent delegation)

## Outcome

All 17 acceptance criteria satisfied with live evidence captured against
the canonical Phase-1 stack (whitestocks FalkorDB at `whitestocks:6379`,
guardkit graphiti-core fork at `v0.29.5-guardkit.2`).

The Lilymay baseline now persists end-to-end via typed-entity writes
(`EntityNode.save` / `EntityEdge.save`), with no LLM in the seed write
path. Re-runs are byte-idempotent via deterministic UUID5 derivation.
The Phase-1 G2 and G3 validation gates flip (G2 to "Held with caveat",
G3 to "Held").

## Acceptance criteria status

| AC | Status | Evidence |
|---|---|---|
| AC-01 (no `add_episode` in seed) | ✅ | AST scan in `tests/unit/seeding/test_seed_student_model.py::test_seed_script_has_no_add_episode_calls` + `test_seam_seeding_script.py::test_seed_writes_via_typed_entity_save` |
| AC-02 (Student readable + `enrolled_subjects`) | ✅ | Live JSON evidence shows Student node with `labels=["Entity", "Student"]`, `attributes_keys` includes `enrolled_subjects`, `year_group=10`, `target_grade="7"` |
| AC-03 (`get_student_state` populated) | ✅ | Live state: `subjects=["English Literature", "English Language"]`, 6 `topic_confidences` spanning all three planner bands |
| AC-04 (idempotency) | ✅ | Pre/post second-run counts identical: 25 nodes, 16 edges in both snapshots; second run hits `seeding_skipped` pre-flight gate |
| AC-05 (phase-1-validation update) | ✅ | New "TASK-GSM-009" section appended to `docs/research/ideas/phase-1-validation.md` with G2/G3 flips, AC-SEED-* superseded table, and live JSON excerpts |
| AC-06 (test rewrite ~30 refs → `_FakeDriver`) | ✅ | `tests/unit/seeding/test_seed_student_model.py` rewritten end-to-end against `EntityNode.save` / `EntityEdge.save` interception |
| AC-07 (test suite at baseline) | ✅ | 765 passing, 1 skipped (live seam), 2 failing — both pre-existing, explicitly named out-of-scope: `test_cross_encoder_sentinel_raises_on_arbitrary_method_name`, `test_mypy_strict_accepts_structurally_conforming_rule` |
| AC-08 (lint/format) | ✅ | `py_compile` + import smoke pass on every modified module; no project-configured ruff/black/mypy beyond pytest |
| AC-09 (CC-13 narrowing in `async_write.py`) | ✅ | Module docstring updated with explicit narrowing language and ADR-ARCH-021 cross-link |
| AC-10 (seed module docstring rewrite) | ✅ | Full rewrite cross-linking ADR-ARCH-021 + TASK-GSM-001; no stale `schedule_write` / `flush_id="SEED"` / `SeedBaselineEpisode` references |
| AC-11 (`SeedBaselineEpisode` deleted) | ✅ | Class + `seed_baseline` `EpisodeKind` literal removed from `episodes.py`; `tests/unit/knowledge/test_episodes.py` 46/46 still green |
| AC-12 (per-class UUID derivation + tests) | ✅ | New `src/study_tutor/knowledge/seed_uuids.py` + `tests/unit/knowledge/test_seed_uuids.py` (24 tests covering determinism + collision-freedom) |
| AC-13 (MERGE-by-uuid smoke test) | ✅ | New `tests/integration/test_typed_entity_writes.py` (skip-if-unreachable, gated on `STUDY_TUTOR_LIVE_GRAPHITI_SMOKE`) |
| AC-14 (seam-test drift fix) | ✅ | `tests/integration/test_lilymay_seed_seam.py`: `year_group=11→10`, `target_grade="8"→"7"`; docstring updated |
| AC-15 (relationship constants, no bare strings) | ✅ | Seed uses `HAS_CONFIDENCE`, `HAS_TEXT`, `COVERS` from `student_model`; `STUDIES`/`WORKING_ON`/`ASSESSED_BY` correctly unused (cross-group, deferred per §G2) |
| AC-16 (drop `helper` from `seed_lilymay`) | ✅ | Signature is now `seed_lilymay(client)` only; `main()` and unit tests updated |
| AC-17 (log event audit) | ✅ | Dropped: `seeding_pending_writes_abandoned`, `seeding_batch_drained`, `seeding_batch_drain_env_invalid`. Added: `seeding_node_written`, `seeding_edge_written` (debug). Removed: `EXIT_PENDING_WRITES_ABANDONED` (no abandonment surface under sequential typed writes). Module docstring updated. |

## Files changed

### Source
- **New**: `src/study_tutor/knowledge/seed_uuids.py` — deterministic UUID5 helpers (Student / Subject / Text / Topic / AO / TopicConfidence / Misconception / edge)
- `src/study_tutor/knowledge/student_model.py` — added `EPOCH_NEVER_REVISED: Final[datetime]` constant + export
- `src/study_tutor/knowledge/queries.py` — `_build_student_state` reads `enrolled_subjects` off Student node attributes (G1 denormalisation)
- `src/study_tutor/knowledge/episodes.py` — deleted `SeedBaselineEpisode` class + `seed_baseline` `EpisodeKind` literal
- `src/study_tutor/knowledge/async_write.py` — module docstring narrows CC-13 to live tutor sessions only; cross-links ADR-ARCH-021
- `scripts/seed_student_model.py` — full rewrite to typed-entity writes; new docstring; `seed_lilymay(client)` signature; pruned log events; removed `EXIT_PENDING_WRITES_ABANDONED`

### Tests
- **New**: `tests/unit/knowledge/test_seed_uuids.py` — 24 tests (determinism, collision-freedom, full Phase-1 surface)
- **New**: `tests/integration/test_typed_entity_writes.py` — MERGE-by-uuid smoke (AC-13, gated)
- `tests/unit/knowledge/test_student_model.py` — added `EPOCH_NEVER_REVISED` import + 3 new tests (epoch shape, TopicConfidence acceptance, planner-cooldown sanity)
- `tests/unit/knowledge/test_queries.py` — added 3 tests for `enrolled_subjects` projection (happy path, missing attribute, malformed value)
- `tests/unit/seeding/test_seed_student_model.py` — full rewrite against `_FakeDriver` + save-recorder fixture (39 tests)
- `tests/unit/seeding/test_seam_seeding_script.py` — rewrote contracts: `EntityNode.save`/`EntityEdge.save` AST checks + zero `add_episode` / `schedule_write` guards + `seed_uuids` import check
- `tests/integration/test_lilymay_seed_seam.py` — drift fix (year_group, target_grade) + docstring

### Docs
- `docs/research/ideas/phase-1-validation.md` — added "TASK-GSM-009 — Typed-entity seed landed" section with G2/G3 flips, AC-SEED-* superseded table, live evidence excerpts

### Evidence captured (live)
- `.guardkit/autobuild/TASK-GR-SEED/logs/TASK-GSM-009_live_evidence.json` — full per-AC evidence dump (state, partition counts, planner recommendations)
- `.guardkit/autobuild/TASK-GR-SEED/logs/verify_lilymay_TASK-GSM-009_run1.json` — `verify_lilymay.py` output post-seed

## Live persistence summary

| Partition | Nodes | Edges | Edge types |
|---|---|---|---|
| `student-lilymay` | 7 | 6 | HAS_CONFIDENCE |
| `subject-english-literature` | 10 | 9 | COVERS, HAS_TEXT |
| `subject-english-language` | 2 | 1 | COVERS |
| `fleet-appmilla` | 6 | 0 | (cross-group ASSESSED_BY deferred per §G2) |
| **Total** | **25** | **16** | |

Per-class breakdown: 1 Student + 2 Subject + 4 Text + 6 Topic + 6 AssessmentObjective + 6 TopicConfidence = 25 nodes, exactly matching the spec.

Day-1 planner output (G3 evidence):
1. `Power and Conflict: Ozymandias themes` — `struggling_stale` (35%)
2. `Macbeth's witches` — `struggling_stale` (25%)
3. `Lady Macbeth's ambition` — `developing_stale` (55%)

EPOCH sentinel (`1970-01-01T00:00:00+00:00`) observed on all six TopicConfidences — confirms G3 design works at runtime, not just unit-test layer.

## Known follow-ups

- **TASK-GR-SEED** is currently in `tasks/blocked/` per the prior unblocking sweep (was blocked pending TASK-GSM-009). Now that TASK-GSM-009 has shipped, GR-SEED's blocker is gone; operator decision needed on whether to close it as superseded or run a final verification under its own name.
- **R-WAVE5-04** (`Connection closed by server` from FalkorDB) reappears intermittently in shutdown logs but does **not** block successful writes — the seed completed end-to-end despite the noise. Worth investigating in a separate task if the noise becomes load-bearing.
- **Cross-group edges** remain unimplemented per ADR-ARCH-021 §G2. Future features needing `Student → STUDIES → Subject` traversal will need either (i) upstream graphiti-core fix, (ii) further denormalisation, or (iii) parallel-writing the Subject node into `student-<id>` too.

## Cross-references

- [ADR-ARCH-021](../../../docs/architecture/decisions/ADR-ARCH-021-typed-entity-seed-design-resolutions.md) — design rationale (G1/G2/G3)
- [TASK-GSM-007](../TASK-GSM-007-typed-entity-seed-refactor.md) — design review that surfaced G1/G2/G3 (kept in `completed/` as design-review historical record)
- [TASK-GSM-008](../TASK-GSM-008-resolve-typed-entity-design-gaps.md) — design-resolution task that produced ADR-ARCH-021
- [scripts/probes/probe_cross_group_edges.py](../../../scripts/probes/probe_cross_group_edges.py) — G2 probe (silent-dangle outcome)
- [.guardkit/autobuild/TASK-GR-SEED/logs/TASK-GSM-009_live_evidence.json](../../../.guardkit/autobuild/TASK-GR-SEED/logs/TASK-GSM-009_live_evidence.json) — full live-evidence JSON
