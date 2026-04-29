# DDR-002 — Coach AsyncSubAgent owns its own Graphiti writes; Tutor handler does not aggregate mid-session observations

## Status

Accepted

**Date:** 2026-04-27
**Phase:** Phase 1 (operative as Coach lands)
**Bounded context:** Tutoring
**Related:** [ADR-ARCH-012](../../architecture/decisions/ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md) (Coach AsyncSubAgent), [ADR-ARCH-019](../../architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) (every write point fire-and-forget), [ADR-ARCH-018](../../architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) (CC-12, CC-13), [DDR-003](DDR-003-session-completed-emits-on-state-transition.md), CC-08, [API-tutoring.md §3.2 Phase 1 evolution + §9 open question 4](../contracts/API-tutoring.md), [DM-tutoring.md §6 I-T7 + §11 flush points](../models/DM-tutoring.md), [graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md).

## Context

[ADR-ARCH-019](../../architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) commits the architecture to **fire-and-forget Graphiti writes at every write point** in the tutor: mid-session and session-end. The 2026-04-27 [latency spike](../../research/ideas/graphiti-latency-spike-results.md) measured `add_episode` median **78.98s**, which makes any synchronous wait on the caller-facing path infeasible (~15× the 5s SR-08 threshold, ~39× the `tutor_session_end` 2s handler budget).

ARCH-019 settles **whether** writes are async (yes, always) and **what failure mode** applies (log-only, no surface to caller). It does **not** settle **who** dispatches each write — specifically, whether mid-session observations the Coach makes (misconceptions, AO-scaffold gaps) are written:

1. **By the Coach itself** — the Coach `AsyncSubAgent` (per [ADR-ARCH-012](../../architecture/decisions/ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md)) calls the Graphiti write helper from inside its own task surface, dispatching one `add_episode` per misconception as it identifies it.
2. **By the Tutor handler aggregating Coach output** — the Coach exposes its observations on a per-turn return value, the Tutor handler collects them across the session, and a single batched flush happens at `tutor_session_end` (or at fixed mid-session checkpoints).
3. **By the Session Planner** — the Planner consumes Coach observations and decides which warrant a Graphiti write. Tutor handler stays out of the dispatch path entirely.

Position (2) is the natural reading of the prior ADR-ARCH-003 (session-end only, batched in the in-process aggregate). ARCH-019 supersedes ARCH-003 but does not explicitly close the question of ownership; it's a design-level choice about **flush-point ownership** that needs recording before Phase 1 PRs land or the answer drifts per-PR.

## Decision

**The Coach `AsyncSubAgent` owns its own Graphiti writes for mid-session misconception observations. The Tutor handler does not aggregate Coach output for batched flushing.**

Concretely:

- **Misconception writes (flush point F1, per [DM-tutoring.md §11](../models/DM-tutoring.md))** — dispatched by the Coach `AsyncSubAgent` from inside its own task surface using the shared Graphiti write helper. The Coach owns the `add_episode` call, owns the structured-log line on failure, and owns the `flush.F1` log dimension.
- **Planner topic-confidence updates (flush point F2)** — dispatched by the Tutor handler via `asyncio.create_task`, using the shared Graphiti write helper. The Planner emits the confidence-delta as a return value the handler consumes; the Planner does not own its own Graphiti dispatch in Phase 1. (If the Planner becomes its own deepagents component in a later phase, it migrates to AsyncSubAgent ownership too — recorded as open follow-up in `API-tutoring.md §9`.)
- **Session-end episode (flush point F3)** — dispatched by the Tutor handler at the `active → ended` state transition, also via `asyncio.create_task` and the shared Graphiti write helper.
- **The shared Graphiti write helper is the only point that calls `add_episode`.** Both the Coach AsyncSubAgent and the Tutor handler route through it. The helper is responsible for the structured-log line on failure (CC-13) and for the `flush.{F-id}` log dimension. There is no per-site bespoke `add_episode` call.
- **The Tutor handler does not buffer Coach observations across turns.** No session-scoped misconception list, no batched session-end flush of Coach output. Each Coach observation flushes independently from inside the Coach's task surface.

