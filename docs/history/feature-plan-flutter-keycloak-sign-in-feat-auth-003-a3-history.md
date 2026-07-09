# /feature-plan — flutter-keycloak-sign-in-feat-auth-003-a3 — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /feature-plan flutter-keycloak-sign-in-feat-auth-003-a3 — 2026-07-08T21:53:48Z

### Prompt

```
/feature-plan "Flutter Keycloak Sign-In (FEAT-AUTH-003, A3)" \
      --context features/flutter-keycloak-sign-in/flutter-keycloak-sign-in_summary.md
```

### Assistant response

I'll start by reading the context file and exploring the existing Keycloak auth structure, since there's clearly related work in progress (FEAT-AUTH-001 and FEAT-AUTH-002 already exist).

Let me read the full feature spec, assumptions, the design doc, and the sibling A2 feature YAML as a structural reference.

Now let me ground the plan in the actual app codebase — the port, composition seam, and error handling referenced in the spec — plus the KC-D7 design section.

Let me read the composition seam, sign-in screen, fake provider, and the KC-D7 design section to fully ground the task breakdown.

Let me check the Flutter test structure and how the fake flavour/BDD wiring works on the app side.

I have a thorough grounding now: the frozen KC-D7 design, the 3-member port, the composition seam, the existing error-handling split, and the A2 feature as a structural template. Let me verify the Flutter test tooling before finalizing the smoke gate.

Flutter isn't on PATH — that affects whether a `flutter test` smoke gate is safe. Let me check for it under common install locations.

I now have everything I need. Flutter 3.44.4 is the project toolchain (invoked as `cd app && flutter test` per the runbook — it's not on this shell's PATH but is present in the build env). Here's my analysis before the decision checkpoint.

---

## 🔍 Feature Planning: Flutter Keycloak Sign-In (FEAT-AUTH-003, A3)

**Design is frozen (KC-D7, gate KC-G3)** — this isn't a "choose between 3 approaches" decision. The spec + design fix the technical path: a real `KeycloakIdentityProvider` behind the unchanged 3-member port, `flutter_appauth` + `flutter_secure_storage`, PKCE S256 public-client with a custom-scheme redirect and `offline_access`, silent-then-interactive `signIn()`, proactive background refresh, sync `currentPrincipal` retained. So the review value here is **decomposition + seam/contract correctness**, not option-picking.

