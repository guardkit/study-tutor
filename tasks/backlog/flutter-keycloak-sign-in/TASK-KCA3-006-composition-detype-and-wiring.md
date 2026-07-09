---
id: TASK-KCA3-006
title: "Composition seam de-type to the port + real-flavour wiring; preserve Unauthenticated↔TransportError distinction"
task_type: refactor
parent_review: TASK-REV-KCA3
feature_id: FEAT-AUTH-003
wave: 5
implementation_mode: task-work
complexity: 6
dependencies:
- TASK-KCA3-003
- TASK-KCA3-004
- TASK-KCA3-005
consumer_context:
  - task: TASK-KCA3-001
    consumes: OIDC_CLIENT_CONFIG
    framework: "composition root (main.dart) constructs KeycloakIdentityProvider(config, appauth, store)"
    driver: "flutter_appauth + flutter_secure_storage"
    format_note: "the keycloak flavour builds KeycloakConfig from KEYCLOAK_ISSUER/KEYCLOAK_CLIENT_ID; an empty KEYCLOAK_ISSUER selects the hermetic-fake flavour, which keeps the concrete FakeIdentityProvider"
---

## Description

The integration wave: flip the one composition seam from the concrete fake to the
port, wire the real adapter in the keycloak flavour, and prove the existing
error-routing distinction survives the real adapter. Design ref **KC-D7**.

**Deliverables:**

1. **De-type the seam** — `composeSessionApi` in
   [main.dart:21](../../../app/lib/main.dart#L21) takes its `identity` parameter as
   the **`IdentityProvider` port**, not the concrete `FakeIdentityProvider`. This
   is the one composition rule `composition_test`
   ([composition_test.dart](../../../app/test/ui/composition_test.dart)) asserts —
   keep it green.
2. **Flavour selection in `main()`** — build the identity adapter by flavour:
   - **keycloak flavour** (`KEYCLOAK_ISSUER` set): construct
     `KeycloakIdentityProvider(KeycloakConfig(...), FlutterAppAuth(),
     SecureSessionStore(...))`.
   - **hermetic-fake flavour** (`KEYCLOAK_ISSUER` empty — the default every
     hermetic test sees): keep the **concrete** `FakeIdentityProvider`. It must
     stay concrete because `FakeSessionApi` consumes its `studentIdForToken`
     introspection hook (the fake auth-server side, §3). The fake flavour stays
     **unchanged and green** — no browser, no network.
3. **Preserve the Unauthenticated ↔ TransportError distinction** — with the real
   adapter wired, the two treatments in
   [error_handling.dart](../../../app/lib/ui/error_handling.dart) must stay
   **distinct**: a backend that **rejects the token** (`Unauthenticated`) →
   `routeToSignIn`; a backend that is **unreachable** (`TransportError`) →
   `showConnectionProblem` and **stay put**. A dead backend must **not** route a
   signed-in student to sign-in. Add/keep a regression test proving this holds for
   a `KeycloakIdentityProvider`-backed session.

Scope boundary (invariant, not a snapshot): this task **de-types and wires**; it
does not re-implement the error treatments (they already exist) and does not add
new adapter behaviour (owned by TASK-KCA3-003).

**Tests:**
- `composition_test.dart` stays green with the de-typed signature (fake flavour ⇒
  `FakeSessionApi` with the concrete fake; keycloak flavour ⇒ `HttpSessionApi`
  with `KeycloakIdentityProvider`).
- `app/test/ui/error_routing_regression_test.dart` — a signed-in session whose
  backend returns `Unauthenticated` routes to sign-in; a signed-in session whose
  backend raises `TransportError` shows the connection problem and does **not**
  route to sign-in.

## Acceptance Criteria

- [ ] `composeSessionApi`'s `identity` parameter is typed as the `IdentityProvider` **port** (not the concrete `FakeIdentityProvider`); `composition_test` is green
- [ ] The **keycloak flavour** composes `KeycloakIdentityProvider` (built from `KeycloakConfig`); the **hermetic-fake flavour** keeps the **concrete** `FakeIdentityProvider` and stays green with no browser and no network (serves "The hermetic fake flavour still signs in with no browser and no network")
- [ ] `FakeSessionApi` still receives the concrete fake's `studentIdForToken` introspection hook — the de-type does not break the fake auth-server wiring
- [ ] A backend-**rejected** token (`Unauthenticated`) routes back to sign-in; a backend-**unreachable** error (`TransportError`) shows a connection problem and does **not** route to sign-in — the two stay distinct with the real adapter (serves both Group-E routing scenarios)
- [ ] `composition_test` and the error-routing regression test are green
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Served

- "The hermetic fake flavour still signs in with no browser and no network" (@key-example @smoke @regression)
- "A backend-rejected token routes the student back to sign-in" (@negative @smoke @regression)
- "A backend unreachable after sign-in shows a connection problem rather than routing to sign-in" (@edge-case @negative @regression)

## Seam Tests

Validate the `OIDC_CLIENT_CONFIG` wiring at the composition boundary (Dart /
`flutter_test`).

```dart
// app/test/ui/composition_flavour_seam_test.dart
// Seam test: OIDC_CLIENT_CONFIG — flavour selection wires the right identity adapter.
import 'package:flutter_test/flutter_test.dart';

void main() {
  test('empty issuer ⇒ concrete FakeIdentityProvider (hermetic flavour)', () {
    final identity = composeIdentity(keycloakIssuer: '');   // helper under test
    expect(identity, isA<FakeIdentityProvider>());          // concrete, for studentIdForToken
  });

  test('set issuer ⇒ KeycloakIdentityProvider built from KeycloakConfig', () {
    final identity = composeIdentity(
      keycloakIssuer: 'https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor',
    );
    expect(identity, isA<KeycloakIdentityProvider>());
    // Contract: the adapter carries the SAME redirect the native config registers.
    expect((identity as KeycloakIdentityProvider).config.redirectUrl,
        'com.appmilla.studytutor:/oauth2redirect');
  });
}
```

## References

- design [KC-D7](../../../docs/design/keycloak-auth-user-management-design.md) · IMPLEMENTATION-GUIDE §4 (`OIDC_CLIENT_CONFIG`) · seam [main.dart:21](../../../app/lib/main.dart#L21) · [composition_test.dart](../../../app/test/ui/composition_test.dart) · treatments [error_handling.dart](../../../app/lib/ui/error_handling.dart)
