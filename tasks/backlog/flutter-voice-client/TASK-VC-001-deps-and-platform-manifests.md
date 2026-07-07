---
id: TASK-VC-001
title: "Scope event: voice runtime deps + Android/iOS manifests"
task_type: scaffolding
parent_review: TASK-REV-V3C1
feature_id: FEAT-VOICE-003
wave: 1
implementation_mode: direct
complexity: 3
dependencies: []
status: pending
tags: [voice, flutter, feat-voice-003, scaffolding]
---

# Task: Scope event — voice runtime deps + Android/iOS manifests

## Description

Record the deliberate dependency-posture amendment (design §6.1, ASSUM-005) and add the
platform permissions the shipped app needs to record and reach the tutor. Today's **release**
build has no network permission at all — this task closes that gap.

## Acceptance Criteria

- [ ] `record`, `just_audio`, `web_socket_channel` added to `app/pubspec.yaml` with exact
      versions pinned in `app/pubspec.lock`; **no** state-management package is added.
- [ ] Android **main** manifest gains `INTERNET` (currently debug/profile-only) and `RECORD_AUDIO`.
- [ ] iOS `Info.plist` gains `NSMicrophoneUsageDescription` with a user-facing string.
- [ ] NSC extension added as documented posture hygiene only; `usesCleartextTraffic` is **not**
      blanket-enabled (per §6.1 WS/dart:io note — Dart-side fail-closed cleartext control is the
      real enforcement, tracked in `app/QUESTIONS.md`).
- [ ] The dependency amendment is recorded as a conscious scope event (comment/PROGRESS note),
      correcting the stale phase-1 "zero added deps" wording.
- [ ] `flutter pub get` resolves cleanly; existing `app/test/` suite still passes.

Covers scenario: *The shipped app is able to record audio and reach the tutor* (`@edge-case @regression`).

## Test Requirements

- [ ] Manifest-presence check (release build declares INTERNET + RECORD_AUDIO; iOS declares mic usage).

## Implementation Notes

- Encoder package choice (m4a/AAC vs opus) is settled in TASK-VC-004 behind the Phase-0 gate;
  this task only pins the `record` dependency.

## Test Execution Log
