# ADR-ARCH-018 — Extend load-bearing cross-cutting concerns with SR-08 (Graphiti async write-back) and SR-09 (runtime LLM parameters explicit)

## Status

Accepted

**Date:** 2026-04-27
**Phase:** Phase 1
**Supersedes:** [ADR-ARCH-009](ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md) — Six parity surfaces (LES1) as load-bearing cross-cutting concerns
**Related:** LES1, CC-01 through CC-08, CC-13, CC-14, ADR-ARCH-003, [phase-1-scope.md §SR-08 / §SR-09](../../research/ideas/phase-1-scope.md), [graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md)

## Context

ADR-ARCH-009 promoted the six LES1 parity surfaces (SR-01 through SR-07) plus CC-08 ("fire-and-forget + poll above 30s") to first-class cross-cutting concerns in Phase 0. Two new pieces of evidence have arrived since:

1. **[phase-1-scope.md](../../research/ideas/phase-1-scope.md) introduces two additional structural requirements** that are intended to be load-bearing across every Phase 1 feature, not just scope-doc lore:
   - **SR-08** — Graphiti episode creation and entity updates are fire-and-forget from the tutor's caller-facing path. `tutor_session_end` returns within 2 seconds regardless of Graphiti write latency; write failures are logged but do not surface to the MCP caller.
   - **SR-09** — Every Ollama Modelfile used by the tutor must set explicit `num_ctx` (≥16384 for RAG-enabled personas) and `num_predict` (≥1500 for tutoring responses), with smoke-test assertions via `ollama show <model> --modelfile | grep PARAMETER` and via the runner log line `llama_new_context_with_model: n_ctx = N` from a real inference call.

2. **The 27 April 2026 Graphiti latency spike** ([graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md)) measured the post-21-Apr vLLM-on-GB10 stack and found:

   | Operation | Median (s) |
   |---|---:|
   | `add_episode` | **78.98** |
   | `search_nodes` | 0.07 |
   | `search_memory_facts` | 0.08 |

   `add_episode` median is 78.98s — over 15× the 5s threshold the Phase 1 scope used as the SR-08 trigger. CC-08's original framing ("fire-and-forget + poll above 30s") is generic; with measured numbers it now specialises to a Graphiti-write-specific invariant that is load-bearing at every write point in the tutor, not just `tutor_session_end`.

   Conversely, `search_nodes` at 0.07s confirms ADR-ARCH-017's sync classification of `tutor_start_session` (and similarly the other read-path tools) — the read side is not the load-bearing one.

SR-09 is unrelated to latency but emerged from the [23 April OpenWebUI RAG empirical findings](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md): Ollama's default `num_ctx=2048` silently truncates tutoring responses mid-sentence when RAG is active. This is a structural failure mode rather than a per-feature concern, so it belongs alongside the parity-surface set.

## Decision

The load-bearing cross-cutting concerns set is extended from **eight** (CC-01 through CC-08) to **fourteen**, retaining CC-09 through CC-12 unchanged from ARCHITECTURE.md §6:

- **CC-01 through CC-07** — unchanged from ADR-ARCH-009; LES1 parity surfaces SR-01 through SR-07.
- **CC-08** — *Generic* fire-and-forget + poll-above-30s discipline (LES1 §4). Retained as the cross-agent rule; specialised below.
- **CC-09 through CC-12** — unchanged (safeguarding boundary, copyright/provenance boundary, in-process event bus vocabulary, async-capable subagent boundary).
- **CC-13 (NEW) — Graphiti write-back is asynchronous from every caller-facing path (SR-08).** Specialises CC-08 with measurement: with `add_episode` median 78.98s, the rule is not just "above 30s" — Graphiti writes are *always* async-from-caller, *every* write point (session-end, mid-session episodes, misconception logs, topic-confidence updates), and write failures are logged-only.
- **CC-14 (NEW) — Runtime LLM parameters are explicit and asserted (SR-09).** Every Modelfile sets explicit `num_ctx` and `num_predict`; smoke tests assert both via `ollama show` *and* via runner log inspection on a real inference call.

The CC numbering avoids colliding with the existing CC-09–CC-12 (which were promoted by ADR-ARCH-010 through ADR-ARCH-013) by placing the new codes at the end of the sequence.

Every Phase 1 feature honours CC-13 and CC-14 structurally:
- **CC-13** — every Graphiti write site goes through helpers that run the work as a background task (deepagents `AsyncSubAgent` per ADR-ARCH-012, or a plain `asyncio.create_task` for simple writes). Caller-facing handlers complete without awaiting Graphiti acknowledgement. Write failures emit a structured log line; they do not raise from the MCP handler.
- **CC-14** — a smoke test (per Modelfile change) runs `ollama show` and parses runner-log output to confirm `num_ctx` and `num_predict` reach the runner at expected values. Regression trips the test.

LES1 remains the evidence base for CC-01–CC-08; the [Phase 1 scope document](../../research/ideas/phase-1-scope.md) and the [27 Apr latency spike](../../research/ideas/graphiti-latency-spike-results.md) are the evidence base for CC-13; the [23 Apr OpenWebUI RAG findings](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) are the evidence base for CC-14.

