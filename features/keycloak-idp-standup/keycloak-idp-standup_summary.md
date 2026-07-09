# Feature Spec Summary: Keycloak IdP Standup on the NAS (FEAT-AUTH-001, A1)

**Stack**: python
**Generated**: 2026-07-08T19:21:55Z
**Scenarios**: 25 total (6 smoke, 0 regression)
**Assumptions**: 9 total (3 high / 4 medium / 2 low confidence)
**Review required**: Yes (2 low-confidence assumptions)

## Scope

Covers the **A1 standup slice** of the Keycloak auth rollout only: bringing the
`study_tutor_keycloak` container up on the NAS (pinned `quay.io/keycloak/keycloak:26.6.x`,
`start --optimized`, 2GB memory limit); creating the co-located `keycloak` database and
role inside `study_tutor_postgres` on `:5434`; importing the realm-as-code from
`deploy/keycloak/realm/` (realm `study-tutor`; clients `study-tutor-app` / `reachy-robot` /
`live-suite`; roles `student` + `parent`; the `student_id` attribute→claim protocol mapper,
with users runbook-created and never in git); minting and mounting the `tailscale cert` for
`whitestocks.tailebf801.ts.net` behind the https issuer; extending `backup.sh` with the
second `pg_dump -d keycloak` line; and passing gate **KC-G1** (device browser reaches the
https realm, discovery doc serves, NAS RAM recorded before/after). Scenarios are written as
verifiable standup outcomes, mirroring the postgres deploy runbook's G0–G7 gate model.

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 6 |
| Boundary conditions (@boundary) | 4 |
| Negative cases (@negative) | 11 |
| Edge cases (@edge-case) | 11 |
| Smoke (@smoke) | 6 |
| Security (@security) | 2 |

_(Tags overlap: several scenarios carry both `@edge-case` and `@negative`, or `@boundary` and `@negative`.)_

## Deferred Items

None deferred. All four core groups (A–D) and all seven edge-expansion scenarios (Group E)
were accepted.

## Out of Scope (later A-slices, not specified here)

- **A2 server** — `TokenResolver` seam, `http/auth_keycloak.py`, env wiring, the JWKS-by-tailnet-IP `extra_hosts` split (KC-D6, gate KC-G2).
- **A3 app** — `KeycloakIdentityProvider`, `flutter_appauth` sign-in UX, token refresh (KC-D7, gate KC-G3).
- **A4 robot** — device-grant pairing + bearer file (KC-D4 `reachy-robot`, gate KC-G4).
- **Parent endpoints/UI** — `parent` role reserved only (KC-D5).

## Open Assumptions (low confidence — verify before freeze)

- **ASSUM-004** — realm import mechanism assumed to be `--import-realm` from `deploy/keycloak/realm/` on the optimized start. Verify against the standup runbook's actual import step.
- **ASSUM-005** — post-standup NAS free-memory headroom assumed at ≥1GB against the 8GB total. KC-G1 requires recording before/after but sets no numeric floor; confirm the acceptance threshold.

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "Keycloak IdP Standup on the NAS (FEAT-AUTH-001, A1)" \
      --context features/keycloak-idp-standup/keycloak-idp-standup_summary.md
