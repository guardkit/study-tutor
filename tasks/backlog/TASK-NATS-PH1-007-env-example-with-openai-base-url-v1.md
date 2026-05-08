---
id: TASK-NATS-PH1-007
title: Update .env.example with NATS and LLM env vars (OPENAI_BASE_URL must include /v1 suffix - Bug #3)
task_type: scaffolding
parent_review: TASK-REV-NATS-001
feature_id: FEAT-NATS
wave: 2
implementation_mode: direct
complexity: 1
estimated_minutes: 15
status: pending
priority: high
created: 2026-05-08 00:00:00+00:00
updated: 2026-05-08 00:00:00+00:00
dependencies:
  - TASK-NATS-PH1-001
tags:
  - nats
  - scaffolding
  - env
  - phase-1
  - bug-3
---

# Task: Update .env.example with NATS and LLM env vars (OPENAI_BASE_URL must include /v1 suffix - Bug #3)

## Description

Documentation-shaped task that prevents Bug #3 (OPENAI_BASE_URL missing `/v1` suffix → `404 Not Found` from langchain-openai mid-`tutor_turn`). Adds the required env vars to `.env.example` so anyone copying it for local dev gets a working configuration on first try.

## Scope

Update `study-tutor/.env.example` to include:

```bash
# NATS fleet
NATS_URL=nats://localhost:4222
NATS_USER=
NATS_PASSWORD=

# Agent identity
AGENT_ID=gcse-tutor

# LLM endpoint (llama-swap on GB10)
# IMPORTANT: OPENAI_BASE_URL MUST include the /v1 suffix.
# Without it, langchain-openai POSTs to /chat/completions instead of /v1/chat/completions
# and gets a 404. See docs/reviews/REVIEW-NATS-FLEET-PATTERNS-2026-05-08.md Bug #3.
OPENAI_BASE_URL=http://host.docker.internal:9000/v1
LLM_BASE_URL=http://host.docker.internal:9000
LOCAL_MODEL=gemma4-tutor
OPENAI_API_KEY=local-no-auth-required

# Heartbeat
HEARTBEAT_INTERVAL_SECONDS=30
```

## Acceptance criteria

- [ ] `.env.example` exists and contains all variables listed above.
- [ ] `grep -E '^OPENAI_BASE_URL=' .env.example` matches a value ending in `/v1` (Bug #3 regression guard — automate this check in CI).
- [ ] The Bug #3 explanatory comment is present immediately above the `OPENAI_BASE_URL` line.
- [ ] No project lint/format violations introduced.

## Implementation notes

- This is the **operator-facing** half of the Bug #3 fix. The **container-facing** half lives in TASK-NATS-PH3-002 (docker-compose env block).
- Do not add real credentials. Leave `NATS_USER`, `NATS_PASSWORD`, and `OPENAI_API_KEY` empty (or with placeholder text); operator fills them locally from password manager.

## Coach validation

```bash
test -f .env.example && grep -qE '^OPENAI_BASE_URL=.*\\/v1$' .env.example && echo OK
```
