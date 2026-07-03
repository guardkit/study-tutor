# Flutter App — Overnight Build Plan (waves)

**Status:** Ready — G-P3 gate artifact ([RUNBOOK-overnight-fable-flutter](../../runbooks/RUNBOOK-overnight-fable-flutter.md) §1).
**Date:** 2026-07-04. **Owner:** Rich.
**CONTRACT_SHA:** `22791afbcdb3b71abbe6bd2f1b8e18218988942f` — [API-session-cross-device.md](../../design/contracts/API-session-cross-device.md) at this commit is the pinned truth. Contract doubts → `app/QUESTIONS.md`, never contract edits (runbook §2 rule 3).
**Scope:** [flutter-app-scope.md](flutter-app-scope.md) (G-P1) — defines the fake's semantics (§2.3), the test suites (§3–4), the approved-dependency list (§6), and what's OUT (§7). This plan only sequences it.
**Structure:** [ADR-ARCH-025](../../architecture/decisions/ADR-ARCH-025-flutter-app-in-monorepo.md) — app lives at `app/`.
**Build gate (G-F0 choice):** `flutter build apk --debug`.

---

## 1. Wave discipline (runbook §2, restated operationally)

- At each wave start: re-read this plan + `app/PROGRESS.md`. Disk is truth, not conversation memory. One wave at a time.
- **Green =** `cd app && flutter analyze` clean + `flutter test` green + `flutter build apk --debug` succeeds.
- On green: tick the wave in `PROGRESS.md`, append a log line, then commit `wave-N: <name> [green]` — the PROGRESS.md update rides *inside* the wave's single commit (this is the operational reading of runbook §2 rule 2's "commit … append PROGRESS.md"). Never start wave N+1 on a red wave N.
- A wave failing twice → mark it blocked in `PROGRESS.md`, jump to the next wave whose dependencies (§3) are all green. Two blocked waves → stop cleanly per runbook §2 rule 6.
- Write only under `app/**` (+ `docs/research/ideas/flutter-*` if strictly needed). Dependencies beyond scope §6's closed list → `QUESTIONS.md`, not `pubspec.yaml`.

