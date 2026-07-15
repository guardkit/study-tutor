---
id: TASK-KC-005
title: "RUNBOOK-study-tutor-keycloak-standup.md — executable standup runbook with the KC-G1 gate model"
task_type: documentation
parent_review: TASK-REV-KCA1
feature_id: FEAT-AUTH-001
wave: 3
implementation_mode: task-work
complexity: 5
dependencies: [TASK-KC-001, TASK-KC-002, TASK-KC-003, TASK-KC-004]
---

## Description

Author `docs/runbooks/RUNBOOK-study-tutor-keycloak-standup.md` — the executable
operator runbook that ties the committed artifacts (TASK-KC-001…004) into a
gated standup, mirroring the structure and gate discipline of
[RUNBOOK-study-tutor-postgres-deploy.md](../../../docs/runbooks/RUNBOOK-study-tutor-postgres-deploy.md)
(its G0–G7 model becomes **KC-G1** here). Documentation only — the *execution* is
TASK-KC-006 (operator_handoff).

Required sections (mirror the postgres runbook):

1. **Credentials & secrets summary** — reuse the existing NAS SSH key; the env
   surface for `deploy/keycloak/.env` (`KC_DB_PASSWORD`, `KC_BOOTSTRAP_ADMIN_*`,
   `KC_HOSTNAME`, cert paths); "secrets & users never in git" stated explicitly.
2. **Phase 0 — NAS prep (reuse)** — SSH/sudoers/docker already proven; only the
   new `/volume1/docker/study_tutor_keycloak/` dir. Reuse gate G0.
3. **Phase 1 — cert mint** — `tailscale cert whitestocks.tailebf801.ts.net` on the
   NAS; place key/cert where compose mounts them. **Ordered fallbacks (KC-D2):**
   (a) direct mount fails on DSM → front with `tailscale serve` (same issuer
   name); (b) last resort → GB10 placement. Document both, with the same issuer
   string preserved.
4. **Phase 2 — DB + role** — apply `init-keycloak-db.sql` (TASK-KC-003) into
   `study_tutor_postgres`.
5. **Phase 3 — deploy + import** — render `.env`, `compose up -d`, realm imported
   on optimized start via `--import-realm` (TASK-KC-001/002).
6. **Phase 4 — provisioning** — create the prod user **Lilymay** (with `student_id`
   attribute) in the admin console **and** `study-tutor seed-students
   --student-ids <id>`; dev realm additionally gets Alex + the `live-suite` client.
   **Users/secrets never committed.**
7. **Phase 5 — backups** — install the extended `backup.sh` (TASK-KC-004) at
   `/volume1/docker/study_tutor_keycloak/…` and schedule nightly via DSM Task
   Scheduler (root), same as postgres.
8. **Phase 6 — network exposure** — tailnet-only, **no WAN port-forward** for
   8443; Tailscale ACL scopes reach; admin console tailnet-only. Same three-layer
   posture as the 5434 deploy.
9. **Gate KC-G1** (the pass condition, executed in TASK-KC-006): device browser
   reaches the https realm sign-in with no cert warning; discovery doc serves over
   the pinned issuer; NAS RAM recorded before/after with positive headroom.
10. **Idempotency & re-run safety** — a second run no-ops/fails cleanly on
    already-bound resources; realm re-import is non-overwriting so runbook-created
    users survive (ASSUM-003). **Cert renewal** — the ~90-day tailscale cert renews
    unattended; note the check.
11. **"What NOT to do"** — no WAN exposure; no users/secrets in git; no floating
    image tag; never `compose down -v`; don't edit compose on the NAS (repo is
    canonical).

Include a **Decision gates table** (KC-G0 reuse → KC-G1) exactly like the postgres
runbook's.

## Acceptance Criteria

- [ ] `docs/runbooks/RUNBOOK-study-tutor-keycloak-standup.md` exists with all phases 0–6, the KC-G1 gate definition, and a decision-gates table
- [ ] Cert story documents the direct `tailscale cert` mount **and** both ordered fallbacks (`tailscale serve`, GB10), all preserving the pinned issuer name
- [ ] Provisioning phase states users are created in the admin console + `seed-students --student-ids`, and are **never committed**
- [ ] Network section states tailnet-only / no-WAN and admin-console-tailnet-only, mirroring the postgres Phase 5 posture
- [ ] Re-run safety (idempotency, non-overwriting realm import, runbook-user survival) and ~90-day cert renewal are documented
- [ ] A "What NOT to do" section is present; the runbook references the committed artifacts (compose, realm, init SQL, backup.sh)

## BDD Scenarios Served

- "The standup falls back to tailscale serve when the direct certificate mount fails on DSM"
- "The standup gate fails clearly when the certificate path is unavailable"
- "A second concurrent standup run does not corrupt the running realm"
- "The tailscale certificate renews before expiry without a manual re-standup"
- "Re-running the standup re-imports the realm without deleting runbook-created users"

## References

- postgres runbook [RUNBOOK-study-tutor-postgres-deploy.md](../../../docs/runbooks/RUNBOOK-study-tutor-postgres-deploy.md) (the G0–G7 model + Phase 5 network posture this mirrors) · design [KC-D2](../../../docs/design/keycloak-auth-user-management-design.md) (cert + fallbacks) · [ADR-ARCH-028](../../../docs/architecture/decisions/ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md) · design §3 (rollout A1 + gate KC-G1)
