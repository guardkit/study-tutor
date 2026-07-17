---
id: TASK-KCA3-001
title: "flutter_appauth + flutter_secure_storage deps, native custom-scheme redirect config, and KeycloakConfig — the OIDC client surface"
task_type: scaffolding
parent_review: TASK-REV-KCA3
feature_id: FEAT-AUTH-003
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
---

## Description

Foundation for the A3 app slice: add the two sign-in runtime dependencies (a
deliberate, recorded break from the app's zero-added-runtime-dependencies DoD —
same pattern as the voice track), register the custom-scheme redirect in both
native projects, and add a frozen `KeycloakConfig` object that carries the OIDC
client surface the adapter (TASK-KCA3-003) consumes. Design ref **KC-D7 / KC-D4**.

Producer of the **§4 `REDIRECT_URI`** and **§4 `OIDC_CLIENT_CONFIG`** contracts.

**Deliverables:**

1. **Dependencies:** add `flutter_appauth` and `flutter_secure_storage` to
   `app/pubspec.yaml` (`dependencies:`). These are the **only** two runtime deps
   the whole feature adds — record the zero-deps-DoD scope event in the task notes
   / DoD ledger (mirrors the voice track's recorded exception).
2. **Android** — `app/android/app/src/main/AndroidManifest.xml` (and the
   `appAuthRedirectScheme` manifest placeholder in `app/android/app/build.gradle.kts` (Kotlin DSL)
   where `flutter_appauth` reads it): register the redirect **scheme**
   `com.appmilla.studytutor` so the browser can hand the result back to the app.
3. **iOS** — `app/ios/Runner/Info.plist`: add the redirect scheme to
   `CFBundleURLTypes` → `CFBundleURLSchemes` as `com.appmilla.studytutor`.
4. **`app/lib/config/keycloak_config.dart`** — a frozen `KeycloakConfig` value
   object: `issuer` (discovery base), `clientId` (`study-tutor-app`), `redirectUrl`
   (`com.appmilla.studytutor:/oauth2redirect`), `scopes` (`['openid',
   'offline_access']`). Built from the compile-time flavour surface below — **no
   `flutter_appauth`/`flutter_secure_storage` import here** (pure config; the
   adapter owns those imports).

**Compile-time config surface (name every value the deliverable reads —
hermetic-env):** the existing flavour switch is `--dart-define=API_BASE_URL=...`
([main.dart:15](../../../app/lib/main.dart#L15)). Add, in the same style:

| `--dart-define` key | Meaning | Default |
|---|---|---|
| `KEYCLOAK_ISSUER` | OIDC discovery base (ts.net https issuer) | empty ⇒ hermetic-fake flavour (no Keycloak) |
| `KEYCLOAK_CLIENT_ID` | public client id | `study-tutor-app` |

`redirectUrl` and `scopes` are **frozen constants** in `KeycloakConfig`, not
dart-defines — the redirect must be byte-identical to the native config and the
Keycloak client, so it is not left to an operator flag. Every test that builds a
`KeycloakConfig` pins these via `KeycloakConfig` constructor args, never ambient
`Platform.environment`.

> **ASSUM-003 (frozen by operator, 2026-07-08):** the redirect URI is
> `com.appmilla.studytutor:/oauth2redirect`. It must be **byte-identical** in
> three places that have to agree — the Keycloak `study-tutor-app` client's
> Valid Redirect URIs, the Android manifest scheme, and the iOS
> `CFBundleURLSchemes`. The Keycloak-client side is registered in A1
> realm-as-code (FEAT-AUTH-001) — this task owns the two app-side registrations
> and the constant.

## Acceptance Criteria

- [ ] `flutter_appauth` and `flutter_secure_storage` are declared in `app/pubspec.yaml` and are the **only** two runtime dependencies added by this feature (serves the scope-event scenario)
- [ ] The redirect scheme `com.appmilla.studytutor` is registered in the Android manifest (`appAuthRedirectScheme`) **and** in the iOS `Info.plist` `CFBundleURLSchemes`, matching `KeycloakConfig.redirectUrl` = `com.appmilla.studytutor:/oauth2redirect` byte-for-byte
- [ ] `KeycloakConfig` carries `issuer`, `clientId` (default `study-tutor-app`), `redirectUrl`, and `scopes` (`openid`, `offline_access`); an empty `KEYCLOAK_ISSUER` selects the hermetic-fake flavour (no Keycloak)
- [ ] The zero-added-runtime-dependencies DoD scope event is recorded in the task notes / DoD ledger
- [ ] `flutter analyze` remains clean; `flutter test` stays green (no behavioural change yet)

## BDD Scenarios Served

- "The new sign-in dependencies are recorded as a deliberate scope event" (@edge-case @regression)
- Config side of "A redirect to a scheme other than the app's own is not honoured" (@security — the app-side scheme registration this contract pins)

## References

- design [KC-D7 / KC-D4](../../../docs/design/keycloak-auth-user-management-design.md) · assumptions [ASSUM-003](../../../features/flutter-keycloak-sign-in/flutter-keycloak-sign-in_assumptions.yaml) (operator-frozen redirect URI) · IMPLEMENTATION-GUIDE §4 (`REDIRECT_URI`, `OIDC_CLIENT_CONFIG`) · flavour precedent [main.dart:15](../../../app/lib/main.dart#L15)
