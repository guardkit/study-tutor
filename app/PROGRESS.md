# PROGRESS — overnight Flutter build (study_tutor_app)

**Build plan:** `docs/research/ideas/flutter-app-build-plan.md` (CONTRACT_SHA pinned in its header — re-read plan + this file at every wave start).
**Rules:** `docs/runbooks/RUNBOOK-overnight-fable-flutter.md` §2.
**Green =** `cd app && flutter analyze` clean + `flutter test` green + `flutter build apk --debug` succeeds.

## Waves

- [x] wave-0: flutter scaffold [green] — attended, 2026-07-04
- [x] wave-1: domain model + SessionApi port + typed errors [green] — unattended, 2026-07-04
- [x] wave-2: IdentityProvider port + FakeIdentityProvider [green] — unattended, 2026-07-04
- [ ] wave-3: FakeSessionApi core + contract tests I (lifecycle)
- [ ] wave-4: ownership + auth + errors + listSessions — contract tests II
- [ ] wave-5: walking skeleton UI
- [ ] wave-6: slice I — sign in, start, exchange turns
- [ ] wave-7: slice II — resume + end + happy-path test
- [ ] wave-8: error handling (scope §3)
- [ ] wave-9: hardening + app README

## Log

- 2026-07-04 — wave-0 [green], attended. Scaffold created (`flutter create`, org com.appmilla, android/ios/web); analyze clean, test green, apk-debug built (first Gradle run installed NDK 28.2 + Build-Tools 36). Landmine fixed: root `.gitignore`'s unanchored `lib/` rule was silently dropping `app/lib/**` — re-include pair added (see wave-0 commit body).
- 2026-07-04 — wave-1 [green], unattended. `domain/` (Session, TurnEntry, SessionSummary, Principal; SessionStatus/TurnRole enums; sealed SessionApiException with the §9 closed set, errorType strings verbatim) + `ports/session_api.dart` (six §5 verbs, full return shapes incl. resumed/resumable/turnCount). 20 tests green (unit/errors + unit/domain_models + scaffold widget test); analyze clean; apk-debug built. No contract doubts.
- 2026-07-04 — wave-2 [green], unattended. `ports/identity_provider.dart` (signIn/signOut/currentPrincipal) + `fakes/fake_identity_provider.dart`: two principals (Lilymay default, Alex second for ownership tests), `signInAs` test hook, invalidate-token switch that leaves the client-side principal set (stale-token shape), and `studentIdForToken` — the fake auth-server introspection FakeSessionApi will trust for §3 token→student_id derivation (wave-3 seam decided here). 31 tests green; analyze clean; apk-debug built.

## HANDOFF

(run not started)
