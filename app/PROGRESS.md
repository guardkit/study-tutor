# PROGRESS — overnight Flutter build (study_tutor_app)

**Build plan:** `docs/research/ideas/flutter-app-build-plan.md` (CONTRACT_SHA pinned in its header — re-read plan + this file at every wave start).
**Rules:** `docs/runbooks/RUNBOOK-overnight-fable-flutter.md` §2.
**Green =** `cd app && flutter analyze` clean + `flutter test` green + `flutter build apk --debug` succeeds.

## Waves

- [x] wave-0: flutter scaffold [green] — attended, 2026-07-04
- [x] wave-1: domain model + SessionApi port + typed errors [green] — unattended, 2026-07-04
- [x] wave-2: IdentityProvider port + FakeIdentityProvider [green] — unattended, 2026-07-04
- [x] wave-3: FakeSessionApi core + contract tests I (lifecycle) [green] — unattended, 2026-07-04
- [x] wave-4: ownership + auth + errors + listSessions — contract tests II [green] — unattended, 2026-07-04
- [x] wave-5: walking skeleton UI [green] — unattended, 2026-07-04
- [ ] wave-6: slice I — sign in, start, exchange turns
- [ ] wave-7: slice II — resume + end + happy-path test
- [ ] wave-8: error handling (scope §3)
- [ ] wave-9: hardening + app README

## Log

- 2026-07-04 — wave-0 [green], attended. Scaffold created (`flutter create`, org com.appmilla, android/ios/web); analyze clean, test green, apk-debug built (first Gradle run installed NDK 28.2 + Build-Tools 36). Landmine fixed: root `.gitignore`'s unanchored `lib/` rule was silently dropping `app/lib/**` — re-include pair added (see wave-0 commit body).
- 2026-07-04 — wave-1 [green], unattended. `domain/` (Session, TurnEntry, SessionSummary, Principal; SessionStatus/TurnRole enums; sealed SessionApiException with the §9 closed set, errorType strings verbatim) + `ports/session_api.dart` (six §5 verbs, full return shapes incl. resumed/resumable/turnCount). 20 tests green (unit/errors + unit/domain_models + scaffold widget test); analyze clean; apk-debug built. No contract doubts.
- 2026-07-04 — wave-2 [green], unattended. `ports/identity_provider.dart` (signIn/signOut/currentPrincipal) + `fakes/fake_identity_provider.dart`: two principals (Lilymay default, Alex second for ownership tests), `signInAs` test hook, invalidate-token switch that leaves the client-side principal set (stale-token shape), and `studentIdForToken` — the fake auth-server introspection FakeSessionApi will trust for §3 token→student_id derivation (wave-3 seam decided here). 31 tests green; analyze clean; apk-debug built.
- 2026-07-04 — wave-3 [green], unattended. `fakes/fake_session_api.dart`: InMemorySessionStore split out as a shareable object (wave-4's second-client durability test needs it); five verbs implemented (startSession with (student,subject)-keyed resumeIfActive, turn with deterministic canned replies keyed off turn index, resumeSession, endSession, sessionStatus full §5 shape); listSessions stubbed (UnimplementedError — wave-4 owns test 9); identity resolved per call via studentIdForToken, null → Unauthenticated. `test/contract/`: harness (deterministic ticking clock, secondClient()) + s4_lifecycle, s4_s6_append_only_transcript, s4_turn_count_monotonic, s5_resume_if_active (scope §4 tests 1, 2, 4, 5). One analyze fix (prefer_initializing_formals → `this._identity`). 46 tests green; analyze clean; apk-debug built.
- 2026-07-04 — wave-4 [green], unattended. FakeSessionApi: ownership assert (`_requireOwner`) on all four session_id verbs incl. sessionStatus; check order fixed as auth → not-found → forbidden → ended; listSessions implemented (student-partitioned, status filter, limit, most-recent-activity first). Contract tests II: s5_ownership (test 6), s3_s9_authentication (test 7, signed-out + stale-token shapes, auth-before-lookup precedence), s9_unknown_session_and_status (test 8 in full), s5_list_sessions (test 9), s4_durability_second_client (test 3, both directions A↔B). Full scope-§4 suite 1–9 green. 65 tests; analyze clean; apk-debug built.
- 2026-07-04 — wave-5 [green], unattended. `ui/` (app.dart + sign_in/home/session screens), Navigator 1.0 MaterialPageRoute pushes (no route table — composes with constructor injection in wave-6), zero port/fake references, default theme. main.dart now boots StudyTutorApp; scaffold counter test necessarily replaced in this wave by test/ui/walking_skeleton_test.dart (boot → sign-in; sign-in→home is pushReplacement; home→session; back pops to home). 66 tests; analyze clean; apk-debug built. *Morning boot checkpoint reached: launches to sign-in and navigates.*

## HANDOFF

(run not started)
