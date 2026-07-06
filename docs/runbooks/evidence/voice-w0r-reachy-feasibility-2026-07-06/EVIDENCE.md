# W0-R Evidence — Reachy local-voice feasibility gates

**Run date:** 2026-07-06 · **Runbook:** [RUNBOOK-voice-w0r-reachy-feasibility.md](../../RUNBOOK-voice-w0r-reachy-feasibility.md)
**Executed by:** Claude (Fable session **on the GB10 itself** — the runbook's operator-only premise
didn't apply; attended parts flagged below) · **Operator:** Rich

## Phase 3 pre-flight (recon deltas D1/D3)

- **D1 — DONE 2026-07-06 (code fix taken, not the swap):** `query_student_model` ported to the
  conformant Pollen shape (`parameters_schema` + `async def __call__(deps, **kwargs)`, pattern
  copied from `ask_jarvis.py`) in `fleet-gateway/reachy/external_content/external_tools/query_student_model.py`.
  Import + shape verified: class is callable, no `run()` remains, schema keys `subject`/`student_name`.
  (Uncommitted in fleet-gateway at time of writing.) Note per the amended gate text: judge R-G3 on
  tool **forwarding + narration**, not data freshness (Graphiti backend is retired/frozen).
- **D3 — PASS (operator, 2026-07-06):** Mac clone at
  `/Users/richardwoollcott/Projects/appmilla_github/reachy_mini_conversation_app`, HEAD
  `f7628debdf7913bb48f67d04256bbf0f2a471e19`; grep confirms `HF_REALTIME_CONNECTION_MODE` /
  `HF_REALTIME_WS_URL` are read via `config` (tests reference `ws://127.0.0.1:8765/v1/realtime`
  exactly). Note: the earlier "Mac offline" reading was a red herring — `nvsync-mac` is a stale
  tailnet node; the live Mac is `richards-macbook-pro`.
- **D1 fix shipped:** fleet-gateway `c051ba3` (pushed) — Mac must `git pull` fleet-gateway before
  the R-G3 run so the conformant tool is the one loaded.
- **Server-side tool machinery confirmed (pre-R-G3):** this s2s build handles `session.update`
  (incl. tools), `function_call`/`function_call_output` conversation items, and emits
  `response.function_call_arguments.done` — the forwarding path exists; R-G3 tests it end-to-end.

## Phase 0 — Preconditions

- keepalive timer: `inactive (dead) since 2026-07-03 06:17 BST` ✔ (matches runbook expectation)
- Running set at start: `all` family — coach-ft-v3, embed, nomic-embed, parakeet-tdt-0.6b-v3,
  qwen-graphiti, qwen3-tts-0.6b, qwen36-workhorse (all `ready`)
- Baseline memory: **113 GB used / 121 GB, ~7 GB available** → **Gate P0 FAIL as found**
  (needs ≥12 GB headroom; above the ~110 GB TTS-cold-start failure line)
- **Remedy (per runbook "free a family" + consistent with the pre-decided R-G5 tutor-default
  posture):** triggered the `tutor` set switch via a 1-token `gemma4-tutor` completion
  (llama-swap set switch, 18.5 s incl. model load; no inference activity in the prior 15 min).
- Post-switch running set: embed, gemma4-tutor, parakeet-tdt-0.6b-v3, qwen3-tts-0.6b (all `ready`;
  tutor-coach loads on demand within the set)
- Post-switch memory: **55 GB used / 121 GB, 66 GB available**

**Gate P0: PASS** (66 GB headroom ≥ 12 GB) — baseline for R-G4 deltas = **55 GB used**.

## Phase 1 — R-G1: throwaway s2s install + start

- Venv: `~/s2s-w0r/.venv` (uv, python 3.12); install started 2026-07-06 15:41 BST, log: `~/s2s-w0r/install.log`
- **Deviation 1 (runbook step defect):** `uv venv` creates the venv **without pip** — the runbook's
  `pip install …` line fails with `.venv/bin/pip: No such file or directory`. Remedy: `uv pip
  install -p .venv/bin/python …` (or `uv venv --seed`).
- **Deviation 2 (runbook pin defect):** the find-links URL
  `…/tree/main/whl/cu130` is an HTML page, not a wheel index — uv resolved an invalid artifact:
  `The structure of qwentts-cpp-python (v0.3.0+cu130) was invalid: Failed to read from zip file`.
  Remedy: direct resolve URL —
  `…/resolve/main/whl/cu130/qwentts_cpp_python-0.3.0%2Bcu130-py3-none-manylinux_2_39_aarch64.whl`
  (wheel exists for aarch64; verified via the HF API tree listing). **R1's productionized unit must
  pin this resolve URL, not the tree URL.**
- **Deviation 3 (runbook pin defect):** `pip install speech-to-speech` (PyPI v0.2.10) AND the git
  fallback both fail to resolve on Python 3.12 — the resolver backtracks to `numba 0.53.1` /
  `llvmlite 0.36` (requires Python <3.10) via `faster-qwen3-tts → qwen-tts → librosa`. Remedy
  (worked): install git HEAD **with modern floors in the same resolve**:
  `uv pip install "git+https://github.com/huggingface/speech-to-speech" "numba>=0.60" "llvmlite>=0.43" "librosa>=0.10.2"`.
- **Install SUCCESS** attempt 5, 15:46:38 → 15:50:07 (~3.5 min), 119 packages. `speech_to_speech`
  imports; CLI entrypoint `.venv/bin/speech-to-speech` present.
- **torch = 2.12.1+cu130 with `cuda.is_available() == True`, straight from PyPI aarch64** — no
  special index needed (a 2026 improvement; the install path is simpler than feared).
- **Flag inventory (this build):** all runbook flags exist (`--mode realtime`, `--stt parakeet-tdt`,
  `--tts qwen3`, `--llm_backend responses-api`, `--model_name`, `--responses_api_base_url`).
  **Voice flag located (R-G2 requirement): `--qwen3_tts_speaker` → set `Ryan`.** Backend selector:
  `--qwen3_tts_backend {ggml,torch}` (ggml first, per runbook). Bind flags for Phase 3:
  `--ws_host` / `--ws_port`.
- **Deviation 4 (runbook step defect):** first server start died at handler build —
  `openai.OpenAIError: The api_key client option must be set…`. The responses-api handler
  constructs an `OpenAI(...)` client requiring `OPENAI_API_KEY`; llama-swap ignores keys, so a
  dummy value suffices: `OPENAI_API_KEY=local-llama-swap`. **R1's unit file must set this env var.**
- **Server UP** (second start, with `OPENAI_API_KEY` set): ready in **~80 s** incl. first-run
  checkpoint downloads; log: `OpenAI Realtime API starting on ws://0.0.0.0:8765/v1/realtime
  (pool size 1)`; `ss` confirms LISTEN on `:8765`. **Note: binds `0.0.0.0` by default** — no
  restart needed for the Mac phase (tailnet-only exposure per house posture; R1's unit should
  bind deliberately).
- **Startup memory delta: 55 → 64 GB used (~9 GB for the full s2s stack** — VAD + Parakeet STT +
  Qwen3-TTS ggml + server).

**Gate R-G1: PASS** (with 4 recorded deviations R1 must pin: uv-venv-no-pip, resolve-URL wheel,
numba floors, `OPENAI_API_KEY`)

## Phase 2 — R-G2: 0.6B TTS synthesizes (+ Ryan voice flag)

- **Synthesis proven at warmup:** the **0.6B CustomVoice** checkpoint
  (`Qwen/Qwen3-TTS-12Hz-0.6B-CustomVoice`) loaded under the **ggml backend** with
  **`--qwen3_tts_speaker Ryan`** accepted, and generated **4.87 s of audio in 1.67 s**
  (server log: `RTF: 2.92, custom_voice`; per-stage perf lines recorded in `~/s2s-w0r/server.log`).
  No fallback to 1.7B or the torch backend was needed.
- _Intelligibility: operator listen via the Mac session (R-G3 doubles as this), or the objective
  STT round-trip if unattended._

**Gate R-G2: PASS on synthesis + voice-flag location; intelligibility confirmed at R-G3**

## Phase 3 — R-G3: tool round-trip through local s2s

Run 2026-07-06 ~16:04–16:06 BST, operator on the Mac clone (HEAD `f7628de`), **with the physical
Reachy in the audio loop** (app ↔ robot daemon over WebRTC, LAN `172.30.1.185:8443`; SDK 1.7.1 vs
daemon 1.8.4 mismatch warning — benign this run).

- **Re-point worked:** app log `connection mode: local` →
  `Using direct Hugging Face realtime endpoint ws://promaxgb10-41b1:8765/v1/realtime`.
- **D1 fix verified in the real loader:** `✓ Loaded external tool: query_student_model` (and
  ask_jarvis, celebrate_achievement); session registered 6 tools. (`emotion` still "not found" —
  known app-version issue, matches recon D4.)
- **Tool fired + narrated:** operator asked "What do you know about Lilymay's studies?" →
  assistant: *"…she's on a 3-day revision streak… English Language at level 2… very close to
  unlocking her next achievement."* Data is knowingly **stale** (frozen Graphiti; live state is in
  Postgres — FEAT-VOICE-004 recon D2 re-points this read). Gate judges forwarding+narration: ✔.
