# /feature-spec — feat-auth-001-keycloak-standup-on-the-nas-per-design-kc-d1-d — history

Captured automatically by `.claude/hooks/capture_slash_command.py`.


---

## /feature-spec feat-auth-001-keycloak-standup-on-the-nas-per-design-kc-d1-d — 2026-07-08T19:14:37Z

### Prompt

```
/feature-spec "FEAT-AUTH-001 Keycloak standup on the NAS per design KC-D1/D2/D3: study_tutor_keycloak container (quay.io/keycloak/keycloak 26.6.x pinned, start --optimized, 2GB memory limit), keycloak database+role in study_tutor_postgres :5434, realm-as-code import from deploy/keycloak/realm/ (realm study-tutor, clients study-tutor-app/reachy-robot/live-suite per KC-D4, roles student+parent, student_id attribute→claim protocol mapper — users runbook-created, never in git), tailscale cert for whitestocks.tailebf801.ts.net + https issuer, backup.sh second pg_dump line, executable standup runbook with KC-G1 gate incl. NAS RAM before/after" \
  --context docs/design/keycloak-auth-user-management-design.md \
  --context docs/runbooks/RUNBOOK-study-tutor-postgres-deploy.md \
  --context deploy/postgres/backup.sh
```

### Assistant response

I'll execute the `/feature-spec` command's six-phase Propose-Review methodology. Let me start with **Phase 1: Context Gathering** (silent, no interaction).

Stack detected as Python. Let me read the postgres runbook context and examine existing conventions.

Good context. Let me check an existing `.feature` file for local conventions and glance at the new ADR-ARCH-028.
