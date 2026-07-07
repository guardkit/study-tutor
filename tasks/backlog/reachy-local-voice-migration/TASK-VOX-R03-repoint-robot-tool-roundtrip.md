---
id: TASK-VOX-R03
title: "Re-point the robot to local s2s and verify tool round-trip"
task_type: operator_handoff
parent_review: TASK-REV-RCH4
feature_id: FEAT-VOICE-004
wave: 2
implementation_mode: task-work
complexity: 6
dependencies: [TASK-VOX-R01, TASK-VOX-R02]
repo: fleet-gateway (on-Pi)
---

# Re-point the robot to local s2s and verify tool round-trip (R-G3)

Point the robot at the local s2s unit and prove — the highest-risk unknown — that tool
calls round-trip through the local Realtime session end-to-end.

## Acceptance criteria

- **AC-R03-1**: `HF_REALTIME_CONNECTION_MODE=local` and
  `HF_REALTIME_WS_URL=ws://promaxgb10-41b1:8765/v1/realtime` are injected via
  `/venvs/apps_venv/.../sitecustomize.py` `os.environ.setdefault(...)` (the daemon passes
  no env). `REACHY_MINI_EXTERNAL_PROFILES_DIRECTORY` is **never** set on the Pi.
- **AC-R03-2**: An open-mic conversation runs entirely against the local s2s unit — **no**
  HF-cloud Realtime session is established (connection sampling on Pi + GB10).
- **AC-R03-3**: A scripted session triggers `query_student_model`; the tool fires through
  the local session and the result is **narrated** by the robot (R-G3 proof).
- **AC-R03-4**: Tool-call control text is **not** spoken aloud (the W0-R defect is fixed:
  template tool-call support + TTS strip filter).

## Required operator follow-up

`task_type: operator_handoff` — live on-Pi session. The operator drives the scripted
conversation and observes the tool round-trip + no-cloud + no-spoken-control-text, then
marks complete.

- **AC-R03-1..4** verified live; connection sampling + transcript captured as evidence.
