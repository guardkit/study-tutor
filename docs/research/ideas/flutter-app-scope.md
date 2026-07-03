# Flutter App — v1 Scope (walking skeleton + one vertical slice)

**Status:** Ready for review — G-P1 gate artifact ([RUNBOOK-overnight-fable-flutter](../../runbooks/RUNBOOK-overnight-fable-flutter.md) §1). Verified against the contract pin by a 3-lens adversarial review, 2026-07-03; awaiting Rich's sign-off.
**Date:** 2026-07-03. **Owner:** Rich.
**Contract pin:** [API-session-cross-device.md](../../design/contracts/API-session-cross-device.md) at `CONTRACT_SHA=22791afbcdb3b71abbe6bd2f1b8e18218988942f` (ratified 2026-07-03). The app is built against the contract *at this SHA*; contract doubts go to `app/QUESTIONS.md`, never into contract edits.
**Related:** [ADR-ARCH-015](../../architecture/decisions/ADR-ARCH-015-uk-on-device-data-residency.md) (residency constraints), monorepo ADR (G-P2, forthcoming), [mobile+voice handoff](../../handoffs/study-tutor-mobile-voice-conversation-starter.md) (the eventual real backend).

---

## 1. What v1 is

Two things, nothing else:

1. **Walking skeleton** — the app boots and navigates between a sign-in screen, a home screen, and a session screen. The **verified target is Android** (`flutter analyze` clean, `flutter test` green, `flutter build apk --debug` succeeds — the runbook G-F0 gate). iOS/web platform folders exist from `flutter create` but v1 makes **no boot claim** for them; no wave may spend time on iOS/web plumbing (simulator boot is a morning check — runbook §4).
2. **One vertical slice** — the full session lifecycle from the ratified contract, end to end through real UI, against an **in-process fake backend**:
   - sign in (fake identity provider) → **start** a session
   - **exchange turns** (type a message, get a canned tutor response, transcript grows)
   - leave the session, **resume** it from the home screen — transcript reloads in order
   - **end** it — ended is terminal: no further turns, no resume.

No network. No real backend. No Keycloak. The value of v1 is a UI shell whose seams are *exactly* the contract's seams, so swapping the fake for the real HTTP/WS adapter later is an adapter change, not a redesign.

## 2. Architecture: two ports, two fakes

Ports-and-adapters, and only two ports:

### 2.1 `SessionApi` port

Mirrors the contract's six verbs 1:1, transport-neutral, same names and full return shapes ([contract §5](../../design/contracts/API-session-cross-device.md)):

`startSession` (with `subject`/`topic` and `resumeIfActive`) · `listSessions` · `resumeSession` · `turn` · `sessionStatus` · `endSession`

The **fake implements all six**; the v1 UI consumes five (`sessionStatus` is exercised by contract tests only). `turn` is the plain request/response shape (contract §7 HTTP variant) — **no streaming in v1**.

### 2.2 `IdentityProvider` port (auth as a port)

