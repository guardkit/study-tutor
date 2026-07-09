---
id: TASK-REV-KCA1
title: "Plan: Keycloak IdP Standup on the NAS (FEAT-AUTH-001, A1)"
task_type: review
status: review_complete
priority: high
feature_id: FEAT-AUTH-001
decision: implement
clarification:
  context_a:
    decisions:
      focus: security_quality
      tradeoff: quality
  context_b:
    decisions:
      approach: option_1_prod_safe_realm_base
      execution: detect_waves
      testing: standard
      live_standup: operator_handoff
---

## Plan: Keycloak IdP Standup on the NAS (FEAT-AUTH-001, A1)

Decision review for the A1 standup slice. **Decision: [I]mplement** — generated
`.guardkit/features/FEAT-AUTH-001.yaml` + 6 tasks under
[tasks/backlog/keycloak-idp-standup/](../backlog/keycloak-idp-standup/).

**Context:** [feature spec](../../features/keycloak-idp-standup/keycloak-idp-standup_summary.md)
(25 scenarios, 6 smoke) · [design KC-D1…D7](../../docs/design/keycloak-auth-user-management-design.md)
· [ADR-ARCH-028](../../docs/architecture/decisions/ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md)
· [lpa-poc reference](../../docs/design/references/keycloak-validation-reference-lpa-poc.md).

**Recommended approach chosen:** Option 1 — prod-safe realm base (no
users/secrets/live-suite committed; dev additions runbook-created), mirroring the
[postgres deploy runbook](../../docs/runbooks/RUNBOOK-study-tutor-postgres-deploy.md)
G0–G7 gate model as KC-G1.

**Task breakdown:** 5 autobuild-suitable artifact tasks (compose, realm-as-code,
keycloak DB/role, backup.sh extension, standup runbook) + 1 `operator_handoff`
live-standup + KC-G1 gate task. Waves 1–4. §4 integration contracts: KEYCLOAK_DB,
REALM_IMPORT.

**Full analysis:** see [IMPLEMENTATION-GUIDE.md](../backlog/keycloak-idp-standup/IMPLEMENTATION-GUIDE.md).
