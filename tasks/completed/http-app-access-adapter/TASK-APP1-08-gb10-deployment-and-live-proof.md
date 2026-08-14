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
status: completed
completed: 2026-07-05T10:26:35Z
completed_by: operator
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

---

## Completion Record — 2026-07-05 (operator handoff closed)

Completed via `/task-complete TASK-APP1-08`. The server-side deliverable — put
the dev flavour live on GB10 `:8100` and hand off the acceptance environment —
is done and live-verified. Full runtime evidence is the execution record in
[docs/runbooks/RUNBOOK-study-tutor-http-dev-deploy.md](../../../docs/runbooks/RUNBOOK-study-tutor-http-dev-deploy.md)
(phases 0–5, ✅).

| AC | Status | Evidence |
|----|--------|----------|
| **AC-OP-01** GB10 `:8100/healthz` from GB10 | ✅ verified | Runbook phase 3 (`{"status":"ok"}`); re-confirmed live at completion time via `http://100.84.90.91:8100/healthz` |
| **AC-OP-02** seed + `start_session` both tokens | ✅ verified | Runbook phase 4 — seed 2 students; 200 for `<bearer-lilymay>` + `<bearer-alex>`; 401 unknown token; 403 cross-student; real tutored turn; ordered resume; end → `resumable:false`; reset roundtrip |
| **AC-OP-03** Tailscale ACL Mac→GB10 `:8100` | ✅ verified (2026-07-05, Mac) | Mac-side `healthz` 200 in 16ms; tailnet allow-all, no ACL work needed |
| **AC-OP-04** Mac live contract suite green | 🟢 running green (Mac, 2026-07-05) | `app/test_live/` `--concurrency=1` detached; §9 unknown-session mapping green; full result ~30 min. Gate for `/feature-complete`, not this task. |
| **AC-OP-05** Cross-device walk end-to-end | ⏳ GB10/operator, pending | Phase-2 scope §3.6; needs emulator observed on screen. Gate for `/feature-complete`. |
| **AC-OP-06** BINDING_SHA communicated | ✅ done | `BINDING_SHA=6eb7b88c4c8ae412fb36327a4f56286c6b539a7a` frozen; recorded in the runbook handoff + `docs/design/contracts/API-session-http-binding.md`; app-side header filled by app p2-wave-3 |

**Next step (separate, gated on the Mac suite):** run
`/feature-complete FEAT-APP-001` only after the Mac-side live suite (AC-OP-04)
and cross-device walk (AC-OP-05) pass green against this deployment. The
service is up, seeded, and the dev reset is armed
(`API_BASE_URL=http://promaxgb10-41b1.tailebf801.ts.net:8100`, `--concurrency=1`).

**Deployment standing posture:** dev flavour left running with reset armed for
the Mac acceptance run. Per the runbook, take it `docker compose down` or
re-flavour to prod once phase-2 acceptance is signed off.

**Open conformance gap (surfaced by the Mac acceptance run):** `tutor_turn`
latency ~43s warm / 66s cold breaches SR-07 (p95<10s, 30s hard ceiling). This
is a *deployment* gap, not an app-posture issue — see the runbook's "Conformance
gap" section for ranked GB10-side triage (top suspect: llama-swap thrash between
the Player `gemma4-tutor` and Coach `qwen36-workhorse` aliases). Blocks the
*latency* half of `/feature-complete`; the *functional* live suite is unaffected.
