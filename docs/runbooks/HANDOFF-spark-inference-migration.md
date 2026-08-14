# HANDOFF — Move study-tutor inference from GB10 to spark-fcf6

**Status:** S0–S2 EXECUTED 2026-07-25 (spark session) · S0 ✅ S1 ✅ · S2 first run ❌
(cold-load-order OOM, 14:56) → **coach-first pre-warm + gate re-run 18:17–18:26 ✅ PASS**
· **Spark is serving all four aliases + embed, warm — READY for attended S3.** Keepalive
timer left PAUSED (see Evidence). S3 not attempted (attended, operator-run). Originally
DRAFT 2026-07-25, authored by the GB10 coordinator session, for a Claude session running
**on spark-fcf6**. Method:
[orchestrated-build playbook](../../../ai-transition/docs/ways-of-working/playbook/orchestrated-build-playbook.md)
— staged builds, an independent coach verifies each stage *by driving*, the final live
cutover stays an attended human step on the GB10.

## Goal

The GB10 now runs factory builds (factory-dashboard, office-manager, forge, autobuild,
specialist agents) and competes with study-tutor's inference. spark-fcf6 is essentially
dedicated. Move the four model endpoints study-tutor consumes onto spark's llama-swap so
the GB10's :9000 keeps serving everything else untouched. **The cutover itself is a pure
`.env` flip on the GB10** — the compose passthrough shipped 2026-07-25 makes every model
endpoint an environment override.

## Verified current state (all checked live 2026-07-25 — trust but re-verify in S0)

**What study-tutor consumes** (all via one llama-swap endpoint, today `GB10:9000`):

| Alias | Role | Where set |
|---|---|---|
| `gemma4-tutor` | tutor loop | compose default `LOCAL_MODEL` (deploy/http/docker-compose.yml) |
| `tutor-coach` | coach verdicts | `TUTOR_COACH_MODEL` in gitignored `deploy/http/.env` |
| `parakeet-tdt` → `parakeet-tdt-0.6b-v3` | voice STT | code default (`src/study_tutor/voice/config.py`) |
| `qwen3-tts` → `qwen3-tts-0.6b`, voice `Ryan` | voice TTS | code default (same file) |

Voice is **live and verified E2E** on GB10 `:8100` as of today (real transcript → tutor
reply → WAV chunk, test user alex). Don't break it: rollback must always be one `.env`
revert away.

**spark-fcf6 already has** (probed today): llama-swap `:9000` as a systemd user service
(`llama-swap.service`, config `/opt/llama-swap/config/config.yaml`) + LiteLLM front door
`:4000`; models already present include **`gemma4-tutor` and `tutor-coach`** plus
`coach`, `workhorse`, `embed`, `gpt-oss-120b`, `recruiter(-8b)`, `granite-vision-4-1-4b`.
121 GB unified, ~70 GB available. Resident co-tenants that MUST keep working:
**`cr0-comfyui`** (FLUX render box for Lilymay's Study Room) and any **`rc-ft-*`**
fine-tune containers.

**spark-fcf6 is missing**: the two audio models. On the GB10 they are llama-swap-managed
docker containers, not llama.cpp processes:

- Config blocks: `/opt/llama-swap/config/config.yaml` ~lines 905–945 on the GB10 —
  `parakeet-tdt-0.6b-v3` (aliases `parakeet-tdt`, `parakeet`; `ttl: 0`;
  `concurrencyLimit: 4`; `checkEndpoint: /health`) and `qwen3-tts-0.6b` (aliases
  `qwen3-tts`, `tts-1`; `ttl: 0`; `concurrencyLimit: 2`). Read the surrounding comments
  in full — residency rules (`pk`/`qt` in every matrix set, audio pair FIRST in preload)
  and the qwen3-tts patched-`/health` warmup contract live there.
- Launch scripts: `/opt/llama-swap/scripts/audio-parakeet.sh`, `audio-qwen3tts.sh`.
- Patched server mount: `/opt/llama-swap/audio/qwen3-tts-config` (makes `/health` 503
  until CUDA-graph warmup completes — `checkEndpoint`-ready ⇒ truly warm).
- Images (digest-pinned, and **built for this spark hardware**):
  `martinb78/parakeet-tdt-v3-spark@sha256:298efedc…`,
  `martinb78/faster-qwen3-tts-dgx-spark@sha256:e1c69bc4…`.
- Container restart policy is `no` **on purpose** — llama-swap owns the lifecycle
  (`cmd`/`cmdStop`); keep it `no` on spark.
- `/opt/llama-swap/config` is **not** a git repo on either box — mirror by `scp`, and
  keep a dated backup of spark's config before editing.

**Networking gotcha (cost us an hour today):** inside a compose network, the bare
hostname `promaxgb10-41b1` resolves to **127.0.0.1**, and containers may not resolve
`*.ts.net` MagicDNS names. All cross-box URLs in `.env` use **tailnet IPs**:
GB10 = `100.84.90.91`, **spark-fcf6 = `100.105.247.62`**, whitestocks = `100.92.74.2`.

## Fences (binding, playbook rule 3)

1. **Never touch `cr0-comfyui` or `rc-ft-*`** — no stop, no restart, no eviction of
   their memory via preload changes. If memory arithmetic doesn't fit with them
   resident, STOP and report; do not "make room".
2. **GB10's llama-swap stays untouched.** Other consumers (factory, LPA, QAV shadow,
   Reachy s2s) depend on it. This migration only *adds* to spark.
