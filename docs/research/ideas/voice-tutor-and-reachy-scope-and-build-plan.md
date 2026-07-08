# Voice — Tutor Voice (server + Flutter) and Reachy Local Migration — Scope + Build Plan

**Status:** Drafted 2026-07-05; **G-RAT + G-CON executed 2026-07-05**; **W0-T PASS + W1 spec/plan done 2026-07-06**; **W0-R ALL GATES PASS 2026-07-06** ([evidence](../../runbooks/evidence/voice-w0r-reachy-feasibility-2026-07-06/EVIDENCE.md)); **FEAT-VOICE-002 + 003 + 004 spec+plan all done (003 + 004 on 2026-07-07: 004 = 25-scenario BDD spec `features/reachy-local-voice-migration/` + TASK-VOX-R01..R09/SMK-R breakdown, YAML `FEAT-VOICE-004.yaml`, all assumptions resolved incl. ASSUM-001 subject→`english`)** — next actions: **W1 build — Opus session (§9 Step 4a)** ‖ **R1 (productionize the s2s unit per the W0-R evidence pins) — Operator + Opus** ‖ **FEAT-VOICE-003 build — Opus `/feature-build FEAT-VOICE-003`** ‖ **FEAT-VOICE-004 build — R-track Operator + Opus in fleet-gateway (NOT study-tutor autobuild)**. Living status in §0; **model allocation in §0a**.
**Voice-phase contract pins (authoritative consumption point):** `CONTRACT_SHA=574615e916bfacafd014b2a0027b47cdf20d8f4a` (contract Rev 1) · `BINDING_SHA=e50897d12470b9f7c9455d5c5836f0d7ee298a50` (binding Rev 1). *Pushed to origin/main (verified 2026-07-06) — the freeze is finalized ("frozen once pushed"); do not amend/rebase these commits or the pins invalidate. Phase-2 pins (`22791afb…`/`6eb7b88c…`) remain the historical record of what phase 2 verified.*
**Generated:** 2026-07-05 · **status refreshed:** 2026-07-06
**Design:** [voice-tutor-and-reachy-design.md](../../design/voice-tutor-and-reachy-design.md) — closes the blueprint's open decisions (streaming-first contract, Starlette port map, audio delivery, quote-handover recommendation) and adds the Reachy track
**Decision authority:** [unified-voice-orientation.md](unified-voice-orientation.md) (ratified pins) · [ADR-ARCH-024 r1](../../architecture/decisions/ADR-ARCH-024-voice-stt-cache-aware-streaming-multilingual-deferred.md) · [voice-implementation-blueprint.md](../../design/voice-implementation-blueprint.md) — **do not re-open pins here**
**Inputs:** [ADR-ARCH-026](../../architecture/decisions/ADR-ARCH-026-player-coach-async-coach-monitor-streaming-ready.md) (Accepted at G-RAT 2026-07-05) · [TASK-STREAM-001](../../../tasks/backlog/TASK-STREAM-001-tutor-turn-token-streaming.md) · [API-session-http-binding.md](../../design/contracts/API-session-http-binding.md) · [conversation starter](../../handoffs/study-tutor-mobile-voice-conversation-starter.md) · [flutter-app-phase2-build-plan.md](flutter-app-phase2-build-plan.md) (this plan is its phase-3 successor)
**Consumed by:** `/design-refine` (G-CON) → `/feature-spec` → `/feature-plan` → `/feature-build`|`/task-work` per wave

---

## 0. Status (2026-07-06)

