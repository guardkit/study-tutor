---
id: TASK-STREAM-001
title: "Tutor-turn token streaming (the real UX win) — server stream + streaming transport + app client"
status: backlog
task_type: feature
implementation_mode: task-work
complexity: 8
dependencies: [ADR-ARCH-026, ADR-ARCH-027]
adr: docs/architecture/decisions/ADR-ARCH-026-player-coach-async-coach-monitor-streaming-ready.md
---

## Why this exists (do not lose it)

ADR-ARCH-026 made the Coach an **async monitor** (phase 1, done) — the
streaming-ready shape, because a pre-send Coach gate is incompatible with
streaming. Streaming itself (phase 2, this task) is the **real UX win**:
perceived latency ≈ time-to-first-token instead of full-generation time, which
is what a responsive tutoring chat (and the voice path) actually needs. It is
filed as a task rather than left in conversation so it is tracked, per the
owner's explicit "don't let streaming get lost in the noise" (2026-07-05).

**This is purely additive to async Coach — none of ADR-ARCH-026's work is
reworked.** `generate_stream` sits alongside `generate`; a streaming endpoint
sits alongside the JSON one.

## Scope (cross-team — not a server-only change)

1. **Server — streaming Player generation.** Add a `generate_stream` path on
   the Player LLM adapter / `LLMClient` (the underlying llama-swap/OpenAI
   endpoint already supports SSE token streaming). The Coach stays async
   (ADR-ARCH-026 D1), evaluating the assembled full response after the stream
   completes. ~~The synchronous quote-handover (ADR-ARCH-026 D3) needs a
   streaming-compatible story — decide: verify-then-stream (adds first-token
   latency) vs stream-then-annotate.~~ **Decided 2026-07-05 at G-RAT:
   verify-at-the-sentence-chunk-boundary —
   [ADR-ARCH-027](../../docs/architecture/decisions/ADR-ARCH-027-streaming-quote-handover-chunk-boundary-verification.md).
   Implement to that shape (note its chunk-straddling-quote obligation).**
2. **Transport + contract.** Add a streaming surface — SSE, or the WebSocket
   `turn` the binding sketches (`API-session-http-binding.md` §7; the `stream?`
   request field is already reserved). This is a **`BINDING_SHA` change**:
   coordinate with the app side, re-freeze, bump the pinned SHA. Align with the
   voice transport shape left open in ADR-ARCH-024 (OQ#2 — Realtime-style WS vs
   discrete routes) so tutor-turn streaming and voice share one transport.
3. **App (Flutter, Mac side).** A streaming client (SSE/WS consumer) +
   incremental UI rendering of partial tokens. This is the majority of the
   user-visible work and is the app team's domain.
4. **Acceptance.** Streaming variants of the 35-assertion contract suite
   (`app/test_live/`), plus the non-streaming JSON endpoint retained for
   clients that don't stream.

## Not required for the 15s deadline

Async Coach (ADR-ARCH-026) already brings the typical turn inside the 15s app
deadline. Streaming is the polish / voice / long-response win, sequenced when
the team is ready to spend the cross-team cost — not a prerequisite for the
FEAT-APP-001 cross-device walk.

## References

- [ADR-ARCH-026](../../docs/architecture/decisions/ADR-ARCH-026-player-coach-async-coach-monitor-streaming-ready.md) (D4 — streaming as phase 2, this task)
- [ADR-ARCH-027](../../docs/architecture/decisions/ADR-ARCH-027-streaming-quote-handover-chunk-boundary-verification.md) (quote handover under streaming — decided; consume, don't re-open)
- [ADR-ARCH-024](../../docs/architecture/decisions/ADR-ARCH-024-voice-stt-cache-aware-streaming-multilingual-deferred.md) (voice transport shape, OQ#2)
- `docs/design/contracts/API-session-http-binding.md` §7 (`stream?`, WS token streaming, deferred to OQ2)