3. Spark config edits are **additive and comment-delimited** (`# BEGIN/END study-tutor
   audio 2026-07-25`), with the pre-edit config saved as
   `config.yaml.bak-<date>`. Rollback = restore the backup.
4. **Measure, don't assume, memory** (the W0-R R-G4 lesson): before and after each
   load, record actual usage (`free -g`, container stats). qwen3-tts cold-start
   fails near memory exhaustion — warm it while headroom is proven.
5. The spark session **does not touch the study-tutor deploys** on the GB10 and does
   not push to the study-tutor repo. The live cutover (S3) is run by the operator /
   GB10 coordinator, attended.

## Stages

Run as a Workflow per the playbook skeleton (builder + independent coach per stage), or
manually in order — but keep the coach discipline: verify by driving, not by reading
the builder's claims.

### S0 — Discovery & preflight (spark)

Build: none. Verify: llama-swap service healthy and its exact config path/flags
(`systemctl --user cat llama-swap`; confirm `-watch-config` — it determines whether
config edits hot-reload or need a service restart). Confirm `gemma4-tutor` and
`tutor-coach` configs match the GB10's (scp GB10's config over for diff; context sizes,
model files present under `/opt/llama-swap/models`). Record free memory with ComfyUI +
any rc-ft job resident. Confirm docker present and can pull the two audio images.
**Coach gate:** a written inventory with numbers, and `curl :9000/v1/models` output.

### S1 — Audio pair standup (spark)

Build: copy from GB10 → spark: the two launch scripts, the
`/opt/llama-swap/audio/qwen3-tts-config` mount dir, and the two config blocks
(comment-delimited, adapted only where paths differ). Update spark's matrix
sets/preload per the GB10 comments (`pk`/`qt` members; audio pair first) **only if
spark uses the same matrix mechanism — otherwise minimal `ttl: 0` entries and note the
divergence**. Pull both images by digest. Reload llama-swap; warm both.
**Coach gate (drive it):** on spark —
`curl -F model=parakeet-tdt -F file=@silence.wav http://127.0.0.1:9000/v1/audio/transcriptions`
returns `{"text":""}`; a `qwen3-tts` + voice `Ryan` speech call returns a RIFF WAV;
both under the **short aliases**; memory recorded before/after; ComfyUI still answers
`:8188/system_stats`; rc-ft container still running.

### S2 — Tutor pair proof under co-tenancy (spark)

Build: none (models already present).
**Coach gate:** `gemma4-tutor` chat completion and `tutor-coach` completion succeed on
spark `:9000` with the audio pair + ComfyUI + rc-ft all resident; note tokens/s vs the
GB10 (the factory-loaded GB10 is the baseline we're escaping — spark should win or
tie); no OOM, no eviction of co-tenants (`docker ps` unchanged).

### S3 — Cutover (ATTENDED — operator/GB10 coordinator, not the spark session)

From the GB10, prove reachability: `curl http://100.105.247.62:9000/v1/models`. Then in
`deploy/http/.env` (all overrides already plumbed — compose passthrough + `TUTOR_*`
interpolations):

