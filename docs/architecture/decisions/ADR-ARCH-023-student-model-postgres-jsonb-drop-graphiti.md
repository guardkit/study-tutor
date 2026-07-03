# ADR-ARCH-023 — Student model persistence: drop Graphiti/FalkorDB, adopt a study-tutor-owned Postgres (JSONB) store

## Status

Accepted

**Ratified:** 2026-07-03 via `/arch-refine` (G-ADR gate — [migration build plan §5a/§9](../../research/ideas/student-model-postgres-migration-scope-and-build-plan.md)). Made effective on ratification: **ADR-ARCH-007** and **ADR-ARCH-019** → `superseded`; **ADR-ARCH-021**'s CC-13 single-call-site invariant annotated as retired; C4 **L1/L2** diagrams regenerated (FalkorDB + Gemini-extractor → study-tutor Postgres). ADR-ARCH-003 was already superseded by ADR-ARCH-019, so the 003→019→023 chain is left intact.

**Date:** 2026-07-02
**Phase:** Phase 1 (Student Model) — decided during the fleet-wide Graphiti decommission
**Supersedes:** [ADR-ARCH-003](ADR-ARCH-003-async-graphiti-writeback.md) (async Graphiti write-back at session-end), [ADR-ARCH-007](ADR-ARCH-007-graphiti-split-topology.md) (Graphiti split topology), [ADR-ARCH-019](ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) (async write-back at every write point). **Retires the CC-13 single-`add_episode`-call-site invariant** of [ADR-ARCH-021](ADR-ARCH-021-typed-entity-seed-design-resolutions.md) (no `add_episode` remains).
**Related:** [ADR-ARCH-022](ADR-ARCH-022-corpus-retrieval-lexical-path-defer-agentic-tool.md) (corpus retrieval — the sibling store; ChromaDB corpus stays separate and is unaffected), [ADR-ARCH-014](ADR-ARCH-014-single-user-scalability-posture.md) (single-user posture), [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md) (UK data residency / minor-data-by-design), [ADR-ARCH-013](ADR-ARCH-013-middleware-level-gamification-engine-future.md) (gamification engine — consumer of this store), FEAT-PH1-001 (Student Model), [docs/gamification/design.md §11](../../gamification/design.md) (persistence model). **Cross-repo context:** the fleet-wide `Graphiti → fleet-memory` cutover + `qwen-graphiti` decommission (`fleet-memory/docs/migration/graphiti-cutover-and-decommission-plan.md`).

## Context

**The fleet is decommissioning Graphiti/FalkorDB.** Graphiti extracts entities/relationships by calling an LLM (`qwen-graphiti`, Qwen2.5-14B, ~28 GB resident) on **every write**; the 2026-04-27 spike measured `add_episode` median **78.98s** ([ADR-ARCH-019](ADR-ARCH-019-async-graphiti-writeback-every-write-point.md)). That LLM-per-write model was a persistent GB10 memory/throughput tax, required a forked-and-patched `graphiti-core`, and resisted reuse of other served models. study-tutor is one of five Graphiti consumers; all are **soft dependencies** (fire-and-forget writes, reads degrade to empty).

**study-tutor's memory is structured, deterministic learner state — not a semantic-graph problem.** The gamification design (§11) models it as **Student** (level, total XP, streak, longest streak), **Topic** (confidence ∈ [0,1], last-studied, session count), **Achievement** (unlocked-at), **Quest** (active/historical, expiry, status), **Session** (episode with XP earned + AOs scaffolded). Every state change is a deterministic update — `XP += 120`, `confidence += 0.1` (capped ±0.1/session), streak increment, achievement check. Routing these through an LLM entity-extraction pipeline was a category error: we paid a 28 GB / ~79s LLM pass to perform a key-value/relational upsert. That mismatch **is** why Graphiti was expensive here.

**Operator goals for study-tutor** (2026-07-02): (a) Graphiti **and** FalkorDB gone; (b) study-tutor **independently deployable** from the agent fleet; (c) `fleet-memory` is available but **not mandatory** — study-tutor's instance would be unique to it regardless.

**Why not fleet-memory for study-tutor.** `fleet-memory` (pure-embeddings, deterministic LLM-free writer, typed payloads, NATS relay, Postgres+pgvector, resident embedder) is the right answer for the *fleet's* semantic recall over unstructured build/session artifacts. For study-tutor's structured learner state it is over-provisioned, and it drags a NATS broker + relay + pgvector + an embedding model into what must be a **standalone** deploy. This is the "JSONB-on-Postgres for the learner profile" option long noted in the project's own history as the clean ending for the graph framing.

## Decision

### D1 — study-tutor-owned Postgres (JSONB) is the student-model store
A study-tutor-dedicated Postgres instance holds the learner profile. Schema follows [gamification/design.md §11](../../gamification/design.md): `student`, `topic_confidence`, `achievement`, `quest`, `session` — relational rows with JSONB for the flexible/nested fields (per-AO observations, session AO scaffolding). Natural keys: `student_id`; `(student_id, topic)`; `(student_id, achievement_id)`. **No graph, no embeddings, no LLM** on the write or read path.

