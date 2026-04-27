# ADR-ARCH-019 — Async Graphiti write-back at every write point in the tutor

## Status

Accepted

**Date:** 2026-04-27
**Phase:** Phase 1
**Supersedes:** [ADR-ARCH-003](ADR-ARCH-003-async-graphiti-writeback.md) — Async Graphiti write-back at session-end boundary
**Related:** [ADR-ARCH-018](ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) (CC-13), [ADR-ARCH-012](ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md) (`AsyncSubAgent`), [ADR-ARCH-017](ADR-ARCH-017-tutor-start-session-sync-classification.md) (sync read path), [ADR-ARCH-002](ADR-ARCH-002-three-layer-architecture.md), CC-08, SR-08, [phase-1-scope.md §SR-08](../../research/ideas/phase-1-scope.md), [graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md), DEC-02, DEC-08.

## Context

ADR-ARCH-003 committed to async Graphiti write-back **at the session-end boundary only**, with mid-session work batched in the in-process `TutorSession` aggregate. That commitment was sized against DEC-08's assumed Graphiti latency of 1–3s per `add_episode` (Gemini extraction era), and against a single Phase-1 write site (`tutor_session_end`).

Two pieces of evidence have arrived since ARCH-003 was accepted (2026-04-18):

1. **The 2026-04-27 Graphiti latency spike** ([graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md)) measured the post-21-Apr vLLM-on-GB10 stack and found:

   | Operation | Median (s) |
   |---|---:|
   | `add_episode` | **78.98** |
   | `search_nodes` | 0.07 |
   | `search_memory_facts` | 0.08 |

   `add_episode` median is **78.98s** — ~15× the 5s SR-08 trigger threshold from `phase-1-scope.md` and ~26× the high end of the original DEC-08 1–3s assumption. CC-08's "fire-and-forget + poll above 30s" rule applies to *every* such write, not just the session-end boundary. Read-path latencies (`search_nodes` / `search_memory_facts` at ~0.07s) are unaffected and continue to satisfy the sync classification of `tutor_start_session` per ADR-ARCH-017.

2. **[ADR-ARCH-018](ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) promoted SR-08 to a load-bearing cross-cutting concern (CC-13)** and explicitly flagged ADR-ARCH-003 as too narrow:

   > ADR-ARCH-003 is a *single-write-point* decision (session-end boundary). The latency spike shows write-back must apply at *every* write point, which is a cross-cutting concern, not a session-boundary policy. ADR-ARCH-003 will need its own follow-up `/arch-refine` to broaden its scope (flagged stale by this ADR; not modified here). — ARCH-018 §Alternatives considered.

ARCH-019 is that follow-up. It broadens the architectural commitment so the cross-cutting concern (CC-13) and the async-write-back ADR are coextensive, removing a contradiction inside `docs/architecture/`.

## Decision

Graphiti write-back is **async-from-caller at every write point in the tutor**, not only at the session-end boundary. The architecture commitment is:

- **Every** Graphiti `add_episode` / entity-update site goes through a helper that runs the work as a background task. Approved mechanisms:
  - `deepagents.AsyncSubAgent` (per [ADR-ARCH-012](ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md)) for write paths the Coach owns or where launch/check/cancel/list semantics are useful.
  - `asyncio.create_task` for simpler one-shot writes that don't need the deepagents tool surface.
- **Caller-facing handlers do not await Graphiti acknowledgement.** Specifically:
  - `tutor_session_end` returns within < 2s regardless of session-end episode write latency.
  - `tutor_turn` retains its p95 < 10s budget — any per-turn or mid-session write (e.g. Coach-observed misconceptions, planner topic-confidence updates) is fire-and-forget.
  - `tutor_start_session` retains its sync < 1s classification (ADR-ARCH-017); its warm-up was already fire-and-forget and is unaffected.
