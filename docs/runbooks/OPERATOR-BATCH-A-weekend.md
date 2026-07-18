# OPERATOR — Batch A (weekend voice window): R02 Pi check + R01 GB10 s2s standup

**For:** Rich (attended). **Do NOT let a code build run these — they are the human-attended checkpoints.**
**Scope:** Handoff §7 **Batch A** only — A1 = **R02** (Pi app version + local-mode support), A2 = **R01** (GB10 s2s unit on `:8765`). ~30 min total.
**Sources (authoritative order):** task `.md` files + `HANDOFF-weekend-auth-voice-fable-window.md` §7/§9 win over the fleet-gateway pickup runbook where they disagree (disagreements called out inline as **⚠ DISAGREEMENT**).
**Origin docs:** `study-tutor/tasks/backlog/reachy-local-voice-migration/TASK-VOX-R01…R02.md` · `study-tutor/docs/runbooks/evidence/voice-w0r-reachy-feasibility-2026-07-06/EVIDENCE.md` (the **W0-R pins — consume verbatim**) · `fleet-gateway/docs/runbooks/RUNBOOK-voice-004-reachy-local-voice-pickup.md`.

---

## 0. Preconditions (read once, before either step)

- **Tailnet up** (tailscale). Everything is **tailnet-only, no WAN, ever** (crib §9).
- **Hosts** (crib §9 is authoritative):
  - GB10 `promaxgb10-41b1.tailebf801.ts.net` = `100.84.90.91` — app `:8100`, llama-swap `:9000`, **s2s target `:8765`**.
  - NAS `whitestocks.tailebf801.ts.net` = `100.92.74.2` — not needed for Batch A.
  - Pi / robot — `ssh pollen@<ROBOT_LOCAL_IP>` (fleet-gateway runbook R02). **The crib sheet does NOT list the robot host/IP → OPERATOR-DECIDES `<ROBOT_LOCAL_IP>` from your deploy notes.**
- **SSH:** crib §9 gives an explicit pattern **only for the NAS** (`ssh -i ~/.ssh/fleet_memory_nas_ed25519 RichardWoollcott@whitestocks…`). **No GB10 SSH pattern is in any source doc** — the W0-R session ran **on the GB10 itself**, so run Step 2 on the GB10 directly. **OPERATOR-DECIDES the exact `ssh` invocation to reach GB10.**
- **Secrets — PATHS only, never values** (crib §9, all gitignored): `deploy/keycloak/.env.deploy`, `deploy/postgres/.env.deploy`, NAS `.env` files, `fleet-gateway/reachy/.env.example` (new voice keys). **Batch A needs no secret values** — the only key Step 2 sets is the dummy `OPENAI_API_KEY=local-llama-swap` (not a real credential; llama-swap ignores keys).
- **Quiet-GPU rule (build-plan §8 / crib):** no LPA extraction or tutor sessions mid-flight while you work `:9000`. **NEVER `GET :9000/unload`** (it unloads everything). The audio pair (`parakeet-tdt-0.6b-v3`, `qwen3-tts-0.6b`) behind `:9000` is **live — consume, don't restart**. llama-swap restart, if ever needed, is **user-mode, no sudo:** `systemctl --user restart llama-swap`.
- **Evidence dir (R-track pattern):** create `docs/runbooks/evidence/voice-r01-r02-batchA-2026-07-<DD>/EVIDENCE.md` and fill the "record" blocks below. Mark each task complete via `/task-complete` after its ACs verify.

---

## STEP 1 — A1 / R02: Pi app version + local-mode support (~10 min)

**Task:** TASK-VOX-R02 · AC-R02-1..4. Goal: read+record the installed `reachy_mini_conversation_app` version and prove it honours `HF_REALTIME_CONNECTION_MODE=local` + `HF_REALTIME_WS_URL`. The keys were verified against **upstream** docs, **not** the Pi's installed build (~2026-05-20) — close that gap before R03 relies on them.

> ⚠ **Scope note:** W0-R EVIDENCE (D3) confirmed the keys in the **Mac** clone (HEAD `f7628de`) — that does **not** cover the Pi. This step must read the **Pi's own installed version**.

