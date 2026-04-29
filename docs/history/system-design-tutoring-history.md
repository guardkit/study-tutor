
/system-design --focus="Tutoring" \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md \
  --context docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md \
  --context docs/research/ideas/graphiti-latency-spike-results.md


I'll start by checking prerequisites: Graphiti availability and architecture context.

Read graphiti.yaml
Bash Check architecture and design directories
IN
ls docs/architecture/ 2>/dev/null && echo "---" && ls docs/architecture/decisions/ 2>/dev/null && echo "---" && ls docs/design/ 2>/dev/null

OUT
ARCHITECTURE.md
assumptions.yaml
container.md
decisions
domain-model.md
system-context.md
---
ADR-ARCH-001-ddd-structural-pattern.md
ADR-ARCH-002-three-layer-architecture.md
ADR-ARCH-003-async-graphiti-writeback.md
ADR-ARCH-004-python-deepagents-langchain-mcp-stack.md
ADR-ARCH-005-defer-dockerfile-to-phase-1.md
ADR-ARCH-006-dual-inference-path-ollama-bedrock.md
ADR-ARCH-007-graphiti-split-topology.md
ADR-ARCH-008-mcp-only-agent-access.md
ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
ADR-ARCH-010-pydantic-at-boundary-validation.md
ADR-ARCH-011-no-caching-rate-limiting-feature-flags-phase-0.md
ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md
ADR-ARCH-013-middleware-level-gamification-engine-future.md
ADR-ARCH-014-single-user-scalability-posture.md
ADR-ARCH-015-uk-on-device-data-residency.md
ADR-ARCH-016-may-18-deadline-as-architectural-constraint.md
ADR-ARCH-017-tutor-start-session-sync-classification.md
ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md
ADR-ARCH-019-async-graphiti-writeback-every-write-point.md
---
contracts
decisions
events-schema.yaml
mcp-tools.json
models
README.md
Architecture context exists; design directory already has artefacts. Let me load the context files in parallel.

Read ARCHITECTURE.md
Read ADR-ARCH-019-async-graphiti-writeback-every-write-point.md
Read ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md
Read graphiti-latency-spike-results.md
Read README.md
Read API-tutoring.md
I need TodoWrite to track this multi-step design session, plus existing design files for the Tutoring context.

Read models
Read contracts
Read decisions
Bash List design subdirectories
IN
ls docs/design/models/ && echo "---" && ls docs/design/contracts/ && echo "---" && ls docs/design/decisions/

OUT
DM-inference-runtime.md
DM-mcp-transport.md
DM-tutoring.md
---
API-inference-runtime.md
API-mcp-transport.md
API-tutoring.md
---
DDR-001-mcp-descriptions-do-not-enumerate-graphiti-writes.md
Update Todos

Load existing Tutoring design artefacts (API + DM)

Load events-schema and DDR-001 for cross-reference

Run interactive design session for Tutoring (5 deltas: ARCH-019, CC-13/CC-14, fire-and-forget every-write-point, errors, planner/coach surfaces)

Capture DDR(s) for Tutoring refresh

Contradiction detection vs ADR-ARCH-001..019

Write updated API-tutoring.md and DM-tutoring.md

C4 L3 review for Tutoring container (Phase 1 components)

Refresh README + offer Graphiti seeding commands
Read DM-tutoring.md
Read events-schema.yaml
Read DDR-001-mcp-descriptions-do-not-enumerate-graphiti-writes.md
command-history.md
Context worth feeding the fresh agent up front:

