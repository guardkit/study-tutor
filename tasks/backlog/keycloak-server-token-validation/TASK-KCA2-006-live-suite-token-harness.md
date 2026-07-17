---
id: TASK-KCA2-006
title: "Live contract-suite token harness \u2014 dev-realm live-suite client token\
  \ minting (skips without live realm)"
task_type: testing
parent_review: TASK-REV-KCA2
feature_id: FEAT-AUTH-002
wave: 4
implementation_mode: task-work
complexity: 5
dependencies:
- TASK-KCA2-003
- TASK-KCA2-004
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-AUTH-002
  base_branch: main
  started_at: '2026-07-17T14:37:52.438507'
  last_updated: '2026-07-17T14:52:39.880066'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-07-17T14:37:52.438507'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

## Description

Author the committable half of the KC-G2 gate: a token-minting harness the live
contract suite uses to obtain **real** tokens the supported way — the dev-realm
`live-suite` confidential client via Direct Access Grant (KC-D4) — while the
hermetic suites stay in `table` mode and mint no real tokens. The actual green run
against a live dev deploy is the operator gate (TASK-KCA2-007); this task ships the
code and its skip discipline.

**Deliverables:**

1. `tests/integration/test_keycloak_contract.py` (new) + a `mint_live_suite_token`
   fixture/helper that performs the Direct Access Grant against the `live-suite`
   client for a test student (`lilymay` / `alex`).
2. `@pytest.mark.integration` (and a keycloak marker) so these are **excluded from
   the default hermetic run**; the harness **skips cleanly** (`pytest.skip`) when
   the live-realm env surface (`STUDY_TUTOR_OIDC_ISSUER` + live-suite credentials)
   is absent — never a hard failure in CI.
3. A hermetic unit check of the harness plumbing (URL construction / response
   parsing) that runs without a network, so the code is Coach-verifiable offline.

**Env surface (name it — hermetic-env):** `STUDY_TUTOR_OIDC_ISSUER`,
`STUDY_TUTOR_LIVE_SUITE_CLIENT_ID`, `STUDY_TUTOR_LIVE_SUITE_CLIENT_SECRET`,
`STUDY_TUTOR_LIVE_SUITE_USERS`. All are read only inside the integration-marked
path; the offline plumbing test pins them via monkeypatch.

**Scope guard (invariant, not snapshot):** hermetic suites **must not** mint real
tokens or reach a network — this is a permanent property, not a boundary a later
task fills. `register` this behaviour with the skip marker, don't assert a
transient "not yet wired" state.

## Acceptance Criteria

- [ ] `tests/integration/test_keycloak_contract.py` mints tokens via the dev-realm `live-suite` client (Direct Access Grant) for a test student
- [ ] The integration test is excluded from the default hermetic run and **skips cleanly** when live-realm env is absent (no hard failure)
- [ ] A hermetic plumbing test covers URL/response handling without a network, pinning env via monkeypatch
- [ ] Hermetic suites stay in `table` mode and mint no real tokens

## BDD Scenarios Served

- "The live contract suite mints tokens through the dev-realm live-suite client"

## References

- design [KC-D4](../../../docs/design/keycloak-auth-user-management-design.md) (live-suite client, Direct Access Grant) · [KC-D6](../../../docs/design/keycloak-auth-user-management-design.md) (hermetic suites stay table) · rollout gate KC-G2 (design §3) · IMPLEMENTATION-GUIDE §2
</content>
</invoke>
