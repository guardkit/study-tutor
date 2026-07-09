# FEAT-AUTH-002 A2 — Keycloak Server-Side Token Validation

Introduce the `TokenResolver` seam so the study-tutor HTTP/WS server can validate
real Keycloak identity tokens and derive the student from a verified claim —
**without the frozen contract changing** (only the derivation source does). Flag
default stays `table` everywhere, so **merging A2 changes nothing in prod** until
cutover (design §3, gate **KC-G2**).

- **Review:** TASK-REV-KCA2 · **Feature id:** FEAT-AUTH-002 · **Complexity:** 8/10
- **Spec:** [features/keycloak-server-token-validation/](../../../features/keycloak-server-token-validation/) (25 scenarios, 2 smoke, 1 regression)
- **Design:** [keycloak-auth-user-management-design.md](../../../docs/design/keycloak-auth-user-management-design.md) (KC-D6) · [lpa-poc reference](../../../docs/design/references/keycloak-validation-reference-lpa-poc.md)
- **Seam:** [src/study_tutor/http/auth.py](../../../src/study_tutor/http/auth.py) (+ AC-005 tripwire in [test_auth.py](../../../tests/unit/http/test_auth.py))
- **Guide (start here):** [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) — data-flow, sequence, dependency diagrams + §4 contracts

## Tasks

| Task | Type | Wave | Deliverable |
|---|---|---|---|
| [TASK-KCA2-001](./TASK-KCA2-001-oidc-config-and-dep.md) | declarative | 1 | `PyJWT[crypto]` dep + `http/oidc_config.py` (env surface + fail-fast `validate()`) |
| [TASK-KCA2-002](./TASK-KCA2-002-tokenresolver-seam-refactor.md) | refactor | 1 | `TokenResolver` protocol + `TableTokenResolver` in `auth.py` (byte-for-byte table parity) |
| [TASK-KCA2-003](./TASK-KCA2-003-keycloak-token-resolver.md) | feature | 2 | `KeycloakTokenResolver` in new `http/auth_keycloak.py` (PyJWT + PyJWKClient) |
| [TASK-KCA2-004](./TASK-KCA2-004-boot-wiring-mode-select-failfast.md) | feature | 3 | `STUDY_TUTOR_AUTH_MODE` selection + boot fail-fast; resolver threaded via `HTTPAuthConfig` |
| [TASK-KCA2-005](./TASK-KCA2-005-ac005-tripwire-rescope.md) | testing | 4 | AC-005 tripwire re-scope + dev-reset/keycloak coexistence guard |
| [TASK-KCA2-006](./TASK-KCA2-006-live-suite-token-harness.md) | testing | 4 | Live-suite Direct-Access-Grant token harness (skips without live realm) |
| [TASK-KCA2-007](./TASK-KCA2-007-kc-g2-live-gate.md) | **operator_handoff** | 5 | KC-G2 gate: live dev deploy, live-suite green, hermetic green (operator-executed) |

## Operator follow-up tasks: 1

TASK-KCA2-007 is `operator_handoff` — AutoBuild will not attempt it. The KC-G2 gate
(live dev deploy in keycloak mode, live-suite mints real tokens, contract suite
green, hermetic green in table mode, ASSUM-001/007 confirmed) is operator-verified
post-merge via `/task-complete`. See its `## Required operator follow-up` block.

## Execution

- **AutoBuild the code:** `/feature-build FEAT-AUTH-002` runs waves 1–4
  (TASK-KCA2-001…006). The operator_handoff task (007) is short-circuited.
- **Then run the gate:** the operator brings up a dev deploy and passes KC-G2.

## Scope guard

Out of scope (later A-slices): A1 NAS standup / realm-as-code (FEAT-AUTH-001);
A3 app OIDC sign-in (KC-D7); A4 robot device-grant pairing (KC-D4); token
refresh/revocation sophistication (design §4); MCP/stdio surface auth
(ADR-ARCH-008); the frozen HTTP/WS contract itself (§3 / binding §3 unchanged —
only the derivation source changes); parent role/endpoints (KC-D5).
</content>
</invoke>
