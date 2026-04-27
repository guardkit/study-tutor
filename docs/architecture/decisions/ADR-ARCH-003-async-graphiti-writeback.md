# ADR-ARCH-003 — Async Graphiti write-back at session-end boundary

## Status

Superseded by [ADR-ARCH-019](ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) on 2026-04-27.

**Date:** 2026-04-18
**Phase:** Phase 0 (architectural commitment; runtime arrives in P1)
**Related:** ADR-ARCH-002, ADR-ARCH-012, DEC-02, DEC-08
**Superseded by:** ADR-ARCH-019 (broadens scope from session-end-only to every Graphiti write point in the tutor, per CC-13 / SR-08 and the 2026-04-27 latency spike).

## Context

Graphiti writes involve entity extraction by Google Gemini 2.5 Pro
(DEC-02) with typical latency 1–3s per operation (DEC-08). Writing
per-turn to Graphiti would add this latency to every `tutor_turn`
call, pushing p95 past the 10s target and risking the 30s threshold
(CC-08 / LES1 row 10 ⚠️).

LES1 §4 (fire-and-forget + poll above 30s) explicitly flags this
pattern. `specialist-agent`'s TASK-MDF-POLR evidence confirms the
failure mode: sync `await` on a generation loop produced a
4-minute timeout in Claude Desktop.

## Decision

Graphiti write-back is **async relative to the tutor's hot path** and
**triggered at the session-end boundary only** — not per turn.

- Within-session state (turns, partial AO coverage, session quality
  samples) lives in the in-process `TutorSession` aggregate.
- On `session.completed`:
  - A `SessionEpisode` entity is prepared.
  - A Coach-proposed per-topic confidence delta (capped ±0.1) is
    computed.
  - Write-back is dispatched to a background task; the tutor's
    `tutor_session_end` response returns to the user without waiting
    for Gemini extraction.
- Misconceptions detected by the Coach during turn evaluation
  accumulate in session-scoped memory and are flushed in the same
  session-end batch (P1 design).
- If Graphiti is unreachable, the session-end handler **logs and
  returns successfully** — fail-soft degradation. The session is
  not lost from the student's perspective.

## Alternatives considered

- **Per-turn Graphiti writes.** Rejected. Would add 1–3s Gemini
  latency to every turn; violates p95 <10s and CC-08.
- **Session-end write with sync await.** Rejected. `tutor_session_end`
  would become long-running and require SR-07 reclassification, which
  complicates the MCP tool contract. The user shouldn't have to wait
  for analytics.
- **Per-turn in-memory plus batched flush on timer.** Rejected for
  Phase 1 MVP — extra machinery, unclear benefit over session-end-only
  semantics.
- **Per-turn async fire-and-forget (per turn).** Considered for
  streaming-style write-back. Deferred to a later revisit — adds
  per-turn background-task bookkeeping without clear benefit.

## Consequences

**Positive:**
- Preserves `tutor_turn` p95 < 10s.
- Aligns with CC-08 and LES1 §4 prescriptions.
- Simplifies the MCP tool contract — no long-running reclassification
  needed for session-end.
- Leverages deepagents 0.5.3 `AsyncSubAgent` pattern natively
  (ADR-ARCH-012).

**Negative:**
- Writes within an active session are not visible to a concurrent
  query (e.g. the Planner) until session-end. Acceptable — single-user
  system, no concurrent sessions.
- If the tutor crashes between session-end and Graphiti flush, the
  session-level state is lost. Acceptable for Phase 1 MVP; revisit if
  we see real crashes.
- Coach has to batch per-turn observations in memory. Straightforward
  to implement; natural boundary.

## References

- DEC-02, DEC-08 in `docs/research/ideas/decisions-log-2026-04-17.md`
- LES1 §4 POLR evidence in
  `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`
- deepagents 0.5.3 `AsyncSubAgent` — native fire-and-forget tool set
  (`launch_task`, `check_task`, `update_task`, `cancel_task`, `list_tasks`).
