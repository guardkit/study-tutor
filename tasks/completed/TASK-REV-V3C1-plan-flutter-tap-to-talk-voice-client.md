---
id: TASK-REV-V3C1
title: "Plan: Flutter tap-to-talk voice client"
status: review_complete
created: 2026-07-07T00:00:00Z
updated: 2026-07-07T00:00:00Z
priority: high
task_type: review
tags: [voice, flutter, feat-voice-003, planning]
complexity: 0
review_results:
  mode: decision
  depth: standard
  decision: implement
  feature_id: FEAT-VOICE-003
  report_path: .claude/reviews/TASK-REV-V3C1-review-report.md
clarification:
  context_a:
    decisions:
      focus: all
      tradeoff: quality
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Plan: Flutter tap-to-talk voice client

## Description

Decision-mode planning review for FEAT-VOICE-003 — the study-tutor Flutter
app's tap-to-talk voice client (`app/`). Client-only scope: record a spoken
question (60 s client hard stop, 10 MB backstop), transcript-first display,
ordered playback of the answer's spoken parts, incremental text on the
streaming (WS) path, the amber `VoiceUnavailable` degradation experience,
mic-permission and connection-problem handling, and the "green-but-broken"
direction-pin fidelity of the outgoing recording. Introduces three new runtime
deps (`record`, `just_audio`, `web_socket_channel`) + Android/iOS manifest
permission additions.

Does **not** duplicate FEAT-VOICE-001 (server upload-validation rulebook) or
FEAT-VOICE-002 (server streaming path / WS frame ordering / chunk-by-URL).

## Context sources

- `features/flutter-voice-client/flutter-voice-client_summary.md` (spec summary)
- `features/flutter-voice-client/flutter-voice-client.feature` (22 scenarios)
- `features/flutter-voice-client/flutter-voice-client_assumptions.yaml` (11 assumptions)
- `docs/design/voice-tutor-and-reachy-design.md` §6 (Flutter client design)
- `app/lib/` (existing ports & adapters: `SessionApi`, `HttpSessionApi`, `SessionScreen`)

## Review objective

Analyse the technical approach, architecture, testing strategy, and risk, then
produce an implementation task breakdown optimised for **quality/reliability**.

## Test Requirements

- N/A (review task — no code)

## Test Execution Log
