# ADR-ARCH-013 — Middleware-level gamification engine (future direction, P2)

## Status

**Superseded** by [ADR-ARCH-030](ADR-ARCH-030-gamification-settlement-pure-engine-finalize-transaction.md)
(2026-07-12) — the middleware/event-subscriber direction noted below is
**rejected**. ADR-ARCH-030 makes the FEAT-PO-007 runtime-shape call this ADR
deferred: the engine is a **pure `decide()` function invoked inside one
`finalize_session` transaction** (the "standalone module" alternative kept open
below), not a deepagents `GamificationMiddleware`. Rationale: the event bus has
zero subscribers and its one emitter violated the schema, the HTTP/WS/voice
transports have no bus at all, and an async fan-out contradicts
`docs/gamification/design.md` §11.2's requirement that session-end state changes
be one synchronous Postgres transaction. This ADR is retained for provenance.

_Originally: Proposed (future direction; not committed for Phase 0/1), 2026-04-18._

**Date:** 2026-04-18 · **Superseded:** 2026-07-12
**Phase:** P2 consideration
**Related:** ADR-ARCH-012, ADR-ARCH-001 (Gamification context),
[ADR-ARCH-030](ADR-ARCH-030-gamification-settlement-pure-engine-finalize-transaction.md) (supersedes this)

## Context

The deepagents 0.5.x middleware architecture allows reacting to tool
calls and state changes via custom middleware classes — intercepting
events in a structured way rather than via ad-hoc callbacks. The
Gamification context's event-consumption responsibilities
(`session.completed` → XP + streak + achievement check) are a natural
fit for this pattern.

However, the Phase 2 Gamification Engine is not a Phase 0 commitment;
the engine's runtime shape will be decided when Phase 2 begins
(12–16 May 2026).

## Decision

**Note the direction; do not commit to it.** In Phase 2, evaluate
implementing the Gamification Engine as a custom deepagents middleware
class (`GamificationMiddleware`) that:

- Subscribes to `session.completed`, `achievement.unlocked`,
  `quest.completed`, `boss_battle.completed` events.
- Updates `StudentProgress` aggregate via the Student Model Client.
- Emits follow-on `achievement.unlocked` events for newly-earned
  achievements.

Alternative considered and kept open: a standalone
`src/study_tutor/gamification/engine.py` module invoked by the session
manager at `session.completed` time. Less idiomatic w.r.t. deepagents
0.5.x but more portable if we later decouple from deepagents.

Phase 2 feature spec (`FEAT-PO-007`) will make the call.

## Alternatives considered

- **Committing to middleware now.** Rejected. Phase 2 is a month
  away. Committing now over-specifies a decision that's best made
  with the Phase 1 event-flow experience in hand.
- **Committing to a standalone module now.** Rejected for the same
  reason — over-specification.

## Consequences

**Positive:**
- Captures the direction for Phase 2 planners without commitment.
- Documents the pattern fit so it's not forgotten when P2 arrives.

**Negative:**
- Slight risk that Phase 1 locks in a call shape that constrains
  Phase 2's choice. Mitigated by keeping Student Model events
  plain-data (Pydantic models) with no deepagents-specific
  dependencies.

**Middleware insertion point.** ADR-ARCH-012's `CompositeBackend`
route-scoped permissions already provide the middleware insertion
point a `GamificationMiddleware` would attach to. If Phase 2 chooses
middleware, the wiring seam is already there; if it chooses the
standalone-module alternative, the cost is a small amount of
additional wiring, not a re-architecture.

## References

- deepagents 0.5.x middleware architecture docs.
- `docs/gamification/design.md §11.2` (event vocabulary).
