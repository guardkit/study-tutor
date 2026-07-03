# ADR-ARCH-021 — Typed-entity seed design resolutions (G1 read-scope, G2 cross-group edges, G3 TopicConfidence baseline)

## Status

Accepted

**⚠️ CC-13 retirement note (2026-07-03).** These resolutions reference the **CC-13 single-`add_episode`-call-site invariant** (see the G-scope discussion and the Positive-consequences "the CC-13 invariant … remains intact"). [ADR-ARCH-023](ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md) removes study-tutor's Graphiti / LLM-extraction path entirely — **no `add_episode` remains** — so CC-13 no longer applies. The typed-entity FalkorDB seed these decisions govern is re-platformed to Postgres (or dropped under ADR-ARCH-023 D3 "start fresh"), which moots G1/G2/G3 for the live system. This ADR stays `Accepted` as the historical design record — the G2 cross-group-edge probe remains a useful graphiti-core finding. No content rewrite below.

**Date:** 2026-05-04
**Phase:** Phase 1 (Lilymay seed prerequisite for FEAT-PH1-001)
**Related:**
[TASK-GSM-007 review report](../../../.claude/reviews/TASK-GSM-007-review-report.md) (accepted-with-revisions),
[TASK-GSM-008](../../../tasks/in_progress/TASK-GSM-008-resolve-typed-entity-design-gaps.md) (this ADR's source task),
[TASK-GSM-009](../../../tasks/backlog/TASK-GSM-009-typed-entity-seed-refactor.md) (downstream implementation task spawned from these decisions),
[ADR-ARCH-007](./ADR-ARCH-007-graphiti-split-topology.md) (group-id split topology),
[ADR-ARCH-019](./ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) (CC-13 single-call-site invariant — narrowed by these decisions)

## Context

The TASK-GSM-007 design review (2026-05-04) approved Path 1B (typed-entity writes via `EntityNode.save` / `EntityEdge.save`) over Path 1A (`add_episode` with entity-type hints) but flagged three load-bearing under-specifications that would produce a green unit test suite paired with a red live-AC outcome unless settled before implementation:

- **G1** — `get_student_state` reads only the `student-<id>` group ([queries.py:450](../../../src/study_tutor/knowledge/queries.py#L450)), but the seed writes Subjects/Texts/Topics/AOs to `subject-<slug>` and `fleet-appmilla`. AC-GSM-007-03's claim that `subjects` will be non-empty without changing `_build_student_state` is structurally false — the *fetcher* never reads those partitions.
- **G2** — The `graphiti-core` fork's bug-#8 fix (pinned at `v0.29.5-guardkit.2[falkordb]`) isolates each `group_id` into its own FalkorDB named graph. `EntityEdge` carries one `group_id`. Cross-group edge behaviour was undocumented and unverifiable from a code read alone.
- **G3** — `TopicConfidence.last_revised_at: datetime` is required ([student_model.py:311](../../../src/study_tutor/knowledge/student_model.py#L311)). The planner's cooldown logic ([rules.py:163](../../../src/study_tutor/planner/rules.py#L163), [queries.py:511](../../../src/study_tutor/knowledge/queries.py#L511)) compares this against `now - 24h` (or 48h for stale-bonus). Writing `now()` at seed time puts every topic inside cooldown immediately, breaking AC-006 (planner has bands to plan against on day 1).

Demo timeline pressure (DDD South West mid-May, Kaggle hackathon) means the resolutions must be ship-velocity-aware, not theoretically optimal.

## Decision

### G1 — Read-scope: **denormalise `enrolled_subjects: list[str]` onto the Student node**

The seed writes Subject nodes under `subject-<slug>` for curriculum-level structure (so the same Subject can later be enrolled by other students without re-seeding) but **also** writes a flat `enrolled_subjects: list[str]` attribute onto the Student node under `student-<id>`. The projection in `_build_student_state` populates `state.subjects` from this attribute directly — no edge traversal, no multi-group read.

Texts, Topics, and AOs are not required for AC-GSM-006 (planner has bands to plan against day 1) — the planner reads `topic_confidences` which the seed already routes under `student-<id>` per the original AC-007 design. Multi-group reads for those entity types are deferred until a live demand surfaces them.

Forced by G2 outcome below: cross-group edges are functionally broken in the fork, so option (a) (multi-group read via STUDIES edge traversal) is not viable.

### G2 — Cross-group edges: **deferred; intra-group edges only**

Per the probe outcome (recorded below), cross-group `EntityEdge.save()` is a **silent dangle**: `save()` returns ok, but the persisted state is unreadable via the typed `EntityEdge.get_by_group_ids` API and invisible to Cypher traversal in either named graph.

Decision: the seed writes only **intra-group edges** — specifically `Student → HAS_CONFIDENCE → TopicConfidence` within `student-<id>`. Curriculum-level edges (`Subject → COVERS → Topic`, `Topic → ASSESSED_BY → AO`, etc.) are written under their respective curriculum group_ids (`subject-<slug>` or `fleet-appmilla`) where source and target both reside.

Cross-group edges (`Student → STUDIES → Subject`, `Student → WORKING_ON → Text`) are deferred until the `graphiti-core` fork or upstream supports them. The denormalisation in G1 covers the only cross-group fact the planner currently needs.

### G3 — TopicConfidence baseline: **far-past timestamp sentinel `EPOCH_NEVER_REVISED`**

A new module-level constant `EPOCH_NEVER_REVISED: Final[datetime] = datetime(1970, 1, 1, tzinfo=timezone.utc)` is added to `student_model.py`. The seed writes `last_revised_at=EPOCH_NEVER_REVISED` for every baseline `TopicConfidence`. This:

- Keeps the field's `datetime` type unchanged (no schema change to the Pydantic model).
- Requires zero changes to `planner/rules.py` (`now - epoch ≈ 56 years` ≫ 48h cooldown delta — every topic is correctly *outside* cooldown on day 1).
- Requires zero changes to `planner/pipeline.py:_project_topic_confidence` (epoch is not `None`, so the existing `if last_revised is None: last_revised = fallback_clock()` branch isn't triggered).
- Requires zero existing test-fixture migrations (`TopicConfidence(last_revised_at=…)` callsites in `tests/unit/planner/*.py` and `tests/unit/knowledge/test_student_model.py` keep their explicit datetimes).
- Sorts deterministically: epoch ties at the head of the "oldest first" ordering; the existing `topic_ref` ascending key ([rules.py:137](../../../src/study_tutor/planner/rules.py#L137)) breaks ties stably.

The trade-off is mild semantic dishonesty (`last_revised_at: 1970-01-01` reads as "revised in 1970" until a real revision overwrites it). Mitigated by the named constant being greppable and centralised — anyone reading the field in raw graph queries follows the constant back to this ADR.

## Why these over the alternatives

The TASK-GSM-007 review report's R1-R3 originally recommended multi-group read via STUDIES traversal (G1 option a), a probe-then-decide path for G2, and `Optional[datetime] = None` (G3 option b). The probe drove G1 → option (b) and forced G2 → defer. G3 was reassessed during TASK-GSM-008 against the actual planner-side hot paths and flipped to option (a) (epoch sentinel) for blast-radius reasons:

- Option (b) `Optional[datetime] = None` cascades into ~4 sites: model field, [pipeline.py:300-302](../../../src/study_tutor/planner/pipeline.py#L300-L302) (the existing `fallback_clock()` substitution would silently relocate G3's bug — under (b), seed writes `None` → projection writes `now` → topic sits in cooldown), [rules.py:137](../../../src/study_tutor/planner/rules.py#L137) sort key (`None` mixed with `datetime` raises TypeError), [rules.py:163](../../../src/study_tutor/planner/rules.py#L163) arithmetic guard (`now - None` raises TypeError), and ≥5 test-fixture sites.
- Option (a) epoch is contained: one named constant + one seed-side use site. Zero existing-code changes.
- Option (c) (transition-event semantics) was already rejected by the review (defeats the no-LLM seed goal).

For G1: option (a) (multi-group read) was preferred by the review but is now structurally unavailable post-probe. Option (c) (co-locate Subjects under `student-<id>` too) duplicates curriculum data across partitions and diverges from the "subjects are curriculum-level / cross-student" intent baked into the group-id topology (ADR-ARCH-007). Option (d) (scope reduction — TopicConfidence-only) underdelivers AC-006's "non-empty `subjects`" verification target. Option (b) denormalise is the cheapest viable path under the probe-confirmed constraint.

For G2: the silent-dangle outcome (rather than a clean save() error) makes the failure mode worse for downstream callers — they'd believe the edge persisted and only discover the read-side blank when a planner query yielded zero results. Documenting it as deferred + adopting the denormalisation workaround is structurally correct; further investigation belongs in a future task once an upstream fix lands.

## Consequences

### Positive

- AC-GSM-007-03 (post-seed `subjects` non-empty + `topic_confidences` non-empty) becomes satisfiable end-to-end. The fetcher reads `subjects` from a Student-node attribute, not via cross-group edge traversal.
- AC-GSM-006 (planner has bands to plan against day 1) is preserved — the epoch sentinel keeps every topic outside the 48h cooldown.
- Implementation in TASK-GSM-009 stays inside the original 1-2 day window. No `student_model.py` schema change, no `planner/*.py` rules changes, no test-fixture migration sweep.
- The CC-13 invariant (single call site for live-tutor `add_episode` writes) remains intact — the seed exits the LLM-extraction path entirely, and the seed's group-id discipline (`student-<id>` for student-scoped, `subject-<slug>` for curriculum-scoped, `fleet-appmilla` for cross-fleet AOs) carries forward.

### Negative / accepted trade-offs

- The Student node's `enrolled_subjects` attribute is denormalised — a Subject rename / un-enrolment requires updating the Student node, not just the Subject. Acceptable for Phase 1 (single learner, stable curriculum). Documented as a known follow-up if the system grows multiple learners with shifting enrolments.
- Cross-group edges are unavailable. Any future feature requiring `Student → WORKING_ON → Text` traversal (e.g. text-level recommendation) needs either upstream graphiti-core support, or a parallel denormalisation, or a per-text Snapshot routing under `student-<id>`. Captured as future-work, not Phase-1 scope.
- The epoch sentinel is opaque to direct graph queries (someone running `MATCH (tc:TopicConfidence) RETURN tc.last_revised_at` sees `1970-01-01T00:00:00+00:00`). Mitigation: the constant is named, centralised, and referenced from this ADR + the seed-script docstring.

### Operational

- TASK-GSM-007 stays in `tasks/completed/` as the design-review historical record (the review accepted the *direction*, not the original ACs). TASK-GSM-009 is the freshly-spec'd implementation task with refreshed ACs reflecting these resolutions and the original review's R4-R12 polish recommendations.
- The Phase-1-validation gate flips for G2 and G3 (in [docs/research/ideas/phase-1-validation.md](../../../docs/research/ideas/phase-1-validation.md)) are gated on TASK-GSM-009's live demo evidence landing — not on this ADR. This ADR only resolves the design path.

## G2 probe — script and observed outcome

### Script

`scripts/probes/probe_cross_group_edges.py` (committed alongside this ADR per AC-GSM-008-02). One-shot, runnable via:

```bash
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.venv/bin/python \
  scripts/probes/probe_cross_group_edges.py
```

Self-cleans `student-probetest` and `subject-probetest` named graphs on both success and failure (`MATCH (n) DETACH DELETE n` Cypher fallback under FalkorDB's per-graph driver). The probe writes a typed `Student` node into `student-probetest`, a typed `Subject` node into `subject-probetest`, and attempts to save an `EntityEdge(name="STUDIES", group_id="student-probetest")` connecting the two. It then reads back via `EntityEdge.get_by_group_ids(student_driver, ["student-probetest"])` and via a Cypher `MATCH` traversal in the student graph.

### Observed outcome (whitestocks FalkorDB, 2026-05-04)

Verbatim JSON output:

```json
{
  "provider": "falkordb",
  "captured_at": "2026-05-04T18:46:08.904795+00:00",
  "student_uuid": "4df6d326-3329-46c7-b1e2-ef54da5d50fc",
  "subject_uuid": "2d71a4a6-f640-4911-8752-05546117a434",
  "student_save": "ok",
  "subject_save": "ok",
  "edge_save": "ok",
  "edge_uuid": "49e4f244-2a47-4bf3-b92a-737793ed6381",
  "edge_read_in_student_graph": {
    "error": "GroupsEdgesNotFoundError: no edges found for group ids ['student-probetest']"
  },
  "traversal_in_student_graph": {
    "count": 0,
    "rows_repr": []
  },
  "cleanup": {
    "student-probetest": "ok (DETACH DELETE)",
    "subject-probetest": "ok (DETACH DELETE)"
  }
}
```

### Interpretation

This is hypothesis **H3 (silent dangle)**:

- `EntityEdge.save()` returns successfully — no exception, a UUID is generated.
- The typed reader (`EntityEdge.get_by_group_ids`) raises `GroupsEdgesNotFoundError`: the edge is *not* materialised in the typed-API view of the student graph.
- Cypher traversal from the student node in the student graph finds zero outbound edges.

The most plausible underlying cause: under per-group named-graph isolation, the edge is persisted into the source-node's named graph, but its target-node UUID resolves to a node that doesn't exist in that graph (the Subject node lives in `subject-probetest`). The fork's typed reader either MERGE-joins on target presence (yielding empty), or the fork writes the edge into a default partition that the student-graph driver doesn't query. Either way, the outcome for our purposes is the same: cross-group edges are functionally broken, and worse, fail silently.

### Consequence for the seed

Per the TASK-GSM-008 decision tree:

> If `edge_outcomes.save == "ok"` but `read_count == 0` (silent dangle): **also forces G1 fallback**. Pick G1 option (b) or (c). Cross-group edges deferred until graphiti-core upstream addresses it.

Adopted in this ADR. G1 = (b) denormalise. G2 = defer all cross-group edges; only intra-group edges (HAS_CONFIDENCE within `student-<id>`, COVERS within `subject-<slug>`, ASSESSED_BY within `subject-<slug>` if the AO ref is local — otherwise dropped) are written by the seed.

### Probe self-cleanup verification

The cleanup outcomes (`ok (DETACH DELETE)` for both partitions) confirm no probe state remains in production FalkorDB after the script exits. AC-GSM-008-02 satisfied.

The probe also produces ~200 lines of stderr noise from `build_indices_and_constraints` background tasks getting cancelled when the wrapper closes. This is a graphiti-core lifecycle artifact (each `driver.clone(database=…)` spawns a background indexing task), not a probe correctness issue. Captured here for awareness; the JSON outcome on stdout is authoritative.

## Implementation surface (handed to TASK-GSM-009)

The decisions above land in code via the following changes in TASK-GSM-009:

1. `src/study_tutor/knowledge/student_model.py` — add `EPOCH_NEVER_REVISED: Final[datetime]` constant and export it.
2. `scripts/seed_student_model.py` — typed-entity rewrite per Path 1B; Student node carries `enrolled_subjects` attribute; TopicConfidence writes use `EPOCH_NEVER_REVISED`; only intra-group edges are written.
3. `src/study_tutor/knowledge/queries.py` — `_build_student_state` populates `state.subjects` from the Student node's `enrolled_subjects` attribute (pluralisation of the existing `_attr` lookup pattern).
4. `tests/integration/test_lilymay_seed_seam.py` — drift fix `year_group=11→10`, `target_grade="8"→"7"` (per TASK-GSM-007 review R7).
5. No changes to `planner/rules.py`, `planner/pipeline.py`, `student_model.py`'s `TopicConfidence` field signature, or any planner-side test fixtures.

## References

- [TASK-GSM-007 review report](../../../.claude/reviews/TASK-GSM-007-review-report.md) — the full design analysis that surfaced G1/G2/G3
- [TASK-GSM-008](../../../tasks/in_progress/TASK-GSM-008-resolve-typed-entity-design-gaps.md) — the design-resolution task this ADR closes
- [TASK-GSM-009](../../../tasks/backlog/TASK-GSM-009-typed-entity-seed-refactor.md) — the downstream implementation task
- [scripts/probes/probe_cross_group_edges.py](../../../scripts/probes/probe_cross_group_edges.py) — the G2 probe script
- [graphiti-core fork pin](../../../pyproject.toml) — `v0.29.5-guardkit.2[falkordb]`
- [phase-1-validation.md](../../../docs/research/ideas/phase-1-validation.md) — TASK-GR-SEED status table; G2/G3 gates flip pending TASK-GSM-009 evidence
