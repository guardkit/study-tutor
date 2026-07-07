---
id: TASK-VC-006
title: "Streaming voiceTurnStream + seq-ordered playback + incremental text"
task_type: feature
parent_review: TASK-REV-V3C1
feature_id: FEAT-VOICE-003
wave: 4
implementation_mode: task-work
complexity: 7
dependencies: [TASK-VC-005]
status: pending
tags: [voice, flutter, feat-voice-003, streaming, playback]
consumer_context:
  - task: TASK-VC-002
    consumes: VoiceApi
    framework: "Dart Stream (implements VoiceApi.voiceTurnStream) + just_audio ordered queue"
    driver: "web_socket_channel (WS) / just_audio"
    format_note: "Consumes VoiceTurnEvent stream; playback queue keyed by seq; text tokens render ahead of audio; per-part fetchAudioChunk authenticated as the signed-in principal"
---

# Task: Streaming voiceTurnStream + seq-ordered playback + incremental text

## Description

Implement the live-channel (WS) path: `voiceTurnStream` over `web_socket_channel`, `just_audio`
ordered playback queue keyed by `seq`, incremental text render running **ahead** of audio, and the
ephemeral-part invariants. Layers on top of the MVP UX from TASK-VC-005 without reworking the port.
Depends on FEAT-VOICE-002 server streaming for live delivery (cross-feature seam — see guide §4).

## Acceptance Criteria

- [ ] `HttpVoiceApi.voiceTurnStream` (WS) yields `VoiceTurnEvent`s; frame-1 transcript renders first.
- [ ] Answer text appears bit by bit as it is composed and **runs ahead** of the spoken audio.
- [ ] `just_audio` plays a `seq`-ordered queue: multi-part answers play in produced order with no gaps
      or out-of-order parts; a single-part answer plays as one continuous answer.
- [ ] An announced part that is **no longer available** at play time (TTL ≤120 s, binding §4.2) is
      **skipped** and the remaining parts continue.
- [ ] If spoken audio stops being produced partway, the **full written answer is still shown**, no
      further parts play past the stop point, and the turn is recorded normally.
- [ ] Each spoken part is fetched via `fetchAudioChunk` **authenticated as me** — a part is never
      retrieved without the signed-in principal's credentials.
- [ ] Sending a recording after the session was ended elsewhere is refused (session ended) and the mic
      is disabled with the rest of the input.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

Covers scenarios: *A spoken answer's text appears while it is still being composed…* (`@key-example @smoke`);
*A spoken answer delivered in several parts plays back in order*, *A short answer delivered as a single
spoken part…* (`@key-example`/`@boundary`); *A spoken part that is no longer available is skipped…*,
*Spoken audio stops partway…*, *The app fetches each spoken part authenticated as me*, *Sending a recording
after the session was ended elsewhere is refused* (`@edge-case`/`@negative`).

## Test Requirements

- [ ] Ordering test: out-of-arrival-order `seq` frames still play in produced order.
- [ ] Skip-expired-part and stop-partway tests; per-part auth-header assertion.
- [ ] Text-ahead-of-audio incremental render test.

## Implementation Notes

- WS rides dart:io's `WebSocket` (pure Dart) — it bypasses the Android NSC exactly like `package:http`;
  keep fail-closed cleartext control Dart-side (design §6.1, `app/QUESTIONS.md`).

## Test Execution Log
