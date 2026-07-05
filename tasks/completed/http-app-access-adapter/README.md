# FEAT-APP-001 — HTTP App Access Adapter

Six contract §5 verbs as plain JSON endpoints on `:8100`, a second consumer of
the proven `SessionService`. Publishes the frozen HTTP binding table in wave 1
(the Mac-side Flutter build is blocked on it), interim token-table auth, a
dev-only reset, the student-identity seed (closes the `session.student_id` FK
gap), `serve-http` + `deploy/http/` compose, READY boot smoke.

**Sequencing:** BEFORE FEAT-SMP-004. **Never touch:** `app/**`, the pinned
cross-device contract.

| Wave | Task | What |
|---|---|---|
| 1 | TASK-APP1-01 | Binding table doc — **push after merge = Mac unblock** |
| 2 | TASK-APP1-02 | Token-table auth + env config |
| 3 | TASK-APP1-03 | Six JSON endpoints + §9 envelope (+ starlette/uvicorn pins) |
| 4 | TASK-APP1-04 | `serve-http` CLI + store/tutor-loop/events wiring + READY smoke |
| 5 | TASK-APP1-05 | `seed-students` CLI + `POST /__dev__/reset` |
| 6 | TASK-APP1-06 | `deploy/http/` compose (dev/prod flavours) |
| 7 | TASK-APP1-07 | BDD steps + binding conformance + MCP-freeze + full-suite gate |
| 8 | TASK-APP1-08 | **Operator:** GB10 deploy, Tailscale ACL, Mac live suite (skipped by AutoBuild) |

Spec: `features/http-app-access-adapter/` · Guide: `IMPLEMENTATION-GUIDE.md` ·
Feature YAML: `.guardkit/features/FEAT-APP-001.yaml`

Launch: `GUARDKIT_HARNESS=sdk guardkit autobuild feature FEAT-APP-001 --fresh`
(ephemeral `STUDY_TUTOR_PG_DSN` exported; see the guide's retro constraints).
