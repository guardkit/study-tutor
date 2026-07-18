# C1 Merge-Review Packet — Weekend Auth (A2 now; A3 appended when it lands)

**For:** Rich · **Prepared:** 2026-07-17 by the weekend Fable session.
**Verdict sought:** approve / query each FULL_REQUIRED diff. On "A2 approved" Fable runs
`/feature-complete FEAT-AUTH-002` (FF-merge to main); push waits for C5.

---

## A2 — FEAT-AUTH-002 server-side Keycloak validation

**Branch:** `autobuild/FEAT-AUTH-002` (worktree `.guardkit/worktrees/FEAT-AUTH-002`).
**Outcome:** 7/7 tasks. KC-G2 (KCA2-007) short-circuited to operator — that's your C3.
**State:** autobuild commits + two Fable review-fix commits (`255e0b5`, `261d1f7`).

### The three diffs to skim (FULL_REQUIRED)

```bash
cd ~/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-AUTH-002
git diff main -- src/study_tutor/http/auth.py            # KCA2-002 TokenResolver seam
git diff main -- src/study_tutor/http/auth_keycloak.py   # KCA2-003 security core (194 lines, new)
git diff main -- src/study_tutor/cli/main.py             # KCA2-004 boot wiring + mode select
# supporting: http/oidc_config.py (new), tests/unit/http/test_auth_keycloak.py (500 lines),
#             tests/integration/test_keycloak_contract.py (KCA2-006 harness, skips w/o live env)
```

### What to look at, per diff

