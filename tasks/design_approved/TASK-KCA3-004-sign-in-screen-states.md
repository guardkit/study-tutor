---
complexity: 5
consumer_context:
- consumes: SIGNIN_OUTCOME
  driver: flutter (Material)
  format_note: the adapter surfaces cancel (SignInCancelled) and failure (SignInFailed)
    as distinct outcomes; the screen must render a distinct cancel message vs a failure
    state, and MUST NOT collapse discovery-unavailable (failure) into the cancel message
  framework: Flutter StatefulWidget state machine over the adapter's signIn() result
  task: TASK-KCA3-003
dependencies:
- TASK-KCA3-003
feature_id: FEAT-AUTH-003
id: TASK-KCA3-004
implementation_mode: task-work
parent_review: TASK-REV-KCA3
status: design_approved
task_type: feature
title: SignInScreen loading / failure / cancel states + try-again — failure ≠ cancel,
  driven by the adapter outcome
wave: 4
---

## Description

Give `SignInScreen`
([sign_in_screen.dart](../../../app/lib/ui/sign_in_screen.dart)) the
loading / failure / cancel states the design calls for (KC-D7), consuming the
adapter's distinct `SIGNIN_OUTCOME` (TASK-KCA3-003). Today the screen is a
`StatelessWidget` with a single "Sign in" button that awaits `signIn()` then
pushes home — it has no visible in-progress, failure, or cancel state. This task
turns it into a small state machine.

**Deliverables (`sign_in_screen.dart` → `StatefulWidget`):**

- **Loading** — while `signIn()` is in flight, show a loading indicator and
  disable the button, so a second tap cannot start a second flow (UI guard
  complementing the adapter's single-flight).
- **Failure** — on `SignInFailed` (IdP unreachable / **discovery document
  unavailable** / transport), show a failure state with an explicit **"Try
  again"** affordance (ASSUM-005 — manual retry, no auto-retry). This reuses the
  app's existing non-auto-dismiss error idiom
  ([error_handling.dart](../../../app/lib/ui/error_handling.dart)).
- **Cancel** — on `SignInCancelled` (user backed out of the browser), return to
  the idle sign-in screen showing that **sign-in was cancelled**, signed out.
- **Success** — unchanged: `pushReplacement` to `HomeScreen`.
- **failure ≠ cancel** — a missing discovery document at sign-in is a **failure**
  (offer try-again), **not** a cancel; the two states must not be conflated.

**Widget tests (`app/test/ui/sign_in_states_test.dart`):** drive a fake
`IdentityProvider` whose `signIn()` (a) succeeds, (b) throws `SignInCancelled`,
(c) throws `SignInFailed` — assert the loading indicator appears during the
in-flight future, the cancel message vs the try-again failure state render
distinctly, the discovery-unavailable case renders the **failure** state (not
cancel), and a second tap while loading invokes `signIn()` only once.

## Acceptance Criteria

- [ ] `SignInScreen` shows a **loading** state while `signIn()` is in flight, with the sign-in control disabled
- [ ] On `SignInFailed` the screen shows a **failure** state with a manual **"Try again"** affordance (no automatic retry) (serves "A failed sign-in shows a failure state and lets me try again")
- [ ] On `SignInCancelled` the screen returns signed-out and shows that **sign-in was cancelled** (serves "Cancelling the browser sign-in returns to the sign-in screen signed out")
- [ ] A **discovery-unavailable** sign-in renders the **failure** state, not the cancel state — the two are never conflated (serves "An unavailable identity-provider discovery at sign-in shows the failure state")
- [ ] While loading, a second tap starts no second flow (UI guard; invokes `signIn()` once)
- [ ] On success the screen `pushReplacement`es to `HomeScreen` (behaviour unchanged)
- [ ] Widget tests drive a fake `IdentityProvider` producing cancel / failure / success outcomes — no browser, no network
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Served

- "Cancelling the browser sign-in returns to the sign-in screen signed out" (@negative @smoke)
- "A failed sign-in shows a failure state and lets me try again" (@negative @smoke)
- "An unavailable identity-provider discovery at sign-in shows the failure state" (@edge-case @negative)
- "A second sign-in tap during an in-progress sign-in is ignored" (@edge-case — UI half of the guard)

## Seam Tests

Validate the `SIGNIN_OUTCOME` contract at the UI boundary (Dart / `flutter_test`).

```dart
// app/test/ui/sign_in_states_seam_test.dart
// Seam test: SIGNIN_OUTCOME (from TASK-KCA3-003) — cancel and failure render distinct UI.
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter/material.dart';

void main() {
  testWidgets('cancel and failure render distinct states', (tester) async {
    // Contract: adapter throws SignInCancelled vs SignInFailed; the screen must
    // NOT render the same surface for both, and discovery-unavailable is failure.
    await tester.pumpWidget(MaterialApp(
      home: SignInScreen(
        identity: FakeIdentity.cancels(),          // throws SignInCancelled
        sessionApi: FakeSessionApi(),
      ),
    ));
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();
    expect(find.textContaining('cancelled'), findsOneWidget);
    expect(find.text('Try again'), findsNothing);   // cancel is NOT the failure state

    await tester.pumpWidget(MaterialApp(
      home: SignInScreen(
        identity: FakeIdentity.failsDiscovery(),    // throws SignInFailed
        sessionApi: FakeSessionApi(),
      ),
    ));
    await tester.tap(find.text('Sign in'));
    await tester.pumpAndSettle();
    expect(find.text('Try again'), findsOneWidget);  // failure IS the try-again state
  });
}
```

## References

- design [KC-D7](../../../docs/design/keycloak-auth-user-management-design.md) · assumptions [ASSUM-005](../../../features/flutter-keycloak-sign-in/flutter-keycloak-sign-in_assumptions.yaml) · IMPLEMENTATION-GUIDE §4 (`SIGNIN_OUTCOME`) · current screen [sign_in_screen.dart](../../../app/lib/ui/sign_in_screen.dart) · error idiom [error_handling.dart](../../../app/lib/ui/error_handling.dart)

## Pre-build drift note (2026-07-17, weekend handoff §5 — binding)

The current `SignInScreen` ctor (`app/lib/ui/sign_in_screen.dart:19`) also
**requires `voiceApi`** (added by FEAT-VOICE-003, after this task was written).
This task's two-arg seam test predates that. Directive: **reconcile the widget
signature with the seam test rather than blindly following either** — keep the
`voiceApi` wiring intact (do not strip it), and adapt the seam test to the real
ctor shape while still proving the loading/failure/cancel states this task owns.