- **No-cloud proof:** Mac `lsof` on the app PID shows only GB10 `:8765`, localhost, and the robot
  WebRTC `:8443` — **no HF/cloud `:443` from the app process**.
- **Latency (AC-R4-grade numbers):** first audio delta **978 ms** (tool-call turn) and **1172 ms**
  (data-narration turn) after user transcript; server TTS RTF ~3.3× realtime.
- **Memory session-active: 64 GB** (no growth over warm — R-G4 input).

**Gate R-G3: PASS** — with three mechanism findings for R1/R2/FEAT-VOICE-004:

1. **Voice pin is SESSION-level, not server-level.** The app's `session.update` set
   `voice='Aiden'` (profile `voice.txt` 'Kore' rejected against the HF-backend list
   `[Aiden, Ryan, Dylan, …]`); the server CLI `--qwen3_tts_speaker Ryan` did **not** hold for the
   session. → The robot deploy must set the app-side voice (e.g. `MODEL_VOICE=Ryan` in
   env/sitecustomize, or profile update) — the fleet Ryan pin cannot be enforced from the server
   flag alone.
2. **Tool calls ride the TEXT protocol — and the robot SPEAKS the tool-call syntax aloud**
   (operator-confirmed on the second session, 16:22–16:24: every `<|tool_call>call:…<tool_call|>`
   line was TTS'd — this is the "garbled audio"). **Refined diagnosis (from server source):** the
   server *does* forward session tools to llama-swap as native functions
   (`base_openai_compatible_language_model.py:551`) and has the full
   `response.function_call_arguments.done` event path — the `Tools: []` log line is the
   *structured tool calls returned* (none). The gap is the **model side**: `gemma4-tutor` under
   the custom leak-fix chat template (`gemma4-tutor.jinja`) never emits llama.cpp-structured tool
   calls, so the app's prompt-taught text protocol is what comes back — as speakable text.
   **Fix options for R1/FEAT-VOICE-004 (recommend both):**
   (b1) extend `gemma4-tutor.jinja` with tool-call support so llama.cpp returns structured
   `tool_calls` → server emits function_call events instead of text → nothing speakable exists
   (the clean fix; test against the `<|channel>` leak the template was built to stop);
   (a) belt-and-braces server-side strip of `<|tool_call>…<tool_call|>` spans in the LLM→TTS path
   (small patch, upstream-able). Client-side auto-flush on tool-call transcript is a partial
   mitigation only (some tokens get spoken before the flush).
   Related observations, same sessions: the narrated "data" drifts/embellishes across calls
   (run 1: streak 3/level 2 · run 2: streak 4/level 3/450 XP/"Consistency King") — stale-Graphiti
   input plus model embellishment; persona hardening ("narrate tool data verbatim") goes with the
   D2 Postgres re-point. Also one robot-daemon WebRTC drop mid-session
   (`Failed to set robot target: Lost connection with the server`, 16:23:57, ~50 repeats) — motion
   plane only, conversation continued; SDK 1.7.1 vs daemon 1.8.4 mismatch is the suspect; note for
   R2 (align SDK versions).
3. **Parakeet mis-transcription of the wake phrase** ("Reachy, are you alright?" →
   "Every chee, are you right?") — robot-mic + name-word quirk; no gate impact, note for persona
   phrasing.

**R-G2 intelligibility: confirmed by operator ear** during this session (voice was Aiden per
finding 1 — synthesis/intelligibility proven; Ryan-specific listen rolls into the voice-pin fix).

## Phase 4 — R-G4: memory arithmetic (measured)

Baseline (tutor set, post-P0): 55 GB used → s2s server warm: **64 GB used** (delta ~9 GB).
_Session-active delta: TBD at R-G3._ **Dual-instance pricing (R-G6 fallback): ~73 GB projected —
comfortably under the ~105 GB line.**

**Gate R-G4: PASS-trending** (PASS = steady state below ~105 GB with s2s + tutor set resident;
session-active measurement outstanding)

## Phase 5 — R-G6: two concurrent sessions

- **Discovery: the server has a native pool** — `--num_pipelines N` ("one uvicorn server …
  routes each incoming websocket to the next free pipeline"). This supersedes the runbook's
  two-instance (`:8765`/`:8766`) fallback design.
- With `--num_pipelines 1` (default): a second WS connect is **accepted then refused** with
  `session_limit_reached` ("All 1 session slots are in use") — recorded 16:11 BST.
- With `--num_pipelines 2`: second session **allocated and fully served concurrently** with the
  operator's live Mac/robot session — headless probe (`~/s2s-w0r/rt_probe.py`) got
  `session.created`, VAD speech start/stop, STT transcription, and a spoken reply while session 1
  stayed live.
- **Objective R-G2 intelligibility (no-human-listener check) rode along:** probe TTS'd
  "What is a simile? Answer in one short sentence." via `:9000` (Ryan), spoke it into the session,
  and STT'd the reply back: *"A simile is a figure of speech that compares two different things
  using the words like or as."* — correct and fully intelligible.
- **Memory: 67 GB used with the pool-of-2 warm AND both sessions active** (~13 GB total for the
  two-pipeline server over the 54 GB tutor-set baseline — the second pipeline costs only ~4 GB
  marginal, far cheaper than the priced dual-instance fallback). 38 GB below the ~110 GB line.
- **Cross-talk/serialization check — confirmed from logs:** the operator conversed continuously
  16:22:38–16:24:01 (app log) while pipeline 1 synthesized the probe's 8.16 s reply (16:23:03,
  RTF 1.50) concurrently with pipeline 0's 17.64 s narration (16:23:06, RTF 2.48) — both above
  realtime, no stalls, no content bleeding between sessions. (Concurrent RTF drops from ~3.4× to
  ~1.5–2.5× — the two ggml TTS instances contend but stay realtime-safe.)

**Gate R-G6: PASS (pool mode)** — R1's unit should launch with `--num_pipelines 2` for the
two-robot fleet; the `:8766` second-instance fallback is unnecessary.

**Process notes for R1 (from this phase's restarts):** killing the launcher parent leaves the
uvicorn child holding `:8765` — a systemd unit (default control-group kill) handles this; manual
restarts must kill the process tree (and beware `pkill -f` patterns matching your own shell).

## Phase 6 — R-G5: tutor set as standing default (decided 2026-07-05)

- Runtime posture exercised since Phase 0 (tutor set active all run).
- **Config executed 2026-07-06 (owner chose ttl 0):** `gemma4-tutor` ttl 1800 → **0** (always
  resident); `on_startup` preload rotated from the `all` family (qg/ne/qw/cfv3) to the tutor set
  (audio pair first, then gt/tc/em); keepalive `MODEL_PROBE_KIND` allowlist rotated to match
  (gt/tc/em; audio pair deliberately unprobed, standing decision). Backups:
  `config.yaml.bak-2026-07-06`, `llama-swap-keepalive.sh.bak-2026-07-06`.
- **Ops fact:** `llama-swap.service` is a **user-mode** unit
  (`~/.config/systemd/user/llama-swap.service`) — restart with `systemctl --user restart
  llama-swap`, no sudo; the keepalive units are system-level. (First restart attempt failed on
  `sudo systemctl restart llama-swap` — unit not found at system level.)
- **Verified after restart:** all tutor-set members `ready` (audio pair loaded first);
  1-token `gemma4-tutor` request answers in **0.120 s** with no set switch.
- **Steady state, full standing posture** (tutor set incl. tutor-coach + s2s pool-of-2 still up):
  **92 GB / 121 GB** — 18 GB under the ~110 GB line. (Heavy sets — coach31/autobuild_go/po_eval —
  still evict the tutor family on demand as designed.)
- **dgx-spark mirror:** `examples/llama-swap-config.gb10-live-2026-07-06-tutor-default.yaml`,
  commit `be71e3f`, pushed.

**Gate R-G5: PASS (decision + config + mirror all executed)**

## Decision-gate summary

| Gate | Result |
|---|---|
| P0 | **PASS** (after tutor-set switch; 66 GB headroom) |
| R-G1 | **PASS** (4 install deviations recorded for R1 to pin) |
| R-G2 | **PASS** — 0.6B/ggml synthesizes (RTF ~3.4×); objective STT round-trip fully intelligible; **voice pin must be app-side** (finding 1) |
| R-G3 | **PASS** — tool fired + narrated via local s2s, no cloud; **defect: tool-call syntax is spoken** (finding 2, fixes identified) |
| R-G4 | **PASS** — 67 GB steady with pool-of-2 + two active sessions (38 GB under the line) |
| R-G5 | **PASS** — ttl 0 (owner decision), tutor-set preload + keepalive rotated, warm tutor 0.12 s, mirrored to dgx-spark `be71e3f` |
| R-G6 | **PASS** — `--num_pipelines 2`; concurrent sessions verified; second-instance fallback unnecessary |