**Grounding confirmed in the codebase:**
- Port [identity_provider.dart](app/lib/ports/identity_provider.dart) — 3 members, sync `currentPrincipal`. Adapter must satisfy it unchanged.
- Composition seam [main.dart:21](app/lib/main.dart#L21) — `composeSessionApi(String, FakeIdentityProvider)`. A3 de-types the `identity` param to the port; hermetic fake flavour keeps the concrete `FakeIdentityProvider` for its `studentIdForToken` introspection hook.
- [error_handling.dart](app/lib/ui/error_handling.dart) — `Unauthenticated → routeToSignIn` vs `TransportError → showConnectionProblem` already exist and are distinct. A3 **preserves** this; the two Group-E scenarios are regression guards, not new code.
- Native config present: [AndroidManifest.xml](app/android/app/src/main/AndroidManifest.xml), [Info.plist](app/ios/Runner/Info.plist) — both need the redirect intent-filter / URL scheme.

**Proposed decomposition — 7 tasks, 6 waves** (mirrors the A2 shape; wave 6 is the operator gate, no code):

| Task | Type | Cx | Wave | Serves |
|------|------|----|----|--------|
| KCA3-001 deps + native redirect config + `KeycloakConfig` | scaffolding | 4 | 1 | scope-event, redirect config |
| KCA3-002 `SecureSessionStore` (secure_storage, read/write/clear, unreadable→signed-out) | feature | 5 | 2 | secure-store + unreadable scenarios |
| KCA3-005 sign-out affordance (home app-bar → signOut → routeToSignIn) | feature | 3 | 2 | sign-out scenario |
| KCA3-003 `KeycloakIdentityProvider` (silent-then-interactive, PKCE, background refresh, single-flight, signOut-wins-refresh) | feature | 8 | 3 | Groups A/B/D + E-security |
| KCA3-004 SignInScreen loading/failure/cancel + try-again (failure≠cancel) | feature | 5 | 4 | Group C + discovery scenario |
| KCA3-006 composition de-type + real-flavour wiring; TransportError/Unauthenticated regression guard | refactor | 6 | 5 | hermetic-fake, both routing scenarios |
| KCA3-007 KC-G3 live gate (real device, >5-min idle, restart) | **operator_handoff** | 5 | 6 | live end-to-end (AutoBuild skips) |

**§4 Integration Contracts**: `REDIRECT_URI` (001→003,006), `OIDC_CLIENT_CONFIG` (001→003), `STORED_SESSION` (002→003), sign-in outcome types cancel≠failure (003→004).

**Smoke gate**: `cd app && flutter test` after waves 3 and 5 (composition gate). Wave 6 is operator_handoff — not gated (the "final wave not covered" warning is expected, same as A2).

**⚠️ One flagged operator gate (ASSUM-003, low-confidence, review-required):** the custom-scheme redirect `com.appmilla.studytutor:/oauth2redirect` must be **byte-identical** in three places (Keycloak `study-tutor-app` client, Android intent-filter, iOS `CFBundleURLSchemes`). The assumptions file already records a human override to this value — I need you to confirm it's final before I freeze it into KCA3-001.

Two decisions before I generate the structure:

All three on the recommended path — redirect URI confirmed, Standard testing, 7 tasks. Let me match the A1/A2 house style before generating, then create everything.

Now I have the exact house style. Let me read the complex feature task and the operator_handoff task bodies to match them precisely.

All three answers on the recommended path. I have the exact A2 template. Now generating the full FEAT-AUTH-003 structure — 7 task files, README, and the IMPLEMENTATION-GUIDE with the mandatory diagrams.

Now the IMPLEMENTATION-GUIDE with the three mandatory diagrams and §4 contracts, then the README.

All 9 files created. Now generate the structured YAML. Let me check the script's flags to pin the `FEAT-AUTH-003` id (the A1/A2 YAMLs use explicit IDs, not auto-generated).

The dependency graph needs one alignment: I documented `wave 2 = {002, 005}`, but with `005` having no deps the generator would place it in wave 1. Making `005` depend on `001` (the feature foundation lands first) keeps waves clean and matches the docs. Let me fix `005`'s frontmatter and the §3 diagram edge.

Now generate the structured YAML with `--discover` and the pinned `FEAT-AUTH-003` id:

Waves match my design exactly, and AC-quality review is clean (0 unverifiable). The R3 nudge fired as expected (6 waves, no smoke gate) — note its example suggests `pytest` roots, but this is the **Flutter** slice, so the correct gate is `cd app && flutter test`. Let me add the `smoke_gates` block I documented, then read back the YAML.

The YAML is well-formed. Now append the `smoke_gates` block (Flutter command, after waves 3 and 5, matching the IMPLEMENTATION-GUIDE):

Now the pre-flight validations (feature validate + smoke-gate validate):

✓ Feature valid. The lone warning ("does not cover the final wave 6") is the expected operator_handoff KC-G3 gate — documented in both the YAML and the guide, same as A2. Smoke-gate validation correctly skipped (Flutter, not pytest).

Now **Step 11 — BDD scenario linking** (add `@task:` tags to the 25 scenarios). First, prepare the matching request:

`status: ready` — 25 scenarios, 7 tasks. Now Step 11.2 — invoke the `bdd-linker` subagent with the request payload:

Now I'll invoke the `bdd-linker` subagent to match scenarios → tasks (Step 11.2):

All 25 scenarios matched above threshold, with sensible mappings (sign-out→005, hermetic-fake & routing→006, secure-store→002, scope-event→001, failure-state→004, adapter behaviours→003). Now write the response and apply the tags (Step 11.3):

All 25 scenarios tagged. Let me verify the tags landed and do a final consistency check across the generated artifacts:

Everything is consistent — 25 tags across the 6 code-bearing tasks (007 the operator gate correctly gets none), 9 files, correct `task_type` distribution, valid YAML with smoke gates. Let me clean up the temp request files.
