---
id: TASK-APP1-06
title: deploy/http/ compose (dev + prod flavours) + .env.example entries
task_type: scaffolding
feature_id: FEAT-APP-001
wave: 6
implementation_mode: task-work
complexity: 3
dependencies:
- TASK-APP1-05
parent_feature_spec: features/http-app-access-adapter/http-app-access-adapter_summary.md
consumer_context:
- task: TASK-APP1-02
  consumes: STUDY_TUTOR_HTTP_TOKENS
  framework: docker compose environment blocks
  driver: env var (JSON object)
  format_note: 'JSON object mapping token to student_id, e.g. {"token-lilymay": "lilymay",
    "token-alex": "alex"}; dev flavour carries two entries + STUDY_TUTOR_HTTP_DEV_RESET=1,
    prod carries one entry and no reset flag'
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-APP-001
  base_branch: main
  started_at: '2026-07-05T09:57:59.593419'
  last_updated: '2026-07-05T10:11:24.288035'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-07-05T09:57:59.593419'
    player_summary: 'Implementation via task-work delegation. Files planned: 0, Files
      actual: 0'
    player_success: true
    coach_success: true
---

## Objective

A deployment slot for the HTTP service that is independent of the root
`docker-compose.study-tutor.yml` (which hard-requires `NATS_PASSWORD` — the
HTTP service must NOT inherit that coupling, per ADR-ARCH-023's
independent-deployability posture).

## Scope

**In scope**
- `deploy/http/docker-compose.yml` (+ a short README): builds/runs
  `study-tutor serve-http` on port **8100**; healthcheck hits `GET /healthz`
  (READY semantics from TASK-APP1-04); documents `study-tutor seed-students`
  as the init step.
- **Dev flavour** env: two tokens + `STUDY_TUTOR_HTTP_DEV_RESET=1`.
  **Prod flavour** env: single lilymay token, no reset flag. Token values per
  the binding doc's dev section; DSN from the deployment `.env`.
- `.env.example`: add `STUDY_TUTOR_HTTP_TOKENS` + `STUDY_TUTOR_HTTP_DEV_RESET`
  with comments (values as placeholders, real tokens per binding doc).

**Out of scope**
- The root compose file (outside this feature's blast radius); Tailscale ACL
  (operator — TASK-APP1-08); any `NATS_*` variable.

## Acceptance Criteria

- [ ] `docker compose -f deploy/http/docker-compose.yml config` validates with
      no `NATS_PASSWORD` requirement anywhere in the file
- [ ] Dev and prod flavours differ only in the token table and reset flag
- [ ] Healthcheck targets `/healthz` on 8100
- [ ] `.env.example` documents the two new vars without real secrets

## Test Requirements

Scaffolding task — validation is `docker compose config` + a grep for
`NATS_PASSWORD` (must be absent).

## Coach Validation

- Run `docker compose -f deploy/http/docker-compose.yml config` (with a stub
  `.env`) — exits 0.
- `rg NATS_PASSWORD deploy/http/` — empty.