```bash
ssh pollen@<ROBOT_LOCAL_IP>          # OPERATOR-DECIDES the IP (not in crib §9)
source /venvs/apps_venv/bin/activate
pip show reachy_mini_conversation_app | grep -E 'Version|Location'
# Confirm the INSTALLED version reads the two re-point keys:
python - <<'PY'
import reachy_mini_conversation_app as a, pathlib, subprocess
root = pathlib.Path(a.__file__).parent
hits = subprocess.run(["grep","-rn","HF_REALTIME",str(root)],capture_output=True,text=True).stdout
print(hits or "NO HF_REALTIME SUPPORT IN INSTALLED VERSION")
PY
```

**Decision:**
- **Keys present** (both `HF_REALTIME_CONNECTION_MODE` and `HF_REALTIME_WS_URL` appear) → **no upgrade** (AC-R02-2). Record evidence, done.
- **Keys absent** → **OPERATOR-DECIDES the upgrade** (AC-R02-3): plan + execute an app upgrade, then **re-run the grep above** to confirm, **AND** run a **Personality-Studio profile-survival check — the Scholar profile MUST survive the upgrade** before R03. *(No upgrade command is pinned in any source doc — the constraint is "an app upgrade is planned and executed, with a Personality-Studio profile-survival check".)*
- **AC-R02-4 hard fence:** the robot must **not** silently keep using the cloud — migration stays **blocked** until the re-point keys are supported.

**Record (into EVIDENCE.md):**
```
Pi host/IP used:            ______
reachy_mini_conversation_app  Version: ______   Location: ______
HF_REALTIME grep result:    [paste hits  |  "NO HF_REALTIME SUPPORT…"]
Keys honoured (local + WS_URL)?  YES / NO
If NO — upgrade target version: ______   executed: Y/N   Scholar profile survived: Y/N
AC-R02-4 confirmed (not silently on cloud): Y/N
```

---

## STEP 2 — A2 / R01: GB10 s2s unit on `:8765` (~20 min, attended)

**Task:** TASK-VOX-R01 · AC-R01-1..6. Productionize the **passing** W0-R throwaway config into a durable, digest-pinned unit **outside** llama-swap, non-loopback bind on `:8765`. **Every flag/pin below comes from the W0-R EVIDENCE flag inventory + the R01 ACs — nothing invented.**

