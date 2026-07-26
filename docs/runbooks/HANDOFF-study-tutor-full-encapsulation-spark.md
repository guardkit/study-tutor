# HANDOFF — Encapsulate ALL study-tutor components on spark-fcf6

**Status:** SPARK SIDE COMPLETE 2026-07-26 — `:8100` live+smoked (09:59 UTC),
**`:8101` keycloak-mode live** (14:47 UTC: healthy, 401 enforcement, NAS OIDC
discovery 200 via the pinned host), **standing posture rotated and gated PASS**
(14:44–14:52 UTC: tutor-set preload coach-first, keepalive allowlist rotated and
self-healing — its first cycle revived the set, next cycle "nothing to revive";
recruiter-8b co-resides without evicting the pair, +5 GB). Remaining items are
operator-side: see the **Operator command block** below (GB10 retirement + memory
handback, fleet-gateway re-point, KC APK). Evidence at the end. Authored by the spark session that ran S0–S2 of
[HANDOFF-spark-inference-migration.md](HANDOFF-spark-inference-migration.md).
**Goal:** the Dell ProMax GB10 goes 100% software-factory (4-day PO dataset
generation planned for the week of 2026-07-27); everything study-tutor serves from
spark-fcf6. Supersedes the earlier plan's S3 "`.env` flip pointing GB10→spark" —
once the app containers themselves run on spark, the compose defaults
(`host.docker.internal:9000`) become correct again and no cross-box model traffic
remains.

## The actual component map (surveyed 2026-07-26)

Much less moves than it sounds. **All durable state is on the NAS and never moves.**

