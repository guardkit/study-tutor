# PROGRESS — overnight Flutter build (study_tutor_app)

**Build plan:** `docs/research/ideas/flutter-app-build-plan.md` (CONTRACT_SHA pinned in its header — re-read plan + this file at every wave start).
**Rules:** `docs/runbooks/RUNBOOK-overnight-fable-flutter.md` §2.
**Green =** `cd app && flutter analyze` clean + `flutter test` green + `flutter build apk --debug` succeeds.

## Waves

- [x] wave-0: flutter scaffold [green] — attended, 2026-07-04
- [x] wave-1: domain model + SessionApi port + typed errors [green] — unattended, 2026-07-04
- [ ] wave-2: IdentityProvider port + FakeIdentityProvider
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

## HANDOFF

(run not started)