### D2 — Writes revert to synchronous at the session-end boundary
A JSONB upsert is single-digit milliseconds, not 79 seconds. The async fire-and-forget machinery introduced by [ADR-ARCH-003](ADR-ARCH-003-async-graphiti-writeback.md)/[ADR-ARCH-019](ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) existed **solely** to keep the caller off Graphiti's latency; that rationale is gone. Therefore:
- Within-session state stays in the in-process `TutorSession` aggregate (unchanged).
- The **session-end flush is a synchronous transactional write** (XP + streak + per-topic confidence deltas + achievement checks in one transaction). `tutor_session_end` still returns well within budget; `tutor_turn` p95 < 10s is unaffected (any per-turn write is also ms-scale).
- The `GraphitiWriteHelper` fire-and-forget helper, `asyncio.create_task` dispatch, shutdown-grace draining, and the **CC-13 single-call-site invariant** are **retired** — there is no `add_episode` to guard.
- The **events bus (Shared Kernel B)** is unchanged: [DDR-003](../../design/decisions/DDR-003-session-completed-emits-on-state-transition.md) already decoupled `session.*` emission from write success; it remains an independent, consumer-facing surface (Gamification engine, dashboard).

### D3 — Start fresh; no data migration
Per the operator decision, prior FalkorDB learner state (Lilymay's streaks/XP/confidence/achievements) is **not** migrated. Her state re-establishes from the next sessions. Consequently study-tutor needs **no `migrate-graph`/`falkordb` tooling at all** — the transitional "keep the `falkordb` client" step in the guardkit decommission does not apply to study-tutor. The old FalkorDB volume is archived/dropped with the fleet-wide teardown (WS-5/6).

### D4 — No fleet coupling for learner state; reuse ChromaDB for any semantic recall
study-tutor takes **no dependency** on `fleet-memory`, NATS, or the fleet embedder for the student model. If semantic recall over past sessions/misconceptions is later wanted, it reuses study-tutor's **existing ChromaDB** ([ADR-ARCH-022](ADR-ARCH-022-corpus-retrieval-lexical-path-defer-agentic-tool.md)) as a second collection — no new infrastructure, no new store type.

### D5 — Remove the Graphiti code + dependency from study-tutor (soft-dep drop, own timeline)
Delete/replace the Graphiti knowledge layer — `knowledge/async_write.py` (→ a synchronous `StudentStore` write), `knowledge/queries.py` (→ SQL reads), `knowledge/graphiti_client.py`, `knowledge/episodes.py`, `knowledge/seed_uuids.py`, and the Graphiti parts of `knowledge/student_model.py` — and drop `graphiti-core[falkordb]` from [pyproject.toml](../../../pyproject.toml). Because study-tutor is a **soft** dependency (reads already degrade to empty; writes are best-effort), this is behaviour-preserving and can land on study-tutor's own schedule, **decoupled from guardkit's WS-2c/W3**.

## Alternatives considered

- **`fleet-memory` (own instance).** Rejected for study-tutor — over-provisioned for structured state and drags NATS + relay + pgvector + embedder into a standalone deploy (see Context). Remains correct for the agent fleet.
- **SQLite (embedded).** Viable and simplest for the current single-user MVP, but the mobile plan needs **networked, concurrent, cross-device** access (phone ↔ robot resume via the HTTP/WS adapter hitting one backend). Postgres serves that without a later migration; SQLite would force one. If a fully offline single-device build is ever wanted, SQLite stays a drop-in for the same schema.
- **Keep Graphiti (patched fork).** Rejected — the LLM-per-write tax, the maintenance burden of the fork, and the model-reuse friction are the entire reason for this ADR.
- **Migrate Lilymay's history.** Rejected by the operator (D3) — low volume, early days, and it keeps the cutover free of `falkordb`/export tooling. (Cheap to revisit: her current values are still readable via the live Graphiti reads until decommission, if continuity is later wanted.)
- **Keep writes async "to be safe."** Rejected — async fire-and-forget was a workaround for 79s latency; retaining it over a ms-scale Postgres write is complexity with no benefit and a crash-loses-writes downside.

## Consequences

**Positive:**
- Eliminates the 28 GB / ~79s LLM-per-write tax on the GB10 — the direct memory-pressure relief motivating the change; also de-risks the mobile/voice async path.
- Deterministic, testable state (pure update functions over rows) — a natural fit for the gamification economy and the Coach's ±0.1 confidence rule.
- **Synchronous writes simplify the architecture** — removes fire-and-forget dispatch, shutdown-grace draining, and the CC-13 audit; no in-flight-write-lost-on-crash caveat.
- **Independently deployable** study-tutor (own Postgres, no fleet broker/embedder) — meets the operator goal and strengthens minor-data-by-design ([ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md)): learner data on owned hardware, off third-party APIs.
- Corpus retrieval (ChromaDB) and student memory (Postgres) are now two clean, independent, self-hosted stores — no graph store, no fleet dependency.

**Negative:**
- Loses graph-topology queries (multi-hop relationship traversal). study-tutor never used them — the reads are per-student partition lookups and confidence distributions — so no functional loss, but it forecloses "reason over the learning graph" without a future re-architecture.
- Lilymay's accrued streak/XP/confidence history is discarded (D3, accepted).
- study-tutor now owns a schema + lightweight migration tooling (Alembic or equivalent) it did not before — offset by deleting the entire Graphiti client, seed, and async-write machinery.
- Supersedes three ADRs and retires a cross-cutting invariant; the downstream artefacts below must be reconciled.

## Downstream artefacts flagged stale

- [docs/gamification/design.md §6.2 / §11](../../gamification/design.md) — "confidence maintained in Graphiti (Phase 1)" and the §11 entity/event model → reframe to the Postgres `StudentStore` schema; the §11.2 "atomic at session-end" claim is now literally true (a single transaction) rather than "fire-and-forget per write".
- [docs/planning/feature-roadmap.md](../../planning/feature-roadmap.md) — FEAT-PH1-001 "Graphiti Student Model" → "Postgres Student Model"; drop ADR-ARCH-003/007/019 references; SR-08 (write-back asynchrony) is retired by D2.
- [ADR-ARCH-022](ADR-ARCH-022-corpus-retrieval-lexical-path-defer-agentic-tool.md) — its "student-memory backend (Graphiti → fleet-memory)" black-box references are now resolved by this ADR (Postgres JSONB); update the parenthetical.
- [src/study_tutor/knowledge/async_write.py](../../../src/study_tutor/knowledge/async_write.py), [queries.py](../../../src/study_tutor/knowledge/queries.py), [graphiti_client.py](../../../src/study_tutor/knowledge/graphiti_client.py), [episodes.py](../../../src/study_tutor/knowledge/episodes.py), [seed_uuids.py](../../../src/study_tutor/knowledge/seed_uuids.py), [student_model.py](../../../src/study_tutor/knowledge/student_model.py) — implementation targets of D5.
- `scripts/seed_student_model.py` — the typed-entity Lilymay seed → a Postgres seed (or removed under D3 "start fresh").
- [pyproject.toml:35](../../../pyproject.toml#L35) — drop `graphiti-core[falkordb]`; add `psycopg`/`asyncpg` + a migration tool.
- `.env` / `.env.example` — replace Graphiti/FalkorDB config with `STUDY_TUTOR_PG_DSN` (or equivalent).
- ADR-ARCH-003 / ADR-ARCH-007 / ADR-ARCH-019 — set `Status: superseded` (queryable as history; no content rewrite). ADR-ARCH-021 — annotate that its CC-13 single-call-site invariant is retired here.

**Reconciliation status (ratified 2026-07-03).** ADR-ARCH-007 → `superseded`; ADR-ARCH-019 → `superseded`; ADR-ARCH-021 CC-13 note added; ADR-ARCH-003 already superseded by ADR-ARCH-019 (chain intact — no change). C4 L1/L2, `ARCHITECTURE.md`, `domain-model.md`, `gamification/design.md` (§2/§6/§9/§11), and `feature-roadmap.md` (FEAT-PH1-001, SR-08) were reconciled in the same pass. Source/deps/config (`pyproject.toml`, `.env`, `knowledge/*`) remain the FEAT-SMP W1/W3 build targets (D5), untouched here.

## C4 diagram re-review status

System topology **changed** (unlike the sibling [ADR-ARCH-022](ADR-ARCH-022-corpus-retrieval-lexical-path-defer-agentic-tool.md), whose corpus decision left topology intact). Ratification therefore **triggered the mandatory C4 re-review gate**: FalkorDB and the Gemini entity-extraction LLM leave the topology, `student_model` moves from `graphiti-core` to a Postgres (asyncpg / JSONB) client, and the GB10 embedder narrows to ChromaDB-only. Revised C4 **Level 1** ([system-context.md](../system-context.md)) and **Level 2** ([container.md](../container.md)) were regenerated and approved on 2026-07-03. Dropping the Gemini extractor also **closes the [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md) on-device-residency exception** — learner data no longer leaves the household for entity extraction.

## References

- `fleet-memory/docs/migration/graphiti-cutover-and-decommission-plan.md` §3 — study-tutor consumer inventory (soft dep; `student-{id}` partition; `async_write.py` / `queries.py` touchpoints).
- [ADR-ARCH-019](ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) — the 78.98s `add_episode` measurement this ADR makes obsolete.
- [ADR-ARCH-022](ADR-ARCH-022-corpus-retrieval-lexical-path-defer-agentic-tool.md) — sibling decision; corpus (ChromaDB) stays separate from student memory (Postgres).
- [docs/gamification/design.md §11](../../gamification/design.md) — the persistence model this store implements.
- [ADR-ARCH-014](ADR-ARCH-014-single-user-scalability-posture.md), [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md) — single-user, local-first, minor-data posture that Postgres-on-owned-hardware satisfies.
</content>
