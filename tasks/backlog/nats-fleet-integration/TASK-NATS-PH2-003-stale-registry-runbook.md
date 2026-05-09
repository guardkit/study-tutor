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
status: in_review
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
autobuild_state:
  current_turn: 1
  max_turns: 7
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-39E1
  base_branch: main
  started_at: '2026-05-09T08:01:03.444488'
  last_updated: '2026-05-09T08:03:14.400554'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-05-09T08:01:03.444488'
    player_summary: "Created docs/runbooks/known-issues.md because the demo runbook\
      \ RUNBOOK-study-tutor-nats-fleet-demo.md (slated for TASK-NATS-PH3-004) does\
      \ not yet exist in the repo \u2014 the task explicitly instructs to use the\
      \ known-issues.md fallback in that case and migrate later. The new file opens\
      \ with an audience/scope header and a top-level 'When the fleet demo runbook\
      \ lands, migrate this' note so the migration intent is preserved. It then contains\
      \ the required 'Known issue: stale registry entries' section wi"
    player_success: true
    coach_success: true
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
