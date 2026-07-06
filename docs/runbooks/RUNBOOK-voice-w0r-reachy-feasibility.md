# RUNBOOK — W0-R: Reachy local-voice feasibility gates (operator, on the GB10)

**Gate:** [voice scope & build plan §5 W0-R](../research/ideas/voice-tutor-and-reachy-scope-and-build-plan.md) · design: [voice-tutor-and-reachy-design.md §7](../design/voice-tutor-and-reachy-design.md)
**Date authored:** 2026-07-06 · **Operator:** Rich, on `promaxgb10-41b1` (no dev-box SSH — that's why this is a runbook)
**Purpose:** prove (or price the fallbacks for) the HF `speech-to-speech` stack on the GB10 **with a throwaway foreground instance** — R1 later productionizes whatever passes. Nothing here touches the robots, llama-swap's config (except Phase 6), or the deployed HF-cloud sessions.
**Fleet fact this covers:** **two Reachy Minis** (Scholar + Bridge profiles) will re-point to this server → R-G6 concurrency gate.
**Evidence:** paste command outputs + timings into `docs/runbooks/evidence/voice-w0r-reachy-feasibility-<date>/EVIDENCE.md` (mirror the [W0-T file](evidence/voice-w0-preflight-2026-07-05/EVIDENCE.md)).

---

## Phase 0 — Preconditions (quiet GPU + baseline)

```bash
# No tutor/LPA/extraction sessions mid-flight; robots can stay on (they're on HF cloud today).
systemctl status llama-swap-keepalive.timer --no-pager | head -3   # expect inactive (since 2026-07-03)
curl -s http://localhost:9000/running | python3 -m json.tool | grep -E 'model|state'
free -g && nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

**Record:** the running set + used/total memory as the baseline.
**Gate P0:** baseline used memory leaves **≥ 12 GB headroom** before Phase 1 (TTS CUDA context creation fails outright near ~110 GB used — the audio-qwen3tts.sh trap). If not: stop, free a family, re-measure.

## Phase 1 — R-G1: throwaway s2s install + start (aarch64 / CUDA 13)

Fresh venv, **cu130 TTS runtime wheel first** (default PyPI wheel targets cu128 and will break):

```bash
mkdir -p ~/s2s-w0r && cd ~/s2s-w0r
uv venv --python 3.12 && source .venv/bin/activate
pip install "qwentts-cpp-python==0.3.0+cu130" \
  -f https://huggingface.co/datasets/andito/qwentts-cpp-python-wheels/tree/main/whl/cu130
pip install speech-to-speech      # or: pip install git+https://github.com/huggingface/speech-to-speech
```

Note: this venv needs one-time HF downloads (Silero VAD, `nvidia/parakeet-tdt-0.6b-v3`, the Qwen3-TTS checkpoint). That is fine for a *feasibility* venv — the D3 no-cloud rule binds the **audio path at runtime**, and R1's productionized unit will pin/pre-fetch. Do not set `HF_HUB_OFFLINE=1` here.

Start foreground, loopback, LLM stage at llama-swap:

```bash
speech-to-speech --mode realtime \
  --stt parakeet-tdt \
  --tts qwen3 --qwen3_tts_model_name Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice \
  --llm_backend responses-api \
  --model_name gemma4-tutor \
  --responses_api_base_url "http://127.0.0.1:9000/v1"
```

**Gate R-G1 (PASS =):** server starts clean and listens at `ws://127.0.0.1:8765/v1/realtime`; record install time, any wheel/CUDA errors verbatim, and startup memory delta (`nvidia-smi` again).
**FAIL path:** capture the error; the recorded fallback decision is bare-metal vs patching the repo's `Dockerfile.arm64` (CUDA 12.8 base vs the GB10's CUDA 13 host — unverified compatibility).

## Phase 2 — R-G2: the 0.6B TTS checkpoint actually synthesizes

The pipeline's documented default is the **1.7B** checkpoint; our fleet pin is **0.6B** — this gate is the proof either way. With the Phase-1 server running, open a Realtime session (Phase 3's client works) or run the pipeline's local mode for a one-shot:

```bash
# Simplest: keep the Phase-1 flags but --mode local, speak a sentence into the mic-less test path
# (if local mode needs audio devices, do R-G2 through the Phase-3 client instead and just LISTEN)
```

