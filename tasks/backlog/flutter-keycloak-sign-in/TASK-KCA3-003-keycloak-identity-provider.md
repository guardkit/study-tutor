---
id: TASK-KCA3-003
title: "KeycloakIdentityProvider \u2014 real OIDC adapter behind the unchanged port\
  \ (silent-then-interactive, PKCE, proactive refresh, sign-out wins)"
task_type: feature
parent_review: TASK-REV-KCA3
feature_id: FEAT-AUTH-003
wave: 3
implementation_mode: task-work
complexity: 8
dependencies:
- TASK-KCA3-001
- TASK-KCA3-002
consumer_context:
- task: TASK-KCA3-001
  consumes: OIDC_CLIENT_CONFIG
  framework: flutter_appauth (FlutterAppAuth.authorizeAndExchangeCode / token)
  driver: flutter_appauth
  format_note: issuer/discovery = KeycloakConfig.issuer; clientId = study-tutor-app;
    scopes = [openid, offline_access]; the interactive flow requests offline_access
    so a refresh token is issued
- task: TASK-KCA3-001
  consumes: REDIRECT_URI
  framework: flutter_appauth redirectUrl argument
  driver: flutter_appauth
  format_note: "redirectUrl passed to appauth MUST equal KeycloakConfig.redirectUrl\
    \ = com.appmilla.studytutor:/oauth2redirect byte-for-byte \u2014 the same string\
    \ registered in the Android manifest scheme and iOS CFBundleURLSchemes and the\
    \ Keycloak client"
- task: TASK-KCA3-002
  consumes: STORED_SESSION
  framework: SecureSessionStore.read/write/clear
  driver: flutter_secure_storage (via the store seam)
  format_note: "adapter maps appauth TokenResponse \u2194 StoredSession (refreshToken,\
    \ accessToken, accessTokenExpiry, displayName); read() \u21D2 null means treat\
    \ as signed out"
status: in_review
autobuild_state:
  current_turn: 2
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-AUTH-003
  base_branch: main
  started_at: '2026-07-17T17:13:35.249581'
  last_updated: '2026-07-17T17:38:25.205917'
  turns:
  - turn: 1
    decision: feedback
    feedback: "- Deterministic honesty record (claim_audit_unmodified, severity=should_fix):\
      \ Player claim: Player claimed file app/lib/adapters/keycloak_identity_provider.dart.\
      \ Actual: Path is tracked in git but 'git status --porcelain' shows no change\
      \ for it \u2014 the Player claimed work on a file it did not actually modify\
      \ this turn. Most likely cause: the report writer swept an orchestrator-managed\
      \ path (e.g. a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n- Runtime-parity failure: the deliverable\
      \ passed pytest but its declared runtime entry point FAILED to run (exit=1,\
      \ expected=0). This is a 'passes tests but does not run' defect \u2014 fix the\
      \ deliverable so it runs standalone. Command: set -e\ncd app && flutter analyze\
      \ && flutter test\n:\n  Analyzing app...                                   \
      \             \n\n   info \u2022 The imported package 'yaml' isn't a dependency\
      \ of the importing package. Try adding a dependency for 'yaml' in the 'pubspec.yaml'\
      \ file \u2022 test/voice_runtime_config_test.dart:20:8 \u2022 depend_on_referenced_packages\n\
      1 issue found. (ran in 0.8s)"
    timestamp: '2026-07-17T17:13:35.249581'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: approve
    feedback: null
    timestamp: '2026-07-17T17:26:22.883792'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

## Description

The security core of the A3 slice: a `KeycloakIdentityProvider` in
`app/lib/adapters/keycloak_identity_provider.dart` implementing the **existing,
unchanged** 3-member `IdentityProvider` port
([identity_provider.dart](../../../app/lib/ports/identity_provider.dart)) with a
real OIDC flow. Design ref **KC-D7**. The port's **sync `currentPrincipal` stays**
— it is answered from an in-memory cached principal that the proactive background
refresh keeps fresh.

**Behaviour (all from KC-D7 / KC-D4):**