```bash
TUTOR_OPENAI_BASE_URL=http://100.105.247.62:9000/v1
TUTOR_COACH_ENDPOINT=http://100.105.247.62:9000/v1
TUTOR_LLM_BASE_URL=http://100.105.247.62:9000
STT_BASE_URL=http://100.105.247.62:9000/v1     # replaces today's host.docker.internal line
TTS_BASE_URL=http://100.105.247.62:9000/v1
```

`docker compose up -d` (recreates), then smoke as **alex** (never lilymay — her real
session state matters): `/healthz`; text turn; the voice-turn curl from
`docs/runbooks/` history (POST `/api/sessions/{id}/voice-turn`, form field `audio`,
Bearer `<bearer-alex>`) returns 200 with transcript + audio chunk. Then the phone
tap-to-talk re-test. **Rollback:** delete/revert those five lines, `docker compose up
-d` — back on GB10 inference in <1 min.

## Out of scope (explicitly)

- QAV shadow models (`qav-*`) and everything else on GB10's llama-swap — stays.
- The keycloak-mode deploy `:8101` — same flip later via `deploy/http/.env.kc` once
  tap-to-talk passes on `:8100` (voice env not yet enabled there at all).
- Reachy/s2s voice (`:8765`) — separate lane (FEAT-VOICE-004), untouched.
- Decommissioning GB10's audio containers — only after S3 has soaked; note their
  `Restart=no` means a GB10 reboot already leaves them down until llama-swap restarts
  them on demand.

## Done means

Spark serves all four aliases warm; `:8100` runs a full voice turn against spark with
factory builds hammering the GB10; rollback path rehearsed; this doc updated with an
evidence block (dates, outputs) and any config divergences found in S0.

---

## Evidence block — S0–S2 run, 2026-07-25 (spark session)

Executed on spark-fcf6 by the Claude session this doc was written for, 14:26–15:10 UTC.
Method per the playbook: builder inline, **independent workflow coach per stage,
verifying by driving** (own test inputs, own probes). Coach transcripts under the
session dir (`subagents/workflows/wf_fa0521de-876`, `wf_6ba30271-f15`,
`wf_a5916ed1-48d`).

### S0 — PASS (two coaches: drive-verify + completeness critic)

- llama-swap: systemd **user** service, v219 (4ca9c478), `-config
  /opt/llama-swap/config/config.yaml -listen :9000 -watch-config` ⇒ **hot-reload, no
  restart needed**. CPUAffinity 4-19.
- `:9000/v1/models` pre-migration: 9 models incl. `gemma4-tutor` + `tutor-coach`;
  `/running` empty (operator had `/unload`-ed the fleet ~14:08 for a training window).
- Tutor pair vs GB10: **flag-for-flag identical** (ctx 32768 both; tutor Q4_K_M +
  jinja template, coach UD-Q4_K_XL `--reasoning off --reasoning-budget 0`); only the
  llama-server binary path differs, plus GB10-only alias `gemma4-specialist` (unused
  by study-tutor). GGUFs + `gemma4-tutor.jinja` present on spark.
- Memory baseline (fence 4): 121 total / 55 used / **65 available**; co-tenants
  resident: `cr0-comfyui` (idle 185 MiB — FLUX ~20-25 GB only while rendering),
  `rc-ft-8bc2-20260725-140837` (active fine-tune, ~6 GiB, 100% CPU).
- Keepalive: system timer, 5-min cadence, allowlist workhorse/coach/chat/embed —
  **deliberately paused 14:08–~18:08** by `flock … sleep 14400` on
  `/var/lock/llama-swap-keepalive.lock`. Left untouched.

**Divergences found:**

- **D1 — live GB10 config not diffable from spark**: spark→GB10 ssh refused (both
  keys; working direction is GB10→spark only). S1 source = dgx-spark repo @ `660cc1d`
  (up to date with origin): `scripts/audio-*.sh`, `vendor/…/deployed/` (patched
  server), `examples/llama-swap-config.gb10-live-2026-07-15.yaml` (audio blocks lines
  728–775). **Accepted as S1 source**: this doc's own audio-block contract (ttl,
  concurrencyLimits, aliases, checkEndpoint, digests) matches the snapshot exactly —
  risk LOW. GB10 live `:9000/v1/models` (read-only GET) confirmed all four aliases
  live there.
