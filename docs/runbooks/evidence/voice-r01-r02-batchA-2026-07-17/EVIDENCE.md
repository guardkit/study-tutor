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

## R02 — Pi app version + local-mode support — **PASS 2026-07-17 ~17:05 BST**

Pi host/IP used: 172.30.1.185 (LAN, from Rich; hostname reachy-mini)
SSH: key auth established — gb10_to_reachy_ed25519 installed by Fable via one-shot
  password auth (factory default per fleet-gateway runbook:31, confirmed unchanged by Rich).
  SECURITY FOLLOW-UP for Rich: change the Pi password post-weekend (runbook's own step).
reachy_mini_conversation_app  Version: 0.6.1   Location: /venvs/apps_venv/.../site-packages
HF_REALTIME keys honoured: **YES — both.** config.py:360-365 reads
  HF_REALTIME_CONNECTION_MODE + HF_REALTIME_WS_URL from env;
  huggingface_realtime.py:125 enforces WS_URL when mode=local; console.py:268-269
  can persist local mode. HF_REALTIME_SESSION_URL deliberately env-ignored (config.py:363).
Upgrade needed: NO (AC-R02-2 met; AC-R02-3 moot; Scholar-profile-survival check not required)
AC-R02-4 (not silently on cloud): UNBLOCKED — migration fence lifts; actual re-point is R03.

### R03-prep findings (read-only, for Batch B)
- sitecustomize.py present at /venvs/apps_venv/.../site-packages/: sets
  REACHY_MINI_EXTERNAL_TOOLS_DIRECTORY -> /home/pollen/fleet-gateway/... + 1 NATS_URL line
  (value not recorded). No HF_REALTIME values persisted anywhere yet.
- **FENCE DEVIATION (pre-existing):** /etc/environment:2-3 sets BOTH
  REACHY_MINI_EXTERNAL_TOOLS_DIRECTORY **and REACHY_MINI_EXTERNAL_PROFILES_DIRECTORY** —
  R03's fence says PROFILES_DIRECTORY must never be set. Left untouched (interacts with
  Scholar profile loading); reconcile inside the R03/R09 procedure per the task .md.
