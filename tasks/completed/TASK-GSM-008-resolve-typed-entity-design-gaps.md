---
id: TASK-GSM-008
title: "Resolve Path 1B design gaps before typed-entity seed implementation (G1 read-scope, G2 cross-group edges, G3 TopicConfidence.last_revised_at)"
task_type: review
review_mode: design
review_depth: standard
status: completed
created: 2026-05-04T00:00:00Z
updated: 2026-05-04T12:35:00Z
priority: high
complexity: 4
estimated_minutes: 120
review_results:
  mode: design
  depth: standard
  score: 88
  ac_satisfied: 7
  ac_total: 7
  decision: approve
  report_path: .claude/reviews/TASK-GSM-008-review-report.md
  adr: docs/architecture/decisions/ADR-ARCH-021-typed-entity-seed-design-resolutions.md
  spawned_implementation_task: TASK-GSM-009
  completed_at: 2026-05-04T12:30:00Z
tags:
  - seed
  - graphiti
  - typed-entities
  - falkordb
  - design-decision
  - phase-1-gate-flip
  - g2-g3-unblock
  - decision-point
  - follow-on
parent_task: TASK-GSM-007
related:
  - TASK-GSM-007  # accepted-with-revisions design review (`.claude/reviews/TASK-GSM-007-review-report.md`)
  - TASK-GSM-001  # Pydantic entity models (TopicConfidence schema change candidate)
  - TASK-GR-SEED  # blocked parent — unblocked once GSM-008 resolves and implementation lands
  - TASK-FORK-PATCH  # graphiti fork v0.29.5-guardkit.2 — G2 probe target
context_files:
  - .claude/reviews/TASK-GSM-007-review-report.md
  - tasks/completed/TASK-GSM-007-typed-entity-seed-refactor.md
  - src/study_tutor/knowledge/queries.py
  - src/study_tutor/knowledge/student_model.py
  - scripts/seed_student_model.py
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Resolve Path 1B design gaps (G1 / G2 / G3) before TASK-GSM-007 implementation

## Why this exists

`/task-review TASK-GSM-007 --mode=design --depth=standard` (2026-05-04, report at [.claude/reviews/TASK-GSM-007-review-report.md](../../.claude/reviews/TASK-GSM-007-review-report.md)) approved Path 1B over Path 1A but flagged three load-bearing under-specifications that will cause green unit tests + red live-AC outcomes if implementation starts before they're settled. Operator decision: **[A]ccept the review, spawn a follow-on review task to resolve G1/G2/G3, then refresh ACs and `/task-work` from there.**

This task is the follow-on. Its output is **decisions + a small probe**, not implementation.

## The three gaps

### G1 — Read-scope mismatch (CRITICAL)

