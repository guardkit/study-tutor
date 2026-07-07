# Review Report: TASK-REV-F732 — Plan: FEAT-VOICE-002 streaming voice

## Executive Summary

FEAT-VOICE-002 implements the streaming path of the frozen contract (Rev 1 §7
frames) — typed streamed turns and spoken turns over a WebSocket live channel,
with sentence-chunked TTS, chunk-by-URL audio delivery, and chunk-boundary
quote verification per ADR-ARCH-027. The design, contract, and all ten spec
assumptions are ratified; nothing is re-opened. The decision under review was
**implementation structuring**, dominated by one fact: sibling feature
FEAT-VOICE-001 (voice-server-module, 7 VOX tasks) is planned but **not yet
implemented**, and the voice half of this feature consumes its components.

**Recommended: Option 1 — tiered dependency.** Tier A (LLM streaming client,
quote-aware sentence chunker, `turn_stream`/orchestrator, WS route + auth +
ordering lock, text-stream acceptance) has zero dependency on FEAT-VOICE-001
and can start immediately, in parallel with the VOX track. Tier B (WS
`voice_turn` STT ingestion, sentence-chunked TTS + `audio_ref` + chunk store,
voice acceptance) hard-depends on VOX-001/002/003/004/005 and must not be
scheduled before FEAT-VOICE-001 completes. 8 tasks, ~19h, aggregate
complexity 7.

- **Mode**: decision · **Depth**: standard
- **Focus**: all · **Trade-off**: quality/spec-fidelity (Context A)
- **Analyst**: software-architect agent (markdown-only; Graphiti retired)

## Options Evaluated

| Option | Shape | Risk | Verdict |
|--------|-------|------|---------|
| 1. Tiered dependency | Tier A independent now; Tier B hard-depends on VOX-001..005 | Medium (dependency discipline) | ✅ **Recommended** |
| 2. Full hard dependency | Everything waits for all of FEAT-VOICE-001 | Low | Wastes ~40% of scenario surface that has no VOX dependency; slowest calendar time |
| 3. Fold VOX pieces in | Duplicate config/errors/AudioClient/chunk store locally | High | ❌ Rejected — refusal-parity drift, two chunk stores, guaranteed rework |

## Recommended Task Breakdown (8 tasks, prefix VS2)

| Task | Title | Type | Cx | Min | Deps |
|------|-------|------|----|-----|------|
| VS2-001 | LLM streaming client (`generate_stream` + `respond_stream`) | feature | 5 | 90 | — |
| VS2-002 | Quote-aware sentence chunker + ADR-027 verification gate | feature | 7 | 150 | — |
| VS2-003 | `turn_stream`/`TurnEvent` widening + streaming orchestrator | feature | 8 | 180 | 001, 002 |
| VS2-004 | WS route: auth-at-upgrade, flag, session-ordering lock, uvicorn dep | feature | 7 | 150 | 003 |
| VS2-005 | Text-stream acceptance suite (Tier A closes) | testing | 6 | 150 | 004 |
| VS2-006 | WS `voice_turn` frame handling (STT, validation reuse) — **Tier B** | feature | 7 | 150 | 004 + VOX-001/002/003/004 |
| VS2-007 | Sentence-chunked TTS + `audio_ref` + chunk store — **Tier B** | feature | 6 | 120 | 002, 006 + VOX-002/005 |
| VS2-008 | Voice-channel acceptance suite — **Tier B** | testing | 6 | 150 | 006, 007 |

Waves: [001,002] → [003] → [004] → [005] → [006] → [007] → [008].
Max in-feature concurrency 2 (Wave 1). Tier A (waves 1–4) runs concurrently
with the FEAT-VOICE-001 VOX track; Tier B converges after VOX completes.

## Material Findings (beyond the spec)

1. **Fail-closed divergence (ASSUM-007)**: the existing
   `coach_handover.apply_quote_verification` *swallows* verifier exceptions and
   returns the unannotated response with `metadata.verifier_exception=True`
   (graceful degradation). The streaming gate must inspect that flag and
   **fail closed** — a deliberate, documented policy divergence in VS2-002/003.
   `coach_handover.py`/`quote_verifier.py` are not modified.
2. **VOX-004 extraction gap**: `parse_voice_upload` is scoped for Starlette's
   HTTP `request.stream()` multipart; the WS path needs the validation core
   (size→empty→MIME→duration + six exceptions) callable on a plain bytes blob.
   Resolve as a small scope note on FEAT-VOICE-001 TASK-VOX-004 (shared
   `validate_audio_bytes`-shaped core) — do NOT write a second validator in
   VS2-006.
3. **Session-ordering lock is new machinery (ASSUM-008)**: a per-`session_id`
   serialization lock (not per-connection) is required for ordered,
   non-interleaved turns across one channel and across two devices. Nothing in
   today's `SessionService` provides this (contract §4 is last-writer-wins).
   Lands in VS2-004; flagged for Coach architectural review.
4. **Chunker must be quote-aware** (ADR-027 straddling obligation):
   `verify_quotes` only recognises a quote once its closing mark is seen, so
   the chunk boundary itself must defer while an odd number of quote marks is
   pending. Verification always runs against accumulated text; released text
   is never retroactively altered.

## Risk Register

- **ASSUM-003** terminal/non-terminal error split: terminal half VS2-004, non-terminal half VS2-006.
- **ASSUM-005** disconnect-survives: generation/persistence/Coach-dispatch detached from the WS handler's cancellation scope (VS2-003; load-bearing test).
- **ASSUM-009** stall bound: httpx **read-timeout** semantics on the stream, not total-deadline (VS2-001).
- **ASSUM-010** eviction policy is VOX-005's; VS2-008 only consumes/tests it — cannot be written before VOX-005 exists.
- **BINDING_SHA discipline**: no task touches the contract docs; VS2-003/004 pin `TurnEvent` serialization byte-for-byte against contract §7 Rev 1. No re-freeze.
- **Single-worker constraint**: `uvicorn[standard]` dep added in VS2-004 must not be paired with a multi-worker deploy (in-memory chunk store assumption, design §5.2).
- **Test isolation**: new acceptance tests either run `--concurrency=1` or avoid global reset (fresh session per test) — explicit decision in VS2-005.

## Operator-handoff candidates

1. Live confirmation of the real ~120 s stall bound ("the turn fails visibly
   after a bounded wait") — hermetic mock in VS2-001 suffices; live wait-out is
   operator-only if wanted.
2. Live long-answer chunk-availability run ("every announced chunk is still
   available when its turn to play arrives") under real TTS pacing + real TTL.
3. Design §5.6 never-at-rest sweep ("no bytea/blob columns + disk sweep") —
   explicitly a human-conducted infrastructure sweep per the LPA evidence
   method.

These are follow-up verification items, not autobuild task ACs; the task ACs
stay hermetic. (Decision: keep all 8 tasks autobuild-suitable; record the
three live checks in the IMPLEMENTATION-GUIDE as operator follow-ups.)

## Decision Matrix

| Option | Fidelity | Calendar time | Duplication | Recommendation |
|--------|----------|---------------|-------------|----------------|
| 1 Tiered | High | Best | None | ✅ Implement |
| 2 Serial | High | Worst | None | Fallback |
| 3 Fold-in | Degrades | Illusory win | High | Reject |
