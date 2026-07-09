# Feature Spec Summary: Flutter Keycloak Sign-In (FEAT-AUTH-003, A3)

**Stack**: flutter
**Generated**: 2026-07-08T20:41:54Z
**Scenarios**: 25 total (8 smoke, 5 regression)
**Assumptions**: 7 total (2 high / 4 medium / 1 low confidence)
**Review required**: Yes (1 low-confidence assumption)

## Scope

Covers the **A3 app slice** of the Keycloak auth rollout only (design **KC-D7**, gate
**KC-G3**): a real `KeycloakIdentityProvider` implementing the unchanged 3-member
`IdentityProvider` port. The port's **sync `currentPrincipal` stays** — the adapter refreshes
proactively in the background (driven by the appauth token-response expiry), and `signIn()`
attempts a **silent refresh before the interactive browser flow** (silent-then-interactive).
Sign-in is an **Authorization Code + PKCE (S256)** public-client flow with a custom-scheme
redirect and `offline_access` scope, so the family device stays signed in. `SignInScreen` gains
**loading / failure / cancel** states plus a **sign-out** affordance. The composition seam —
`composeSessionApi` in `main.dart` — has its `identity` parameter **de-typed from the concrete
`FakeIdentityProvider` to the port**, while the hermetic fake flavour keeps the concrete fake for
its introspection hook and is otherwise unchanged and green. The existing
**`Unauthenticated → routeToSignIn()`** recovery is preserved as the hard fallback, and is kept
strictly distinct from `TransportError → showConnectionProblem()` (a dead backend must not route a
signed-in student to sign-in). Adding `flutter_appauth` + `flutter_secure_storage` is a deliberate,
recorded break from the app's zero-added-runtime-dependencies DoD.

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 6 |
| Boundary conditions (@boundary) | 3 |
| Negative cases (@negative) | 9 |
| Edge cases (@edge-case) | 12 |
| Security (@security) | 4 |
| Smoke (@smoke) | 8 |
| Regression (@regression) | 5 |

_(Tags overlap: several scenarios carry both `@edge-case` and `@negative`/`@security`, or `@boundary` and `@negative`.)_

## Deferred Items

None deferred. All five groups (A–D core + the Group E security/concurrency/integration
edge-expansion) were accepted as proposed.

## Out of Scope (other rollout slices, not specified here)

- **A1 standup** — `study_tutor_keycloak` container, realm-as-code, TLS (FEAT-AUTH-001, KC-G1).
- **A2 server** — `TokenResolver` seam, `http/auth_keycloak.py` JWKS validation, `STUDY_TUTOR_AUTH_MODE` (FEAT-AUTH-002, KC-G2). A3 depends on the A2 dev deploy running in `keycloak` mode.
- **A4 robot** — device-grant pairing + `ask_tutor` bearer injection (FEAT-AUTH-004, KC-G4).
- **Parent-facing UI** — `parent` role reserved only (KC-D5).
- **Token-rotation hardening** beyond appauth defaults (design §4).
- The **exact PKCE / JWKS / redirect wire mechanics** — an IdP + AppAuth-library property; ASSUM-003 and the two PKCE/redirect security scenarios document intent and will likely resolve to `pending` at the task level rather than executable Dart oracles.

## Open Assumptions (low confidence — verify before freeze)

- **ASSUM-003** — the custom-scheme redirect URI, human-overridden to
  `com.appmilla.studytutor:/oauth2redirect`. The build must register the **identical** value in
  three places that have to agree: the Keycloak `study-tutor-app` client's redirect URIs, the
  Android manifest intent-filter, and the iOS `CFBundleURLSchemes`. Confirm the final string with
  the operator before the A1 realm-as-code and the app config are frozen.

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "Flutter Keycloak Sign-In (FEAT-AUTH-003, A3)" \
      --context features/flutter-keycloak-sign-in/flutter-keycloak-sign-in_summary.md

`/feature-plan` Step 11 (BDD linking) will add the `@task:<TASK-ID>` tags to the scenarios once
the A3 tasks exist — they are intentionally left off this fresh spec.
