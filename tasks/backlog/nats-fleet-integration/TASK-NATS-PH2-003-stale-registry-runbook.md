---
id: TASK-NATS-PH2-003
title: Document stale registry entry symptom and manual cleanup in runbook
task_type: documentation
parent_review: TASK-REV-NATS-001
feature_id: FEAT-NATS
wave: 8
implementation_mode: direct
complexity: 2
estimated_minutes: 30
status: pending
priority: medium
created: 2026-05-08 00:00:00+00:00
updated: 2026-05-08 00:00:00+00:00
dependencies: []
tags:
  - nats
  - documentation
  - runbook
  - phase-2
  - decision-3
---

# Task: Document stale registry entry symptom and manual cleanup in runbook

## Description

Per Decision 3 (2026-05-08): the stale-agent reaper is deferred to jarvis post-demo. Until it lands, study-tutor's runbook documents the symptom (jarvis advertises tutor but commands time out) and the manual cleanup command.

## Scope

Add a "Known issue: stale registry entries" section to `docs/runbooks/RUNBOOK-study-tutor-nats-fleet-demo.md` (created in TASK-NATS-PH3-004) covering:

- **Symptom**: jarvis lists `gcse-tutor` as available; commands time out instead of returning errors.
- **Cause**: tutor process was killed without graceful shutdown (SIGKILL, OOM, container crash). The `agent-registry` KV row persists indefinitely (no TTL).
- **Cleanup**: `nats kv del agent-registry gcse-tutor`
- **When jarvis-side reaper lands**: TASK-NATS-FU-002 (jarvis repo, post-demo) will make this self-healing.

If the demo runbook (TASK-NATS-PH3-004) doesn't exist yet at the time this task runs, create the section in this repo's `docs/runbooks/known-issues.md` instead and migrate it later.

## Acceptance criteria

- [ ] A section titled "Known issue: stale registry entries" exists in either `RUNBOOK-study-tutor-nats-fleet-demo.md` or `docs/runbooks/known-issues.md`.
- [ ] The section names the symptom, cause, and cleanup command verbatim.
- [ ] The section references TASK-NATS-FU-002 as the long-term fix.
- [ ] No project lint/format violations introduced.

## Implementation notes

This is purely documentation. Do not write any code.

Dependency on PH1-010 was a temporal hint ("don't write Phase 2 docs until Phase 1 demo evidence exists"), not a real ordering constraint. Removed per [TASK-REV-D509](../../TASK-REV-D509-analyse-feat-39e1-autobuild-run-2-failure.md). Pure documentation task with no code touchpoints.
