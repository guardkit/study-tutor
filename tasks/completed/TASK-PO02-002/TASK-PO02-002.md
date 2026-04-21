---
id: TASK-PO02-002
title: Role manifest and player prompt shell
status: completed
created: 2026-04-20T00:00:00Z
updated: 2026-04-20T07:25:00Z
completed: 2026-04-20T07:25:00Z
completed_location: tasks/completed/TASK-PO02-002/
priority: high
task_type: declarative
tags: [phase-0, role-manifest, declarative]
complexity: 2
parent_review: TASK-REV-PO02
feature_id: FEAT-PO-002
wave: 1
implementation_mode: direct
dependencies: []
estimated_minutes: 30
test_results:
  status: n/a
  coverage: null
  last_run: null
  note: "direct-mode task — file authoring only, no tests"
---

# Role manifest and player prompt shell

## Description

Create the `roles/tutor/` directory with a minimal `role.yaml` manifest and a placeholder `prompts/player.md`. Per **D1 in the review report**, the file structure is owned by FEAT-PO-002 (infrastructure) while the *content* of `prompts/player.md` is owned by FEAT-PO-001 (domain).

This task ships the shells. FEAT-PO-001 overwrites `prompts/player.md` with the real content once `domains/gcse-english/GOAL.md` is drafted.

## Acceptance Criteria

- [ ] `roles/tutor/role.yaml` exists with minimal fields: `name: tutor`, `description`, `player_prompt_path: roles/tutor/prompts/player.md`, `criteria_path: roles/tutor/criteria/definitions.yaml` (file itself is FEAT-PO-001's responsibility — reference is fine even if file is absent in Phase 0 Saturday).
- [ ] Shape of `role.yaml` mirrors `specialist-agent/roles/product-owner/role.yaml`. No schema divergence — future Coach integration in Phase 1 depends on this.
- [ ] `roles/tutor/prompts/player.md` exists as a placeholder with a single line: `<!-- FEAT-PO-001 will populate this from domains/gcse-english/GOAL.md -->`.
- [ ] `roles/tutor/criteria/` directory created (empty) so FEAT-PO-001 has somewhere to drop `definitions.yaml`.
- [ ] Relative paths inside `role.yaml` resolve from the **repo root**, not CWD. SR-02 compliance is enforced later by the bash wrapper (TASK-PO02-005) `cd`-ing to absolute path.

## Implementation Notes

- This is a **direct-mode** task — file authoring, no logic. No tests. No implementation plan phase needed.
- Do not invent new YAML fields. If a field exists in specialist-agent's `role.yaml` and isn't obviously needed for Phase 0, leave it as `null` or omit it — don't add new ones.

## Reference Files

- Shape source: `../specialist-agent/roles/product-owner/role.yaml`
- Plan: [docs/research/ideas/phase-0-build-plan.md:442-444](../../../docs/research/ideas/phase-0-build-plan.md#L442-L444)