`get_student_state` reads only `student-<id>` group ([queries.py:450](../../src/study_tutor/knowledge/queries.py#L450)), but the seed writes Subjects/Texts/Topics/AOs to `subject-<slug>` and `fleet-appmilla`. AC-GSM-007-03's claim that `subjects` will be non-empty under typed-entity writes "without any change to `_build_student_state`" is structurally false — the projection is correct; the *fetcher* is the problem.

**Resolution candidates** (review report §G1):

| Option | Description | Trade-off |
|--------|-------------|-----------|
| (a) | Multi-group read: derive subject group_ids via STUDIES edge traversal off the Student node, aggregate. | Cleanest; depends on G2 outcome (cross-group edge support). |
| (b) | Denormalise: write `enrolled_subjects: list[str]` attribute on the Student node; projection reads it directly. | Flattest. Loses Subject-level structured state but matches `StudentState.subjects: list[str]` shape. No edge-traversal dependency. |
| (c) | Co-locate: write Subject nodes under `student-<id>` group too (in addition to `subject-<slug>`). | Duplicates data across partitions; diverges from "subjects are curriculum-level / cross-student" intent. |
| (d) | Scope reduction: AC-03 covers TopicConfidence-only for TASK-GSM-007; multi-group reads deferred to a separate task. | Smallest implementation footprint; demo can ship if Phase-1 only needs TopicConfidence-driven planner output. |

**Review's recommendation**: (a) for `subjects` if G2 cross-group edges work; (b) as the safe fallback; (d) for non-Subject fields (Text/AO/Topic) which aren't strictly required for AC-006 planner behaviour.

### G2 — Cross-group-graph edge writes (HIGH)

The fork's bug-#8 fix isolates each `group_id` into its own FalkorDB named graph. `EntityEdge` takes a single `group_id`. An edge from a Student in `student-lilymay` graph to a Subject in `subject-english-literature` graph has no obvious home — behaviour is **undocumented** and not obvious from a code read.

**Resolution: probe before designing.** Build a one-shot script that:

1. Creates Student in `student-probetest` graph
2. Creates Subject in `subject-probetest` graph
3. Attempts `EntityEdge(source=..., target=..., group_id="student-probetest").save(driver)`
4. Reads back via `EntityEdge.get_by_group_ids(driver, ["student-probetest"])`
5. Tries to traverse from Student to Subject across graphs

Document outcomes against three hypotheses:
- **H1**: edge persists in source's graph; target node lookup from edge fails (dangle).
- **H2**: `save()` raises or returns an error (cross-graph edges rejected).
- **H3**: edge silently writes both nodes' UUIDs into one graph as standalone strings (no traversal possible).

Whichever holds, document the consequence for Path 1B's edge strategy.

### G3 — `TopicConfidence.last_revised_at` semantics for baseline writes (HIGH)

`TopicConfidence.last_revised_at: datetime` is required ([student_model.py:311](../../src/study_tutor/knowledge/student_model.py#L311)). The planner cooldown logic at [queries.py:511](../../src/study_tutor/knowledge/queries.py#L511) uses it. Setting it to `now()` at seed → every topic in 24h cooldown → AC-006 (planner has bands to plan against on day 1) breaks.

**Resolution candidates** (review report §G3):

| Option | Description | Trade-off |
|--------|-------------|-----------|
| (a) | Far-past timestamp (epoch) | Pure value choice; no schema change. Slightly dishonest ("revised in 1970"). |
| (b) | Make `last_revised_at: datetime \| None = None`; projection treats `None` as "not in cooldown". | Schema change but semantically clean ("never revised"). 1-line model + 1-line projection update. |
| (c) | Keep transition-event semantics: write a steady-state TopicConfidence + a separate TopicConfidenceUpdated event. | Most expressive; reintroduces episode-style writes, defeating the no-LLM seed goal. |

**Review's recommendation**: (b).

## Acceptance Criteria

- [ ] **AC-GSM-008-01** — A short ADR-style markdown file `docs/architecture/ADR-typed-entity-seed-design-resolutions.md` (or similar location matching repo convention) is committed, capturing:
  - The chosen option for G1 with rationale (referencing the G2 probe outcome).
  - The chosen option for G3 with rationale.
  - The G2 probe script + its observed outcome (H1/H2/H3 or other) + its consequence for the edge-write strategy.
- [ ] **AC-GSM-008-02** — A G2 probe script is committed at `scripts/probes/probe_cross_group_edges.py` (or similar). Runnable end-to-end against live FalkorDB with one command. Self-cleans (deletes its `*-probetest` partitions) on success or failure. Log output captured into the ADR.
- [ ] **AC-GSM-008-03** — TASK-GSM-007 is **re-spec'd as a fresh task `TASK-GSM-009-typed-entity-seed-refactor.md`** (or, equivalently, TASK-GSM-007 is reopened with refined ACs — operator's choice on naming) with:
  - AC-03 wording updated to match the chosen G1 resolution (e.g. "non-empty `subjects` derived via enrolled-subjects denormalisation on the Student node, non-empty `topic_confidences`").
  - Edge-write scope updated to match the G2 probe outcome (e.g. "Student→HAS_CONFIDENCE→TopicConfidence edges within the `student-<id>` partition only; cross-group edges deferred to TASK-GSM-XXX pending fork support").
  - `last_revised_at` semantics updated to match the G3 resolution (e.g. "TopicConfidence baseline writes use `last_revised_at=None` per ADR-typed-entity-seed-design-resolutions").
  - All other TASK-GSM-007 ACs (01, 02, 04, 05, 06, 07, 08, 09, 10, 11) carried forward with the review's R4-R12 polish recommendations applied.
- [ ] **AC-GSM-008-04** — If G3 option (b) is chosen, [src/study_tutor/knowledge/student_model.py:311](../../src/study_tutor/knowledge/student_model.py#L311) field change is included in the implementation task scope (TASK-GSM-009), AND the existing test surface that constructs `TopicConfidence` in tests is identified and listed in the implementation task's test-rewrite scope.
- [ ] **AC-GSM-008-05** — `tests/integration/test_lilymay_seed_seam.py` schema-drift fix (year_group=11→10, target_grade="8"→"7") is included in the implementation task scope (TASK-GSM-009 / refreshed -007) per review R7. This is a 2-line change; surfaced now to avoid it falling through.
- [ ] **AC-GSM-008-06** — [docs/research/ideas/phase-1-validation.md](../../docs/research/ideas/phase-1-validation.md) is **not** updated by this task (G2/G3 gate flips are gated on the implementation task landing — TASK-GSM-008 only resolves the design path). A 1-2 line note IS added to the existing TASK-GR-SEED status table noting "design resolution in TASK-GSM-008; implementation in TASK-GSM-009 (or refreshed -007)".
- [ ] **AC-GSM-008-07** — No production code changes outside the probe script. This is a design + decision task, not an implementation task. Lint/format checks pass on the new files.

## Non-goals

- **Not in scope**: implementing the typed-entity write path (deferred to refreshed -007 / -009).
- **Not in scope**: rewriting `tests/unit/seeding/test_seed_student_model.py` (deferred).
- **Not in scope**: re-running the live seed against FalkorDB (deferred).
- **Not in scope**: flipping G2/G3 gates in `phase-1-validation.md` (deferred to implementation task).

## Probe expectations (G2)

Estimated time-box: **30 minutes**. The probe is a single-purpose script with no abstraction layer. Pseudo-code:

```python
# scripts/probes/probe_cross_group_edges.py
import asyncio, uuid
from graphiti_core.driver.driver import GraphProvider
from graphiti_core.nodes import EntityNode
from graphiti_core.edges import EntityEdge
from study_tutor.knowledge.graphiti_client import (
    get_client, load_graphiti_config_from_yaml,
)

GROUP_STUDENT = "student-probetest"
GROUP_SUBJECT = "subject-probetest"

async def main() -> int:
    config = load_graphiti_config_from_yaml()
    wrapper = await get_client(config)
    if wrapper is None:
        print("graphiti client unavailable"); return 2
    inner = wrapper.client_or_none
    driver = inner.driver

    # 1. Write nodes into separate partitions
    student_uuid = str(uuid.uuid4())
    subject_uuid = str(uuid.uuid4())
    student_driver = driver.clone(database=GROUP_STUDENT) if driver.provider == GraphProvider.FALKORDB else driver
    subject_driver = driver.clone(database=GROUP_SUBJECT) if driver.provider == GraphProvider.FALKORDB else driver

    await EntityNode(
        uuid=student_uuid, name="ProbeStudent",
        labels=["Student"], group_id=GROUP_STUDENT, attributes={},
    ).save(student_driver)
    await EntityNode(
        uuid=subject_uuid, name="ProbeSubject",
        labels=["Subject"], group_id=GROUP_SUBJECT, attributes={},
    ).save(subject_driver)

    # 2. Probe: edge with group_id=GROUP_STUDENT, source in GROUP_STUDENT, target in GROUP_SUBJECT
    edge_outcomes = {}
    try:
        edge = EntityEdge(
            source_node_uuid=student_uuid,
            target_node_uuid=subject_uuid,
            name="STUDIES", fact="probe",
            group_id=GROUP_STUDENT, attributes={},
        )
        await edge.save(student_driver)
        edge_outcomes["save"] = "ok"
    except Exception as e:
        edge_outcomes["save"] = f"{type(e).__name__}: {e}"

    # 3. Read back
    try:
        edges = await EntityEdge.get_by_group_ids(student_driver, [GROUP_STUDENT])
        edge_outcomes["read_count"] = len(edges or [])
        edge_outcomes["read_first_source"] = edges[0].source_node_uuid if edges else None
        edge_outcomes["read_first_target"] = edges[0].target_node_uuid if edges else None
    except Exception as e:
        edge_outcomes["read"] = f"{type(e).__name__}: {e}"

    # 4. Try traversal from Student to Subject
    # ... attempt MATCH (s:Student)-[r]-(t:Subject) RETURN t in student_driver context

    print(json.dumps(edge_outcomes, indent=2))

    # 5. Cleanup: delete probe partitions
    # await driver.execute_query(f"GRAPH.DELETE {GROUP_STUDENT}")
    # await driver.execute_query(f"GRAPH.DELETE {GROUP_SUBJECT}")

    await wrapper.close()
    return 0
```

Capture the JSON output verbatim into the ADR. The decision tree is:

- If `edge_outcomes.save == "ok"` and `edge_outcomes.read_count >= 1`: **G2 is solvable**. Cross-group edges work; pick G1 option (a). Document any traversal-side caveats observed.
- If `edge_outcomes.save` is an error: **G2 forces G1 fallback**. Pick G1 option (b) or (c). Cross-group edges deferred until graphiti-core upstream addresses it.
- If `edge_outcomes.save == "ok"` but `read_count == 0` (silent dangle): **also forces G1 fallback**. Document the silent-failure mode for future reference.

## Implementation Notes

### Where the ADR lives

Repo convention check first — look for existing `docs/architecture/ADR-*.md` or similar. If none exist, create the directory; document the ADR template inline (Context / Decision / Consequences sections) and use the lightweight format from `.claude/rules/quality-gates.md` §Architecture Decision Records.

### Test surface impact of G3 option (b)

If `TopicConfidence.last_revised_at: datetime | None = None` is chosen:

- `_build_student_state` projection at [queries.py:356-358](../../src/study_tutor/knowledge/queries.py#L356) — already coerces via `_coerce_datetime` which returns `None` for missing values. ✓ Likely no change needed.
- Cooldown check at [queries.py:510-512](../../src/study_tutor/knowledge/queries.py#L510) — already guards on `tc.last_revised_at is not None`. ✓ Already correct.
- Test fixtures in [tests/unit/seeding/test_seed_student_model.py:248-255](../../tests/unit/seeding/test_seed_student_model.py#L248) — construct `TopicConfidenceSnapshot` without `last_revised_at`; need to verify the snapshot model's optional-field handling matches.
- Any `TopicConfidence(...)` constructor call in tests — needs `last_revised_at=None` permitted.

Estimate: 5 fixture sites max (grep before committing the spec).

### Naming for the refreshed implementation task

Operator's choice. Options:

- **(α)** Reopen TASK-GSM-007: move the existing file from `tasks/completed/` back to `tasks/backlog/`, update the AC block in-place, mark `status: backlog` again. Preserves task ID continuity but blurs the "review accepted; implementation is a fresh task" boundary.
- **(β)** Spawn TASK-GSM-009 as the implementation task, leave -007 in completed/ as the review-accepted historical record. Cleaner audit trail; -007 ≡ "the review", -009 ≡ "the implementation". Recommended.

This task assumes (β) for AC-GSM-008-03 wording but happily accepts (α) at the operator's discretion.

## Cross-references

- **Source review report**: [.claude/reviews/TASK-GSM-007-review-report.md](../../.claude/reviews/TASK-GSM-007-review-report.md) — full context including alternatives evaluated and architecture score (75/100).
- **Parent design review (accepted)**: [tasks/completed/TASK-GSM-007-typed-entity-seed-refactor.md](../completed/TASK-GSM-007-typed-entity-seed-refactor.md).
- **Pydantic models** (potential G3 modification target): [src/study_tutor/knowledge/student_model.py](../../src/study_tutor/knowledge/student_model.py) — `TopicConfidence` class.
- **Read seam** (G1 modification target — depending on G1 outcome): [src/study_tutor/knowledge/queries.py](../../src/study_tutor/knowledge/queries.py) — `get_student_state`, `_read_student_partition`, `_build_student_state`.
- **graphiti-core fork** (G2 probe target): pinned at `v0.29.5-guardkit.2[falkordb]` in [pyproject.toml](../../pyproject.toml). Bug-#8 fix (per-group named-graph isolation) is the relevant context.

## Notes

- This task is `task_type: review` because its output is decisions + a probe + ADR + refreshed implementation task spec, not production code. Run via `/task-review TASK-GSM-008 --mode=design --depth=standard` once ready, or proceed manually if the operator prefers a hands-on resolution.
- DDD South West (mid-May) and Kaggle hackathon are the demo-timeline pressure. Estimated 2-hour design window for this task; if it grows past 3 hours something's off and the scope should be reassessed (likely by collapsing G1 to option (b) "denormalise" and skipping the G2 probe — accepting the cost of edge-strategy uncertainty in exchange for ship velocity).
- The G2 probe touches a live FalkorDB. The probe script must self-clean its `*-probetest` partitions on both success and failure to avoid leaving state in the production FalkorDB. AC-GSM-008-02 enforces this.
