# EVIDENCE — Batch A (R01 s2s standup + R02 Pi check) · 2026-07-17

Operator: Fable (delegated by Rich, "can't you execute it?"); Rich on call for
physical/credential steps. Runbook: ../../OPERATOR-BATCH-A-weekend.md.

## R01 — GB10 s2s unit (:8765)

GB10 baseline before standup:   USED 78 / 121 GB   headroom 43 GB (>=12 OK)   keepalive.timer: inactive (since 07-03)
Resident set at start: audio pair (parakeet-tdt-0.6b-v3, qwen3-tts-0.6b, ttl 0) + qwen36-workhorse (fleet)
Tutor-set switch: 1-token completion loaded gemma4-tutor (37.9 s) BUT the fleet re-evicted it
  within seconds — active consumer identified: Rich's dcl-corpus session, ends ~17:30-18:00 BST.
  s2s launch DEFERRED to that window (watcher armed); envelope target 55+~37 = ~92 GB (< ~110 line).
Install order honoured: qwentts cu130 wheel BEFORE speech-to-speech: Y — but the s2s resolve
  REPLACED it with plain PyPI 0.3.1 (new deviation, "Deviation 2b"): wheelhouse now carries
  0.3.1+cu130; re-asserted with --reinstall AFTER s2s. import qwentts_cpp OK.
  -> install-s2s.sh encodes wheel-before-AND-after.
torch: 2.13.0+cu130 (PyPI aarch64; W0-R had 2.12.1 — version drift, cuda.is_available()=True)
speech-to-speech: git 118acb79fb2375a404ef640aa92b29d035b3c5ed (same rev family as W0-R venv)
TTS checkpoint: pending launch (0.6B target; 1.7B fallback pre-approved ASSUM-003)
Ryan flag set server-side: Y (--qwen3_tts_speaker Ryan in launch-s2s.sh); audible-Ryan deferred to R03 app-side MODEL_VOICE (W0-R finding 1)
Unit type: systemd USER unit  name: s2s-realtime.service  (staged, daemon-reloaded, NOT started)
  Digest pin = wheel resolve-URL 0.3.1+cu130 + s2s git rev + torch 2.13.0+cu130, recorded in launch-s2s.sh
Bind: 0.0.0.0:8765 (in unit); ss check pending launch
--model_name: gemma4-tutor (runbook "confirm/pass" — passed explicitly)
VAD: in-process Silero (no version flag exists — recorded as such, matches EVIDENCE inventory)
num_pipelines 2 concurrent check: pending launch
Round-trip rt_probe.py: pending launch
Steady-state memory: pending launch
Unit files/scripts mirrored to dgx-spark: Y — spark-fcf6:~/s2s-mirror/ {install-s2s.sh, launch-s2s.sh, s2s-realtime.service} (via gb10_to_nodeb key)

## R02 — Pi app version + local-mode support

Pi host/IP used: 172.30.1.185 (LAN, from Rich; tailscale reachy-mini=100.75.228.107 also seen)
SSH: pollen@172.30.1.185 — publickey DENIED from GB10; key install one-liner handed to Rich
  (gb10_to_reachy_ed25519.pub) — PENDING. R02 commands queued to run the moment access lands.
reachy_mini_conversation_app Version: pending access
HF_REALTIME keys honoured: pending access
AC-R02-4 (not silently on cloud): pending access