| Component | Today | After | Action |
|---|---|---|---|
| Inference (gemma4-tutor, tutor-coach, embed, parakeet, qwen3-tts) | spark `:9000` (S0–S2 ✅ 2026-07-25) | spark | none — done |
| ComfyUI Study-Room renders (`cr0-comfyui`) | spark `:8188` | spark | none |
| StudentStore Postgres `:5434` (lilymay's real state) + nightly `backup.sh` + Hyper Backup | NAS whitestocks `100.92.74.2` | NAS | none — verified reachable from spark (TCP open 2026-07-26) |
| Keycloak `:8443` (issuer `https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor`) | NAS | NAS | none — OIDC discovery answers 200 from spark (2026-07-26) |
| `study_tutor_http` `:8100` (table-mode, voice ON) — **stateless** | GB10 | **spark** | recreate compose project |
| `study_tutor_http_kc` `:8101` (keycloak-mode, voice off) — **stateless** | GB10 | **spark** | recreate overlay project |
| `deploy/http/.env` + `.env.kc` (gitignored, only real copies) | GB10 | **spark** | **scp GB10→spark** (the one push; spark→GB10 ssh is not authorized) + edits below |
| Phone APKs (compile-time `API_BASE_URL`) | point at GB10 | point at spark | **rebuild + reinstall** |
| Reachy s2s `:8765` (FEAT-VOICE-004) | GB10 | GB10 (fenced, separate lane) | only re-point fleet-gateway's `ask_tutor`/student-model URL → spark `:8100` (config lives in the fleet-gateway repo) |
| QAV shadow (`.guardkit/config.yaml` → `localhost:9000`, model `qav-shadow`) | runs wherever guardkit/autobuild runs (GB10 factory) | unchanged | none — factory-side, hits the factory box's own llama-swap |
| GB10 llama-swap tutor preload + audio containers | GB10 (R-G5 posture) | retire after soak | **frees ~50 GB for the PO dataset gen** — see Phase D |

Spark readiness (probed 2026-07-26): ports 8100/8101/5432/8080/8443 free; docker
compose v5.0.2; 2.9 TB disk; no conflicting networks/volumes; UFW inactive (prefer
127.0.0.1 binds for anything internal — tailnet-wide exposure otherwise).

## Phase A — spark prep (no GB10 involvement) — DONE by this session except build

1. ✅ `nats-core` cloned beside `study-tutor` (the compose build uses the repos'
   common parent as context + a BuildKit named context to `../nats-core`).
2. ✅ NAS reachability from spark: PG `100.92.74.2:5434` TCP-open; Keycloak
   `:8443` OIDC discovery HTTP 200.
3. ⚠️ `study-tutor:latest` image build on spark (equivalent to the compose build):
   `cd ~/Projects/appmilla_github && docker buildx build -f study-tutor/Dockerfile
   --build-context nats-core=./nats-core -t study-tutor:latest .`
   **BLOCKED on Phase B**: the Dockerfile `COPY study-tutor/data/ ./data/` requires
   the repo's `data/` directory, which is **entirely untracked** (0 files in git) —
   it exists only on the GB10 checkout and must come across in the Phase B push.
   All other build inputs verified present on spark (src/ 85 tracked, roles/ 4,
   pyproject+uv.lock, nats-core sibling).
4. `study-tutor:kc-a2` for `:8101` = same build, different tag (build once, retag:
   `docker tag study-tutor:latest study-tutor:kc-a2` at Phase C6 time, preserving
   the two-image isolation convention).

## Phase B — the one GB10-side push (operator or GB10 session, ~2 min)

From the GB10:

```bash
scp ~/Projects/appmilla_github/study-tutor/deploy/http/.env \
    ~/Projects/appmilla_github/study-tutor/deploy/http/.env.kc \
    spark-fcf6:~/Projects/appmilla_github/study-tutor/deploy/http/
# data/ is untracked (curriculum/knowledge content the image build COPYs):
rsync -a ~/Projects/appmilla_github/study-tutor/data/ \
    spark-fcf6:~/Projects/appmilla_github/study-tutor/data/
```

After the push, complete the Phase A image build on spark (A3), then `docker tag
study-tutor:latest study-tutor:kc-a2` when Phase C6 needs it.

Then **edit both files on spark** (the values that implicitly meant "the GB10"):

- **Delete / comment the five cross-box overrides** if present
  (`TUTOR_OPENAI_BASE_URL`, `TUTOR_COACH_ENDPOINT`, `TUTOR_LLM_BASE_URL`,
  `STT_BASE_URL`, `TTS_BASE_URL` pointing at any `100.84.90.91` /
  `host.docker.internal` GB10 meaning): on spark the compose defaults
  `http://host.docker.internal:9000(/v1)` resolve to **spark's own llama-swap** —
  correct.
- **EXCEPT voice — set explicitly** (the code fallback is the GB10 hostname
  `promaxgb10-41b1`, which resolves to 127.0.0.1 inside compose):
  `STT_BASE_URL=http://host.docker.internal:9000/v1` and
  `TTS_BASE_URL=http://host.docker.internal:9000/v1`.
- **Keep `TUTOR_COACH_MODEL=tutor-coach`** (compose default is `qwen36-workhorse`,
  which on spark aliases the factory workhorse — wrong model AND a matrix-set
  switch that would evict the tutor pair).
- Keep unchanged: `STUDY_TUTOR_PG_DSN` (NAS — works identically from spark),
  `STUDY_TUTOR_HTTP_TOKENS`, `STUDY_TUTOR_VOICE_ENABLED=true` (`:8100` only),
  the `.env.kc` OIDC issuer/audience (NAS-pinned; the checked-in overlay's
  `extra_hosts` 100.92.74.2 pin carries over as-is).
- `chmod 600` both files.

## Phase C — cutover (attended; parallel-run is safe — state is NAS-side)

1. Spark: `cd deploy/http && docker compose up -d` → `curl :8100/healthz` → `ok`.
   (No `seed-students` — the NAS DB is live and seeded; that step is for fresh DBs.)
2. Smoke **as alex, never lilymay**: text turn, then the voice-turn curl
   (POST `/api/sessions/{id}/voice-turn`, form field `audio`, `Bearer token-alex`)
   → 200 with transcript + audio chunk.
3. Rebuild the table-mode APK with
   `--dart-define=API_BASE_URL=http://spark-fcf6.tailebf801.ts.net:8100`
   (phones resolve MagicDNS — prefer the name over `100.105.247.62` so a future
   re-home is a DNS story), reinstall, tap-to-talk test.
4. GB10: `docker compose -p study_tutor_http down` (the old `:8100`). Rollback at
   any point = phone re-points at the GB10 build / restart the GB10 container —
   both instances share the same NAS state, so nothing forks.
5. Re-point fleet-gateway's `ask_tutor` + student-model URL (Reachy lane, config in
   the fleet-gateway repo on its own box) from GB10 `:8100` → spark `:8100`; same
   static bearer (table mode preserved for the robot, FEAT-AUTH-004 unchanged).
