---
feature_id: FEAT-CDR-C7D1
parent_review: TASK-REV-C7D1
feature_slug: claude-desktop-review-fixes
status: backlog
created: 2026-04-19
---

# Feature: Claude Desktop Review Fixes (pre-`/system-design` gate)

## Problem

The Claude Desktop architecture review
([docs/reviews/architecture/claude-desktop-review-system-arch-output.md](../../../docs/reviews/architecture/claude-desktop-review-system-arch-output.md))
flagged one hard bug and eight doc/decision issues against the `/system-arch` output.
Going into `/system-design` on Sunday morning without these fixed means the design doc
inherits inconsistent framing, and the one hard bug (embedding dimension mismatch)
will block Phase 1 seeding.

Parent review: [TASK-REV-C7D1](../../in_review/TASK-REV-C7D1-analyze-claude-desktop-arch-review.md) ·
Report: [.claude/reviews/TASK-REV-C7D1-review-report.md](../../../.claude/reviews/TASK-REV-C7D1-review-report.md)

## Solution Approach

Six small, focused edits organised into two waves:

- **Wave 1 (blocks `/system-design`):** TASK-CDR-001, TASK-CDR-002, TASK-CDR-003.
- **Wave 2 (non-blocking, before Phase 2):** TASK-CDR-004, TASK-CDR-005, TASK-CDR-006.

Each subtask touches a different file; waves are internally parallelisable.

## Subtasks

| ID | Title | Wave | Mode | Complexity | Addresses |
|---|---|---|---|---|---|
| TASK-CDR-001 | Fix `embedding_dimensions` 1024 → 768 | 1 | task-work | 2 | F1 (hard bug) |
| TASK-CDR-002 | ADR-008: `tutor_start_session` rationale + stdio session scope note | 1 | direct | 2 | F2, F3 |
| TASK-CDR-003 | ADR-015: verify eu-west-2 Bedrock + fix "UK-adjacent" framing | 1 | task-work | 3 | F4 |
| TASK-CDR-004 | ADR-013: make CompositeBackend middleware seam explicit | 2 | direct | 1 | O1 |
| TASK-CDR-005 | ASSUM-007: capture Bedrock-out workload contingency (user decision) | 2 | task-work | 3 | O2 |
| TASK-CDR-006 | decisions-log: record DEC-NN "do not seed reference prose to Graphiti" | 2 | direct | 1 | O5 |

## Go / No-Go on `/system-design`

`/system-design` proceeds after **Wave 1 is complete**. Wave 2 tasks do not block.

## See Also

- [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) — wave-by-wave execution plan
- [TASK-REV-C7D1](../../in_review/TASK-REV-C7D1-analyze-claude-desktop-arch-review.md) — parent review with full triage rationale
- [.claude/reviews/TASK-REV-C7D1-review-report.md](../../../.claude/reviews/TASK-REV-C7D1-review-report.md) — full verification evidence
