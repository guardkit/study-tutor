---
id: TASK-CDR-003a
title: ADR-015 / ASSUM-007 — narrow region prose after eu-west-2 Bedrock verification
status: backlog
task_type: implementation
parent_review: TASK-REV-C7D1
parent_task: TASK-CDR-003
feature_id: FEAT-CDR-C7D1
wave: 1
implementation_mode: direct
created: 2026-04-19
priority: high
tags: [adr, aws-bedrock, data-residency, feat-po-004, region, follow-up]
complexity: 1
blocks: []
dependencies: [FEAT-PO-004]
related: [TASK-CDR-003, FEAT-PO-004]
test_results:
  status: not-applicable
  coverage: null
  last_run: null
---

# Task: ADR-015 / ASSUM-007 — narrow region prose after eu-west-2 Bedrock verification

## Description

Follow-up to [TASK-CDR-003](../../completed/TASK-CDR-003/TASK-CDR-003.md).
That task closed with **conditional** prose in ADR-015 and ASSUM-007 because
the AWS Bedrock console check for `eu-west-2` Custom Model Import support of
Gemma 4 31B was scheduled for 21–22 Apr 2026 (FEAT-PO-004 setup), after
TASK-CDR-003 needed to land for `/system-design`.

Once the verification is performed, the conditional "prefer eu-west-2, fall
back to us-east-1/us-west-2" wording should be narrowed to a single
confirmed region.

## Scope of Changes

**Step 1 — Record the verification outcome** in
`tasks/completed/TASK-CDR-003/TASK-CDR-003.md` under the "Verification
Result" section:

- Check date
- Source (e.g. "AWS Bedrock console → Custom model import → region selector
  → eu-west-2 → supported model list, checked 22 Apr 2026")
- Outcome (supported / not supported / unclear)
- Chosen region (`eu-west-2` | `us-east-1` | `us-west-2`)

**Step 2 — Narrow ADR-015** in
`docs/architecture/decisions/ADR-ARCH-015-uk-on-device-data-residency.md`:

- Layer 1 inference bullet (Context section): drop the conditional and
  state the confirmed region.
- "Bedrock exception" subsection (Decision section): drop the conditional
  and state the confirmed region. If the chosen region is not `eu-west-2`,
  keep the residency-trade-off paragraph and the Phase 3 migration note;
  if it is `eu-west-2`, the residency-trade-off paragraph can be removed
  (no trade-off remains).

**Step 3 — Narrow ASSUM-007** in
`docs/architecture/assumptions.yaml`:

- `description`: replace the "preferred eu-west-2, fallback us-east-1 /
  us-west-2" wording with the confirmed region.
- `revisit_trigger`: drop the "if eu-west-2 does not support" branch
  (verification has resolved it).

## Acceptance Criteria

- [ ] Verification Result section in TASK-CDR-003 (in `tasks/completed/`)
      is filled in with date, source, outcome, and chosen region.
- [ ] ADR-015 names exactly one region for Bedrock; no conditional
      ("preferred ... fallback ...") wording remains.
- [ ] ASSUM-007 names exactly one region; revisit_trigger no longer
      mentions the verification branch.
- [ ] If the chosen region is `us-east-1` or `us-west-2`, ADR-015 keeps
      the explicit residency trade-off acknowledgement and the Phase 3
      migration note.

## Test Requirements

Doc-only. Grep verification:

```bash
! grep -nE "preferred|fallback|eu-west-2.*us-east-1|conditional" \
    docs/architecture/decisions/ADR-ARCH-015-*.md \
    docs/architecture/assumptions.yaml \
  | grep -i "region\|bedrock"
# Should not show the conditional region wording after the narrowing edit.
```

## Implementation Notes

- Trivial doc edit (`--micro` candidate). Implementation mode: direct.
- Schedule: as soon as FEAT-PO-004 verification finishes (target 22 Apr
  2026 evening).
- Do not touch ADR-015's on-device residency story or the Gemini
  exception — both are out of scope.

## Provenance

- Parent task: [TASK-CDR-003](../../completed/TASK-CDR-003/TASK-CDR-003.md)
  (closed 19 Apr with conditional prose).
- Parent review finding: F4
  (see [review report](../../../.claude/reviews/TASK-REV-C7D1-review-report.md)).