6. `:8101` keycloak overlay on spark, same pattern (tag `kc-a2`, `--env-file
   .env.kc`, `-p study_tutor_http_kc`); KC smoke; rebuild the KC APK
   (`API_BASE_URL=http://spark-fcf6.tailebf801.ts.net:8101`, same
   `KEYCLOAK_ISSUER` — unchanged, NAS); then GB10 kc project down. Voice-on-kc
   stays the later `.env.kc` flip per the original handoff.

## Phase D — free the GB10 (the actual point) + spark posture

1. **GB10** (operator): after `:8100`/`:8101` are down and spark has soaked, retire
   the GB10's study-tutor inference residency: rotate its llama-swap preload off
   the R-G5 tutor posture and drop the audio pair from preload (audio containers
   have `Restart=no` — they die at next stop and stay down). **~50 GB back for the
   factory / PO dataset generation.** qav-* models stay (factory's own consumers).
2. **Spark posture (recommendation, needs operator sign-off):** make `tutor` the
   standing set — preload `parakeet-tdt-0.6b-v3, qwen3-tts-0.6b, tutor-coach,
   gemma4-tutor, embed` (audio first, coach before tutor — the S2 lesson) and
   rotate the keepalive allowlist to match (R-G5 pattern). Optionally add `rc`/`r8`
   to the `tutor` set so recruiter exams co-reside (~7 GB) instead of evicting the
   pair. Until this is decided the keepalive timer stays STOPPED (it currently is;
   restarting it as-is evicts the tutor pair within 5 min).
3. Memory law (measured 2026-07-25): base ~53 + audio ~9 + tutor pair ~36 ≈ 98 GB;
   a concurrent FLUX render (~20–25 GB) does **not** fit — schedule Study-Room
   renders vs tutoring windows, or accept the documented eviction behaviour.

## Operator command block (the remaining GB10/robot-side steps, 2026-07-26)

**1. GB10: retire the study-tutor app containers** (spark `:8100` is live+smoked;
`:8101` stood up on spark 2026-07-26 — do this once the phone builds point at spark):

```bash
cd ~/Projects/appmilla_github/study-tutor/deploy/http
docker compose -p study_tutor_http down            # old :8100
docker compose -p study_tutor_http_kc down          # old :8101
```

**2. GB10: hand the factory its memory back** (~50 GB — do before the PO dataset
generation). Edit `/opt/llama-swap/config/config.yaml` on the GB10 (backup first:
`cp config.yaml config.yaml.bak-$(date +%Y%m%d)-post-tutor-migration`):

- `hooks.on_startup.preload`: remove `parakeet-tdt-0.6b-v3`, `qwen3-tts-0.6b`,
  `gemma4-tutor`, `tutor-coach` (keep `embed` if other consumers use it); restore
  the factory family per the R-G5-era comments.
- Keepalive allowlist (`/usr/local/bin/llama-swap-keepalive.sh`
  `MODEL_PROBE_KIND`): mirror the new preload.
- Then `curl localhost:9000/unload` and let the factory's first requests (or
  preload after a service restart) load its own set. The audio containers have
  `Restart=no` — they stay down once stopped. Keep the model entries registered
  (rollback = re-add to preload).
