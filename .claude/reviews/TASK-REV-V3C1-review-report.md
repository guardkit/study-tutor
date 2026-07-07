# Review Report: TASK-REV-V3C1

**Plan: Flutter tap-to-talk voice client (FEAT-VOICE-003)**

## Review Details
- **Mode**: Decision
- **Depth**: Standard
- **Focus**: All aspects (Context A)
- **Trade-off priority**: Quality/reliability (Context A)
- **Knowledge graph**: Unavailable (Graphiti retired for study-tutor)

## Executive Summary

FEAT-VOICE-003 is a **client-only** Flutter feature whose architecture is already
strongly pre-decided by `docs/design/voice-tutor-and-reachy-design.md §6`: a new sibling
`VoiceApi` port (leaving the frozen `SessionApi` untouched), an `HttpVoiceApi` reusing the
`HttpSessionApi` seams (base-URL normalization, bearer `_headers()`, envelope→sealed-exception
mapping), `FakeVoiceApi`/`FlakyVoiceApi` for hermetic tests, and mic/playback UX bolted onto
`SessionScreen` behind the existing `_sending`/`_ended` guards. Three new runtime deps
(`record`, `just_audio`, `web_socket_channel`) and Android/iOS manifest permissions are a
deliberate, spec-recorded scope event.

Because the design pre-settles the *approach*, the real decision is **sequencing and slicing**
for a quality-weighted delivery. The dominant quality risk is the **"green-but-broken" fidelity
seam** — a recording that uploads successfully but reaches the tutor mis-authenticated, on the
wrong session, or re-encoded — which only the hermetic MockClient direction-pins catch. The plan
front-loads the port + fidelity pins before any UX, and gates the encoder choice (ASSUM-006,
Phase-0 m4a-against-live-STT) rather than hard-coding it.

## Current Situation Assessment

- **App architecture**: clean ports & adapters. `app/lib/ports/session_api.dart` (frozen),
  `app/lib/adapters/http_session_api.dart` (280 LOC, the reuse target), `app/lib/ui/session_screen.dart`
  (204 LOC, mic host), `app/lib/fakes/` (fake pattern to mirror), `app/test_live/` (live-suite discipline).
- **Spec**: 22 scenarios, 11 assumptions (8 high / 1 medium / 2 low). All confirmed by human.
- **Companion features**: FEAT-VOICE-001 (server rulebook) + FEAT-VOICE-002 (server streaming)
  own the server; this feature asserts only the **client's surfacing and recoverability**.
- **Open items**: ASSUM-006 (encoder, Phase-0 gated), ASSUM-010/011 (permission + refusal copy,
  low-confidence — behaviour firm, wording inferred).

## Option Evaluation Matrix

| Option | Approach | Quality fit | Effort | Risk | Recommendation |
|--------|----------|-------------|--------|------|----------------|
| **1. Port + fidelity first, then MVP HTTP, then streaming** | Build `VoiceApi` port + direction-pins + degradation before any UX; MVP HTTP turn before WS streaming | **Highest** — fidelity seam proven before feature surface grows | Medium | Low | ✅ **Recommended** |
| 2. Streaming-first | Build the WS path first, retrofit MVP | Medium | High | Medium — WS ordering + incremental render is the hardest surface, poor first foothold | No |
| 3. Big-bang single task | One large "add voice" task | Low | Medium | High — collapses the fidelity seam into UX churn; Coach can't isolate the green-but-broken defence | No |

**Rationale for Option 1**: The trade-off priority is quality/reliability. The fidelity defence
(§6.4 "green but broken", ported from the LPA to the Dart seam) is the single highest-value test
asset. Building the port and its MockClient direction-pins *before* the mic UX means every later
UX slice is added on top of a proven-correct upload seam. MVP HTTP (`voiceTurn`) before streaming
(`voiceTurnStream`) gives a shippable transcript-first loop early; streaming's incremental render +
`seq`-ordered playback layer on afterwards without reworking the port.