## Alternatives considered

- **Leave SR-08 / SR-09 as Phase 1 scope-doc lore only.** Rejected. The Phase 0 lesson from ADR-ARCH-009 was that promoting parity surfaces to first-class CCs ensures every feature audits against them. Repeating the same elevation for SR-08 / SR-09 keeps the discipline consistent, and the latency spike makes SR-08 too consequential to leave at scope-doc level.
- **Inline the SR-08 changes into ADR-ARCH-003 (async Graphiti write-back) instead of refining ADR-ARCH-009.** Rejected. ADR-ARCH-003 is a *single-write-point* decision (session-end boundary). The latency spike shows write-back must apply at *every* write point, which is a cross-cutting concern, not a session-boundary policy. ADR-ARCH-003 will need its own follow-up `/arch-refine` to broaden its scope (flagged stale by this ADR; not modified here).
- **Supersede the SR series entirely with a new "LES1 + Phase 1 lessons" combined ADR.** Rejected. The LES1 parity surfaces and the Phase 1 additions have different evidence bases (cross-agent monorepo lore vs measured Graphiti latency / OpenWebUI empirical findings); collapsing them would obscure the chain of evidence. Keeping the supersession surgical (one ADR-ARCH-009 → one ADR-ARCH-018) preserves traceability.

## Consequences

**Positive:**
- Every Phase 1 feature has a 14-row checklist to audit against, not just the 8 from Phase 0. The two new rows are exactly the ones the Phase 1 scope identified as load-bearing.
- CC-13 forces Graphiti write-back patterns to be uniform across the tutor: session-end, mid-session, planner updates, Coach-observed misconceptions all go through the same fire-and-forget shape. No per-feature ad-hoc await of Graphiti.
- CC-14 closes a known silent failure mode (Modelfile param defaults overriding intended runtime configuration) before it can corrupt RAG-enabled persona behaviour.
- The latency spike's measurement (78.98s median) is now load-bearing in an architecture artefact, not just a research note — future agents reading the architecture see why CC-13 is non-negotiable.

**Negative:**
- ADR-ARCH-003 (async Graphiti write-back at session-end boundary) becomes too narrow in framing. It is flagged stale by this refinement and will need a separate `/arch-refine` to broaden to "every write point" semantics. Until that refinement, ADR-ARCH-003's scope statement is a strict subset of CC-13's; the two are consistent but not coextensive.
- Five design contracts (`API-mcp-transport`, `API-tutoring`, `DM-mcp-transport`, `events-schema.yaml`, `design/README.md`) that reference CC-08 in its generic form are flagged stale. Their CC-08 references remain *correct*; they just no longer enumerate CC-13 / CC-14. `/system-design` will detect and report these on next run.
- Adding a smoke test for CC-14 introduces a small per-Modelfile-change CI/manual cost. Accepted as cheap relative to the silent-truncation regression class it prevents.

## Downstream artefacts flagged stale

The following artefacts reference the previous (8-CC) framing and should be updated when convenient:

- **ADR-ARCH-003** — single-write-point framing; needs `/arch-refine` to broaden to every-write-point.
- `docs/architecture/domain-model.md` §324, §351 — CC-08 references only; correct but not mentioning CC-13.
- `docs/architecture/container.md` — tool-description rows for the MCP adapter; CC-08-aligned but not updated for CC-13's every-write-point semantics.
- `docs/design/contracts/API-mcp-transport.md` — 4 CC-08 references in invariants and adapter table.
- `docs/design/contracts/API-tutoring.md` — fire-and-forget references in classification rows.
- `docs/design/models/DM-mcp-transport.md` — CC-08 in invariants table.
- `docs/design/events-schema.yaml` — async write-back reference.
- `docs/design/README.md` — D2 closure note.

ADR-ARCH-009 itself remains queryable as the historical first-elevation decision; only its `Status` is updated to `superseded`. No content rewrite of ADR-ARCH-009.

## References

- [ADR-ARCH-009](ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md) — superseded predecessor.
- [ADR-ARCH-003](ADR-ARCH-003-async-graphiti-writeback.md) — single-write-point async decision (now narrower than CC-13).
- [ADR-ARCH-012](ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md) — `AsyncSubAgent` is the preferred mechanism for CC-13 conformance in Phase 1.
- [ADR-ARCH-017](ADR-ARCH-017-tutor-start-session-sync-classification.md) — sync classification corroborated by `search_nodes` 0.07s in the same spike.
- [phase-1-scope.md](../../research/ideas/phase-1-scope.md) — SR-08 and SR-09 origins.
- [graphiti-latency-spike-results.md](../../research/ideas/graphiti-latency-spike-results.md) — measured Graphiti latency, 27 Apr 2026.
- [openwebui-rag-empirical-findings-2026-04-23.md](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) — SR-09 origin.
- `specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md` (LES1) — origin of CC-01 through CC-08.
