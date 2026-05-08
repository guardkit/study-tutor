---
id: TASK-NATS-PH3-003
title: Add scripts/docker-build.sh mirroring specialist-agent pattern
task_type: scaffolding
parent_review: TASK-REV-NATS-001
feature_id: FEAT-NATS
wave: 9
implementation_mode: direct
complexity: 2
estimated_minutes: 20
status: pending
priority: low
created: 2026-05-08 00:00:00+00:00
updated: 2026-05-08 00:00:00+00:00
dependencies:
  - TASK-NATS-PH3-001
tags:
  - nats
  - scaffolding
  - docker
  - phase-3
---

# Task: Add scripts/docker-build.sh mirroring specialist-agent pattern

## Description

One-line shell wrapper for `docker build` that handles the BuildKit named context for sibling `nats-core`. Operator convenience — saves remembering the long `--build-context` flag. Mirrors specialist-agent's pattern.

## Scope

Create `study-tutor/scripts/docker-build.sh`:

```bash
#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

DOCKER_BUILDKIT=1 docker build \
    --build-context nats-core=../nats-core \
    -f Dockerfile \
    -t "study-tutor:${TAG:-latest}" \
    .
```

Make executable: `chmod +x scripts/docker-build.sh`.

## Acceptance criteria

- [ ] `scripts/docker-build.sh` exists and is executable.
- [ ] Running `./scripts/docker-build.sh` from the repo root succeeds and produces an image tagged `study-tutor:latest`.
- [ ] `TAG=dev ./scripts/docker-build.sh` produces `study-tutor:dev`.
- [ ] Script uses `set -euo pipefail` and exits non-zero on build failure.
- [ ] No project lint/format violations introduced (run `shellcheck` if available).

## Implementation notes

Reference: specialist-agent's equivalent script (look in `specialist-agent/scripts/`).

## Coach validation

```bash
test -x scripts/docker-build.sh && ./scripts/docker-build.sh && docker image inspect study-tutor:latest >/dev/null
```
