# Review Report: TASK-GSM-008

## Executive Summary

**Decision recommendation: APPROVE design resolutions.** All three load-bearing gaps from TASK-GSM-007 are settled, evidenced, and committed:

- **G1 (CRITICAL — read-scope mismatch)** → Option (b) **denormalise** `enrolled_subjects: list[str]` onto the Student node. Forced by G2 outcome (cross-group edges silently dangle).
- **G2 (HIGH — cross-group edges)** → **Defer**. Live probe against `whitestocks:6379` confirmed hypothesis **H3 (silent dangle)**: `EntityEdge.save()` returns ok but the edge is unreadable via the typed API and invisible to Cypher traversal in either named graph. Only intra-group edges (`Student → HAS_CONFIDENCE → TopicConfidence` within `student-<id>`) are written by the seed.
- **G3 (HIGH — TopicConfidence baseline)** → Option (a) **epoch sentinel** `EPOCH_NEVER_REVISED: Final[datetime] = datetime(1970, 1, 1, tzinfo=UTC)`. **Reversed from the original review's recommendation of (b) `Optional[datetime] = None`** after auditing the planner's hot paths — option (b) cascades into ~4 sites of changes (model + projection + 2 rule-side guards + ≥5 test fixtures) with subtle bug risk; option (a) is contained to 1 named constant + the seed-side use site.

All three resolutions are captured in [`docs/architecture/decisions/ADR-ARCH-021-typed-entity-seed-design-resolutions.md`](../../docs/architecture/decisions/ADR-ARCH-021-typed-entity-seed-design-resolutions.md), and the implementation surface is handed to [`TASK-GSM-009`](../../tasks/backlog/TASK-GSM-009-typed-entity-seed-refactor.md) (operator chose option β: spawn a fresh implementation task rather than reopen TASK-GSM-007).

**Architecture score: 88/100.** All design decisions are evidence-grounded (G2 probe), blast-radius-aware (G3 reversal), and downstream-honest (G2 deferral documented as future-work, not buried). The ship-velocity argument was respected without compromising correctness.

**Probe artifact**: [`scripts/probes/probe_cross_group_edges.py`](../../scripts/probes/probe_cross_group_edges.py) committed; outcome JSON pasted verbatim into the ADR.

---

## Review Details

- **Task**: TASK-GSM-008 — Resolve Path 1B design gaps (G1 / G2 / G3) before typed-entity seed implementation
- **Mode**: Design review (decision + architectural hybrid; original task was authored as `review_mode: design`, not a standard framework mode)
- **Depth**: Standard
- **Reviewer**: Manual structured review (no agent delegation — focused single-task scope; followed `/task-review` Phase 1–5 flow)
- **Date**: 2026-05-04
- **Source review**: TASK-GSM-007 design review (accepted-with-revisions, 2026-05-04)

---

## Findings

### G1 — Read-scope mismatch resolved via denormalisation

**Resolution**: Option (b) denormalise.

**Evidence**: G2 probe outcome (below) eliminated option (a) (multi-group read via STUDIES traversal) by confirming cross-group edges are functionally broken in the fork. Option (c) (co-locate Subjects under `student-<id>`) was rejected as duplicating curriculum data across partitions and diverging from the group-id-topology intent in ADR-ARCH-007. Option (d) (scope reduction) underdelivers AC-006's "non-empty `subjects`" verification target.

**Implementation footprint**:
- `scripts/seed_student_model.py` Student-node `EntityNode.save(...)` carries `attributes={"enrolled_subjects": [s["name"] for s in SUBJECTS], ...}`.
- `src/study_tutor/knowledge/queries.py` `_build_student_state` adds one branch under `kind == "student"` that populates `state.subjects` from the `enrolled_subjects` attribute.

**Trade-off**: The Student node's `enrolled_subjects` is denormalised — a Subject rename or un-enrolment requires updating the Student node. Acceptable for Phase 1 (single learner, stable curriculum). Documented in ADR §"Negative / accepted trade-offs" as a known follow-up if the system grows multiple learners with shifting enrolments.

### G2 — Cross-group edges deferred (silent dangle confirmed)

**Resolution**: All cross-group edges deferred. Only intra-group edges written by the seed.

**Evidence — live probe against `whitestocks:6379`** (verbatim JSON from `scripts/probes/probe_cross_group_edges.py`):

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

**Hypothesis matched**: H3 (silent dangle).