| Item | State | Record |
|---|---|---|
| GB10 audio endpoints (`parakeet-tdt-0.6b-v3`, `qwen3-tts-0.6b` behind `:9000`) | **Live, smoked** | `lpa-platform-poc` RUNBOOK/RESULTS-gb10-voice-unified-2026-07 |
| LPA reference implementation (~230 tests) + live smoke TASK-VOICE-011 | **Done** (lift, don't rebuild) | blueprint §3 |
| ADR-ARCH-024 r1 | **Accepted** | — |
| ADR-ARCH-026 (async Coach — streaming precondition) | **Accepted** — G-RAT executed 2026-07-05 | `fdb2878` |
| Quote-handover decision (design §5.4 recommendation) | **Decided** — [ADR-ARCH-027](../../architecture/decisions/ADR-ARCH-027-streaming-quote-handover-chunk-boundary-verification.md) (chunk-boundary verification) | `fdb2878` |
| Contract change + CONTRACT_SHA/BINDING_SHA re-freeze, once (design §8) | **Done + PUSHED** (verified 2026-07-06) — contract Rev 1 + binding Rev 1; SHAs in the header above; freeze finalized | `574615e` · `e50897d` |
| W0-T pre-flight (tutor) | **PASS** 2026-07-05 — all four gates green; STT warm 0.11–0.29 s across wav/ogg-opus/**m4a**; TTS Ryan 2.09 s/sentence | [evidence](../../runbooks/evidence/voice-w0-preflight-2026-07-05/EVIDENCE.md) |
| W0-R feasibility gates (Reachy, R-G1..R-G6) | **ALL GATES PASS — run 2026-07-06** (agent-on-GB10 + operator Mac/robot session). Headlines: `--num_pipelines 2` supersedes the two-instance fallback (R-G6); voice pin must be app-side (`MODEL_VOICE`), not server flag; **known defect: tool-call text is spoken** (fixes identified — template tool-call support + TTS strip filter → R1/FEAT-VOICE-004); R-G5 executed (ttl 0, tutor-set preload, keepalive rotated, dgx-spark mirror `be71e3f`); 4 install pins for R1 recorded | [EVIDENCE](../../runbooks/evidence/voice-w0r-reachy-feasibility-2026-07-06/EVIDENCE.md) |
| W1 — FEAT-VOICE-001 spec + plan | **Done 2026-07-06**: 27-scenario BDD spec (all assumptions owner-confirmed) + TASK-VOX-001..007 breakdown, AutoBuild YAML validated, all scenarios `@task:`-linked | `c149929` · `2f8b299` |
| W1 — FEAT-VOICE-001 build (TASK-VOX-001..007) | **NEXT (W-track)** — `/feature-build FEAT-VOICE-001` or `/task-work TASK-VOX-001` sequentially | `tasks/backlog/voice-server-module/` |
| W2 — FEAT-VOICE-002 spec + plan | **Done** (Fable window) — spec `features/streaming-voice/` + plan `.guardkit/features/FEAT-VOICE-002.yaml` | `features/streaming-voice/` |
| W2a/W3 — FEAT-VOICE-003 spec + plan | **Done 2026-07-07**: 22-scenario BDD spec (`features/flutter-voice-client/`, all assumptions owner-confirmed) + TASK-VC-001..007 breakdown, AutoBuild YAML validated, all 22 scenarios `@task:`-linked (R2 active), `flutter test` smoke gate (waves 3/4/5, R3 active), review TASK-REV-V3C1 | `tasks/backlog/flutter-voice-client/` · `.guardkit/features/FEAT-VOICE-003.yaml` |
| W2a/W3 — FEAT-VOICE-003 build (TASK-VC-001..007) | **NEXT (W-track, Opus)** — `/feature-build FEAT-VOICE-003` or `/task-work TASK-VC-001` per wave; MVP HTTP path (waves 1–3) needs only FEAT-VOICE-001, streaming (wave 4) consumes FEAT-VOICE-002 | `tasks/backlog/flutter-voice-client/` |
| FEAT-VOICE-004 spec + plan | **Done 2026-07-07**: 25-scenario BDD spec (`features/reachy-local-voice-migration/`, all 9 assumptions resolved/confirmed — ASSUM-001 subject resolved to `english`, app `defaultSubject` moved `'maths'→'english'`; 1.7B TTS fallback pre-approved; persona copy drafted) + TASK-VOX-R01..R09/SMK-R breakdown (5 code / 5 operator_handoff), YAML validated. Consumes recon deltas D1/D2/D3/D4/D6/D7. Review TASK-REV-RCH4 | `tasks/backlog/reachy-local-voice-migration/` · `.guardkit/features/FEAT-VOICE-004.yaml` |
| FEAT-VOICE-004 build (R-track) | **NEXT (R-track, Operator + Opus)** — code (R04–R08) lands in **sibling `fleet-gateway` repo**, NOT study-tutor autobuild; operator gates R01/R02/R03/R09/SMK-R are `operator_handoff`. Resolve nothing further — all assumptions closed | `tasks/backlog/reachy-local-voice-migration/` |

Detailed, ordered actions in **§9**.

## 0a. Model allocation (Fable window 2026-07-06 → 07)

Fable 5 is available only through **2026-07-07**; Opus thereafter. Allocation principle (from the
2026-07-06 GuardKit stage-sensitivity review): **spend Fable where output quality has no downstream
verification** — feature decomposition (`/feature-plan` is the most model-sensitive stage: informational
gates only, errors amplified by autonomous execution), scenario coverage (`/feature-spec`: the human
curates only what the model proposes), contract/design surgery, and adversarial review. **Implementation
is gate-carried** (Coach re-runs tests independently against deterministic thresholds; nothing
auto-merges) — Opus runs it.

Mechanical fact so nobody misallocates: AutoBuild's Player/Coach models come from the FEAT YAML
(`player_model`/`coach_model`), defaulting to Sonnet 4.5 — `FEAT-VOICE-001.yaml` pins neither, so
**builds never run on the driving session's model**. The rules below are about (a) not burning
Fable-session time orchestrating gate-carried builds, and (b) `/task-work`, which **does** run on the
session model.

| Work | Session model | Why |
|---|---|---|
| `/feature-spec` + `/feature-plan` FEAT-VOICE-002 + 003 (004 once W0-R passes within the window) | **Fable, before 2026-07-08** | spec/plan are the model-sensitive, least-gated stages; contract already frozen at G-CON so early speccing is safe |
| Adversarial review of authored specs/plans and of the W1 merged diff | **Fable** | review quality is unverifiable-by-tests |
| `/feature-build FEAT-VOICE-001` (W1) and all later wave builds; any `/task-work TASK-VOX-*` | **Opus** | deterministic Coach gates + human merge carry the bar; autobuild Player/Coach are YAML-pinned anyway |
| W2 joint TASK-STREAM-001 + FEAT-VOICE-002 build; W2a/W3 Flutter builds | **Opus** (against the Fable-authored spec/plan) | same |
| W0-R run, R1–R4 GB10/robot config, `TASK-VOX-SMK-*` smokes | **Operator (Rich)** | hardware/attended (`operator_handoff` pattern) |
| Roadmap row, backlog hygiene, pin bookkeeping, evidence write-ups | **Opus** | mechanical, self-evident from repo state |

Sibling Fable-window tracks (outside this plan's scope, same allocation logic): the auth/D9
[design](../../design/keycloak-auth-user-management-design.md) +
[scope/build plan](keycloak-auth-scope-and-build-plan.md) (authored 2026-07-06 — note its
FEAT-AUTH-004 ↔ R3 coupling), and the AWS hosting scope + ADR-ARCH-006 revision seeded by
[aws-production-hosting-research-2026-07-06.md](aws-production-hosting-research-2026-07-06.md);
the W0-R pre-run amendments from
[reachy-local-backend-recon-deltas-2026-07-06.md](reachy-local-backend-recon-deltas-2026-07-06.md)
are already applied to the runbook.

## 1. Why this document exists

The [blueprint](../../design/voice-implementation-blueprint.md) says what to lift from
the LPA and in what phase order; the [design](../../design/voice-tutor-and-reachy-design.md)
closes the remaining decisions and adds the Reachy track. This is the thin sequencing
layer that turns both into scoped features, ratification gates, and ready-to-run
`/feature-spec` invocations — for the two consumers the owner asked to build now:
the **Flutter app** (tap-to-talk tutor voice) and the **Reachy Mini** (local voice,
direct to the tutor, no Jarvis in the loop).

## 2. The shape (why this is lower-risk than it looks)

| Layer | Today | After | Change |
|---|---|---|---|
| GB10 audio serving | Live: discrete `/v1/audio/*` behind llama-swap `:9000`, persistent group | Same, untouched | **None** (consume) |
| study-tutor server | Six JSON verbs on `:8100` (Starlette); `turn_stream` stub raises `NotImplementedError` | + `voice/` package, `voice-turn`/`voice-audio` routes, WS turn with token+voice frames | New package + TASK-STREAM-001; contract freeze ×1 |
| Flutter app | Text-only; zero audio deps; no mic/network perms in release manifest | + tap-to-talk, playback queue, streaming client; 3 new deps | Additive; DoD scope event |
| Reachy voice plane | HF-cloud Realtime session (minor's voice off-premises) | s2s server on GB10 `:8765`, robot re-pointed via 2 env keys | New GB10 unit; **config-only** on the robot |
| Reachy tool plane | `ask_jarvis` → NATS → Jarvis; `query_student_model` | + `ask_tutor` → HTTP `:8100` direct; rest untouched | One new tool file; profile `tools.txt` edit |
| Jarvis | In the robot's tutoring path | **Out of the tutoring path** | No Jarvis changes needed |

_Look for: every wave leaves a working system; the robot track never blocks on the app track's contract freeze._

## 3. Scope

**In:**
- Server `voice/` package (LPA port per design §5.1), non-streaming `voice_turn` behind `STUDY_TUTOR_VOICE_ENABLED`.
- The one contract change, executed at G-CON: voice routes (binding §2) + WS frame vocabulary (contract §7) + six voice `error_type`s (contract §9) across **both** frozen docs; `CONTRACT_SHA` and `BINDING_SHA` bumped together, once; TASK-STREAM-001 then implements against the frozen shape (design §8).
- TASK-STREAM-001 execution (existing backlog task, complexity 8) — `generate_stream`, WS transport, streaming contract-suite variants — plus voice's sentence-chunked TTS on that stream.
- Flutter tap-to-talk client + playback + degradation copy + hermetic/live test extensions (design §6).
- Reachy: s2s standup on the GB10, robot re-point, tool-plane verification, `ask_tutor` direct-to-tutor tool, Scholar profile update (design §7).
- Two operator-handoff live smokes with evidence (§8).

**Out:**
- Re-opening model pins, topology, or `:9100`/`:9200` — dead (ADR-ARCH-024 r1 / ADR-POC-015 r1).
- Phone open-mic/VAD/barge-in — the accepted ADR-ARCH-024 r1 trade; sole revisit trigger is open-mic/barge-in landing on the phone.
- On-device Gemma offline fallback — phase-2 keep-warm (conversation starter).
- LPA narration cache / batch jobs / donor-attorney plumbing — explicitly not ported (blueprint §3).
- Keycloak — D9 lands separately ([design](../../design/keycloak-auth-user-management-design.md) + [plan](keycloak-auth-scope-and-build-plan.md), authored 2026-07-06; its FEAT-AUTH-004 couples to this plan's R3); interim single-user tokens serve both clients until its prod cutover.
- Jarvis changes — it simply stops being in the tutoring path.
- LPA browser/React voice UI — different repo, already live-smoked.

## 4. Feature decomposition

| Feature | Gist | Depends on |
|---|---|---|
| **FEAT-VOICE-001** | Server voice module: `voice/` package, in-memory multipart validation (`python-multipart` direct pin), `AudioClient`, non-streaming `voice_turn` + `voice-audio` behind flag; contract-seam tests (mock transport, multipart pins) | G-RAT, G-CON, W0-T |
| **FEAT-VOICE-002** | Streaming voice: sentence-chunked TTS on the token stream, WS voice frames (`uvicorn[standard]`/websockets server dep), chunk-boundary quote verification — **executed jointly with TASK-STREAM-001**, implementing the shape already frozen at G-CON | FEAT-VOICE-001, TASK-STREAM-001 |
| **FEAT-VOICE-003** | Flutter voice client: deps + manifests, `VoiceApi` port/adapters/fakes, tap-to-talk UI, playback queue, degradation copy, hermetic + live test variants | G-CON (frozen contract); MVP path needs only FEAT-VOICE-001 |
| **FEAT-VOICE-004** | Reachy local voice: s2s unit on GB10, robot re-point, tool-call verification, `ask_tutor` tool (subject pinned to the app's constant), profile update, D3 residency closure | W0-R gates; **independent of 001–003 and of G-RAT/G-CON** |

Live smokes are `operator_handoff` tasks (AutoBuild cannot provision GPU serving —
the TASK-VOICE-011 pattern), written **before** building: `TASK-VOX-SMK-T` (tutor
voice, AC-V1..V3) and `TASK-VOX-SMK-R` (Reachy, AC-R1..R4). Task prefix `VOX` avoids
cross-repo confusion with lpa-platform-poc's `TASK-VOICE-*`.

## 5. Sequencing (waves)

```
{G-RAT ──► G-CON}  ‖  W0-T  ‖  W0-R          (the two gates and the two discovery sets run in parallel)

G-CON + W0-T ──► W1 (FEAT-VOICE-001) ──► W2 (TASK-STREAM-001 + FEAT-VOICE-002) ──► W3 (FEAT-VOICE-003 streaming) ──► W4 (TASK-VOX-SMK-T)
                                             ‖ W2a: FEAT-VOICE-003 MVP slice (against 001, fakes + dev deploy)

W0-R ──► R1 (s2s standup) ──► R2 (re-point + tools) ──► R3 (ask_tutor) ──► R4 (TASK-VOX-SMK-R)
         [R-track independent of the W-track and of G-RAT/G-CON; the only shared
          resource is the GB10 itself + quiet-GPU discipline]
```

```mermaid
graph TD
    GRAT[G-RAT: ratify ADR-ARCH-026 + quote-handover ADR]:::gate --> GCON[G-CON: /design-refine contract change; CONTRACT_SHA + BINDING_SHA freeze ×1]:::gate
    W0T[W0-T: tutor pre-flight, no code]:::w1 --> W1
    GCON --> W1[W1: FEAT-VOICE-001 server voice module, non-streaming, flagged]:::w1
    W1 --> W2[W2: TASK-STREAM-001 + FEAT-VOICE-002 streaming voice]:::w2
    W1 --> W2a[W2a ‖: FEAT-VOICE-003 MVP slice]:::w2
    W2 --> W3[W3: FEAT-VOICE-003 streaming client + live variants]:::w3
    W2a --> W3
    W3 --> W4[W4: TASK-VOX-SMK-T live smoke]:::gate
    W0R[W0-R: Reachy feasibility gates R-G1..R-G5]:::w1 --> R1[R1: s2s server standup on GB10]:::w2
    R1 --> R2[R2: robot re-point + tool-plane verify]:::w2
    R2 --> R3[R3: ask_tutor direct-to-tutor]:::w3
    R3 --> R4[R4: TASK-VOX-SMK-R live smoke]:::gate
    classDef w1 fill:#cdf,stroke:#333
    classDef w2 fill:#cfe,stroke:#333
    classDef w3 fill:#fdc,stroke:#333
    classDef gate fill:#eee,stroke:#333
```

**W0-T — tutor pre-flight (no code; blueprint §8 Phase 0).** `GET :9000/v1/models` lists both audio models; STT round-trips a known clip **including one in the Flutter recorder's actual output format (the m4a test)**; TTS `voice=Ryan` returns playable audio; `GET :9000/running` shows both `ready`. Record timings. *Gate: all four pass.*

**W0-R — Reachy feasibility gates** (operator, on the GB10 — [runbook](../../runbooks/RUNBOOK-voice-w0r-reachy-feasibility.md)). Run against a **throwaway foreground s2s instance** — feasibility only; R1 later productionizes the passing configuration into the durable unit. R-G1 s2s installs and runs on GB10 aarch64/CUDA-13 (cu130 wheel first; bare-metal vs container decision); R-G2 `--qwen3_tts_model_name …0.6B-CustomVoice` works under the s2s qwen3 backend (fallback decision to owner if not; locate + record the Ryan voice flag); R-G3 tool calls round-trip through local s2s (`query_student_model` fires and is narrated — the highest-risk unknown); R-G4 memory arithmetic re-done against live steady state (TTS cold-start fails at ~110 GB used — measure, don't assume; price the dual-instance option); R-G5 **decided 2026-07-05**: `tutor` set becomes the standing default + `gemma4-tutor` ttl raised — executed as runbook Phase 6, config mirrored to `dgx-spark`; **R-G6 (added 2026-07-06, two-robot fleet fact)**: two concurrent Realtime sessions against one s2s server — fallback: one instance per robot (`:8765`/`:8766`) if R-G4's arithmetic allows. *Gate: all pass or each failure has a recorded decision.*

**W1 — FEAT-VOICE-001.** Port per design §5.1; tutor envelope errors; seam tests pin the wire shape (multipart field/filename/content-type with codec params/model field — the "green but broken" defence); non-streaming `voice_turn` + `voice-audio` behind the flag. *Gate: full tutor suite green; seam tests pin the contract; flag off ⇒ routes 404.*

**W2 — TASK-STREAM-001 + FEAT-VOICE-002 (one joint effort).** `generate_stream` (the current `LLMClient` hardcodes `stream: False` and is bridged via `asyncio.to_thread` in the Player adapter — new path touching both seams, not a rework); WS `turn` implementing — and widening — the stubbed `turn_stream`/`TurnEvent` (design §5.2); `uvicorn[standard]`/websockets server dep pinned; sentence-chunked TTS emitting `audio_ref` frames; chunk-boundary quote verification per the G-RAT decision. **W2a in parallel:** Flutter MVP voice slice (deps, manifests, `VoiceApi`+fakes, tap-to-talk against non-streaming `voice_turn`). *Gate: streaming contract-suite variants green against the dev deploy (`RUNBOOK-study-tutor-http-dev-deploy.md`).*

**W3 — FEAT-VOICE-003 streaming client.** WS consumer, incremental token render, ordered chunk playback, degradation copy; live suite voice variants (`--concurrency=1`, quiet GPU). *Gate: `app/test_live/` voice variants green on device against the GB10.*

**W4 — TASK-VOX-SMK-T (operator handoff).** AC-V1..V3 (§8). *Gate: ACs hold; evidence + RESULTS written.*

**R1–R4 — Reachy track** (starts after W0-R; fully parallel to the W-track): systemd/docker s2s unit productionizing the W0-R configuration (digest-pinned, non-loopback bind, Ryan voice flag located and set) → `sitecustomize.py` env injection + `HF_REALTIME_CONNECTION_MODE=local`/`HF_REALTIME_WS_URL` re-point, open-mic latency + tool verification → `ask_tutor` tool (subject pinned to the app's constant — design §7.4) + Scholar `tools.txt`/persona update (reconcile repo-vs-Pi profile drift) → live smoke AC-R1..R4. *Gates per step; R4 evidence closes the D3 residency exception.*

## 5a. Ratification gates — ✅ BOTH EXECUTED 2026-07-05, DO NOT RE-RUN

> **G-RAT and G-CON are done and pushed** (`fdb2878`; contract Rev 1 `574615e9…` + binding Rev 1
> `e50897d1…` on origin/main — re-verified 2026-07-06). Re-running the commands below would create
> a duplicate ADR / spurious freeze cycle. They are kept **as the record of what was run**, not as
> to-dos.

| Gate | Command | Ratifies | Blocks |
|---|---|---|---|
| G-RAT | `/arch-refine` | ADR-ARCH-026 Proposed → Accepted **+** quote-handover decision (design §5.4) as ADR-ARCH-026 revision or new ADR | W1 onward (streaming precondition + handover shape). Does **not** block the R-track |
| G-CON | `/design-refine` | The executed contract change: binding §2 routes, contract §7 frames, contract §9 error set — **both docs re-frozen; `CONTRACT_SHA` + `BINDING_SHA` bumped together, once** | W1 (routes exist), W2a/W3 (app consumes). Does **not** block the R-track |

```bash
/arch-refine "Ratify ADR-ARCH-026 (async Coach) to Accepted and record the chunk-boundary quote-handover decision for streaming voice (design §5.4)" \
  --adr=ADR-ARCH-026 \
  --context docs/design/voice-tutor-and-reachy-design.md

/design-refine "Add voice routes (binding §2), the voice WS frame vocabulary (contract §7), and six voice error_types (contract §9) per the voice design §8; re-freeze both contract docs; CONTRACT_SHA and BINDING_SHA bumped together, once" \
  --context docs/design/contracts/API-session-cross-device.md \
  --context docs/design/contracts/API-session-http-binding.md \
  --context docs/design/voice-tutor-and-reachy-design.md \
  --context tasks/backlog/TASK-STREAM-001-tutor-turn-token-streaming.md
```

## 6. /feature-spec invocations (run in wave order)

**Execution state: ALL FOUR /feature-spec + /feature-plan invocations (W1, W2, W2a/W3, R-track) are ✅ DONE — do not re-run.**
W1 spec `c149929`, plan `2f8b299` (`features/voice-server-module/` + `tasks/backlog/voice-server-module/`).
W2 spec+plan in `features/streaming-voice/` + `.guardkit/features/FEAT-VOICE-002.yaml`.
W2a/W3 (FEAT-VOICE-003) spec+plan **done 2026-07-07** — `features/flutter-voice-client/` +
`tasks/backlog/flutter-voice-client/` + `.guardkit/features/FEAT-VOICE-003.yaml` (TASK-VC-001..007,
22 scenarios `@task:`-linked, `flutter test` smoke gate, review TASK-REV-V3C1).
R-track (FEAT-VOICE-004) spec+plan **done 2026-07-07** — `features/reachy-local-voice-migration/`
(25 scenarios) + `tasks/backlog/reachy-local-voice-migration/` + `.guardkit/features/FEAT-VOICE-004.yaml`
(TASK-VOX-R01..R09/SMK-R, 5 code + 5 operator_handoff, review TASK-REV-RCH4; all 9 assumptions closed —
ASSUM-001 subject→`english`, 1.7B fallback pre-approved, persona copy drafted). **Not** `@task:`-linked
(scenarios exercise fleet-gateway/robot behaviour the study-tutor task-runner can't drive).
**Nothing left to spec.** Builds proceed under §0a: W-track Opus; R-track Operator + Opus, code in fleet-gateway.

```bash
# ── W1 ── ✅ EXECUTED 2026-07-06 (kept as record — spec c149929, plan 2f8b299) ──
/feature-spec "FEAT-VOICE-001 server voice module: port the lpa-platform-poc voice shape (config/client/errors/utils/validation/service) into src/study_tutor/voice/ on Starlette idioms per design §5.1; in-memory multipart parsing (never request.form() — Starlette spools >1MB parts to disk) with python-multipart as a direct pin; non-streaming POST voice-turn + GET voice-audio behind STUDY_TUTOR_VOICE_ENABLED; six voice error_types in the tutor envelope; httpx.MockTransport seam tests pinning the multipart wire contract; ephemeral audio invariants (no audio at rest)" \
  --context docs/design/voice-tutor-and-reachy-design.md \
  --context docs/design/voice-implementation-blueprint.md \
  --context docs/design/contracts/API-session-http-binding.md \
  --context docs/research/ideas/voice-tutor-and-reachy-scope-and-build-plan.md

# ── W2 ── ✅ EXECUTED 2026-07-07 (kept as record — spec+plan in features/streaming-voice/ + .guardkit/features/FEAT-VOICE-002.yaml; tasks TASK-VS2-001..008) ──
/feature-spec "FEAT-VOICE-002 streaming voice on the token stream: implement and widen SessionService.turn_stream/TurnEvent + WebSocketRoute turn per the frozen contract §7 frames; uvicorn[standard]/websockets server dep; LLMClient generate_stream incl. the asyncio.to_thread Player-adapter seam (TASK-STREAM-001 Scope 1); sentence-chunked TTS (~15-25 words, response_format=wav) emitting audio_ref frames; chunk-boundary quote verification per the G-RAT ADR; streaming variants of the contract suite" \
  --context docs/design/voice-tutor-and-reachy-design.md \
  --context tasks/backlog/TASK-STREAM-001-tutor-turn-token-streaming.md \
  --context docs/design/contracts/API-session-http-binding.md \
  --context docs/research/ideas/voice-tutor-and-reachy-scope-and-build-plan.md

# ── W2a/W3 ── ✅ EXECUTED 2026-07-07 (kept as record — spec+plan in features/flutter-voice-client/ + .guardkit/features/FEAT-VOICE-003.yaml; tasks TASK-VC-001..007; review TASK-REV-V3C1) ──
/feature-spec "FEAT-VOICE-003 Flutter tap-to-talk voice client: record/just_audio/web_socket_channel deps (deliberate zero-deps DoD scope event); INTERNET+RECORD_AUDIO main-manifest + NSMicrophoneUsageDescription; VoiceApi port with Http/Fake/Flaky adapters mirroring SessionApi seams; tap-to-talk with client-side 60s hard stop; transcript-first display; ordered wav chunk playback; VoiceUnavailable amber degradation copy; hermetic direction-pin tests + app/test_live voice variants" \
  --context docs/design/voice-tutor-and-reachy-design.md \
  --context app/README.md \
  --context docs/design/contracts/API-session-http-binding.md \
  --context docs/research/ideas/voice-tutor-and-reachy-scope-and-build-plan.md

# ── R-track ── ✅ EXECUTED 2026-07-07 (kept as record — spec+plan in features/reachy-local-voice-migration/ + .guardkit/features/FEAT-VOICE-004.yaml; tasks TASK-VOX-R01..R09/SMK-R; review TASK-REV-RCH4. Outcome: ASSUM-001 subject resolved to `english` — app defaultSubject moved 'maths'→'english', so the recon-D6 tension below is CLOSED, not open) ──
/feature-spec "FEAT-VOICE-004 Reachy local voice migration: huggingface speech-to-speech realtime unit on GB10 :8765 (Silero VAD, --stt parakeet-tdt, --tts qwen3 with the 0.6B pin per R-G2, Ryan voice flag, --llm_backend responses-api pointed at llama-swap :9000 with the resident-set posture from R-G5); robot re-point via HF_REALTIME_CONNECTION_MODE=local + HF_REALTIME_WS_URL through sitecustomize.py (recon D3: verify the Pi's installed app version supports these keys; plan an upgrade step if not); verify tool round-trip; ask_tutor external tool direct to the study-tutor HTTP adapter :8100 with resume_if_active session pickup and the subject string pinned to the app's constant (recon D6: app pins 'maths' at app/lib/ui/home_screen.dart:12 while the Scholar persona is English — resolve to ONE shared constant or D8 pickup never matches; no Jarvis in the tutoring loop); port query_student_model off frozen Graphiti onto a Postgres-backed read via :8100 (recon D2) and fix its rejected tool-interface shape (recon D1); ship to the Pi via clean re-clone, not git pull (recon D7 — hand-edited clone); Scholar profile update reconciling repo-vs-Pi drift to the Pi where the Pi is right (recon D4)" \
  --context docs/design/voice-tutor-and-reachy-design.md \
  --context docs/research/ideas/unified-voice-orientation.md \
  --context docs/research/ideas/reachy-local-backend-recon-deltas-2026-07-06.md \
  --context docs/research/ideas/voice-tutor-and-reachy-scope-and-build-plan.md
```

Each was followed by `/feature-plan "<title>" --context features/<slug>/<slug>_summary.md` —
**all four `/feature-plan` runs are ✅ DONE** (task breakdowns + `.guardkit/features/FEAT-VOICE-00{1..4}.yaml` committed). **Nothing in §6 remains to run.**
Sibling-repo context (read in-session, not `--context`): `lpa-platform-poc/src/voice/` +
`tests/voice/`, `fleet-gateway/reachy/RUNBOOK-deploy-scholar-reachy-mini.md`,
`dgx-spark/vendor/README.md` + `scripts/audio-*.sh`.

## 7. Cross-cutting / ADRs to reconcile

- **ADR-ARCH-026** → Accepted at G-RAT; quote-handover recorded (revision or new ADR).
- **New ADR not required for pins** — orientation + ADR-ARCH-024 r1 stay canonical; this plan adds no model decisions.
- **Binding + cross-device contract** re-frozen once at G-CON; `CONTRACT_SHA` re-pinned (binding header + phase-2 plan header) and `BINDING_SHA` bumped (phase-2 plan header, dev-deploy runbook, `app/PROGRESS.md`) together.
- **Roadmap:** voice is absent from `docs/planning/feature-roadmap.md` — add a phase-3 voice row pointing here (FEAT-VOICE-001…004) rather than retro-fitting old phases.
- **Orientation erratum to carry, not fix silently:** the Parakeet Docker Hub image is `martinb78/parakeet-tdt-v3-spark` (the orientation's `martinb78/dgx-spark-parakeet-asr` is the GitHub repo name) — corrected in `dgx-spark/vendor/README.md:14-16`.
- **Fleet-gateway repo:** `ask_tutor` tool + profile changes land there (gateway owns robot-side code — NATS-plan precedent); this plan is their sequencing home.
- **dgx-spark repo:** s2s unit files, install/launch scripts, and the llama-swap-adjacent residency note mirror there (standing config-mirror discipline).

## 8. Downstream gate — the two live smokes (operator handoff)

**TASK-VOX-SMK-T (tutor voice, after W3):**
1. **AC-V1:** a spoken question tap-recorded on the real phone produces a correct transcript (live Parakeet) and an audible tutor answer (live Qwen3-TTS) in the app.
2. **AC-V2:** the session record and logs contain the transcript and **no raw audio anywhere** (DB `bytea`/blob sweep + disk sweep).
3. **AC-V3:** with both audio models stopped **and their launch scripts disabled** (a bare `docker stop audio-*` self-heals via llama-swap), the app degrades to text with the amber copy and **zero third-party calls** (outbound-connection sampling in the adapter container).
4. Objective intelligibility: round-trip TTS output back through live STT and compare text (the LPA no-human-listener check).

**TASK-VOX-SMK-R (Reachy, after R3):**
1. **AC-R1:** open-mic conversation against the local s2s server — no HF-cloud Realtime session established (connection sampling on the Pi and GB10).
2. **AC-R2:** `query_student_model` and `ask_tutor` fire through the local session; a tutor session started on the phone is **resumed by the robot** (D8 pickup — requires `ask_tutor` to send the app's exact subject string, since `resume_if_active` matches on `(student, subject)`; design §7.4).
3. **AC-R3:** no raw audio at rest on Pi or GB10; transcripts only in the tutor's session store.
4. **AC-R4:** open-mic latency recorded (simple turn vs `ask_tutor` turn) against design §7.5 estimates.

Evidence into `docs/runbooks/evidence/` + a RESULTS file each, per house runbook
discipline. Operational guardrails while smoking: quiet-GPU rule (no LPA extraction /
tutor sessions mid-flight), never `GET :9000/unload` (unloads **everything**), check
`systemctl status llama-swap-keepalive.timer` before assuming self-revival (audio pair
is deliberately not probed; timer inactive since 2026-07-03, confirmed during the
2026-07-05 standup).

## 9. Next steps (detailed, in order)

Run order: **{ G-RAT → G-CON } ‖ W0-T ‖ W0-R** first, then **{ W1 → W2(+W2a) → W3 → W4 } ‖ { R1 → R2 → R3 → R4 }**

### Step 1 — G-RAT — ✅ DONE 2026-07-05 (`fdb2878`, pushed)
ADR-ARCH-026 Accepted; quote-handover recorded as ADR-ARCH-027 (chunk-boundary verification).
**Do not re-run** — verified 2026-07-06 (a re-run would mint a duplicate ADR).

### Step 2 — G-CON — ✅ DONE 2026-07-05 (contract Rev 1 `574615e9…` · binding Rev 1 `e50897d1…`, pushed)
Both docs re-frozen; SHAs bumped together, once; pin locations updated. **Do not re-run** —
verified 2026-07-06; W2 implements against this shape with **no second freeze**.

### Step 3 — W0-T ✅ DONE 2026-07-05 · W0-R ✅ ALL GATES PASS 2026-07-06
W0-T: all four gates green ([evidence](../../runbooks/evidence/voice-w0-preflight-2026-07-05/EVIDENCE.md)).
W0-R: P0 + R-G1..R-G6 all PASS ([evidence](../../runbooks/evidence/voice-w0r-reachy-feasibility-2026-07-06/EVIDENCE.md))
— run by the agent on the GB10 with the operator's Mac/robot session for R-G3. R1 consumes the
evidence file's pins verbatim (resolve-URL wheel, numba floors, `OPENAI_API_KEY`, `--num_pipelines 2`,
app-side voice pin, tool-call-speech fixes, user-mode `systemctl --user restart llama-swap`).

### Step 4a — W1 (FEAT-VOICE-001) — **Opus session** (spec+plan already done)
**Do:** build the server voice module — `/feature-build FEAT-VOICE-001` (or `/task-work TASK-VOX-001` sequentially). Do **not** run this from a Fable session (§0a): the build is gate-carried and the autobuild Player/Coach models are YAML-pinned anyway.
**Gate:** suite green; seam tests pin the multipart contract; flag off ⇒ 404.

### Step 4b — R1 → R2 → R3 (parallel to Steps 4a–5) — **Operator + Opus** (FEAT-VOICE-004 spec by **Fable** if W0-R passes within the window)
**Do:** productionize the W0-R configuration as the durable s2s unit; re-point the robot; verify tools; build `ask_tutor` (subject pinned — resolve recon D6 first) + profile update.
**Gate:** R2's tool round-trip verified; robot converses locally end-to-end.

### Step 5 — W2 + W2a — **Opus builds; spec+plan authored by Fable first (§0a)**
**Do:** joint TASK-STREAM-001 + FEAT-VOICE-002 build; Flutter MVP slice in parallel (GB10 access is the only resource shared with the R-track). The FEAT-VOICE-002 (and 003) `/feature-spec` + `/feature-plan` runs happen in the Fable window — the contract shape is frozen at G-CON, so speccing ahead of the W1 build is safe; fold any W1-build learnings into the plan at review.
**Gate:** streaming contract variants green against dev deploy; MVP voice works on device.

### Step 6 — W3 → W4 and R4 — **Opus builds; Operator smokes**
**Do:** streaming Flutter client; then the two operator-handoff smokes (§8).
**Gate:** AC-V1..V3 and AC-R1..R4 hold; RESULTS + evidence written; D3 residency exception closed.
**Then:** update roadmap row; retro the freeze discipline (did we really only bump once?).

---

*Generated 2026-07-05; status refreshed 2026-07-06 (G-RAT + G-CON executed 2026-07-05 — ADR-ARCH-026 Accepted, ADR-ARCH-027 recorded, contract + binding at Revision 1, SHAs pinned in the header; W0-T PASS; **W0-R all gates PASS 2026-07-06** with [evidence](../../runbooks/evidence/voice-w0r-reachy-feasibility-2026-07-06/EVIDENCE.md) — R-track fully unblocked, R-G5 config executed + mirrored; W1 spec 27 scenarios + plan TASK-VOX-001..007 committed, AutoBuild-ready; **model allocation in §0a**). Companion design: [voice-tutor-and-reachy-design.md](../../design/voice-tutor-and-reachy-design.md). Next actions: **Step 4a (W1 build — Opus)** ‖ **Step 4b R1 (productionize s2s per evidence pins — Operator + Opus)** ‖ **FEAT-VOICE-002/003/004 spec+plan (Fable, by 2026-07-07)** in §9.*
