---
id: TASK-CDR-006
title: decisions-log — record DEC-NN "do not seed reference prose to Graphiti"
status: completed
task_type: implementation
parent_review: TASK-REV-C7D1
feature_id: FEAT-CDR-C7D1
wave: 2
implementation_mode: direct
created: 2026-04-19
completed: 2026-04-19
completed_location: tasks/completed/TASK-CDR-006/
priority: low
tags: [decisions-log, graphiti, documentation, seeding-policy]
complexity: 1
blocks: []
dependencies: []
test_results:
  status: not-applicable
  coverage: null
  last_run: null
---

# Task: decisions-log — record DEC-NN "do not seed reference prose to Graphiti"

## Description

Parent review
[TASK-REV-C7D1](../../in_review/TASK-REV-C7D1-analyze-claude-desktop-arch-review.md)
observation **O5**. The Claude Desktop reviewer confirmed the existing handoff
decision: do NOT seed `domain-model.md`, `system-context.md`, `container.md`,
or `assumptions.yaml` as `full_doc` Graphiti episodes. The 16 ADRs already
encode every decision; domain-model is reference prose that loses fidelity in
Graphiti's extraction step.

The decision exists informally but isn't captured in the decisions log.
Writing it down prevents re-litigation and gives `/system-design` and
`/system-plan` an explicit pointer to disk-read reference docs rather than
Graphiti-query them.

## Scope of Changes

**File:** `docs/research/ideas/decisions-log-2026-04-17.md`

**Edit:** add a new decision entry using the next available `DEC-NN` ID.
Suggested content (exact ID and final wording assigned during the edit):

> **DEC-NN — Reference prose stays on disk; Graphiti holds decisions only.**
>
> Do NOT seed `domain-model.md`, `system-context.md`, `container.md`, or
> `assumptions.yaml` as `full_doc` Graphiti episodes. The 16 ADRs already
> encode every decision. Domain-model is reference prose that loses
> fidelity in Graphiti's extraction step. Read reference docs from disk in
> `/system-design` and `/system-plan`.
>
> Graphiti remains the "decision record" (ADRs + session-derived entities);
> disk remains the "reference library." Revisit only if Graphiti's
> extraction fidelity improves materially.
>
> Confirmed by the Claude Desktop `/system-arch` review on 2026-04-19
> (TASK-REV-C7D1, observation O5).

## Acceptance Criteria

- [ ] A new `DEC-NN` entry exists in `decisions-log-2026-04-17.md` capturing
      the decision.
- [ ] The entry names the four files that must not be seeded as full_doc.
- [ ] The entry references TASK-REV-C7D1 / observation O5 as the confirming
      source.

## Test Requirements

Not applicable — doc-only edit.

## Provenance

- Parent review observation: O5
- Reviewer confirmation: Claude Desktop review §40 (existing handoff
  decision confirmed).
- Triage: ACCEPT (see
  [review report](../../../.claude/reviews/TASK-REV-C7D1-review-report.md)).