- **Write failures are logged-only.** A failed background `add_episode` emits a structured log line; it does **not** raise from the MCP handler, does **not** retry synchronously on the caller-facing path, and does **not** surface to the student. Fail-soft degradation, consistent with ARCH-003's original posture but now applied at every write point.
- **Within-session state still lives in the in-process `TutorSession` aggregate.** What changes is that the *flush points* are no longer constrained to session-end: any flush point may be introduced by a Phase 1 feature (e.g. the Planner topic-confidence updater, the Coach misconception logger), and every such flush point follows the same fire-and-forget shape.
- **Single-process / single-user posture is unchanged** ([ADR-ARCH-014](ADR-ARCH-014-single-user-scalability-posture.md)). No worker process, no out-of-process queue. Background tasks run inside the tutor's asyncio loop.

This decision is the architecture-level corollary of CC-13 (ARCH-018). CC-13 sets the rule for cross-cutting compliance audits; ARCH-019 records the architectural commitment so the chain of evidence (latency spike → CC-13 → architecture decision) is explicit in `docs/architecture/`.

## Alternatives considered

- **Leave ARCH-003 as-is and rely solely on CC-13 (ARCH-018) for the broader rule.** Rejected. ARCH-018 itself flagged ARCH-003 as needing this refinement. Leaving the architecture decision at "session-end only" while the cross-cutting concern says "every write point" creates a permanent contradiction inside `docs/architecture/`; future readers and `/feature-spec` runs would have to reconcile the two, and the contradiction would be a recurring source of drift.
- **Per-turn synchronous writes for "small" updates (e.g. Coach misconceptions or topic-confidence deltas).** Rejected. The 78.98s median is for *any* `add_episode`; there is no measured cheap-write path on the current FalkorDB + vLLM stack. Differentiating "small" vs "session" writes would require a per-payload latency model that we do not have, and would re-introduce SR-08 violations at the per-turn boundary (CC-08 / 30s threshold).
- **Buffer all mid-session writes and flush at session-end (a generalisation of ARCH-003).** Rejected for Phase 1. Adds session-scoped buffering machinery and concentrates the cost into a single fat session-end flush; with `add_episode` at 78.98s and a multi-write batch, the session-end task could run for several minutes. Fire-and-forget at each write point spreads the cost across the session and matches CC-13's "uniform shape across write sites" requirement.
- **Move Graphiti writes onto a separate worker process / queue.** Considered. Deferred — out of Phase 1 scope (single-user, single-process tutor per ADR-ARCH-014). Revisit if the multi-user posture changes or if the tutor process's asyncio loop becomes congested with background writes; neither is on the Phase 1 path.
- **Wait for a faster Graphiti stack (alternative graph store, smaller LLM for extraction) before broadening.** Rejected. ARCH-019 is a *correctness* fix relative to CC-13, not a performance optimisation. Even a 10× faster stack (still ~8s `add_episode`) would breach CC-08 / SR-08 if awaited on the caller path. The architectural rule should not depend on the absolute latency number.

## Consequences

**Positive:**
- Architecture decision now coextensive with CC-13. No contradiction between an async-write-back ADR and the cross-cutting concerns set.
- Every Graphiti write site has a uniform fire-and-forget shape, routed through one helper or `AsyncSubAgent` pattern. Easier to audit Phase 1 features against a single rule.
- `tutor_turn` p95 < 10s and `tutor_session_end` < 2s remain achievable even with `add_episode` median at 78.98s, because no caller-facing path awaits Graphiti.
- Removes a guaranteed future SR-08 violation: the prior ARCH-003 wording could have been read as licensing a synchronous mid-session write at some later feature (e.g. a "live" Coach misconception update). ARCH-019 closes that escape hatch.
- The 78.98s measurement is now load-bearing in two architecture artefacts (ARCH-018 / CC-13 and ARCH-019), not just a research note. Future readers see the same evidence from both the cross-cutting and per-decision angles.

