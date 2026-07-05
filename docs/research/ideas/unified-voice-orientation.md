# Unified Voice Orientation — one model set, one GB10, three consumers

**Status:** Discussion artifact — feeds an ADR-ARCH-024 revision (study-tutor) + ADR-POC-015 cross-ref (lpa-platform-poc). Decisions marked ⚖️ are Rich's.
**Date:** 2026-07-05. **Owner:** Rich.
**Sources:** [HF/Cerebras Gemma-4 voice post](https://huggingface.co/blog/cerebras-gemma4-voice-ai) + HF's "Reachy Mini goes fully local" follow-up recipe; `lpa-platform-poc` FEAT-POC-006 (merged, never live-smoked); study-tutor ADR-ARCH-024/026, contract §7, TASK-STREAM-001; `fleet-gateway/reachy/RUNBOOK-deploy-scholar-reachy-mini.md` (the live Scholar deployment).

---

## 1. The three consumers and where they stand

| Consumer | Mic mode | Today | Voice serving shape (target) |
|---|---|---|---|
| **Reachy Mini** ("Scholar") | **open mic** (VAD/endpointing needed) | DEPLOYED on the HF-hosted Realtime backend; profile + tools (`ask_jarvis`, `query_student_model`) route via NATS `:4222` → Jarvis on the GB10 | HF `speech-to-speech` pipeline ON the GB10 exposing OpenAI-Realtime-compatible `/v1/realtime`; robot's Realtime session re-pointed; Pi stays a thin audio client |
| **LPA platform** (FEAT-POC-006) | press-to-ask | Code built + merged (~200 tests) against `MockAudioTransport`; **real STT/TTS never stood up**; TASK-VOICE-011 live smoke deferred | Discrete OpenAI-compatible `/v1/audio/transcriptions` + `/v1/audio/speech`, plain REST |
| **Flutter tutor app** (phase 3) | tap-to-talk (OQ3) | Paper: D6 path *phone → WS → STT → `turn` → TTS*; TASK-STREAM-001 holds streaming; async Coach already cleared the pre-send path (ADR-ARCH-026) | Same discrete endpoints, orchestrated app-side around the tutor's own `turn` WS (contract §7 frames) |

**Key structural fact (from the Scholar runbook):** the robot's *tool plane* (`ask_jarvis` → NATS → Jarvis, `query_student_model`, Personality Studio profiles) is entirely separate from its *audio/LLM plane* (the HF Realtime session). Migrating voice locally swaps only the latter — profiles, tools, and NATS wiring survive untouched. The one open verification: whether `reachy_mini_conversation_app` exposes a backend-URL override as config (HF's fully-local post likely documents this) or needs a small patch.

## 2. Model pins (⚖️ ratify in one canonical record — kills the current three-way split-brain)

The current record disagrees with itself: LPA ADR-POC-015 says Parakeet TDT 1.1B, study-tutor ADR-ARCH-024 says `nemotron-speech-streaming-en-0.6b`, the LPA config default says `parakeet-tdt`, and the HF local recipe says `parakeet-tdt-0.6b-v3`.

