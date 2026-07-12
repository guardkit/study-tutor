# ADR-ARCH-030 — Gamification settlement: pure `decide()` + one `finalize_session` transaction, banked-facts model, notification-only bus

## Status

Accepted

**Date:** 2026-07-12
**Phase:** Phase R (adaptive-loop repair + gamification engine), Lane B (GB10)
**Supersedes:** [ADR-ARCH-013](ADR-ARCH-013-middleware-level-gamification-engine-future.md)
(middleware-level gamification engine — **rejected**; this ADR is the FEAT-PO-007
"which runtime shape" call ADR-013 deferred).
**Annotates (no reversal of current force):**
[DDR-003](../../design/decisions/DDR-003-session-completed-emits-on-state-transition.md)
(`session.completed` emit posture — this ADR moves the emit from *state-transition,
emit-before/decoupled-from-write* to **emit-after-commit**; see D5),
[ADR-ARCH-019](ADR-ARCH-019-async-graphiti-writeback-every-write-point.md)
(fire-and-forget every-write-point — a Graphiti-era posture; the student store is now
Postgres and settlement is **synchronous in one transaction**, not fire-and-forget).
**Related:** [ADR-ARCH-023](ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md)
(Postgres student store; synchronous session-end transaction — the substrate this ADR
builds on), [ADR-ARCH-014](ADR-ARCH-014-single-user-scalability-posture.md) (single-user
posture — why a serialized single-row settlement is sufficient),
[`docs/gamification/design.md`](../../gamification/design.md) §11.2 (atomic-at-session-end
event vocabulary; §13.1 the ratified economy constants),
[`docs/research/ideas/gamification-engine-and-app-ux-scope-and-build-plan.md`](../../research/ideas/gamification-engine-and-app-ux-scope-and-build-plan.md)
(decisions D1–D8, the source of this ADR),
[`docs/design/gamification-engine-and-adaptive-loop-spec.md`](../../design/gamification-engine-and-adaptive-loop-spec.md)
§4 (the build spec).

## Context

The Phase-2 gamification engine was never built. [ADR-ARCH-013](ADR-ARCH-013-middleware-level-gamification-engine-future.md)
noted a *direction* — implement the engine as a deepagents middleware class subscribing to
`session.completed` — and deferred the runtime-shape call to FEAT-PO-007. Two facts, verified
against `main` @ `a81ec5d` (runs `wf_29f79e88-efd`, `wf_70d314d1-ce4`, `wf_f41e9839-be8`),
make the middleware/subscriber direction untenable:

1. **The bus has zero subscribers, and its one emitter is broken.** Only `session.completed`
   is emitted (MCP path only), its payload violates `events-schema.yaml` (`subject_slug`
   carries the *student id*, not the subject), and the HTTP/WS/voice surfaces have no event
   infrastructure at all. An engine that *subscribes* would subscribe to nothing on the
   primary product transport.
2. **Asynchrony violates the design contract.** `design.md` §11.2 requires session-end state
   changes to be **atomic at the session-end boundary** — "literally a single synchronous
   Postgres transaction (XP + streak + per-topic confidence deltas + achievement checks), not
   a fire-and-forget per-write." A middleware fan-out over an at-most-once bus is the opposite
   posture.

Separately, the live session-end path had (Phase-R W0) a bug that silently dropped **all**
completion children because `store.end_session` flipped `status='ended'` in its own transaction
*before* `record_session_completion`, whose `ON CONFLICT … WHERE status != 'ended'` idempotency
gate then never fired. Any settlement design must make the status transition and the settlement
writes **one indivisible unit**, and must make the transition itself the idempotency gate.

## Decision

**The gamification engine is a pure decision function invoked inside one `finalize_session`
transaction. Facts are banked; aggregates are derived. The bus stays notification-only.**

### D1 — Pure `decide()` core, no I/O
`src/study_tutor/gamification/engine.py` exposes
`decide(prior: PriorFacts, session: SessionFacts, now: datetime) → GamificationDecision`.
It performs **no I/O**, takes an **injected clock** (`now`), and shares its London-day helpers
with the read-side projection so live settlement and the read model never disagree. The decision
carries `{xp_awarded, total_xp_after, level_before, level_after, level_up, streak_days,
streak_extended, unlocked: [AchievementAward{id, name, xp}], near_achievements:
[NearAchievement{id, name, progress, target, hint}]}`. Purity is what makes the engine
replayable, unit-testable without a database, and identical between the live path and the sweep.

