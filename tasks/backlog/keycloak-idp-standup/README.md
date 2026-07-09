# FEAT-AUTH-001 A1 — Keycloak IdP Standup on the NAS

Bring `study_tutor_keycloak` up on the NAS with realm-as-code, tailnet TLS, a
co-located `keycloak` DB, and backups — passing gate **KC-G1**. A1 standup slice
only; auth is **not** switched on anywhere in this slice (server stays `table`
mode until A2).

- **Review:** TASK-REV-KCA1 · **Feature id:** FEAT-AUTH-001 · **Complexity:** 6/10
- **Spec:** [features/keycloak-idp-standup/](../../../features/keycloak-idp-standup/) (25 scenarios, 6 smoke)
- **Design:** [keycloak-auth-user-management-design.md](../../../docs/design/keycloak-auth-user-management-design.md) (KC-D1…D7)
- **ADR:** [ADR-ARCH-028](../../../docs/architecture/decisions/ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md)
- **Guide (start here):** [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) — data-flow, sequence, dependency diagrams + §4 contracts

## Tasks

| Task | Type | Wave | Deliverable |
|---|---|---|---|
| [TASK-KC-001](./TASK-KC-001-keycloak-compose-and-env.md) | scaffolding | 1 | `deploy/keycloak/` compose + pinned optimized build + `.env.deploy.example` |
| [TASK-KC-002](./TASK-KC-002-realm-as-code.md) | declarative | 1 | `deploy/keycloak/realm/study-tutor-realm.json` (no users/secrets/live-suite) |
| [TASK-KC-003](./TASK-KC-003-keycloak-db-and-role.md) | feature | 1 | `keycloak` DB + least-privilege role bootstrap |
| [TASK-KC-004](./TASK-KC-004-backup-keycloak-dump.md) | feature | 2 | `backup.sh` second `pg_dump -d keycloak` (fails if either dump fails) |
| [TASK-KC-005](./TASK-KC-005-standup-runbook.md) | documentation | 3 | `RUNBOOK-study-tutor-keycloak-standup.md` (KC-G1 gate model) |
| [TASK-KC-006](./TASK-KC-006-live-standup-kc-g1-gate.md) | **operator_handoff** | 4 | Live NAS standup + KC-G1 gate (operator-executed) |

## Operator follow-up tasks: 1

TASK-KC-006 is `operator_handoff` — AutoBuild will not attempt it. The live NAS
standup and KC-G1 gate (device browser reaches https realm, RAM before/after,
tailnet-only, user creation never in git) are operator-verified post-merge via
`/task-complete`. See its `## Required operator follow-up` block.

## Execution

- **AutoBuild the artifacts:** `/feature-build FEAT-AUTH-001` runs waves 1–3
  (TASK-KC-001…005). The operator_handoff task (006) is short-circuited.
- **Then execute the standup:** the operator runs the runbook and passes KC-G1.

## Scope guard

Out of scope (later A-slices): A2 server `TokenResolver`/`auth_keycloak.py` + the
`extra_hosts` JWKS split (KC-G2); A3 app OIDC sign-in (KC-G3); A4 robot
device-grant pairing (KC-G4); parent endpoints (KC-D5 — role reserved only).
