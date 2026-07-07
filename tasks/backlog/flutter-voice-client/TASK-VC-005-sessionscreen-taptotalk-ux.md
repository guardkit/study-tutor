---
id: TASK-VC-005
title: "SessionScreen tap-to-talk UX + VoiceUnavailable degradation"
task_type: feature
parent_review: TASK-REV-V3C1
feature_id: FEAT-VOICE-003
wave: 3
implementation_mode: task-work
complexity: 6
dependencies: [TASK-VC-003, TASK-VC-004]
status: pending
tags: [voice, flutter, feat-voice-003, ui, degradation]
consumer_context:
  - task: TASK-VC-002
    consumes: VoiceApi
    framework: "Flutter StatefulWidget (SessionScreen) + constructor injection"
    driver: "VoiceApi (HttpVoiceApi live / FakeVoiceApi test)"
    format_note: "Consumes VoiceTurnResult; renders transcript first, then answer; maps VoiceUnavailable to amber degradation copy"
---

# Task: SessionScreen tap-to-talk UX + VoiceUnavailable degradation

## Description

Add the mic button to the `SessionScreen` input row (`session_screen.dart:173-199`), guarded by
the existing `_sending`/`_ended` flags, and wire the MVP tap-to-talk loop: press → record (elapsed
indicator) → press → send → transcript-first render → spoken answer. Implement the degradation and
error surfacing exactly per design §6.3. No VAD / open-mic / barge-in (ADR-ARCH-024 r1).

## Acceptance Criteria

- [ ] Mic button joins the input row behind `_sending`/`_ended`; press-to-record, press-to-send with
      an elapsed indicator; **one turn at a time** — pressing mic while a send is in flight does nothing.
- [ ] On send, the transcript enters the session list **first**, exactly like a typed turn, then the
      tutor's spoken answer follows.
- [ ] `VoiceUnavailable` → amber notice with the verbatim copy *"Spoken answers aren't available right
      now — text still works"*; the mic stays **visible but disabled for the rest of the session** until
      a retry succeeds; typed turns are unaffected (ASSUM-003/004).
- [ ] Transport error keeps the existing `showConnectionProblem` treatment — recording preserved,
      retry = resend (ASSUM-008).
- [ ] Recording without microphone permission explains it needs mic access (copy per ASSUM-010) and
      **does not fail** — typing still works.
- [ ] Each refusal error type surfaces a plain-terms message (copy per ASSUM-011 Examples table) and the
      app stays ready to record again immediately.
- [ ] The mic is disabled along with the rest of the input once the session has ended.
- [ ] Typing a question still works exactly as before (regression — nothing about typed tutoring changes).
- [ ] All modified files pass project-configured lint/format checks with zero errors.

Covers scenarios: *Asking a question by voice…*, *My spoken question is shown as text before the answer*,
*Typing a question still works* (`@key-example`/`@regression`); *When spoken answers are unavailable…*,
*A connection problem…preserves my recording*, *The app explains why a recording could not be used…*,
*Recording without microphone permission…* (`@negative`); *The mic does nothing while…*, *The mic is
disabled once the session has ended* (`@edge-case`).

## Test Requirements

- [ ] Widget tests: record→send→transcript→answer states; degradation amber copy; disabled-mic states.
- [ ] Negative widget tests driven by `FlakyVoiceApi`: each refusal message + connection-problem + mic-permission.

## Test Execution Log
