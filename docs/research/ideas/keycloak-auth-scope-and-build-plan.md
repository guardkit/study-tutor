# Auth — Keycloak + User Management (D9 execution) — Scope + Build Plan

**Status:** Drafted 2026-07-06 (Fable window). Sequencing layer over the
[design](../../design/keycloak-auth-user-management-design.md) (KC-D1…KC-D7 + rollout).
**Blocked on:** the design's §5 ratification checklist (KC-D1/D2 `/arch-refine`; KC-D4/D5 owner
sign-off). Nothing else — the contract/binding are untouched by construction.
**Model allocation (voice plan §0a discipline):** this doc + the design = **Fable**;
`/feature-spec` + `/feature-plan` = Fable if run by 2026-07-07, else **Opus with the design as
context**; all builds = **Opus**; A1 standup + cutovers = **Operator + Opus**.

---

## 1. Scope

**In:** Keycloak 26.6.x on the NAS (container, `keycloak` DB in `study_tutor_postgres`,
realm-as-code, tailscale cert, backup.sh extension); server `TokenResolver` seam +
`http/auth_keycloak.py` JWT validation behind `STUDY_TUTOR_AUTH_MODE`; Flutter
`KeycloakIdentityProvider` (appauth + secure storage, sign-in/out UX); Reachy device-grant pairing
+ `ask_tutor` bearer injection; dev-realm live-suite token client; cutover + rollback runbook steps.

**Out:** multi-tenancy; parent endpoints/UI (role reserved only); MCP surface auth; contract or
binding changes (frozen; none needed); WAN exposure; token-rotation hardening beyond defaults.

## 2. Feature decomposition

| Feature | Gist | Depends on |
|---|---|---|
| **FEAT-AUTH-001** | Keycloak standup on the NAS: container + DB + realm-as-code (`deploy/keycloak/realm/`) + TLS + users + backup extension. Mostly an **executable runbook** (operator_handoff-heavy) with a small repo artifact footprint | design ratification (§5 checklist) |
| **FEAT-AUTH-002** | Server validation: `TokenResolver` protocol refactor of `auth.py` step 2, new `auth_keycloak.py` (PyJWT/JWKS), env selection + boot fail-fast, re-scoped AC-005 tripwire, live-suite token helper. Flag-gated: merging changes nothing while mode=`table` | FEAT-AUTH-001 (a realm to validate against, for the live variants) |
| **FEAT-AUTH-003** | Flutter sign-in: `KeycloakIdentityProvider` behind the unchanged port, `flutter_appauth` + `flutter_secure_storage` (DoD scope event), SignInScreen states + sign-out, `composeSessionApi` de-typing | FEAT-AUTH-002 dev deploy in keycloak mode |
| **FEAT-AUTH-004** | Reachy pairing: device-grant flow, Pi token file + refresh, `ask_tutor` bearer injection; KC-G4 = the D8 same-subject resume proof | FEAT-AUTH-002 **and** voice R3 (`ask_tutor` exists) |

## 3. Sequencing

```
ratify (§5 checklist) ──► A1 (FEAT-AUTH-001 standup) ──► A2 (FEAT-AUTH-002 server, flag-gated)
                                                            ├──► A3 (FEAT-AUTH-003 app)
                                                            └──► A4 (FEAT-AUTH-004 robot; also needs voice R3)
A3 ──► prod cutover (env flip, rollback = flip back; table retired from prod config after a week green)
```

Gates KC-G1…KC-G4 per the design §3. Fully parallel to the voice W-track (dev flavour stays on
table mode); A4 is the only voice-coupled step.

## 4. /feature-spec invocations (run in wave order, after ratification)