- **`Principal? get currentPrincipal`** — sync; returns the cached principal
  (`token` = the current access token; `displayName` from the id-token/name claim)
  or `null` when signed out. Never does I/O.
- **`Future<Principal> signIn()` — silent-then-interactive:**
  1. **Silent first** — if `SecureSessionStore.read()` yields a session with a
     refresh token, call `FlutterAppAuth.token(...)` with that refresh token
     (`offline_access`). On success: persist the rotated response, set the cached
     principal, return — **no browser**.
  2. **Interactive fallback** — otherwise `authorizeAndExchangeCode(...)` with
     `KeycloakConfig` (issuer/discovery, `clientId`, `redirectUrl`, scopes
     `openid offline_access`). **PKCE S256** is the appauth default for a public
     client; the custom-scheme `redirectUrl` completes the flow after the browser
     backgrounds the app. On success: persist via `SecureSessionStore.write`, set
     the cached principal, return.
  - **Distinguish cancel from failure (§4 `SIGNIN_OUTCOME`):** an appauth
    user-cancel (browser dismissed) surfaces as a distinct **cancel** outcome; a
    discovery/IdP/transport error surfaces as a distinct **failure** outcome. The
    two must **never** be conflated — the UI (TASK-KCA3-004) renders different
    states. Model as two exception types (e.g. `SignInCancelled` /
    `SignInFailed`) or an equivalent sealed result.
- **Single-flight guard** — a `signIn()` while one is already in flight returns
  the **same** in-flight `Future` (a second tap starts no second flow).
- **Proactive background refresh** — schedule a refresh shortly **before** the
  access-token expiry (`TokenResponse.accessTokenExpirationDateTime`, ASSUM-007);
  on refresh, persist + update the cached principal so `currentPrincipal` stays
  answerable across a >5-min idle (KC-G3, ASSUM-002). An **unrecoverable** refresh
  (offline session dead / IdP unreachable and retries exhausted) clears the cached
  principal so the next use degrades to the sign-in fallback — **never crash or
  hang**.
- **`Future<void> signOut()` — local clear that WINS a refresh race** — clear
  `SecureSessionStore` + the cached principal + cancel any scheduled refresh, and
  **bump a generation/epoch** so an in-flight refresh that completes *after*
  sign-out is discarded and does **not** restore the session (ASSUM-004 — local
  clear only, no IdP end-session call).
- **Launch/read** — an absent, unreadable, or offline-expired stored session is
  treated as signed out (`currentPrincipal == null`), so the app presents sign-in
  rather than failing to launch.

