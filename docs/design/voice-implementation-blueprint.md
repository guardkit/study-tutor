# Voice implementation blueprint — building tutor voice on the proven LPA stack

**Date:** 2026-07-05 · **Status:** Blueprint (feeds `/feature-spec` for tutor voice)
**Based on:** `lpa-platform-poc` FEAT-POC-006, live-smoked end-to-end 2026-07-05
(TASK-VOICE-011 complete, browser UI included). The shared GB10 endpoints this
blueprint consumes are **already live** — nothing in §2 needs building.
**Authority for pins/topology:** `docs/research/ideas/unified-voice-orientation.md`
(ratified) + [ADR-ARCH-024](../architecture/decisions/ADR-ARCH-024-voice-stt-cache-aware-streaming-multilingual-deferred.md)
Revision 1 + `lpa-platform-poc` ADR-POC-015 Revision 1. Do not re-open pins here.

---

## 1. What this document is

The LPA platform built, tested and live-proved a complete voice feature against
the shared GB10 audio endpoints: press-to-ask capture in the browser, STT,
narrated answers via TTS, audit discipline, graceful degradation, and an
operator-handoff live smoke. study-tutor's voice slice (conversation-starter
D4–D6: thin Flutter client, tap-to-talk, phone → adapter → STT → `turn` → TTS)
rides the same endpoints and can lift most of that implementation's shape,
tests and operational knowledge wholesale. This blueprint maps exactly what to
reuse, what differs (one thing, fundamentally: **the tutor LLM is in the voice
loop**), and the phase/gate order to build it in.

## 2. Already done — consume, don't rebuild

| What | State | Record |
|---|---|---|
| STT `parakeet-tdt-0.6b-v3` (alias `parakeet-tdt`) | **Live** behind llama-swap `http://promaxgb10-41b1:9000/v1`, persistent (`ttl: 0`, every matrix set, audio-first preload) | `lpa-platform-poc/docs/runbooks/RUNBOOK-gb10-voice-unified-2026-07.md` + its RESULTS |
| TTS `qwen3-tts-0.6b` CustomVoice (aliases `qwen3-tts`, `tts-1`; English voices `Ryan` [fleet pin], `Aiden`) | **Live**, same topology; health endpoint patched to 503-until-CUDA-graph-warmup | same runbook/RESULTS; patched server + digest-pinned launch scripts mirrored in `dgx-spark` repo (`vendor/`, `scripts/audio-*.sh`, commit `568af53`) |
| Endpoint smoke evidence (latency, formats, degradation, no-cloud proof) | Captured | `lpa-platform-poc/docs/runbooks/evidence/gb10-voice-endpoints/` |
| The `:9100`/`:9200` standalone plan | **Dead** — do not resurrect | ADR-ARCH-024 r1 / ADR-POC-015 r1 |

**The realised endpoint contract** (verified live 2026-07-05):

- `POST {base}/v1/audio/transcriptions` — multipart: `file` (required; wav,
  webm/opus, ogg/opus, mp3 all proven), `model` (accepted and ignored — send
  `parakeet-tdt`), `language` (optional, default auto), `response_format`
  (default `json` → `{"text": "..."}`). Output has punctuation + capitals.
- `POST {base}/v1/audio/speech` — JSON `{model, voice, input, response_format,
  speed}`. `response_format`: `wav` | `pcm` (stream during generation — use for
  low TTFA), `mp3` (encoded after generation — whole-file), `zip`
  (timestamps — **unavailable**: needs an HF-hosted aligner and the containers
  run `HF_HUB_OFFLINE=1`).
- `GET {base}/speakers` — voice list.
- Measured: STT warm **0.09–0.35 s** (short clip; up to ~1.4 s under full
  fleet co-residency), TTS whole-file mp3 **~1–2 s per sentence**; cold start
  after a crash/restart ~20 s each (pinned residency exists so users never
  see it). The upstream TTFA-<400 ms figure applies to `wav`/`pcm` streaming
  only — treat it as upstream's claim until we measure it in our shape.

## 3. Reference implementation — lift from `lpa-platform-poc`

The LPA voice module is the template. Copy the *shape* (and much of the code)
of these files; every one is exercised by ~230 passing tests there:

