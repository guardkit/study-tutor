# study_tutor_app — Flutter v1 (walking skeleton + one vertical slice)

Cross-device tutoring sessions against the ratified session contract's
seams. The **default flavour** composes an in-process fake backend — no
network, no Keycloak (v1 scope §1), and the hermetic test gate only ever
runs this flavour. Phase 2 added an opt-in **real-transport flavour**
(`--dart-define=API_BASE_URL=…` → `HttpSessionApi`, see §Phase-2 flavours).
The verified target is **Android**; iOS/web folders exist but carry no boot
claim.

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

## Phase-2 flavours (phase-2 scope §3.3)

One compile-time switch — no settings UI:

```bash
# Hermetic flavour (default): fake backend, exactly v1 behaviour.
flutter run

# Real-transport flavour: HTTP adapter against the GB10 dev deployment.
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8100
```

Base-URL rule: on the **Android emulator**, `10.0.2.2` is the host machine's
**own loopback** (127.0.0.1 of the dev machine) — not a gateway onto the
host's tailnet. To reach the GB10 adapter from the emulator, either forward
the port on the host first (`ssh -L 8100:localhost:8100 <gb10>`, then
`API_BASE_URL=http://10.0.2.2:8100`) or point `API_BASE_URL` at the GB10's
tailnet address directly and let the emulator's NAT route it — the wave-7
attended run records which of the two the walk actually used. On a
**physical device** on the tailnet, use the GB10's MagicDNS hostname
directly.

Cleartext posture, honestly stated: the app's own `package:http` traffic
rides `dart:io`, which on current Flutter engines does **not** consult
Android's network-security-config and allows cleartext HTTP to any host,
debug and release alike (engine-verified in the wave-5 review). The
debug-only `network_security_config.xml` is kept as hygiene — it scopes any
future Android-platform-stack traffic (WebView/native plugins, e.g. a WS
voice plugin) to named backend hosts, but it does not constrain
`HttpSessionApi`. The real residency guarantee stays ADR-ARCH-015 discipline:
`API_BASE_URL` only ever points at household/Tailscale infrastructure
(fail-closed Dart-side enforcement is an open question in `QUESTIONS.md`).
Identity stays the fake IdP in both flavours; its constant token is the
binding doc's dev-table entry #1.

## Architecture: two ports, two fakes (scope §2)

```
lib/
  main.dart      composition root — the ONLY place adapters are constructed;
                 composeSessionApi() switches fake ↔ HttpSessionApi on the
                 API_BASE_URL define (Keycloak later lands here the same way)
  domain/        Session, TurnEntry, SessionSummary, Principal; typed errors
                 carrying contract §9's exact error_type strings (closed set,
                 plus the client-local TransportError — phase-2 scope §3.2)
  ports/         SessionApi (the six §5 verbs, 1:1, transport-neutral)
                 IdentityProvider (signIn/signOut/currentPrincipal)
  adapters/      HttpSessionApi — the real transport behind SessionApi
                 (phase 2; binding table API-session-http-binding.md at
                 BINDING_SHA 53f2fc5 — the S-R2 Revision-2 ratification commit,
                 superseding the phase-2 pin 6eb7b88)
                 HttpStudentModelApi — the real GET /api/student-model read
                 (S-A3; binding §2.2/§2.2.1 at the same BINDING_SHA 53f2fc5)
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

Checks a backend against statements in the contract doc, named for the
sections they verify. Since p2-wave-2 the suite is written against the
`ContractBackend` harness abstraction (`contract_backend.dart`: clients bound
to a principal, principal switch, token invalidation, `secondClient()`,
`reset()`, reply/clock expectations). Each file's `main()` wires
`FakeContractBackend` (hermetic — exactly the v1 harness behind the
interface); p2-wave-6's `test_live/` reuses the same `run…Tests` bodies
against the real HTTP adapter, so "fake and backend agree" is one suite run
twice.

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
