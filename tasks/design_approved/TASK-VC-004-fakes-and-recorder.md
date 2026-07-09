---
complexity: 5
consumer_context:
- consumes: VoiceApi
  driver: in-memory fake
  format_note: Fakes return canned transcript + tiny silent-wav bytes; FlakyVoiceApi
    decorator mirrors FlakySessionApi failure injection
  framework: Dart abstract interface (FakeVoiceApi/FlakyVoiceApi implement VoiceApi)
  task: TASK-VC-002
dependencies:
- TASK-VC-001
- TASK-VC-002
feature_id: FEAT-VOICE-003
id: TASK-VC-004
implementation_mode: task-work
parent_review: TASK-REV-V3C1
status: design_approved
tags:
- voice
- flutter
- feat-voice-003
- fakes
- recorder
task_type: feature
title: FakeVoiceApi/FlakyVoiceApi + recorder with 60s/10MB client stop
wave: 2
---

# Task: FakeVoiceApi/FlakyVoiceApi + recorder with 60s/10MB client stop

## Description

Provide the hermetic backend (`FakeVoiceApi` + `FlakyVoiceApi` decorator, mirroring the existing
`FlakySessionApi` pattern in `app/lib/fakes/`) and the recorder wrapper around `record`, with the
**client-side 60 s hard stop** (the real enforcement — streamed containers omit duration headers)
and the 10 MB byte backstop (design §6.1/§6.3).

## Acceptance Criteria

- [ ] `app/lib/fakes/fake_voice_api.dart` implements `VoiceApi`: canned transcript + tiny silent-wav
      bytes for `voiceTurn`/`voiceTurnStream`/`fetchAudioChunk`.
- [ ] `FlakyVoiceApi` decorator injects failure paths (transport error, `VoiceUnavailable`, each of
      the six refusal error types) mirroring `FlakySessionApi`.
- [ ] Recorder wrapper starts/stops recording via `record`; **stops automatically at 60 s** so a
      recording can never exceed the limit; enforces a 10 MB backstop.
- [ ] Encoder is m4a/AAC by default with opus fallback, selected **behind the Phase-0 gate**
      (ASSUM-006, blueprint §6/§8): the fidelity guarantee (format preserved exactly as captured)
      holds regardless of which encoder wins — do **not** hard-code an assumption the gate hasn't settled.
- [ ] Cancel-before-send discards the recording and starts no turn; an interruption (incoming call /
      backgrounding) abandons the recording cleanly and allows a fresh start.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

Covers scenarios: *A recording shorter than the time limit is sent when I stop it*, *Recording stops
automatically at the 60-second limit* (`@boundary`); *A recording cancelled before sending starts no turn*,
*A recording interrupted by a call or backgrounding is abandoned cleanly* (`@edge-case`).

## Test Requirements

- [ ] 59 s sends / 60 s auto-stops boundary tests.
- [ ] Cancel and interruption paths leave no half-sent turn.
- [ ] FlakyVoiceApi drives each failure type for the UX task to consume.

## Implementation Notes

- Keep the encoder choice injectable so the Phase-0 m4a-against-live-STT result can flip the default
  without touching the fidelity assertions.

## Test Execution Log