---
id: TASK-KCA3-005
title: "Sign-out affordance \u2014 home-screen app-bar action \u2192 identity.signOut()\
  \ \u2192 routeToSignIn"
task_type: feature
parent_review: TASK-REV-KCA3
feature_id: FEAT-AUTH-003
wave: 2
implementation_mode: task-work
complexity: 3
dependencies:
- TASK-KCA3-001
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-AUTH-003
  base_branch: main
  started_at: '2026-07-17T13:52:28.400287'
  last_updated: '2026-07-17T14:11:45.502784'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-07-17T13:52:28.400287'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

## Description

Add the new sign-out affordance the design calls for (KC-D7). Per **ASSUM-006**
it lives on the **home screen** as an app-bar action (sign-out is exercised while
signed in, not from the sign-in screen). It uses only the existing 3-member
`IdentityProvider` port ([identity_provider.dart](../../../app/lib/ports/identity_provider.dart))
and the existing `routeToSignIn` treatment
([error_handling.dart](../../../app/lib/ui/error_handling.dart)) — so it is
port-only and can land and be tested against `FakeIdentityProvider` **in parallel
with the Keycloak adapter** (no dependency on TASK-KCA3-003).

Scope boundary (invariant, not a snapshot): this task adds the **UI affordance +
local-clear routing** only. The "sign-out **wins over an in-flight background
refresh**" guarantee is an **adapter** concern owned by TASK-KCA3-003 — do **not**
write a test here asserting the adapter's refresh-race behaviour (a later task in
this feature implements it; asserting its absence now would go red when 003
lands).

**Deliverables:**

1. **`app/lib/ui/home_screen.dart`** — an app-bar action (icon/overflow) labelled
   for sign-out. On tap: `await widget.identity.signOut()` then
   `routeToSignIn(context, widget.identity, widget.sessionApi)` (clears the whole
   stack, lands on `SignInScreen`). Guard with the screen's existing `mounted`
   discipline.
2. Per **ASSUM-004**, `signOut` is a **local** clear (the port's contract — secure
   store + `currentPrincipal`); it does **not** call an IdP end-session endpoint.
   That local-clear semantics is the adapter's (003); this task just invokes the
   port method.

**Widget test (`app/test/ui/sign_out_test.dart`):** build `HomeScreen` with a
`FakeIdentityProvider` signed in, tap the sign-out action, assert the port's
`signOut` was called, `currentPrincipal` is `null`, and the `SignInScreen` is
shown with the back-stack cleared.

## Acceptance Criteria

- [ ] `HomeScreen` exposes a sign-out affordance as an app-bar action (ASSUM-006)
- [ ] Tapping it calls `identity.signOut()` and then `routeToSignIn(...)`, clearing the navigation stack and landing on `SignInScreen`
- [ ] After sign-out `identity.currentPrincipal` is `null` and the sign-in screen is shown (serves "Signing out clears the session and returns to the sign-in screen")
- [ ] The affordance is driven through the `IdentityProvider` port — the widget test uses `FakeIdentityProvider`, no Keycloak adapter required
- [ ] No test in this task asserts adapter-level refresh-race behaviour (owned by TASK-KCA3-003)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Served

- "Signing out clears the session and returns to the sign-in screen" (@key-example @smoke)

## References

- design [KC-D7](../../../docs/design/keycloak-auth-user-management-design.md) · assumptions [ASSUM-004, ASSUM-006](../../../features/flutter-keycloak-sign-in/flutter-keycloak-sign-in_assumptions.yaml) · reuses [routeToSignIn](../../../app/lib/ui/error_handling.dart)