This decision is the design-level corollary of ARCH-019's "every write point" semantics: ARCH-019 says writes are uniform in *shape* (fire-and-forget, log-only failure); DDR-002 says they're also uniform in *ownership* (the agent that produces the observation dispatches the write).

## Rationale

- **Coach is already an `AsyncSubAgent` per [ADR-ARCH-012](../../architecture/decisions/ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md).** It already has its own task surface, its own life-cycle, and its own boundary for fire-and-forget work. Adding "writes its own observations" to that surface is the smallest extension. Aggregating Coach output back into the Tutor handler reintroduces a coupling ARCH-012 explicitly removes.
- **Aggregation reintroduces session-scoped buffering, which ARCH-019 explicitly rejected** (ARCH-019 §Alternatives considered: "Buffer all mid-session writes and flush at session-end (a generalisation of ARCH-003). Rejected for Phase 1. Adds session-scoped buffering machinery and concentrates the cost into a single fat session-end flush"). DDR-002 is the design-level affirmation of that architectural rejection: not only does the architecture not buffer, the design assigns ownership in a way that prevents buffering from being added later by accident.
- **One-write-per-observation matches the 78.98s latency profile** ([latency spike](../../research/ideas/graphiti-latency-spike-results.md)). Cost is spread across the session at the moment each misconception is observed, rather than concentrated in a fat session-end flush of N misconceptions × 78.98s. With a chatty session (e.g. 10 misconceptions), the batched session-end alternative would queue ~13 minutes of background work at `tutor_session_end`, all of which loses on a process crash.
- **Crash-recovery posture is unchanged from ARCH-019.** A crash mid-task loses the in-flight write at any flush point. With per-observation ownership, only one observation is in flight per task at a time per Coach instance; with batched session-end ownership, an entire session's worth of observations is in flight simultaneously. The per-observation shape minimises per-crash data loss.
- **The Planner is treated differently because it's not (yet) its own AsyncSubAgent.** In Phase 1, Planner logic lives inside the Tutor handler's per-turn flow. The Tutor handler dispatching its `flush.F2` write directly is the simpler shape until/unless the Planner becomes its own component. This is recorded as an open follow-up in `API-tutoring.md §9` open question 4.
- **The session-end episode (F3) is owned by the Tutor handler** because the `active → ended` state transition itself happens in the handler — the Coach has no view of the lifecycle event. Routing F3 through the same shared write helper as F2 keeps the helper as the single Graphiti dispatch surface.

## Alternatives considered

- **Position (2) — Tutor handler aggregates Coach output, single batched flush at session-end.** Rejected. ARCH-019 explicitly rejected this at the architecture level for the reasons quoted above. Reintroducing it as a design-level decision would contradict ARCH-019. It also concentrates crash-window risk and forces `tutor_session_end` to dispatch potentially several minutes of background work.

- **Position (3) — Session Planner owns all mid-session writes; Coach exposes observations as Planner inputs only.** Rejected for Phase 1. The Planner is not a separate deepagents component in Phase 1; it's per-turn handler-internal logic. Routing Coach observations through the Planner's "decision" loop adds a per-PR coupling between two components that don't otherwise need to know about each other and delays the Coach's write until the Planner runs (which may be once per turn, not once per observation). The Planner becomes a candidate owner if/when it migrates to its own AsyncSubAgent — captured as a follow-up.

- **Per-misconception synchronous write inside Coach.** Rejected. ARCH-019 is unconditional: every Graphiti write at every site is fire-and-forget. Even from inside an AsyncSubAgent, the call must dispatch via `asyncio.create_task` rather than `await` directly, because the AsyncSubAgent's own life-cycle should not stretch to ~79s per misconception. The shared write helper enforces this shape.

- **Defer the rule to per-PR review.** Rejected. The risk profile mirrors DDR-001's: a single Phase 1 PR that wires Coach output through the Tutor handler "for convenience" introduces session-scoped buffering by accident; rolling it back later is a non-trivial refactor of multiple PRs. Recording the rule once, with the F-id naming convention as a checkable artefact, is cheaper than re-litigating each Coach-touching PR.

## Consequences