`signIn()` / `signOut()` / current-principal. (`signOut` completes the port but gets **no v1 UI affordance** — don't wire it into a screen.) A principal carries a token; **`student_id` is derived from the token by the backend port, never asserted by UI code** (contract §3). The fake ships with:

- a default single student (Lilymay — the contract's interim single-user mode as the degenerate case),
- a **second principal**, so ownership violations are constructible,
- an **invalidate-token** switch, so `Unauthenticated` is constructible.

No Keycloak, no OIDC library, no network. When Keycloak arrives, it's a second adapter behind the same port.

### 2.3 `FakeSessionApi` — the semantics it MUST implement

The fake is not a stub; it's a reference implementation of the contract's behavioural statements:

| Contract statement | Fake behaviour |
|---|---|
| States `active` \| `ended`; **`ended` is terminal** (§4) | any verb except `sessionStatus` on an ended session → `SessionEnded`; no re-open path exists |
| **`active` is resumable** (§4) | `resumeSession(sessionId)` on an active session returns it with ordered turns |
| `resume_if_active` keyed on **`(student, subject)`** (§5) | `startSession(resumeIfActive: true)` returns the existing active session *for that student and subject* (`resumed: true`, with turns); a different subject creates a new session |
| **Turns append-only, per-turn durable** (§4, §6) | each `(user, tutor)` pair is committed to the fake store as the turn completes; a second client object over the same store sees all completed turns mid-session |
| `turn_count` monotonic (§4 `session_version`) | increments per turn, never decreases, returned by `sessionStatus`/`listSessions` |
| `sessionStatus` full shape (§5) | returns `{session_id, student_id, status, turn_count, started_at, last_activity, resumable}`; `resumable` is true iff `active` |
| **Ownership** (§5): every `session_id` verb asserts owner | session's `student_id` ≠ caller's → `SessionForbidden` |
| Auth required (§3, §9) | missing/invalidated token on any verb → `Unauthenticated` |
| Unknown session (§9) | → `SessionNotFoundError` |
| `resumeSession` returns ordered transcript (§5, §6) | `[{role, content, ts}]` in turn order |

Errors are typed Dart exceptions carrying the contract's exact `error_type` strings (`SessionNotFoundError`, `SessionEnded`, `SessionForbidden`, `Unauthenticated` — the closed set of §9), so the future real-transport adapter maps the wire envelope 1:1.

Tutor responses are **canned and deterministic** (e.g. keyed off turn index) — no LLM, no cleverness. Determinism is what makes the contract tests exact.

## 3. Error handling is real

The fake can produce every error in the contract's closed set, and the UI must handle each without crashing. Two errors get distinct treatment because the app's behaviour genuinely differs; the other two share one generic surface — in v1 they are only reachable through the fakes in tests, and bespoke screens for unreachable states is agent time wasted:

- `Unauthenticated` → route to the sign-in screen
- `SessionEnded` → session screen shows ended state, input disabled
- `SessionForbidden` / `SessionNotFoundError` → one shared, non-crashing error surface ("can't open this session"), back to home

Each of the four is verified by a **widget test that induces the error through the fakes** (invalidate the token; seed a session owned by the second principal; end the session then attempt a turn; use an unknown id). No debug UI is needed to trigger errors — tests drive the fakes directly.

## 4. Contract tests (required, not optional)

A pure-Dart test suite (`test/contract/`) that checks `FakeSessionApi` against **statements in the contract doc**, each test named for the section it verifies. Minimum set:

1. §4 — start → active; end → ended; ended is terminal (turn/resume/end on ended → `SessionEnded`).
2. §4/§6 — turns are append-only: transcript order is insertion order; resume returns the full ordered transcript.
3. §4 — per-turn durability analogue: a second client instance over the same store, same student, resumes mid-session and sees every completed turn.
4. §4 — `turn_count` is monotonic across turns and preserved across resume.
5. §5 — `startSession(resumeIfActive)` returns the existing active session **for `(student, subject)`** (`resumed: true`, with turns) instead of creating a new one; a different subject, or omitting the flag, creates a new session.
6. §5 — every `session_id`-taking verb rejects a caller whose `student_id` isn't the owner with `SessionForbidden`.
7. §3/§9 — every verb without a valid token → `Unauthenticated`.
8. §9 — unknown `session_id` → `SessionNotFoundError`; `sessionStatus` is the one verb that still answers on an ended session, with `resumable: true` while active and `false` once ended.
9. §5 — `listSessions` reflects status filter and `turn_count`/`last_activity` after activity.

These tests are the moat: when the real adapter lands, the same suite runs against it (behind the same port) and *proves* fake and backend agree.

**Plus one happy-path widget test** (`test/slice/`): pump the real app with the fakes injected and drive the whole slice through actual widgets — sign in → start → two turns (transcript grows) → navigate away → resume from home (transcript intact) → end (input disabled). This is the test that makes `flutter test` fail if the screens are never wired to the port — without it an unattended run could go "green" on contract tests alone while the UI does nothing.

## 5. ADR-ARCH-015 constraints (binding on the app)

- **No telemetry, analytics, or crash reporting** — no Sentry, Crashlytics, Firebase, LogRocket. Any phase. Non-negotiable ([ADR-ARCH-015](../../architecture/decisions/ADR-ARCH-015-uk-on-device-data-residency.md)).
- **No network calls of any kind in v1** — the fake is in-process; there is nothing to leak.
- **Session data stays in memory** — v1 does not persist transcripts to device storage; the fake store dies with the process. (On-device persistence is a later, deliberate decision.)
- Logs: local debug console only.

## 6. Approved dependencies (closed list)

| Package | Kind | Why |
|---|---|---|
| Flutter SDK (`flutter`, `flutter_test`) | SDK | everything: Navigator for routing, `ChangeNotifier`/`ValueNotifier` + `ListenableBuilder` for state |
| `cupertino_icons` | runtime | ships with `flutter create`; leave it |
| `flutter_lints` | dev | ships with `flutter create`; `analyze` gate |

That's the whole list — **zero added runtime dependencies**. No `provider`/`riverpod`/`bloc` (built-in `ChangeNotifier` is enough at this size), no `go_router` (Navigator 1.0 is enough for three screens), no `dio`/`http` (no network), no codegen. Per runbook rule 5: anything an agent wants beyond this list goes in `QUESTIONS.md`, and the wave proceeds without it or blocks.

## 7. Explicitly OUT of v1

- Real HTTP/WS transport; any backend or `src/**` change; Alembic/schema anything
- Keycloak / OIDC / any real auth; token refresh; `sub → student_id` mapping (contract §11 OQ1)
- WS streaming `turn`, voice, STT/TTS, Reachy (contract §7 is future work)
- Concurrent-resume detection UX (`session_version` conflict handling — contract §11 OQ2)
- On-device persistence, offline queue, background sync, push notifications
- Multi-student UI, profiles, settings screens
- Theming/branding, animations, i18n, accessibility passes beyond Flutter defaults
- CI, golden tests, integration/simulator tests (runbook §4 — `flutter test` only overnight)
- State-management or navigation packages

## 8. Definition of done for v1

- Walking skeleton + slice behaviours in §1 demonstrable on the Android debug build (Android only — no iOS/web claim).
- Contract test suite (§4) green; happy-path slice widget test green; widget tests for all four error handlings green.
- Every wave commit satisfied the per-wave gate: `flutter analyze` clean, `flutter test` green, `flutter build apk --debug` succeeds (runbook §2 rule 2).
- Zero diff outside `app/**` + `docs/research/ideas/flutter-*` (runbook §2 rule 3).
- Morning gate = runbook §6, pre-registered in the build plan.

---

*Feeds G-P3: [flutter-app-build-plan.md](flutter-app-build-plan.md) breaks this into overnight waves.*
