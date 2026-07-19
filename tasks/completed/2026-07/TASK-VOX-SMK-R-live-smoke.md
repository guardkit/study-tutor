---
id: TASK-VOX-SMK-R
title: "Reachy live smoke (AC-R1..R4)"
task_type: operator_handoff
parent_review: TASK-REV-RCH4
feature_id: FEAT-VOICE-004
wave: 5
implementation_mode: task-work
complexity: 6
dependencies: [TASK-VOX-R03, TASK-VOX-R09]
repo: fleet-gateway (Pi + GB10)
status: completed
completed: '2026-07-19T14:05:53.704879Z'
completed_location: tasks/completed/2026-07
updated: '2026-07-19T14:05:53.704879Z'
---

# Reachy live smoke — AC-R1..R4 (build-plan §8)

The downstream gate: an operator-handoff live smoke closing the D3 residency exception.
Written before building; run after R09.

## Acceptance criteria

- **AC-R1**: Open-mic conversation against the local s2s server — **no** HF-cloud Realtime
  session established (connection sampling on Pi and GB10).
- **AC-R2**: `query_student_model` and `ask_tutor` fire through the local session; a tutor
  session started on the phone is **resumed by the robot** (D8 pickup — requires `ask_tutor`
  to send the app's exact subject string).
- **AC-R3**: **No raw audio at rest** on Pi or GB10; transcripts only in the tutor's session
  store (DB `bytea`/blob sweep + disk sweep).
- **AC-R4**: Open-mic latency recorded (simple turn vs `ask_tutor` turn) against design §7.5
  estimates.

## Required operator follow-up

`task_type: operator_handoff` — live cross-device smoke. The operator drives the phone→robot
pickup and the sweeps, records latency, then marks complete. Evidence + a RESULTS file into
`docs/runbooks/evidence/` per house discipline.

- **AC-R1..R4** verified live. Operational guardrails: quiet-GPU rule, never `GET
  :9000/unload`, check the keepalive timer before assuming self-revival.
