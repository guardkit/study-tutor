---
complexity: 3
dependencies:
- TASK-KCA2-003
- TASK-KCA2-004
feature_id: FEAT-AUTH-002
id: TASK-KCA2-005
implementation_mode: task-work
parent_review: TASK-REV-KCA2
status: design_approved
task_type: testing
title: AC-005 tripwire re-scope + dev-reset/keycloak coexistence guard
wave: 4
---

## Description

Re-scope the AC-005 import tripwire so it now spans **both** auth modules, and
lock the dev-reset/keycloak-exclusion invariant with a test. Design ref KC-D6
("the AC-005 tripwire is kept and re-scoped: `auth.py` stays JWT-free forever,
the imports live only in `auth_keycloak.py`").

**Deliverables (tests only):**

1. **Keep** `tests/unit/http/test_auth.py::test_no_keycloak_jwt_imports` green:
   `auth.py` has none of `jwt` / `JWT` / `keycloak` / `Keycloak` / `jose`.
2. **Add the positive half:** assert `auth_keycloak.py` **does** import the JWT
   stack (e.g. `jwt` and `PyJWKClient` are referenced) — the imports must live
   *somewhere*, and that somewhere is the sibling module, not `auth.py`.
3. **Dev-reset coexistence guard:** a test asserting `/__dev__/reset` is never
   mounted when the server is composed in keycloak mode (dev flavour stays
   `table`; the route and keycloak validation never coexist).

**Invariant, not snapshot:** these assertions pin **permanent** boundaries of the
whole feature — `auth.py` is JWT-free *forever*, and dev-reset never coexists with
keycloak *by design*. No later task in this feature fills or flips them, so they
are safe standing assertions (not transient boundary tests that a later wave turns
red).

## Acceptance Criteria

- [ ] `test_no_keycloak_jwt_imports` still passes for `auth.py` (no jwt/keycloak/jose)
- [ ] A test asserts the JWT/JWKS imports **are present** in `auth_keycloak.py`
- [ ] A test asserts `/__dev__/reset` is not mounted in keycloak mode
- [ ] The new tests are hermetic (no live realm, no network)

## BDD Scenarios Served

- "The base auth module stays free of JWT and Keycloak imports" (@regression)
- "The developer reset route and keycloak mode never coexist"

## References

- design [KC-D6](../../../docs/design/keycloak-auth-user-management-design.md) (AC-005 re-scope) · existing tripwire [test_auth.py](../../../tests/unit/http/test_auth.py) · IMPLEMENTATION-GUIDE §1 (import boundary)
</content>
</invoke>