- **STT: `parakeet-tdt-0.6b-v3`.** CC-BY-4.0, 25 European languages **including French** (dissolves study-tutor's licence-blocked French gap that the English-only nemotron pin couldn't serve), ~2GB, GB10-proven ARM64 container (`martinb78/dgx-spark-parakeet-asr`, OpenAI-compatible route). Trade-off accepted: no true word-by-word streaming ASR (VAD-chunked partials) — fine for tap-to-talk and press-to-ask; the s2s pipeline handles Reachy's open-mic VAD in-process (Silero v5). Nemotron returns to the table only if open-mic/barge-in ever lands on the *phone*.
- **TTS: Qwen3-TTS 0.6B** (Apache-2.0, `faster-qwen3-tts` GB10-proven container, TTFA <400ms with CUDA-graph serving). Reachy already *speaks* Qwen3-TTS via the HF backend — pinning it gives one consistent voice across robot, LPA, and tutor. **Kokoro-82M demotes to named fallback** (it was the prior cross-repo pin; LPA's `TTS_MODEL`/`TTS_VOICE` are env knobs, so the switch is config, not code). Caveats: needs a persistent (never-swapped) slot or first-utterance pays ~30s CUDA-graph capture; sentence-chunk at ~15–25 words for voice consistency.
- **LLM: Gemma 4 as deployed** (gemma4-tutor + tutor-coach set). Honesty note: the blog's snappiness came from Cerebras at ~1,851 tok/s; the GB10 decodes in low tens of tok/s — **the LLM is the latency wall**, which is why tutor voice needs TASK-STREAM-001 (token streaming → chunked TTS) rather than faster audio models.

## 3. Topology (⚖️)

- **One front door:** llama-swap already proxies `/v1/audio/transcriptions` and `/v1/audio/speech` — put the Parakeet and Qwen3-TTS containers in a **persistent, non-swapping group** (alongside embeddings; ~3–4GB total) behind `:9000`, Gemma swapping as today. This makes LPA's existing base-URL defaults (`http://promaxgb10-41b1:9000/v1`) **correct as-is**; the 9100/9200 earmarks become container-internal ports.
- **Reachy:** s2s server on the GB10 (its LLM stage pointed at llama-swap; STT/TTS in-process — ~4–6GB duplication is acceptable in 128GB, keep pins identical to avoid drift). Robot re-points its Realtime session; NATS tool plane untouched.
- **OQ2 (study-tutor voice transport) resolves to:** discrete STT/TTS routes + the tutor's own WS for `turn` streaming. `/v1/realtime` is Reachy's shape, not the household standard.
- **aarch64 traps:** speaches' CUDA image is broken on DGX Spark; CTranslate2 wheels are CPU-only on ARM; s2s Qwen3-TTS wheels default cu128 vs the GB10's CUDA 13 (install cu130 wheels first). Pin the two community container digests and vendor their Dockerfiles (single-maintainer artifacts). Mirror all llama-swap config into the dgx-spark repo (standing note).

## 4. Sequencing

1. **Ratify pins** (this doc → ADR-ARCH-024 revision + ADR-POC-015 cross-ref; also fixes LPA's runbook naming Parakeet 1.1B).
2. **Stand up the endpoints once** on the GB10 (`lpa-platform-poc` RUNBOOK-gb10-voice-endpoints.md is the vehicle — update to the unified pins first; persistent llama-swap group; CUDA-graph warm-up in the healthcheck).
3. **LPA live smoke first** (TASK-VOICE-011) — code already built, cheapest live validation of the endpoints. Pre-smoke fixes: placeholder `cdn.example.com` narration URL, unenforced 60s duration cap, webm/opus multipart acceptance check; base-URL defaults become correct under the front-door topology. UI note: with the Lovable/React integration now at phase 5, browser voice capture belongs in the React frontend (MediaRecorder → `POST /api/v1/voice/query`), not resurrected HTMX templates — smoke via curl first, decide UI home second.
4. **Reachy local migration** — re-point the Realtime session at the GB10 s2s server; verify open-mic latency and that `ask_jarvis`/tools still fire; this also closes the residency exception (minor's voice currently transits HF's cloud, which ADR-ARCH-024 D3 forbids for tutoring use).
5. **Flutter tutor voice** (phase 3) rides proven endpoints: TASK-STREAM-001 (server `generate_stream`, transport aligned with OQ2, coordinated BINDING_SHA re-freeze, streaming contract-suite variants), sentence-chunked TTS. Open design question with no answer yet: the quote-verification handover under streaming (verify-then-stream latency vs stream-then-annotate speaking an unverified quote).

## 5. Standing risks (condensed from the survey; full lists in the session record)

- **GPU multi-tenancy is real** (phase-2 wave-7 attempts 3–4: the LPA docling/VLM workload degraded tutor turns to >60s). Persistent audio group + quiet-GPU discipline for demos; an eviction-priority story eventually.
- **LPA's audio contract is pinned only by mocks** — first live call is where multipart field names, webm/opus acceptance, and response shapes get proven (the feature's own retro: "green but broken" once already).
- **Single-process assumptions in LPA voice** (in-memory cache, BackgroundTask jobs) — fine for the POC, a redesign item before any multi-worker deployment.
- **Community containers are single-maintainer** — pin digests, vendor Dockerfiles.
- **Both study-tutor voice ADRs are still Proposed** — ratification is step 1 for a reason.
- Mac-side housekeeping: the Mac's `lpa-platform-poc` clone has a dead remote (`FinProxy/lpa-platform-poc` not found — repo renamed/moved?) and is stale.

---

*Compiled 2026-07-05 from the three-source survey (LPA voice implementation read, study-tutor voice-groundwork read, self-hosting research) plus the Scholar runbook facts. Supersedes the informal chat-only orientation; next artifact is the ADR revision.*
