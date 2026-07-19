---
id: TASK-KCA3-007
title: "KC-G3 gate — live end-to-end sign-in on a real device against the A2 dev deploy (>5-min idle survives, restart stays signed in)"
task_type: operator_handoff
parent_review: TASK-REV-KCA3
feature_id: FEAT-AUTH-003
wave: 6
implementation_mode: task-work
complexity: 5
dependencies:
- TASK-KCA3-006
status: completed
completed: '2026-07-19T14:05:53.704879Z'
completed_location: tasks/completed/2026-07
updated: '2026-07-19T14:05:53.704879Z'
---

## Description

The KC-G3 rollout gate (design §3, step A3). This is `task_type: operator_handoff`
— **AutoBuild will not attempt it.** It observes real-world runtime behaviour — a
real device, a live browser OIDC flow against a live Keycloak dev deploy, and a
**wall-clock idle longer than the access-token lifetime** — that the Player ↔
Coach loop cannot satisfy by construction. The operator runs it post-merge and
verifies the criteria below, then marks the task complete via `/task-complete`.

A3 depends on the **A2 dev deploy running in `keycloak` mode** (FEAT-AUTH-002) and
the **A1 realm** (FEAT-AUTH-001) providing the `study-tutor-app` client. This gate
also closes the two lower-confidence assumptions the spec flagged: **ASSUM-002**
(the access-token lifetime is ~5 minutes, so a >5-min idle actually exercises a
refresh) and **ASSUM-003** (the `com.appmilla.studytutor:/oauth2redirect` redirect
round-trips on the real Keycloak client + a real device).

## Required operator follow-up

This task is `task_type: operator_handoff` — AutoBuild will not attempt it. The
operator must verify the runtime acceptance criteria below manually, then mark the
task complete via `/task-complete`.

- **AC-G3-01**: On a real device, a first-time sign-in through the external
  browser completes via the custom-scheme redirect and lands on the home screen,
  against the A2 dev deploy in `keycloak` mode (A1 realm, `study-tutor-app`
  client).
- **AC-G3-02**: After closing and reopening the app, the device is **still signed
  in with no browser prompt** (the persisted `offline_access` session refreshes
  silently).
- **AC-G3-03**: An **active session survives an idle longer than the access-token
  lifetime** (>5 min, ASSUM-002) — continuing the session does not prompt a
  re-sign-in; the proactive background refresh kept the token fresh (KC-G3).
- **AC-G3-04**: The sign-out affordance clears the session; the app returns to the
  sign-in screen and a fresh sign-in is required (browser or silent, per the
  stored-session state).
- **AC-G3-05**: ASSUM-003 confirmed against reality — the redirect URI
  `com.appmilla.studytutor:/oauth2redirect` is byte-identical on the Keycloak
  `study-tutor-app` client, the Android manifest scheme, and the iOS
  `CFBundleURLSchemes`, and the browser redirect returns to the app on the real
  device.
- **AC-G3-06**: The hermetic-fake flavour build is still green (no browser, no
  network) on the same commit — the real wiring did not disturb the fake path.

## References

- design §3 rollout gate KC-G3 · [KC-D7 / KC-D4](../../../docs/design/keycloak-auth-user-management-design.md) · assumptions [ASSUM-002 / ASSUM-003](../../../features/flutter-keycloak-sign-in/flutter-keycloak-sign-in_assumptions.yaml) · depends on the A2 dev deploy (FEAT-AUTH-002) + A1 realm (FEAT-AUTH-001) · precedent: FEAT-AUTH-002 TASK-KCA2-007 (operator_handoff live gate)