| LPA file (`lpa-platform-poc/`) | Take for study-tutor | Adaptation |
|---|---|---|
| `src/voice/config.py` | Env-driven `VoiceSettings`: `stt_base_url`, `stt_model`, `tts_base_url`, `tts_model`, `tts_voice`, `max_query_seconds` (60), `max_recording_bytes` (10 MB), supported-MIME sets | Defaults are already correct for the GB10; only `TTS_VOICE=Ryan`, `TTS_MODEL=qwen3-tts` differ from its historical Kokoro defaults |
| `src/voice/clients/audio.py` | `AudioClient` — thin httpx wrapper, injectable `transport` for tests, raises domain `VoiceUnavailable` on failure | Keep verbatim shape; it is provider-agnostic OpenAI-audio |
| `src/voice/exceptions.py` | Closed-set voice errors: 413 `query_too_long` / `recording_too_large`, 415 `unsupported_audio_format`, 422 empty/unintelligible, 503 `voice_unavailable` | **Map into the tutor's flat `{"error", "error_type"}` envelope** (binding §4) — do not import the LPA's `{error_code, message}` body shape |
| `src/voice/utils.py` | Stdlib WebM/Ogg duration probe (EBML walk + Ogg granulepos) enforcing the 60 s cap server-side where derivable | Phone uploads may be AAC/m4a — extend or rely on the byte cap + client-side stop (see §6) |
| `src/voice/router.py` → `validate_audio_upload` | Upload validation: byte cap, **base-MIME matching** (codec params vary by client — exact-string matching 415s real recorders), emptiness, best-effort duration | Same logic, tutor route |
| `tests/voice/*`, `tests/integration/test_voice_integration.py`, `tests/voice/audio_samples.py` | The whole testing pattern: synthetic WebM/Ogg builders, MIME-variant matrix, and **the multipart contract pinned at the httpx protocol seam** (captured MockTransport request asserts field name, filename, content-type incl. codec params, `model` field) | This is the defence against the LPA's own "green but broken" retro — port it, don't re-derive it |

What **not** to copy: the LPA's narration cache/`BackgroundTask` batch jobs
(single-process assumptions, flagged for redesign there) and its
donor/attorney authorization plumbing — the tutor has its own session auth.

## 4. The one fundamental difference: the LLM is in the loop

The LPA's voice path deliberately **never calls an LLM** — it narrates the
flag explanation already recorded, so its end-to-end warm latency is ~0.1 s +
~3 s narration. Tutor voice is the harder shape:

```
tap-to-talk audio ──► STT (:9000, ~0.1–0.4 s warm)
                          │ transcript
                          ▼
              tutor `turn` (Player LLM — THE latency wall;
              async Coach per ADR-ARCH-026 keeps it off the path)
                          │ tokens
                          ▼
        sentence-chunked TTS (~15–25 words/chunk, orientation §2)
                          │ audio chunks (wav/pcm streaming)
                          ▼
                    phone playback
```

Consequences, in decision order:

1. **Voice UX quality is gated on [TASK-STREAM-001](../../tasks/backlog/TASK-STREAM-001-tutor-turn-token-streaming.md)**
   (`generate_stream` + streaming transport), not on the audio models — they
   are already fast. Without token streaming, spoken answers wait for full
   generation. A non-streaming MVP (transcribe → full turn → single TTS call)
   is *acceptable to ship first* — async Coach already brought turns inside
   the 15 s deadline — but it must be framed as the stepping stone.
2. **Sentence-chunk the TTS on the token stream** (buffer ~15–25 words →
   `/v1/audio/speech` with `response_format=wav` → play chunks in order).
   One synthesis call per sentence keeps voice consistency and overlaps LLM
   generation with speech.
3. **The quote-verification handover under streaming is still an open design
   question** (verify-then-stream latency vs stream-then-annotate speaking an
   unverified quote — orientation §4.5). Decide it in the TASK-STREAM-001
   design pass; do not let voice silently decide it.
