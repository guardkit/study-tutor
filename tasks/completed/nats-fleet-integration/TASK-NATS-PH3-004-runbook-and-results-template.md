---
id: TASK-NATS-PH3-004
title: Write RUNBOOK and RESULTS template under docs/runbooks (mirror jarvis structure)
task_type: documentation
parent_review: TASK-REV-NATS-001
feature_id: FEAT-NATS
wave: 10
implementation_mode: direct
complexity: 4
estimated_minutes: 90
status: completed
priority: medium
created: 2026-05-08 00:00:00+00:00
updated: 2026-05-08 00:00:00+00:00
dependencies:
- TASK-NATS-PH3-002
tags:
- nats
- documentation
- runbook
- phase-3
- bug-4
autobuild_state:
  current_turn: 1
  max_turns: 7
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-39E1
  base_branch: main
  started_at: '2026-05-09T08:01:03.443501'
  last_updated: '2026-05-09T08:11:49.524393'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-05-09T08:01:03.443501'
    player_summary: "Created the three artefacts the task scope demands, mirroring\
      \ the structural shape of jarvis's RUNBOOK-jarvis-architect-align-dddsw-demo.md\
      \ and RESULTS-jarvis-architect-align-dddsw-demo-2026-05-08-followup-post-W2.md\
      \ so cross-runbook comparisons are trivial.\n\nRUNBOOK structure (mirrored from\
      \ jarvis):\n- Header: status / purpose / topology arrow / companion references\
      \ / machine layout / wall-clock / outputs.\n- 'What this runbook does NOT cover'\
      \ (forge path; mid-session Graphiti checkpoints \u2014 Decis"
    player_success: true
    coach_success: true
---

# Task: Write RUNBOOK and RESULTS template under docs/runbooks (mirror jarvis structure)

## Description

Adopt jarvis's three-part runbook artefact pattern (RUNBOOK procedure + RESULTS-{date} per execution + evidence/ directory). Establishes the on-disk template for every future demo run.

## Scope

Create:

- `docs/runbooks/RUNBOOK-study-tutor-nats-fleet-demo.md` — the procedure: phase × gate table, expected outputs, wire-tap commands, environmental prerequisites, ADR pair (if relevant).
- `docs/runbooks/templates/RESULTS-template.md` — blank RESULTS template that operators copy to `RESULTS-{slug}-{YYYY-MM-DD}.md` per execution.
- `docs/runbooks/evidence/.gitkeep` — placeholder for the per-execution evidence directories.

The RUNBOOK must include:

- Phase × Gate × Outcome × Evidence column structure (matching jarvis runbooks).
- Wire-tap commands using `agents.command.>` and `agents.result.>` (NOT `agents.command.<id>.>` — Bug #4 regression guard).
- The "Known issue: stale registry entries" section from TASK-NATS-PH2-003.
- A "Bug catalogue" section template (symptom / cause / fix / where-it-must-live shape).

The RESULTS template must include:

- HEAD shas of all participating repos (study-tutor, jarvis, specialist-agent, nats-core, fleet-gateway)
- "Outcome" line at the top: ✅/⏸/❌
- "Demo blocking?" line
- Phase × Gate × Outcome × Evidence table
- Bug catalogue (if any)
- "What's working" narrative
- "Next steps" with concrete fix-and-rerun list

## Acceptance criteria

- [ ] `docs/runbooks/RUNBOOK-study-tutor-nats-fleet-demo.md` exists with the full procedure.
- [ ] Wire-tap subject patterns in the runbook are `agents.command.>` and `agents.result.>` (Bug #4 regression — automate the negative check via `! grep -E 'agents\.command\.[a-z-]+\.>'` in the runbook).
- [ ] `docs/runbooks/templates/RESULTS-template.md` exists with all required sections.
- [ ] `docs/runbooks/evidence/.gitkeep` exists (empty file is fine).
- [ ] No project lint/format violations introduced.

## Implementation notes

Reference: [jarvis/docs/runbooks/RUNBOOK-jarvis-architect-align-dddsw-demo.md](/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/runbooks/RUNBOOK-jarvis-architect-align-dddsw-demo.md) and [RESULTS-jarvis-architect-align-dddsw-demo-2026-05-08-followup-post-W2.md](/Users/richardwoollcott/Projects/appmilla_github/jarvis/docs/runbooks/RESULTS-jarvis-architect-align-dddsw-demo-2026-05-08-followup-post-W2.md). Mirror their structure exactly so cross-runbook comparisons are trivial.

## Coach validation

```bash
test -f docs/runbooks/RUNBOOK-study-tutor-nats-fleet-demo.md
test -f docs/runbooks/templates/RESULTS-template.md
test -f docs/runbooks/evidence/.gitkeep
# Bug #4 regression: wire-tap pattern must be flat
! grep -E 'agents\.command\.[a-z-]+\.>' docs/runbooks/RUNBOOK-study-tutor-nats-fleet-demo.md && echo "wire-tap pattern OK"
```
