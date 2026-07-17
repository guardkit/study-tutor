---
complexity: 4
dependencies: []
feature_id: FEAT-AUTH-002
id: TASK-KCA2-001
implementation_mode: task-work
parent_review: TASK-REV-KCA2
status: design_approved
task_type: declarative
title: OIDC settings + PyJWT[crypto] dependency — http/oidc_config.py env surface
  + fail-fast validation
wave: 1
---

## Description

Foundation for keycloak mode: add the OIDC validation dependency and a frozen
settings object that carries the OIDC configuration and knows when it is
incomplete. Producer of the **§4 `OIDC_SETTINGS`** contract (consumed by
TASK-KCA2-003 and TASK-KCA2-004). Design ref: KC-D6.

**Deliverables:**

1. **Dependency:** add `PyJWT[crypto]>=2.8` to `pyproject.toml` (`[project]`
   dependencies). The `[crypto]` extra pulls `cryptography` for RS256 / JWKS
   asymmetric verification. This is a deliberate zero-deps-scope event (same
   pattern as the voice track) — record it in the task notes.
2. **`src/study_tutor/http/oidc_config.py`** — a frozen `OIDCSettings` dataclass
   with `from_env(...)` and a `validate() -> list[str]` (returns the list of
   missing/invalid-setting messages; **empty list == valid**). The caller
   (TASK-KCA2-004) turns a non-empty list into a boot `SystemExit`. This module
   is pure config — **no PyJWT import here** (the resolver owns that).

**Full env-var surface (name every var the deliverable reads — hermetic-env):**

| Env var | Meaning | Default |
|---|---|---|
| `STUDY_TUTOR_AUTH_MODE` | `table` \| `keycloak` (any other value is invalid) | `table` when unset (ASSUM-003) |
| `STUDY_TUTOR_OIDC_ISSUER` | ts.net https issuer; must equal token `iss` | **required** in keycloak mode (ASSUM-002) |
| `STUDY_TUTOR_OIDC_AUDIENCE` | expected token `aud` | **required** in keycloak mode (ASSUM-002) |
| `STUDY_TUTOR_OIDC_JWKS_URL` | JWKS fetch override (tailnet-IP form, KC-D2 gotcha) | optional; derived from issuer when absent |
| `STUDY_TUTOR_OIDC_STUDENT_CLAIM` | claim carrying the student id | `student_id` (ASSUM-004) |
| `STUDY_TUTOR_OIDC_LEEWAY` | clock-skew leeway (s) on `exp`/`nbf` | `60` (ASSUM-001) |

Every test that exercises `from_env`/`validate` MUST pin the surface with
`monkeypatch.setenv`/`delenv` — no test may read the ambient environment.

## Acceptance Criteria

- [ ] `PyJWT[crypto]>=2.8` is declared in `pyproject.toml`
- [ ] `OIDCSettings.from_env` parses the full env surface above with the documented defaults (mode defaults to `table`; student-claim to `student_id`; leeway to `60`)
- [ ] `validate()` returns messages for keycloak mode with a missing **issuer** and/or **audience**, and for an **unknown** `STUDY_TUTOR_AUTH_MODE` value (ASSUM-002/005/007); returns `[]` when config is complete
- [ ] When `STUDY_TUTOR_OIDC_JWKS_URL` is absent, the effective JWKS URL is derived from the issuer; when present, it overrides fetch **without** changing the issuer used for `iss` validation (KC-D2)
- [ ] All tests are hermetic (env pinned via monkeypatch), never reading ambient config
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Served

- "Keycloak mode boots when the OIDC configuration is complete"
- "Keycloak mode refuses to start when a required OIDC setting is missing" (issuer / audience)

## References

- design [KC-D6](../../../docs/design/keycloak-auth-user-management-design.md) (env selection + fail-fast) · assumptions ASSUM-001..007 · IMPLEMENTATION-GUIDE §4 (`OIDC_SETTINGS`) · DSN fail-fast precedent [cli/main.py:869](../../../src/study_tutor/cli/main.py)
</content>
</invoke>