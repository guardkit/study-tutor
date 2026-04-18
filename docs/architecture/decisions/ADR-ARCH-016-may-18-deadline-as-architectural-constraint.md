# ADR-ARCH-016 — 18 May 2026 deadline as load-bearing architectural constraint

## Status

Accepted

**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ALL other ADRs (timeline is the constraint they are all
optimising against)

## Context

Study Tutor's submission to the Gemma 4 Good Hackathon is due
**18 May 2026, 23:59 UTC**. From the `/system-arch` session date
(2026-04-18), that is 31 calendar days; subtracting DDD Southwest
(16 May) + weekend submission (17–18 May) + ~4 days of DDD prep
leaves roughly 18 effective working days.

This is an unusual architectural constraint in the literal sense —
it reshapes every technology decision. "Build the right thing" has a
fixed end date; "build the thing that can be visibly three-layer on
16 May demo capture" takes priority over "build the feature-complete
thing."

## Decision

**Timeline is a primary architectural constraint.** All other ADRs
are explicitly calibrated against it.

Specific timeline-shaped decisions:

- **Phase staging** (Phase 0 18–24 Apr, Phase 1 25 Apr – 11 May,
  Phase 2 12–16 May, Submission 17–18 May) — feature gating per
  phase rather than parallel development.
- **Bedrock in Phase 0, not Phase 2** (ADR-ARCH-006) — frees GB10
  and removes a demo-week dependency.
- **No Dockerfile in Phase 0** (ADR-ARCH-005) — saves SR-05 audit
  burden.
- **No caching / rate limiting / feature flags in Phase 0**
  (ADR-ARCH-011) — saves speculative work.
- **DDD over Modular Monolith** (ADR-ARCH-001) — accepts slightly
  more ceremony upfront to avoid mid-phase restructuring when
  gamification and student-model contexts land.
- **Three-layer explicitly described up front** (ADR-ARCH-002) —
  submission narrative depends on a clear architecture diagram;
  fuzz early and the submission suffers.
- **deepagents 0.5.3 AsyncSubAgent for Coach** (ADR-ARCH-012) —
  native SDK support, not hand-rolled; saves Phase 1 implementation
  time.
- **Reachy as stretch, gated 4 May** (ASSUM-015) — cannot be on the
  critical path.
- **Single-user scalability posture** (ADR-ARCH-014) — multi-tenancy
  would absorb the entire hackathon budget.

**Non-negotiables for 18 May:**

1. A public repo that passes the six parity surfaces in a clean
   walkthrough.
2. A working fine-tuned tutor, demoable on video.
3. The three-layer architecture visible and credibly instantiated.
4. At least a thin slice of Player-Coach proving the architecture
   runs end-to-end.
5. Technical write-up covering methodology + provenance +
   architecture + roadmap.

**Slip absorption:**

- Friday 25 April is a soft buffer day at end of Phase 0.
- If Phase 1 features slip, Phase 2 engagement-layer surface drops
  from full engine → Pydantic models + dashboard mockup.
- If Phase 2 slips, Reachy is the first stretch to drop.
- Safeguarding (CC-09), copyright (CC-10), parity surfaces (CC-01 to
  CC-08) **never drop** — they are architectural invariants.

## Alternatives considered

- **Ignore the timeline and build the best architecture.** Rejected.
  Over-engineering kills hackathon submissions. The judging is 18 May
  or never.
- **Cut scope to just Layer 1 + MCP + nice README.** Rejected.
  The three-layer architecture is the submission's core
  differentiator. Without Layer 3 credibly instantiated, Study
  Tutor looks like any other fine-tuned-model hackathon entry.

## Consequences

**Positive:**
- Every ADR has a shared "why this tradeoff" anchor.
- Phase gating is structural, not aspirational.
- Post-hackathon work has an obvious starting point (the deferred
  items).

**Negative:**
- Some Phase 0 choices (e.g. no Dockerfile, no caching) would be
  different if the horizon were longer. Accepted — this is what
  the 31-day burn looks like.
- Timeline slippage scenarios (Kaggle rule surprise, Bedrock
  incompatibility, deepagents 0.6.0 breaking release) would force
  mid-phase revision. Mitigated by explicit slip-absorption
  ordering above and by the ASSUM-017 read-Kaggle-rules Friday
  gate.

## References

- Phase 0 scope §Success Criteria.
- Phase 0 build plan §Day-by-day plan.
- `gemma4-hackathon-submission-plan.md` — overarching timing.
