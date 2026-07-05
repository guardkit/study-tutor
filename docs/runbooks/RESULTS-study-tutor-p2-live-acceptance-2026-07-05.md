# RESULTS — Phase-2 live acceptance (p2-wave-7): live contract suite + §3.6 cross-device walk

**Date:** 2026-07-05. **Operator:** Rich (watching) + Claude (Mac session, driving via adb/curl).
**Deployment under test:** GB10 HTTP App Access adapter, dev config, `promaxgb10-41b1.tailebf801.ts.net:8100` (Tailscale IP `100.84.90.91`), async-Coach build (ADR-ARCH-026), main @ `369973d`+.
**App under test:** `app/` real-transport flavour, `--dart-define=API_BASE_URL=http://100.84.90.91:8100`, Pixel 9a emulator (the v1 morning-gate AVD).
**Pre-registered bar (build plan §Pre-registered success bar):** live contract suite green against the real adapter AND the fake (same assertions) + §3.6 walk clean + full hermetic suite green with pre-phase tests unmodified in substance.

## Verdict: PASS — phase 2 is done

- Hermetic suite: **125/125** (35 contract tests via `FakeContractBackend`; pre-phase tests unmodified in substance, W2 harness refactor the sanctioned exception).
- Live suite: **35/35** (`flutter test test_live --concurrency=1`), same test bodies, `LiveContractBackend`.
- §3.6 walk: **every step observed clean** (record below).

## Live suite attempts ledger

| # | Deployment state | Harness turn deadline | Result | Notes |
|---|---|---|---|---|
| 1 | sync Coach, mis-wired serializers | 120s | 22/35 | All 13 failures triaged (binding doc as arbiter) to two adapter wire bugs: `timestamp` vs `ts`; row-counted `turn_count`. Fixed GB10-side (`208ebf1`). |
| 2 | sync Coach, wire fixed | 120s | **35/35** (11m52s) | Functional conformance proven; turns-with-history 36–48s flagged. |
| 3 | async Coach (ADR-ARCH-026) | 35s | 34/35 | One deadline spike — later attributed to concurrent LPA workload. |
| 4 | async Coach + concurrent LPA extraction | 60s | 32/35 | Degradation was llama-swap eviction by LPA's docling/VLM models (confound identified by Rich); async Coach exonerated. |
| 5 | async Coach, quiet GPU | 60s | **35/35** (3m33s) | Warm turns ~3.5s, cold-load ~22s — ADR-ARCH-026 numbers hold from the Mac. |

## §3.6 cross-device walk record (attempt: 1, clean)

Session `bf569219-b982-4d36-887c-100113ecb284`, student `lilymay` (dev token table entry #1). Screenshots in the session scratchpad (`walk_01`–`walk_10`); observed live by Rich.

1. **Emulator: sign in → home.** Real `list_sessions` over the tailnet returned empty; no connection dialog. ✅
2. **Emulator: start + 2 turns.** Real Socratic tutoring ("What is a fraction?" → pizza-slices prompt; "3/8?" → reply). Both inside the app's 15s product deadline. ✅
3. **Mac curl, same student: `list_sessions`** → the session, `status: active`, **`turn_count: 2`**. ✅
4. **Mac curl: `turn`** ("Hello from the second device …") → real reply continuing the thread. ✅
5. **Mac curl: `resume_session`** → **6 turns, strict order**, roles alternating user/tutor, timestamps monotonic (15:16:27 → 15:18:01). ✅
6. **Emulator: home re-list** → card shows **"maths, 3 turns"** (sees the curl-advanced count). ✅
7. **Emulator: Resume** → transcript renders **all six messages in order, including the curl-injected pair**. ✅
8. **Emulator: End session** → "Session ended" banner, input disabled, End affordance gone, transcript intact. ✅
9. **Mac curl: `session_status`** → `status: "ended"`, `resumable: false`, `turn_count: 3`, history preserved. ✅
10. **Bonus: emulator home** → ended session dropped off the resume list ("No active sessions"). ✅

## Notes for the record

- **Networking:** emulator reached the GB10 directly via the Tailscale IP through the emulator NAT — no host port-forward needed. (README's port-forward rule remains the fallback.)
- **Latency journey:** 43s warm turns (sync Coach, mis-modeled Coach LLM) → 8.5s first-turn / 36–48s with history (Coach model fixed, sync) → **~2–10s any turn** (async Coach). The one remaining latency item is tracked GB10-side as TASK-STREAM-001 (streaming, phase 2 of ADR-ARCH-026).
- **Operational:** the GB10 GPU is multi-tenant in practice (tutor set / LPA models / voice later) — live suite runs and demos want a quiet GPU (attempts 3–4 are the cautionary tale). Logged in `app/QUESTIONS.md`.
- Binding doc held as arbiter throughout; the app was never adapted to off-contract wire behaviour. `BINDING_SHA=6eb7b88c4c8ae412fb36327a4f56286c6b539a7a` unchanged since pin.

*Filed by the Mac session on walk completion; closes p2-wave-7 and the app side of FEAT-APP-001 (backend `/feature-complete` is the GB10 session's call).*
