# study_tutor_app — Flutter v1 (walking skeleton + one vertical slice)

Cross-device tutoring sessions against the ratified session contract's
seams. The **default flavour** composes an in-process fake backend — no
network, no Keycloak (v1 scope §1), and the hermetic test gate only ever
runs this flavour. Phase 2 added an opt-in **real-transport flavour**
(`--dart-define=API_BASE_URL=…` → `HttpSessionApi`, see §Phase-2 flavours).
The device-walked target is **Android** (see Definition of done). **iOS**
compiles and runs the hermetic slice green; a live simulator walk is pending an
attended run — see [§iOS](#ios-compiles--hermetic-green-live-walk-pending). The
web folder still carries no boot claim.

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
flutter test               # HERMETIC suite — unit + contract + widget (no network)
flutter build apk --debug  # the G-F0 build gate
flutter run                # attended: Android emulator/device (fake backend)
```

Per-wave green gate = all three of analyze / test / apk-debug.

### Hermetic vs live suites

- **Hermetic** (`test/`) — the gate. Runs entirely against the in-process
  fakes; no network, no GB10, no Keycloak. This is what `flutter test` and CI
  run, and every stage commit must keep it green.
- **Live** (`test_live/`) — the SAME contract-suite bodies run against the real
  HTTP adapter on the GB10 deployment. It is opt-in and never part of the
  hermetic gate: it requires the deployment and is invoked explicitly with a
  base URL and single-threaded so runs don't race on shared server state:

  ```bash
  flutter test test_live \
    --dart-define=API_BASE_URL=http://<gb10>:8100 \
    --concurrency=1
  ```

  Without `API_BASE_URL` the live suite fails fast by design (see
  `test_live/README.md`). Do not run it as part of local iteration.

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

## iOS: compiles + hermetic green, live walk pending

This repo is checked out on a Mac, so iOS is brought to a real (honest) boot
claim — no simulator walk is asserted that was not run.

**What is claimed now:**

- The app **compiles for iOS**: every adapter that touches native code
  (`voice_recorder.dart`, `audio_playback.dart`, `http_voice_api.dart`) sits on
  cross-platform `dart:io` (`File`, `Directory.systemTemp`, `WebSocket`) with no
  Android-only paths. `record`'s default encoder is AAC-LC/m4a — the iOS/Android
  shared codec.
- The **hermetic suite is platform-agnostic**: `flutter test` runs entirely
  against the in-process fakes (`FakeVoiceRecorder`, injected `AudioPlayback`
  mocks) and passes under the same gate regardless of host OS — screens never
  reach a real mic or player in tests.
- `ios/Runner/Info.plist` carries the usage strings the bundled plugins need on
  iOS: **`NSMicrophoneUsageDescription`** (for `record`) and the intact
  **`com.appmilla.studytutor`** URL scheme under `CFBundleURLTypes` (the
  Keycloak OAuth2 redirect, ASSUM-003 frozen scheme — used by `flutter_appauth`).
  `just_audio`, `flutter_secure_storage`, `web_socket_channel`, and
  `path_provider` need no additional plist strings for our foreground use.
- The Xcode **deployment target is iOS 13.0**, which satisfies the minimum of
  every runtime plugin (`record` / `just_audio` / `flutter_appauth` /
  `flutter_secure_storage`). `AppDelegate.swift` registers the generated plugin
  set; `SceneDelegate` is in place.

**What is NOT yet verified:** a **live simulator/device walk** — signing in,
recording a real turn, hearing TTS playback, and resuming on an iOS simulator.
That requires an attended run (`cd app && flutter run` with a booted simulator,
after `pod install`) and has not been performed from this environment. Treat the
iOS claim as "compiles + hermetic suite green"; promote it to a device claim
only after that attended walk (mirror the Android entry in Definition of done).

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

## App shell, theming, voice & gamification (Lane A, S-A1–S-A4)

The UX revamp (`docs/design/app-ux-and-gamification-ui-spec.md`) added the
gamification surfaces and a small app shell on top of the v1 slice. No new
runtime packages beyond the bundled display font — no provider/riverpod/bloc,
Navigator 1.0 stays.

### Composition & state

- **`AppScope`** (`lib/ui/app_scope.dart`) — a root `InheritedWidget` that
  composes the four ports (`SessionApi`, `VoiceApi`, `IdentityProvider`,
  `StudentModelApi`) so screens read them via `AppScope.of(context)` instead of
  constructor prop-drilling. Constructor injection stays available for widget
  tests (the scope wraps; tests inject directly).
- **`ProgressStore`** (`lib/ui/progress_store.dart`) — a `ChangeNotifier` owning
  the student-model snapshot: fetch, cache, and refresh-after-session-end. A
  failed refresh keeps the last good snapshot (the Home card is never blanked).
  "Streak alive today" is app-local UX state (no wire field) — it flips true
  only once a session-end block reports `streak_extended` during the app run.
- **`SubjectStore`** (`lib/ui/subject_store.dart`) — a `ChangeNotifier` owning
  the selected tutoring subject (Lane 1 step 2). The offer is a client-side
  constant (`availableSubjects`, English-only today — a server endpoint would
  be a contract addition, deferred until content packs exist); the Home picker
  is visible even with one subject (Rich's call 2026-08-02). `defaultSubject`
  (`home_screen.dart`) stays the fallback and the cross-repo seam anchor
  (`tests/seam/test_subject_default.py`). The shell wires selection changes
  into `ProgressStore.updateSubject`, so the progress read follows the picked
  subject; resume keeps each session's own subject. Session-scoped — nothing
  persists across launches.
- **Port triplet** `StudentModelApi` — port (`lib/ports/student_model_api.dart`)
  + `HttpStudentModelApi` adapter + `FakeStudentModelApi`, composed in
  `main.dart` on the `API_BASE_URL` flavour switch exactly like `SessionApi`.
  The `end_session` settlement is an additive optional `gamification` block on
  `EndSessionResult`; absent means absent (a plain pop, never a fabricated
  celebration).

### Theming (`lib/ui/theme/`)

- `AppTheme` builds **both** light and dark schemes from a single indigo seed
  (`#324376`) with `ColorScheme.fromSeed`; `themeMode: ThemeMode.system`. The
  tertiary role is steered to warm gold via `copyWith` (⏸A-pinned role values).
- **`BandColors`** — a `ThemeExtension` carrying the four topic-mastery band
  colours (struggling / developing / secure / mastered) in light and dark
  pairs, read via `BandColors.of(context)`. No `Colors.*` literals live in
  `lib/ui`; every colour resolves through the `ColorScheme` or `BandColors`.
- **Display face** — Bricolage Grotesque (OFL), bundled at `assets/fonts/`
  and declared in `pubspec.yaml` (weights 400/500/600/700). Applied to
  headings, level titles, and the celebration XP numeral only; body/UI keep the
  platform default (Roboto/SF). Motion constants live in `lib/ui/theme/motion.dart`
  (`AppMotion`) so every animation shares one timing vocabulary.

### Voice pipeline

- **Recording** — `VoiceRecorder` (`lib/adapters/voice_recorder.dart`) captures
  real microphone bytes (`record`), enforcing the 10 MB cap; the session screen
  shows a 56 dp mic with a ticking elapsed label and a pulsing-red recording
  state. `FakeVoiceRecorder` (in `lib/fakes/`) is the hermetic mock.
- **TTS playback** — spoken-answer `AudioAnswerPart` chunks are fetched via the
  voice adapter and played sequentially through `just_audio`
  (`lib/adapters/audio_playback.dart`), with a stop control; answer text renders
  alongside.
- The WebSocket streaming client (`voiceTurnStream`) is **wired** — the
  session screen's streaming voice send consumes it
  (`lib/ui/session_screen.dart`, TASK-STREAM-001; this note previously
  said "stays unwired", stale since the wiring landed).

### Gamification surfaces (`lib/ui/gamification/`)

- **Progress header card** (Home) — level title, `LevelProgressBar`,
  `StreakBadge` (flame + count; "ends tonight" nudge when yesterday-anchored),
  this-week XP; `data_available:false` renders a warm zero-state, never hidden.
- **Session-end celebration sheet** — only on a non-null `gamification` block:
  XP count-up, streak tick, staggered achievement-unlock cards, level-up
  crossfade, and a confetti burst (achievement/level-up only). Dismiss pops to
  Home and refreshes the store.
- **Progress screen** — level + progress, streak current/longest, a
  band-coloured mastery grid with a "how bands work" sheet, top-3 near-unlocks,
  and recent achievements. Warm, specific empty states throughout.

### Accessibility & resilience (S-A4)

Every new component carries a `Semantics` label (header card reads as one
button; badges, mastery/near/recent cells, celebration elements, and the
mic/recording/typing states are all labelled). The Home header card and the
celebration sheet are text-scale resilient at 1.3× (the sheet scrolls; wide
rows flex) — pinned by widget tests in `test/ui/s_a4_hardening_test.dart`.

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
