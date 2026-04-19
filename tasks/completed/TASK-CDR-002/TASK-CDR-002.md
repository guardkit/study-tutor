---
id: TASK-CDR-002
title: ADR-008 — clarify tutor_start_session rationale + add stdio session scope note
status: completed
task_type: implementation
parent_review: TASK-REV-C7D1
feature_id: FEAT-CDR-C7D1
wave: 1
implementation_mode: direct
created: 2026-04-19
completed: 2026-04-19
completed_location: tasks/completed/TASK-CDR-002/
priority: high
tags: [adr, mcp, session-state, phase-0, demo-prep]
complexity: 2
blocks: [system-design]
dependencies: []
test_results:
  status: not-applicable
  coverage: null
  last_run: null
---

# Task: ADR-008 — clarify tutor_start_session rationale + add stdio session scope note

## Description

Parent review
[TASK-REV-C7D1](../../in_review/TASK-REV-C7D1-analyze-claude-desktop-arch-review.md)
findings **F2** and **F3**. Two doc-consistency issues in the same ADR, bundled:

- **F2:** the SR-07 classification table in ADR-ARCH-008 marks
  `tutor_start_session` as long-running but does not say *why*. The scope doc
  gives a reason that doesn't apply in Phase 0 ("includes Graphiti read of
  student model") even though the behaviour is correct. This mismatch will
  confuse `/feature-spec FEAT-PO-002`.
- **F3:** Phase 0 session state is an in-memory dict inside a single stdio
  child process. Claude Desktop launches a fresh child per conversation — a
  real bear-trap for the 16 May demo if the stdio transport is reopened
  mid-session. ASSUM-003 generalises the limitation but doesn't call out the
  stdio-child specifics.

## Scope of Changes

**File:** `docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md`

**Edit 1 (F2):** add a rationale note to or immediately below the SR-07
classification table (line ~37) explaining that `tutor_start_session` is
*architected* as long-running for Phase-1 forward compatibility (where it will
read the student model from Graphiti), while the Phase 0 implementation is a
UUID mint + in-memory dict insert returning in ≤1s.

**Edit 2 (F3):** add a "Phase 0 session scope" subsection to "Consequences"
covering:

1. A fresh stdio child = a fresh (empty) session dict.
2. `tutor_session_status` across Claude Desktop conversations will fail.
3. Demo-script constraint (16 May): do not close and re-open the stdio
   transport mid-session.
4. Link to ASSUM-003 as the general statement of this limitation.

Suggested wording is in the feature's
[IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) §Wave 1 / TASK-CDR-002.

## Acceptance Criteria

- [ ] ADR-008 classification table (or adjacent text) contains the
      "architected as long-running for Phase-1 forward compatibility" rationale.
- [ ] ADR-008 "Consequences" (or an adjacent section) contains the Phase 0
      session-scope behavioural note with the three numbered points above.
- [ ] The note references ASSUM-003 as the generalised version of the
      limitation.
- [ ] Demo-script constraint is explicitly written so the 16 May run does not
      trip over it.

## Test Requirements

Not applicable — doc-only edit. Verification is by reviewing the ADR against
the acceptance criteria.

## Provenance

- Parent review findings: F2, F3
- Reviewer evidence:
  - Scope mismatch confirmed at ADR-ARCH-008:37.
  - In-memory dict confirmed at container.md:31.
  - ASSUM-003 at assumptions.yaml:45-53 is the general statement; stdio-child
    nuance is uncovered.
- Triage: ACCEPT — bundled (see
  [review report](../../../.claude/reviews/TASK-REV-C7D1-review-report.md)).