4. **Transport (OQ#2, resolved by ADR-ARCH-024 r1):** discrete STT/TTS routes
   + the tutor's own `turn` WebSocket. No `/v1/realtime` — that is Reachy's
   in-process s2s shape, not the household standard.

## 5. Server work (`src/study_tutor/`)

Add a `voice/` package mirroring the LPA layout (`config.py`, `client.py`,
`service.py`, `errors.py`), surfaced through the existing HTTP adapter
(`src/study_tutor/http/`). Proposed binding additions (contract change —
see freeze note below):

| Verb | Route | Request | Response |
|---|---|---|---|
| `voice_turn` | `POST /api/sessions/{session_id}/voice-turn` | multipart `audio` (+ the `stream?` semantics reserved in binding §2) | non-streaming: `{ transcript, tutor_response }`; streaming: the §7 WS/token-stream shape carrying `transcript` first, then tokens, then per-sentence audio refs |
| `voice_audio` (if chunk-by-URL rather than inline) | `GET /api/sessions/{session_id}/voice-audio/{chunk_id}` | — | `audio/wav` stream, bearer-authenticated |

Rules carried over from the LPA build (all proven live):

- **Auth:** bearer token, student derived server-side (binding §3) — the
  voice routes add no new identity surface.
- **Errors:** closed set only, in the tutor's `{"error", "error_type"}`
  envelope; voice adds `VoiceUnavailable` → 503, upload-validation errors →
  413/415/422. **Degradation is a feature with copy**, not an error path —
  the app shows "spoken answers unavailable, text still works" (LPA's amber
  notice) and the text `turn` is untouched.
- **Ephemeral audio (D3 — stronger here than in the LPA: the user is a
  minor):** inbound audio is transcribed and discarded; no audio bytes at
  rest anywhere (the LPA proof: zero `bytea` columns, disk scan clean);
  session history stores the transcript exactly as a typed turn; TTS output
  is streamed/cached in memory only.
- **BINDING_SHA discipline:** the voice routes + streaming shape are a
  binding change. Coordinate with the app side, re-freeze, bump the pinned
  SHA **once**, jointly with TASK-STREAM-001's transport work (binding §7 —
  don't pay the freeze cost twice).

## 6. Client work (Flutter `app/`)

- **Tap-to-talk** (conversation-starter OQ#3 resolution): press → record →
  press → send. No VAD/open-mic/barge-in in MVP; that is exactly the
  trade-off ADR-ARCH-024 r1 accepted when choosing Parakeet.
- **Record format:** phone-native AAC/m4a is fine to *try first* — the STT
  container transcodes via ffmpeg and accepted every format thrown at it
  (wav/webm/ogg/mp3) — but run the §8 Phase-0 discovery gate with a real
  m4a before freezing the app's recorder config. Opus-in-ogg is the proven
  fallback.
- **Client-side 60 s hard stop.** LPA lesson: streamed containers
  (Chrome WebM, likely phone streams too) omit duration headers, so the
  server can only best-effort the cap — the client stop is the real
  enforcement, the 10 MB byte cap the backstop.
- **Playback:** ordered queue of wav chunks (streaming path) or a single
  clip (MVP). Show the transcript as it arrives — it doubles as the
  user-visible confirmation the STT heard correctly (the LPA UI does this).
- **Acceptance:** extend the 35-assertion live contract suite
  (`app/test_live/`) with voice variants per TASK-STREAM-001 §Scope 4.
- **Web-target testing trick** (from the LPA browser E2E, reusable if the
  Flutter web bonus target is exercised): headless Chromium's
  `--use-fake-device-for-media-capture` yields **no audio input on the GB10**
  — shim `getUserMedia` with a WebAudio `MediaStreamDestination` playing a
  base64 WAV instead; recorder/upload/STT stay fully real. Reference script:
  LPA evidence addendum (browser-ui) + that repo's session notes.

## 7. Testing strategy (the "green but broken" defence)

The LPA feature passed ~200 mock tests and was still wrong at the seam in
three places (fake narration URL, unenforced cap, MIME exact-matching).
Adopt its post-mortem discipline from day one:

1. **Unit/feature tests on a mock transport** (`httpx.MockTransport`) — free
   to run everywhere, no GPU.
2. **Pin the wire contract at the protocol seam**: capture the mock request
   and assert multipart field names, filename, content-type (codec params
   intact), model field — not just "service was called".
3. **Live smoke as an `operator_handoff` task** (the TASK-VOICE-011 pattern —
   AutoBuild cannot provision or verify GPU serving). Write its ACs before
   building; suggested, mirroring AC-LIVE-01/02/03:
   - **AC-V1:** a spoken question tap-recorded on the real phone produces a
     correct transcript (live Parakeet) and an audible tutor answer (live
     Qwen3-TTS) in the app.
   - **AC-V2:** the session record and logs contain the transcript and **no
     raw audio** anywhere (DB + disk sweep).
   - **AC-V3:** with both audio models stopped *and their launch scripts
     disabled* (a bare `docker stop` self-heals — see §9), the app degrades
     to text with clean copy and **zero third-party calls** (connection
     sampling in the adapter container — method in the LPA evidence file).
4. **Objective intelligibility check:** round-trip TTS output back through
   the live STT and compare text — the LPA smoke used this to verify audio
   content without a human listener. Cheap and automatable.

## 8. Phased build with gates (runbook discipline)

Follow the phase/Pass-Fail-gate style of
`RUNBOOK-gb10-voice-unified-2026-07.md`; each phase ends with evidence.

- **Phase 0 — pre-flight (no code).** From the adapter host: `GET :9000/v1/models`
  lists both audio models; STT round-trips a known-text clip **including one
  in the Flutter recorder's actual output format (m4a test!)**; TTS
  `voice=Ryan` returns playable audio; `GET :9000/running` shows both `ready`.
  *Gate: all four pass; record timings.*
- **Phase 1 — server voice module against mocks.** Port §3's files; voice
  errors in the tutor envelope; contract-seam tests green; **non-streaming**
  `voice_turn` behind a feature flag.
  *Gate: full tutor suite green; seam tests pin the wire shape.*
- **Phase 2 — transport + streaming (joint with TASK-STREAM-001).** One
  BINDING_SHA re-freeze covering token streaming and voice; sentence-chunked
  TTS on the token stream; quote-handover decision recorded (ADR or
  ADR-ARCH-026 revision).
  *Gate: streaming contract-suite variants green against the dev deploy
  (`RUNBOOK-study-tutor-http-dev-deploy.md`).*
- **Phase 3 — Flutter tap-to-talk client.** Recorder + 60 s stop + upload +
  transcript display + chunked playback + degradation copy.
  *Gate: `app/test_live/` voice variants green on device against the GB10.*
- **Phase 4 — live smoke (operator handoff).** AC-V1..V3 above; evidence into
  `docs/runbooks/evidence/`; RESULTS file; task-complete.
  *Gate: ACs hold; RESULTS written.*

## 9. Operational knowledge you inherit (read before touching the GB10)

All from the standup RESULTS (`lpa-platform-poc/docs/runbooks/RESULTS-gb10-voice-unified-2026-07.md`) — condensed:

- **Memory is the constraint, not compute.** Steady state after the voice
  standup is ~116/121 GB with swap full. A *new* CUDA process can fail at
  context creation when the box is that full — this OOM'd the TTS first-load
  twice. The audio pair loads **first** in llama-swap's preload for exactly
  this reason. Don't add resident models without re-doing that arithmetic.
- **`GET :9000/unload` unloads EVERYTHING** (`?model=` is ignored). Never use
  it for one model.
- **`docker stop audio-*` self-heals** — llama-swap restarts the container on
  the next request (~20 s). For real outage testing, also disable
  `/opt/llama-swap/scripts/audio-*.sh`.
- **Quiet-GPU discipline:** don't run voice standup/smokes while an LPA
  extraction or tutor session is mid-flight (documented >60 s turn
  degradation under contention).
- **Keepalive timer** doesn't probe the audio models (no chat/embed probe
  shape); crash recovery is next-request reload. The timer itself was left
  inactive on 2026-07-05 — check `systemctl status llama-swap-keepalive.timer`
  before assuming the family self-revives.
- Config/scripts source of truth on the box: `/opt/llama-swap/config/config.yaml`
  (+ dated `.bak-*` before every edit); mirrored with vendored Dockerfiles in
  the `dgx-spark` repo.

## 10. Out of scope here

Reachy's local-voice migration (orientation §4.4 — s2s pipeline, `/v1/realtime`,
in-process VAD) and the phase-2 on-device Gemma fallback. Both ride the same
pins but are separate build items.

