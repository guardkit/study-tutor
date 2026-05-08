---
id: TASK-NATS-PH3-001
title: Build study-tutor Dockerfile mirroring specialist-agent pattern
task_type: scaffolding
parent_review: TASK-REV-NATS-001
feature_id: FEAT-NATS
wave: 8
implementation_mode: task-work
complexity: 5
estimated_minutes: 90
status: pending
priority: medium
created: 2026-05-08 00:00:00+00:00
updated: 2026-05-08 00:00:00+00:00
dependencies:
  - TASK-NATS-PH1-005
tags:
  - nats
  - scaffolding
  - docker
  - phase-3
---

# Task: Build study-tutor Dockerfile mirroring specialist-agent pattern

## Description

Containerise study-tutor so it can run alongside specialist-agent on GB10. Mirrors specialist-agent's Dockerfile pattern at [specialist-agent/Dockerfile:1-37](../../../../specialist-agent/Dockerfile), particularly the BuildKit named context for sibling `nats-core` (since `nats-core` is consumed via editable install).

## Scope

Create `study-tutor/Dockerfile`:

- Base image: `python:3.13-slim` (or whichever the existing project pins).
- Use BuildKit named contexts: `--build-context nats-core=../nats-core` so the editable `nats-core` install resolves at build time.
- Copy `pyproject.toml` and `uv.lock`, run `uv sync --frozen --no-dev`.
- Copy `src/`, install editable: `uv pip install -e .`.
- Default entrypoint: `study-tutor serve-nats`.
- Expose nothing (it's a NATS subscriber, not an HTTP service).

## Acceptance criteria

- [ ] `docker build -f study-tutor/Dockerfile --build-context nats-core=../nats-core -t study-tutor:dev ..` (from a parent directory containing both repos) succeeds without errors.
- [ ] `docker run --rm study-tutor:dev study-tutor serve-nats --help` shows the expected flag surface.
- [ ] `docker run --rm study-tutor:dev which study-tutor` returns a valid path.
- [ ] Image size is reasonable (< 800MB; track if it exceeds).
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation notes

- Reference: [specialist-agent/Dockerfile:1-37](../../../../specialist-agent/Dockerfile). Match the layering (deps before source) so cache invalidation is minimal.
- For the nats-core named context, see [specialist-agent/scripts/docker-build.sh](../../../../specialist-agent/scripts/) (replicated by TASK-NATS-PH3-003).
- Do NOT bake credentials. Env vars come from runtime via `docker-compose` or `--env-file`.

## Coach validation

```bash
docker build -f Dockerfile --build-context nats-core=../nats-core -t study-tutor:dev .. 2>&1 | tail -20
docker run --rm study-tutor:dev study-tutor serve-nats --help | grep -E '(--nats|--agent-id)'
```
