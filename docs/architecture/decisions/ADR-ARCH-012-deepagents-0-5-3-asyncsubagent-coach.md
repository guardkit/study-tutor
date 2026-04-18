# ADR-ARCH-012 — deepagents 0.5.3+ with AsyncSubAgent Coach + CompositeBackend routing

## Status

Accepted

**Date:** 2026-04-18
**Phase:** Phase 0 (declares dependency); runtime usage arrives in P1
**Related:** ADR-ARCH-003, ADR-ARCH-004, CC-08, CC-12

## Context

deepagents 0.5.3 (released 15 April 2026) introduced features that
materially change Study Tutor's Phase 1 architecture:

- **`AsyncSubAgent` class** — native async subagents, invoked via
  built-in `launch_task`, `check_task`, `update_task`,
  `cancel_task`, `list_tasks` tools. This is the canonical form of
  the fire-and-forget + poll pattern LES1 §4 prescribes.
- **Static structured output for subagent responses** (Pydantic).
- **`model=None` deprecated** — `create_deep_agent()` now requires
  an explicit model argument.
- **Permissions system** (0.5.2) with route-scoped permissions on
  `CompositeBackend`.
- **Middleware architecture** (`FilesystemMiddleware` +
  `StateBackend` / `StoreBackend` / `CompositeBackend`).

Without this decision, Study Tutor's Phase 1 Coach would be hand-rolled
fire-and-forget + poll (LES1 prescription). With 0.5.3, the SDK
provides the pattern natively.

## Decision

Pin `deepagents >= 0.5.3` in `pyproject.toml` `[providers]` extra
(CC-04) from Phase 0 for SR-04 smoke-test compliance, even though
Phase 0 code does not import deepagents yet.

Phase 1+ design:

1. **Player** is a regular deepagents agent — `create_deep_agent(
   model=<explicit>, tools=[rag_retrieval, think], subagents=[coach],
   system_prompt=TUTOR_PROMPT)`.
2. **Coach** is an `AsyncSubAgent` — runs off the hot path via
   `launch_task`/`check_task`. Evaluates per-turn quality, batches
   observations, flushes at session-end to Student Model.
3. **Backend** is a `CompositeBackend`:
   - Default: `StateBackend()` — ephemeral, in-process session turns.
   - Route `/student/`: `StoreBackend()` — persistent cross-session
     state (LangGraph Store-backed), with Graphiti write-back wired
     in as an event handler.
4. **Structured output** is used for Coach `TurnFeedback` and
   `SessionSummary` per ADR-ARCH-010.
5. **`model=None` not used** — all `create_deep_agent()` calls pass an
   explicit model (e.g. `init_chat_model("ollama:gcse-tutor-gemma4")`).

## Alternatives considered

- **deepagents 0.5.2.** Rejected — misses `AsyncSubAgent`, which is
  the cleanest Coach pattern. Upgrade benefit outweighs the
  `model=None` breaking change (which we want to avoid anyway).
- **Hand-roll fire-and-forget + poll for Coach.** Rejected. Adds code
  (session-id tracking, poll response shape) that 0.5.3 gives for
  free.
- **Synchronous Coach.** Rejected. Violates CC-08 budget; per-turn
  Coach call would add 3–5s to every `tutor_turn`.
- **LangGraph directly (no deepagents).** Rejected. deepagents'
  middleware stack, skills, filesystem backends, and subagent patterns
  would all have to be re-derived. Phase-1 effort budget doesn't
  allow it.

## Consequences

**Positive:**
- Native support for CC-08 (fire-and-forget + poll) via
  `AsyncSubAgent`.
- Coach can be a remote agent via `graph_id` + `url` if we deploy it
  later (e.g. to a Bedrock or LangGraph Cloud endpoint). No P0/P1
  commitment to do so — option is preserved.
- `CompositeBackend` routing cleanly maps Session vs Student Model
  persistence layers.
- Structured subagent output (0.5.3) aligns with Pydantic-at-boundary
  strategy (ADR-ARCH-010).

**Negative:**
- deepagents 0.5.x has had breaking changes in quick succession
  (permissions, `model=None`). Must pin exact version and revalidate
  after any upgrade (ASSUM-014).
- Async subagent orchestration is newer SDK territory and may have
  rough edges.
- Phase 0 declares the dependency but doesn't import it yet — SR-04
  smoke test needs to cover this explicitly (declare + import
  succeeds; runtime import on first P1 commit).

## References

- deepagents 0.5.3 release notes (April 2026).
- deepagents 0.5.2 permissions system.
- LES1 §4 fire-and-forget + poll prescription.
- `deepagents-patterns-review.md §1.1, §1.3` (Player-Coach applied to
  Study Tutor).
