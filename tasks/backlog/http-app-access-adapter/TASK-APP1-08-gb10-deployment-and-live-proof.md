---
id: TASK-APP1-08
title: "GB10 deployment (:8100) + Tailscale ACL + Mac live-suite coordination"
task_type: operator_handoff
feature_id: FEAT-APP-001
wave: 8
implementation_mode: direct
complexity: 2
dependencies: [TASK-APP1-07]
parent_feature_spec: features/http-app-access-adapter/http-app-access-adapter_summary.md
---

## Objective

Put the feature live on the GB10 and hand the Mac side its acceptance
environment. Everything here is live infrastructure + attended verification —
AutoBuild must not attempt it.

## Required operator follow-up

This task is `task_type: operator_handoff` — AutoBuild will not attempt it.
The operator must verify the runtime acceptance criteria below manually, then
mark the task complete via `/task-complete`.

- **AC-OP-01**: The dev flavour (`deploy/http/`) is running on GB10 `:8100`
  against the deployment Postgres; `curl http://<gb10>:8100/healthz` answers
  from the GB10 itself.
- **AC-OP-02**: `study-tutor seed-students` has been run against the
  deployment DB; `start_session` via curl succeeds for BOTH dev tokens.
- **AC-OP-03**: A Tailscale ACL entry lets the Mac/emulator host reach GB10
  `:8100` (and nothing wider); verified with curl from the Mac.
- **AC-OP-04**: The Mac-side live contract suite (`app/test_live/`, built by
  the Mac's p2 waves; may not exist yet when the server work finishes — that
  is expected) runs green against this deployment with `--concurrency=1`.
- **AC-OP-05**: The cross-device walk (phase-2 scope §3.6) passes end-to-end:
  emulator start + 2 turns → curl list/turn/resume as the same student →
  emulator Resume shows all six messages in order → End on emulator → curl
  `session_status` shows `ended`, `resumable: false`.
- **AC-OP-06**: `BINDING_SHA` (the commit that froze
  `docs/design/contracts/API-session-http-binding.md`) is communicated to the
  Mac side / recorded in the app build plan.

Coordinate with Rich before calling the feature complete — the app suite is
the acceptance test.