- Leave `qav-*` and everything else untouched.

**3. Fleet-gateway (Reachy lane): re-point the tutor URL.** In the fleet-gateway
config (its own repo/box), change the `ask_tutor` / student-model base URL from
the GB10 `:8100` to `http://100.105.247.62:8100` (or the spark ts.net name if the
gateway host resolves MagicDNS). Same static bearer — spark `:8100` runs the same
table-token mode. Smoke: one `ask_tutor` call from the robot path.

**4. MacBook: KC-flavour APK** (when `:8101` cutover matters):
`--dart-define=API_BASE_URL=http://spark-fcf6.tailebf801.ts.net:8101` with the
unchanged `KEYCLOAK_ISSUER` (NAS). Voice on `:8101` is still deliberately OFF —
enable later via `STUDY_TUTOR_VOICE_ENABLED` + STT/TTS URLs in spark's `.env.kc`
once the KC phone flow is proven.

## Decisions needed from the operator

1. Approve the spark standing-posture rotation (D2) — entangled with recruiter-lane
   scheduling.
2. APK URL: ts.net hostname (recommended) vs tailnet IP; which devices get rebuilt
   (table-mode certainly; KC build at C6 time).
3. Fleet-gateway re-point timing (robot lane owner).
4. GB10 posture rotation timing (D1) — before or after the PO dataset gen starts.

## Evidence — Phases A–C2 executed 2026-07-26 (spark session)

- **Phase B push received 09:55**: `deploy/http/.env` (1,087 B), `.env.kc` (727 B),
  `data/` (6.4 MB incl. `data/chroma/`). **Zero env edits were needed** — the GB10's
  `.env` already used `host.docker.internal:9000` semantics (the old cross-box S3
  flip was never applied), which on spark now points at spark's own llama-swap;
  `TUTOR_COACH_MODEL=tutor-coach` and the voice STT/TTS overrides carry over
  verbatim. `chmod 600` applied to `.env`.
- **Image built on spark**: `study-tutor:latest` `sha256:21ad7bb9…` (first attempt
  failed on the then-missing untracked `data/` — now a documented Phase B item).
- **Pre-warm (documented order, 84 GB headroom, keepalive still stopped)**: audio
  pair → `tutor-coach` cold 19.7 s → `gemma4-tutor` cold 18.5 s; **zero kernel
  NVRM/OOM lines**; end state 84 GB used / 37 available, four models ready.
- **`docker compose up -d`**: `study_tutor_http` healthy in ~12 s; `/healthz`
  `{"status":"ok"}` on loopback AND on `100.105.247.62:8100` (the phone target).
- **Independent smoke as alex — PASS** (workflow coach, window 09:59–10:01 UTC):
  session start 0.205 s; text turn 3.835 s (caught the mitochondria misconception;
  async coach fired `decision=revise` in logs — log-only by design); voice turn
  **18.66 s vs the 90 s budget** with a character-exact transcript of the coach's
  own synthesized question and a valid 1.39 MB WAV reply chunk; session persisted
  to the NAS (`turn_count=2`); zero container restarts, zero kernel OOM, zero app
  tracebacks; models stayed resident throughout.
- **Observation (pre-existing, not a regression)**: boot logs
  `event=rag_disabled reason=chromadb_missing` — the image has no `[rag]` extra, so
  the pushed `data/chroma/` store is unused. Same Dockerfile as the GB10 build, so
  behaviour is unchanged; installing the extra is a separate decision if RAG
  retrieval should be live.

## Explicitly out of scope

- NAS anything (Postgres, Keycloak, backups, certs) — untouched, verified reachable.
- Reachy s2s `:8765` itself — stays on the GB10 per FEAT-VOICE-004.
- QAV shadow — factory-side GuardKit config, moves with the factory, not with study-tutor.
