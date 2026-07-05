# ADR-ARCH-026 — Player-Coach: async Coach monitor (off the pre-send path) as the streaming-ready tutor-turn architecture

## Status

Accepted — ratified 2026-07-05 at gate G-RAT (voice scope & build plan §5a). Decisions D1–D5 and D-DATA stand as written. **Extended by [ADR-ARCH-027](ADR-ARCH-027-streaming-quote-handover-chunk-boundary-verification.md)**, which resolves the quote-handover-under-streaming question this ADR's D4a left to the streaming design pass.

**Date:** 2026-07-05
**Phase:** FEAT-APP-001 acceptance follow-on (HTTP App Access adapter live on GB10)
**Related:** FEAT-PH1-003 (Player-Coach bounded revision loop — the design this supersedes on the caller path), [ADR-ARCH-019](ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) (the "move non-user-facing work off the caller path, fire-and-forget" pattern this reuses), [ADR-ARCH-024](ADR-ARCH-024-voice-stt-cache-aware-streaming-multilingual-deferred.md) (voice STT; its OQ#2 *transport shape* — Realtime WebSocket vs discrete routes — is the same transport this ADR's phase 2 lands on), the frozen HTTP binding `docs/design/contracts/API-session-http-binding.md` (reserves `stream?` on `turn`; §7 sketches WS token streaming, deferred to OQ2), SR-07 (`API-tutoring.md` — `tutor_turn` p95<10s / 30s ceiling). ASSUM-001 (`ACCEPTANCE_THRESHOLD = 0.70`), ASSUM-002 (`MAX_REVISION_ATTEMPTS = 3`), D-COACH-07 (`on_flag` observability-only).

## Context

FEAT-APP-001 put the tutoring loop live on GB10 as an HTTP API. The Mac-side live contract suite passes 35/35, but the attended cross-device walk is blocked on **turn latency**: warm turns measure ~9–17s on an idle box (and 36–48s under the Mac's probe), above SR-07's p95<10s / 30s ceiling and above the app's **15s product deadline** — so every send after the first would show "connection problem".

Direct measurement (2026-07-05) located the cost precisely:
- **Prefill is cheap.** A 3,385-token history prefills in 2.7s cold / 1.5s cached on `gemma4-tutor`. Deep history is not the problem; the KV cache reuses fine.
- **It is generation-bound.** GB10 runs these 26B-A4B models at ~55 tok/s. Every turn the **Coach synchronously generates a ~500-token `CoachVerdict` (~9s)**, and this happens *before the learner sees anything*. That fixed ~9s Coach tax dominates the turn.
- **The revision loop essentially never fires.** Across ~20 probe turns the Coach accepted every one (0 revisions, 0 flags). The bounded-revision loop (FEAT-PH1-003, ASSUM-002) — the reason the Coach is on the pre-send path — paid ~9s/turn for a correction that did not occur.

The Coach's per-turn verdict currently drives only: (a) the synchronous accept/revise decision + revision loop, and (b) `on_flag` (logger-only, D-COACH-07). It writes **nothing** to the student model per-turn — mid-session misconception/topic-confidence persistence does not yet exist (session-end `build_session_completion` passes an empty `misconceptions_per_topic`, ASSUM-007). So moving the Coach off the caller path loses no persisted learner state.

Crucially for the long term: the product's UX target is **token streaming** (the contract reserves `stream?` and a WS path; [ADR-ARCH-024](ADR-ARCH-024-voice-stt-cache-aware-streaming-multilingual-deferred.md) commits the voice loop to streaming). **Streaming is incompatible with a pre-send Coach gate** — you cannot revise tokens already on the student's screen. So the Coach must come off the pre-send path regardless of the latency number; the latency is merely what forces it now.

## Decision

### D1 — The Coach becomes an asynchronous monitor, not a pre-send gate (phase 1, now)
`run_turn` returns the Player's response (after the synchronous quote-handover, D3) **as soon as it is generated**. `coach.evaluate` runs **once**, fire-and-forget, on a background task; there is **no live revision loop**. The critical path drops to Player + handover (~5s typical). This reuses the [ADR-ARCH-019](ADR-ARCH-019-async-graphiti-writeback-every-write-point.md) fire-and-forget pattern: the background task's failure is logged and never affects the turn. The background verdict still emits `on_flag` when `weighted_total < ACCEPTANCE_THRESHOLD` (0.70) so below-bar turns remain visible for session-end review. This supersedes FEAT-PH1-003's caller-path revision loop on the production path; the sync revision path is retained behind a `coach_evaluation` constructor mode. The default stays `"sync"` (so FEAT-PH1-003's 24 revision-test sites and a future async-correction feature, D4b, keep a home without churn), and the two production wirings (`_build_orchestrator_factory`) opt into `"async"` **explicitly and visibly** — the go-forward intent lives in the wiring + this ADR, not in a default that would silently break the revision suite.

### D2 — The Coach verdict is trimmed to ~250 tokens
`roles/tutor/prompts/coach.md` is trimmed to terse output — the six criterion scores + misconceptions (the machine-useful signal), with per-criterion evidence reduced to a short phrase rather than a full sentence. On a single-GPU box (`-np 1`) the background Coach still holds the GPU; halving its generation (~500→~250 tokens, ~9s→~4.5s) means it usually finishes in the inter-turn gap (student reading/typing) instead of queueing the next turn's Player. Off the critical path an occasional over-run is harmless.

### D3 — The synchronous factual guardrail stays on the path
The `coach_handover` quote-verification step (`apply_quote_verification`) runs synchronously and produces the learner-visible response — it is the "do not show a fabricated quote" gate, the highest-harm error for an English-literature tutor. Only the **pedagogical rubric scoring** goes async. This is the principled split: block on "is this a fabrication," do not block on "is this a 0.8 or 0.9 on AO2."

### D4 — Streaming token delivery is the planned phase 2 (the real UX win), built *on* D1
- **4a:** Streaming is a cross-team effort — a streaming Player generation (`generate_stream`), a new streaming transport (SSE or the WS `turn` the binding sketches in §7 / the [ADR-ARCH-024](ADR-ARCH-024-voice-stt-cache-aware-streaming-multilingual-deferred.md) voice transport), a `BINDING_SHA` change coordinated with the app, a Flutter streaming client + incremental UI, and streaming variants of the contract suite. It is **not** a server-only change and is not required to meet the 15s deadline (D1 does that). It is filed as its own backlog task so it is tracked, not remembered.
- **4b:** Streaming *requires* D1 (async Coach) as a precondition and is **purely additive** to it — `generate_stream` alongside `generate`, a streaming endpoint alongside the JSON one. D1 is not reworked when streaming lands. Async follow-up correction (surfacing a below-bar verdict as a follow-up message rather than a pre-send revision) is the option that would reuse the retained sync-revision logic; deferred pending D-DATA below.

### D5 — Applies to the shared orchestrator (both transports)
The change lives in `PlayerCoachOrchestrator`, so the MCP surface and the HTTP deployment get identical behaviour. No divergence between transports.

### D-DATA — Measure the production revision rate before investing in correction
The choice between "pure async monitor" (D1) and "async + follow-up correction" (D4b) hinges on how often the Coach would actually reject and materially improve a turn. Observed 0/20 on narrow content. Before building correction, instrument `decision`/`weighted_total` per turn over a spread of realistic GCSE prompts and record the rate. If ~0–2%, pure async is right and correction is over-engineering.

## Alternatives considered

- **Keep the Coach synchronous, make it faster** (smaller/faster Coach model, or D2's token trim alone). Rejected as the *primary* answer: it still taxes every turn, and — decisively — it dead-ends streaming, which forbids any pre-send gate. The token trim (D2) is kept, but as an efficiency measure on the *async* Coach, not a way to preserve the sync gate.
- **Async + follow-up correction now** (D4b). Deferred, not rejected — gated on D-DATA. Preserves in-flight quality intervention without blocking, at the cost of an occasional visible self-correction. The retained sync-revision code (D1) is its foundation.
- **Do streaming now instead of async Coach.** Rejected as *now* work: it is the cross-team phase-2 effort (D4a), depends on the app side, and is not needed to unblock the walk. But it is the acknowledged end-state, and D1 is explicitly its enabler — so this is sequencing, not omission.
- **Status quo (sync pre-send gate).** Rejected: fails the 15s deadline deep in a session and is architecturally incompatible with the streaming UX target.

## Consequences

**Positive:**
- Typical turns meet the 15s app deadline and SR-07 (critical path ≈ Player + handover, ~5s).
- Establishes the **streaming-ready** architecture: the Coach is off the pre-send path, which streaming requires — phase 2 grafts on without rework.
- Less GPU tax per turn on the shared GB10 (D2), reducing contention with the fleet and the next turn.
- The factual guardrail (D3) — the highest-harm error class — stays synchronous.

**Negative:**
- **Loses live pre-send revision.** A below-bar Player response can briefly reach the student before the (async) Coach scores it. Mitigated by: the near-zero observed revision rate, the fine-tuned Player, `on_flag` review visibility, D3's retained factual guardrail, and D4b as the escalation if D-DATA shows it is needed. This is an accepted product trade (owner-confirmed 2026-07-05).
- Two Coach modes exist in code (`sync`/`async`); production uses `async`. Slight surface increase, justified by keeping FEAT-PH1-003's tests and the D4b foundation alive.
- The background task's verdict is not awaited, so per-turn `TurnResult.decision`/`verdict` at return time no longer reflect a completed evaluation (they become `"deferred"`/`None`). Consumers already use only `response` + coarse metadata; tests updated accordingly.

## Downstream artefacts flagged stale

- `API-tutoring.md` SR-07 framing — the *caller-facing* `tutor_turn` path is now Player-only; the Coach's latency no longer enters the budget (mirrors how ADR-ARCH-019 removed Graphiti writes from it). Reconcile the note.
- FEAT-PH1-003 docs / `roles/tutor/prompts/coach.md` — the revision loop is no longer on the caller path (retained behind `coach_evaluation="sync"`); the coach prompt is trimmed (D2).
- Any test asserting synchronous revision / a completed verdict on the returned `TurnResult` — updated for `coach_evaluation="async"` default.
- **Backlog:** the streaming phase-2 task (D4a) — server `generate_stream` + streaming transport + `BINDING_SHA` change + Flutter client + suite variants.

## References

- Latency measurement (2026-07-05): `docs/runbooks/RUNBOOK-study-tutor-http-dev-deploy.md` "Mac-side acceptance" + the prefill/generation probes recorded there.
- `src/study_tutor/tutoring/orchestrator.py` (`run_turn`, the revision loop), `src/study_tutor/tutoring/coach/rubric.py` (`ACCEPTANCE_THRESHOLD`, `parse_coach_output`), `src/study_tutor/cli/main.py` (`_build_orchestrator_factory`, `_on_flag`, the HTTP reply factory).
