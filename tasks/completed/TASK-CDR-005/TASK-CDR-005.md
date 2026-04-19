---
id: TASK-CDR-005
title: ASSUM-007 — capture Bedrock-out workload contingency (user decision)
status: completed
task_type: implementation
parent_review: TASK-REV-C7D1
feature_id: FEAT-CDR-C7D1
wave: 2
implementation_mode: task-work
created: 2026-04-19
decision_recorded: 2026-04-19
completed: 2026-04-19
completed_location: tasks/completed/TASK-CDR-005/
priority: medium
tags: [assumption, bedrock, gb10, dec-07, contingency, user-decision]
complexity: 3
blocks: []
dependencies: []
blocked_by_decision: resolved
test_results:
  status: not-applicable
  coverage: null
  last_run: null
---

# Task: ASSUM-007 — capture Bedrock-out workload contingency (user decision)

## Description

Parent review
[TASK-REV-C7D1](../../in_review/TASK-REV-C7D1-analyze-claude-desktop-arch-review.md)
observation **O2**. ASSUM-007 says that if FEAT-PO-004 (22 Apr) shows Bedrock
doesn't support Gemma 4 31B natively, "Ollama-primary posture stays and
demo-week scheduling becomes tighter." But that doesn't actually solve the
problem: GB10 is still needed for three sequential DEC-07 workloads, and if
demo-week inference is on Ollama, one of the training runs gets squeezed.

The decision of *which* workload gets squeezed is easier to make now than at
3am on 11 May.

## Decision Needed (user)

If FEAT-PO-004 fails on 22 Apr and Bedrock is out, pick a priority ordering of
the three DEC-07 GB10 workloads:

1. Study-tutor training-dataset expansion (additional subjects).
2. Study-tutor re-fine-tune.
3. Architect-agent training + fine-tune for DDD Southwest (16 May).

**Question:** which workload is squeezed first? Second? Which is non-negotiable?

## Scope of Changes (after decision is recorded)

**File 1:** `docs/architecture/assumptions.yaml` — update ASSUM-007's
`revisit_trigger` to name the chosen priority ordering.

**File 2 (optional):** `docs/research/ideas/phase-0-build-plan.md` — add a
short "Bedrock-out contingency" callout under the FEAT-PO-004 section so the
decision is visible from the build plan, not just the assumptions file.

## Acceptance Criteria

- [ ] User's priority ordering of the three DEC-07 workloads under the
      "Bedrock out" branch is recorded in this task file (section below).
- [ ] ASSUM-007's `revisit_trigger` in `assumptions.yaml` names the chosen
      priority (e.g. "If Bedrock is out: workload X deferred, workloads Y/Z
      retain priority; demo-week runs on Ollama only.").
- [ ] (Optional) `phase-0-build-plan.md` FEAT-PO-004 section references the
      contingency so it's visible during the 22 Apr verification.

## User Decision

Recorded **2026-04-19** by the project owner.

**Bedrock-out branch — GB10 workload priority ordering:**

- **Priority 1 (non-negotiable):** Architect-agent training + fine-tune for
  DDD Southwest (16 May 2026). Fixed external deadline, planned for the
  week of 21 Apr.
- **Priority 2 (squeezed if needed):** Study-tutor re-fine-tune. The
  current Gemma 4 MoE study-tutor checkpoint was fine-tuned **18 Apr 2026**
  and is usable as-is for demo week; only re-runs once a meaningfully
  larger dataset is available.
- **Priority 3 (squeezed first):** Study-tutor training-dataset expansion
  (additional GCSE subjects). Gated on further GCSE subject books arriving
  — explicitly user-deferred until then. Naturally couples with Priority 2
  (a re-fine-tune follows a dataset expansion).

**Rationale:**

- DDD Southwest 16 May is a fixed, externally-committed deadline → the
  architect-agent run is the only one that cannot slip.
- Study-tutor was fine-tuned the day before this decision, so demo-week
  inference (whether on Bedrock or fallback Ollama) already has a
  shippable model — the re-fine-tune isn't on the critical path.
- The dataset expansion is input-bound (waiting on physical GCSE
  textbooks), so deferring it costs nothing — it can't run sooner anyway.

## Side Decision — Bedrock Hosting Order (Bedrock-in Branch)

If FEAT-PO-004 succeeds and Bedrock is available, the hosting priority
order on Bedrock Custom Model Import is:

1. Study-tutor Gemma 4 MoE (first to host — drives the demo).
2. Architect-agent Gemma 4 MoE (host once architect training completes,
   before 16 May).

This is captured here because it surfaced from the same decision
conversation; the assumptions.yaml edit only encodes the Bedrock-*out*
contingency, since that's the conditional one.

## Test Requirements

Not applicable — doc-only edit after the decision is made.

## Implementation Notes

- This task stays in `backlog` until the user records the decision. Do not
  attempt to pick a priority ordering autonomously — DEC-07 workload
  prioritisation involves commitments outside the repo (DDD Southwest
  deadline, Lilymay's daily use, training data quality).
- Once the decision is recorded, the actual doc edit is a few lines and can
  land in minutes.

## Provenance

- Parent review observation: O2
- Reviewer evidence: ASSUM-007:112-116 acknowledges tighter scheduling but
  does not name a priority ordering.
- Triage: ACCEPT (see
  [review report](../../../.claude/reviews/TASK-REV-C7D1-review-report.md)).
