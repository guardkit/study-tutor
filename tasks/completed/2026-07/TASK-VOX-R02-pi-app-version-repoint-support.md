---
id: TASK-VOX-R02
title: "Verify the Pi app supports the re-point keys; upgrade if not"
task_type: operator_handoff
parent_review: TASK-REV-RCH4
feature_id: FEAT-VOICE-004
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
repo: fleet-gateway (on-Pi)
status: completed
completed: '2026-07-19T14:05:53.704879Z'
completed_location: tasks/completed/2026-07
updated: '2026-07-19T14:05:53.704879Z'
---

# Verify the Pi app supports the re-point keys; upgrade if not (recon D3)

The `HF_REALTIME_CONNECTION_MODE` / `HF_REALTIME_WS_URL` re-point keys were verified
against **upstream** docs, not the version installed on the Pi (~2026-05-20). Close that
gap before R03 relies on them.

## Acceptance criteria

- **AC-R02-1**: The installed `reachy_mini_conversation_app` version on the Pi is read and
  recorded.
- **AC-R02-2**: Confirm that version honours `HF_REALTIME_CONNECTION_MODE=local` and
  `HF_REALTIME_WS_URL`. If it does, no upgrade — record the evidence.
- **AC-R02-3**: If it does **not**, an app upgrade is planned and executed, **with a
  Personality-Studio profile-survival check** (the Scholar profile must survive the
  upgrade).
- **AC-R02-4**: The robot does not silently keep using the cloud — the migration is
  explicitly blocked until the re-point keys are supported.

## Required operator follow-up

`task_type: operator_handoff` — AutoBuild will not attempt it. The operator reads the Pi's
installed version, confirms/upgrades, and verifies profile survival, then marks complete.

- **AC-R02-1..4** verified on the Pi; evidence recorded.
