# ADR-ARCH-024 — Voice STT model: cache-aware streaming (English) on the shared GB10 endpoints; multilingual deferred pending a production-licensed model

## Status

Accepted — **as revised 2026-07-05** (Revision 1, below). The original D1
model pick and the D2 deferral are superseded together by the unified voice
pin `parakeet-tdt-0.6b-v3`; D3 (no cloud audio) and the shared-backend
posture stand, and are now implemented and live-verified on the GB10.

**Date:** 2026-07-03 · **Revised:** 2026-07-05
**Phase:** Mobile + Voice client (transition Act 2 — production observability)
**Related:** [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md) (on-device residency / minor-data-by-design), [ADR-ARCH-006](ADR-ARCH-006-dual-inference-path-ollama-bedrock.md) (env-var-driven model selection at the client factory), [ADR-ARCH-023](ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md) (removed the last cloud write-back exception), [ADR-ARCH-014](ADR-ARCH-014-single-user-scalability-posture.md) (single-user posture), the mobile + voice client conversation-starter (`docs/handoffs/study-tutor-mobile-voice-conversation-starter.md` — D5 shared backend, OQ#2 model/transport, OQ#3 tap-to-talk). **Cross-repo:** the shared GB10 voice cascade + OpenAI-compatible endpoint contract lives in `lpa-platform-poc/docs/poc/decisions/ADR-POC-015-voice-cascade-and-audio-endpoints.md` (+ its `RUNBOOK-gb10-voice-endpoints.md`); this ADR selects the STT **model** that runs behind those shared endpoints for study-tutor's use.

> **⚠️ Revision 1 (2026-07-05) — unified voice pins ratified and deployed;
> read alongside the original.** Two days after this ADR was proposed, the
> three-consumer survey (`docs/research/ideas/unified-voice-orientation.md`)
> found the fleet's voice record disagreeing with itself four ways and
> ratified one pin set, which was stood up and live-smoked on the GB10 the
> same day (`lpa-platform-poc` RUNBOOK/RESULTS-gb10-voice-unified-2026-07).
> What changes here:
>
> - **D1 superseded — STT is `parakeet-tdt-0.6b-v3`** (CC-BY-4.0, ~2 GB,
>   25 European languages **including French**, punctuation + caps,
>   GB10-proven ARM64 container). Alias `parakeet-tdt` behind the shared
>   endpoint; env-var swap discipline (ADR-ARCH-006 pattern) unchanged.
> - **D2 dissolved, not merely deferred.** The French gap that
>   `nemotron-3.5-asr-streaming-0.6b`'s licence blocked is closed by the
>   multilingual Parakeet under a production-usable licence. The watch-list
>   narrows to one trigger: **true cache-aware streaming / barge-in on the
>   phone.** Parakeet TDT is not cache-aware (VAD-chunked partials only) —
>   the trade-off D1 originally refused is now **accepted**, because the
>   validated interaction shapes (tap-to-talk on the phone per OQ#3;
>   press-to-ask in the LPA app) never stream word-by-word, and Reachy's
>   open-mic VAD runs in-process in its s2s pipeline (Silero v5), not in
>   the shared STT service. Nemotron (or a successor) returns to the table
>   only if open-mic/barge-in lands on the *phone* under a production
>   licence.
> - **D4's premise updated:** the shared TTS pin is now **Qwen3-TTS 0.6B
>   CustomVoice** (Apache-2.0, CUDA-graph serving); **Kokoro-82M demotes to
>   named fallback**. Still out of scope here; recorded in the
>   ADR-POC-015 revision + orientation doc §2.
> - **Topology/transport (closes OQ#2's remaining half):** the `:9100`/
>   `:9200` standalone earmarks are dead — both audio models run as a
>   persistent, never-evicted group **behind llama-swap on `gb10:9000`**
>   (discrete OpenAI-compatible `/v1/audio/*` routes). study-tutor voice
>   uses those discrete routes plus the tutor's own `turn` WebSocket
>   (contract §7); `/v1/realtime` is Reachy's shape, not the household
>   standard. Token streaming for tutor voice remains TASK-STREAM-001 —
>   the LLM, not the audio models, is the latency wall.
> - **The "open owner decision" (canonical record location) is resolved:**
>   pins are recorded once in the orientation doc + the live llama-swap
>   config mirror (`dgx-spark` repo, digest-pinned launch scripts +
>   vendored Dockerfiles); this ADR and ADR-POC-015 cross-reference it
>   rather than duplicating authority.
> - **D3 stands and is now evidence-backed:** the LPA live smoke proved
>   text-only degradation with zero third-party calls under a forced
>   outage; both containers run with `HF_HUB_OFFLINE=1`.

## Context

The mobile + voice client conversation-starter fixes the voice backend as **shared GB10 endpoints** — one STT service (`:9100`) and one TTS service (`:9200`) — as the single source of truth for both the Reachy Mini robot and the Flutter phone client (**D5**, resolved). That shared-backend decision is **not reopened here**. What the conversation-starter explicitly left open (**OQ#2**) is the STT *model* and transport shape, "decide when building the GB10 endpoints." This ADR resolves the **model** half of OQ#2 for study-tutor; transport shape (a single Realtime-style WebSocket vs discrete STT/TTS routes) stays open — that is an endpoint-interface decision, not a model one.

The endpoint provisioning, cascade architecture, and OpenAI-compatible route contract already exist in `lpa-platform-poc` ADR-POC-015 — authored there because the LPA voice feature drove the provisioning runbook first, but the endpoints are shared infrastructure. That ADR names **Parakeet TDT** as the STT model and describes it as "streaming." Two things make that insufficient for study-tutor:

1. **The "streaming" characterisation is imprecise.** Plain Parakeet TDT runs buffered/chunked streaming — it recomputes left context per chunk — rather than *cache-aware* streaming. For an interactive tap-to-talk loop (OQ#3's recommended MVP), and any later barge-in, a cache-aware model gives lower and tunable end-to-end latency for the same footprint.
2. **study-tutor's STT requirements are a superset of the LPA POC's.** The LPA POC is UK-English-only. study-tutor is validated across Maths, Biology, and **French** — a French session means the student *speaks* French, which an English-only recogniser mis-transcribes. Multilingual STT is therefore a genuine study-tutor requirement with no analogue in the financial POC, and must be decided here.

Trigger: a review of whether NVIDIA's newest streaming ASR — `nemotron-3.5-asr-streaming-0.6b` (40-locale, cache-aware) — is the right STT model, given it looks tailor-made for the multilingual requirement.

## Decision

### D1 — STT model is `nemotron-speech-streaming-en-0.6b` (English, cache-aware streaming)
The STT model behind the shared `:9100` endpoint, for study-tutor's use, is NVIDIA `nemotron-speech-streaming-en-0.6b`: a cache-aware streaming FastConformer encoder with an RNN-T decoder, 600M parameters, en-US, with punctuation and capitalisation. It replaces "Parakeet TDT" as the study-tutor STT baseline because it does *true* cache-aware streaming (non-overlapping chunks reusing cached encoder state) rather than buffered streaming, and it exposes runtime-selectable latency (≈80 / 160 / 560 / 1120 ms via `att_context_size`) along the latency-accuracy curve with no retraining (≈6.9% average WER at the 1.12 s setting on the OpenASR leaderboard). It is licensed under the **NVIDIA Open Model License** (commercial use permitted), its model-card test hardware includes **DGX Spark** (our exact GB10), and it is already used in the `pollen-robotics/reachy-mini-chatbox` Space — corroborating fit with the Reachy consumer. Selection is via an env-var model alias per the [ADR-ARCH-006](ADR-ARCH-006-dual-inference-path-ollama-bedrock.md) factory pattern (`STT_MODEL`), so the model is a load-time swap, not a code change.

### D2 — Multilingual (French) STT is deferred, not solved; the ideal model is licence-blocked
`nemotron-3.5-asr-streaming-0.6b` — the multilingual (40-locale) cache-aware successor — is on paper the correct answer to the French requirement. **It is not adoptable.** Its Hugging Face repo is gated to NVIDIA employees (waiting-list / early-access request only), and it ships under the **NVIDIA Software and Model Evaluation License**: internal evaluation only, explicitly *no production use*, under confidentiality, on a ~6-month term. That is incompatible with a shipped product and with study-tutor's owned-stack, minor-data posture — a model we cannot license, obtain, or deploy for the real user is not a candidate, however capable. **Rejected for now.**

Interim posture: the English cache-aware baseline (D1) serves English sessions — the majority of use, and the whole of the GCSE English tutor. **French-session STT is a known, named gap.** Watch-list triggers to close it: (a) adopt `nemotron-3.5-asr-streaming-0.6b` if/when NVIDIA relicenses it under the Open Model License; or (b) if French STT becomes a near-term requirement first, evaluate a production-licensed multilingual alternative (a multilingual Parakeet TDT variant, or a Whisper-family model), accepting the loss of native cache-aware streaming in the offline-multilingual case. The shared endpoint's single running model can move to the multilingual choice when it lands — it would still serve the LPA POC's English need — so closing this gap does not fork the endpoint.

### D3 — The voice path introduces no cloud dependency (reinforces ADR-ARCH-015)
Both STT and TTS run locally on GB10; the voice path sends no audio to any third party. This matters more here than in the financial POC's FCA framing: study-tutor's real user is a **minor**, and audio carries both voice biometrics and session content. Keeping it on owned hardware is minor-data-by-design in its strongest form, and it adds nothing to [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md)'s exception ledger. Note that [ADR-ARCH-023](ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md) has since removed the Graphiti/Gemini write-back exception, so with local inference (or Bedrock for demo-week validation only — prompts/responses only, per [ADR-ARCH-006](ADR-ARCH-006-dual-inference-path-ollama-bedrock.md)) the voice layer keeps study-tutor's cloud surface at nil.

### D4 — TTS is out of scope here
The TTS model (Kokoro-82M) is settled by the shared endpoint contract (ADR-POC-015 §4) and conversation-starter D5. This ADR is STT-scoped; it does not re-litigate TTS.

## Alternatives considered

- **Parakeet TDT (the inherited pick).** Open-licensed, very high real-time factor, runs natively on Blackwell — but buffered streaming only, so higher and less-tunable interactive latency. Retained as the fast **offline/batch** transcription alternative (e.g. bulk processing), not the interactive primary.
- **`nemotron-3.5-asr-streaming-0.6b`.** The ideal multilingual streaming model; rejected on licensing/access (gated + evaluation-only) — see D2. The single reason to keep watching this space.
- **`parakeet-unified-en-0.6b`.** Open Model License; offline + streaming in one model; ≈160 ms — but its current pipeline is buffered streaming only, giving no interactive advantage over the cache-aware D1 choice.
- **Canary-Qwen-2.5B.** English accuracy leader (~5.6% WER) at higher latency; the LPA POC's financial-term-accuracy alternative. Not a study-tutor priority (tutoring tolerates the streaming model's WER), but available on the same NeMo/Riva serving if accuracy on proper nouns ever matters.
- **Whisper / multilingual offline models.** The pragmatic fallback for French before a production-licensed multilingual *streaming* model exists (D2b); loses native streaming.
- **On-device STT in the Flutter app (ONNX three-graph export of the cache-aware model).** Deferred — the phone MVP is a thin client (conversation-starter D4); on-device is a phase-2 *offline* concern, aligned with the phase-2 on-device Gemma fallback. Recorded so it isn't lost.

## Consequences

**Positive:**
- Correct interactive-latency STT shape (cache-aware, tunable) for tap-to-talk, on our exact hardware, under a commercial licence.
- Local-only — the strongest form of minor-data-by-design; zero cloud audio egress; no new ADR-ARCH-015 exception.
- Env-var-swappable model (ADR-ARCH-006 pattern) — the multilingual upgrade is a load-time change when it becomes licensable, not a re-architecture.
- The French gap is **named and gated** rather than silently mis-served; the watch-list makes the upgrade condition explicit.
- Corrects the imprecise "Parakeet TDT (streaming)" inheritance for study-tutor's interactive use without reopening the shared-backend decision (D5).

**Negative:**
- **French-session STT is a known interim gap** until a production-licensed multilingual streaming model exists. English (the GCSE English tutor, the primary case) is unaffected.
- The STT model now sits behind a shared endpoint recorded in two repos (this ADR for study-tutor; ADR-POC-015 for the LPA POC). Today both consumers are served by the same English cache-aware model (the LPA POC is English-only; study-tutor's French need is deferred), so there is **no conflict now** — but the two records must be reconciled if/when the shared model changes. Flagged below.
- Depends on NVIDIA NeMo/Riva serving the cache-aware model on ARM64 GB10 — the same serving assumption ADR-POC-015 already carries (no new risk, but validated in the endpoint runbook, not here).

## Downstream artefacts flagged stale

- `docs/handoffs/study-tutor-mobile-voice-conversation-starter.md` **D5** — names "Parakeet STT (:9100)"; reconcile to `nemotron-speech-streaming-en-0.6b` (or note it as the `STT_MODEL` alias). **OQ#2** — its model half is now resolved by this ADR; the transport-shape half remains open.
- **Cross-repo (`lpa-platform-poc`):** ADR-POC-015 §4 still names Parakeet TDT as STT primary, and `RUNBOOK-gb10-voice-endpoints.md` Phase 1 stands it up with the `parakeet-tdt` alias. Because the endpoint is shared, these should reference or align with this ADR so the single running model stays consistent (the English cache-aware model serves the LPA POC's English case too). **Open owner decision:** whether the shared endpoint's canonical model record lives here, in ADR-POC-015, or in a neutral/fleet location.
- The GB10 voice-endpoint stand-up (whoever runs the runbook) should pull `nemotron-speech-streaming-en-0.6b` as the STT model and record the realised `STT_MODEL` alias.

## References

- HF model cards: `nvidia/nemotron-speech-streaming-en-0.6b` (Open Model License; DGX-Spark test hardware; OpenASR WER tables; used in `pollen-robotics/reachy-mini-chatbox`); `nvidia/nemotron-3.5-asr-streaming-0.6b` (gated to NVIDIA employees; NVIDIA Software and Model Evaluation License); `nvidia/parakeet-unified-en-0.6b` (Open Model License).
- NVIDIA **Software and Model Evaluation License** (internal-evaluation, no-production terms) vs NVIDIA **Open Model License** (commercial use permitted) — the distinction that decides D1/D2.
- `lpa-platform-poc` ADR-POC-015 + `RUNBOOK-gb10-voice-endpoints.md` — shared cascade + OpenAI-compatible endpoint contract.
- `docs/handoffs/study-tutor-mobile-voice-conversation-starter.md` — D5 (shared backend), OQ#2 (model/transport), OQ#3 (tap-to-talk MVP).
- [ADR-ARCH-015](ADR-ARCH-015-uk-on-device-data-residency.md), [ADR-ARCH-006](ADR-ARCH-006-dual-inference-path-ollama-bedrock.md), [ADR-ARCH-023](ADR-ARCH-023-student-model-postgres-jsonb-drop-graphiti.md), [ADR-ARCH-014](ADR-ARCH-014-single-user-scalability-posture.md).
