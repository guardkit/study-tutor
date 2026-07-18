# RUNBOOK — Standing up a (second) Reachy Mini on the local voice stack

**Written 2026-07-18** from the live Batch B execution (AC-R09-4). Replays the FULL
proven sequence for a fresh robot, with every landmine hit on robot #1 marked ⚠.
Evidence trail: `evidence/voice-r01-r02-batchA-2026-07-17/` + `evidence/voice-r03-r09-smkr-batchB-2026-07-18/`.
Prereqs: GB10 s2s unit standing (`RUNBOOK` §A below), robot on LAN/tailnet, its IP known
(Reachy Mini Control app → settings).

## A. GB10 side (once, already done for robot #1)
1. s2s venv + unit: `~/s2s/install-s2s.sh` (pins inside; **order load-bearing**: cu130
   qwentts wheel BEFORE speech-to-speech, re-assert AFTER; huggingface-hub <1.0).
   ⚠ The venv install alone is NOT enough — the local patch set
   `~/s2s/patches/0001-local-toolcall-fixes.patch` must be applied over site-packages
   (12 observed tool-call dialects, template teaching, function-item textification —
   see the Batch B evidence §saga). Verify: `grep -c "R-G3" .../base_openai_compatible_language_model.py` > 0.
2. GPU posture: tutor set resident (1-token completion to `gemma4-tutor`; NEVER
   `GET :9000/unload`). Envelope: tutor set + s2s ≈ 67-92 GB of 121; coordinate with
   fleet/dcl consumers of `qwen36-workhorse` (they evict the tutor set).
3. `systemctl --user start s2s-realtime` → wait for
   `Realtime API starting on ws://0.0.0.0:8765/v1/realtime`; `ss -ltn | grep 8765`.

## B. Pi access (per robot)
1. `ssh pollen@<ROBOT_IP>`, factory password (fleet-gateway deploy runbook Phase 1) —
   **change it after standup**. Install your automation key:
   `ssh pollen@<IP> 'mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys' <<< "<pubkey>"`.

## C. Code plane (per robot) — clean clone, never git pull
```bash
[ -d /home/pollen/fleet-gateway ] && mv /home/pollen/fleet-gateway /home/pollen/fleet-gateway.bak-$(date +%F)
git clone https://github.com/guardkit/fleet-gateway.git /home/pollen/fleet-gateway
# Re-apply the NATS hand-edit by transplanting from the backup (creds stay on-Pi):
OLD=$(grep '^_DEFAULT_NATS_URL' /home/pollen/fleet-gateway.bak-*/reachy/external_content/external_tools/ask_jarvis.py | tail -1)
python3 - "$OLD" <<'PY'
import sys, re, pathlib
p = pathlib.Path('/home/pollen/fleet-gateway/reachy/external_content/external_tools/ask_jarvis.py')
p.write_text(re.sub(r'^_DEFAULT_NATS_URL.*$', sys.argv[1], p.read_text(), count=1, flags=re.M))
PY
# (First robot ever: take the line from deploy runbook Phase 7 + the NATS password.)
echo "/home/pollen/fleet-gateway" > /venvs/apps_venv/lib/python3.12/site-packages/fleet-gateway.pth
source /venvs/apps_venv/bin/activate && pip install httpx
```
Gate: `python -c "from common.tutor_client import TutorClient; print('OK')"` and a
file-path load of `ask_tutor.py` (see Batch B evidence for the snippet).

## D. Config plane (per robot) — the landmine field
1. ⚠ **`/home/pollen/.env`**: if present, it OVERRIDES all env whenever a process's
   cwd-upward search finds it. Delete any `REACHY_MINI_EXTERNAL_*` lines (robot #1 had
   Mac paths here — worked-sometimes breakage). Keep `REACHY_MINI_CUSTOM_PROFILE=scholar`.
2. ⚠ **`/etc/environment`**: `REACHY_MINI_EXTERNAL_PROFILES_DIRECTORY` must NOT be set
   (AC-R03-1). `REACHY_MINI_EXTERNAL_TOOLS_DIRECTORY` -> the clone's external_tools stays.
3. **sitecustomize** `/venvs/apps_venv/lib/python3.12/site-packages/sitecustomize.py`
   (the daemon passes no env; this is the channel):
```python
import os
os.environ.setdefault("REACHY_MINI_EXTERNAL_TOOLS_DIRECTORY", "/home/pollen/fleet-gateway/reachy/external_content/external_tools")
os.environ.setdefault("NATS_URL", "nats://rich:<NATS_PASSWORD>@promaxgb10-41b1:4222")
os.environ.setdefault("HF_REALTIME_CONNECTION_MODE", "local")
os.environ.setdefault("HF_REALTIME_WS_URL", "ws://promaxgb10-41b1:8765/v1/realtime")
os.environ.setdefault("STUDY_TUTOR_HTTP_URL", "http://promaxgb10-41b1:8100")
os.environ.setdefault("STUDY_TUTOR_TOKEN", "<token from the :8100 deploy's STUDY_TUTOR_HTTP_TOKENS>")
os.environ.setdefault("MODEL_VOICE", "Ryan")  # legacy pin, harmless
```
4. **Scholar profile into Personality Studio** (external profiles dir is fenced off):
```bash
PS=/venvs/apps_venv/lib/python3.12/site-packages/reachy_talk_data/profiles/user_personalities/scholar
mkdir -p $PS
cp /home/pollen/fleet-gateway/reachy/external_content/external_profiles/scholar/{instructions.txt,tools.txt} $PS/
```
5. ⚠ **THE voice pin** (0.6.1: beats every other channel):
   `/venvs/apps_venv/lib/python3.12/site-packages/reachy_mini_conversation_app/startup_settings.json`
   → `{"profile": "user_personalities/scholar", "voice": "Ryan"}`.

## E. Bring-up + verify (per robot)
```bash
sudo reboot   # clean env pickup
# after boot (daemon API on :8000):
curl -X POST "http://localhost:8000/api/daemon/start?wake_up=true"   # if body asleep
curl -X POST  http://localhost:8000/api/apps/start-app/reachy_mini_conversation_app
curl -X POST  http://localhost:8000/api/volume/set -H 'Content-Type: application/json' -d '{"volume": 90}'
```
Verify (GB10): `ss -tn | grep 8765` shows ESTAB from the robot; s2s journal shows
`connection open`. Verify (Pi journal): `Realtime session initialized with
profile='user_personalities/scholar' voice='Ryan'` and `Tools to be used ...
['ask_jarvis','ask_tutor','query_student_model',...]` (emotion ABSENT).
Live: say "Ask the tutor, what is a metaphor?" → expect think-line, pause (tutor turns
run 25-80 s on the spark topology), spoken Socratic answer. Check
`docker logs study_tutor_http` for the session start/turn as the robot's token student.

## F. Known behaviours / recovery (from the live smoke)
- "Back to connection" in the phone app = daemon backend STOP; recover with
  `POST /api/daemon/start?wake_up=true` + app restart. Volume often resets on reboot.
- Model quirks (gemma4-tutor): erratic tool CHOICE (use explicit "ask the tutor ..."
  phrasing); reasoning-channel leak (<|channel>thought) may occasionally be spoken;
  Qwen3-TTS-0.6B sometimes babbles to its 28.7 s frame cap (1.7B fallback pre-approved).
- Every robot shares the student token → shares sessions. Per-child robots need
  FEAT-AUTH-004 device pairing (out of scope this weekend).
