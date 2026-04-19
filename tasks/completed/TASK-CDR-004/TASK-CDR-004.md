---
id: TASK-CDR-004
title: ADR-013 — make CompositeBackend middleware seam explicit
status: completed
updated: 2026-04-19
completed: 2026-04-19
previous_state: in_review
completed_location: tasks/completed/TASK-CDR-004/
task_type: implementation
parent_review: TASK-REV-C7D1
feature_id: FEAT-CDR-C7D1
wave: 2
implementation_mode: direct
created: 2026-04-19
priority: medium
tags: [adr, gamification, deepagents, phase-2, doc-consistency]
complexity: 1
blocks: []
dependencies: []
test_results:
  status: not-applicable
  coverage: null
  last_run: null
---

# Task: ADR-013 — make CompositeBackend middleware seam explicit

## Description

Parent review
[TASK-REV-C7D1](../../in_review/TASK-REV-C7D1-analyze-claude-desktop-arch-review.md)
observation **O1**. ADR-ARCH-013 describes `GamificationMiddleware` as a
possible Phase 2 shape but does not link back to ADR-ARCH-012's
`CompositeBackend` route-scoped permissions, which are the actual middleware
insertion point the gamification middleware would attach to. Making the seam
explicit now ensures FEAT-PO-007 (Phase 2 Gamification Engine spec) inherits
the awareness.

## Scope of Changes

**File:**
`docs/architecture/decisions/ADR-ARCH-013-middleware-level-gamification-engine-future.md`

**Edit:** add one sentence (or a short paragraph) to the "Consequences" section
(or immediately after the middleware-shape description in "Decision") linking
the middleware seam to ADR-012. Suggested wording in
[IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) §Wave 2 / TASK-CDR-004.

## Acceptance Criteria

- [x] ADR-013 contains an explicit reference to ADR-012's `CompositeBackend`
      route-scoped permissions as the middleware insertion point.
- [x] The reference notes that if Phase 2 picks middleware, the wiring seam
      already exists; if Phase 2 picks a standalone module, the cost is small
      additional wiring (not a re-architecture).

## Test Requirements

Not applicable — doc-only edit.

## Provenance

- Parent review finding: O1
- Reviewer evidence: ADR-013:25-62 (no reference to ADR-012 insertion point).
- Triage: ACCEPT (see
  [review report](../../../.claude/reviews/TASK-REV-C7D1-review-report.md)).
