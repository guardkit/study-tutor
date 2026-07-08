---
id: TASK-VC-003
title: "HttpVoiceApi (MVP HTTP turn) + fidelity direction-pins"
task_type: feature
parent_review: TASK-REV-V3C1
feature_id: FEAT-VOICE-003
wave: 2
implementation_mode: task-work
complexity: 6
dependencies: [TASK-VC-002]
status: pending
tags: [voice, flutter, feat-voice-003, adapter, fidelity]
consumer_context:
  - task: TASK-VC-002
    consumes: VoiceApi
    framework: "Dart abstract interface (implements VoiceApi.voiceTurn)"
    driver: "package:http (MultipartRequest)"
    format_note: "Must satisfy the voice-upload multipart contract: field name 'audio', filename extension matching the captured codec, Content-Type preserving codec params exactly as recorded"
---

# Task: HttpVoiceApi (MVP HTTP turn) + fidelity direction-pins

## Description

Implement the MVP HTTP `voiceTurn` path in `HttpVoiceApi`, reusing the `HttpSessionApi` seams
(base-URL normalization `http_session_api.dart:35-37`, `_headers()` bearer injection, the §9
envelope → sealed-exception mapping `http_session_api.dart:73-147`), extended with the six voice
`error_type`s from TASK-VC-002. **This task carries the "green but broken" fidelity defence**
(design §6.4) — the LPA MockClient direction-pins ported to the Dart seam.

## Acceptance Criteria

- [ ] `app/lib/adapters/http_voice_api.dart` implements `VoiceApi.voiceTurn`, reusing the
      `HttpSessionApi` base-URL + `_headers()` seams (no duplicated auth logic).
- [ ] The tutor envelope's six voice `error_type`s map to the sealed members from TASK-VC-002;
      `VoiceUnavailable` maps to the degradation member.
- [ ] **Direction-pins (MockClient)** assert the outgoing request:
      method + path; `Authorization` bearer present; multipart field name is `audio`; filename
      carries the correct extension; `Content-Type` preserves codec params **intact** (not
      silently re-encoded/stripped). This is the fidelity guarantee.
- [ ] `voiceTurn` returns transcript first (MVP `response` field), then the answer parts.
- [ ] Transport failures surface as the existing connection-problem type (not a voice error),
      preserving retry-as-resend semantics for the UX layer.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

Covers scenario: *A spoken question is delivered to the tutor exactly as recorded* (`@key-example @smoke`).

## Seam Tests

Validates the voice-upload multipart contract at the client boundary (hermetic; the live-seam
port lives in TASK-VC-007).

```dart
// seam test: verify the voiceTurn upload preserves capture format & auth (green-but-broken defence)
// Uses MockClient to capture the outgoing MultipartRequest.
//
// Contract: field 'audio'; filename extension matches captured codec;
//           Content-Type preserves codec params exactly as recorded; bearer present.
// Producer: TASK-VC-003 (this task)   Consumer/validator: TASK-VC-007 (live) + tutor server
test('voiceTurn delivers recording authenticated, on-session, format-intact', () async {
  // arrange: MockClient capturing the request; a known content-type e.g. 'audio/mp4; codecs=mp4a.40.2'
  // act: await api.voiceTurn(sessionId, bytes, contentType: capturedContentType);
  // assert:
  //   expect(captured.fields/files 'audio' present)
  //   expect(captured.files.single.contentType.toString(), capturedContentType); // codec params intact
  //   expect(captured.headers['Authorization'], startsWith('Bearer '));
  //   expect(captured.url.path, contains(sessionId)); // attached to my session
});
```

## Test Requirements

- [ ] Direction-pin tests above (hermetic, MockClient).
- [ ] Envelope→sealed-exception mapping tests for all six voice error types.

## Test Execution Log