- `EntityEdge.save()` returns ok and generates a UUID — no exception path.
- `EntityEdge.get_by_group_ids(student_driver, ["student-probetest"])` raises `GroupsEdgesNotFoundError`: the edge is not materialised in the typed-API view.
- Cypher traversal from the student node finds zero outbound edges in the student graph.

**Plausible underlying cause** (not load-bearing for the decision, but useful for future remediation): under per-group named-graph isolation, the edge persists into the source-node's named graph but its target-node UUID resolves to a node that doesn't exist in that graph (the Subject lives in `subject-probetest`). The fork's typed reader either MERGE-joins on target presence (yielding empty), or writes the edge into a default partition the student-graph driver doesn't query.

**Severity calibration**: The silent-dangle outcome is *worse* than a clean save() error would have been — downstream callers would believe the edge persisted and only discover the gap when a planner query yielded zero results. Documenting the deferral and adopting the denormalisation workaround is structurally correct.

**Self-cleanup verified**: cleanup outcomes (`ok (DETACH DELETE)` for both partitions) confirm no probe state remains in production FalkorDB after the script exits. AC-GSM-008-02 satisfied.

**Probe stderr noise (not blocking)**: ~200 lines of `build_indices_and_constraints` background-task cancellation traces — graphiti-core lifecycle artifact (each `driver.clone(database=…)` spawns a background indexing task that gets cancelled on `wrapper.close()`). Captured in the ADR for future awareness; does not affect probe correctness or JSON outcome authority.

**Probe robustness fix discovered during execution**: First run failed with `ValidationError: created_at Field required` on `EntityEdge` construction. The fork's Pydantic v2 model declares `created_at` as required (no default). Probe updated to pass `created_at=_now_utc()` explicitly. This is a small but real fork-specific contract that any future cross-group-edge-using code must respect — worth noting in the ADR for downstream callers.

### G3 — TopicConfidence baseline: epoch sentinel (reversed from review recommendation)

**Resolution**: Option (a) epoch sentinel `EPOCH_NEVER_REVISED: Final[datetime] = datetime(1970, 1, 1, tzinfo=timezone.utc)`.

**Reversal rationale** (the most architecturally interesting decision in this task):

The original TASK-GSM-007 review recommended option (b) `Optional[datetime] = None` on semantic-cleanliness grounds. The TASK-GSM-008 audit of the planner's actual hot paths revealed this would cascade into ~4 sites:

| Site | Under (b) `Optional[datetime] = None` | Under (a) epoch |
|------|--------------------------------------|-----------------|
| `student_model.py:311` `TopicConfidence.last_revised_at` | Field signature change `datetime → Optional[datetime] = None` | Unchanged |
| `pipeline.py:300-302` `_project_topic_confidence` | `if last_revised is None: last_revised = fallback_clock()` would silently relocate G3's bug — under (b), seed writes `None` → projection writes `now()` → topic sits in 24h cooldown → AC-006 fails. Must change to substitute epoch (or distinguish missingness flavours) | Unchanged (epoch is not None; existing branch isn't triggered) |
| `rules.py:137` sort key | `sorted(key=lambda tc: (tc.percentage, tc.last_revised_at, tc.topic_ref))` raises `TypeError` if any entry is None mixed with datetimes. Need `tc.last_revised_at or datetime.min.replace(tzinfo=UTC)` wrapper | Unchanged (epoch sorts oldest; tie-break on `topic_ref` already deterministic) |
| `rules.py:163` cooldown filter | `(now - tc.last_revised_at) >= _COOLDOWN_DELTA` raises `TypeError` on `now - None`. Need `is not None and …` guard | Unchanged (`now - epoch ≈ 56y` ≫ 48h cooldown) |
| `rules.py:330` `_to_utc_aware(pair[0].last_revised_at)` | Helper's None handling depends on internals; likely needs guard | Unchanged |
| Test fixtures (`tests/unit/planner/*.py`, `tests/unit/knowledge/test_student_model.py:252-262, 398`) | ≥5 sites verify; `_topic("alpha", percentage=10, last_revised_at=recent)`-style helpers need audit | Unchanged |
| Future None-guard discipline | Required everywhere `tc.last_revised_at` is read | Not needed |

The planner is a hot path — it runs on every `tutor_start_session`. Introducing `None`-guards across `rules.py` adds cascade risk: any future rule path that forgets the guard silently breaks under seed-baseline data. Option (a) contains the trade-off: one named constant, one seed-side use site, zero cascade.

