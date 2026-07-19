# KC-G3 Evidence — live end-to-end sign-in on a real device (TASK-KCA3-007)

**Date:** 2026-07-19 · **Gate:** KC-G3, binding ACs in
`tasks/backlog/TASK-KCA3-007-kc-g3-live-gate.md` · **Device:** Samsung SM-A236B on
WiFi · **Deploy:** keycloak-mode `:8101` (`study_tutor_http_kc`, image
`study-tutor:kc-a2`) against NAS Keycloak realm `study-tutor` · **App build:** main
`5a5384c` + operator dart-defines · **Operators:** Rich (phone) + MacBook session
(build/drive) + GB10 Fable session (server/realm + log verification)

> STATUS: **GATE PASS** (2026-07-19). All six ACs met + cancel path — see per-AC
> evidence below. AC-G3-03 has a discrete 12-min-idle capture plus continuous
> proactive-refresh mechanism evidence.

## Bugs the gate surfaced and fixed (all committed to main)

KC-G3 exercised the real browser→device→server chain for the first time and found
five defects that the hermetic A3 gates (analyze + test only, no APK, no live IdP)
could not:

| # | Defect | Fix | Commit |
|---|---|---|---|
| 1 | `turnBudget` 15 s under water vs 26–80 s spark turns → every send shows "Connection problem", retries duplicate turns | raise to 90 s + test | `641c4b8` |
| 2 | APK build broken — flutter_appauth 8.0.3 pins compileSdk 31 vs AGP 9 | raise plugin modules < 34 to 36 | `4336035` |
| 3 | **Duplicate OAuth redirect handler** — manual VIEW intent-filter on MainActivity + appauth's `RedirectUriReceiverActivity` both claimed the scheme → Android chooser, token response never reached appauth | remove the manual intent-filter | `8c438eb` |
| 4 | **Missing audience mapper** on `study-tutor-app` — real app token lacked `aud=study-tutor-app`, resolver would 401 it (KC-G2 masked it via the live-suite client) | add oidc-audience-mapper (live realm + realm-as-code) | `c2e3b1a` |
| 5 | **Redirect never completed in-app** — (a) `<queries>` missing browser/Custom-Tabs visibility → appauth fell back to a full Chrome tab, whose gestureless custom-scheme redirect Chrome drops; (b) `taskAffinity=""` on MainActivity → redirect spawned a new task with no pending appauth state ("No stored state") | add browser `<queries>` + remove `taskAffinity=""` | `5a5384c` |

## AC results

