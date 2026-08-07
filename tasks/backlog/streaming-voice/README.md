# FEAT-VOICE-002 — Streaming Voice (streaming-voice)

> **CLOSED 2026-08-07 (Lane 5 ledger closure): all 8 waves below BUILT + MERGED
> 2026-07-08 (`8d4bf2dd` — Tier A and Tier B both shipped; the Tier B gate was
> satisfied by FEAT-VOICE-001's prior merge `5d57b022`).** This README stays as the
> planning record; live status lives in the plan of record. Full wave/gate closure:
> `docs/research/ideas/voice-tutor-and-reachy-scope-and-build-plan.md` §0-close.

Streaming tutoring turns — live text and voice on the session channel,
implementing the streaming path of the frozen contract (Rev 1 §7 frames).

## Problem

Perceived turn latency is full-generation time. The frozen contract already
defines the streaming surface (WS live channel: `token`/`done` plus voice
frames `transcript`/`audio_ref`/`error`), ADR-ARCH-026 made the Coach an async
monitor (streaming-ready), and ADR-ARCH-027 decided chunk-boundary quote
verification — but `SessionService.turn_stream` is a stub, `LLMClient`
hardcodes `"stream": False`, and no `WebSocketRoute` exists.

## Solution (Option 1 — tiered dependency, from TASK-REV-F732)

- **Tier A (waves 1–4, no external deps)**: SSE streaming client
  (`generate_stream`/`respond_stream`), quote-aware sentence chunker with the
  fail-closed ADR-027 gate, `turn_stream` + widened `TurnEvent` + streaming
  orchestrator (durability parity, async Coach), WS route with
  auth-at-upgrade / voice-flag gating / per-session ordering lock, and the
  text-stream acceptance suite. **Tier A is a legitimate release point.**
- **Tier B (waves 5–7, gated on FEAT-VOICE-001)**: WS `voice_turn` STT
  ingestion reusing the VOX validation core, sentence-chunked TTS emitting
  `audio_ref` frames through the shared ChunkStore, voice acceptance suite.

## Subtasks

| Task | Title | Cx | Wave |
|------|-------|----|------|
| TASK-VS2-001 | LLM streaming client (generate_stream + respond_stream) | 5 | 1 |
| TASK-VS2-002 | Quote-aware sentence chunker + ADR-027 fail-closed gate | 7 | 1 |
| TASK-VS2-003 | turn_stream + TurnEvent widening + streaming orchestrator | 8 | 2 |
| TASK-VS2-004 | WS route: auth, flag, session-ordering lock, uvicorn[standard] | 7 | 3 |
| TASK-VS2-005 | Text-stream acceptance suite (Tier A closes) | 6 | 4 |
| TASK-VS2-006 | WS voice_turn STT + validation reuse (Tier B) | 7 | 5 |
| TASK-VS2-007 | Streaming TTS + audio_ref + ChunkStore (Tier B) | 6 | 6 |
| TASK-VS2-008 | Voice-channel acceptance suite (Tier B) | 6 | 7 |

**⚠️ Tier B gate**: VS2-006/007/008 import FEAT-VOICE-001's voice module
(VOX-001..005, planned but unbuilt at planning time). Do not run waves 5–7
until FEAT-VOICE-001 is complete. Open coordination item: TASK-VOX-004 needs a
bytes-blob-callable validation core (`validate_audio_bytes` extraction) —
raise before starting VS2-006.

## Provenance

- Parent review: TASK-REV-F732 (`.claude/reviews/TASK-REV-F732-review-report.md`)
- Spec: `features/streaming-voice/` (31 scenarios; 10 assumptions owner-confirmed 2026-07-06)
- Frozen: contract §7 Rev 1 + binding §2.1 Rev 1 (`CONTRACT_SHA=574615e9…`, `BINDING_SHA=e50897d1…`); ADR-ARCH-026 (Accepted), ADR-ARCH-027
- Subsumes TASK-STREAM-001 scopes 1/2/4 (Scope 3, the Flutter client, is FEAT-VOICE-003)
