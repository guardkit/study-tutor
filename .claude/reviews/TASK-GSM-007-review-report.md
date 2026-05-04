# Review Report: TASK-GSM-007

## Executive Summary

**Decision recommendation: APPROVE Path 1B with revisions** before spawning `/task-work`.

Path 1B (typed-entity writes via `EntityNode.save` / `EntityEdge.save`) is the correct architectural choice over Path 1A. It cleanly removes the LLM from the seed write path — which is the actual root cause of both Wave-4/5 failure modes (rate-limit-driven write loss + untyped `Entity`-only labels defeating projection). The CC-13 scope-narrowing is principled and the determinism/idempotency story is materially better than `add_episode`-based extraction.

However, the design as currently spec'd has **one critical gap and three significant under-specifications** that will produce a green test suite but a red live-AC outcome unless resolved up front:

1. **CRITICAL — AC-GSM-007-03 is not satisfiable as written.** `get_student_state` reads only from `student-<id>` group, but the seed writes Subjects/Texts/Topics/AOs to *other* group_ids (`subject-<slug>`, `fleet-appmilla`). Typed-entity writes don't change this — the projection will still see `subjects=[]` end-to-end even with perfectly-typed Subject nodes, because the fetcher never reads those partitions. Needs a read-scope decision before `/task-work` starts.
2. **HIGH — Edge-write story crosses graphiti-core's per-group-graph isolation.** The fork's bug-#8 fix isolates each group_id into its own FalkorDB named graph. An edge from a Student node (in `student-lilymay` graph) to a Subject node (in `subject-english-literature` graph) cannot live in either graph alone. Behaviour under cross-graph edges is unspecified and needs investigation before relying on six relationship types from `student_model.py`.
3. **HIGH — `TopicConfidence.last_revised_at` semantics for baseline writes are unspecified.** The Pydantic model requires this field; the planner's cooldown logic uses it ([queries.py:511](../../src/study_tutor/knowledge/queries.py#L511)). Setting it to `now()` at seed time puts every topic in cooldown immediately, breaking AC-006 (planner has bands to plan against on day 1). The current code dodges this by emitting transition-event `TopicConfidenceUpdatedEpisode` rather than a steady-state node.
4. **MEDIUM — Per-entity UUID derivation strategy is sketched but not specified.** `uuid5(NAMESPACE_OID, f"{group_id}:{label}:{name}")` works for entities with stable `name` (Student, Subject, Topic, AO) but `TopicConfidence` and `Misconception` have no `name` — their identity keys are tuples (`student_ref + topic_ref` / `topic_ref + observed_at`). Needs a per-class derivation strategy.

**Architecture score: 75/100.** Good design intent, sound choice of Path 1B over 1A, principled CC-13 scope-narrowing — but read-side scope and cross-group edge semantics are underspecified in a way that will surface during `/task-work` and likely loop back here.

