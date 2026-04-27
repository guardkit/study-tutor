# ADR-ARCH-017 — `tutor_start_session` SR-07 classification: sync (Phase 0)

## Status

Accepted

**Date:** 2026-04-27
**Phase:** Phase 0
**Supersedes:** ADR-ARCH-008 (partial — only the SR-07 classification table at lines 35–46 and the "stable across phases for forward compatibility" rationale block; the rest of ADR-ARCH-008 — single-transport choice, HTTP-deferral, auth posture, Phase-0 session-scope note — stands unchanged).
**Related:** ADR-ARCH-009 (CC-07 / SR-07), LES1 row 19, design D2 (`docs/design/README.md §3`).

## Context

The 2026-04-26 `/system-design` pass surfaced two findings that invalidate ADR-ARCH-008's classification of `tutor_start_session` as long-running:

1. **The Phase 0 implementation never satisfied the long-running protocol.** [src/study_tutor/mcp/adapter.py:49–68](../../../src/study_tutor/mcp/adapter.py) returns `{"session_id": "..."}` synchronously in well under 1s; the LLM warm-up runs as a fire-and-forget `asyncio.create_task`. There is no still-running task to poll, and no `_status`/`_cancel` companion tool exists. This is a current SR-07 violation: the registered tool description says "Long-running, returns session_id immediately" but the handler exposes none of the long-running protocol's affordances.

2. **The forward-compat rationale doesn't survive Phase 1 planning.** ADR-ARCH-008 justified the long-running classification with "the classification is stable across phases so `/feature-spec` does not need to re-classify the MCP contract when Graphiti lands." But [phase-1-scope.md:84–85](../../research/ideas/phase-1-scope.md) explicitly makes the Phase 1 classification *dependent on* the Graphiti latency spike outcome:

   > If search_nodes median > 3s: `tutor_start_session` stays long-running (Phase 0 classification holds)
   > If search_nodes median < 1s: `tutor_start_session` could be reclassified as sync, simplifying the MCP tool shape

   So phase-stability was never load-bearing — it was always conditional on a measurement that hadn't been taken. Forward-compat speculation cannot justify a current SR-07 violation.

LES1 row 19 (latency classification, marked ⚠️ for study-tutor) and TASK-MDF-POLR (4-minute Claude Desktop timeout from a long-running/sync mismatch) are the prior-art evidence that an SR-07 violation is not a paper-only concern.

## Decision

`tutor_start_session` is classified **sync** in Phase 0. The full Phase-0 SR-07 classification table is:

| Tool | Class | Bound |
|---|---|---|
| `tutor_start_session` | **sync** | < 1s; warm-up is fire-and-forget |
| `tutor_turn` | sync | p95 < 10s |
| `tutor_session_status` | sync | < 2s |
| `tutor_session_end` | sync (triggers async Graphiti write-back in P1) | < 2s |

All four Phase-0 MCP tools are sync. No `_status`/`_cancel` companion tool is required.

**Phase 1 reversion condition.** If the Graphiti latency spike (per `phase-1-scope.md` §"Graphiti latency spike") shows that the Phase 1 student-model read at session start pushes `search_nodes` median > ~3s, `tutor_start_session` will be reclassified back to long-running and a `_status`/`_cancel` companion will be added. Reversion is conditional on measurement, not speculation. The reversion path is documented here and in `phase-0-scope.md §SR-07` so a future `/arch-refine` is unsurprising rather than disruptive.

## Alternatives considered

- **Keep `tutor_start_session` long-running for forward compatibility (ADR-ARCH-008's original choice).** Rejected. The forward-compat argument requires phase-stability, which `phase-1-scope.md` already contradicts. Meanwhile the long-running classification has no operational basis in Phase 0 — there is no polled task, no `_status`/`_cancel` companion, and the registered tool description misrepresents the handler. Holding the classification for a forward-compat that may not survive measurement creates a guaranteed current SR-07 violation in exchange for a hypothetical future continuity that may not materialise.

- **Add a `_status`/`_cancel` companion to honour the long-running classification.** Rejected. Introduces dead protocol surface in Phase 0 (a polling endpoint that has nothing to poll) to satisfy a classification with no operational basis. Increases the four-tool surface, complicates the demo script, and provides no value to either Lilymay or judges.

- **Mark Phase 0 classification as TBD until the Phase 1 latency spike.** Rejected. SR-07's acceptance criterion is explicit: "Every MCP tool in Phase 0 classified as either 'sync' (< 30s bound) or 'long-running' (returns session_id immediately, poll via companion). No tool in the undefined middle." TBD is exactly the undefined middle.

## Consequences

**Positive:**
- The Phase 0 SR-07 contract aligns with shipped behaviour. The current violation is resolved.
- The Phase 1 reversion path is documented and conditional on a specific empirical measurement — replacing forward-compat speculation with a measurement-conditional rule.
- The four-tool MCP surface stays minimal (no companion `_status`/`_cancel` for `tutor_start_session`).
- The classification is now derivable from inspection of `src/study_tutor/mcp/adapter.py` rather than from architectural commitment alone.

**Negative:**
- If the Phase 1 Graphiti latency spike shows `search_nodes` median > ~3s and we revert to long-running, MCP integrators (Claude Desktop, the demo script) will see a tool description change — visible in their tool list. This is a description-string change, not an API break, and the spike result will be known before any P1 implementation work commits to the tool surface.
- Two ADRs (ARCH-008 and ARCH-017) now need to be read together to understand the SR-07 classification subdecision. Mitigated by the partial-supersession status block on ARCH-008 and by both ADRs being co-located in `docs/architecture/decisions/`.

## Affected downstream artefacts

This decision supersedes wording in the following derived artefacts (all updated in the same `/arch-refine` run):

- `docs/architecture/domain-model.md §7.1` — table row for `tutor_start_session`.
- `docs/architecture/container.md` — C4 Container description for the MCP Adapter.
- `docs/research/ideas/phase-0-scope.md §SR-07` — classification table, header note, reversion conditions, FEAT-PO-002 bullet.
- `docs/research/ideas/phase-0-build-plan.md` — SR-07 verification step (punch-list item 7's D2 record stays as historical context).
- `docs/design/README.md §3 D2 + §7.4` — design follow-up note marked resolved.
- `src/study_tutor/mcp/server.py` — registered tool description (the canonical SR-07 contract).
- `src/study_tutor/mcp/adapter.py` — module docstring.

## References

- ADR-ARCH-008 (partially superseded): MCP-only for agent access; single-user auth posture.
- ADR-ARCH-009: Six parity surfaces (LES1) as load-bearing cross-cutting concerns.
- LES1 §1 row 19 + TASK-MDF-POLR — `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md`.
- `docs/design/README.md §3 D2` — design pass that surfaced this contradiction.
- `docs/research/ideas/phase-1-scope.md §"Graphiti latency spike"` — the empirical reversion condition.