**Library-property scenarios (document as intent, likely `pending` oracles per the
spec summary):** PKCE binding of an intercepted code, and rejection of a foreign
redirect scheme, are `flutter_appauth` + IdP properties — assert the adapter
*configures* them (S256, the app's own `redirectUrl`), not the wire mechanics.

**Hermetic tests (`app/test/adapters/keycloak_identity_provider_test.dart`) — no
browser, no network, no platform channel:** inject a fake `FlutterAppAuth` and a
fake `SecureSessionStore` (constructor injection). Cover: valid stored session ⇒
silent refresh, no interactive call; no/expired stored session ⇒ interactive call;
cancel ⇒ `SignInCancelled`; discovery/IdP error ⇒ `SignInFailed`; second concurrent
`signIn()` shares one flow; refresh before expiry updates the principal;
unrecoverable refresh clears the principal (no throw to the caller of a sync
`currentPrincipal`); **sign-out during an in-flight refresh stays signed out even
after the refresh completes**; unreadable store at launch ⇒ signed out.

## Acceptance Criteria

- [ ] `KeycloakIdentityProvider` implements the 3-member `IdentityProvider` port unchanged, with a **sync** `currentPrincipal` backed by an in-memory cached principal
- [ ] `signIn()` attempts a **silent refresh** of the stored session before opening the browser, and opens the interactive **PKCE S256** browser flow only when silent refresh is unavailable/fails
- [ ] The interactive flow uses `KeycloakConfig.redirectUrl` (`com.appmilla.studytutor:/oauth2redirect`) and requests `offline_access`, and completes after the custom-scheme redirect returns the app to the foreground
- [ ] `signIn()` surfaces **cancel** and **failure** as distinct outcomes (§4 `SIGNIN_OUTCOME`) and never conflates them
- [ ] A second `signIn()` while one is in flight starts no second flow (single-flight)
- [ ] The adapter refreshes proactively before access-token expiry using the appauth token-response expiry, so an idle longer than the access-token lifetime does not force a re-sign-in while the offline session is valid (KC-G3)
- [ ] `signOut()` clears the secure store and cached principal and **wins over an in-flight background refresh** — a refresh completing after sign-out does not restore the session
- [ ] An unrecoverable background refresh leaves `currentPrincipal == null` and degrades to the sign-in fallback rather than crashing or hanging
- [ ] At launch an absent/unreadable/offline-expired stored session is treated as signed out
- [ ] Hermetic tests fake `FlutterAppAuth` and `SecureSessionStore` — no browser, no network, no platform channel
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Served

- GROUP A: silent reuse of a valid session; device stays signed in across restart; active session survives a >access-token-lifetime idle
- GROUP B: refresh within the offline window; browser required past the offline window
- GROUP D: second sign-in tap ignored (single-flight); sign-in completes after the browser redirect; silent recovery after a rejected token; failed background refresh degrades to sign-in
- GROUP E (security): sign-out during a background refresh stays signed out; PKCE-bound code / own-scheme redirect (configured here; wire mechanics documented as intent per summary)

## Seam Tests

Validate the `STORED_SESSION` and `SIGNIN_OUTCOME` contracts at the adapter
boundary (Dart / `flutter_test` — this repo is Flutter, not pytest).

```dart
// app/test/adapters/keycloak_identity_provider_seam_test.dart
// Seam test: STORED_SESSION (from TASK-KCA3-002) + SIGNIN_OUTCOME (produced here).
import 'package:flutter_test/flutter_test.dart';

void main() {
  // Contract: STORED_SESSION — a readable stored session with a refresh token
  // drives a SILENT refresh; the interactive browser flow is never invoked.
  test('a valid stored session refreshes silently — no interactive flow', () async {
    final appauth = FakeAppAuth();                 // records authorizeAndExchangeCode calls
    final store = FakeSecureSessionStore()
      ..seed(refreshToken: 'r0', accessToken: 'a0', expiry: farFuture);
    final idp = KeycloakIdentityProvider(config, appauth, store);

    await idp.signIn();

    expect(appauth.interactiveCalls, 0, reason: 'silent refresh must precede any browser');
    expect(appauth.tokenRefreshCalls, 1);
    expect(idp.currentPrincipal, isNotNull);
  });

  // Contract: SIGNIN_OUTCOME — cancel and failure are DISTINCT, catchable outcomes.
  test('cancel and failure surface as distinct outcomes', () async {
    final store = FakeSecureSessionStore();        // empty ⇒ interactive path
    final cancelIdp =
        KeycloakIdentityProvider(config, FakeAppAuth.cancels(), store);
    final failIdp =
        KeycloakIdentityProvider(config, FakeAppAuth.failsDiscovery(), store);

    await expectLater(cancelIdp.signIn(), throwsA(isA<SignInCancelled>()));
    await expectLater(failIdp.signIn(), throwsA(isA<SignInFailed>()));
  });
}
```

## References

- design [KC-D7 / KC-D4](../../../docs/design/keycloak-auth-user-management-design.md) · assumptions [ASSUM-002/003/004/007](../../../features/flutter-keycloak-sign-in/flutter-keycloak-sign-in_assumptions.yaml) · IMPLEMENTATION-GUIDE §4 (`OIDC_CLIENT_CONFIG`, `REDIRECT_URI`, `STORED_SESSION`, `SIGNIN_OUTCOME`) · port [identity_provider.dart](../../../app/lib/ports/identity_provider.dart) · security-critical (secure storage, PKCE, sign-out race) ⇒ FULL_REQUIRED human checkpoint
