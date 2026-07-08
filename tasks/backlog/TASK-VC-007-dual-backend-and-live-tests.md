---
id: TASK-VC-007
title: "Dual-backend contract tests + live voice variants"
task_type: testing
parent_review: TASK-REV-V3C1
feature_id: FEAT-VOICE-003
wave: 5
implementation_mode: task-work
complexity: 5
dependencies: [TASK-VC-003, TASK-VC-005, TASK-VC-006]
status: pending
tags: [voice, flutter, feat-voice-003, testing, live]
consumer_context:
  - task: TASK-VC-003
    consumes: VOICE_UPLOAD_MULTIPART
    framework: "Dart live test (LiveContractBackend, app/test_live/)"
    driver: "package:http against the live tutor on the GB10"
    format_note: "Live-seam port of the direction pins: field 'audio', filename extension matches captured codec, Content-Type preserves codec params exactly; authenticated + on-session"
---

# Task: Dual-backend contract tests + live voice variants

## Description

Run the voice scenarios through **both** backends per design §6.4: hermetic (`FakeVoiceApi`/
`FlakyVoiceApi` + MockClient direction pins) and live (`app/test_live/` voice variants alongside the
streaming variants, `LiveContractBackend`). Ports the "green but broken" direction-pins to the live
Dart seam under the existing live-suite discipline.

## Acceptance Criteria

- [ ] Contract-style test bodies run against the dual-backend harness (`ContractBackend` → fake + live),
      following the existing `app/test/contract/` pattern.
- [ ] Voice live variants added under `app/test_live/`, run with `--concurrency=1` (binding global-reset
      note), quiet GPU, honouring the 60 s turn-deadline precedent.
- [ ] The upload direction-pins (field `audio`, filename, Content-Type codec params intact, bearer,
      on-session) are asserted at the **live** seam, not only hermetically.
- [ ] Live variants are opt-in / skip cleanly when the live tutor is unavailable (no false failures in
      CI without the GB10).

## Seam Tests

Live-seam port of the voice-upload multipart contract (producer: TASK-VC-003).

```dart
// live seam test: the recording reaches the live tutor exactly as captured, as me, on my session.
// Contract: multipart field 'audio'; filename extension matches captured codec;
//           Content-Type preserves codec params exactly; Authorization bearer present.
// Runs under LiveContractBackend, --concurrency=1, quiet GPU.
test('live voiceTurn preserves capture format, auth, and session binding', () async {
  // arrange: LiveContractBackend against the GB10 tutor; a captured recording + its exact content-type
  // act: final result = await liveVoiceApi.voiceTurn(sessionId, bytes, contentType: capturedContentType);
  // assert: transcript returned; turn attached to sessionId; server did not reject on format
  //         (fidelity preserved end-to-end — the green-but-broken defence at the live seam)
}, skip: liveTutorUnavailable);
```

## Test Requirements

- [ ] Hermetic + live parity for the key-example and negative scenarios.
- [ ] Direction-pin live assertion (above).

## Test Execution Log
