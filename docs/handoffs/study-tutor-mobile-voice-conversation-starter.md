# study-tutor mobile + voice client — Conversation Starter
## For: /goal → planning session · study-tutor · July 2026

---

## Purpose of this document

Context brief for the planning session (attended, frontier model per DF-003) that turns this into architecture and a build plan for a **mobile (and bonus web) client** for study-tutor. Paste at the start of the `/goal` session, then run down the pipeline (`/system-arch` → `/system-design` → `/feature-spec` → `/feature-plan` → AutoBuild).

Everything below marked **resolved** is a constraint — do not reopen in planning. Open questions are flagged separately.

---

## What is this?

A voice-first mobile client for the study-tutor, sharing the Reachy robot's voice backend, so the real user can hold study sessions on the phone **and** the robot and move between them mid-thread.

**Real-user driver:** [daughter] used OpenWebUI on her phone and asked to pick up study sessions from her phone and/or the Reachy Mini robot. That request is the spec.

**Strategic role:** this slice is **Act 2 — production observability** from the transition strategy (the "one real gap"): the tangible, real-user surface for a deployed, instrumented system. The app is how it's *seen*; the serving story is what makes it *count* (see Production framing below).

---

## Key decisions (resolved — do not reopen)

| # | Decision | Resolution |
|---|---|---|
| D1 | Cross-platform framework | **Flutter**, not Compose Multiplatform |
| D2 | Why Flutter | (a) **audio-I/O maturity** — real-time mic streaming, low-latency playback, echo cancellation, VAD are the riskiest surface in a voice-first app and Flutter's plugin ecosystem is more mature; (b) **lower-hallucination substrate** for AI-assisted build — KMP/CMP is still a higher-risk domain for confident-but-wrong model output (thin, fast-moving corpus around exactly the target/library boundaries); (c) **web is a bonus** and Flutter's web target is further along than CMP's beta |
| D3 | Accepted costs of D1 | Gives up Kotlin-domain reuse and the *cleanest* on-device-Gemma path (still doable via the younger LiteRT-LM Flutter binding — phase 2) |
| D4 | Client role | **Thin real-time client.** Voice + tutor LLM live on the GB10; the phone streams audio, it does **not** run the model on-device (MVP) |
| D5 | Voice backend | The **same GB10 endpoints as the Reachy bridge** — STT (:9100) + Kokoro TTS (:9200). Single source of truth for both clients. STT model pinned to `nemotron-speech-streaming-en-0.6b` (cache-aware streaming) by [ADR-ARCH-024](../architecture/decisions/ADR-ARCH-024-voice-stt-cache-aware-streaming-multilingual-deferred.md) — multilingual/French deferred there |
| D6 | Voice path | phone → WebSocket → STT → study-tutor `turn` → TTS → stream back. **No MCP in the loop** |
| D7 | Interface to study-tutor | The app hits study-tutor's **HTTP/WS adapter directly** (per ADR-FLEET-003) — not MCP, not via jarvis |
| D8 | Session model | Sessions keyed to the **student**, resumable across devices; both clients authenticate as the same student. This is what enables phone ↔ robot pickup |
| D9 | Auth | Keycloak (already in the deployment plan) fronts the HTTP/WS API |

---

## Hard dependencies (gates)

| Gate | What | Why it blocks |
|---|---|---|
| **FEAT-1773** | study-tutor student persistence layer (Pydantic entities, async write-back, query helpers) | **Cross-device pickup is impossible without it** — nothing to resume. This is the feature the real user actually asked for. Already gates the session planner (FEAT-PH1-002) and Player-Coach loop (FEAT-PH1-003) |
| **GB10 voice endpoints** | STT :9100 (`nemotron-speech-streaming-en-0.6b`, ADR-ARCH-024) / Kokoro :9200 | Don't exist yet — ADR-POC-015 + `RUNBOOK-gb10-voice-endpoints.md` written, not provisioned. Gate FEAT-POC-006. Build **once** as single source of truth, ideally behind a streaming/Realtime-shaped interface so the Reachy/Pollen patterns and the phone share transport. Building them **also unblocks the robot's local-voice migration** |