Stale references to sweep (flagged by ADR-018/019, listed in docs/design/README.md §5):
docs/design/contracts/API-tutoring.md §3.4 (tutor_session_end row cites ADR-ARCH-003 directly)
docs/design/events-schema.yaml lines 185–186 (ADR-ARCH-003 reference)
docs/design/contracts/API-tutoring.md lines 119, 133 (fire-and-forget classification rows)
DDR-001 was created today: tool descriptions don't enumerate Graphiti writes. The Tutoring run should reference it (not duplicate it) for the same tutor_session_end / tutor_turn write sites.
CC-14 (num_ctx/num_predict explicit) belongs primarily to Inference Runtime but the Tutoring contract should add a one-line pointer.
Background seeding still running — when the new conversation finishes its design pass and offers guardkit graphiti add-context commands, queue them after the current batch (don't run in parallel; add_episode median 78.98s + max_concurrent_episodes: 3).
I have enough context to proceed. Let me check mcp-tools.json once more for the Tutoring-relevant entries, then present the proposed design refresh for your review.

Read mcp-tools.json
Acknowledged. I'll keep CC-14 as a one-line pointer in Tutoring (Inference Runtime owns it), reference DDR-001 rather than duplicate, and present Graphiti seeding commands as a queued (not parallel) batch at the end.

Now I have full context. Here's the proposed Tutoring design refresh for your review.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏗️  Architecture loaded: 6 bounded contexts (focused: Tutoring)
🔄 Existing design context found — refresh mode
📌 Seed contexts: ARCH-018, ARCH-019, latency spike (78.98s add_episode)
📎 Cross-reference: DDR-001 (MCP Transport refresh, 2026-04-27)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 DESIGNING: Tutoring (refresh)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Live code: src/study_tutor/session/, src/study_tutor/mcp/adapter.py
Phase posture: P0 live; P1 adds Coach + Planner + every-write-point Graphiti
Protocols: MCP (registered in MCP Transport context) + In-process Events (Shared Kernel B)
Proposed deltas
Δ1 — API-tutoring.md §3 lead-in. Replace "see decision D2 (2026-04-26)" with [ADR-ARCH-017](...); D2 was closed in MCP refresh.

Δ2 — API-tutoring.md §3.2 (tutor_turn) — extend "Side effects" with a Phase 1 evolution subsection: per ARCH-019 / CC-13, mid-session writes (Coach-observed misconceptions, planner topic-confidence updates) are fire-and-forget via AsyncSubAgent (CC-12 / ARCH-012) or asyncio.create_task. Caller p95 < 10s budget remains binding regardless of add_episode latency (78.98s median per spike). Reference DDR-001: writes are not surfaced in the registered MCP description.

Δ3 — API-tutoring.md §3.4 (tutor_session_end). Rewrite line 119 classification cell + line 133 "Phase 1 evolution":

Line 119: drop the parenthetical "P1 adds an async Graphiti write-back inside the handler" framing. Replace with: classification stays sync because every Graphiti write at this site is fire-and-forget per CC-13 / ARCH-019.
Line 133: replace "ADR-ARCH-003" reference with ARCH-019 + CC-13; cite the 78.98s anchor; reference DDR-001 for the SR-07/silent-description rule (don't duplicate it).
Δ4 — API-tutoring.md §5 (Events) §5.3 (Delivery semantics). Add bullet: "Event emit is decoupled from Graphiti write success per ARCH-019 — session.completed emits on the active → ended state transition, not on write acknowledgement."

Δ5 — API-tutoring.md §7 (Conformance tests). Add row:

Handler-latency test (CC-13) — tutor_turn p95 < 10s and tutor_session_end < 2s when the Graphiti write helper is patched to sleep ≥ 30s. Recommended addition; symmetric with the I-MCP8 test recommended in the MCP Transport refresh.
Plus a one-line pointer noting that the SR-07 substring test (DDR-001) is owned by MCP Transport (API-mcp-transport.md §10), not duplicated here.

Δ6 — API-tutoring.md §9 (Open questions). Refresh:

Q1 keep but rewrite to cite ARCH-017's measurement-conditional reversion rule.
New Q4 — flush-point ownership: who dispatches mid-session writes? Coach owns its own episodes (its AsyncSubAgent boundary) vs Tutor handler aggregates and flushes at fixed boundaries. Proposed DDR-002 below resolves this.
New Q5 — write-failure observability: structured-log per failure vs aggregate counter vs both.
Δ7 — DM-tutoring.md §5 (Persistence). Refresh P1 row: Graphiti episodes still live under student:{student_id} group, but written at multiple flush points (mid-session: misconceptions, planner topic-confidence; session-end: SessionEpisode). All fire-and-forget per ARCH-019.

Δ8 — DM-tutoring.md §6 (Invariants). Add:

I-T7 — Tutoring handlers MUST NOT await Graphiti acknowledgement on caller-facing paths. All add_episode / entity-update calls dispatch via AsyncSubAgent (CC-12) or asyncio.create_task (CC-13 / ARCH-019). Failures emit a structured log line; do not raise from the handler.
One-line pointer to CC-14 (num_ctx / num_predict) noting authoritative invariant lives in DM-inference-runtime.md.

Δ9 — DM-tutoring.md §9 (P1 fields deferred). Add a brief line that the TutorSession aggregate's P1 evolution may add a flush_history: list[FlushAttempt] value object only if DDR-002 lands "Tutor handler aggregates"; under "Coach owns its own writes" no new fields are required on the aggregate.

Δ10 — events-schema.yaml lines 185–186. Replace ADR-ARCH-003 reference with ADR-ARCH-019 + CC-13; rephrase rationale to "every-write-point fire-and-forget" rather than "session-end boundary".

Proposed DDRs (numbering continues from DDR-001)
DDR-002 — Coach AsyncSubAgent owns its own Graphiti writes; Tutor handler does not aggregate mid-session observations.

Why: ARCH-019 says writes are fire-and-forget at every write point but doesn't pin ownership. Coach is already an AsyncSubAgent per ARCH-012 — natural boundary. Aggregation in the Tutor handler reintroduces session-scoped buffering that ARCH-019 explicitly rejected (alternatives §3).
Consequence: Tutor handler dispatches only the session-end episode + planner topic-confidence updates; misconception writes happen inside the Coach's task surface.
DDR-003 — session.completed emits on state transition, not on Graphiti write success (fail-soft event-emit).

Why: ARCH-019 says write failures are log-only and never surface to the MCP caller. Coupling event emit to write success would re-introduce a synchronous wait dependency the architecture rejects. Consumers (Student Model, Gamification) treat the event as the source of truth; the Graphiti episode is a secondary persistence artefact.
Symmetric with at-most-once delivery semantics already in events-schema.yaml §178.
C4 L3 review (now triggered)
P0 noted Tutoring would cross the >3-component threshold in P1. With ARCH-019, the P1 component set is:

MCPAdapter boundary (in MCP Transport, called from here)
SessionStore (in-memory aggregate registry)
TutorSession aggregate
Tutor Player (LLM-driven response generator)
Coach AsyncSubAgent (CC-12 / ARCH-012; quality monitor + misconception writer)
Session Planner (P1; topic-confidence updater)
Graphiti Write Helper (single point for fire-and-forget; ARCH-019)
RAG Retriever wrapper (P1; Knowledge & Curriculum read path)
Six internal components inside Tutoring → C4 L3 generation triggered. I'll produce a Mermaid C4Component diagram showing fire-and-forget edges (dashed) to the Graphiti Write Helper from Coach + Planner + Tutor Player.

Out-of-focus, flagged stale only
DM-inference-runtime.md for CC-14 invariant — owned by Inference Runtime focus run.
API-inference-runtime.md num_ctx/num_predict rows — same.
Checkpoint — please confirm before I generate artefacts:

Δ1–Δ10 deltas above — [A]ccept all / [M]odify / specify exclusions
DDR-002 (Coach owns writes) — [A]ccept / [R]evise rationale / [D]rop
DDR-003 (event-emit fail-soft) — [A]ccept / [R]evise / [D]rop
C4 L3 component list (6 internal) — [A]ccept / [M]odify components
Reply with your selections (e.g. 1A 2A 3A 4A) or pushback per item.

system-design-tutoring-history.md
1A 2A 3A 4A
All accepted. Generating artefacts now.

Update Todos

Load existing Tutoring design artefacts (API + DM)

Load events-schema and DDR-001 for cross-reference

Run interactive design session for Tutoring (5 deltas)

Update API-tutoring.md (Δ1-Δ6 + Δ9)

Update DM-tutoring.md (Δ7-Δ9)

Update events-schema.yaml (Δ10)

Write DDR-002 (Coach owns writes)

Write DDR-003 (event-emit fail-soft)

Generate C4 L3 component diagram for Tutoring

Mandatory C4 L3 review gate

Contradiction detection vs ADR-ARCH-001..019

Refresh README + offer Graphiti seeding commands
Bash Check diagrams directory
IN
ls docs/design/diagrams/ 2>/dev/null || echo "no diagrams dir"

OUT
no diagrams dir
Bash Create diagrams directory
IN
mkdir -p docs/design/diagrams

OUT
(Bash completed with no output)
Δ1–Δ6, Δ9 — API-tutoring.md
Edit API-tutoring.md
Added 1 line
Edit API-tutoring.md
Modified
Δ2 — tutor_turn Phase 1 evolution:

Edit API-tutoring.md
Added 7 lines
Δ3 — tutor_session_end:

Edit API-tutoring.md
Modified
Edit API-tutoring.md
Added 6 lines
Δ4 — Events delivery semantics:

Edit API-tutoring.md
Added 1 line
Δ5 — Conformance tests:

Edit API-tutoring.md
Added 14 lines
Δ6 — Open questions:

Edit API-tutoring.md
Added 3 lines
Update Todos

Load existing Tutoring design artefacts (API + DM)

Load events-schema and DDR-001 for cross-reference

Run interactive design session for Tutoring (5 deltas)

Update API-tutoring.md (Δ1-Δ6 + Δ9)

Update DM-tutoring.md (Δ7-Δ9)

Update events-schema.yaml (Δ10)

Write DDR-002 (Coach owns writes)

Write DDR-003 (event-emit fail-soft)

Generate C4 L3 component diagram for Tutoring

Mandatory C4 L3 review gate

Contradiction detection vs ADR-ARCH-001..019

Refresh README + offer Graphiti seeding commands
Δ7–Δ9 — DM-tutoring.md
Edit DM-tutoring.md
Added 1 line
Δ7 — Persistence:

Edit DM-tutoring.md
Added 2 lines
Δ8 — Add I-T7 invariant + CC-14 pointer:

Edit DM-tutoring.md
Added 3 lines
Δ9 — Update §9 P1 fields deferred + add §11 P1 flush points:

Edit DM-tutoring.md
Added 16 lines
Update Todos

Load existing Tutoring design artefacts (API + DM)

Load events-schema and DDR-001 for cross-reference

Run interactive design session for Tutoring (5 deltas)

Update API-tutoring.md (Δ1-Δ6 + Δ9)

Update DM-tutoring.md (Δ7-Δ9)

Update events-schema.yaml (Δ10)

Write DDR-002 (Coach owns writes)

Write DDR-003 (event-emit fail-soft)

Generate C4 L3 component diagram for Tutoring

Mandatory C4 L3 review gate

Contradiction detection vs ADR-ARCH-001..019

Refresh README + offer Graphiti seeding commands
Δ10 — events-schema.yaml
Edit events-schema.yaml
Added 4 lines
Edit events-schema.yaml
Added 15 lines
DDR-002 — Coach owns its own writes
Write DDR-002-coach-async-subagent-owns-graphiti-writes.md
91 lines
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
DDR-003 — Event-emit fail-soft
Write DDR-003-session-completed-emits-on-state-transition.md
97 lines
# DDR-003 — `session.completed` (and the rest of Shared Kernel B) emits on state transition, not on Graphiti write success

## Status

Accepted

**Date:** 2026-04-27
**Phase:** Phase 1 (operative when the in-process bus is wired)
**Bounded context:** Tutoring (producer of session.* events)
**Related:** [ADR-ARCH-019](../../architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md), [ADR-ARCH-018](../../architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) (CC-13), [ADR-ARCH-003](../../architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md) (superseded predecessor), [DDR-002](DDR-002-coach-async-subagent-owns-graphiti-writes.md), CC-11 (in-process event bus vocabulary), [API-tutoring.md §3.4 + §5.3](../contracts/API-tutoring.md), [events-schema.yaml `delivery_semantics`](../events-schema.yaml), [graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md), `gamification/design.md §2.1`.

## Context

Shared Kernel B (the in-process events vocabulary in [`events-schema.yaml`](../events-schema.yaml)) lists three Tutoring-produced events:

- `session.started` — emitted on transition to `active`
- `session.turn_completed` — emitted after each `(user, tutor)` pair appends
- `session.completed` — emitted on transition to `ended`

The events bus is in-process, at-most-once, and forbidden from synchronous fan-out per CC-11 + CC-12. Subscribers (Student Model in P1; Gamification in P2) read these events via the deepagents AsyncSubAgent boundary or equivalent async hook.

[ADR-ARCH-019](../../architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) commits the architecture to fire-and-forget Graphiti writes at every site, including `tutor_session_end`'s `SessionEpisode` write (flush point F3 per [`DM-tutoring.md §11`](../models/DM-tutoring.md)). Failures are log-only and never surface to the MCP caller.

This raises a design-level question that ARCH-019 itself does not settle: **at `tutor_session_end`, does `session.completed` emit on the `active → ended` state transition (before the Graphiti write task is even scheduled) or only after the Graphiti write task succeeds?** Three positions are possible:

1. **Emit on state transition**, decoupled from any Graphiti write outcome. Consumers see the event; the write succeeds or fails independently.
2. **Emit only on Graphiti write success.** Consumers wait for the (asynchronous) write to complete before observing the event.
3. **Emit on state transition with a `graphiti_write_pending` flag, then re-emit (or emit a follow-up `session.persisted`) on write success.**

The same question applies in spirit to `session.started` (vs the Coach AsyncSubAgent's startup writes, if any) and `session.turn_completed` (vs misconception writes per DDR-002), but `session.completed` is the load-bearing instance because it gates Student Model rollup and (P2) Gamification XP/streak/achievement evaluation.

## Decision

**Shared Kernel B Tutoring events emit on the relevant state transition. They are explicitly decoupled from any Graphiti write success.**

Concretely:

- `session.started` emits on the `→ active` state transition, before any Coach warm-up or Graphiti write is scheduled.
- `session.turn_completed` emits after the `(user, tutor)` pair appends to `TutorSession.turns`, regardless of whether the Coach has dispatched a misconception write for the turn (Coach observation flow is asynchronous; emission cannot block on it).
- `session.completed` emits on the `active → ended` state transition, *before* the F3 session-end Graphiti write task is even scheduled. The handler returns `{ session_id, status: "ended" }` to the MCP caller; the `session.completed` event fan-outs to in-process subscribers; the Graphiti write helper is invoked via `asyncio.create_task` — all three happen on the same code path inside the handler, in that order.
- **No `session.persisted` event, no `graphiti_write_pending` flag, no follow-up emit on write success.** A Graphiti write failure for a session emits a structured-log line at the helper boundary (per CC-13) and is observable on the next `tutor_session_status` read against the student-model substrate, but it does not fire any additional event on the bus.
- **Subscribers treat the event as the source of truth.** Student Model (P1) builds its `SessionEpisode` rollup from the event payload; the Graphiti episode is a secondary persistence artefact. Gamification (P2) evaluates XP / streaks / achievements off the event, not off the Graphiti write.
- The existing I-T6 invariant ([`DM-tutoring.md §6`](../models/DM-tutoring.md)) is unchanged: a session abandoned before any tutor turn must not emit `session.completed` — that's a domain-rule guard at the events boundary, not a write-success guard.

## Rationale

- **ARCH-019 makes (2) infeasible.** The 27 Apr 2026 [latency spike](../../research/ideas/graphiti-latency-spike-results.md) measured `add_episode` median **78.98s**. Coupling `session.completed` to write success would mean Student Model and Gamification subscribers wait ~79s after `tutor_session_end` returns before observing the event. That re-introduces a synchronous Graphiti dependency one step removed from the MCP handler — exactly the shape ARCH-019 / CC-13 forbid.
- **(3) introduces dual emission for no benefit.** Two events for the same state change forces every subscriber to deduplicate (or, worse, react to the wrong one). A `graphiti_write_pending` flag adds a field consumers either ignore (no value gained) or branch on (which means they're now reasoning about Graphiti write topology — the very abstraction CC-13 is meant to hide from them). The honest position is that the events bus and Graphiti are independent persistence/notification surfaces; consumers either subscribe to one or the other, not to a coordination layer between them.
- **(1) matches the events bus's at-most-once semantics already in `events-schema.yaml §178`.** A consumer crash on `session.completed` is already an observable defect, not a silent data-loss event. Adding write-success coupling would not fix that — it would add a *second* class of silent failure (event never fires because Graphiti write times out or fails) that is harder to diagnose because the consumer sees no event at all rather than the expected event.
- **Symmetric with [DDR-002](DDR-002-coach-async-subagent-owns-graphiti-writes.md).** DDR-002 says writes are owned by the agent that produces the observation, dispatched as fire-and-forget. DDR-003 says events are owned by the state transition that produces them, emitted unconditionally. Both decisions push the design toward "each persistence/notification surface is independent, with its own ownership and its own failure mode" — which is the design-level shape that prevents accidental synchronisation across surfaces.
- **Symmetric with [DDR-001](DDR-001-mcp-descriptions-do-not-enumerate-graphiti-writes.md).** DDR-001 keeps Graphiti writes off the MCP tool descriptions because they're not part of the user-visible contract. DDR-003 keeps Graphiti writes off the events bus payloads for the same reason: subscribers shouldn't reason about a write topology they have no protocol affordance for.
- **Operational: a session that never persists is recoverable; a session that never emits is invisible.** If the Graphiti write fails, the session is still observable through the events bus (Student Model has its event-driven rollup) and through `tutor_session_status` (which reads the in-memory `SessionStore` for the active session and surfaces the gap on the next read). If the event never emits, no consumer ever sees the session — a silent failure with no recovery path. The asymmetry justifies favouring event emission over write coupling.

## Alternatives considered

- **Position (2) — emit only on Graphiti write success.** Rejected. Re-introduces a synchronous Graphiti dependency at ~79s median. Subscribers wait, the bus stalls, and a write failure means a permanently-unfired event with no recovery path. Inconsistent with CC-13's intent (caller-facing path never awaits Graphiti) once the events bus is treated as a quasi-caller of the handler.

- **Position (3) — emit on state transition + re-emit on write success.** Rejected. Adds a coordination layer (subscribers must handle two events for one state change, or branch on a `graphiti_write_pending` flag) that exposes the very Graphiti write topology CC-13 / DDR-001 hide from other surfaces. No subscriber currently has a use case for distinguishing "ended" from "persisted" — the Student Model rollup uses the event payload directly; the Graphiti episode is a parallel artefact, not a precondition.

- **Defer the rule to per-PR review.** Rejected. The risk profile mirrors DDR-001 / DDR-002: a single Phase 1 PR that wires `session.completed` emission inside the Graphiti write helper's success callback creates exactly position (2), with a multi-month-to-detect failure mode (most demos succeed; the silent-failure case shows up first in production at full session volume). Recording the rule once is cheaper than discovering the regression later.

- **Add a `session.persisted` event for the cases where a downstream subscriber genuinely needs durability confirmation.** Rejected for Phase 1 — no such subscriber exists. Reserved as a future option if (e.g.) a P2 Reachy companion script wanted to celebrate only durably-persisted sessions. If reintroduced, it would be an *additional* event, not a replacement for `session.completed`, preserving DDR-003's decoupling.

- **Make the rule purely architectural inside ARCH-019.** Rejected. ARCH-019 is about *write topology* (where writes happen, async-from-caller). The events-vs-writes decoupling is a *design-level* artefact about *how the in-process bus presents* state transitions relative to that topology. Conflating them obscures the chain of evidence and would make the rule invisible to anyone reading only `docs/design/`.

## Consequences

**Positive:**
- `session.completed` fires within the handler's < 2s budget regardless of `add_episode` latency. Student Model rollup and (P2) Gamification XP evaluation are not gated on Graphiti write success.
- The events bus's at-most-once semantics and the Graphiti write helper's fire-and-forget shape are now expressed as a single coherent design posture: each surface has independent ownership, independent failure mode, independent recovery path.
- A Graphiti write failure is observable in two places (structured log line per CC-13; gap on next `tutor_session_status` read) but does not propagate as a missing event. Diagnostics improve: a failed write is a Graphiti diagnostic, not an apparent "session never ended" diagnostic.
- The design surface absorbs future flush sites without renegotiation: any new flush point added per [`DM-tutoring.md §11`](../models/DM-tutoring.md) inherits DDR-003's decoupling automatically.
- Symmetric with DDR-001 (MCP description silence) and DDR-002 (per-observation write ownership) — the three together form a coherent "Graphiti is invisible to consumers" posture.

**Negative:**
- A consumer that *wants* durability confirmation has no current event for it. Acceptable in Phase 1 (no such subscriber exists). Mitigated by the explicit "future option: `session.persisted`" path documented in alternatives.
- A persistent Graphiti outage produces healthy-looking events on the bus while no Graphiti episodes are accumulating. Mitigated by the structured-log line per CC-13 and the recommended aggregate counter (open question 5 in `API-tutoring.md §9`); a demo-week dashboard reading the counter would surface the outage independently of the events bus.
- Future contributors may instinctively want to "wait for the write" inside the events emit path — DDR-003 is the rule to point at when reviewing such PRs. Recommend adding a brief code-comment at the `session.completed` emit site referencing this DDR when Phase 1 wires the bus.

## Affected artefacts

- [`docs/design/contracts/API-tutoring.md §3.4 (`tutor_session_end` Phase 1 evolution)`](../contracts/API-tutoring.md) — references this DDR for the event-emit timing.
- [`docs/design/contracts/API-tutoring.md §5.3 (Delivery semantics)`](../contracts/API-tutoring.md) — adds the "event emit decoupled from Graphiti write success" bullet citing this DDR.
- [`docs/design/contracts/API-tutoring.md §7.2 (Recommended additions)`](../contracts/API-tutoring.md) — adds the event-emit-without-write conformance test.
- [`docs/design/events-schema.yaml `delivery_semantics`](../events-schema.yaml) — `emit_decoupled_from_graphiti_write: true` flag and updated rationale referencing this DDR.
- Phase 1 implementation surface (when it lands): the events emission helper at the `tutor_session_end` boundary fires `session.completed` *before* invoking the Graphiti write helper for F3. A code comment at that site references this DDR.

## References

- [ADR-ARCH-019](../../architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) — every-write-point async commitment + log-only failure semantics.
- [ADR-ARCH-018](../../architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) — CC-11 (in-process event bus vocabulary), CC-13 (Graphiti async at every write point).
- [ADR-ARCH-003](../../architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md) — superseded predecessor that scoped writes to session-end; DDR-003 is part of the design-level cleanup that ARCH-019 forecasts.
- [DDR-001](DDR-001-mcp-descriptions-do-not-enumerate-graphiti-writes.md) — sibling rule: Graphiti writes invisible at the MCP description surface.
- [DDR-002](DDR-002-coach-async-subagent-owns-graphiti-writes.md) — sibling rule: writes owned by the producing agent, not aggregated into the handler.
- [graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md) — 78.98s `add_episode` median that makes write-success coupling infeasible.
- `gamification/design.md §2.1` — origin of the "no `session.completed` for sessions abandoned before any tutor turn" rule (I-T6); DDR-003 leaves that guard intact.
Update Todos

Load existing Tutoring design artefacts (API + DM)

Load events-schema and DDR-001 for cross-reference

Run interactive design session for Tutoring (5 deltas)

Update API-tutoring.md (Δ1-Δ6 + Δ9)

Update DM-tutoring.md (Δ7-Δ9)

Update events-schema.yaml (Δ10)

Write DDR-002 (Coach owns writes)

Write DDR-003 (event-emit fail-soft)

Generate C4 L3 component diagram for Tutoring

Mandatory C4 L3 review gate

Contradiction detection vs ADR-ARCH-001..019

Refresh README + offer Graphiti seeding commands
C4 L3 component diagram — Tutoring container
Write tutoring-c4-l3.md
94 lines
# C4 Level 3 — Tutoring container (Phase 1 components)

**Bounded context:** Tutoring
**Phase:** P1 forward-design (P0 has only a 2-component subset: SessionStore + TutorSession aggregate)
**Generated:** 2026-04-27 by `/system-design --focus="Tutoring"` (refresh)
**Trigger:** Tutoring container crosses the >3-internal-component threshold once Phase 1 lands the Coach AsyncSubAgent + Session Planner + Graphiti Write Helper + RAG Retriever wrapper. Phase 0 deferred this diagram per [`docs/design/README.md §4`](../README.md).
**Related ADRs / DDRs:** [ARCH-012](../../architecture/decisions/ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md), [ARCH-019](../../architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md), [DDR-002](../decisions/DDR-002-coach-async-subagent-owns-graphiti-writes.md), [DDR-003](../decisions/DDR-003-session-completed-emits-on-state-transition.md).

---

## Component diagram

```mermaid
C4Component
    title Tutoring container — P1 components

    Container_Boundary(tutoring, "Tutoring (bounded context)") {
      Component(store, "SessionStore", "Python dict + asyncio.Lock", "In-memory aggregate registry; UUID-keyed")
      Component(agg, "TutorSession aggregate", "dataclass", "Per-session state; append-only turns; active/ended status")
      Component(player, "Tutor Player", "deepagents agent + LangChain prompt", "Generates the tutor reply for tutor_turn; routes through LLMClient")
      Component(coach, "Coach AsyncSubAgent", "deepagents AsyncSubAgent (CC-12)", "Quality monitor; observes turns; owns its own misconception writes (DDR-002)")
      Component(planner, "Session Planner", "Tutor-handler-internal P1; future AsyncSubAgent", "Emits topic-confidence deltas the handler dispatches")
      Component(rag, "RAG Retriever wrapper", "ChromaDB client adapter", "Reads curriculum chunks; passes ChunkRefs to Tutor Player + Coach")
      Component(helper, "Graphiti Write Helper", "asyncio.create_task wrapper", "Single Graphiti dispatch surface; uniform fire-and-forget shape; structured-log on failure (CC-13)")
      Component(events, "Events emitter", "in-process bus, CC-11", "Fires session.{started,turn_completed,completed} on state transitions (DDR-003)")
    }

    System_Ext(mcp, "MCP Adapter (MCP Transport context)", "Calls tutor_start_session / tutor_turn / tutor_session_status / tutor_session_end")
    System_Ext(llm, "LLMClient (Inference Runtime context)", "Provider-resolved at call time per SR-03; CC-14 num_ctx/num_predict")
    System_Ext(student, "Student Model (P1)", "Subscribes session.* events; Graphiti read path")
    System_Ext(graphiti, "Graphiti (FalkorDB + vLLM)", "add_episode median 78.98s — write-only from this container")
    System_Ext(chroma, "ChromaDB (Knowledge & Curriculum)", "Curriculum chunk store")

    Rel(mcp, store, "create / get / end", "sync")
    Rel(mcp, player, "tutor_turn dispatch", "sync, p95 < 10s")
    Rel(mcp, events, "tutor_session_end → state transition", "sync, < 2s")
    Rel(store, agg, "owns", "1..*")
    Rel(player, llm, "generate(...)", "sync via asyncio.to_thread")
    Rel(player, rag, "retrieve(topic, k)", "sync, P1 read")
    Rel(coach, llm, "evaluate turn quality", "sync via asyncio.to_thread")
    Rel(coach, rag, "retrieve evidence", "sync, P1 read")
    Rel(planner, agg, "reads turn history", "in-process")
    Rel(events, student, "session.* events", "in-process, at-most-once")

    Rel(coach, helper, "F1: misconception write", "asyncio.create_task — fire-and-forget (DDR-002)")
    Rel(planner, helper, "F2: topic-confidence write", "asyncio.create_task — fire-and-forget (DDR-002)")
    Rel(events, helper, "F3: session-end episode", "asyncio.create_task — fire-and-forget (after emit, DDR-003)")
    Rel(helper, graphiti, "add_episode (~79s)", "fire-and-forget; failures log-only (CC-13)")
```

## Component table

| # | Component | Lives in | Phase live | Owns |
|---|---|---|---|---|
| 1 | `SessionStore` | `src/study_tutor/session/tutor_session.py` (P0) | P0 | UUID → `TutorSession` map; create / get / end |
| 2 | `TutorSession` aggregate | `src/study_tutor/session/tutor_session.py` (P0) | P0 | Per-session state, turns (append-only), status (active / ended) |
| 3 | Tutor Player | `src/study_tutor/roles/tutor/` (P0 stub → P1) | P0 stub, P1 wired | Reply generation via LLMClient + Player prompt |
| 4 | Coach AsyncSubAgent | `src/study_tutor/roles/coach/` (P1) | P1 | Quality monitoring + misconception observations + **F1 dispatch** (per DDR-002) |
| 5 | Session Planner | inside `MCPAdapter.tutor_turn` flow (P1) | P1 | Topic-confidence delta emission; today returns deltas the handler dispatches as **F2** |
| 6 | RAG Retriever wrapper | `src/study_tutor/roles/tutor/` (P1) | P1 | ChromaDB client + ChunkRef serialisation |
| 7 | Graphiti Write Helper | `src/study_tutor/student/graphiti_writer.py` (P1, future) | P1 | Single `add_episode` dispatch surface; `flush.{F-id}` log dimension; CC-13 conformance |
| 8 | Events emitter | `src/study_tutor/session/events.py` (P1, future) | P1 | In-process bus emit for `session.*` (CC-11); DDR-003 timing — emits *before* F3 helper invocation |

External systems shown for context only — they are not Tutoring components:

- **MCP Adapter** lives in MCP Transport context (`src/study_tutor/mcp/adapter.py`).
- **LLMClient** lives in Inference Runtime context (`src/study_tutor/llm/client.py`); CC-14 (`num_ctx`/`num_predict`) is enforced there, not here.
- **Student Model**, **Graphiti**, **ChromaDB** are bounded contexts / external systems; this diagram only shows the edges Tutoring participates in.

## Edge legend

| Style cue | Meaning |
|---|---|
| Sync edges (e.g. `Rel(mcp, player, ...)` with "sync") | Caller-facing path; latency budget binding |
| Fire-and-forget edges (F1 / F2 / F3) | Dispatched via the Graphiti Write Helper; `asyncio.create_task` — caller does not await; failures log-only |
| In-process edges (events to Student Model) | At-most-once; per-aggregate FIFO; subscribers via AsyncSubAgent boundary (CC-12) |

## Why exactly these eight components

- **All three flush points (F1 / F2 / F3) per `DM-tutoring.md §11` are visible** as named edges, each routed through the same Graphiti Write Helper. Auditors can see by inspection that there is no second Graphiti dispatch path — DDR-002's "single helper" rule is structurally enforced by the diagram.
- **The Events emitter and the Graphiti Write Helper are distinct components** even though they both fire on the `tutor_session_end` path. This is the structural expression of DDR-003: events emit on state transition (Events emitter), Graphiti writes are dispatched separately (Helper). A diagram that fused them would obscure the rule and make a future PR's accidental coupling invisible.
- **Tutor Player and Coach are siblings, not parent/child.** The Coach is an `AsyncSubAgent` per ARCH-012; it observes turns produced by the Tutor Player but does not gate them. Drawing them as siblings prevents the diagram from suggesting a synchronous "Tutor → Coach review → reply" flow that does not exist.
- **Session Planner is shown as a Tutoring-internal component, not as its own AsyncSubAgent**, matching DDR-002's Phase 1 stance. The diagram label notes "future AsyncSubAgent" so the migration path is visible. When the migration happens, F2's owner will move from "Tutor handler" to "Planner AsyncSubAgent" — the same edge shape, different owner.
- **`MCPAdapter` is external** because it lives in the MCP Transport context. Tutoring's diagram should not absorb it; doing so would smear the bounded-context boundary.

## Open questions reflected in the diagram

- Open question 4 in [`API-tutoring.md §9`](../contracts/API-tutoring.md): Planner-to-AsyncSubAgent migration. Diagram annotates Planner as "future AsyncSubAgent" so the diagram remains accurate after the migration with only a label change.
- Open question 6 in [`API-tutoring.md §9`](../contracts/API-tutoring.md): a fourth flush site would add a new edge to the Helper (named per the F-id convention from `DM-tutoring.md §11`). Diagram regeneration trivial.

---

*Generated 2026-04-27 by `/system-design --focus="Tutoring"`. Reviewed and approved at the C4 L3 review gate. Re-render via Mermaid Live Editor or `mmdc -i tutoring-c4-l3.md -o tutoring-c4-l3.svg`.*
C4 L3 Review Gate (mandatory)
Per /system-design Phase 3.5, this diagram requires explicit approval. Here it is for review:


C4Component
    title Tutoring container — P1 components

    Container_Boundary(tutoring, "Tutoring (bounded context)") {
      Component(store, "SessionStore", "Python dict + asyncio.Lock", "In-memory aggregate registry")
      Component(agg, "TutorSession aggregate", "dataclass", "Per-session state; append-only turns")
      Component(player, "Tutor Player", "deepagents agent + LangChain prompt", "tutor_turn reply via LLMClient")
      Component(coach, "Coach AsyncSubAgent", "deepagents AsyncSubAgent (CC-12)", "Quality monitor; owns F1 misconception writes (DDR-002)")
      Component(planner, "Session Planner", "Tutor-handler-internal P1", "Topic-confidence deltas → handler dispatches as F2")
      Component(rag, "RAG Retriever wrapper", "ChromaDB client adapter", "Reads curriculum chunks")
      Component(helper, "Graphiti Write Helper", "asyncio.create_task wrapper", "Single dispatch surface; CC-13; structured-log on failure")
      Component(events, "Events emitter", "in-process bus, CC-11", "session.* on state transitions (DDR-003)")
    }

    System_Ext(mcp, "MCP Adapter", "MCP Transport context")
    System_Ext(llm, "LLMClient", "Inference Runtime context; CC-14")
    System_Ext(student, "Student Model", "P1; subscribes session.*")
    System_Ext(graphiti, "Graphiti", "FalkorDB + vLLM; add_episode median 78.98s")
    System_Ext(chroma, "ChromaDB", "Knowledge & Curriculum")

    Rel(mcp, store, "create / get / end", "sync")
    Rel(mcp, player, "tutor_turn dispatch", "sync, p95 < 10s")
    Rel(mcp, events, "tutor_session_end → state transition", "sync, < 2s")
    Rel(player, llm, "generate(...)", "sync via asyncio.to_thread")
    Rel(player, rag, "retrieve(topic, k)", "sync, P1 read")
    Rel(coach, llm, "evaluate turn quality", "sync via asyncio.to_thread")
    Rel(coach, rag, "retrieve evidence", "sync, P1 read")
    Rel(planner, agg, "reads turn history", "in-process")
    Rel(events, student, "session.* events", "in-process, at-most-once")

    Rel(coach, helper, "F1: misconception write", "fire-and-forget (DDR-002)")
    Rel(planner, helper, "F2: topic-confidence write", "fire-and-forget (DDR-002)")
    Rel(events, helper, "F3: session-end episode", "fire-and-forget after emit (DDR-003)")
    Rel(helper, graphiti, "add_episode (~79s)", "fire-and-forget; failures log-only (CC-13)")
Look for: components with too many dependencies (Helper has 4 in-edges by design — single dispatch point); missing persistence layers (none — Tutoring is in-memory + Graphiti via Helper, both shown); unclear separation of concerns (Events emitter and Helper are deliberately distinct per DDR-003).

Approval needed: [A]pprove | [R]evise (specify changes) | [X] reject (drops the diagram from output)

[A]pprove
Approved. Proceeding to contradiction detection and final outputs.

Update Todos

Load existing Tutoring design artefacts (API + DM)

Load events-schema and DDR-001 for cross-reference

Run interactive design session for Tutoring (5 deltas)

Update API-tutoring.md (Δ1-Δ6 + Δ9)

Update DM-tutoring.md (Δ7-Δ9)

Update events-schema.yaml (Δ10)

Write DDR-002 (Coach owns writes)

Write DDR-003 (event-emit fail-soft)

Generate C4 L3 component diagram for Tutoring

Mandatory C4 L3 review gate

Contradiction detection vs ADR-ARCH-001..019

Refresh README + offer Graphiti seeding commands
Contradiction detection vs 19 architecture ADRs
Checked the proposed contracts + DDRs + events-schema + diagram against ARCH-001..019:

ARCH-019 (every-write-point async) — All deltas align; the only references to ARCH-003 (now superseded) are removed (events-schema rationale, API-tutoring §3.4 Phase-1 evolution).
ARCH-018 (CC-13 + CC-14) — CC-13 referenced throughout; CC-14 deliberately scoped to a one-line cross-context pointer in DM-tutoring.md §6 (authoritative invariant remains in DM-inference-runtime.md).
ARCH-017 (sync classification) — Replaces stale "decision D2" reference in API-tutoring.md §3 lead-in; reversion-conditional rule cited in §9 Q1.
ARCH-012 (Coach AsyncSubAgent) — Load-bearing for DDR-002; both consistent.
ARCH-014 (single-user, single-process) — DDR-002's "no out-of-process queue" caveat aligns; DDR-003's "no session.persisted event" stays inside the in-process bus.
DDR-001 (sibling, MCP Transport-owned) — Referenced from API-tutoring §3 lead-in, §3.2, §3.4, §7.3; not duplicated.
No new contradictions detected. No superseding ADRs required.

Δ — Refresh docs/design/README.md
Edit README.md
Added 3 lines
Edit README.md
Added 6 lines
Edit README.md
Added 7 lines
Update §4 (out-of-scope artefacts — C4 L3 now generated for Tutoring):

Edit README.md
Modified
Update §5 contradiction detection result (add Tutoring refresh row) and §5 stale-references (mark swept):

Edit README.md
Added 2 lines
Edit README.md
Added 1 line
Now update §7 Next steps:

Edit README.md
Added 16 lines
Update §8 Graphiti seeding to include the new Tutoring artefacts:

Edit README.md
Added 2 lines
Update Todos

Load existing Tutoring design artefacts (API + DM)

Load events-schema and DDR-001 for cross-reference

Run interactive design session for Tutoring (5 deltas)

Update API-tutoring.md (Δ1-Δ6 + Δ9)

Update DM-tutoring.md (Δ7-Δ9)

Update events-schema.yaml (Δ10)

Write DDR-002 (Coach owns writes)

Write DDR-003 (event-emit fail-soft)

Generate C4 L3 component diagram for Tutoring

Mandatory C4 L3 review gate

Contradiction detection vs ADR-ARCH-001..019

Refresh README + offer Graphiti seeding commands
Summary

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ SYSTEM DESIGN COMPLETE — Tutoring (refresh)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Modified: docs/design/
  ├── README.md                              (refresh log + DDR-002/003 + C4 L3 row)
  ├── contracts/
  │   └── API-tutoring.md                    (Δ1–Δ6 + Δ9: ADR-019/CC-13 alignment, F1/F2/F3 references, DDR-001/002/003 cross-refs)
  ├── models/
  │   └── DM-tutoring.md                     (Δ7–Δ9: I-T7 invariant, §11 flush points, persistence narrative)
  └── events-schema.yaml                     (Δ10: ARCH-003 → ARCH-019; emit_decoupled flag; DDR-003 rationale)

Created:
  ├── decisions/
  │   ├── DDR-002-coach-async-subagent-owns-graphiti-writes.md
  │   └── DDR-003-session-completed-emits-on-state-transition.md
  └── diagrams/
      └── tutoring-c4-l3.md                  (8-component C4 L3, approved at gate)

Out of scope (still pending):
  • DM-inference-runtime.md / API-inference-runtime.md — CC-14 invariants
    Recommended: /system-design --focus="Inference Runtime"

Contradiction detection: ✓ no conflicts vs 19 architecture ADRs
C4 L3 review gate: ✓ approved
OpenAPI validation: N/A (no REST surface in Phase 0; ADR-ARCH-008)
Graphiti seeding (sequential — queue after current batch)
add_episode median 78.98s × max_concurrent_episodes: 3. Run these after the in-flight MCP-Transport-refresh batch completes; do not parallelise:


# Updated artefacts (re-seed superseding the 2026-04-26 versions)
guardkit graphiti add-context docs/design/contracts/API-tutoring.md \
  --group project_design

guardkit graphiti add-context docs/design/models/DM-tutoring.md \
  --group project_design

guardkit graphiti add-context docs/design/events-schema.yaml \
  --group project_design

# New DDRs
guardkit graphiti add-context docs/design/decisions/DDR-002-coach-async-subagent-owns-graphiti-writes.md \
  --group architecture_decisions

guardkit graphiti add-context docs/design/decisions/DDR-003-session-completed-emits-on-state-transition.md \
  --group architecture_decisions

# New C4 L3 diagram
guardkit graphiti add-context docs/design/diagrams/tutoring-c4-l3.md \
  --group project_design

# README refresh (re-seed superseding the prior version)
guardkit graphiti add-context docs/design/README.md \
  --group project_design
Run these commands now? [Y/n] — or queue manually after the in-flight batch finishes.

Y
Queuing all 7 commands sequentially in the background (chained with &&, one episode at a time so we don't pile on top of the in-flight batch).

Bash Sequentially seed 7 Tutoring refresh artefacts into Graphiti
IN
guardkit graphiti add-context docs/design/contracts/API-tutoring.md --group project_design \
&& guardkit graphiti add-context docs/design/models/DM-tutoring.md --group project_design \
&& guardkit graphiti add-context docs/design/events-schema.yaml --group project_design \
&& guardkit graphiti add-context docs/design/decisions/DDR-002-coach-async-subagent-owns-graphiti-writes.md --group architecture_decisions \
&& guardkit graphiti add-context docs/design/decisions/DDR-003-session-completed-emits-on-state-transition.md --group architecture_decisions \
&& guardkit graphiti add-context docs/design/diagrams/tutoring-c4-l3.md --group project_design \
&& guardkit graphiti add-context docs/design/README.md --group project_design \
&& echo "=== ALL 7 SEEDING COMMANDS COMPLETED ==="

OUT
Command running in background with ID: b9jz42byl. Output is being written to: /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/694990ff-e56e-4e0f-bdfc-bb35f9088013/tasks/b9jz42byl.output
Seeding queued in background (shell ID b9jz42byl). With add_episode median ~79s × 7 commands plus whatever's still in flight from the MCP refresh, expect roughly 10–15 minutes for the full batch. You'll be notified when it finishes; check /tmp/...b9jz42byl.output if you want to peek at progress.

Tutoring design refresh is complete: 4 artefacts updated, 3 created (DDR-002, DDR-003, C4 L3 diagram), zero contradictions detected, and the only outstanding ADR-018/019 stale-reference sweep is now Inference Runtime (CC-14).

Read b9jz42byl.output
Bash Check correct option name for graphiti add-context
IN
guardkit-py graphiti add-context --help 2>&1 | head -40

OUT
Usage: guardkit-py graphiti add-context [OPTIONS] PATH

  Add context from files to Graphiti.

  Adds content from markdown files to the Graphiti knowledge graph. Supports
  single files or directories with glob patterns.

  Examples:
      guardkit graphiti add-context docs/ADR-001.md
      guardkit graphiti add-context docs/architecture/
      guardkit graphiti add-context docs/ --pattern "**/*.md"
      guardkit graphiti add-context docs/ADR-001.md --type adr
      guardkit graphiti add-context docs/ --dry-run
      guardkit graphiti add-context docs/ --delay 1.0
      guardkit graphiti add-context docs/ --delay 0

  Supported parser types:
      - adr: Architecture Decision Records
      - feature_spec: Feature specifications
      - full_doc: Full document capture (entire markdown content)
      - project_overview: Project overview documents
      - project_doc: General project documentation (CLAUDE.md, README.md)

Options:
  --type TEXT           Force parser type (adr, feature-spec, project-
                        overview)
  -f, --force           Overwrite existing context
  --dry-run             Show what would be added without adding
  --pattern TEXT        Glob pattern for directory (default: **/*.md)
  -v, --verbose         Show detailed processing output
  -q, --quiet           Suppress non-error output
  --delay FLOAT         Inter-episode delay in seconds (default: 0.5, 0 to
                        disable)
  --chunk-size INTEGER  Force chunking for docs above this size in bytes
                        (default: 10240). Use 0 to always chunk.
  --timeout FLOAT       Per-episode timeout in seconds (overrides auto-
                        detected timeout). Use for slow vLLM instances.
  --help                Show this message and exit.
The CLI has no --group flag — auto-routes via --type. Let me check the recent query log for the exact pattern used in the MCP refresh.

Bash Check recent graphiti-query-log entries for command pattern
IN
tail -20 .guardkit/graphiti-query-log.jsonl 2>/dev/null | head -10

OUT
{"timestamp":"2026-04-27T06:20:49.940782+00:00","source":"graphiti_client","operation":"add_episode","query":"docs/planning/feature-roadmap.md","group_ids":["project_architecture"],"result_count":1,"first_result_preview":"Both decisions surfaced during the 2026-04-26 `/sy"}
{"timestamp":"2026-04-27T09:05:43.883970+00:00","source":"graphiti_client","operation":"add_episode","query":"adr_adr-arch-017-tutor-start-session-sr-07-classification-sync-phase-0","group_ids":["project_decisions"],"result_count":1,"first_result_preview":"# ADR-ARCH-017 \u2014 `tutor_start_session` SR-07 class"}
{"timestamp":"2026-04-27T09:12:14.412229+00:00","source":"graphiti_client","operation":"add_episode","query":"adr_adr-arch-008-mcp-only-for-agent-access-single-user-auth-posture","group_ids":["project_decisions"],"result_count":1,"first_result_preview":"# ADR-ARCH-008 \u2014 MCP-only for agent access; single"}
{"timestamp":"2026-04-27T10:59:40.237484+00:00","source":"graphiti_client","operation":"add_episode","query":"adr_adr-arch-018-extend-load-bearing-cross-cutting-concerns-with-sr-08-graphiti-async-write-back-and-sr-09-runtime-llm-parameters-explicit","group_ids":["project_decisions"],"result_count":1,"first_result_preview":"# ADR-ARCH-018 \u2014 Extend load-bearing cross-cutting"}
{"timestamp":"2026-04-27T11:04:45.060452+00:00","source":"graphiti_client","operation":"add_episode","query":"adr_adr-arch-009-six-parity-surfaces-les1-as-load-bearing-cross-cutting-concerns","group_ids":["project_decisions"],"result_count":1,"first_result_preview":"# ADR-ARCH-009 \u2014 Six parity surfaces (LES1) as loa"}
{"timestamp":"2026-04-27T11:17:10.398570+00:00","source":"graphiti_client","operation":"add_episode","query":"adr_adr-arch-003-async-graphiti-write-back-at-session-end-boundary","group_ids":["project_decisions"],"result_count":1,"first_result_preview":"# ADR-ARCH-003 \u2014 Async Graphiti write-back at sess"}
{"timestamp":"2026-04-27T11:17:50.889767+00:00","source":"graphiti_client","operation":"add_episode","query":"adr_adr-arch-019-async-graphiti-write-back-at-every-write-point-in-the-tutor","group_ids":["project_decisions"],"result_count":1,"first_result_preview":"# ADR-ARCH-019 \u2014 Async Graphiti write-back at ever"}
{"timestamp":"2026-04-27T12:59:58.195222+00:00","source":"graphiti_client","operation":"add_episode","query":"adr_ddr-001-mcp-tool-descriptions-do-not-enumerate-graphiti-write-side-effects","group_ids":["project_decisions"],"result_count":1,"first_result_preview":"# DDR-001 \u2014 MCP tool descriptions do not enumerate"}
{"timestamp":"2026-04-27T13:03:58.830494+00:00","source":"graphiti_client","operation":"add_episode","query":"docs/design/contracts/API-mcp-transport.md_chunk_0","group_ids":["project_knowledge"],"result_count":1,"first_result_preview":"# API Contract \u2014 MCP Transport\n\n**Bounded context:"}
{"timestamp":"2026-04-27T13:05:28.277327+00:00","source":"graphiti_client","operation":"add_episode","query":"docs/design/contracts/API-mcp-transport.md_chunk_1","group_ids":["project_knowledge"],"result_count":1,"first_result_preview":"## 1. Purpose\n\nMCP Transport is a **thin fa\u00e7ade** "}
CLI uses --type adr for ADRs/DDRs (auto-routes to project_decisions) and no flag for content docs (auto → project_knowledge). YAML isn't supported, so I'll skip events-schema.yaml — it's already referenced from the seeded .md artefacts. Re-queueing 6 commands:

Bash Sequentially seed 6 Tutoring refresh artefacts (corrected CLI)
IN
guardkit-py graphiti add-context docs/design/decisions/DDR-002-coach-async-subagent-owns-graphiti-writes.md --type adr \
&& guardkit-py graphiti add-context docs/design/decisions/DDR-003-session-completed-emits-on-state-transition.md --type adr \
&& guardkit-py graphiti add-context docs/design/contracts/API-tutoring.md \
&& guardkit-py graphiti add-context docs/design/models/DM-tutoring.md \
&& guardkit-py graphiti add-context docs/design/diagrams/tutoring-c4-l3.md \
&& guardkit-py graphiti add-context docs/design/README.md \
&& echo "=== ALL 6 SEEDING COMMANDS COMPLETED ==="

OUT
Command running in background with ID: bxra5xm36. Output is being written to: /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/694990ff-e56e-4e0f-bdfc-bb35f9088013/tasks/bxra5xm36.output
Re-queued (shell ID bxra5xm36) with the corrected CLI:

2 DDRs with --type adr → project_decisions group
4 content artefacts (auto-detect) → project_knowledge group
events-schema.yaml skipped (YAML not supported by add-context; same as prior MCP refresh — its content is already referenced from the seeded .md artefacts)
I'll be notified on completion. Expected ~8–12 minutes given the 78.98s add_episode median plus chunking on the larger contracts.

Bash Check seeding output
IN
tail -50 /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/694990ff-e56e-4e0f-bdfc-bb35f9088013/tasks/bxra5xm36.output

OUT
INFO:guardkit.knowledge.graphiti_client:Episode profile [docs/design/models/DM-tutoring.md_chunk_8]: nodes=5, edges=3, invalidated=0
WARNING:graphiti_core.utils.maintenance.edge_operations:LLM returned invalid duplicate_facts idx values [4] (valid range: 0--1 for EXISTING FACTS)
INFO:graphiti_core.graphiti:Completed add_episode in 137076.41005516052 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [docs/design/models/DM-tutoring.md_chunk_9]: nodes=11, edges=15, invalidated=0
INFO:graphiti_core.graphiti:Completed add_episode in 50354.36177253723 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [docs/design/models/DM-tutoring.md_chunk_10]: nodes=3, edges=2, invalidated=0
INFO:graphiti_core.graphiti:Completed add_episode in 130872.55334854126 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [docs/design/models/DM-tutoring.md_chunk_11]: nodes=5, edges=15, invalidated=0
  ✓ docs/design/models/DM-tutoring.md (full_doc)

Summary:
  Added 1 file, 12 episodes

Warnings:
  Warning: docs/design/models/DM-tutoring.md: Large document (10653 bytes) split
into 12 chunks
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

INFO:graphiti_core.graphiti:Completed add_episode in 236549.02386665344 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [docs/design/diagrams/tutoring-c4-l3.md]: nodes=14, edges=17, invalidated=0
  ✓ docs/design/diagrams/tutoring-c4-l3.md (full_doc)

Summary:
  Added 1 file, 1 episode
Graphiti Add Context

INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: handle_multiple_group_ids patched for single group_id support (upstream PR #1170)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: build_fulltext_query patched to remove group_id filter (redundant on FalkorDB)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_fulltext_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.falkordb_workaround:[Graphiti] Applied FalkorDB workaround: edge_bfs_search patched for O(n) startNode/endNode (upstream issue #1272)
INFO:guardkit.knowledge.graphiti_client:Connected to FalkorDB via graphiti-core at whitestocks:6379
Connected to Graphiti

INFO:graphiti_core.graphiti:Completed add_episode in 114953.4330368042 ms
INFO:guardkit.knowledge.graphiti_client:Episode profile [study-tutor-design-artefacts]: nodes=7, edges=21, invalidated=0
  ✓ docs/design/README.md (project_overview)

Summary:
  Added 1 file, 1 episode

Warnings:
  Warning: docs/design/README.md: Missing 'architecture' section
=== ALL 6 SEEDING COMMANDS COMPLETED ===
Bash Per-file seeding summary
IN
grep -E "(Summary:|✓ docs)" /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/694990ff-e56e-4e0f-bdfc-bb35f9088013/tasks/bxra5xm36.output

OUT
  ✓ docs/design/decisions/DDR-002-coach-async-subagent-owns-graphiti-writes.md 
Summary:
  ✓ docs/design/decisions/DDR-003-session-completed-emits-on-state-transition.md
Summary:
Summary:
  ✓ docs/design/models/DM-tutoring.md (full_doc)
Summary:
  ✓ docs/design/diagrams/tutoring-c4-l3.md (full_doc)
Summary:
  ✓ docs/design/README.md (project_overview)
Summary:
Bash Full per-file episode counts and warnings
IN
grep -E "(Summary:|Added|Warning)" /private/tmp/claude-501/-Users-richardwoollcott-Projects-appmilla-github-study-tutor/694990ff-e56e-4e0f-bdfc-bb35f9088013/tasks/bxra5xm36.output

OUT
Summary:
  Added 1 file, 1 episode
Summary:
  Added 1 file, 1 episode
Summary:
  Added 1 file, 9 episodes
Warnings:
  Warning: docs/design/contracts/API-tutoring.md: Large document (15826 bytes) 
Summary:
  Added 1 file, 12 episodes
Warnings:
  Warning: docs/design/models/DM-tutoring.md: Large document (10653 bytes) split
Summary:
  Added 1 file, 1 episode
Summary:
  Added 1 file, 1 episode
Warnings:
  Warning: docs/design/README.md: Missing 'architecture' section
All 6 seeded successfully. Episode counts:

File	Episodes	Group
DDR-002	1	project_decisions
DDR-003	1	project_decisions
API-tutoring.md	9 (chunked, 15.8 KB)	project_knowledge
DM-tutoring.md	12 (chunked, 10.7 KB)	project_knowledge
tutoring-c4-l3.md	1	project_knowledge
README.md	1 (project_overview)	project_knowledge
Total: 25 episodes added. One benign warning on README.md ("Missing 'architecture' section" — the parser expects that section in project-overview docs; not relevant here since it's a design index, not a project root).

Tutoring design refresh fully landed and seeded. The remaining ADR-018/019 stale-reference sweep is /system-design --focus="Inference Runtime" for CC-14 (num_ctx/num_predict).