---
id: TASK-KC-006
title: "Live NAS standup + KC-G1 gate (operator-executed)"
task_type: operator_handoff
parent_review: TASK-REV-KCA1
feature_id: FEAT-AUTH-001
wave: 4
implementation_mode: direct
complexity: 5
dependencies: [TASK-KC-005]
---

## Description

Execute the runbook (TASK-KC-005) on **whitestocks** and pass gate **KC-G1**. This
task is `task_type: operator_handoff` — AutoBuild will **not** attempt it: every
acceptance criterion here is `observed_at_runtime(real_world)` (live NAS state, a
household device browser, wall-clock RAM readings, a ~90-day cert lifecycle), which
the Player ↔ Coach loop cannot satisfy by construction. The operator runs it and
records evidence, then marks it complete via `/task-complete`.

Execution outline (detail in the runbook): mint the `tailscale cert`; apply
`init-keycloak-db.sql`; render `.env` and `compose up -d`; realm imports on start;
create the prod user Lilymay (admin console + `seed-students --student-ids`) — **never
committed**; record NAS free RAM before and after; then run the KC-G1 checks below
from a real device.

## Required operator follow-up

This task is `task_type: operator_handoff` — AutoBuild will not attempt it. The
operator must verify the runtime acceptance criteria below manually (recording
evidence in the runbook), then mark the task complete via `/task-complete`.

- **AC-G1-01**: A household device browser opens the study-tutor realm sign-in page over the tailnet and it loads over a **trusted https** connection with **no certificate warning**.
- **AC-G1-02**: The realm **discovery document** is served over the tailnet https issuer, and its advertised `issuer` matches the pinned `https://whitestocks.tailebf801.ts.net:8443/realms/study-tutor`.
- **AC-G1-03**: NAS **free memory is recorded before and after** standup; both readings are captured in the runbook evidence and the after-reading leaves **positive headroom** against the 8 GB total (ASSUM-005 — confirm the acceptance threshold against the runbook).
- **AC-G1-04**: The identity service **is not reachable from the public internet** (connection from outside the tailnet fails) and no WAN port-forward at the edge gateway routes to 8443.
- **AC-G1-05**: The **admin console is tailnet-only** (probe from outside the tailnet is unreachable) and no admin credential is present in any committed file.
- **AC-G1-06**: The realm was imported via `--import-realm` and shows the expected clients/roles/mapper; the runbook-created user Lilymay exists and is **not** in git.
- **AC-G1-07** (deferred verification, note only): the ~90-day tailscale cert renews unattended before expiry — record the expiry date and the renewal-check method; no re-standup required.

## BDD Scenarios Served

- "A household device browser reaches the realm sign-in page over https"
- "The realm discovery document is served over the tailnet https issuer"
- "NAS memory is recorded before and after standup and headroom stays positive"
- "The identity service is not reachable from the public internet"
- "The admin bootstrap credential is never committed and the admin console is tailnet-only"

## References

- design §3 (A1 rollout + **gate KC-G1**) · [ADR-ARCH-028](../../../docs/architecture/decisions/ADR-ARCH-028-keycloak-idp-nas-placement-tailnet-tls.md) (residual risk: DSM cert path) · runbook TASK-KC-005 · ASSUM-005 (RAM headroom threshold — confirm at gate)
