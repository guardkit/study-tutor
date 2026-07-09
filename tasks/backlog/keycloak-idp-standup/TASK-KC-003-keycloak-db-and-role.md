---
id: TASK-KC-003
title: "Co-located keycloak DB + least-privilege role bootstrap in study_tutor_postgres"
task_type: feature
parent_review: TASK-REV-KCA1
feature_id: FEAT-AUTH-001
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
---

## Description

Produce the committed, idempotent bootstrap that creates the `keycloak` database
and role **inside the existing `study_tutor_postgres` container** on `:5434`
(design KC-D1: the D4 rule separates *projects*, not a project's own services;
Postgres 16 is in Keycloak 26.6's supported range). This is the **producer** of
the §4 KEYCLOAK_DB contract (consumed by TASK-KC-001 and TASK-KC-004).

Deliverable `deploy/keycloak/init-keycloak-db.sql` (plus a short idempotent apply
snippet the runbook invokes via `docker exec ... psql`):

- **Role** `keycloak` — a **distinct, non-superuser** login role with its own
  password (from env; never committed), `NOSUPERUSER NOCREATEDB NOCREATEROLE`.
- **Database** `keycloak` — `OWNER keycloak`, separate from `study_tutor`.
- **Least-privilege isolation (the load-bearing security AC):** the `keycloak`
  role must **not** be able to read the `study_tutor` learner tables. Because both
  DBs live in one cluster, explicitly ensure `keycloak` has no grants into the
  `study_tutor` database (it is not a superuser and is not granted CONNECT/USAGE
  there) — and, symmetrically, `study_tutor` is not granted into `keycloak`.
  Include the negative-proof query the runbook/gate runs (a `keycloak`-role
  connection attempting to `SELECT` a `study_tutor` table is denied).
- **Idempotent**: guarded `CREATE ROLE`/`CREATE DATABASE` (checks against
  `pg_roles`/`pg_database`) so re-running the standup is safe.

**Env-var surface**: `KC_DB_PASSWORD` (the `keycloak` role password), applied by
the runbook — the SQL takes it as a psql variable, it is never hard-coded.

**Out of scope (name negatively):** this task does **not** create any realm state,
Keycloak tables, or users — Keycloak creates its own schema in the `keycloak` DB on
first optimized start; this task stands up an **empty DB + role** only (exactly the
posture the postgres runbook takes for `study_tutor`).

## Acceptance Criteria

- [ ] `deploy/keycloak/init-keycloak-db.sql` creates role `keycloak` (login, **non-superuser**, NOCREATEDB/NOCREATEROLE) and database `keycloak` owned by it
- [ ] Creation is idempotent (guarded against `pg_roles`/`pg_database`) — a second apply is a clean no-op
- [ ] The role password is taken from a psql variable / env, never hard-coded or committed
- [ ] The script includes/《documents》 the least-privilege proof: the `keycloak` role is denied `SELECT` on `study_tutor` learner tables and can reach only its own `keycloak` database
- [ ] The DB name and role name match the §4 KEYCLOAK_DB contract exactly (`keycloak` / `keycloak`)
- [ ] All modified files pass project-configured lint/format checks with zero errors

## BDD Scenarios Served

- "The keycloak database and role are created in the existing Postgres container"
- "The keycloak database role cannot read the learner tables"

## References

- design [KC-D1](../../../docs/design/keycloak-auth-user-management-design.md) (co-located keycloak DB + role) · [ADR-ARCH-028](../../../docs/architecture/decisions/ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md) D1 · postgres runbook [Phase 2/3](../../../docs/runbooks/RUNBOOK-study-tutor-postgres-deploy.md) (empty-DB-and-role posture) · IMPLEMENTATION-GUIDE §4 (KEYCLOAK_DB producer) · security-touching (DB role least-privilege) ⇒ FULL_REQUIRED human checkpoint
