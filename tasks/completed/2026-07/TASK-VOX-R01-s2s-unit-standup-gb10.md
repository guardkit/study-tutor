---
id: TASK-VOX-R01
title: "Stand up the local speech-to-speech unit on GB10 :8765"
task_type: operator_handoff
parent_review: TASK-REV-RCH4
feature_id: FEAT-VOICE-004
wave: 1
implementation_mode: task-work
complexity: 8
dependencies: []
repo: fleet-gateway/dgx-spark (GB10 host)
status: completed
completed: '2026-07-19T14:05:53.704879Z'
completed_location: tasks/completed/2026-07
updated: '2026-07-19T14:05:53.704879Z'
---

# Stand up the local speech-to-speech unit on GB10 :8765

Productionize the W0-R-verified s2s configuration into a durable unit — the greenfield
GB10 component that replaces the HF-cloud Realtime session (design §7.2). Consumes the
W0-R EVIDENCE pins verbatim.

## Acceptance criteria

- **AC-R01-1**: The HF `speech-to-speech` unit runs on the GB10 exposing an
  OpenAI-Realtime-compatible WS at `ws://promaxgb10-41b1:8765/v1/realtime`, bound
  **non-loopback** so the Pi can reach it.
- **AC-R01-2**: Stages are Silero-VAD-v5 → `--stt parakeet-tdt` → `--tts qwen3` with the
  `Qwen3-TTS-…-0.6B-CustomVoice` pin (R-G2), and `--llm_backend responses-api
  --responses_api_base_url http://127.0.0.1:9000/v1` (llama-swap). **If the 0.6B checkpoint
  fails to load under the s2s qwen3 backend, fall back to 1.7B on the robot path and keep
  going — pre-approved, no need to stop (ASSUM-003, standing green light 2026-07-07).**
- **AC-R01-3**: The **Ryan** voice flag is located and set **server-side**; the robot
  speaks in Ryan.
- **AC-R01-4**: aarch64/CUDA-13 install order honoured — `qwentts-cpp-python==0.3.0+cu130`
  from the cu130 wheelhouse installed **before** `speech-to-speech`.
- **AC-R01-5**: Memory arithmetic re-verified against **live** steady state before standup
  (TTS CUDA context fails at ~110 GB used — measured, not assumed).
- **AC-R01-6**: Runs as a digest-pinned systemd/docker unit **outside** llama-swap; the
  R-G5 resident-set posture (tutor set standing default, `gemma4-tutor` ttl raised) is in
  effect; unit files + install/launch scripts mirrored to `dgx-spark`.

## Required operator follow-up

This task is `task_type: operator_handoff` — AutoBuild will not attempt it. The operator
verifies the runtime ACs above on the GB10, then marks the task complete via
`/task-complete`. Evidence into `docs/runbooks/evidence/`.

## Notes

- Consumes the W0-R evidence pins (resolve-URL wheel, numba floors, `OPENAI_API_KEY`,
  `--num_pipelines 2`, tool-call-speech fixes, user-mode `systemctl --user restart
  llama-swap`).
- The 0.6B → 1.7B fallback is **pre-approved** (ASSUM-003, owner 2026-07-07): if R-G2 fails,
  the operator accepts 1.7B on the robot path and proceeds — no mid-standup consult needed.
  Voice consistency trade knowingly accepted (1.7B on robot vs 0.6B on phone/app).
