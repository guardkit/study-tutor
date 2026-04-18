# ADR-ARCH-011 — No caching / rate limiting / feature flags in Phase 0

## Status

Accepted

**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ADR-ARCH-014 (single-user), ADR-ARCH-016 (timeline)

## Context

Common architectural concerns that teams often build in speculatively:

- **Caching layers** (response cache, embedding cache, RAG-chunk cache).
- **Rate limiting** (per-user, per-token, per-provider).
- **Feature flags** (runtime switches for phase-straddling behaviour).

Each of these adds infrastructure and mental overhead. Phase 0's
explicit goal is a skeleton that passes the six parity surfaces and
ships a working tutor; speculative optimisation compounds timeline
risk with no Phase 0 benefit.

Phase 0 is also single-user and on-device, so the classical use
cases for these concerns don't apply.

## Decision

Phase 0 **does not include**:

- **No caching.** LLM responses, RAG chunks, Graphiti queries — all
  uncached. Revisit Phase 1+ only after the latency spike measures
  actual bottlenecks.
- **No rate limiting.** Single user; no abuse surface. External
  provider APIs are rate-limited by the vendor, which is sufficient.
- **No feature flags.** Phase gating is handled by git commits and
  the `phase-N-scope.md` docs — not by runtime flags.
  Phase-straddling code does not belong in Phase 0.

If Phase 1+ measurement surfaces a real need, each gets its own ADR.

## Alternatives considered

- **Build response-cache framework from day 1.** Rejected.
  Premature; Ollama-local responses are cheap and varied per student
  turn; no cache-hit rate signal.
- **Ship a `ConfigFlag` abstraction for Phase 2 features.** Rejected.
  Violates YAGNI; Phase 2 features are non-existent in Phase 0 code
  and should be added when they exist, not stubbed under a flag.
- **Rate limiting on outbound provider calls (Gemini, Bedrock).**
  Rejected for Phase 0 — at this traffic level (single-user,
  <10 sessions/day), vendor-side rate limits won't be touched.

## Consequences

**Positive:**
- Smaller Phase 0 surface; weekend build target realistic.
- No premature abstractions to unwind in Phase 1 if measurements show
  a different bottleneck than anticipated.

**Negative:**
- If a Phase 1 latency spike surfaces a bottleneck (e.g. ChromaDB RAG
  retrieval), a cache layer has to be added mid-build. Accepted;
  targeted intervention is cheaper than speculative framework.
- Phase 2 features might benefit from feature-flag gating for demo
  vs production. Accepted — add when the need is real.

## References

- YAGNI principle as applied in `CLAUDE.md` (don't design for
  hypothetical future requirements).
- Phase 0 scope §Do-Not-Change list.
