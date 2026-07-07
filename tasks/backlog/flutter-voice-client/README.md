# FEAT-VOICE-003: Flutter tap-to-talk voice client

**Source:** `/feature-plan "Flutter tap-to-talk voice client"` · **Review:** TASK-REV-V3C1
**Spec:** `features/flutter-voice-client/` (22 scenarios, 11 assumptions) · **Design:** `docs/design/voice-tutor-and-reachy-design.md §6`

## Problem

The study-tutor Flutter app (`app/`) has no voice. Students should be able to ask a question by
speaking and hear the answer spoken back, hands-free — while typed tutoring keeps working exactly
as before. The shipped release build today has **no network permission at all**, so a voice app
must also fix that.

## Solution (client-only)

Add a new **sibling** `VoiceApi` port (leaving the frozen `SessionApi` untouched), an `HttpVoiceApi`
reusing the `HttpSessionApi` seams, hermetic `Fake`/`FlakyVoiceApi`, and mic/playback UX on
`SessionScreen`. Ship the MVP HTTP transcript-first loop first; layer the WS streaming path
(incremental text + `seq`-ordered playback) on top. Three new runtime deps (`record`, `just_audio`,
`web_socket_channel`) + Android/iOS manifest permissions are a deliberate, spec-recorded scope event.

The defining quality asset is the **"green but broken" fidelity defence**: MockClient direction-pins
proving a recording reaches the tutor authenticated, on-session, and in the exact captured format.

## Subtasks

| ID | Title | Type | Cx | Wave | Deps |
|----|-------|------|----|------|------|
| TASK-VC-001 | Deps + Android/iOS manifests | scaffolding | 3 | 1 | — |
| TASK-VC-002 | VoiceApi port + DTOs + sealed errors | declarative | 3 | 1 | — |
| TASK-VC-003 | HttpVoiceApi (MVP) + fidelity direction-pins | feature | 6 | 2 | VC-002 |
| TASK-VC-004 | Fakes + recorder (60s/10MB, gated encoder) | feature | 5 | 2 | VC-001, VC-002 |
| TASK-VC-005 | SessionScreen tap-to-talk UX + degradation | feature | 6 | 3 | VC-003, VC-004 |
| TASK-VC-006 | Streaming voiceTurnStream + ordered playback | feature | 7 | 4 | VC-005 |
| TASK-VC-007 | Dual-backend contract + live voice tests | testing | 5 | 5 | VC-003, VC-005, VC-006 |

## Boundaries

- **Not** FEAT-VOICE-001 (server upload-validation rulebook) — client asserts surfacing/recoverability only.
- **Not** FEAT-VOICE-002 (server streaming, WS frame ordering, chunk-by-URL) — client consumes it.
- No VAD / open-mic / barge-in on the phone (ADR-ARCH-024 r1).

## Getting started

See [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) for diagrams, waves, and integration contracts.
Run `/feature-build FEAT-VOICE-003`, or start Wave 1: `/task-work TASK-VC-001`, `/task-work TASK-VC-002`.