**Estimated remediation effort to close gaps: 1–2 hours of design-side work** (mostly resolving #1 and #2 with concrete read-scope and edge-strategy choices) before `/task-work` is productive.

---

## Review Details

- **Task**: TASK-GSM-007 — Refactor `seed_student_model.py` to write typed entities directly (Path 1B)
- **Mode**: Design review (architectural + decision hybrid)
- **Depth**: Standard
- **Reviewer**: Manual structured review (no agent delegation — focused single-file scope)
- **Date**: 2026-05-04

---

## Findings

### Strengths (what works in Path 1B)

**S1. Removes LLM dependency from seed writes — root-cause aligned.**  
Wave-4/5's failure modes (HTTP 429 rate-limit storms, `_perform_write` → `openai.AuthenticationError`, `succeeded_writes=6 of 25`) all root in graphiti-core's `add_episode`-internal entity-extraction LLM fan-out. Removing that path entirely (rather than rate-limit-tuning the GB10) is the structurally correct fix. The GB10 `-np 6` / `concurrencyLimit: 8` bump remains valid for live tutor sessions where narrative content genuinely needs extraction.

**S2. Determinism + structured attributes solve the `_entity_type` problem.**  
Today every seeded node returns `labels: ["Entity"]`, `attributes_keys: []` ([verify_lilymay.py output, recorded in task description](../../tasks/backlog/TASK-GSM-007-typed-entity-seed-refactor.md#L52)). [queries.py:273-292](../../src/study_tutor/knowledge/queries.py#L273) `_entity_type` returns `""` for those, so projection silently drops every node. Path 1B writes `labels=["Student"]` (or whichever class) directly, and the projection at [queries.py:330-367](../../src/study_tutor/knowledge/queries.py#L330) will key correctly on `kind == "student"` / `"subject"` / `"topicconfidence"`.

**S3. Idempotency-by-deterministic-UUID is elegant.**  
`uuid5(NAMESPACE_OID, ...)` collapses re-runs into MERGE no-ops without needing the `_is_already_seeded` short-circuit. Cleaner than the current pre-flight check. (Caveat: the task assumes graphiti-core 0.29's `EntityNode.save` is a MERGE-by-uuid in the FalkorDB driver. Worth verifying — see G2 below.)

**S4. CC-13 scope-narrowing is principled, not a hack.**  
"Single call site for live tutor session `add_episode` writes" preserves the original invariant's *intent* (auditable LLM-extraction path) while admitting that the seed has a different operational profile (deterministic, no extraction needed). Documented clearly in the task rationale. Approved.

**S5. Aligns with TASK-GSM-001's original Pydantic-typed entity intent.**  
The Pydantic models in [src/study_tutor/knowledge/student_model.py](../../src/study_tutor/knowledge/student_model.py) (Student, Subject, Text, Topic, AssessmentObjective, Misconception, TopicConfidence) were designed for typed-entity writes. They've been waiting for a write path that honours their schema rather than passing them through an LLM that flattens them. Path 1B finally consumes them as designed.

**S6. Driver-clone-per-group pattern is already proven on the read side.**  
[queries.py:243-263](../../src/study_tutor/knowledge/queries.py#L243) already implements `clone(database=gid)` for FalkorDB partition isolation. The seed will mirror this exact pattern — no new pattern, no new risk surface.

---

### Critical issues (must resolve before /task-work)

#### G1. AC-GSM-007-03 is structurally unsatisfiable without a read-scope decision

**Severity: CRITICAL**

The acceptance criterion claims:

> AC-GSM-007-03 — `get_student_state(client, "lilymay")` returns a populated `StudentState` with `year_group=10`, `target_grade="7"`, **non-empty `subjects`** (English Literature + English Language), non-empty `topic_confidences` — **without any change to `_build_student_state`**.

But the data layout makes this impossible without a *fetcher* change (separate from the projection):

| Entity | Seed group_id | Read group_ids in `get_student_state` |
|--------|---------------|--------------------------------------|
| Student | `student-lilymay` | `student-lilymay` ✓ |
| TopicConfidence | `student-lilymay` | `student-lilymay` ✓ |
| Subject | `subject-english-literature` | **NOT READ** ✗ |
| Subject | `subject-english-language` | **NOT READ** ✗ |
| Text | `subject-<slug>` | **NOT READ** ✗ |
| Topic | `subject-<slug>` | **NOT READ** ✗ |
| AssessmentObjective | `fleet-appmilla` | **NOT READ** ✗ |

Confirmed by reading [queries.py:450](../../src/study_tutor/knowledge/queries.py#L450):

```python
group_ids = [f"{STUDENT_GROUP_PREFIX}{student_id}"]   # ONLY student-lilymay
```

This is independent of typed-vs-untyped writes. Even if every Subject node is written with perfect `labels=["Subject"]` and structured `attributes`, the read never asks the `subject-<slug>` partition for them. `state.subjects` will be `[]`. AC-03 fails.

Why hasn't this been visible? Because **the existing tests mock `_build_student_state` directly with already-fetched node lists** (e.g. [test_seed_student_model.py:286-294](../../tests/unit/seeding/test_seed_student_model.py#L286)) — they exercise the projection on synthetic `subjects=["English Literature"]`-bearing fixtures rather than the live fetcher. The unit tests would still pass under Path 1B; the live AC evidence (verify_lilymay.py JSON) would still show `subjects: []`.

**Resolution options** (one must be chosen as part of TASK-GSM-007's scope):

- **(a)** Expand `get_student_state` to query multiple group_ids: derive subject group_ids from the Student node's enrolled-subject attribute (or via STUDIES edge traversal) and aggregate. Cleanest if edges work cross-graph (see G2).
- **(b)** Denormalise: write Subject names into a list-attribute on the Student node (`enrolled_subjects: ["English Literature", "English Language"]`). Projection reads this directly. Loses the ability to attach Subject-level state but matches what `StudentState.subjects: list[str]` actually wants.
- **(c)** Co-locate: write Subject nodes ALSO under `student-<id>` group (in addition to or instead of `subject-<slug>`). Diverges from the curriculum-level/cross-student sharing intent of subject groups.
- **(d)** Defer: explicitly scope AC-03's `subjects` and `topic_confidences` assertions to "TopicConfidence-only" for TASK-GSM-007, and create a follow-up TASK-GSM-008 to wire multi-group reads. Acceptable if the Phase-1 demo only needs TopicConfidence-driven planner recommendations.

**Recommendation**: **Option (a) for `subjects`** (clean, aligns with Pydantic model intent), **option (d) for `current_texts`/AOs/Topics** (defer — these aren't strictly required for AC-006 planner behaviour). Update AC-03 to: "non-empty `subjects` (via enrolled-subject derivation / edge traversal) and non-empty `topic_confidences`."

---

#### G2. Cross-group-graph edge writes are unspecified — graphiti-core may not support them

**Severity: HIGH**

The task's "Wave / sub-task structure" (point 4) calls for:
- Student → ENROLLED_IN → Subject
- Topic → ASSESSES → AO
- Student → HAS_CONFIDENCE → TopicConfidence

Two of these (Student→Subject, Topic→AO) cross group-id boundaries. Under the fork's per-group-graph isolation ([queries.py:209-220](../../src/study_tutor/knowledge/queries.py#L209) docstring), each `group_id` is its own FalkorDB named graph. An edge between a Student in `student-lilymay` graph and a Subject in `subject-english-literature` graph has no obvious home graph.

graphiti-core's `EntityEdge` constructor takes a single `group_id`, suggesting an edge belongs to exactly one graph. If the edge is written into `student-lilymay`, the source node exists there but the target node doesn't (it's in `subject-english-literature`). Whether the edge dangles, fails-fast on save, or silently writes a malformed reference is **not documented in the task** and not obvious from a reading of the codebase.

**Resolution options**:

- **(a)** Test before designing: write a one-shot probe script that creates Student in `student-lilymay`, Subject in `subject-english-literature`, and tries `EntityEdge(source=..., target=..., group_id="student-lilymay").save(driver)`. Read back via `EntityEdge.get_by_group_ids(driver, ["student-lilymay"])` and confirm the edge appears. If it doesn't, fall back to (b).
- **(b)** Co-locate edge endpoints: write Subject nodes also under `student-lilymay` (as duplicate typed nodes — accepted as denormalisation cost). Edges then have both endpoints in the same partition. Aligns with G1 option (c) if chosen.
- **(c)** Drop cross-group edges from TASK-GSM-007's scope: only Student→HAS_CONFIDENCE→TopicConfidence (same-partition) is in scope; cross-group edges deferred. Match this to AC-03's scope per G1.

**Recommendation**: **(a) probe first.** Spend 30 minutes confirming graphiti-core's actual behaviour rather than designing for assumptions. Then either (b) or (c) based on what the probe reveals. Add the probe outcome to the task's "Implementation Notes" before starting.

---

#### G3. `TopicConfidence.last_revised_at` semantics for baseline writes are unspecified

**Severity: HIGH**

The Pydantic `TopicConfidence` model ([student_model.py:288-314](../../src/study_tutor/knowledge/student_model.py#L288)) requires `last_revised_at: datetime` (no default). The current seed dodges this by emitting `TopicConfidenceUpdatedEpisode` (a transition event with `previous_band → new_band`) rather than a steady-state TopicConfidence node — a Pydantic-model field that needs a value.

The planner's cooldown logic at [queries.py:509-515](../../src/study_tutor/knowledge/queries.py#L509):

```python
in_cooldown = (
    tc.last_revised_at is not None and tc.last_revised_at >= cooldown_cutoff
)
if in_cooldown:
    continue   # excluded from recommendations
```

Default `cooldown_hours=24` (see `DEFAULT_COOLDOWN_HOURS`). If the seed sets `last_revised_at=now()`, every topic is in cooldown for the first 24 hours after seeding — the planner returns `[]` for `get_topic_recommendations(...)`. **AC-006 (planner has bands to plan against on day 1) breaks.**

**Resolution options**:

- **(a)** Set `last_revised_at` to a far-past timestamp (e.g. unix epoch / `datetime(1970, 1, 1, tzinfo=UTC)`). Cooldown logic treats it as "long out of cooldown". Pure value choice; no code change.
- **(b)** Make `last_revised_at: datetime | None = None` in the Pydantic model and update the projection to treat `None` as "not in cooldown". One-line schema change; semantically cleaner ("never revised" → not in cooldown). 
- **(c)** Keep the transition-event `TopicConfidenceUpdatedEpisode` semantics: write a steady-state TopicConfidence with one timestamp + a *separate* "TopicConfidenceUpdated" event. Most expressive but doubles the write count and reintroduces episode-style writes that defeat the no-LLM goal.

**Recommendation**: **(b) — make `last_revised_at` optional.** Cleanest conceptually, smallest code surface, doesn't lie about a baseline being a "revision". Document the semantic in the field docstring and update [queries.py:511](../../src/study_tutor/knowledge/queries.py#L511) to treat `None` as `not in_cooldown`. Backwards-compatible at the wire level (existing rows have a value and will continue to work).

---

### High-priority concerns

#### G4. Per-entity UUID derivation strategy is sketched, not specified

**Severity: MEDIUM**

The task sketches:

```python
def deterministic_uuid(group_id: str, label: str, name: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_OID, f"{group_id}:{label}:{name}"))
```

This works for entities with stable `name` fields (Student, Subject, Topic, AO). It does **not** work for:

- **TopicConfidence** — has no `name` field. Identity = `(student_ref, topic_ref)`. Derivation key should be `f"{group_id}:TopicConfidence:{student_ref}:{topic_ref}"`.
- **Misconception** — has no `name` field. Identity = `(topic_ref, observed_at)` per [student_model.py:264](../../src/study_tutor/knowledge/student_model.py#L264). Derivation key needs to include both. (Although the seed doesn't write Misconceptions today, leaving this ambiguous bakes in tech debt.)
- **Edges** — UUID derivation for `EntityEdge` is independent of node UUIDs. Suggest `uuid5(NAMESPACE_OID, f"{group_id}:{relationship}:{source_uuid}:{target_uuid}")` for MERGE-on-re-run.

**Recommendation**: Specify a per-class `_derive_uuid` strategy (a small dispatch table or per-class method) rather than a single 3-arg helper. Surface this in the helper extraction sub-task (point 1 of the task's "Wave / sub-task structure") so it's testable in isolation.

---

#### G5. `EntityNode.save` upsert semantics in graphiti-core 0.29 (fork) need explicit verification

**Severity: MEDIUM**

The task's idempotency claim assumes `EntityNode.save(driver)` is a MERGE-by-uuid in the FalkorDB driver. If it's CREATE, calling save twice with the same UUID produces two nodes (or fails the second time, depending on FalkorDB's MERGE-vs-CREATE behaviour at the GRAPH.QUERY level).

The fork (`v0.29.5-guardkit.2`) hasn't necessarily preserved upstream's semantics here, and the upstream itself hasn't been audited for this in the task.

**Recommendation**: Add to TASK-GSM-007's helper-extraction sub-task a smoke test that:
1. Calls `EntityNode(uuid=..., ...).save(driver)` twice with identical args
2. Reads back via `EntityNode.get_by_group_ids(driver, [group_id])`
3. Asserts exactly 1 node returned (not 2, not error)

Pin this as an inline test in the helper module, not a downstream integration test, so it runs in CI without the live FalkorDB requirement (use a mock driver or the existing graphiti-core test fixtures).

---

#### G6. Test surface impact is wider than AC-GSM-007-06 acknowledges

**Severity: MEDIUM**

AC-GSM-007-06 names two tests for rewrite:
- `test_seed_lilymay_fresh_run_succeeds_and_uses_seed_flush_id`
- `test_seed_lilymay_returns_exit_3_when_writes_abandoned`

But the helper-call-recording fixture is used by *every* test in `tests/unit/seeding/test_seed_student_model.py` (e.g. [test_seed_lilymay_seeds_all_six_aos_with_descriptions:304-313](../../tests/unit/seeding/test_seed_student_model.py#L304) iterates `helper.calls` looking for `SeedBaselineEpisode` instances). Once `helper.schedule_write` is no longer the seed's call site, all of these need rework — the test fixture needs to record `EntityNode.save` invocations rather than `helper.schedule_write` invocations.

Counted with grep:

```
$ grep -c "helper\.calls\|helper\.drain_call_count\|_FakeHelper\|schedule_write" tests/unit/seeding/test_seed_student_model.py
~30 hits across the file
```

**Recommendation**: Update AC-GSM-007-06 to scope as "all unit tests in test_seed_student_model.py rewritten to use a `_FakeDriver` fixture that records `EntityNode.save` / `EntityEdge.save` calls instead of `helper.schedule_write` calls". This is a larger but more honest scope. ~30-45 minutes additional work over the two-test rewrite estimate.

---

#### G7. Seam test will fail (pre-existing schema drift)

**Severity: LOW (catch with AC update)**

[tests/integration/test_lilymay_seed_seam.py:73-77](../../tests/integration/test_lilymay_seed_seam.py#L73) asserts:

```python
assert state.year_group == 11, ...
assert state.target_grade == "8", ...
```

But the seed source ([scripts/seed_student_model.py:115-118](../../scripts/seed_student_model.py#L115)) sets `year_group=10`, `target_grade="7"`. This drift pre-exists TASK-GSM-007 (the seam test was authored against an out-of-date assumption) but TASK-GSM-007 is the first task that will surface it because Path 1B will actually populate these fields end-to-end.

AC-GSM-007-05 mentions correcting the validation doc but doesn't explicitly call out the seam test.

**Recommendation**: Add to AC-GSM-007-05 a bullet for `tests/integration/test_lilymay_seed_seam.py`: update `year_group=11 → 10` and `target_grade="8" → "7"`. Two-line change.

---

### Lower-priority observations

#### O1. Relationship constant naming consistency

The task's "Wave / sub-task structure" point 4 mentions `Student → ENROLLED_IN → Subject`, but [student_model.py:89](../../src/study_tutor/knowledge/student_model.py#L89) defines `STUDIES: str = "STUDIES"`. The seed should use the constants from `student_model.py` rather than introducing new relationship names. (Also `ASSESSED_BY` not `ASSESSES`, etc.) Minor naming consistency win, no design impact.

#### O2. `seed_lilymay(client, helper)` signature

Under typed-entity writes the `helper` parameter becomes vestigial — every write goes through `EntityNode.save(driver)`. Either:
- Remove it (cleaner; updates `main()` and tests)
- Keep it for the post-finally drain (which becomes a no-op `(0, 0)` tuple)

Recommend removing for cleanliness; the cost is a single-line change in `main()`.

#### O3. Episode-type module — `SeedBaselineEpisode` should be deleted, not deprecated

AC-GSM-007-11 offers "delete or deprecate". Recommend **delete cleanly**. Deprecated code attracts misreads. The two failing tests being rewritten (per AC-06) will remove the only references; no zombie code is needed.

#### O4. Logging event-shape audit

The current seed emits structured logs:
- `seeding_failed` / `reason=client_unavailable`
- `seeding_skipped` / `reason=already_seeded`
- `seeding_completed` / `subjects=N, topic_confidences=N, succeeded_writes=N`
- `seeding_pending_writes_abandoned` / `abandoned=N, succeeded=N`
- `seeding_batch_drained` / `batch=<label>, succeeded=N, abandoned=N`
- `seeding_verification_warning`
- `seeding_failed_unhandled`
- `seeding_batch_drain_env_invalid` (env-var validation)

Under typed-entity writes:
- KEEP: `seeding_failed/skipped/completed/verification_warning/failed_unhandled` (operationally meaningful regardless of write strategy).
- DROP: `seeding_pending_writes_abandoned`, `seeding_batch_drained`, `seeding_batch_drain_env_invalid` (no batching, no abandonment — `EntityNode.save` is sequential and synchronous-like).
- ADD (suggested): `seeding_node_written` per node (debug-level, structured with `entity_kind`, `name`, `group_id`, `uuid`) so post-mortem diagnosis without graph dump is possible.

Document the log-shape contract in the seed module docstring under "Exit-code contract".

#### O5. Live-AC evidence for AC-GSM-007-04 idempotency

AC-04 ("re-running the seed is byte-idempotent") needs concrete evidence. The unit-test side (mock driver, second-call-no-op) is in scope per the test rewrite. The live side needs:

1. Run seed against FalkorDB.
2. Capture `GRAPH.QUERY study_tutor "MATCH (n) RETURN count(n)"` (or per-group equivalent given the partition isolation).
3. Run seed again.
4. Re-capture. Assert identical count.

Add this to the `verify_lilymay.py` follow-up (or a sister script). One-line addition to AC-04's evidence requirements.

#### O6. `pyproject.toml` no-new-deps claim

AC-GSM-007-08 says "no new dependencies". Confirmed: `graphiti-core[falkordb]` (already pinned at the fork tag) provides `EntityNode`, `EntityEdge`, and `GraphProvider.FALKORDB`. ✓

---

## Recommendations (Prioritised)

### Must-fix before /task-work spawns implementation tasks

| ID | Recommendation | Source finding | Effort |
|----|----------------|----------------|--------|
| R1 | Choose read-scope strategy for AC-03 (multi-group read OR denormalise enrolled subjects on Student node OR scope reduction). Update AC-03 wording. | G1 | 30 min design + AC update |
| R2 | Probe graphiti-core's cross-group-graph edge behaviour BEFORE designing edge writes. Update edge scope based on probe result. | G2 | 30 min probe + scope update |
| R3 | Decide TopicConfidence baseline `last_revised_at` semantics. Recommend making the field optional (`datetime | None = None`) with `None`-means-not-in-cooldown projection. | G3 | 15 min decision + 1-line model + 1-line projection |

### Should-fix as part of /task-work scope

| ID | Recommendation | Source finding | Effort |
|----|----------------|----------------|--------|
| R4 | Specify per-class UUID derivation (Student/Subject/Topic/AO use `name`; TopicConfidence uses `student_ref + topic_ref`; edges use `relationship + source_uuid + target_uuid`). Inline in helper module. | G4 | 30 min implementation + tests |
| R5 | Add a smoke test verifying `EntityNode.save` is MERGE-by-uuid in the FalkorDB driver. Pin behaviour against a possible fork drift. | G5 | 20 min |
| R6 | Expand AC-GSM-007-06 to cover the full unit-test rewrite (~all tests in `test_seed_student_model.py`), not just the 2 named tests. | G6 | AC update only; ~45 min implementation |
| R7 | Fix seam-test schema drift (`year_group: 11→10`, `target_grade: "8"→"7"`) as part of AC-GSM-007-05. | G7 | 2-line change |

### Nice-to-have polish

| ID | Recommendation | Source finding | Effort |
|----|----------------|----------------|--------|
| R8 | Use `student_model.py`'s relationship constants (`STUDIES`, `ASSESSED_BY`, etc.) — not new names like `ENROLLED_IN`. | O1 | naming pass |
| R9 | Remove `helper` parameter from `seed_lilymay(client, helper)` signature; update `main()` and tests. | O2 | 1 hour incl. tests |
| R10 | Delete `SeedBaselineEpisode` cleanly rather than deprecating. | O3 | 5 min |
| R11 | Audit and prune structured-log event types (drop batching events, add per-node-written debug log). Document contract in module docstring. | O4 | 30 min |
| R12 | Add live second-run-byte-idempotent evidence to `verify_lilymay.py` flow under AC-04. | O5 | 15 min |

---

## Decision Matrix (Path 1A vs Path 1B vs reject-and-rethink)

| Option | Determinism | LLM-in-seed? | Effort | Risk to AC | Recommendation |
|--------|-------------|--------------|--------|------------|----------------|
| **1A** (`add_episode` with `entity_types` hints) | Partial — LLM can still skip/mis-attribute fields | Yes (still rate-limited) | Smallest | High — doesn't solve root cause | ❌ Reject |
| **1B** (`EntityNode.save` direct) — *as currently spec'd* | Full | No | Larger but bounded | Medium — read-side AC fails per G1 | ⚠️ Approve with revisions |
| **1B-revised** (with R1-R3 resolved) | Full | No | Larger + 1-2h design upfront | Low — green path on AC-01 through AC-04 | ✅ Recommended |
| **Reject + rethink** (full graphiti-core read seam audit) | Full | No | Much larger (4-6h+) | Lowest | ❌ Over-scope for the demo timeline |

**Recommended decision: 1B-revised** — approve Path 1B, return TASK-GSM-007 for AC update with R1-R3 resolved, then proceed to `/task-work`.

---

## Architecture Score: 75/100

| Principle | Score (0-10) | Rationale |
|-----------|--------------|-----------|
| **SRP** | 9 | Seed-script SRP is sharper under 1B (deterministic data loader, no LLM concern). Helper module separation per the sub-task structure preserves single responsibilities. |
| **OCP** | 7 | Adding a new entity type means adding a new `_seed_*` writer + UUID derivation + edge writers. Bounded; not extensible-by-default but the surface is small. |
| **LSP** | 8 | Pydantic models substitute cleanly for their typed-node counterparts because graphiti-core's `EntityNode(attributes={...})` accepts any dict. No subtype contract violated. |
| **ISP** | 8 | The `helper` parameter becomes vestigial (R9). Removing it tightens the seed's interface. |
| **DIP** | 7 | The seed depends on `EntityNode` / `EntityEdge` directly rather than a helper abstraction. Acceptable: the helper abstraction was for the LLM-extraction-routing concern that no longer applies. |
| **DRY** | 7 | UUID derivation, driver-clone-per-group, and `_now_utc()` are all centralisable. Per the sub-task structure, this is in scope. |
| **YAGNI** | 8 | No hypothetical extensibility. Cuts the unused episode types from this path. CC-13 scope-narrowing is "what we actually need" rather than dogma. |
| **KISS** | 7 | Net simplification (seed runs in 1s vs 30+ min, no rate-limit reasoning). The cross-group edge question (G2) reveals graphiti-core complexity that 1B inherits — not 1B's fault, but 1B doesn't *fix* it either. |

Composite ≈ 75/100 — solid design, validation-blocked by under-specified read-side and edge-side that need a 1-2h design refinement before implementation.

---

## Context Used

This review was prepared from direct source reading; no Graphiti knowledge graph context was queried (deferred-tool MCP path skipped to keep the review self-contained).

Files inspected:
- [tasks/backlog/TASK-GSM-007-typed-entity-seed-refactor.md](../../tasks/backlog/TASK-GSM-007-typed-entity-seed-refactor.md) — task spec
- [scripts/seed_student_model.py](../../scripts/seed_student_model.py) — current seed script (the refactor target)
- [src/study_tutor/knowledge/student_model.py](../../src/study_tutor/knowledge/student_model.py) — Pydantic typed-entity models
- [src/study_tutor/knowledge/queries.py](../../src/study_tutor/knowledge/queries.py) — `get_student_state`, `_build_student_state`, `_read_student_partition`, `_entity_type`, planner cooldown logic
- [src/study_tutor/knowledge/episodes.py](../../src/study_tutor/knowledge/episodes.py) — episode types incl. `SeedBaselineEpisode` (to be deleted)
- [tests/unit/seeding/test_seed_student_model.py](../../tests/unit/seeding/test_seed_student_model.py) — unit-test rewrite scope
- [tests/integration/test_lilymay_seed_seam.py](../../tests/integration/test_lilymay_seed_seam.py) — runtime contract pin (G7 schema drift)
- [.guardkit/autobuild/TASK-GR-SEED/verify_lilymay.py](../../.guardkit/autobuild/TASK-GR-SEED/verify_lilymay.py) — verification script (live-AC evidence shape)
- [docs/research/ideas/phase-1-validation.md](../../docs/research/ideas/phase-1-validation.md) — G2/G3 falsification context

---

## Decision Checkpoint

**Review Results**:
- Architecture Score: 75/100
- Findings: 7 (3 critical/high, 3 medium, 1 low) + 6 minor observations
- Recommendations: 12 (3 must-fix, 4 should-fix, 5 nice-to-have)

**Key Findings**:
1. **G1 (CRITICAL)**: AC-03 unsatisfiable as written — `get_student_state` reads only `student-<id>`, but Subjects/Texts/Topics/AOs live in other group_ids
2. **G2 (HIGH)**: Cross-group-graph edge writes are unspecified under the fork's per-group isolation
3. **G3 (HIGH)**: `TopicConfidence.last_revised_at` semantics for baseline writes break planner cooldown logic (AC-006)

**Key Recommendations**:
1. R1 — Choose read-scope strategy (recommend: multi-group via STUDIES edge traversal OR denormalise enrolled_subjects on Student node)
2. R2 — Probe graphiti-core cross-group edge behaviour before designing
3. R3 — Make `TopicConfidence.last_revised_at` optional (`datetime | None = None`)
4. R4-R7 — Pickup during `/task-work` scope expansion
5. R8-R12 — Polish during implementation

**Decision Options**:

- **[A]ccept** — Approve findings, mark TASK-GSM-007 as REVIEW_COMPLETE (review report archived; task stays in backlog awaiting AC update before `/task-work`)
- **[R]evise** — Request deeper analysis (recommend: probe graphiti-core's cross-group edge behaviour as a precursor to design refinement)
- **[I]mplement** — Create implementation tasks based on recommendations (NOT recommended yet — R1/R2/R3 must be resolved at the AC level before implementation tasks make sense)
- **[C]ancel** — Discard review

**Recommended decision**: **[A]ccept** the review findings, then **manually update TASK-GSM-007's AC-03 wording per R1, add a probe step per R2, and add a `last_revised_at: Optional` decision per R3** before invoking `/task-work TASK-GSM-007`. The task is *not* ready for `/task-work` implementation in its current AC shape.

Awaiting operator decision.