## 11. References

- `study-tutor/docs/research/ideas/unified-voice-orientation.md` — ratified pins + topology (canonical, with the dgx-spark config mirror)
- [ADR-ARCH-024 r1](../architecture/decisions/ADR-ARCH-024-voice-stt-cache-aware-streaming-multilingual-deferred.md) · ADR-ARCH-026 (async Coach) · [TASK-STREAM-001](../../tasks/backlog/TASK-STREAM-001-tutor-turn-token-streaming.md)
- [API-session-http-binding.md](contracts/API-session-http-binding.md) (§2 verbs, §3 auth, §4 errors, §7 freeze) · [conversation-starter](../handoffs/study-tutor-mobile-voice-conversation-starter.md) (D1–D9, OQ#3)
- `lpa-platform-poc`: ADR-POC-015 r1 · `docs/runbooks/RUNBOOK-gb10-voice-unified-2026-07.md` + `RESULTS-gb10-voice-unified-2026-07.md` + `evidence/gb10-voice-endpoints/` (incl. browser-ui E2E) · `src/voice/` + `tests/voice/` (reference implementation) · `tasks/completed/2026-07/TASK-VOICE-011-…` (the operator-handoff smoke template)
- `dgx-spark`: `vendor/README.md` (digests, upstream SHAs, health patch), `scripts/audio-parakeet.sh` / `audio-qwen3tts.sh`, `examples/llama-swap-config.gb10-live-2026-07-05-voice-unified.yaml`
