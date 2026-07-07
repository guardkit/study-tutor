---
id: TASK-VOX-R09
title: "Ship to the Pi via clean re-clone (not git pull)"
task_type: operator_handoff
parent_review: TASK-REV-RCH4
feature_id: FEAT-VOICE-004
wave: 4
implementation_mode: task-work
complexity: 5
dependencies: [TASK-VOX-R05, TASK-VOX-R07, TASK-VOX-R08]
repo: fleet-gateway (on-Pi)
---

# Ship to the Pi via clean re-clone, not git pull (recon D7)

The Pi clone is hand-edited (hardcoded NATS creds in `ask_jarvis.py`), so `git pull` will
conflict when shipping `ask_tutor` + the reconciled profile. Deploy via a clean re-clone and
re-apply the hand-config.

## Acceptance criteria

- **AC-R09-1**: The new tutor tool (`ask_tutor`, R07), the Postgres-backed
  `query_student_model` (R05), and the reconciled Scholar profile (R08) are shipped to the
  Pi via a **clean re-clone**, not an in-place `git pull`.
- **AC-R09-2**: The `sitecustomize.py` env injection (R03) and the hardcoded NATS creds are
  re-applied after the re-clone; the robot's hand-applied local settings are still in
  effect.
- **AC-R09-3**: The deployment did **not** rely on merging over the hand-edited files.
- **AC-R09-4**: The procedure is runbooked for repeatability (second robot / future ships).

## Required operator follow-up

`task_type: operator_handoff` — on-Pi deployment. The operator performs the clean re-clone,
re-applies config, and confirms the hand-settings survive, then marks complete.

- **AC-R09-1..4** verified on the Pi; procedure captured in the runbook.