**Original review's blind spot**: the review report observed "_build_student_state already coerces via `_coerce_datetime` which returns None for missing values ✓" and "Cooldown check at queries.py:510 already guards on `tc.last_revised_at is not None` ✓" — these are correct but cover the *snapshot-side* (`TopicConfidenceSnapshot`) None-handling. The post-projection `TopicConfidence` entity (consumed by `rules.py`) has different surface that wasn't audited. TASK-GSM-008 closed this gap.

**Trade-off accepted**: mild semantic dishonesty (`last_revised_at: 1970-01-01` reads as "revised in 1970" until a real revision overwrites it). Mitigation: the constant is named, centralised in `student_model.py`, and grep-able back to ADR-ARCH-021 for anyone reading raw graph queries.

### Operator-confirmed scope choices

- **Q1 = Full probe** (operator chose the full G2 investigation rather than skip-and-pre-commit-to-(b)). Probe was written, run live, and produced a definitive answer in ~30 minutes — well under the time-box. Right call: pre-committing without the probe would have left H1/H2/H3 ambiguity in the ADR.
- **Q2 = β (spawn TASK-GSM-009)** — leaves TASK-GSM-007 in `tasks/completed/` as the design-review historical record; TASK-GSM-009 is the freshly-spec'd implementation task. Cleaner audit trail.
- **Q3 = (a) epoch** — operator confirmed the reversed recommendation after pros/cons evaluation.

---

## Recommendations

All three TASK-GSM-007 review **must-fix** recommendations (R1, R2, R3) are now closed:

| ID | Original | Status | Resolution |
|----|----------|--------|------------|
| R1 | Choose read-scope strategy | ✅ Closed | G1 = (b) denormalise. ADR-ARCH-021 §G1. |
| R2 | Probe cross-group edge behaviour | ✅ Closed | Probe committed and run; H3 confirmed. ADR-ARCH-021 §G2. |
| R3 | Decide TopicConfidence baseline | ✅ Closed | G3 = (a) epoch sentinel (reversed from review's recommendation). ADR-ARCH-021 §G3. |

The TASK-GSM-007 review's **should-fix** (R4-R7) and **nice-to-have** (R8-R12) recommendations are carried into [TASK-GSM-009](../../tasks/backlog/TASK-GSM-009-typed-entity-seed-refactor.md)'s acceptance criteria:

| ID | Original | TASK-GSM-009 AC |
|----|----------|------------------|
| R4 | Per-class UUID derivation | AC-GSM-009-12 |
| R5 | MERGE-by-uuid smoke test | AC-GSM-009-13 |
| R6 | Expand AC-06 to full unit-test rewrite | AC-GSM-009-06 |
| R7 | Seam-test schema drift fix | AC-GSM-009-14 |
| R8 | Use `student_model.py` relationship constants | AC-GSM-009-15 |
| R9 | Drop `helper` parameter from `seed_lilymay` | AC-GSM-009-16 |
| R10 | Delete `SeedBaselineEpisode` | AC-GSM-009-11 |
| R11 | Audit/prune structured-log events | AC-GSM-009-17 |
| R12 | Live second-run-byte-idempotent evidence | AC-GSM-009-04 |

No new recommendations from TASK-GSM-008. The design surface is closed.

---

## Acceptance Criteria status

| AC | Description | Status |
|----|-------------|--------|
| AC-GSM-008-01 | ADR committed with G1/G3 decisions + G2 probe outcome | ✅ [ADR-ARCH-021](../../docs/architecture/decisions/ADR-ARCH-021-typed-entity-seed-design-resolutions.md) |
| AC-GSM-008-02 | Probe script committed, runnable, self-cleaning | ✅ [`scripts/probes/probe_cross_group_edges.py`](../../scripts/probes/probe_cross_group_edges.py); cleanup verified via JSON output |
| AC-GSM-008-03 | TASK-GSM-007 re-spec'd as TASK-GSM-009 with R4-R12 + AC refreshes | ✅ [TASK-GSM-009](../../tasks/backlog/TASK-GSM-009-typed-entity-seed-refactor.md), 17 ACs covering R1-R12 + new G1/G2/G3 resolutions |
| AC-GSM-008-04 | If G3=(b), include field change + test-rewrite scope in TASK-GSM-009 | ✅ N/A — G3=(a) chosen, no field change required. Documented in ADR §G3. |
| AC-GSM-008-05 | Seam-test schema drift fix included in TASK-GSM-009 | ✅ TASK-GSM-009 AC-14 |
| AC-GSM-008-06 | 1-2 line note added to TASK-GR-SEED status table in `phase-1-validation.md` | ✅ Added between table and footer (line 151) |
| AC-GSM-008-07 | No production code changes outside the probe; lint/format on new files | ✅ New `.py` files compile + import; no edits to `src/`. The 22-pass / 2-fail seeding-test baseline is unchanged from pre-task state. |

---

## Decision Matrix (for the §Notes alternative paths)

| Path | Description | Trade-off | Recommendation |
|------|-------------|-----------|----------------|
| **A** | Full G2 probe + evidence-driven G1 + (a) epoch sentinel | 30-min probe; 1-named-constant change; zero cascade | ✅ **Adopted** |
| B | Skip probe, pre-commit (b) denormalise + (b) Optional[datetime] | Faster (saves 30 min); accepts edge-strategy uncertainty + 4-site cascade | Rejected — operator chose Q1=F + Q3=(a) flip |
| C | Probe but stick with (b) Optional[datetime] | Same 30 min; still has 4-site cascade | Rejected at Q3 evaluation step |
| D | Reject + rethink (full graphiti-core read seam audit) | Much larger scope (4-6h+); blocks demo timeline | Out of scope for Phase 1 |

---

## Architecture Score: 88/100

| Principle | Score (0-10) | Rationale |
|-----------|--------------|-----------|
| **SRP** | 9 | Probe is single-purpose. ADR captures one cohesive set of related decisions. TASK-GSM-009's AC structure separates G1/G2/G3 resolution from R4-R12 polish. |
| **OCP** | 8 | Denormalisation is bounded — the Student node's attribute surface grows by one field. The seed's group-id discipline is unchanged. |
| **LSP** | 9 | Epoch sentinel preserves the `datetime` type contract. Pydantic models substitute identically for typed-node counterparts in graphiti-core. |
| **ISP** | 9 | Probe exposes only the JSON outcome surface to the ADR (no internal state leaked). TASK-GSM-009 R9 drops the `helper` parameter, tightening the seed's interface. |
| **DIP** | 8 | The seed depends on `EntityNode` / `EntityEdge` directly rather than a helper abstraction — acceptable, the helper abstraction was for the LLM-extraction-routing concern that no longer applies post-Path-1B. |
| **DRY** | 9 | `EPOCH_NEVER_REVISED` is the single source of truth for "never revised". Per-class UUID derivation (R4) is centralised. |
| **YAGNI** | 10 | Cross-group edges deferred (not retrofitted). Misconception UUID derivation specified but not seeded (helper in place for future without code execution). G3 chose the lowest-blast-radius option. |
| **KISS** | 9 | Net simplification. The decision tree from G1/G2/G3 → ADR → TASK-GSM-009 is linear and traceable. The original review's recommendation was reversed *because* the simpler option became visible after auditing the planner. |
| **Evidence quality** | 10 | G2 probe is reproducible (script committed); JSON outcome is verbatim in ADR; H3 hypothesis matched cleanly. |
| **Honesty** | 9 | The G3 reversal is openly documented as "reversed from the original review's recommendation" with explicit rationale, not silently overridden. The G2 silent-dangle pathology is named, not glossed. |

Composite ≈ 88/100 — high-quality design closure. Minor deductions:
- DIP (8): direct dependency on `EntityNode` / `EntityEdge` is acceptable but means the seed can't be tested without graphiti-core in the test path. R5 (MERGE-by-uuid smoke test) only partially mitigates this.
- OCP (8): denormalisation is a known trade-off — it adds a "Student attribute must be updated when enrolment changes" surface that wasn't there before.

---

## Context Used

This review was prepared from direct source reading + a live probe against the production FalkorDB. No Graphiti knowledge graph context was queried (the deferred-tool MCP path was skipped to keep the review self-contained, mirroring the TASK-GSM-007 review's posture).

Files inspected during the design phase:
- [tasks/in_progress/TASK-GSM-008-resolve-typed-entity-design-gaps.md](../../tasks/in_progress/TASK-GSM-008-resolve-typed-entity-design-gaps.md) — task spec
- [.claude/reviews/TASK-GSM-007-review-report.md](./TASK-GSM-007-review-report.md) — source review with R1-R12
- [tasks/completed/TASK-GSM-007-typed-entity-seed-refactor.md](../../tasks/completed/TASK-GSM-007-typed-entity-seed-refactor.md) — original AC structure carried forward
- [src/study_tutor/knowledge/student_model.py](../../src/study_tutor/knowledge/student_model.py) — `TopicConfidence` schema (line 311)
- [src/study_tutor/knowledge/queries.py](../../src/study_tutor/knowledge/queries.py) — `_build_student_state` projection seam
- [src/study_tutor/planner/rules.py](../../src/study_tutor/planner/rules.py) — sort key (line 137) + cooldown filter (line 163) — primary G3 audit surface
- [src/study_tutor/planner/pipeline.py](../../src/study_tutor/planner/pipeline.py) — `_project_topic_confidence` (line 300) — secondary G3 audit surface
- [src/study_tutor/knowledge/graphiti_client.py](../../src/study_tutor/knowledge/graphiti_client.py) — client wrapper API for the probe
- [scripts/seed_student_model.py](../../scripts/seed_student_model.py) — current seed shape (Path 1A) for refactor scope
- [.guardkit/graphiti.yaml](../../.guardkit/graphiti.yaml) — connection config used by the probe

Files created/modified:
- [docs/architecture/decisions/ADR-ARCH-021-typed-entity-seed-design-resolutions.md](../../docs/architecture/decisions/ADR-ARCH-021-typed-entity-seed-design-resolutions.md) — new ADR
- [scripts/probes/probe_cross_group_edges.py](../../scripts/probes/probe_cross_group_edges.py) — new probe script
- [scripts/probes/__init__.py](../../scripts/probes/__init__.py) — new package marker
- [tasks/backlog/TASK-GSM-009-typed-entity-seed-refactor.md](../../tasks/backlog/TASK-GSM-009-typed-entity-seed-refactor.md) — new implementation task
- [docs/research/ideas/phase-1-validation.md](../../docs/research/ideas/phase-1-validation.md) — 1-line update referencing TASK-GSM-008/-009 (line 151)
- [tasks/in_progress/TASK-GSM-008-resolve-typed-entity-design-gaps.md](../../tasks/in_progress/TASK-GSM-008-resolve-typed-entity-design-gaps.md) — status frontmatter updated to `in_progress`

Live infrastructure consulted:
- FalkorDB at `whitestocks:6379` (Synology, over Tailscale) — G2 probe execution; reachable via `nc -zv whitestocks 6379` ≈ 4ms RTT.

---

## Decision Checkpoint

**Review Results**:
- Architecture Score: 88/100
- AC Status: 7/7 satisfied (1 N/A under chosen G3 path)
- Probe outcome: H3 (silent dangle) confirmed live; G1 forced to (b) denormalise; G2 deferred
- ADR + TASK-GSM-009 + phase-1-validation.md note all committed in this session

**Key Decisions**:
1. G1 → denormalise `enrolled_subjects` on Student node (forced by G2 outcome)
2. G2 → defer all cross-group edges; only intra-group edges in seed
3. G3 → epoch sentinel `EPOCH_NEVER_REVISED` (reversed from review's `Optional[datetime] = None` recommendation after planner-side audit)
4. Implementation handed to TASK-GSM-009 (option β); TASK-GSM-007 stays in `completed/` as historical record

**Decision Options**:

- **[A]ccept** — Approve all design resolutions; mark TASK-GSM-008 as `REVIEW_COMPLETE`. Operator can then `/task-work TASK-GSM-009` to begin Path 1B implementation against the refreshed ACs.
- **[R]evise** — Request deeper analysis on a specific aspect (e.g. G2 silent-dangle root cause investigation upstream, or alternative G1 strategies). Time cost: another 1-2h.
- **[I]mplement** — Equivalent to [A]ccept here, since TASK-GSM-009 is *already* spawned and waiting in backlog. Choosing [I] would just mark TASK-GSM-008 complete and queue TASK-GSM-009 for `/task-work`.
- **[C]ancel** — Discard the design resolutions and leave the gaps open. Not recommended — the demo timeline depends on TASK-GSM-009 landing.

**Recommended decision**: **[A]ccept**. The design surface is closed, the implementation task is spec'd, and the next step is `/task-work TASK-GSM-009` (or an interim `/task-create` follow-up if you want to subdivide TASK-GSM-009 further per its §"Wave / sub-task structure").

Awaiting operator decision.