### D2 — Bank facts, derive aggregates (no `gamification_state` table)
There is **no running-total table**. `total_xp = SUM(session.xp_awarded) +
SUM(achievement.xp_awarded)`; level, current streak, longest streak, and `near_achievements`
are **derived at read time** from banked session/achievement rows (London-date arithmetic).
This honours `schema_reference.sql` ASSUM-002 and reverses nothing. The Phase-R migration adds
only: `session.settled_at` (nullable — the sweep's work queue), `achievement.session_id`
(replay linkage), and an append-only `topic_confidence_history` table. Because
`topic_confidence_history` **cannot be backfilled**, capture starts on day one even though the
Growth/Mastery achievements that consume it land in a later tranche.

### D3 — One `finalize_session` transaction; the status UPDATE is the sole gate
`finalize_session` replaces the broken two-call `end_session → record_session_completion`
sequence with a single `engine.begin()`:

1. `UPDATE session SET status='ended', last_activity=:now, … WHERE session_id=:sid AND
   status='active' RETURNING started_at, topic, text_name, …`. A **non-matching UPDATE** means
   the session was already ended → the **replay path** (D6). This gate **is** the idempotency
   mechanism *and* returns the settlement's session facts.
2. Read prior facts in-transaction (SUM xp, session dates for streaks, confidence rows,
   achievement ids already held).
3. Engagement facts: `SELECT min(ts), max(ts), count(*) FROM session_turn WHERE
   session_id=:sid`. Engagement duration = `max − min`; zero rows → 0 XP, still settled.
4. Call `decide()`; write `session.xp_awarded` **and `settled_at=:now`**, insert achievement
   rows (`ON CONFLICT DO NOTHING`, carrying `session_id`), append `topic_confidence_history`
   rows, run the existing confidence/misconception helpers.

Double-end / two-device races serialize on the session row lock; exactly one caller wins the
`active → ended` transition and settles, the other replays.

### D4 — Settlement runs in a savepoint and can never block ending a session
Step 4 above executes inside a nested savepoint (`begin_nested()`). `settled_at` is stamped
**inside** the savepoint, so a settlement fault leaves it NULL with no compensating update. On
any settlement exception: roll back to the savepoint, **commit the end**, log at ERROR. The
session always ends; settlement is best-effort-then-swept.

### D5 — Sweep CLI is load-bearing (recovery **and** backfill)
`study-tutor settle-sessions` (a click subcommand modeled on `seed-students`) settles every
`status='ended' AND settled_at IS NULL` row through the **same** `decide()`, idempotently, with
per-row logging. It is both the fault-recovery path (rows D4 left NULL) and the one-time
historical backfill. Engagement falls back to `started_at/last_activity` when a swept session
has no turns. Running it against the live NAS store is an **attended** operation, never an
unattended stage.

### D6 — Exactly-once via replay, not locks-held-across-work
An already-ended session (the non-matching UPDATE in D3) does **not** re-settle. The replay path
reads the banked `session.xp_awarded` and the achievement rows where `achievement.session_id=:sid`
and returns the **identical** `GamificationDecision`. Both racing callers therefore observe the
same XP, level, and unlock set. `achievement.session_id` exists precisely to make replay a read,
not a recomputation.

### D7 — Single hook point: `SessionService.end_session`, both transports (D14 fence)
Settlement is invoked from `SessionService.finalize_session`, called by `end_session` for **all**
transports. The MCP adapter passes only its topic hint; the HTTP handler's `completion=None`
bypass is deleted; `record_session_completion` collapses to a thin wrapper (or is removed) and
its phantom-insert branch does not survive (an unknown session ⇒ `SessionNotFoundError`). Per
the D14 architectural fence, the MCP adapter may hold **no** settlement logic the HTTP path
lacks — the adapter is a tool-shape skin over the core.

### D8 — The bus stays notification-only; emit moves to **after-commit**
The event bus is **never state-bearing** — no consumer's correctness may depend on a delivered
event, and settlement never awaits one. While there are still zero subscribers, the emit posture
is corrected: `session.completed` (and any gamification-derived signal) is emitted **after the
`finalize_session` commit succeeds**, with an `events-schema.yaml`-conforming payload and
`subject_slug` carrying the **actual subject**. This **replaces DDR-003's emit-decoupled-from-write
posture** (and ADR-ARCH-019's fire-and-forget-before-ack framing, which were Graphiti-era): with
a fast synchronous Postgres commit there is no latency reason to emit before the write, and
emit-after-commit means a delivered event always corresponds to durable state. Gamification
results reach product surfaces through **API responses** (the enriched `GET /api/student-model`
and the nullable `gamification` block on `end_session`), not through the bus; bus emission of
gamification events is deferred until a real subscriber exists.

## Alternatives considered

- **`GamificationMiddleware` deepagents subscriber (ADR-013's noted direction).** Rejected. Zero
  subscribers exist, the sole emitter violates the schema, the HTTP/voice transports have no bus,
  and an async fan-out contradicts `design.md` §11.2's "single synchronous transaction" contract.
  The middleware seam (ADR-012 `CompositeBackend`) is left unused for this purpose.
- **A `gamification_state` running-totals table.** Rejected (D2). Running totals invite drift
  between the write path and the read model and demand compensating updates on every rebalance;
  deriving from banked rows is the ASSUM-002 posture and makes the sweep a pure re-derivation.
- **Two transactions (end, then settle) as today.** Rejected — that *is* the W0 bug. The status
  transition and the settlement writes must be one unit with the transition as the gate.
- **Locks held across the settlement work for exactly-once.** Rejected in favour of
  replay-the-banked-decision (D6): the row lock only guards the `active → ended` flip; the loser
  reads and returns the winner's banked result, which is cheaper and race-proof under the
  single-user posture (ADR-014).
- **Keep DDR-003 emit-decoupled / ADR-019 fire-and-forget.** Rejected as the settlement posture:
  those were justified by 78.98 s Graphiti `add_episode` latency. Postgres settlement commits in
  milliseconds, so emit-after-commit costs nothing and buys "a delivered event implies durable
  state."

## Consequences

**Positive:**
- Settlement is atomic, idempotent, replayable, and unit-testable without a database — the
  engine is a pure function, the transaction is one gate.
- Live settlement and the historical backfill run identical code (`decide()`), so they cannot
  diverge — the sweep is not a second, drifting implementation.
- No running-total drift; the read model is always a re-derivation of banked facts.
- A delivered `session.completed` now implies committed state (emit-after-commit), and its
  payload finally conforms to `events-schema.yaml`.

**Negative / accepted:**
- `topic_confidence_history` is unbackfillable, so pre-Phase-R sessions never gain Growth-signal
  history — accepted; capture starts day one.
- The sweep CLI is **load-bearing**, not a convenience: a settlement fault that leaves
  `settled_at` NULL is only healed when the sweep runs. Operationally, the sweep must be run
  (attended) after any ERROR-logged settlement fault and once as the historical backfill.
- Gamification events are not on the bus for now; any future subscriber must wait for the
  deferred emission (D8) rather than reading a state-bearing stream today.

## C4 diagram re-review status

No structural change to the container/component topology — settlement lives inside the existing
`SessionService`/store within the Tutoring context; no new container, no new external dependency.
The Gamification context becomes a **module invoked by the session manager** (the standalone-module
alternative ADR-013 kept open), not a middleware attached to `CompositeBackend`. The C4 re-review
gate is **not** triggered.

## References

- [ADR-ARCH-013](ADR-ARCH-013-middleware-level-gamification-engine-future.md) — superseded; the
  middleware direction this ADR rejects.
- [ADR-ARCH-023](ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md) — the Postgres
  student store and synchronous session-end transaction this ADR builds on.
- [DDR-003](../../design/decisions/DDR-003-session-completed-emits-on-state-transition.md) — the
  emit posture this ADR moves to after-commit (D8).
- [ADR-ARCH-019](ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) — the Graphiti-era
  fire-and-forget framing that no longer applies to Postgres settlement.
- [`docs/gamification/design.md`](../../gamification/design.md) §11.2 (atomic session-end),
  §13.1 (ratified economy constants).
- [`docs/design/gamification-engine-and-adaptive-loop-spec.md`](../../design/gamification-engine-and-adaptive-loop-spec.md)
  §4 — the build spec for the engine, `finalize_session`, and the sweep.
- [`docs/research/ideas/gamification-engine-and-app-ux-scope-and-build-plan.md`](../../research/ideas/gamification-engine-and-app-ux-scope-and-build-plan.md)
  — decisions D1–D8.
