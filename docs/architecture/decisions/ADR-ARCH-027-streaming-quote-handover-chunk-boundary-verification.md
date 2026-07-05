# ADR-ARCH-027 — Quote verification under streaming: verify at the sentence-chunk boundary

## Status

Accepted

**Date:** 2026-07-05 (gate G-RAT, voice scope & build plan §5a)
**Phase:** Voice feature planning (pre-W1); implemented at W2 (TASK-STREAM-001 + FEAT-VOICE-002)
**Related:** **Extends** [ADR-ARCH-026](ADR-ARCH-026-player-coach-async-coach-monitor-streaming-ready.md) D3 (synchronous factual guardrail) onto the streaming path; resolves the open question named in ADR-ARCH-026 D4a, `docs/design/voice-implementation-blueprint.md` §4.3, and [TASK-STREAM-001](../../../tasks/backlog/TASK-STREAM-001-tutor-turn-token-streaming.md) Scope 1. Design: `docs/design/voice-tutor-and-reachy-design.md` §5.3–5.4. Does **not** supersede any prior ADR.

## Context

ADR-ARCH-026 D3 keeps `apply_quote_verification` synchronous: never show a fabricated
quote — the highest-harm error class for a minor-facing English-literature tutor. That
gate was defined for whole-response turns. Token streaming (ADR-ARCH-026 D4, executed
as TASK-STREAM-001) breaks the assumption: tokens reach the student before the full
response exists, and tutor voice (FEAT-VOICE-002) additionally *speaks* them via
sentence-chunked TTS. The blueprint (§4.3) required this handover to be decided
explicitly, not silently by the voice implementation. The voice design is
streaming-first — the contract freezes at G-CON before any build wave — so the
handover shape must be settled now, not at the W2 design pass.

## Decision

**Verify at the sentence-chunk boundary.** The streaming pipeline already buffers the
token stream into sentence chunks of ~15–25 words (the TTS synthesis unit, chosen for
Qwen3-TTS voice consistency). Each completed chunk passes quote verification
(`apply_quote_verification`, scoped to the text accumulated so far) **before** its
tokens are emitted to the client and before the chunk is synthesized. A chunk
containing an unverifiable quote is corrected/annotated before it is ever shown or
spoken.

Properties:
- The learner-visible/audible stream never contains an unverified quote — D3's
  guarantee is preserved at chunk granularity.
- Streaming survives: the hold point is a buffer that already exists for TTS; the
  verification cost per chunk is bounded and overlaps TTS synthesis of the previous
  chunk.
- The non-streaming path is unchanged (whole-response verification, exactly D3).

## Alternatives considered

- **Verify-then-stream** (hold all tokens until generation completes, verify, then
  emit). Rejected: it cancels token streaming entirely — time-to-first-token collapses
  back to full-generation latency, which is the wall streaming exists to break.
- **Stream-then-annotate** (emit/speak immediately, annotate or correct after
  verification). Rejected: an unverified quote reaches the student — and on the voice
  path is *spoken aloud* — before correction. Speaking a fabricated quote is strictly
  worse than showing one; this inverts the D3 principle.
- **Defer to the TASK-STREAM-001 design pass** (the blueprint §4.3 placement).
  Rejected as sequencing: the voice design is streaming-first and the G-CON contract
  freeze encodes the frame flow; freezing a contract whose verification semantics are
  undecided would either force a second freeze or decide the question silently.

## Consequences

**Positive:**
- One verification rule serves text streaming and voice; FEAT-VOICE-002 and
  TASK-STREAM-001 implement against a settled shape.
- G-CON can freeze the streaming frame vocabulary without an open semantic hole.

**Negative / accepted costs:**
- Per-chunk verification adds bounded latency to each chunk's emission (overlapped
  with TTS on the voice path; small but nonzero on the text-streaming path).
- Quote spans that straddle a chunk boundary must be handled (verifier sees
  accumulated text, not the isolated chunk) — an implementation obligation on W2,
  named here so it is tested, not discovered.

## Downstream artefacts

- [TASK-STREAM-001](../../../tasks/backlog/TASK-STREAM-001-tutor-turn-token-streaming.md)
  Scope 1 — its open question ("verify-then-stream vs stream-then-annotate") is
  resolved by this ADR; the design pass consumes this decision.
- `docs/design/voice-implementation-blueprint.md` §4.3 — its instruction to decide at
  the TASK-STREAM-001 design pass is satisfied early, at G-RAT (the voice design
  records why the decision was pulled forward).
- `docs/design/voice-tutor-and-reachy-design.md` §5.4 — the recommendation this ADR
  ratifies.

## References

- ADR-ARCH-026 D3/D4 · voice-tutor-and-reachy-design.md §5.3–§5.4 ·
  voice-implementation-blueprint.md §4.3 · unified-voice-orientation.md §2
  (sentence-chunking pin) · `src/study_tutor/tutoring/` `coach_handover` /
  `apply_quote_verification` (the mechanism this extends)