## Recommended Task Breakdown (7 tasks, quality-weighted)

1. **TASK-VC-001 — Scope event: deps + platform manifests** (`scaffolding`, cx 3)
   Pin `record`, `just_audio`, `web_socket_channel` in `pubspec.yaml`/`pubspec.lock`; add Android
   `INTERNET` + `RECORD_AUDIO` to the **main** manifest (release currently has no network permission),
   iOS `NSMicrophoneUsageDescription`. NSC extension as posture hygiene only. Covers `@edge-case @regression`
   "shipped app can record and reach the tutor".
2. **TASK-VC-002 — `VoiceApi` sibling port + DTOs** (`declarative`, cx 3)
   `VoiceApi` interface (`voiceTurn`, `voiceTurnStream`, `fetchAudioChunk`), `VoiceTurnResult`/`VoiceTurnEvent`
   types, six voice `error_type` sealed members incl. `VoiceUnavailable`. Leaves `SessionApi` untouched.
3. **TASK-VC-003 — `HttpVoiceApi` + fidelity direction-pins** (`feature`, cx 6)
   MVP HTTP `voiceTurn` reusing `HttpSessionApi` seams; MockClient direction-pins asserting method/path/
   auth/multipart field `audio`/filename/content-type **with codec params intact**. The green-but-broken
   defence. Covers `@key-example @smoke` "delivered exactly as recorded".
4. **TASK-VC-004 — `FakeVoiceApi`/`FlakyVoiceApi` + recorder (60 s/10 MB stop)** (`feature`, cx 5)
   Fakes mirroring `FlakySessionApi`; `record` integration with client-side 60 s hard stop + 10 MB backstop;
   encoder m4a/AAC default, opus fallback **behind the Phase-0 gate (ASSUM-006)**. Covers `@boundary` 59s/60s
   + cancel/interruption edge cases.
5. **TASK-VC-005 — SessionScreen tap-to-talk UX + degradation** (`feature`, cx 6)
   Mic button in input row behind `_sending`/`_ended`; transcript-first render; amber `VoiceUnavailable`
   notice (verbatim copy, ASSUM-003/004); mic-permission explain-don't-fail; connection-problem preserves
   recording. Covers the negative-case scenarios + `@edge-case` mic/session guards.
6. **TASK-VC-006 — Streaming path: `voiceTurnStream` + ordered playback** (`feature`, cx 7)
   WS `voiceTurnStream`; `just_audio` ordered queue keyed by `seq`; incremental text ahead of audio;
   ephemeral-part skip (TTL); per-part authenticated fetch. Covers `@key-example @smoke` streaming +
   `@edge-case` skip/stop/auth scenarios.
7. **TASK-VC-007 — Dual-backend + live voice tests** (`testing`, cx 5)
   Contract-style bodies through the dual-backend harness (fake + `LiveContractBackend`); voice variants
   into `app/test_live/` (`--concurrency=1`, quiet GPU, 60 s deadline). Ports the direction-pins to the
   live seam.

**Open-item handling**: ASSUM-006 encoder is gated inside TASK-VC-004 (fidelity holds regardless of
winner). ASSUM-010/011 copy is low-confidence — flagged as `operator_handoff`-adjacent verification, but
the scenarios are hermetic-testable against whatever strings are chosen, so they remain autobuild-suitable.

## Disconnection check (preview)

Write path (record → `voiceTurn` upload) and read paths (transcript render, ordered playback, chunk fetch)
are all wired in the breakdown. The streaming read path (TASK-VC-006) depends on FEAT-VOICE-002 server
delivery — a **cross-feature** seam, not a disconnected in-feature read. Will be called out in the guide.

## Decision Options

- **[A]ccept** — save this analysis for later
- **[R]evise** — deeper analysis on a specific area (encoder gate, streaming, test harness)
- **[I]mplement** — generate the feature structure (7 tasks + guide + diagrams + YAML + BDD linking)
- **[C]ancel** — discard