**Negative:**
- Background-task bookkeeping now appears at multiple sites in the tutor, not just session-end. Mitigated by routing all sites through one helper (or `AsyncSubAgent`); no per-site bespoke code expected.
- A tutor crash now risks losing in-flight writes from any write point, not just the one session-end batch. Acceptable for Phase 1 MVP (single-user, no concurrent sessions; demo-window crash recovery is not load-bearing); revisit if real crashes appear during Phase 1 testing.
- ADR-ARCH-003 remains queryable as the historical session-end-only decision; readers must follow `superseded_by` to ARCH-019. Standard cost of temporal superseding.
- Three downstream architecture artefacts (`ARCHITECTURE.md`, `container.md`, `domain-model.md`) carry session-end-only language and are updated in this run; five design/planning artefacts are flagged stale and will be picked up by `/system-design` and `/feature-spec` on next run.

## Downstream artefacts flagged stale

The following artefacts reference the previous (session-end-only) framing and will be updated either in this run or by the next `/system-design` / `/feature-spec` pass:

**Updated in-place by this `/arch-refine`:**
- `docs/architecture/ARCHITECTURE.md` §"Phase 1" row and ADR index — Phase 1 description and ADR-ARCH-003 / ADR-ARCH-019 status entries.
- `docs/architecture/container.md` — MCP Adapter description, Coach AsyncSubAgent annotation, Coach → student_model relationship, Session → export relationship, "Enforces ADR-ARCH-003" reference.
- `docs/architecture/domain-model.md` §7.1 (`tutor_session_end` row) and §7.4 (write-back narrative + diagram caption).

**Flagged stale only — picked up by next `/system-design` / `/feature-spec`:**
- `docs/design/README.md` line 70 — references ADR-ARCH-003 for async events bus consistency.
- `docs/design/contracts/API-tutoring.md` lines 119, 133 — fire-and-forget classification rows still cite ADR-ARCH-003 explicitly.
- `docs/design/events-schema.yaml` lines 185–186 — references ADR-ARCH-003 session-end framing.
- `docs/planning/feature-roadmap.md` lines 74, 81, 100–102 — FEAT-PH1-001 dependency cites ADR-ARCH-003; SR-08 row uses session-end-only language; `/feature-spec` invocation hint references the old ADR file.
- `docs/gamification/design.md` line 482 — "atomic at session-end boundary" claim is too strong under ARCH-019 (writes are fire-and-forget at every point; atomicity is per-write, not session-scoped).

ADR-ARCH-003 itself remains queryable as the historical session-end-only decision; only its `Status` is updated to `superseded`. No content rewrite of ARCH-003.

## C4 diagram re-review status

System topology is **unchanged** by this refinement: same containers (MCP Adapter, Tutor Player, Coach AsyncSubAgent, Session Aggregate, Graphiti, Export channel), same external systems, same relationships. What changes is the *label text* on existing relationships (e.g. "writes confidence delta [P1 on session-end]" → "writes confidence delta [P1, async fire-and-forget]"). The mandatory C4 re-review gate is therefore not triggered; affected description strings inside `container.md` are refreshed in-place.

## References

- [ADR-ARCH-003](ADR-ARCH-003-async-graphiti-writeback.md) — superseded predecessor (session-end boundary only).
- [ADR-ARCH-018](ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) — promoted SR-08 to CC-13 and forecast this refinement.
- [ADR-ARCH-012](ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md) — `AsyncSubAgent` mechanism for CC-13 conformance.
- [ADR-ARCH-017](ADR-ARCH-017-tutor-start-session-sync-classification.md) — sync read-path classification corroborated by `search_nodes` 0.07s in the same spike.
- [ADR-ARCH-014](ADR-ARCH-014-single-user-scalability-posture.md) — single-user, single-process posture (constrains "no worker process" in this ADR).
- [graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md) — measured Graphiti latency, 2026-04-27.
- [phase-1-scope.md](../../research/ideas/phase-1-scope.md) §SR-08 — origin of the every-write-point requirement.
- DEC-02, DEC-08 in `docs/research/ideas/decisions-log-2026-04-17.md` — original Gemini-era latency assumptions, now superseded by the 2026-04-27 measurement.
- LES1 §4 — `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md` — fire-and-forget cross-agent rule (CC-08 origin).