**Gate R-G2 (PASS =):** an audible, intelligible spoken reply is produced by the **0.6B** checkpoint (`ggml` backend; retry `--qwen3_tts_backend torch` if ggml rejects it). Also locate and record the **voice-selection flag** and set it to `Ryan` (fleet pin) — record the exact flag name for R1.
**FAIL path (owner decision, pre-made):** if 0.6B won't load under either backend, run the robot path on **1.7B** and record the pin deviation in the evidence + plan §0 (robot-path-only deviation; the shared `:9000` endpoints stay on 0.6B).

## Phase 3 — R-G3: tool calls round-trip through local s2s

Highest-fidelity client without touching a robot: the **MacBook's `reachy_mini_conversation_app` clone** in local mode (robot not required — it runs with local mic/speaker):

```bash
# On the GB10: restart Phase-1 server bound non-loopback:  --host 0.0.0.0  (record the actual flag)
# On the MacBook, in the conversation-app clone's .env:
#   HF_REALTIME_CONNECTION_MODE=local
#   HF_REALTIME_WS_URL=ws://promaxgb10-41b1:8765/v1/realtime
#   REACHY_MINI_CUSTOM_PROFILE=scholar   (+ external tools/profile dirs as in fleet-gateway/reachy/README)
# Ask: "what do you know about Lilymay's studies?"  → must trigger query_student_model
```

**Gate R-G3 (PASS =):** the session runs against the local server (verify no HF-cloud websocket: `ss -tnp | grep -i python` on the Mac shows only the GB10 connection), the tool **fires**, and its result is **narrated back**. Record end-to-end latency of one simple turn and one tool turn.
**FAIL path:** if the s2s Realtime implementation doesn't forward tool calls, the Reachy track is blocked pending an s2s patch/issue — record precisely what frame the flow died on (this is the single highest-risk unknown).

## Phase 4 — R-G4: memory arithmetic, measured not assumed

With the s2s server warm and a session active:

```bash
free -g && nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

**Record:** baseline → server-started → session-active deltas; the s2s process's own RSS.
**Gate R-G4 (PASS =):** steady state with s2s resident + the `tutor` matrix set leaves the box **below ~105 GB used** (buffer above the ~110 GB TTS-cold-start failure line, which the shared `qwen3-tts-0.6b` container will hit on any crash-reload). Price the **dual-instance** option (×2 the s2s delta) for R-G6's fallback while you have the numbers.

## Phase 5 — R-G6: two robots = two concurrent sessions

Open a **second** Realtime session against the same server while the first is active (second conversation-app instance, or any Realtime-compatible client).

**Gate R-G6 (PASS =):** both sessions converse without cross-talk or serialization stalls.
**FAIL path (pre-approved fallback):** one s2s instance **per robot** (`:8765` Scholar, `:8766` Bridge) — only if R-G4's dual-instance arithmetic passed; otherwise robots share one instance and concurrent use is a known limitation recorded in the evidence.

## Phase 6 — R-G5 execution: tutor set as standing default (decided 2026-07-05)

Owner decision already made — `tutor` becomes the GB10's standing default set outside heavy-workload sessions, and `gemma4-tutor` gets a longer ttl within it:

```bash
sudo cp /opt/llama-swap/config/config.yaml /opt/llama-swap/config/config.yaml.bak-$(date +%F)
# Edit: in the tutor set's gemma4-tutor entry, raise ttl (1800 → 0 or ≥14400 — operator's call on idle-unload);
# make `tutor` the set loaded by default/on-startup preload posture.
# Reload llama-swap; verify:  curl -s localhost:9000/running  shows the tutor family + audio pair.
```

**Gate R-G5 (PASS =):** after reload, a `gemma4-tutor` request is warm without a set switch; the audio pair is still resident (preload order unchanged — audio first). **Mirror the config change into the `dgx-spark` repo** (standing discipline) with a dated example file.

---

## Paste-back

Fill `docs/runbooks/evidence/voice-w0r-reachy-feasibility-<date>/EVIDENCE.md` with: P0 baseline, R-G1 install log tail + startup delta, R-G2 checkpoint/backend/voice-flag results, R-G3 tool round-trip + latencies + no-cloud check, R-G4 memory table (incl. dual-instance pricing), R-G6 outcome, R-G5 config diff + running set. Any FAIL: verbatim error + the fallback taken. Then update plan §0 (W0-R row) — R1 productionizes exactly what passed here.