**Positive:**
- Coach observations land in Graphiti with minimal lag from the moment of observation. No session-end batch delay.
- The Tutor handler stays small: it dispatches exactly two flush sites (F2 planner, F3 session-end) via the shared helper. Every other Graphiti write lives inside its producing agent.
- The shared Graphiti write helper has exactly one call shape across all flush points (`asyncio.create_task` from the Tutor handler, or `add_episode` invoked from inside an AsyncSubAgent's task) — auditable by single grep.
- Per-observation ownership minimises per-crash loss: at most one in-flight write per Coach instance, not a whole session's worth.
- Cost (~79s per write) is spread across the session, not concentrated at session-end. `tutor_session_end` returns within < 2s even after a Coach-heavy session.
- Symmetry with [DDR-003](DDR-003-session-completed-emits-on-state-transition.md): events emit on state transition; writes happen on observation. Both are decoupled from each other and from caller-facing handler returns.

**Negative:**
- More than one component now calls Graphiti directly (Coach AsyncSubAgent + shared helper invoked by Tutor handler). Mitigated: both go through the *same* shared helper, so the per-call shape and the failure logging path remain uniform.
- The Coach AsyncSubAgent now has a hard dependency on the shared Graphiti write helper (or on Graphiti directly via the helper). Acceptable: the Coach's purpose is to log observations to the student model; Graphiti is the student-model substrate. Refusing this dependency would require a separate intermediary that adds no value.
- A future component that produces observations (e.g. a per-AO tracker, a session-quality scorer) needs an explicit decision on ownership before it lands. Mitigated by `DM-tutoring.md §11` (the F-id table) and `API-tutoring.md §9` open question 6 — the design surface is set up to absorb a fourth flush site without re-litigating DDR-002.
- Crash recovery is per-write, not per-session. Acceptable for Phase 1 MVP per [ADR-ARCH-014](../../architecture/decisions/ADR-ARCH-014-single-user-scalability-posture.md); revisit if real crashes appear during Phase 1 testing.

## Affected artefacts

- [`docs/design/contracts/API-tutoring.md §3.2 (Phase 1 evolution)`](../contracts/API-tutoring.md) — references this DDR for misconception write ownership.
- [`docs/design/contracts/API-tutoring.md §9 (open question 4)`](../contracts/API-tutoring.md) — marked resolved by this DDR; Planner-to-AsyncSubAgent migration is the outstanding follow-up.
- [`docs/design/models/DM-tutoring.md §11 (flush-point table F1/F2/F3)`](../models/DM-tutoring.md) — names the three flush sites and their owners per this DDR.
- [`docs/design/models/DM-tutoring.md §6 I-T7`](../models/DM-tutoring.md) — invariant pinning the fire-and-forget shape.
- [`docs/design/models/DM-tutoring.md §9 (P1 fields deferred)`](../models/DM-tutoring.md) — `flush_history` discussed as conditional on a future supersession of this DDR.
- Phase 1 implementation surface (when it lands): the Coach AsyncSubAgent module, the shared Graphiti write helper, and the Tutor handler's `tutor_turn` / `tutor_session_end` paths must all go through the helper. No bespoke `add_episode` calls anywhere else in Tutoring.

## References

- [ADR-ARCH-012](../../architecture/decisions/ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md) — Coach AsyncSubAgent component definition.
- [ADR-ARCH-018](../../architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) — CC-12 (async-capable subagent boundary), CC-13 (every-write-point fire-and-forget).
- [ADR-ARCH-019](../../architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) — every-write-point async commitment + alternatives section that rejected session-end batching.
- [DDR-001](DDR-001-mcp-descriptions-do-not-enumerate-graphiti-writes.md) — sister rule: registered MCP description strings do not enumerate any of these writes.
- [DDR-003](DDR-003-session-completed-emits-on-state-transition.md) — sister rule: events emit on state transition, decoupled from Graphiti write success.
- [graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md) — 78.98s `add_episode` median that makes per-observation per-task dispatch necessary.
- [ADR-ARCH-014](../../architecture/decisions/ADR-ARCH-014-single-user-scalability-posture.md) — single-user single-process posture (constrains "no out-of-process queue" in this DDR).