- **D2 — llama-swap v219 re-runs `hooks.on_startup.preload` on config hot-reload.**
  The 14:43 config install preloaded audio pair **and** wh/co/em, peaking **115 GB
  used / 6 available** during the training window; unloaded immediately after
  preload settled, then re-warmed audio only. Plan for this on ANY future config edit.
- **D3 — spark is also the recruiter micro-agents lane venue** (train + serve:
  `recruiter`, `recruiter-8b`, workhorse judge on the same `:9000`; discovered
  mid-session from the operator). The `tutor` set and the recruiter/fleet seats are
  **mutually exclusive** (set switch evicts); the audio pair survives all switches
  (`pk`/`qt` in every set). Tutoring windows and recruiter gate/exam runs must be
  scheduled around each other.

### S1 — PASS (two coaches: endpoint driver + artifact auditor)

Build (all additive; backup `config.yaml.bak-20260725-pre-study-tutor-audio`):

- Launch scripts → `/opt/llama-swap/scripts/audio-{parakeet,qwen3tts}.sh` —
  byte-identical to dgx-spark repo (md5 `6269…f3c` / `d37b…4bb`), executable.
- Patched mount → `/opt/llama-swap/audio/qwen3-tts-config/` from `vendor/…/deployed/`
  (503-until-warm health patch verified in the installed copy).
- Weights → `/opt/llama-swap/models/qwen3-tts/Qwen3-TTS-12Hz-0.6B-CustomVoice`
  (`hf download`, 2.4 GB, model.safetensors 1.81 GB + speech_tokenizer).
- Images pulled by exact digest (`298efedc…`, `e1c69bc4…`; 22.9 GB + 7.3 GB, arm64).
- Config: audio blocks inside `# BEGIN/END study-tutor audio 2026-07-25`; `pk`/`qt`
  vars; **all three sets** (`all`, `big`, `tutor`) gained `& pk & qt`; preload gained
  the audio pair FIRST. Auditor confirmed the live-vs-backup diff contains **nothing
  else**.

Coach drive (own inputs): silence → `{"text":""}` under `parakeet-tdt` (0.18 s warm);
`qwen3-tts` + Ryan → RIFF WAV 24 kHz mono (2.02 s warm); **round-trip transcript
matched the coach's sentence**; aliases `parakeet`/`tts-1` also serve. Builder cold
loads: parakeet 36 s (+5 GB), qwen3-tts 55 s (+4 GB). Container restart policy `no`
both. ComfyUI `:8188/system_stats` alive; co-tenants untouched.

### S2 — FAIL (gate letter), with strong positives — re-run required before S3