```bash
/feature-spec "FEAT-AUTH-001 Keycloak standup on the NAS per design KC-D1/D2/D3: study_tutor_keycloak container (quay.io/keycloak/keycloak 26.6.x pinned, start --optimized, 2GB memory limit), keycloak database+role in study_tutor_postgres :5434, realm-as-code import from deploy/keycloak/realm/ (realm study-tutor, clients study-tutor-app/reachy-robot/live-suite per KC-D4, roles student+parent, student_id attribute→claim protocol mapper — users runbook-created, never in git), tailscale cert for whitestocks.tailebf801.ts.net + https issuer, backup.sh second pg_dump line, executable standup runbook with KC-G1 gate incl. NAS RAM before/after" \
  --context docs/design/keycloak-auth-user-management-design.md \
  --context docs/runbooks/RUNBOOK-study-tutor-postgres-deploy.md \
  --context deploy/postgres/backup.sh

/feature-spec "FEAT-AUTH-002 server Keycloak validation per design KC-D6: TokenResolver protocol (async resolve(token)->student_id raising Unauthenticated), TableTokenResolver preserving current auth.py behaviour byte-for-byte, KeycloakTokenResolver in new http/auth_keycloak.py (PyJWT+PyJWKClient, validate iss/aud/exp/signature, student_id claim per KC-D3, JWKS URL override for the extra_hosts gotcha), STUDY_TUTOR_AUTH_MODE=table|keycloak with boot fail-fast on incomplete OIDC config, AC-005 tripwire re-scoped to keep auth.py JWT-free, unseeded-guard and Bearer extraction unchanged (ASSUM-001, binding §3), WS upgrade path inherits automatically, live-suite token helper via the dev-realm live-suite client, hermetic tests stay on table mode" \
  --context docs/design/keycloak-auth-user-management-design.md \
  --context src/study_tutor/http/auth.py \
  --context docs/design/contracts/API-session-http-binding.md

/feature-spec "FEAT-AUTH-003 Flutter Keycloak sign-in per design KC-D7: KeycloakIdentityProvider behind the existing IdentityProvider port (sync currentPrincipal kept — background refresh, silent-then-interactive signIn), flutter_appauth + flutter_secure_storage deps (deliberate DoD zero-deps scope event), PKCE S256 public client with custom-scheme redirect, offline_access scope, SignInScreen loading/failure/cancel states + sign-out affordance, composeSessionApi de-typed to the port with FakeIdentityProvider kept for the hermetic flavour, Unauthenticated→routeToSignIn preserved as the hard fallback" \
  --context docs/design/keycloak-auth-user-management-design.md \
  --context app/lib/ports/identity_provider.dart \
  --context app/README.md

# FEAT-AUTH-004 spec is cut AFTER voice R3 lands (ask_tutor exists) — device-grant pairing,
# Pi token file + monthly-refresh discipline, ask_tutor bearer injection, KC-G4 D8 proof.
```

Each followed by `/feature-plan "<title>" --context features/<slug>/<slug>_summary.md`.

## 5. Cross-cutting

- **ADR-ARCH-028 (candidate):** self-hosted IdP placement + tailnet-only posture — record at
  ratification via `/arch-refine`.
- **Contract §11 OQ1:** resolved by KC-D3; fold the text edit into the next coordinated
  `/design-refine` touch (doc-only, no freeze event of its own).
- **Voice plan:** its Out-list line ("Keycloak — D9 lands separately") now points here; A4 ↔ R3
  coupling noted in both plans.
- **`seed-students`:** `--student-ids` becomes the primary path; token-table default is legacy
  once prod cuts over.
- **Live suite:** gains a keycloak-mode variant (token acquisition helper); hermetic suites remain
  derivation-agnostic by construction.

## 6. Next steps

1. **Owner:** ratify the design §5 checklist (KC-D1/D2 via `/arch-refine`; KC-D4/D5 sign-off;
   NAS RAM op-check).
2. **Fable (if window remains) else Opus:** run §4 specs + plans in wave order.
3. **Operator + Opus:** A1 standup runbook; then A2→A3 builds per §3.
4. **After voice R3:** cut FEAT-AUTH-004's spec; run A4; prod cutover last.

---

*Generated 2026-07-06. Companion design:
[keycloak-auth-user-management-design.md](../../design/keycloak-auth-user-management-design.md).*
