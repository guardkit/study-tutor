# HANDOFF — Move study-tutor inference from GB10 to spark-fcf6

**Status:** DRAFT 2026-07-25 · authored by the GB10 coordinator session, for a Claude
session running **on spark-fcf6**. Method:
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
Bearer `token-alex`) returns 200 with transcript + audio chunk. Then the phone
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
