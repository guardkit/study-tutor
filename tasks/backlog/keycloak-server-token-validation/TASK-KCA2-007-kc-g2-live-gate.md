---
id: TASK-KCA2-007
title: "KC-G2 gate — live dev deploy in keycloak mode, live-suite mints real tokens, contract suite green"
task_type: operator_handoff
parent_review: TASK-REV-KCA2
feature_id: FEAT-AUTH-002
wave: 5
implementation_mode: task-work
complexity: 5
dependencies:
- TASK-KCA2-006
---

## Description

The KC-G2 rollout gate (design §3, step A2). This is `task_type: operator_handoff`
— **AutoBuild will not attempt it.** It observes real-world runtime behaviour
(a live dev Keycloak deploy, real minted tokens, wall-clock validation) that the
Player ↔ Coach loop cannot satisfy by construction. The operator runs it post-merge
and verifies the criteria below, then marks the task complete via `/task-complete`.

It also closes the two low-confidence assumptions the spec flagged for
confirmation against the real resolver: **ASSUM-001** (60s leeway on `exp`/`nbf`,
and whether `nbf` is enforced) and **ASSUM-007** (unknown `STUDY_TUTOR_AUTH_MODE`
fails fast) — Coach/operator confirm both against `KeycloakTokenResolver` before
freeze.

## Required operator follow-up

This task is `task_type: operator_handoff` — AutoBuild will not attempt it. The
operator must verify the runtime acceptance criteria below manually, then mark the
task complete via `/task-complete`.

- **AC-G2-01**: A dev Keycloak deploy (FEAT-AUTH-001 A1 realm) is brought up and
  the study-tutor HTTP server runs in `keycloak` mode against it (issuer pinned to
  the ts.net name; JWKS fetched via the tailnet-IP override per KC-D2).
- **AC-G2-02**: The live contract suite (TASK-KCA2-006) mints real tokens via the
  dev-realm `live-suite` client and runs **green** end-to-end against the
  keycloak-mode server for a seeded student (`lilymay`).
- **AC-G2-03**: The hermetic test suite runs **green** in `table` mode on the same
  build — merging A2 changes nothing for the default (table) path.
- **AC-G2-04**: ASSUM-001 confirmed against the real resolver — a token within the
  60s skew is accepted and one just outside is refused; `nbf` behaviour matches the
  documented leeway.
- **AC-G2-05**: ASSUM-007 confirmed — an unknown `STUDY_TUTOR_AUTH_MODE` value
  fails fast at boot (`SystemExit`), not a silent fallback.

## References

- design §3 rollout gate KC-G2 · [KC-D6](../../../docs/design/keycloak-auth-user-management-design.md) · assumptions ASSUM-001 / ASSUM-007 · precedent: FEAT-AUTH-001 TASK-KC-006 (operator_handoff live gate)
</content>
</invoke>
