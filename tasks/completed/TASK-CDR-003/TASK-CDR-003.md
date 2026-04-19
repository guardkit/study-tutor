---
id: TASK-CDR-003
title: ADR-015 — verify eu-west-2 Bedrock availability + rewrite "UK-adjacent" framing
status: completed
task_type: implementation
parent_review: TASK-REV-C7D1
feature_id: FEAT-CDR-C7D1
wave: 1
implementation_mode: task-work
created: 2026-04-19
completed: 2026-04-19
completed_location: tasks/completed/TASK-CDR-003/
priority: high
tags: [adr, aws-bedrock, data-residency, feat-po-004, region]
complexity: 3
blocks: [system-design]
dependencies: []
related: [FEAT-PO-004]
follow_up: [TASK-CDR-003a]
test_results:
  status: not-applicable
  coverage: null
  last_run: null
completion_notes: >-
  Closed with the conditional ADR-015 / ASSUM-007 rewrite landed.
  The 21–22 Apr eu-west-2 console verification and follow-up
  narrowing edit are tracked under TASK-CDR-003a.
---

# Task: ADR-015 — verify eu-west-2 Bedrock availability + rewrite "UK-adjacent" framing

## Description

Parent review
[TASK-REV-C7D1](../../in_review/TASK-REV-C7D1-analyze-claude-desktop-arch-review.md)
finding **F4**. ADR-ARCH-015:62 says Bedrock "runs in a UK-adjacent region," but
ASSUM-007:99-116 explicitly names `us-east-1` or `us-west-2` as the selected
region. us-east-1 is Virginia; us-west-2 is Oregon. Neither is UK-adjacent in
any GDPR-relevant sense, and the residency posture in ADR-015 depends on this
claim being true.

Two-step fix: verify whether eu-west-2 (London) actually supports Bedrock
Custom Model Import for Gemma 4 31B, then rewrite ADR-015 to match reality.

## Scope of Changes

**Step 1 — Verification (folds into FEAT-PO-004 Bedrock setup, 21 Apr evening):**

Check the AWS Bedrock console's "Custom model import" region selector and
supported-model list for `eu-west-2`. Record the result (supported / not
supported / unclear) in this task.

**Step 2 — ADR edit:**

Rewrite the `Bedrock exception` paragraph in
`docs/architecture/decisions/ADR-ARCH-015-uk-on-device-data-residency.md` based
on the verification outcome:

- **If eu-west-2 supports it:** change "UK-adjacent region" to "eu-west-2
  (London) — UK-region." Update ASSUM-007's region list if necessary.
- **If eu-west-2 does not support it:** rewrite to honestly state us-east-1 or
  us-west-2, acknowledging the residency posture is a Phase 3 concern for the
  hackathon, and that only prompts/responses transit the region (no student
  identity or session metadata). Wording guidance in
  [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) §Wave 1 / TASK-CDR-003.

## Acceptance Criteria

- [ ] Verification outcome recorded in this task file (section below) with
      the date and source (e.g. "checked AWS Bedrock console on 21 Apr 2026,
      eu-west-2 Custom Model Import lists/does not list Gemma 4 31B").
- [ ] ADR-015's "UK-adjacent region" wording is replaced with a region
      statement that matches reality.
- [ ] If the actual region is us-east-1 / us-west-2, ADR-015 explicitly
      acknowledges the residency trade-off and marks it as a Phase 3 concern
      for post-hackathon.
- [ ] ASSUM-007's region list is consistent with the ADR-015 wording after
      the edit.

## Test Requirements

Not a code change — verification is by console check + doc read. Grep
verification:

```bash
! grep -n "UK-adjacent" docs/architecture/decisions/ADR-ARCH-015-*.md
# Must return no matches after the edit.
```

## Verification Result

_To be populated during FEAT-PO-004 setup (21–22 Apr 2026). The ADR-015
edit has landed as conditional prose ahead of the verification per
IMPLEMENTATION-GUIDE.md guidance; once the console check is done, this
section is filled in and the ADR/ASSUM-007 wording is narrowed to the
confirmed region in a follow-up edit._

- Check date: ____
- Source: ____ (e.g. "AWS Bedrock console → Custom model import →
  region selector → eu-west-2 → supported model list")
- Outcome: ____ (supported / not supported / unclear)
- Chosen region: ____ (eu-west-2 | us-east-1 | us-west-2)

## Implementation Log

**2026-04-19 — Conditional rewrite landed.**

- `docs/architecture/decisions/ADR-ARCH-015-uk-on-device-data-residency.md`
  - Removed the "UK-adjacent region" wording.
  - Replaced with conditional prose: prefer `eu-west-2` (London —
    UK-region); fall back to `us-east-1` / `us-west-2` for demo week
    if `eu-west-2` does not yet support Bedrock Custom Model Import
    for Gemma 4 31B; explicitly notes the residency trade-off and
    marks it as a Phase 3 concern for post-hackathon migration.
  - Updated the Layer 1 inference bullet in Context to match.
- `docs/architecture/assumptions.yaml`
  - ASSUM-007 description now lists `eu-west-2` first as the
    preferred region, with `us-east-1` / `us-west-2` as fallback,
    matching ADR-015.
  - `revisit_trigger` extended: if `eu-west-2` Custom Model Import
    does not list Gemma 4 31B, fall back per ADR-ARCH-015.
- Verification (Step 1) deferred to 21–22 Apr per the implementation
  guide. Result will narrow the ADR/ASSUM-007 prose to a single
  region in a follow-up edit.

Verification:

```bash
$ grep -n "UK-adjacent" docs/architecture/decisions/ADR-ARCH-015-*.md
# (no matches — see acceptance criterion)
```

## Implementation Notes

- The ADR edit can happen before the 22 Apr verification if written as
  conditional prose; the verification then narrows the language to match the
  confirmed region.
- Do not replace the ADR's on-device residency story — the Bedrock exception
  is already accepted; the edit is about describing the exception accurately.

## Provenance

- Parent review finding: F4
- Reviewer evidence:
  - ADR-ARCH-015:62 ("UK-adjacent region") vs ASSUM-007:99-116 ("us-east-1 or
    us-west-2").
- Triage: ACCEPT (see
  [review report](../../../.claude/reviews/TASK-REV-C7D1-review-report.md)).
