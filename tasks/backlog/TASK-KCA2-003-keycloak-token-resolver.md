---
id: TASK-KCA2-003
title: "KeycloakTokenResolver in http/auth_keycloak.py — PyJWT + PyJWKClient JWKS validation"
task_type: feature
parent_review: TASK-REV-KCA2
feature_id: FEAT-AUTH-002
wave: 2
implementation_mode: task-work
complexity: 8
dependencies:
- TASK-KCA2-001
- TASK-KCA2-002
consumer_context:
  - task: TASK-KCA2-001
    consumes: OIDC_SETTINGS
    framework: "PyJWT decode + PyJWKClient (asymmetric JWKS)"
    driver: "PyJWT[crypto] (cryptography for RS256)"
    format_note: "issuer stays pinned to the ts.net https name for iss validation even when STUDY_TUTOR_OIDC_JWKS_URL overrides the fetch location to a tailnet IP (KC-D2); audience must match token aud; 60s leeway on exp/nbf"
  - task: TASK-KCA2-002
    consumes: TOKEN_RESOLVER
    framework: "implements the async TokenResolver protocol"
    driver: "asyncio"
    format_note: "async resolve(token) -> student_id, raising Unauthenticated on every failure mode (never a 500)"
---

## Description

The security core of the slice — a `KeycloakTokenResolver` in the **new sibling
module** `src/study_tutor/http/auth_keycloak.py` that implements the
`TokenResolver` protocol (TASK-KCA2-002) by validating a real Keycloak access
token. Design ref KC-D6; copy-directly parts + study-tutor divergences in the
[lpa-poc reference](../../../docs/design/references/keycloak-validation-reference-lpa-poc.md).

**Validation pipeline (all failures → `Unauthenticated`, never an unexpected error):**

- **Signature** via `jwt.PyJWKClient(jwks_url)` (cached, kid-rotation aware —
  refetches on an unknown kid, and concurrent first requests share one fetch).
- **`iss`** must equal `OIDCSettings.issuer` (the ts.net name), even when JWKS was
  fetched via the tailnet-IP override (KC-D2 gotcha).
- **`aud`** must include `OIDCSettings.audience`.
- **`exp`/`nbf`** with `leeway=60s` (ASSUM-001) — expired or not-yet-valid → refuse.
- **Algorithm allowlist — asymmetric only (`["RS256"]`).** Reject `alg: none` and
  any symmetric algorithm (HS256) explicitly. This blocks the classic JWKS
  alg-confusion attack; use a positive allowlist, never a denylist.
- **Claim extraction:** read `OIDCSettings.student_claim` (default `student_id`);
  a validly-signed token **missing** the claim is a clean `Unauthenticated`
  (KC-D3 / ASSUM-001 — a mis-provisioned attribute is a 401, never a 500).
- **Fail-closed on infra:** unreachable JWKS / key fetch error → `Unauthenticated`,
  not a 500.

The unseeded-student guard is **not** re-implemented here — it stays in
`resolve_student_from_token` (TASK-KCA2-002) and runs after `resolve` returns.

**AC-005:** the `jwt` / `PyJWKClient` imports live **only** in this file.

**Hermetic tests (`tests/unit/http/test_auth_keycloak.py`) — no live infra:**
mint an RSA keypair in-test, build a fake JWKS, monkeypatch `PyJWKClient` to serve
it, and cover: valid claim → student id · expired · not-yet-valid (beyond skew) ·
within-skew accepted · wrong `iss` · wrong `aud` · missing student claim ·
unknown kid · `alg:none` · HS256 (symmetric) · unreachable JWKS · key rotation ·
concurrent first-request fetch.

## Acceptance Criteria

- [ ] `KeycloakTokenResolver` in `src/study_tutor/http/auth_keycloak.py` implements `TokenResolver` and validates signature, `iss`, `aud`, `exp`/`nbf` (60s leeway), and an RS256-only algorithm allowlist
- [ ] The `student_id` claim (name from `OIDCSettings.student_claim`) is extracted only **after** validation; a missing claim raises `Unauthenticated`, never a 500
- [ ] Every negative path (bad signature, wrong issuer, wrong audience, expired, not-yet-valid, `alg:none`/HS256, unknown kid, unreachable JWKS, garbage token) raises `Unauthenticated` and raises no unexpected error
- [ ] Issuer used for `iss` validation stays the ts.net name even when the JWKS fetch URL is overridden to a tailnet IP (KC-D2)
- [ ] Hermetic tests mint their own keys and monkeypatch JWKS — no live realm and no network
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Served

- "In keycloak mode a valid identity token identifies the student from its verified claim" (@smoke)
- All of GROUP C (negative) and GROUP D (edge/security) keycloak scenarios: unrecognised signature, unexpected issuer, wrong audience, missing/garbage claim, rotated key, tailnet-address fetch, unexpected algorithm, unknown key id, unreachable keys, concurrent fetch, not-yet-valid

## Seam Tests

Validates the `OIDC_SETTINGS` integration contract (issuer-pinning) at the boundary.

```python
"""Seam test: verify OIDC_SETTINGS contract from TASK-KCA2-001."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("OIDC_SETTINGS")
def test_oidc_settings_issuer_pinning():
    """Issuer stays pinned to the ts.net name even under a JWKS-URL override.

    Contract: STUDY_TUTOR_OIDC_JWKS_URL overrides only the fetch location
    (KC-D2 tailnet-IP gotcha); the issuer used for `iss` validation is the
    ts.net public name from STUDY_TUTOR_OIDC_ISSUER, never the fetch URL.
    Producer: TASK-KCA2-001
    """
    from study_tutor.http.oidc_config import OIDCSettings

    settings = OIDCSettings.from_env(
        env={
            "STUDY_TUTOR_AUTH_MODE": "keycloak",
            "STUDY_TUTOR_OIDC_ISSUER": "https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor",
            "STUDY_TUTOR_OIDC_AUDIENCE": "study-tutor-app",
            "STUDY_TUTOR_OIDC_JWKS_URL": "https://100.92.74.2:8443/realms/study-tutor/protocol/openid-connect/certs",
        }
    )
    resolver = KeycloakTokenResolver(settings)  # noqa: F821 (illustrative)
    # The issuer enforced during validation is the ts.net name, not the IP:
    assert resolver.expected_issuer == settings.issuer
    assert "ts.net" in resolver.expected_issuer
    assert resolver.expected_issuer != settings.jwks_url
```

## References

- design [KC-D6](../../../docs/design/keycloak-auth-user-management-design.md) · [lpa-poc reference](../../../docs/design/references/keycloak-validation-reference-lpa-poc.md) (proven core + divergences) · IMPLEMENTATION-GUIDE §4 (`OIDC_SETTINGS`, `TOKEN_RESOLVER`) · security-critical (JWKS validation) ⇒ FULL_REQUIRED human checkpoint
</content>
</invoke>