### 2a. Warm + check the GPU FIRST (AC-R01-5, quiet-GPU)
```bash
systemctl status llama-swap-keepalive.timer      # keepalive is inactive since 07-03 → expect a cold set
free -g                                           # or your mem probe: read USED / TOTAL
```
- **Memory gate (R-G4):** need **≥12 GB headroom** and must stay **below ~110 GB used** (measured TTS-CUDA-cold-start failure line). W0-R baseline with the tutor set resident = **55 GB used**; full standing posture (tutor set + s2s pool-of-2) measured **92 GB / 121 GB** (18 GB under the line).
- If the `all`/heavy family is resident (too little headroom): **switch to the tutor set** via a 1-token completion (llama-swap set switch — do NOT `:9000/unload`). Per W0-R this frees to ~55 GB and is the standing **R-G5** posture (`gemma4-tutor` ttl 0, tutor set is `on_startup` default — already configured 2026-07-06; you're just confirming).

### 2b. Build the throwaway-proven install — **install order is load-bearing** (R-G1)
Run on the GB10. `uv` venv, python 3.12 (W0-R used `~/s2s-w0r/.venv`).
```bash
uv venv --seed                                    # Deviation 1: plain `uv venv` has NO pip → seed it
# Deviation 2 — the cu130 TTS wheel BEFORE speech-to-speech (AC-R01-4). Use the RESOLVE url, NOT the tree url:
uv pip install "https://huggingface.co/datasets/andito/qwentts-cpp-python-wheels/resolve/main/whl/cu130/qwentts_cpp_python-0.3.0%2Bcu130-py3-none-manylinux_2_39_aarch64.whl"
# (full URL recovered from the W0-R install log ~/s2s-w0r/install.log, 2026-07-17)
# Deviation 3 — speech-to-speech = git HEAD with modern floors in the SAME resolve (PyPI 0.2.10 backtracks numba→py<3.10):
uv pip install "git+https://github.com/huggingface/speech-to-speech" "numba>=0.60" "llvmlite>=0.43" "librosa>=0.10.2"
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"   # expect 2.12.1+cu130  True (PyPI aarch64, no special index)
```
> **AC-R01-4 clarification:** the cu130 wheel that must precede `speech-to-speech` is **`qwentts-cpp-python==0.3.0+cu130`** (EVIDENCE Deviation 2). **`torch` cu130 resolves automatically from PyPI aarch64** — no separate index. *(The task prose "cu130 torch wheel BEFORE speech-to-speech" maps to this qwentts wheel + the auto torch.)*
> **`<REPO>` in the resolve URL is not spelled out in EVIDENCE** (it records the wheel path + filename, not the org) → **OPERATOR-DECIDES the repo segment** from the cu130 wheelhouse you used at W0-R. Verify the wheel opens (Deviation 2 was a bad *tree* URL that resolved an invalid zip).

### 2c. Launch flags — from the W0-R flag inventory (R-G1/R-G2/R-G6)
```bash
export OPENAI_API_KEY=local-llama-swap             # Deviation 4: responses-api handler builds an OpenAI() client; dummy is fine
speech-to-speech \
  --mode realtime \
  --stt parakeet-tdt \
  --tts qwen3 --qwen3_tts_backend ggml --qwen3_tts_speaker Ryan \
  --llm_backend responses-api --responses_api_base_url http://127.0.0.1:9000/v1 \
  --num_pipelines 2 \
  --ws_host 0.0.0.0 --ws_port 8765
# --model_name : the flag exists; W0-R ran the LLM as `gemma4-tutor` (tutor set). Value not explicitly pinned in EVIDENCE → confirm/pass gemma4-tutor.
```
- **VAD:** Silero VAD is **in-process endpointing** — the EVIDENCE flag inventory shows **no `--vad`/version flag**. Task/handoff say "**Silero-VAD-v5**"; if a version pin flag is actually required it is **OPERATOR-DECIDES** (no such flag in any source doc). Constraint quoted: *"Stages are Silero-VAD-v5 → --stt parakeet-tdt → --tts qwen3."*
- **TTS checkpoint (AC-R01-2, R-G2):** target `Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice` (0.6B, ggml). **If 0.6B fails to load, fall back to 1.7B on the robot path and keep going — pre-approved ASSUM-003, no consult.** (W0-R loaded 0.6B cleanly: 4.87 s audio in 1.67 s, no fallback.)
- Expected start: ready in **~80 s** incl. first-run checkpoint downloads; log `OpenAI Realtime API starting on ws://0.0.0.0:8765/v1/realtime`.

### 2d. Package as the durable unit (AC-R01-6)
> **OPERATOR-DECIDES the unit packaging + digest pin.** Constraint (AC-R01-6, quoted): *"Runs as a **digest-pinned** systemd/docker unit **outside** llama-swap … unit files + install/launch scripts **mirrored to `dgx-spark`**."* **No unit-file text or digest value exists in any source doc** — author the unit around the 2c launch line as `ExecStart`, pin the digest (image digest for docker / pinned wheel+git-rev for systemd), then mirror to `dgx-spark`.
> W0-R process note: **systemd is preferred** — killing a bare launcher parent leaves the uvicorn child holding `:8765`; a systemd unit's control-group kill handles the tree. Consistent with llama-swap being a **user-mode** unit (`~/.config/systemd/user/`, `systemctl --user`), an s2s **user** unit is the natural fit (OPERATOR-DECIDES system vs user).

### 2e. Verification probes
```bash
ss -ltnp | grep 8765                               # expect LISTEN on 0.0.0.0:8765 (non-loopback, AC-R01-1)
# From the robot side, confirm :8765 is reachable (AC-R01-1: "bound non-loopback so the Pi can reach it").
# Scripted round-trip (the W0-R headless realtime probe — R-G6):
python ~/s2s-w0r/rt_probe.py                       # expect: session.created → VAD start/stop → STT → spoken reply
```
- **Bare-turn gate (fleet-gateway R01):** `:8765` reachable from the robot, a bare turn round-trips, **Ryan voice audible**, memory arithmetic holds at live steady state.
- **num_pipelines 2 check (R-G6):** a second WS connect should be **allocated & served concurrently** — NOT rejected with `session_limit_reached` (that's the `--num_pipelines 1` symptom).

> ⚠ **DISAGREEMENT — Ryan voice, server-side vs app-side.** AC-R01-3 (task `.md`, authoritative) says *"the Ryan voice flag is located and set **server-side**; the robot speaks in Ryan."* The fleet-gateway runbook repeats "set server-side" **but flags** — and W0-R EVIDENCE **finding 1 proves** — the server flag `--qwen3_tts_speaker Ryan` **does NOT hold at session level**; the session voice came back `Aiden`. **The reliable Ryan pin is app-side (`MODEL_VOICE=Ryan`), set at R03 (Batch B).** Resolution: **satisfy AC-R01-3 by setting the server flag now** (it *is* located + set), but **"robot speaks in Ryan" can only be fully proven after the app-side R03 pin** — record Ryan as *set server-side* here and defer the audible-Ryan-on-robot confirmation to R03. Flag this to Fable.

### 2f. Rollback / stop
```bash
systemctl --user stop <s2s-unit-name>              # control-group kill reaps the uvicorn child holding :8765
# Manual fallback (NO systemd): kill the whole process tree — a bare parent-kill orphans uvicorn on :8765.
#   Beware: a broad `pkill -f speech-to-speech` can also match your own shell (W0-R Phase 5 note).
```
- **Do NOT touch llama-swap `:9000`** to roll back s2s — s2s is a **separate unit outside** llama-swap. **Never `GET :9000/unload`.** Never restart the live `:9000` audio pair.

**Record (into EVIDENCE.md):**
```
GB10 baseline before standup:   USED ___ / 121 GB   headroom ___ GB (≥12?)   keepalive.timer: ___
Resident set at start / tutor-set switch done?: ______
Install order honoured (qwentts cu130 wheel BEFORE speech-to-speech)?: Y/N   resolve-URL wheel opened OK?: Y/N
torch: ______ (+cu130)   cuda.is_available(): T/F
speech-to-speech install: success? attempts ___ / pkgs ___
TTS checkpoint loaded: 0.6B  |  1.7B fallback (ASSUM-003)     ggml backend?: Y/N
Ryan flag set server-side?: Y/N   (session voice actually heard: ____  — see R01/R03 caveat)
Unit type: systemd(user/system) | docker    unit name: ______    digest pinned: ______
Bind: ss LISTEN 0.0.0.0:8765?: Y/N    start log line seen?: Y/N
--num_pipelines 2 concurrent 2nd session allocated (not session_limit_reached)?: Y/N
Round-trip: rt_probe.py result: ______   bare turn OK?: Y/N   Ryan audible?: Y/N/deferred-to-R03
Steady-state memory with s2s + tutor set: ___ GB (target <~110)
Unit files/scripts mirrored to dgx-spark?: Y/N
```

---

## TELL FABLE (report back when Batch A is done)

1. **Pi version (R02):** installed `reachy_mini_conversation_app` **Version** + whether it **honours `HF_REALTIME_CONNECTION_MODE=local` + `HF_REALTIME_WS_URL`** (yes/no); if upgraded — new version + Scholar-profile-survived (yes/no). Whether migration is unblocked or still fenced (AC-R02-4).
2. **s2s unit (R01):** **unit name** + type (systemd user/system or docker) + **digest pinned** value + **mirrored to dgx-spark** (yes/no).
3. **Bind address:** confirm `ws://promaxgb10-41b1:8765/v1/realtime`, listening `0.0.0.0:8765` (non-loopback).
4. **Round-trip result:** `rt_probe.py` outcome + bare-turn OK + **which TTS checkpoint (0.6B vs 1.7B fallback)** + steady-state memory number.
5. **Ryan-voice caveat:** confirm the ⚠ disagreement — server flag set, audible-Ryan confirmation deferred to R03's app-side `MODEL_VOICE=Ryan`.
6. **Any OPERATOR-DECIDES you resolved:** GB10 ssh method, `<ROBOT_LOCAL_IP>`, cu130 wheel `<REPO>`, `--model_name` value, VAD-v5 flag (if any), unit packaging.
