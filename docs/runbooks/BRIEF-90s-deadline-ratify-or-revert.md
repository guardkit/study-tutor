# BRIEF — the 90s turn deadline: ratify or revert (ruling-queue item 8)

**2026-08-07 · one page · one word wanted.** The app now waits **90s** per turn; the
contract's paper still says **p95 < 10s, hard ceiling 30s**. Plan receipt:
`docs/study-tutor-plan-of-record.md:69` (known-contradictions) and `:385` (housekeeping).

## 1. What changed, when, and why (git receipts)

- **`641c4b87` (2026-07-19)** — *"fix(app): raise session turn deadline 15s -> 90s for the
  spark LLM topology."* Text-turn deadline 15s → 90s. From the commit message: at the
  2026-07-18 D8 walk, warm turns took **26–34s** and a cold model load **~90s** — "every
  send timed out client-side while committing server-side, and each retry appended a
  duplicate turn."
- **`56b832e5` (2026-07-25)** — *"fix(app): raise voice-turn deadline 30s->90s to match the
  text turnBudget."* First live phone attempt: the server completed the voice turn **200 OK**
  (~40s server-side under factory load, `app/lib/adapters/http_voice_api.dart:38-40`) but the
  app's separate 30s deadline fired first — "'Connection problem' with a healthy server."
- **`fa8d95b8` (2026-08-03)** — the streaming voice path gained a matching 90s stall
  timeout (`streamEventTimeout`, `app/lib/ui/session_screen.dart:35`).

## 2. What the frozen contract actually says

The app-facing binding (`docs/design/contracts/API-session-http-binding.md`) has **no
latency section** — the word "latency" does not appear in it. The latency text lives in the
transport-neutral contract it pins, and in the MCP-era contract that one inherits from:

> "Same shape; now **persists the pair per-turn**. p95 < 10s budget unchanged."
> — `API-session-cross-device.md:64` (§5, `turn` row)

> "Latency target | p95 < 10s; hard ceiling 30s (SR-07)"
> — `API-tutoring.md:67` (§3.2 `tutor_turn`)

Read paths are separate and untouched: "Read-path budget < 2s" (`API-session-cross-device.md:100`).
No server code enforces the 30s ceiling — the only 30s timeout in the backend is a JWKS
fetch (`src/study_tutor/http/auth_keycloak.py:106`). The ceiling is paper only, and the
deployed server routinely runs 26–40s turns past it.

## 3. Current deployed behaviour (today's values)

| What | Value | Receipt |
|---|---|---|
| Text turn deadline | 90s | `app/lib/adapters/http_session_api.dart:58` |
| Other session verbs (reads) | 5s | `app/lib/adapters/http_session_api.dart:59` |
| Voice turn deadline | 90s | `app/lib/adapters/http_voice_api.dart:42` |
| Streaming stall timeout | 90s | `app/lib/ui/session_screen.dart:35` |

The backend is already **engineered against the 90s figure**: the TTS piece cap keeps the
voice worst case "near ~65 s against the app's 90 s deadline"
(`src/study_tutor/voice/service.py:56`, constant at `:61`), and the streamed-audio word cap
exists so a long reply can't "stall the stream past the app's 90s deadline"
(`src/study_tutor/voice/streaming_tts.py:31`, constant at `:34`).

## 4. The two rulings, honestly

**RATIFY** — a dated in-place annotation, the same instrument as the 2026-08-02 §2.2
annotation (`API-session-http-binding.md:72`) and the 2026-08-04 `start_session` annotation
(`:50`). No shape or status-code change ⇒ **no `CONTRACT_SHA`/`BINDING_SHA` re-pin**. It
would sit on the cross-device §5 `turn` row (with a pointer at `API-tutoring.md` §3.2) and
say, roughly: *"Dated annotation: on the spark llama-swap topology the client turn deadline
is 90s (commits `641c4b87`, `56b832e5`) — warm turns measured 26–34s (2026-07-18 D8 walk),
voice ~40s server-side under factory load (2026-07-25). The p95<10s / 30s-ceiling figures
assumed an unloaded GB10 and stand as a serving-side aspiration, not a client-abandonment
threshold. No shape change; no re-pin."*

**REVERT** — restore 15s (text) / 30s (voice). By measurement, this breaks live use today:
every warm text turn (26–34s) exceeds 15s; voice turns run ~40s server-side and up to ~65s
worst case — TTS alone costs **~10–12s per audio piece, up to 2 pieces/turn**
(`docs/runbooks/known-issues.md:77-78`). Each client timeout on a turn that later commits
reinstates the duplicate-turn-appending retry defect `641c4b87` fixed. Reverting is only
honest after the server is brought under the ceiling — and that serving work is unscoped
(the voice reply cap / synthesis cost follow-up is already a named deferral,
`known-issues.md:82-84`).

## 5. Recommendation and the ask

**RATIFY.** The 90s value is measurement-backed, live-proven since 2026-07-19, and the
backend's voice budgets are built against it; reverting reintroduces a known defect and
gains nothing until serving gets faster. The 30s figure survives inside the annotation as
the serving-side aspiration it always was.

**The ask — one word: "ratify" or "revert".** On *ratify*, the dated annotation above lands
in place (no re-pin) and plan contradiction `:69` closes. On *revert*, the app deadlines
return to 15s/30s only after a serving-latency workstream is scoped first.