**Target layout** (so waves don't re-litigate structure):

```
app/lib/
  main.dart          # composition root — fakes constructed + injected here (from wave-6 on)
  domain/            # models: Session, TurnEntry, SessionSummary, Principal; typed errors
  ports/             # SessionApi, IdentityProvider (abstract)
  fakes/             # FakeIdentityProvider, FakeSessionApi (+ its in-memory store)
  ui/                # app widget, sign-in / home / session screens
app/test/
  unit/              # wave 1–2
  contract/          # wave 3–4 — scope §4 suite, tests named for contract §s
  slice/             # wave 7 — happy-path widget test
  errors/            # wave 8 — four error-handling widget tests
```

## 2. Waves

Each is ~1–2 h of agent work, ends green, and is one commit.

### wave-0: flutter scaffold [green] — ✅ done attended, 2026-07-03
`flutter create --project-name study_tutor_app --org com.appmilla --platforms android,ios,web app`; analyze clean, test green, apk-debug built. Baseline commit.

### wave-1: domain model + SessionApi port + typed errors
Pure Dart, no UI. `domain/`: `Session` (id, studentId, subject, topic, status, startedAt, lastActivity, turnCount), `TurnEntry` (role, content, ts), `Principal` (token, displayName). Typed exceptions carrying the contract's exact `error_type` strings: `SessionNotFoundError`, `SessionEnded`, `SessionForbidden`, `Unauthenticated` (closed set, contract §9). `ports/session_api.dart`: the six verbs, contract §5 names and full return shapes (incl. `resumed`, `resumable`, `turn_count`). Unit tests: error `errorType` strings, model equality/ordering basics.
**Done when:** port compiles with all six verbs; error strings match contract §9 verbatim; green.

### wave-2: IdentityProvider port + FakeIdentityProvider
`ports/identity_provider.dart`: `signIn()`, `signOut()`, current principal (`signOut` gets no UI — scope §2.2). `fakes/fake_identity_provider.dart`: two principals (default student Lilymay + a second student for ownership tests), an invalidate-token switch (`Unauthenticated` becomes constructible). Unit tests: sign-in yields principal; invalidated token is detectable.
**Done when:** both principals + invalidation usable from tests; green.

### wave-3: FakeSessionApi core + contract tests I (lifecycle)
`fakes/fake_session_api.dart` over an in-memory store; caller identity resolved per call from `IdentityProvider` (UI never passes `student_id` — contract §3). Deterministic canned tutor replies keyed off turn index. Implement: `startSession` (with `(student, subject)`-keyed `resumeIfActive` — scope §2.3), `turn` (append pair, bump `turn_count`), `resumeSession`, `endSession`, `sessionStatus` (full §5 shape, `resumable` iff active). Contract tests (scope §4) **1, 2, 4, 5**: start→active; end→ended; ended terminal (`SessionEnded` on turn/resume/end); append-only ordering; `turn_count` monotonic incl. across resume; `resumeIfActive` keying.
**Done when:** those tests green against the fake; green gate.

### wave-4: ownership + auth + errors + listSessions — contract tests II
Ownership assert on every `session_id` verb → `SessionForbidden` (test 6, using the second principal); token check on every verb → `Unauthenticated` (test 7); **test 8 in full** (unknown id → `SessionNotFoundError`; `sessionStatus` alone answers on an ended session; `resumable` true while active, false once ended — wave-4 owns all of test 8, wave-3 wrote none of it); `listSessions` with status filter, `turn_count`, `last_activity` (test 9); second-client-over-same-store mid-session durability analogue (test 3).
**Done when:** full scope-§4 contract suite (1–9) green; green gate.

### wave-5: walking skeleton UI
`ui/`: app widget + Navigator 1.0 routes for sign-in / home / session screens — **placeholder content, zero port references**: this wave touches no fakes and no ports, so it stays executable even if waves 2–4 are blocked. State plumbing (`ChangeNotifier`/`ListenableBuilder`, no new deps — scope §6) can be introduced here on placeholder state. Widget test: app boots to sign-in; navigation between the three screens works.
**Done when:** boot + navigation widget test green; green gate. *Morning boot checkpoint: app launches to sign-in and navigates.*

### wave-6: slice I — sign in, start, exchange turns
Wire the composition root: `main.dart` constructs `FakeIdentityProvider` + `FakeSessionApi` and injects them via constructors. Sign-in screen drives `IdentityProvider.signIn()` → home. Home: "Start new session" (fixed subject is fine for v1) → `startSession` → session screen. Session screen: transcript list + input; send → `turn` → canned reply appended, transcript grows. Widget tests: sign-in→home; start→session screen; one turn round-trip renders both messages.
**Done when:** those widget tests green; green gate. *Morning boot checkpoint: can start a session and exchange turns.*

### wave-7: slice II — resume + end + happy-path test
Home lists the active session via `listSessions` with a Resume affordance → `resumeSession` → transcript reloads in order. Session screen End button → `endSession` → ended state, input disabled. **The happy-path slice widget test** (scope §4 close): sign in → start → two turns → navigate away → resume (transcript intact) → end (input disabled) — the test that fails if screens aren't wired to the port.
**Done when:** happy-path test green; green gate. *Morning boot checkpoint: full slice works on device.*

### wave-8: error handling (scope §3)
`Unauthenticated` → route to sign-in; `SessionEnded` → ended state, input disabled; `SessionForbidden`/`SessionNotFoundError` → one shared non-crashing "can't open this session" surface, back to home. Four widget tests inducing each error through the fakes (invalidate token; seed second-principal session; end-then-turn; unknown id).
**Done when:** four error tests green; green gate. *Morning boot checkpoint: no error state crashes the app.*

### wave-9: hardening + app README
`app/README.md`: how to run/test; map of `test/contract/` tests → contract §s; ports/fakes overview; the CONTRACT_SHA pin. Sweep vs scope §8 DoD; delete dead scaffold code (counter demo); confirm pubspec still has zero added runtime deps.
**Done when:** DoD checklist in README all ticked; green gate.

## 3. Dependency map (for the blocked protocol)

A wave may start only when every wave in its "needs" column is committed green:

| wave | needs | notes |
|---|---|---|
| 1 | 0 | pure Dart |
| 2 | 1 | |
| 3 | 2 | fake resolves caller via IdentityProvider |
| 4 | 3 | |
| 5 | 0 | **the only fake-independent wave** — no ports, no fakes |
| 6 | 3, 5 | composition root wires the fakes |
| 7 | 4, 6 | resume UI needs `listSessions` (wave-4) |
| 8 | 7 | error tests exercise wave-4 behaviours through wave-6/7 screens |
| 9 | 8 | |

Fallback routing: if the fake chain (2/3/4) blocks, wave-5 is the one independent jump; once it's green and the chain is still blocked, nothing else is startable — stop cleanly (runbook §2 rule 6). If wave-5 blocks, continue the fake chain.

**Attempt accounting:** if a UI wave (6+) goes red because the fake is defective, fixing the fake is part of the **current wave's** attempt — the fix rides the current wave's commit, and it is the *current* wave's failure counter that increments on a second red. Committed green waves stay closed; never re-open or amend their commits.

## 4. Morning-after gate — pre-registered success bar (runbook §6, copied verbatim)

- Every commit at HEAD re-verifies green (spot-run analyze + test).
- App boots on simulator to the wave-defined checkpoint (attended, morning).
- `git diff main --stat` shows **zero** files outside `app/**` + allowed docs.
- PROGRESS.md coherent; QUESTIONS.md triaged.
- **Fable data point recorded:** waves attempted / completed / blocked, defects found in review, quota consumed. (Second entry in the hype ledger; interventions = 0 by construction.)
- Any red → `git worktree remove` + branch delete is the whole rollback; green commits survive regardless. Whatever didn't land is still in the build plan — Opus or local resumes from the same artifact.

*Pre-registered clarification (attended, 2026-07-04): "boots on simulator" reads as the Android emulator for this run — scope §1 makes no iOS/web boot claim and G-F0 verified the Android toolchain only.*

---

*Instruments: `app/PROGRESS.md` (wave checklist + log + HANDOFF) and `app/QUESTIONS.md` (G-R1). Optimise for waves that survive review, not waves attempted.*
