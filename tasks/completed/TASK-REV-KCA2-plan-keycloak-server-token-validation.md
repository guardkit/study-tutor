---
id: TASK-REV-KCA2
title: "Plan: Keycloak Server-Side Token Validation (FEAT-AUTH-002, A2)"
task_type: review
status: review_complete
priority: high
feature_id: FEAT-AUTH-002
decision: implement
clarification:
  context_a:
    decisions:
      focus: security_quality
      tradeoff: quality
  context_b:
    decisions:
      approach: option_1_resolver_on_authconfig
      execution: detect_waves
      testing: standard
      live_gate: operator_handoff
---

## Plan: Keycloak Server-Side Token Validation (FEAT-AUTH-002, A2)

Decision review for the A2 server slice. **Decision: [I]mplement** — generated
`.guardkit/features/FEAT-AUTH-002.yaml` + 7 tasks under
[tasks/backlog/keycloak-server-token-validation/](../backlog/keycloak-server-token-validation/).

**Context:** [feature spec](../../features/keycloak-server-token-validation/keycloak-server-token-validation_summary.md)
(25 scenarios, 2 smoke, 1 regression) · [design KC-D6](../../docs/design/keycloak-auth-user-management-design.md)
· [lpa-poc reference](../../docs/design/references/keycloak-validation-reference-lpa-poc.md)
· [auth.py seam](../../src/study_tutor/http/auth.py).

**Recommended approach chosen:** Option 1 — the selected `TokenResolver` is carried
on `HTTPAuthConfig`, so `resolve_student_from_token(header, config, store)` keeps its
signature and the [app.py](../../src/study_tutor/http/app.py) / [ws.py](../../src/study_tutor/http/ws.py)
callsites are untouched (the frozen HTTP/WS contract does not change — only the
derivation source does). `auth.py` stays JWT-free forever; all PyJWT/Keycloak
imports live in the new sibling `http/auth_keycloak.py`.

**Task breakdown:** 6 autobuild-suitable tasks (OIDC config + dep, resolver-seam
refactor, KeycloakTokenResolver, boot wiring + fail-fast, AC-005 tripwire re-scope,
live-suite token harness) + 1 `operator_handoff` KC-G2 live gate. Waves 1–5.
§4 integration contracts: `OIDC_SETTINGS`, `TOKEN_RESOLVER`. This slice **wires the
JWKS read path A1 deliberately left `NOT WIRED`** — no disconnected paths remain.

**Full analysis:** see [IMPLEMENTATION-GUIDE.md](../backlog/keycloak-server-token-validation/IMPLEMENTATION-GUIDE.md).
</content>
</invoke>
