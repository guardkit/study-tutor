---
id: TASK-NATS-PH3-002
title: Build docker-compose.study-tutor.yml with full env block (OPENAI_BASE_URL /v1)
task_type: scaffolding
parent_review: TASK-REV-NATS-001
feature_id: FEAT-NATS
wave: 9
implementation_mode: task-work
complexity: 5
estimated_minutes: 60
status: pending
priority: medium
created: 2026-05-08 00:00:00+00:00
updated: 2026-05-08 00:00:00+00:00
dependencies:
  - TASK-NATS-PH3-001
consumer_context:
  - task: TASK-NATS-PH1-007
    consumes: OPENAI_BASE_URL
    framework: 'langchain-openai (ChatOpenAI client)'
    driver: 'OpenAI HTTP API (compatible endpoint via llama-swap)'
    format_note: 'URL must include /v1 suffix or langchain-openai POSTs to /chat/completions instead of /v1/chat/completions and gets 404. See Bug #3.'
tags:
  - nats
  - scaffolding
  - docker
  - compose
  - phase-3
  - bug-3
---

# Task: Build docker-compose.study-tutor.yml with full env block (OPENAI_BASE_URL /v1)

## Description

Compose file that runs study-tutor alongside the existing specialist-agent dual-role stack on GB10. Critical: the env block must include `OPENAI_BASE_URL=http://host.docker.internal:9000/v1` (with the `/v1` suffix) — Bug #3 manifests when this is missing, and the symptom appears as a 404 mid-`tutor_turn` rather than a startup error.

## Scope

Create `study-tutor/docker-compose.study-tutor.yml`:

- Service `gcse-tutor` using `study-tutor:dev` image (or built inline via `build:` directive).
- `extra_hosts: ["host.docker.internal:host-gateway"]` so llama-swap on the host is reachable.
- Environment block (full list, not just NATS):
  ```yaml
  NATS_URL: nats://${NATS_HOST:-host.docker.internal}:4222
  NATS_USER: ${RICH_NATS_USER:-appmilla}
  NATS_PASSWORD: ${RICH_NATS_PASSWORD:?must-be-set}
  AGENT_ID: gcse-tutor
  OPENAI_BASE_URL: ${TUTOR_OPENAI_BASE_URL:-http://host.docker.internal:9000/v1}
  LLM_BASE_URL: ${TUTOR_LLM_BASE_URL:-http://host.docker.internal:9000}
  LOCAL_MODEL: ${TUTOR_LOCAL_MODEL:-gemma4-tutor}
  OPENAI_API_KEY: ${TUTOR_OPENAI_API_KEY:-local-no-auth-required}
  HEARTBEAT_INTERVAL_SECONDS: 30
  ```
- Healthcheck: optional Phase 3+ — for now skip (the heartbeat *is* the liveness signal).
- Restart policy: `unless-stopped`.

## Acceptance criteria

- [ ] `docker compose -f docker-compose.study-tutor.yml config` validates the file (no schema errors).
- [ ] The compose file references `study-tutor:dev` (or builds it via `build:` directive pointing at the Dockerfile).
- [ ] `OPENAI_BASE_URL` in the env block ends with `/v1` (Bug #3 regression guard — automate this check).
- [ ] `RICH_NATS_PASSWORD` uses `${VAR:?must-be-set}` syntax so the compose-up fails with a clear error if unset.
- [ ] `docker compose -f docker-compose.study-tutor.yml up -d` brings the tutor container up against a running NATS; the container is reachable via `nats request agents.command.gcse-tutor ...` from the host.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation notes

- Reference: [specialist-agent/docker-compose.dual-role.yml:1-49](/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/docker-compose.dual-role.yml). Mirror the env-var-with-default pattern and the `extra_hosts` directive.
- Do NOT define a NATS service in this compose file — NATS is provisioned elsewhere (`nats-infrastructure/`); this compose file only adds the tutor container.

## Coach validation

```bash
docker compose -f docker-compose.study-tutor.yml config | grep -E 'OPENAI_BASE_URL.*\/v1$'
docker compose -f docker-compose.study-tutor.yml up -d
docker compose -f docker-compose.study-tutor.yml ps
docker compose -f docker-compose.study-tutor.yml down
```
