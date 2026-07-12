# Spec — Flutter App UX Revamp + Gamification UI (Lane A, MacBook Pro)

**Status:** BINDING spec for the Lane A orchestrated build — 2026-07-12. Build to it verbatim; visual judgment calls within it are settled at the attended Phase-A mockup review (⏸) before the build stages run. Parent doc: `docs/research/ideas/gamification-engine-and-app-ux-scope-and-build-plan.md` (D11–D14, R2 "warm academic" adopted).
**Upstream (binding):** `docs/design/contracts/API-session-http-binding.md` + its gamification addenda / Revision 2 (Lane B §6 — gate for §6 below) · `app/` existing port/fake/adapter conventions.
**Ground truth:** `app/lib` as of `main` @ `a81ec5d` — three screens, no theme, `setState` only, ports prop-drilled; defects list in parent doc §1/§5.

---

## §1 Design system ("warm academic" — R2)

- **Color**: Material 3, `ColorScheme.fromSeed`. Seed **`#324376`** (deep ink indigo); tertiary steered to warm gold **`#B98A2E`**-family. Both `light` and `dark` schemes from day one; `themeMode: ThemeMode.system`. No hardcoded `Colors.*` anywhere in `lib/ui` — everything through the scheme or the tokens below (the two existing hardcoded amber/red banners migrate).
- **Semantic band tokens** (design.md §6.1, must read in both modes — light/dark pairs): `struggling` `#C4453C`/`#E58A82` · `developing` `#B98A2E`/`#E3B95C` · `secure` `#3E6FA3`/`#8FB8E0` · `mastered` `#3F8F5F`/`#7FC79B`. Exposed via a `BandColors` ThemeExtension.
- **Typography**: body/UI = platform default (Roboto/SF). Display face for headings, level titles, and celebration numerals: **Lora** (OFL), bundled as an asset — no runtime font fetching. Type scale: display 28/24, title 18, body 15, label 12.
- **Shape & space**: 4-pt grid; card radius 12; screen gutter 16; list item padding 12/16.
- **Motion**: standard transitions 200–300 ms `easeOutCubic`; XP count-up 800 ms; celebration confetti burst ≤1.2 s used ONLY where design.md specifies celebration (achievement unlock, level-up; later daily-sweep) — never on routine actions. Streak flame gets a subtle idle pulse on the Home card only when the streak is alive today.
- **Register**: engaging but not childish (Year 10/11). No mascots, no streak-shaming copy; empty states are warm and specific ("No sessions yet today — 20 minutes keeps your 6-day streak alive") not bare strings.

## §2 App architecture changes (minimal, no new packages)

- **`AppScope`** InheritedWidget at the root composing the ports (`SessionApi`, `VoiceApi`, `IdentityProvider`, new `StudentModelApi`) — replaces constructor prop-drilling; screens read ports via `AppScope.of(context)`. Constructor injection stays available for widget tests (scope wraps, tests inject).
- **`ProgressStore`** `ChangeNotifier` owning the student-model snapshot (fetch, cache, refresh-after-session-end); no provider/riverpod/bloc/go_router — pubspec gains ONLY the Lora font asset. Navigator 1.0 stays.
- New port triplet **`StudentModelApi`** (port + `HttpStudentModelApi` + `FakeStudentModelApi`) mirroring `composeSessionApi` (`main.dart:24-32`), composed against the **`IdentityProvider` interface** (KC-D7-proofing, D10).

## §3 Screen refits

