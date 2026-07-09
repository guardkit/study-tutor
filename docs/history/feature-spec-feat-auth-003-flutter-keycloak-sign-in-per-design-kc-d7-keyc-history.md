# /feature-spec — feat-auth-003-flutter-keycloak-sign-in-per-design-kc-d7-keyc — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /feature-spec feat-auth-003-flutter-keycloak-sign-in-per-design-kc-d7-keyc — 2026-07-08T20:30:45Z

### Prompt

```
/feature-spec "FEAT-AUTH-003 Flutter Keycloak sign-in per design KC-D7: KeycloakIdentityProvider behind the existing IdentityProvider port (sync currentPrincipal kept — background refresh, silent-then-interactive signIn), flutter_appauth + flutter_secure_storage deps (deliberate DoD zero-deps scope event), PKCE S256 public client with custom-scheme redirect, offline_access scope, SignInScreen loading/failure/cancel states + sign-out affordance, composeSessionApi de-typed to the port with FakeIdentityProvider kept for the hermetic flavour, Unauthenticated→routeToSignIn preserved as the hard fallback" \
  --context docs/design/keycloak-auth-user-management-design.md \
  --context app/lib/ports/identity_provider.dart \
  --context app/README.md
```

### Assistant response

I'll execute the `/feature-spec` command following the six-phase Propose-Review methodology. Let me start with Phase 1: Context Gathering.

Now let me read the primary design document and related context in parallel.

Let me examine the app's composition root, sign-in screen, Principal model, and the fake IdP to ground the spec in the actual seams.

Let me read the current sign-in screen, the app shell, the fake IdP, and the error-handling surface to capture the existing behaviour precisely.

Let me quickly check the home screen for the current Unauthenticated recovery wiring and any existing sign-out affordance.

