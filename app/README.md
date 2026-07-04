# study_tutor_app — Flutter v1 (walking skeleton + one vertical slice)

Cross-device tutoring sessions against an **in-process fake backend** whose
seams are exactly the ratified session contract's seams. No network, no real
backend, no Keycloak (scope §1). The verified target is **Android**; iOS/web
folders exist but v1 makes no boot claim for them.

**Contract pin:** `docs/design/contracts/API-session-cross-device.md` at
`CONTRACT_SHA=22791afbcdb3b71abbe6bd2f1b8e18218988942f` (ratified 2026-07-03).
The app is built against the contract *at this SHA*; contract doubts go to
`QUESTIONS.md`, never into contract edits.

**Scope:** `docs/research/ideas/flutter-app-scope.md` ·
**Build plan:** `docs/research/ideas/flutter-app-build-plan.md` ·
**Wave log:** `PROGRESS.md`

## Run / test

```bash
cd app
flutter analyze            # must be clean
flutter test               # unit + contract + widget suites
flutter build apk --debug  # the G-F0 build gate
flutter run                # attended: Android emulator/device
```

Per-wave green gate = all three of analyze / test / apk-debug.

## Architecture: two ports, two fakes (scope §2)

```
lib/
  main.dart      composition root — the ONLY place fakes are constructed;
                 swapping in real HTTP/WS + Keycloak adapters is a change
                 here, not in the screens
  domain/        Session, TurnEntry, SessionSummary, Principal; typed errors
                 carrying contract §9's exact error_type strings (closed set,
                 plus the client-local TransportError — phase-2 scope §3.2)
  ports/         SessionApi (the six §5 verbs, 1:1, transport-neutral)
                 IdentityProvider (signIn/signOut/currentPrincipal)
  fakes/         FakeIdentityProvider — two principals (Lilymay default,
                 Alex for ownership tests), invalidate-token switch, and the
                 token → student_id introspection the fake backend trusts (§3)
                 FakeSessionApi — reference implementation of the contract's
                 behavioural statements over a shareable InMemorySessionStore
                 (a second client over the same store = a second device)
  ui/            sign-in / home / session screens (ports injected via
                 constructors; screens never import fakes) + the shared
                 scope-§3 error surfaces
```

Session data is in-memory only; no telemetry, analytics, crash reporting, or
network calls of any kind (ADR-ARCH-015; scope §5).

## Test map

### `test/contract/` — the moat (scope §4)

Checks `FakeSessionApi` against statements in the contract doc, named for the
sections they verify. When the real adapter lands, this same suite runs
against it behind the same port and proves fake and backend agree.

| File | Contract § | Scope §4 test |
|---|---|---|
| `s4_lifecycle_test.dart` | §4 | 1 — start→active; end→ended; ended is terminal (`SessionEnded` on turn/resume/end) |
| `s4_s6_append_only_transcript_test.dart` | §4/§6 | 2 — append-only; resume returns full ordered transcript; deterministic canned replies |
| `s4_durability_second_client_test.dart` | §4 | 3 — per-turn durability analogue: second client over the same store sees all completed turns mid-session |
| `s4_turn_count_monotonic_test.dart` | §4 | 4 — `turn_count` monotonic, preserved across resume |
| `s5_resume_if_active_test.dart` | §5 | 5 — `resume_if_active` keyed on (student, subject); ended never matches |
| `s5_ownership_test.dart` | §5 | 6 — every `session_id` verb asserts owner → `SessionForbidden` |
| `s3_s9_authentication_test.dart` | §3/§9 | 7 — every verb without a valid token → `Unauthenticated` (signed-out + stale-token shapes) |
| `s9_unknown_session_and_status_test.dart` | §9 | 8 — unknown id → `SessionNotFoundError`; `session_status` alone answers on ended; `resumable` flips with the transition |
| `s5_list_sessions_test.dart` | §5 | 9 — status filter, `turn_count`/`last_activity` after activity, limit |

### The other suites

- `test/slice/happy_path_test.dart` — the whole slice through real widgets:
  sign in → start → two turns → away → resume (transcript intact, in order)
  → end (input disabled). Fails if screens are never wired to the port.
- `test/errors/` — scope §3, one per induced error: invalidate token →
  sign-in; second-principal ownership → shared "can't open" surface;
  ended-elsewhere then turn → ended state, input disabled; unknown id →
  shared surface; throwing-stub transport failure → "connection problem"
  dialog, unsent input preserved (phase 2, all five port call paths).
- `test/ui/` — walking-skeleton boot/navigation + slice-I wiring tests.
- `test/unit/` — domain models, error strings (§9 verbatim), identity fake.

## Definition of done (scope §8)

- [x] Walking skeleton + slice behaviours demonstrable on the Android debug
      build (Android only — no iOS/web claim); verified at the 2026-07-04
      morning gate — Pixel 9a emulator walk through all slice checkpoints
      (see docs/runbooks/RESULTS-overnight-fable-flutter-2026-07-04.md)
- [x] Contract test suite (scope §4, tests 1–9) green
- [x] Happy-path slice widget test green
- [x] Widget tests for all four error handlings green
- [x] Every wave commit passed the gate: analyze clean, `flutter test`
      green, `flutter build apk --debug` succeeds
- [x] Zero diff outside `app/**` (+ allowed docs) — see `QUESTIONS.md` note
      on the phantom runbook deletion (`main` moved ahead post-branch)
- [x] Zero added runtime dependencies: `flutter` + `cupertino_icons`
      (scaffold) only; dev: `flutter_test` + `flutter_lints` (scope §6)
- [x] Dead scaffold code removed (counter demo replaced in wave-5)
