---
complexity: 5
consumer_context:
- consumes: TOKEN_RESOLVER
  driver: click CLI + uvicorn boot
  format_note: select TableTokenResolver in table mode, KeycloakTokenResolver in keycloak
    mode; inject via HTTPAuthConfig.resolver so app.py/ws.py callsites are unchanged
  framework: Starlette boot wiring — HTTPAuthConfig.resolver injected at serve_http
  task: TASK-KCA2-002
- consumes: OIDC_SETTINGS
  driver: SystemExit(1) matching the DSN discipline
  format_note: non-empty validate() list -> click.echo(err) + SystemExit(1); unknown
    STUDY_TUTOR_AUTH_MODE also fails fast
  framework: boot fail-fast on OIDCSettings.validate()
  task: TASK-KCA2-001
dependencies:
- TASK-KCA2-001
- TASK-KCA2-002
- TASK-KCA2-003
feature_id: FEAT-AUTH-002
id: TASK-KCA2-004
implementation_mode: task-work
parent_review: TASK-REV-KCA2
status: design_approved
task_type: feature
title: Boot wiring — STUDY_TUTOR_AUTH_MODE resolver selection + fail-fast, thread
  resolver into HTTPAuthConfig
wave: 3
---

## Description

Wire mode selection and boot fail-fast into the HTTP server boot path
([cli/main.py `serve_http`](../../../src/study_tutor/cli/main.py)) so the right
`TokenResolver` is injected and a mis-configured keycloak mode never starts
serving. Consumer of both §4 contracts.

**Deliverables:**

1. Load `OIDCSettings.from_env(...)` at boot; call `validate()`. A **non-empty**
   result → `click.echo(...err=True)` + `raise SystemExit(1)` (mirrors the
   `STUDY_TUTOR_PG_DSN` fail-fast at [cli/main.py:869](../../../src/study_tutor/cli/main.py)).
   This covers incomplete keycloak config (missing issuer/audience — ASSUM-002/005)
   **and** an unknown `STUDY_TUTOR_AUTH_MODE` value (ASSUM-007).
2. **Resolver selection:** `table` → `TableTokenResolver` (from the existing
   `STUDY_TUTOR_HTTP_TOKENS` table); `keycloak` → `KeycloakTokenResolver(settings)`.
   Import `auth_keycloak` **lazily inside the keycloak branch** so table-mode boot
   never imports PyJWT and `auth.py` stays keycloak-free (AC-005). Do the selection
   in the boot path (or a small `http` factory) — **never** inside `auth.py`.
3. Build `HTTPAuthConfig` carrying the selected resolver and pass it to
   `create_app(...)` exactly as today. app.py/ws.py are untouched — **WS inherits
   the resolver at upgrade time** (binding §2.1).
4. **Dev-reset pairing:** keep `/__dev__/reset` existence-gated; assert in this
   task's tests that the dev-reset route and keycloak mode never coexist (dev
   flavour stays `table`) — the boot must not mount dev-reset when mode is keycloak.

**Tests** (`tests/unit/http/test_serve_http.py` or a new boot test): table-mode
boot unchanged; keycloak-mode boot with complete config succeeds; missing issuer,
missing audience, and unknown mode each raise `SystemExit`. Pin all env with
monkeypatch (hermetic).

## Acceptance Criteria

- [ ] Boot selects `TableTokenResolver` in `table` mode and `KeycloakTokenResolver` in `keycloak` mode, injecting it via `HTTPAuthConfig.resolver`; `create_app`/app.py/ws.py callsites are unchanged
- [ ] `keycloak` mode with a missing issuer or audience, or an unknown `STUDY_TUTOR_AUTH_MODE`, fails fast with `SystemExit(1)` and a clear message; the server does not begin serving
- [ ] `auth_keycloak`/PyJWT is imported only in the keycloak branch (table-mode boot pulls no JWT import)
- [ ] `/__dev__/reset` is never mounted in keycloak mode (dev-reset and keycloak never coexist)
- [ ] Boot tests are hermetic (env pinned via monkeypatch)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Served

- "Keycloak mode boots when the OIDC configuration is complete"
- "Keycloak mode refuses to start when a required OIDC setting is missing" (issuer / audience)
- "A streaming connection authenticates through the same resolver as the plain routes"
- "The developer reset route and keycloak mode never coexist"

## Seam Tests

Validates the `TOKEN_RESOLVER` integration contract (injection + no callsite change).

```python
"""Seam test: verify TOKEN_RESOLVER contract from TASK-KCA2-002."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("TOKEN_RESOLVER")
def test_token_resolver_injected_without_callsite_change():
    """The selected resolver reaches routes via HTTPAuthConfig.resolver.

    Contract: async resolve(token) -> student_id raising Unauthenticated,
    injected through HTTPAuthConfig so resolve_student_from_token keeps its
    signature (app.py/ws.py unchanged).
    Producer: TASK-KCA2-002
    """
    from study_tutor.http.auth import HTTPAuthConfig, TokenResolver

    config = HTTPAuthConfig.from_env(
        tokens_json='{"token-lilymay": "lilymay"}', dev_reset="false"
    )
    # Table mode default wires a TokenResolver:
    assert isinstance(config.resolver, TokenResolver) or hasattr(config.resolver, "resolve")
```

## References

- design [KC-D6](../../../docs/design/keycloak-auth-user-management-design.md) (env selection, SystemExit fail-fast) · DSN precedent [cli/main.py:869](../../../src/study_tutor/cli/main.py) · [binding §2.1 WS auth](../../../docs/design/contracts/) · IMPLEMENTATION-GUIDE §4 · security-touching (boot auth wiring) ⇒ FULL_REQUIRED human checkpoint
</content>
</invoke>