Context loaded: stack=flutter/dart (pubspec.yaml; `--stack` maps to `generic` in the table but the project is unambiguously Flutter/Dart — I'll treat it as such), 3 context files read, IdentityProvider port + Principal + composition root + all four UI screens + FakeIdentityProvider inspected, 18 existing `.feature` files found (FEAT-AUTH-001 `keycloak-idp-standup` and FEAT-AUTH-002 `keycloak-server-token-validation` are the sibling A1/A2 slices — conventions mirrored), design doc KC-D1…KC-D7 read (this feature = KC-D7 / rollout step A3).

I have everything I need. Presenting the full proposal.

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC PROPOSAL: Flutter Keycloak Sign-In (FEAT-AUTH-003, A3)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Feature: Flutter Keycloak Sign-In
  As a student signing in on the family device
  I want the app to sign me in through the household identity provider and keep me signed in
  So that I can start and resume tutoring sessions without repeatedly re-authenticating

  Background:
    Given the study-tutor app is installed on the family device
    And the app is running against the household Keycloak identity provider

━━ GROUP A: Key Examples (6 scenarios) ━━

  # Why: Core path — a first-time sign-in through the browser flow lands the student on home
  @key-example @smoke
  Scenario: A first-time sign-in through the browser flow reaches the home screen
    Given no one is signed in on the device
    When I choose to sign in and complete authentication in the browser
    Then I should be signed in
    And I should land on the home screen ready to start a session

  # Why: The family device must stay signed in across restarts via the persisted offline session
  @key-example @smoke
  Scenario: The device stays signed in across an app restart without a browser prompt
    Given I signed in earlier and then closed the app
    When I reopen the app
    Then I should still be signed in without seeing the browser sign-in
    And I should land on the home screen

  # Why: signIn attempts a silent refresh of the stored session before ever opening the browser
  @key-example
  Scenario: Signing in reuses the stored session silently when it is still valid
    Given I have a still-valid stored session
    When I choose to sign in
    Then I should be signed in without the browser opening

  # Why: The new sign-out affordance clears the session and returns to sign-in
  @key-example @smoke
  Scenario: Signing out clears the session and returns to the sign-in screen
    Given I am signed in on the home screen
    When I sign out
    Then I should no longer be signed in
    And I should be returned to the sign-in screen

  # Why: KC-G3 — a >5-minute idle must not interrupt an active session; background refresh keeps the token fresh
  # [ASSUMPTION: confidence=high] The gate requires surviving an idle longer than 5 minutes (KC-G3)
  @key-example @smoke
  Scenario: An active session survives an idle period longer than the access-token lifetime
    Given I am signed in with an active session
    When the app sits idle for longer than the access-token lifetime and I then continue the session
    Then the session should continue without a re-sign-in prompt

  # Why: The composeSessionApi de-type to the port must not disturb the hermetic fake flavour
  @key-example @smoke @regression
  Scenario: The hermetic fake flavour still signs in with no browser and no network
    Given the app is instead built in the hermetic fake flavour with no backend configured
    When I sign in
    Then I should be signed in against the in-process fake with no browser and no network call

━━ GROUP B: Boundary Conditions (3 scenarios) ━━

  # Why: Just-inside boundary — an idle shorter than the offline-session window still refreshes silently
  # [ASSUMPTION: confidence=high] The offline-session idle limit is 30 days (KC-D4: refresh at least monthly)
  @boundary
  Scenario: A device idle just under the offline-session window refreshes without a browser
    Given I have not opened the app for just under 30 days
    When I reopen the app
    Then I should still be signed in without the browser sign-in

  # Why: Just-outside boundary — past the offline-session window the stored session is dead and the browser is required
  @boundary @negative
  Scenario: A device idle beyond the offline-session window requires an interactive sign-in
    Given I have not opened the app for more than 30 days
    When I reopen the app and choose to sign in
    Then the silent refresh should fail and the browser sign-in should be required

  # Why: Across the idle band below the offline limit, background refresh keeps the session usable
  @boundary
  Scenario Outline: Sessions remain usable across idle periods within the offline window
    Given I am signed in and the app has been idle for <idle>
    When I continue an active session
    Then the session should continue without a re-sign-in prompt

    Examples:
      | idle       |
      | 6 minutes  |
      | 1 day      |
      | 29 days    |

━━ GROUP C: Negative Cases (4 scenarios) ━━

  # Why: The cancel state — the student backs out of the browser without authenticating
  @negative @smoke
  Scenario: Cancelling the browser sign-in returns to the sign-in screen signed out
    Given no one is signed in on the device
    When I start signing in and cancel the browser without authenticating
    Then I should remain signed out
    And the sign-in screen should show that sign-in was cancelled

  # Why: The failure state — the identity provider errors or is unreachable during sign-in
  @negative @smoke
  Scenario: A failed sign-in shows a failure state and lets me try again
    Given the household identity provider cannot be reached
    When I choose to sign in
    Then the sign-in should fail
    And the sign-in screen should show a failure state offering to try again

  # Why: The preserved hard fallback — a backend-rejected token routes the student back to sign-in
  @negative @smoke @regression
  Scenario: A backend-rejected token routes the student back to sign-in
    Given I am signed in and using the app
    When the backend rejects my token as no longer valid
    Then I should be returned to the sign-in screen to sign in again

  # Why: A valid IdP login for an unprovisioned identity still cannot use the app — it lands back at sign-in
  @negative
  Scenario: Signing in as an identity with no provisioned student returns to sign-in
    Given I can authenticate at the identity provider but my identity has no provisioned student
    When I complete the browser sign-in and take my first action
    Then that action should be rejected as unauthorised
    And I should be returned to the sign-in screen

━━ GROUP D: Edge Cases (6 scenarios) ━━

  # Why: While the browser flow runs the screen shows loading and a second tap cannot start a duplicate flow
  @edge-case
  Scenario: A second sign-in tap during an in-progress sign-in is ignored
    Given no one is signed in on the device
    And a browser sign-in is already in progress showing the loading state
    When I tap sign in again
    Then only one sign-in flow should be running

  # Why: The custom-scheme redirect must complete even though the browser backgrounded the app
  @edge-case
  Scenario: A sign-in completes after the browser redirects back into the app
    Given I am authenticating in the external browser
    When the browser redirects back to the app and the app returns to the foreground
    Then the sign-in should complete and I should be signed in

  # Why: The silent-then-interactive path lets the hard-fallback loop recover without a browser when the offline token is still good
  @edge-case @regression
  Scenario: Re-signing in after a rejected token recovers silently when the stored session is still refreshable
    Given my token was rejected and I was returned to sign-in
    And my stored offline session can still be refreshed
    When I choose to sign in again
    Then I should be signed back in without the browser opening

  # Why: A failed background refresh must degrade gracefully to the sign-in fallback, never crash
  @edge-case @negative
  Scenario: A failed background refresh degrades to the sign-in fallback rather than crashing
    Given I am signed in and the background refresh can no longer reach the identity provider
    When the stored session can no longer be refreshed and I next use the app
    Then I should be returned to the sign-in screen
    And the app should not crash or hang

  # Why: If the stored session cannot be read, the app must present sign-in, not fail to launch
  @edge-case @negative
  Scenario: An unreadable stored session is treated as signed out
    Given the securely stored session cannot be read at launch
    When I open the app
    Then I should be shown the sign-in screen
    And the app should start normally rather than fail to launch

  # Why: The two new sign-in dependencies are a deliberate, recorded break from the zero-added-deps DoD
  @edge-case @regression
  Scenario: The new sign-in dependencies are recorded as a deliberate scope event
    Given the app previously declared a zero-added-runtime-dependencies definition of done
    When the sign-in feature adds its identity and secure-storage dependencies
    Then exactly those two runtime dependencies should be added
    And the addition should be recorded as a deliberate scope event

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Total: 19 scenarios across 4 groups
Inferred assumptions: 7 (will be resolved in Phase 5)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURATION: Review each group
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

For each group, you may:

  [A] Accept  — include all scenarios in this group as-is
  [R] Reject  — exclude all scenarios in this group
  [M] Modify  — accept but specify changes (provide inline)
  [+] Add     — accept and add additional scenarios you describe
  [?] Defer   — mark group for future specification; excluded from output

Fast path: type "A A A A" to accept all four groups at once.

GROUP A — Key Examples (6 scenarios): _
GROUP B — Boundary Conditions (3 scenarios): _
GROUP C — Negative Cases (4 scenarios): _
GROUP D — Edge Cases (6 scenarios): _
```

A few things I want to flag before you curate, since they shape the spec:

- **`@task:` tags** — I've left them off the proposal (FEAT-AUTH-001/002 carry them, but those were added by `/feature-plan` Step 11 after tasks existed). For FEAT-AUTH-003 the clean path is to add them via `/feature-plan` later. Say the word if you'd rather I hand-tag now.
- **Group A scenario 6** (`hermetic fake flavour still signs in`) deliberately overrides the Background flavour with "instead built in the hermetic fake flavour" — it's the one scenario proving the `composeSessionApi` port de-type didn't leak Keycloak into the hermetic gate. If you'd rather that live as a separate Feature block, tell me under [M].
- **Phase 4** will separately offer security/concurrency/integration scenarios (PKCE-S256 interception resistance, secure-store-at-rest, redirect-binding, sign-out-during-refresh, and the important **TransportError-vs-Unauthenticated** distinction — a dead GB10 must surface "connection problem", *not* route to sign-in). Hold your thoughts on those until then.

Reply with your four group decisions (e.g. `A A A A`, or per-group with `M`/`+`/`?` notes).

All four groups accepted. Let me quickly check the companion scope/build plan (you just opened it — it may pin down some of my assumptions) before presenting Phase 4.