### AC-G3-01 — first-time browser sign-in → redirect → home screen ✅
Browser sign-in as `lilymay` → custom-scheme redirect round-trips into the app
(Custom Tab confirmed on-device, `RedirectUriReceiverActivity` fired) → home screen
rendered with real server data (Level 3, streak, session cards). Server trace
(`:8101`, 12:29:43 UTC):
```
Token validated successfully: student_id=lilymay, iss=…/realms/study-tutor
Auth success: Resolved student_id=lilymay from token
GET /api/student-model?subject=english  200
GET /api/sessions?status=active         200
```
Confirms the audience-mapper fix (#4) against a real app token and closes ASSUM-003
(redirect round-trips on the real device + client).

### Working turn (authenticated write path) ✅
Started a session and sent a turn; full Socratic tutor reply (sibilance) in ~43 s,
inside the new 90 s budget. Server trace:
```
12:32:42  POST /api/sessions/start                                  200
12:33:25  POST /api/sessions/{bfcad81d…}/turn                       200   (student_id=lilymay)
```

### AC-G3-02 — close/reopen stays signed in, no browser ✅
App closed ~11 min (past the 300 s access-token lifetime), reopened → home screen
loaded with data, **no browser prompt, no new interactive login**. Server trace
(12:44:07 UTC): `GET /api/sessions` + `GET /api/student-model` both 200,
`student_id=lilymay`; Keycloak shows no `LOGIN`/`CODE_TO_TOKEN` since the original —
token came from a silent refresh of the persisted session.

### AC-G3-03 — active session survives >5-min idle (proactive refresh) ✅
Discrete capture: after the app sat idle 6+ min (operator-timed), a **`GET
/api/sessions/{bfcad81d…}/resume` at 14:06:36 returned 200** with `student_id=lilymay`
validated — **12 minutes** after the prior call (13:54:21), well past the 300 s
access-token lifetime, on the **same SSO session `bd57abdc`** with **no fresh
`LOGIN`** and no browser prompt. The proactive background refresh kept the token
fresh across the idle. Corroborating mechanism evidence: Keycloak logged the refresh
running continuously and successfully (`REFRESH_TOKEN` err=None) at ~10.7/second
across multiple open windows. (The over-eager rate is post-gate fix #1; it does not
affect this AC, which passes because the token never goes stale.)

### AC-G3-04 — sign-out returns to sign-in screen ✅ (client-observed)
Sign-out driven on-device (MacBook session): the affordance cleared the local
session and returned the app to the sign-in screen. Sign-out is local-only by design
(ASSUM-004 — the IdP SSO session survives), so there is no server-side logout event
to trace; this AC is inherently client-observed. Verified separately: after the
~70-min break the IdP session had idle-expired, so the 13:54 re-sign-in required
full credentials (`bd57abdc`, fresh `LOGIN`) and succeeded end-to-end — confirming
"a fresh sign-in is required" works. Known follow-up: an *immediate* re-sign-in while
the IdP session still survives hits the custom theme's `prompt=login` re-auth page
(disabled Sign In on mobile Chrome) — post-gate fix #3.

### AC-G3-05 — redirect URI byte-identical ×4 ✅
`com.appmilla.studytutor:/oauth2redirect` (single slash) on the live Keycloak
`study-tutor-app` client (patched C2, verified), realm-as-code, Android
`appAuthRedirectScheme` placeholder, and iOS `CFBundleURLSchemes`.

### AC-G3-06 — hermetic-fake build still green ✅
`flutter analyze` 0 issues + `flutter test` 338/338 on main `5a5384c` (MacBook
toolchain-of-record + GB10 arm64 cross-check).

### Cancel path ✅ (observed)
Cancelling the browser sign-in produced "Sign-in was cancelled" — distinct from a
failure state.

## Assumptions closed
- **ASSUM-002** — access-token lifetime is 300 s (confirmed KC-G2 + KC-G3), so the
  idle test genuinely crosses expiry.
- **ASSUM-003** — the single-slash redirect URI round-trips on the real device +
  real Keycloak client (AC-G3-01).
- **ASSUM-004** — sign-out is local-only; IdP session survives (AC-G3-04 handling).

## Post-gate follow-ups (defects/observations, NOT gate blockers)
1. **Refresh hot-loop** — proactive scheduler refreshes ~10.7×/second (300 s token,
   refresh-5-min-before-expiry → ~zero delay). Floor the refresh delay in
   `keycloak_identity_provider.dart`. Real load/battery/log-spam; gate passes because
   the token never goes stale.
2. **"Hi, User" greeting** — id_token lacks `name`/`preferred_username`; add a mapper
   to the app client (same place as the audience mapper). Cosmetic.
3. **Custom login theme** — `prompt=login` re-auth page disables Sign In on mobile
   Chrome; fix theme or drop `promptValues:['login']`.
4. **Fix B (robustness)** — switch the redirect to a verified HTTPS App Link
   (assetlinks.json + client redirect-URI update) so it never depends on Custom-Tab
   availability. Needs a coordinated realm change.

## Fences honoured
Table-mode `:8100` untouched throughout · secrets only in gitignored env files ·
tailnet-only · admin-API realm changes only (no volume/filesystem ops, no
`compose down -v`) · realm-as-code kept in sync with live (audience mapper).
