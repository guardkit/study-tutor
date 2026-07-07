---
id: TASK-VC-002
title: "VoiceApi sibling port + DTOs + sealed error types"
task_type: declarative
parent_review: TASK-REV-V3C1
feature_id: FEAT-VOICE-003
wave: 1
implementation_mode: direct
complexity: 3
dependencies: []
status: pending
tags: [voice, flutter, feat-voice-003, declarative, ports]
---

# Task: VoiceApi sibling port + DTOs + sealed error types

## Description

Define the new **sibling** `VoiceApi` port (design §6.2), leaving the frozen `SessionApi`
(`app/lib/ports/session_api.dart`) untouched. This is the interface contract every voice
adapter and fake implements, and the type surface the SessionScreen UX consumes.

## Acceptance Criteria

- [ ] `app/lib/ports/voice_api.dart` declares:
      ```dart
      abstract interface class VoiceApi {
        Future<VoiceTurnResult> voiceTurn(String sessionId, Uint8List audio,
            {required String contentType});
        Stream<VoiceTurnEvent> voiceTurnStream(String sessionId, Uint8List audio,
            {required String contentType});
        Future<Uint8List> fetchAudioChunk(String sessionId, String chunkId);
      }
      ```
- [ ] `VoiceTurnResult` (transcript + ordered answer parts) and `VoiceTurnEvent` (transcript
      frame, incremental text token, audio-part-by-`seq`) DTOs defined with immutable fields.
- [ ] Six voice `error_type`s modelled as **sealed** members extending the app's existing
      error hierarchy (`app/lib/domain/errors.dart`): `UnsupportedAudioFormat`, `EmptyRecording`,
      `UnintelligibleQuery`, `QueryTooLong`, `RecordingTooLarge`, and `VoiceUnavailable`
      (the member that drives the amber degradation copy).
- [ ] `SessionApi` and its adapter are unmodified (frozen-contract invariant holds).
- [ ] File compiles; no new runtime dependency imported here beyond `dart:typed_data`.

## Test Requirements

- [ ] Type/exhaustiveness: a `switch` over the sealed voice errors is exhaustive (compile check).

## Implementation Notes

- This is the §4 Integration Contract producer for the internal `VoiceApi` interface consumed by
  TASK-VC-003 / TASK-VC-004 / TASK-VC-006. Keep the DTO field names stable — downstream direction
  pins assert against them.

## Test Execution Log
