---
complexity: 6
dependencies: []
feature_id: FEAT-AUTH-001
id: TASK-KC-002
implementation_mode: task-work
parent_review: TASK-REV-KCA1
status: design_approved
task_type: declarative
title: Realm-as-code — deploy/keycloak/realm/study-tutor-realm.json (clients, roles,
  student_id mapper; no users, no secrets, no live-suite in prod)
wave: 1
---

## Description

Author the committed realm-as-code that Keycloak imports on optimized start
(§4 REALM_IMPORT contract; consumed by TASK-KC-001). Per design KC-D3/D4 and the
lpa-poc reference
([keycloak-validation-reference-lpa-poc.md](../../../docs/design/references/keycloak-validation-reference-lpa-poc.md)
§3), this is the **prod-safe base** realm — reproducible config, **zero PII**.

`deploy/keycloak/realm/study-tutor-realm.json` contains:

- **Realm** `study-tutor`. Realm `id` and all client `id` fields **pinned** to
  fixed values (the lpa-poc "pinned id prevents sub-drift across down/up" rule),
  so re-import is stable. `sslRequired` set so the realm is https-only (a
  plain-http issuer must be rejected — see the negative scenario).
- **Clients (prod-safe set):**
  - `study-tutor-app` — **public**, Authorization Code + **PKCE S256 enforced**,
    custom-scheme redirect URI, `scope=offline_access` (KC-D4).
  - `reachy-robot` — **public**, OAuth 2.0 **Device Authorization Grant** enabled
    (KC-D4; robot acts *as the student* for D8 same-subject pickup).
  - **`live-suite` is deliberately ABSENT** from this committed prod realm. It is
    a confidential, direct-access **dev-realm-only** test client, created at dev
    standup by the runbook (TASK-KC-005) — never committed (a confidential client
    carries a secret; secrets never enter git).
- **Realm roles** `student` and `parent` both created now (cheap, schema-stable);
  only `student` is used by the API this phase (KC-D5 — parent reserved, no parent
  user/endpoints).
- **Protocol mapper**: the `student_id` **user attribute → `student_id` token
  claim** mapper (KC-D3; claim name `student_id` per KC-D6 default), added to the
  `study-tutor-app` (and `reachy-robot`) client/scope so validated tokens carry it.

**Invariants of the WHOLE feature (permanent, safe to assert):** no `users` array,
no client `secret` value, and no `live-suite` client in this committed prod realm.
These are not transient boundaries a later task fills — users and the dev-only
live-suite client are *runbook-created and never committed*, by design, forever.

## Acceptance Criteria

- [ ] `deploy/keycloak/realm/study-tutor-realm.json` defines realm `study-tutor` with pinned realm/client `id` fields and https-only `sslRequired`
- [ ] Clients `study-tutor-app` (public, PKCE S256 enforced, offline_access) and `reachy-robot` (public, device-grant enabled) are present with correct flows
- [ ] Realm roles `student` and `parent` both exist
- [ ] A `student_id` user-attribute → `student_id` claim protocol mapper is defined and attached so tokens can carry the claim
- [ ] The committed file contains **no** `users`, **no** client `secret`, and **no** `live-suite` client (grep-verifiable negatives)
- [ ] The realm JSON is valid JSON and passes project-configured lint/format checks with zero errors

## BDD Scenarios Served

- "The realm is provisioned from code with the expected clients, roles, and claim mapper"
- "The committed realm-as-code contains no users and no client secrets"
- "The production realm does not contain the test-only live-suite client"
- "A plain-http issuer is not accepted as the realm issuer"

## References

- design [KC-D3/D4/D5/D6](../../../docs/design/keycloak-auth-user-management-design.md) · lpa-poc reference §2 (deliberate divergences: users NOT in git; `student_id` attribute not a column) + §3 (attribute→claim mapper, pinned ids) · IMPLEMENTATION-GUIDE §4 (REALM_IMPORT) · security-touching (identity realm) ⇒ FULL_REQUIRED human checkpoint