- **SignIn**: app name in display face + one-line purpose + the existing button; shows `Principal.displayName` choices if multiple principals exist (fake has two). Post-Keycloak this screen is replaced — keep it minimal.
- **Home**: AppBar shows greeting with `displayName` + overflow menu with Sign out (wired to the port; clears to SignIn). Above the list: the **Progress header card** (§6.1). Session cards: title-cased subject, relative timestamp from `SessionSummary.lastActivity`, turn count, Resume affordance; specific empty state per §1.
- **Session**: AppBar title = title-cased subject/topic (from start response once Lane B §2.1 lands; subject until then) + End session. Transcript: timestamps on long-press, `animateTo` scrolling, optimistic user bubble on send + three-dot typing indicator while awaiting the reply (text and voice); failed sends mark the bubble with retry. Banners become dismissible `MaterialBanner`s themed via the scheme; blocking dialogs remain ONLY for the two §9-contract cases (can't-open, connection-problem) unchanged in behavior. Recording UI: prominent mic (56 dp FAB-style), live ticking elapsed label (Timer.periodic), pulsing red while recording.
- **Progress screen** (new, pushed from Home): §6.3.

## §4 UX defect fixes (from parent doc §1/§5 — all in scope)

Optimistic send + typing indicator (kills the 15–30 s frozen wall) · dismissible banners · `animateTo` · timestamps rendered · title-cased subject · identity display + sign-out · ticking recording timer · `VoiceUnavailable` gets a retry path when leaving/re-entering the screen (mic no longer permanently dead) · hardcoded 320 px bubble width → 76% of width, max 560.

## §5 Voice fixes (production defects — all in scope)

1. `VoiceRecorder.stop()` returns the REAL recorded file bytes (today: 100-byte placeholder, `lib/fakes/fake_voice_api.dart:298-301`); enforce the declared 10 MB cap; class moves out of `lib/fakes/` into `lib/adapters/voice_recorder.dart` (the fake keeps a mock).
2. **TTS playback**: `AudioAnswerPart` chunks are fetched via the existing `fetchAudioChunk` adapter and played via `just_audio` (already declared), sequentially, with a stop control; text renders as today alongside.
3. WS streaming client (`voiceTurnStream`) stays **unwired** — deferred to TASK-STREAM-001 with the server-side fix (Lane B §2.7). Do not delete the adapter or its tests.

## §6 Gamification UI (GATED on Lane B §6 contract docs being ratified — build against fakes immediately after)

### §6.1 Progress header card (Home)
Level title in display face + `LevelProgressBar` (xp_into_level / xp_to_next_level) + `StreakBadge` (flame + count; greyed with "ends tonight" hint when yesterday-anchored) + this-week XP. Tap → Progress screen. Data: `GET /api/student-model` via `ProgressStore`; `data_available:false` renders the card in a warm zero-state, never hidden.

### §6.2 Session-end celebration sheet
On `endSession` returning a non-null `gamification` block: modal bottom sheet — XP count-up (800 ms), streak row (`streak_extended` → flame tick animation), unlock cards for `achievements_unlocked` (staggered, confetti per §1 motion), level-up moment when `level_up` (old→new title crossfade in display face). Dismiss → pop to Home + `ProgressStore.refresh()`. Block is nullable: absent → today's plain pop (no fake celebration, ever). `EndSessionResult` gains the optional typed block; `FakeSessionApi` models it deterministically over `InMemorySessionStore` (fixed XP per fake session shape) so contract tests pin exact values while live tests assert invariants (non-negative, monotonic total) — the established `expectedTutorReply` pattern.

### §6.3 Progress screen
Sections: level + progress (as §6.1, larger) · streak current/longest · **mastery grid** — `topic_confidence` entries as band-colored cells (BandColors + band label, design §6.1 phrasings) with a "how bands work" info sheet · **near-unlocks** — top 3 `near_achievements` as cards with progress bar + `hint` line · **recent achievements** — last 5 with dates and XP. Empty states per §1 register. No quests/boss-battle panels (not built — no placeholder chrome for absent features).

## §7 Tests & fences

- Widget tests for every new component and refit behavior (optimistic send, ticking timer, celebration sheet from a canned block, band token resolution light+dark); contract suite extended via the `ContractBackend` seam (a `studentModelApi` member on both backends); adapter unit tests for `HttpStudentModelApi` (auth header, 401/400 mapping, shape). No goldens this lane (visual sign-off is the ⏸ mockup review + attended emulator walk).
- Fences: blast radius `app/**` only; no backend/source changes outside `app/`; no new pub dependencies beyond the bundled font; existing 125+ hermetic tests stay green; established port names/shapes unchanged except the specified additive `EndSessionResult` field; never commit `.claude/`/`.guardkit/`.

## §8 Out of scope (Lane A)

Subject picker (v1 stays 'english', display-cased) · streaming token UI (TASK-STREAM-001) · Keycloak sign-in UI (FEAT-AUTH lane) · parent views (KC-D5) · quests/daily-challenges/boss-battle UI · tablet/desktop layouts (phone-first, must not crash on tablet).

---

*Written 2026-07-12. Visual constants (§1) are Phase-A proposals — the attended mockup review (⏸, Rich) may adjust hue/type values; structural sections §2–§8 are binding as written. All rulings adopted at recommended values per the parent scope doc.*