- `gemma4-tutor`: cold 22.5 s; **warm 1.48 s @ 54.3 tok/s** (alone).
- `tutor-coach` **first cold request returned HTTP 500** ("upstream command exited
  prematurely") with **4 kernel NVRM `NV_ERR_NO_MEMORY`** events at 14:56:03: the
  17 GB UD-Q4_K_XL with `--no-mmap -ngl 999` could not allocate at **27 GB
  available** (tutor ~25 GB already resident + audio + co-tenants). Retry succeeded
  after the kernel swapped ~5 GB: cold 41.3 s, **warm 2.98 s @ 15.9 tok/s — ~3×
  faster than the GB10's documented ~9 s CoachVerdict** (no live GB10 probe; fence 2).
- Audio pair **survived the set switch** and still served (first TTS after the switch
  6.6 s, then 4.0 s; STT 2.4 s). No co-tenant died/restarted; no Linux oom-killer.
- **Measured, not assumed (fence 4):** tutor pair ≈ **36 GB resident + ~5 GB swap
  displacement** (config note says ~33 GB); end-of-gate box: 100 used / 21 available /
  swap 11 of 15. Co-resident throughput: tutor drops to **18.1 tok/s** (vs 54 alone)
  — the realistic serving number, since study-tutor alternates tutor and coach.
- Post-gate the session `/unload`-ed and re-warmed **audio only** (end state: audio
  pair ready, 62 used / 58 available), returning the box to the training-window
  posture.

### S2 re-run — PASS (18:17–18:26 UTC, after coach-first pre-warm)

Builder executed the prescribed pre-warm once the recruiter lane freed the box
(keepalive timer paused first, per the tutoring-window procedure — **left paused, see
below**):

- `tutor-coach` requested FIRST: set switch evicted wh+co (115→89 GB used, 32 GB
  available), coach loaded clean in 29 s — no 500 this time.
- `gemma4-tutor` second: loaded in 34.7 s. **One transient NVRM `NV_ERR_NO_MEMORY` at
  18:19:36 during this load — the allocator recovered and the request returned 200**
  (vs S2's user-visible 500). Load-time transients remain a thing near the ceiling;
  they are confined to the attended pre-warm, never live traffic.
- (An earlier NVRM line at 18:14:05 was the keepalive's own fleet revival after the
  flock expired — not this migration's doing.)

Independent coach re-drive (window 18:21:13–18:25:37, kernel log **zero** events):

- Warm `gemma4-tutor`: 9.57 s / 150 tok @ **16.9 tok/s** (co-resident number).
- Warm `tutor-coach`: **2.58 s**, strict-JSON verdict, no fence — **~3.5× faster than
  the GB10's documented ~9 s**.
- STT exact (`{"text":""}` on silence, 2.0 s; verbatim round-trip transcript).
- **Full voice-turn shape STT→tutor→coach→TTS: 10.85 s total vs the 90 s budget.**
- `/running` identical before/after (nothing evicted); swap stable; co-tenants'
  `StartedAt` unchanged; ComfyUI answering. pocket-sync self-recovered at 16:38
  (healthy, restarts=0 — resolved outside this lane).
- **Flagged caveat (only refuted row, non-blocking):** under full co-tenancy
  qwen3-tts synthesizes at ~0.6–0.7× realtime — a 5 s-audio sentence takes 7–9 s
  wall (TTFB 4.5 ms, it streams). Fine for `/voice-turn`'s chunked delivery inside
  90 s; would matter only if TTS playback were ever streamed live.

**Box state left for S3:** tutor set warm (`gemma4-tutor`, `tutor-coach`, `embed`,
`parakeet-tdt-0.6b-v3`, `qwen3-tts-0.6b` all ready on `:9000`), ~107 GB used / ~13
available, **`llama-swap-keepalive.timer` STOPPED** (restart with `sudo systemctl
start llama-swap-keepalive.timer` — but doing so before the posture decision below
will evict the tutor pair within 5 min).

### S3 additions (operator, attended — beyond the .env flip above)

1. **Pre-warm in order while headroom is proven**, before flipping `.env`: audio pair
   → `tutor-coach` (17 GB) → `gemma4-tutor` (25 GB); check `free -g` + `/running`
   between each. Never let the first live user request trigger a 17 GB cold alloc —
   S2 proved that 500s.
2. ~~**Re-run the S2 gate** (coach-first order, quiet window) and require zero NVRM
   OOM before cutover.~~ **DONE 18:17–18:26 — PASS** (see the S2 re-run section
   above). The pre-warm is already in place; if the models get evicted before S3,
   repeat the coach-first pre-warm from that section.
3. **Decide spark's standing posture**: rotate preload+keepalive to the tutor set
   (GB10 R-G5 precedent) vs keep the wh/co/em fleet default — now entangled with the
   recruiter lane's workhorse/recruiter seats (D3). Until decided, the keepalive
   (resumes ~18:08) will revive wh/co and evict the tutor set every ≤5 min: pause the
   timer for any tutoring window (config comment's `systemctl stop
   llama-swap-keepalive.timer`, or the operator's flock idiom).
4. **Memory budget at cutover (measured)**: base (co-tenants + OS) ~53 + audio ~9 +
   tutor pair ~36 ≈ **98 GB**; a ComfyUI FLUX render (~20-25 GB) on top does NOT fit
   — schedule tutoring vs Study-Room renders, or accept the eviction rules.
5. Unrelated but observed 15:01–15:07: `pocket-sync-pocket-sync-1` crash-looping
   (config file not found, policy unless-stopped, 11 restarts) — not part of this
   migration, not touched.

**Rollback (rehearsed by audit):** restore
`/opt/llama-swap/config/config.yaml.bak-20260725-pre-study-tutor-audio` over
`config.yaml` (hot-reloads; the diff contains nothing but this migration), then
`curl :9000/unload` and let normal traffic reload. Scripts/mount/weights/images are
inert without the config entries.
