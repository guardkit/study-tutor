# /feature-spec — feat-auth-002-server-keycloak-validation-per-design-kc-d6-to — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /feature-spec feat-auth-002-server-keycloak-validation-per-design-kc-d6-to — 2026-07-08T19:43:27Z

### Prompt

```
/feature-spec "FEAT-AUTH-002 server Keycloak validation per design KC-D6: TokenResolver protocol (async resolve(token)->student_id raising Unauthenticated), TableTokenResolver preserving current auth.py behaviour byte-for-byte, KeycloakTokenResolver in new http/auth_keycloak.py (PyJWT+PyJWKClient, validate iss/aud/exp/signature, student_id claim per KC-D3, JWKS URL override for the extra_hosts gotcha), STUDY_TUTOR_AUTH_MODE=table|keycloak with boot fail-fast on incomplete OIDC config, AC-005 tripwire re-scoped to keep auth.py JWT-free, unseeded-guard and Bearer extraction unchanged (ASSUM-001, binding §3), WS upgrade path inherits automatically, live-suite token helper via the dev-realm live-suite client, hermetic tests stay on table mode" \
  --context docs/design/keycloak-auth-user-management-design.md \
  --context src/study_tutor/http/auth.py \
  --context docs/design/contracts/API-session-http-binding.md
```

### Assistant response

I'll execute the feature-spec workflow. Starting with Phase 1: silent context gathering.
