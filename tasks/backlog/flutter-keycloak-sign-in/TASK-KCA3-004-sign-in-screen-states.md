---
id: TASK-KCA3-004
title: "SignInScreen loading / failure / cancel states + try-again \u2014 failure\
  \ \u2260 cancel, driven by the adapter outcome"
task_type: feature
parent_review: TASK-REV-KCA3
feature_id: FEAT-AUTH-003
wave: 4
implementation_mode: task-work
complexity: 5
dependencies:
- TASK-KCA3-003
consumer_context:
- task: TASK-KCA3-003
  consumes: SIGNIN_OUTCOME
  framework: Flutter StatefulWidget state machine over the adapter's signIn() result
  driver: flutter (Material)
  format_note: the adapter surfaces cancel (SignInCancelled) and failure (SignInFailed)
    as distinct outcomes; the screen must render a distinct cancel message vs a failure
    state, and MUST NOT collapse discovery-unavailable (failure) into the cancel message
status: in_review
autobuild_state:
  current_turn: 3
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-AUTH-003
  base_branch: main
  started_at: '2026-07-17T17:38:34.849081'
  last_updated: '2026-07-17T18:11:18.297794'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- Deterministic honesty record (claim_audit, severity=critical): Player
      claim: Player claimed file `app/lib/ui/sign_in_screen.dart. Actual: Path absent
      from ''git status --porcelain'' so ''git add -A'' would not stage it. Probes:
      path_exists=False; gitignore_match=no rule matched; tracked=no. Most likely
      cause: the Player claimed work on a file that does not exist on disk..

      - Deterministic honesty record (claim_audit, severity=critical): Player claim:
      Player claimed file `app/test/ui/sign_in_states_test.dart. Actual: Path absent
      from ''git status --porcelain'' so ''git add -A'' would not stage it. Probes:
      path_exists=False; gitignore_match=no rule matched; tracked=no. Most likely
      cause: the Player claimed work on a file that does not exist on disk..

      - Evidence gathering aborted at ''partial_honesty_abort'' stage due to path
      formatting errors in the Player''s report. The report includes malformed paths
      with leading backticks: ''`app/lib/ui/sign_in_screen.dart'' and ''`app/test/ui/sign_in_states_test.dart''.
      These paths do not exist on disk (the actual files lack the leading backtick).
      This triggered honesty checks that aborted before independent test verification,
      coverage analysis, BDD oracle, and quality gates could run.: Fix the path formatting
      in files_modified and files_created lists - remove leading backticks. The correct
      paths are ''app/lib/ui/sign_in_screen.dart'' and ''app/test/ui/sign_in_states_test.dart''
      (as shown in files_authored). Once corrected, re-run to trigger complete evidence
      gathering including independent tests, coverage, and quality gates.

      ... and 3 more issues'
    timestamp: '2026-07-17T17:38:34.849081'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: "- Deterministic honesty record (claim_audit, severity=critical): Player\
      \ claim: Player claimed file `app/lib/ui/sign_in_screen.dart. Actual: Path absent\
      \ from 'git status --porcelain' so 'git add -A' would not stage it. Probes:\
      \ path_exists=False; gitignore_match=no rule matched; tracked=no. Most likely\
      \ cause: the Player claimed work on a file that does not exist on disk..\n-\
      \ Deterministic honesty record (claim_audit, severity=critical): Player claim:\
      \ Player claimed file `app/test/ui/sign_in_states_test.dart. Actual: Path absent\
      \ from 'git status --porcelain' so 'git add -A' would not stage it. Probes:\
      \ path_exists=False; gitignore_match=no rule matched; tracked=no. Most likely\
      \ cause: the Player claimed work on a file that does not exist on disk..\n-\
      \ Deterministic honesty record (claim_audit_unmodified, severity=should_fix):\
      \ Player claim: Player claimed file app/lib/ui/sign_in_screen.dart. Actual:\
      \ Path is tracked in git but 'git status --porcelain' shows no change for it\
      \ \u2014 the Player claimed work on a file it did not actually modify this turn.\
      \ Most likely cause: the report writer swept an orchestrator-managed path (e.g.\
      \ a file under .guardkit/autobuild/ or tasks/<state>/) into files_modified.\
      \ Defence-in-depth for the agent_invoker-side filter; this is a warning, not\
      \ a turn-rejecting fabrication..\n... and 5 more issues"
    timestamp: '2026-07-17T17:51:38.605695'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
  - turn: 3
    decision: approve
    feedback: null
    timestamp: '2026-07-17T17:58:34.266155'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
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
