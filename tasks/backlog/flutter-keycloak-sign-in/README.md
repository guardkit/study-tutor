# FEAT-AUTH-003 A3 — Flutter Keycloak Sign-In

The app slice of the Keycloak auth rollout (design **KC-D7**, gate **KC-G3**): a real
`KeycloakIdentityProvider` implementing the **unchanged** 3-member `IdentityProvider` port.
The port's **sync `currentPrincipal` stays** — the adapter refreshes proactively in the
background, and `signIn()` tries a **silent refresh before the interactive browser flow**.
PKCE S256 public client, custom-scheme redirect, `offline_access` so the family device stays
signed in. `SignInScreen` gains loading / failure / cancel states plus a sign-out affordance.

- **Review:** TASK-REV-KCA3 · **Feature id:** FEAT-AUTH-003 · **Complexity:** 7/10
- **Spec:** [features/flutter-keycloak-sign-in/](../../../features/flutter-keycloak-sign-in/) (25 scenarios, 8 smoke, 5 regression)
- **Design:** [keycloak-auth-user-management-design.md](../../../docs/design/keycloak-auth-user-management-design.md) (KC-D7 / KC-D4, gate KC-G3)
- **Port (unchanged):** [app/lib/ports/identity_provider.dart](../../../app/lib/ports/identity_provider.dart) · **Seam:** [app/lib/main.dart](../../../app/lib/main.dart) (`composeSessionApi` de-types to the port)
- **Guide (start here):** [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) — data-flow, silent-then-interactive sequence, dependency diagrams + §4 contracts

## Tasks

| Task | Type | Wave | Deliverable |
|---|---|---|---|
| [TASK-KCA3-001](./TASK-KCA3-001-deps-native-redirect-config.md) | scaffolding | 1 | `flutter_appauth` + `flutter_secure_storage` deps, Android/iOS redirect scheme, `KeycloakConfig` |
| [TASK-KCA3-002](./TASK-KCA3-002-secure-session-store.md) | feature | 2 | `SecureSessionStore` (secure-storage token persistence; unreadable ⇒ signed out) |
| [TASK-KCA3-005](./TASK-KCA3-005-sign-out-affordance.md) | feature | 2 | Home app-bar sign-out → `signOut()` → `routeToSignIn` (port-only) |
| [TASK-KCA3-003](./TASK-KCA3-003-keycloak-identity-provider.md) | feature | 3 | `KeycloakIdentityProvider` — silent-then-interactive, PKCE, proactive refresh, sign-out-wins |
| [TASK-KCA3-004](./TASK-KCA3-004-sign-in-screen-states.md) | feature | 4 | `SignInScreen` loading/failure/cancel + try-again (failure ≠ cancel) |
| [TASK-KCA3-006](./TASK-KCA3-006-composition-detype-and-wiring.md) | refactor | 5 | Composition de-type to the port + flavour wiring; preserve `Unauthenticated`↔`TransportError` |
| [TASK-KCA3-007](./TASK-KCA3-007-kc-g3-live-gate.md) | **operator_handoff** | 6 | KC-G3 gate: live device, >5-min idle survives, restart stays signed in (operator-executed) |

## Operator follow-up tasks: 1

TASK-KCA3-007 is `operator_handoff` — AutoBuild will not attempt it. The KC-G3 gate (live
sign-in on a real device against the A2 dev deploy in `keycloak` mode; >5-min idle survives;
restart stays signed in; ASSUM-002/003 confirmed against reality) is operator-verified
post-merge via `/task-complete`. See its `## Required operator follow-up` block.

## Execution

- **AutoBuild the code:** `/feature-build FEAT-AUTH-003` runs waves 1–5
  (TASK-KCA3-001…006). The operator_handoff task (007) is short-circuited.
- **Then run the gate:** the operator brings up the A2 dev deploy in `keycloak` mode and passes
  KC-G3 on a real device.
- **Depends on:** A2 dev deploy (FEAT-AUTH-002) in `keycloak` mode and the A1 realm
  (FEAT-AUTH-001) `study-tutor-app` client for the live gate — code waves 1–5 build hermetically
  without them.

## Scope guard

Out of scope (other rollout slices): A1 NAS standup / realm-as-code (FEAT-AUTH-001); A2 server
`TokenResolver` / `auth_keycloak.py` validation (FEAT-AUTH-002); A4 robot device-grant pairing
(FEAT-AUTH-004); parent-facing UI (KC-D5, role reserved only); token-rotation hardening beyond
appauth defaults (design §4); the exact PKCE/JWKS/redirect **wire mechanics** (an IdP + AppAuth
library property — documented as intent; the two PKCE/redirect security scenarios likely resolve
to `pending` oracles at the task level per the spec summary).
