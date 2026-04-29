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
