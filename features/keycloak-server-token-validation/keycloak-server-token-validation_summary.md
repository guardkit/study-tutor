# Feature Spec Summary: Keycloak Server-Side Token Validation (FEAT-AUTH-002, A2)

**Stack**: python
**Generated**: 2026-07-08T19:50:14Z
**Scenarios**: 25 total (2 smoke, 1 regression)
**Assumptions**: 7 total (3 high / 2 medium / 2 low confidence)
**Review required**: Yes

## Scope

FEAT-AUTH-002 is the **A2 server slice** of the Keycloak auth design (KC-D6). It introduces a
`TokenResolver` protocol (`async resolve(token) -> student_id`, raising `Unauthenticated`) behind
which `resolve_student_from_token` keeps its outer contract unchanged — Bearer extraction and the
unseeded-student guard (ASSUM-001, binding §3) — delegating only "step 2" (the derivation source).
`TableTokenResolver` stays in `auth.py` preserving today's behaviour byte-for-byte; a new sibling
module `http/auth_keycloak.py` carries `KeycloakTokenResolver` (PyJWT + `PyJWKClient`; validates
signature, `iss`, `aud`, `exp`; extracts the `student_id` claim per KC-D3; JWKS-URL override for the
`extra_hosts`/IP-fetch gotcha, KC-D2). `STUDY_TUTOR_AUTH_MODE=table|keycloak` selects the resolver,
with boot fail-fast on incomplete OIDC config; the AC-005 tripwire is re-scoped to keep `auth.py`
JWT-free; the WS upgrade path inherits the resolver automatically; the live contract suite mints
tokens via the dev-realm live-suite client while hermetic suites stay on table mode.

## Scenario Counts by Category

Categories overlap (several scenarios carry more than one tag); the distinct total is 25.

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 4 |
| Boundary conditions (@boundary) | 5 |
| Negative cases (@negative) | 12 |
| Edge cases (@edge-case) | 11 |
| Smoke (@smoke) | 2 |
| Regression (@regression) | 1 |
| Security (@security) | 2 |
| Concurrency (@concurrency) | 1 |
| Integration (@integration) | 1 |

## Deferred Items

None — all four proposed groups and all six edge-case expansion scenarios were accepted.

## Open Assumptions (low confidence)

- **ASSUM-001** — Clock-skew leeway of 60s on `exp`/`nbf`. Not stated in the design or `auth.py`;
  PyJWT defaults to 0. Coach should confirm the intended leeway (and whether `nbf` is enforced at
  all) against the KeycloakTokenResolver implementation before freeze.
- **ASSUM-007** — Unknown/typo `STUDY_TUTOR_AUTH_MODE` value fails fast at boot. Not stated in the
  design; only `table|keycloak` are defined. Coach should confirm the intended posture (reject vs
  silent fallback) against KC-D6's boot discipline.

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "Keycloak Server-Side Token Validation" \
      --context features/keycloak-server-token-validation/keycloak-server-token-validation_summary.md \
      --context docs/design/keycloak-auth-user-management-design.md

Step 11 (Link BDD scenarios to tasks) will attach `@task:<TASK-ID>` tags to these scenarios once
the A2 tasks are created — no hand-tagging needed. The `@smoke` scenarios (table byte-for-byte
identity; keycloak valid-claim identity) are the minimal Coach-blocking oracle set for the slice.