## Sequencing

1. **GB10 voice endpoints** — also unblocks Reachy.
2. **FEAT-1773 persistence** — unblocks pickup + session planner + Player-Coach.
3. **study-tutor HTTP/WS adapter** — session contract mirrors the MCP verbs (ADR-FLEET-003).
4. **Flutter thin client** — voice + chat, instrumented for metrics.

---

## Phase 2 (keep-warm, not MVP)

**On-device small Gemma 4 (E2B/E4B, LiteRT-LM) as an offline fallback tutor** — for when the phone is off Tailscale and can't reach the Spark. Same Gemma family as the served model; a LoRA could be emitted from the **same dataset-factory corpus** that trains the big one (LiteRT-LM supports LoRA). Offline resilience is the phone's genuine on-device use case — the robot is always home/on-network; the phone isn't. **Explicitly deferred** per "subtract, don't add"; recorded so it isn't lost. (Could alternatively live in the mission doc's "keep-warm, not central" bucket.)

---

## Production framing (why this matters — carry into planning)

This slice earns its keep as **evidence of the serving spine**, not as a component count.

- **Instrument for:** cost-per-session (and per-token), latency distribution, reliability over weeks, and **GB10-vs-cloud economics**. That is the Act 2 / Act 4 proof. Deploy target AWS/Vertex, but **lead with the own portable serving stack** (llama-swap/vLLM lifted from GB10 to a cloud GPU) over a managed endpoint — managed is the "I know the enterprise path too" footnote, self-hosted is the depth.
- **Minor-data-by-design** (a production decision worth making explicit): the real user is a minor; the system does voice + auth + stores study data. Data minimisation, persistence on owned hardware, her data off third-party APIs — DF-001 already gets most of the way; naming it as a design principle is a strong, defensible production narrative.

---

## Open questions for planning to resolve

1. **Web app scope** — authenticated student tool only, or also a public-facing site? Changes little for Flutter (web is a bonus), but decides whether any public/SEO surface is needed — which would be plain HTML, done separately.
2. **Voice transport shape** — a single Realtime-style conversation WebSocket vs separate STT/TTS endpoints. Decide when building the GB10 endpoints. *(The STT-model half of this question is resolved by [ADR-ARCH-024](../architecture/decisions/ADR-ARCH-024-voice-stt-cache-aware-streaming-multilingual-deferred.md); only the transport shape remains open.)*
3. **Interaction mode** — tap-to-talk vs open-mic / barge-in. Tap-to-talk is simpler, acceptable for a student app, and substantially narrows the acoustic-echo problem. **Recommended MVP default: tap-to-talk.**
4. **Session-contract detail** — the exact HTTP/WS shape mirroring `start/turn/status/end`, streaming semantics for `turn`, and how session identity binds to the Keycloak subject.

---

## Related documents

- **ADR-FLEET-003** — agent capability exposure: MCP for agent-hosts, HTTP/WS for app clients (the interface boundary this build sits on)
- **[ADR-ARCH-024](../architecture/decisions/ADR-ARCH-024-voice-stt-cache-aware-streaming-multilingual-deferred.md)** — STT model selection (cache-aware streaming; multilingual deferred) for the shared voice endpoints
- **ADR-POC-015** + `RUNBOOK-gb10-voice-endpoints.md` — GB10 voice endpoint provisioning (shared cascade + endpoint contract)
- study-tutor `.guardkit/features/` — FEAT-1773, FEAT-PH1-002, FEAT-PH1-003, FEAT-POC-006
- Transition strategy §4 (differentiation) / mission arc Act 2 & Act 4 — the strategic frame for instrumenting this slice

---

## Key insight to carry forward

**The unifier is the backend, not the device.** Because voice, STT, TTS and the tutor LLM all live on the GB10, the phone, the web app and the robot are three thin clients over one pipeline. "Same voice backend as the robot" means shared *server*, not shared client code — and it means on-device AI is an *offline* concern (phase 2), not what makes the phone work.

---

*Prepared: 2 July 2026 | study-tutor mobile + voice client planning*
*Use as context for /goal and the downstream pipeline*