- **auth.py (seam):** `TokenResolver` Protocol + `TableTokenResolver` extraction;
  `HTTPAuthConfig` gains `resolver` — **defaults to table via `__post_init__`**
  (Fable fix: five direct-construction callsites in cli/gamification tests broke when
  the field was required; the default mirrors `from_env`'s documented table-mode
  semantics, keeping KCA2-002's "existing tests pass unchanged" AC true). Mode
  *selection* stays in the boot path — the default is parity, not selection.
- **auth_keycloak.py (cx-8 core):** PyJWKClient + `jwt.decode` with explicit
  `algorithms=["RS256"]`, issuer pinned to `settings.issuer` (KC-D2 — independent of
  any JWKS IP override), audience/exp/nbf enforced with 60s leeway, every failure
  branch → `Unauthenticated`. Fable fix (SEC-1): JWKS lookup wrapped in
  `asyncio.to_thread` so an unknown-`kid` flood can't stall the shared event loop.
- **cli/main.py (boot):** fail-fast `SystemExit(1)` on invalid OIDC env; resolver
  selection extracted to `_select_token_resolver()` (Fable fix F3 — makes the AC-003
  lazy-import fence executable in tests); keycloak branch lazy-imports
  `auth_keycloak`; `dev_reset` force-`false` in keycloak mode.

### Fence evidence (verified by Fable directly, not from coach verdicts)

| Fence | Evidence |
|---|---|
| AC-005 tripwire — auth.py JWT-free | grep: zero jwt/jose/keycloak imports (prose mentions only); imports = json/logging/dataclasses/typing/errors |
| app.py / ws.py callsites unchanged | `git diff main -- http/app.py http/ws.py` → empty |
| RS256 positive allowlist | `auth_keycloak.py:124` `algorithms=["RS256"]` |
| iss pinned (KC-D2) | `expected_issuer` set from `settings.issuer`, never from JWKS URL |
| Failures → Unauthenticated, never 500 | every except branch mapped; broad catch-all included |
| Unseeded guard stays post-resolve | `resolve_student_from_token` in auth.py unchanged in position |
| dev-reset × keycloak never coexist | `cli/main.py` forces `dev_reset="false"` in keycloak branch + `test_dev_reset_not_mounted_in_keycloak_mode` |
| Hermetic: in-test RSA keys, no live realm | test_auth_keycloak.py mints keys in-test; KCA2-006 skips cleanly without env |
| No secrets in diff | scan clean |

**Suites:** `tests/unit/http` 121 passed · full repo suite **1587 passed** — identical
to the main baseline (remaining 1 failure + 9 errors reproduce on main with the
loopback throwaway PG: pre-existing `test_no_whitestocks_connection_in_tests` +
unmigrated-schema PG errors; not A2's).

### Adversarial review (wf_b80118b0-46c): 3 lenses → refute pass

- **Confirmed + fixed (both minor):** SEC-1 event-loop-blocking JWKS fetch (fixed,
  `261d1f7`); F3 no-op lazy-import proxy test (now executable, `261d1f7`).
- **Refuted, worth knowing:**
  - The `dir()`-based AC-005 tripwire test misses `from jwt import X` / aliased
    imports — **pre-existing on main verbatim**, coach grep remains the primary
    tripwire. Candidate future hardening, not this lane's regression.
  - (2nd refuted finding was a duplicate-of-SEC-1 variant; see workflow journal.)
- **Future hardening noted, deliberately not done now:** negative caching /
  rate-limit for unknown-`kid` JWKS lookups (tailnet-only deploy bounds it);
  guardkit smoke-gate scope for A2-style features should include `tests/unit/cli`
  (that gap is how the 5 broken callsites slipped past per-task gates).

### Process notes (for the record)

- One infra block mid-run: the plan-audit gate parsed the AC phrase
  "`app.py`/`ws.py` callsites unchanged" as a literal path `/app.py/ws.py` and
  deterministically failed KCA2-004 for 5 turns. Fixed by rewording the AC to real
  paths (task .md, both copies); task then approved in 1 turn. No fence was relaxed.
- `uv.lock` regenerated on-branch (PyJWT dep) — also absorbs the pending sibling
  `nats-core` 0.5.0→0.7.1 drift that was sitting dirty in the main tree.

---

## A3 — FEAT-AUTH-003 Flutter sign-in — READY (2026-07-17 evening)

**Branch:** `autobuild/FEAT-AUTH-003` (worktree `.guardkit/worktrees/FEAT-AUTH-003`).
**Outcome:** 7/7 tasks (KC-G3 deferred to Batch C4). Autobuild + THREE Fable commits:
the KCA3-003 unblock (whenComplete zone-error fix), the realm redirect-URI fix
(`fa49ce5`), and the six-finding review batch (`2cb537f`).
**State:** `flutter analyze` 0 issues · **338/338 tests pass** (arm64 toolchain).

### Your two steps

1. **Mac toolchain-of-record verify (~5 min):** on the MacBook —
   `git fetch && git checkout autobuild/FEAT-AUTH-003 && cd app && flutter analyze && flutter test`
   (official 3.44.4; expect 0 issues / 338 pass — tell me any delta).
2. **Skim the FULL_REQUIRED diff:** `git diff main -- app/lib/adapters/keycloak_identity_provider.dart`
   (KCA3-003, cx-8) — plus, if time allows, `app/lib/main.dart` (flavour wiring) and
   `app/lib/adapters/secure_session_store.dart`.

### Adversarial review (wf_04337153-2d6): 6 raw → 6 CONFIRMED → all fixed on-branch

| # | Sev | What it was | Fix |
|---|---|---|---|
| AUTH-1 | **blocker** | Real flutter_appauth 8.x cancel = `FlutterAppAuthUserCancelledException`, a SIBLING of the caught type → real cancel escaped uncaught, sign-in screen hung on the spinner; test passed only because the fake threw the wrong type | Explicit catch → `SignInCancelled`; fake now throws the real type |
| F1 | **blocker** | Silent refresh gated on access-token freshness → the *normal* >5-min-idle case forced the browser (would fail KC-G3's idle-refresh AC) | Silent refresh always attempted when a refresh token exists |
| AUTH-2 | major | Store write raced `signOut` (write before generation guard) → signed-out session resurrected next launch on the family device | Generation-guarded write + post-write re-check + compensating clear; regression test |
| F2 | minor | `KEYCLOAK_ISSUER` set + `API_BASE_URL` empty → as-cast boot crash | `assertFlavourCoherence` fails fast with actionable message |
| TEST-1 | major | Proactive-refresh test was satisfied by the sign-in refresh alone (timer never proven) | Fake `tokenLifetime` shortened past the 5-min threshold; asserts a SECOND refresh |
| TEST-2 | minor | Corrupt-store test asserted a pre-read constant | Now drives `signIn()`, asserts fail-closed → interactive |

### Fence evidence (Fable-verified directly)

| Fence | Evidence |
|---|---|
| Redirect URI byte-identical ×4 | config `:/oauth2redirect` = android scheme = iOS scheme; **realm-as-code fixed `fa49ce5`** (A1 had `://` — LIVE NAS client patch queued before KC-G3) |
| 3-member port unchanged | `git diff main -- app/lib/ports/identity_provider.dart` → empty |
| Runtime deps = exactly 2 | `flutter_appauth` + `flutter_secure_storage` (yaml is dev_dependencies) |
| Scopes / PKCE | `[openid, offline_access]`; S256 (flutter_appauth default, verified in package) |
| currentPrincipal sync, no I/O | in-memory field only |
| Cancel ≠ Failure | now guarded by a test that throws the REAL SDK type |
| signOut wins in-flight | generation bump + guarded persist + regression test |
| Store fail-closed | absent/corrupt → null → interactive (tests) |
| Fake flavour purity | `composeIdentity` keeps concrete fake; coherence guard prevents mixing |

### Queued consequence for Batch C
Before KC-G3 (C4): patch the **live** NAS `study-tutor-app` client's redirectUris to
`com.appmilla.studytutor:/oauth2redirect` via admin API (one call, alongside C2).

---

## MERGED — approval record (2026-07-18)

- **A2**: approved by Rich 2026-07-17 → merged `b03cbbf`.
- **A3**: Mac toolchain-of-record verify (official 3.44.4): analyze 0 issues,
  338/338, zero delta; 17 independent verifiers, 0 refuted. Approved with one
  condition (strip committed test-output artifacts) → stripped + gitignored on
  branch, merged `bf9ed99`. Remote branch deleted; all pushed.

### Post-merge follow-ups (from the Mac verify's PARTIALs — none defects)

1. **AUTH-2 depth**: completer-controlled fake-store `write()` so the post-write
   re-check + compensating clear (`keycloak_identity_provider.dart:~182-187`)
   becomes test-reachable; also assert store-cleared (not just principal-null)
   in the refresh-race test.
2. **Scopes on the wire**: assert `[openid, offline_access]` on the outgoing
   Token/Authorization requests, not just the frozen constant.
3. **Design note**: `SignInCancelled`/`SignInFailed` live beside the adapter but
   are the port's de-facto error taxonomy — a second IdentityProvider impl must
   throw the same types (consider moving them portside when one appears).
4. **Observation**: when signOut wins the race, `_handleTokenResponse` still
   returns the principal to the awaiting `signIn()` caller (publish suppressed,
   nothing persists) — cosmetic UI edge, revisit with #1.

### Still queued for Batch C
Live NAS `study-tutor-app` client redirectUris → `com.appmilla.studytutor:/oauth2redirect`
(admin API, one call, alongside C2) — realm-as-code already fixed (`fa49ce5`).
