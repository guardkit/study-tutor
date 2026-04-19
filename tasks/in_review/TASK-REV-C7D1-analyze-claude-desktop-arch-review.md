---
id: TASK-REV-C7D1
title: Analyze Claude Desktop architecture review feedback
status: review_complete
task_type: review
decision_required: true
created: 2026-04-19T00:00:00Z
updated: 2026-04-19T00:00:00Z
priority: high
tags: [architecture-review, assessment, decision-point, system-arch, phase-0]
complexity: 6
source_document: docs/reviews/architecture/claude-desktop-review-system-arch-output.md
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: architectural
  depth: standard
  score: 95
  findings_count: 10
  accepted_count: 7
  deferred_count: 3
  rejected_count: 0
  decision: proceed_to_system_design_after_F1_F4
  report_path: .claude/reviews/TASK-REV-C7D1-review-report.md
  completed_at: 2026-04-19T00:00:00Z
---

# Task: Analyze Claude Desktop architecture review feedback

## Description

A Claude Desktop review of the `/system-arch` output has surfaced one hard bug, four
structural issues worth addressing before `/system-design`, plus several smaller
observations. This task captures the review feedback as a single analysis/decision
unit so each finding is triaged (accept / defer / reject), assigned an owner, and
— where accepted — spawned as concrete implementation tasks.

Source: [claude-desktop-review-system-arch-output.md](../../docs/reviews/architecture/claude-desktop-review-system-arch-output.md)

The reviewer's bottom line: **proceed to `/system-design` after fixing items 1–4**.
Item 5 (Subject enum shape) can be resolved inside `/system-design`. The rest is
either correctly phase-gated, proposed, or a presentation nit.

## Scope of Analysis

Triage each finding below. For each one, record: **accept / defer / reject**,
rationale, and — if accepted — the follow-up action (ADR edit, config edit, new
implementation task, or note captured elsewhere).

### Hard bug (blocks Phase 1 seeding)
- [ ] **F1 — Embedding dimension mismatch.** ADR-007 + `.guardkit/graphiti.yaml`
  declare `embedding_dimensions: 1024`, but `nomic-embed-text-v1.5` returns 768.
  Decide: correct to 768, or document Matryoshka truncation intent. Apply fix in
  both the ADR and the actual config before Phase 1 seeding.

### Structural issues (address before `/system-design`)
- [ ] **F2 — Phase 0 `tutor_start_session` "long-running" rationale.** Scope and
  architecture agree on behaviour (≤1s return) but disagree on *why*. Update
  ADR-008 rationale to say "architected as long-running for Phase-1 forward
  compatibility," not "currently does Graphiti read."
- [ ] **F3 — stdio child-process session scope.** In-memory session dict lives
  inside a stdio child; Claude Desktop spawns a fresh child per conversation,
  so `tutor_session_status` across conversations will fail. Add an explicit
  behavioural note in ADR-008 or ADR-014 and a demo-script constraint: do not
  close-and-reopen the stdio connection mid-session on 16 May.
- [ ] **F4 — AWS region framing in ADR-015.** "UK-adjacent" is inaccurate if
  the region is us-east-1 / us-west-2. Confirm whether eu-west-2 (London)
  supports Bedrock Custom Model Import for Gemma 4 31B; rewrite ADR-015 to
  reflect actual region and acknowledge residency posture as a Phase-3 concern
  if the demo lands in a US region.
- [ ] **F5 — Shared Kernel A: Subject enum value shape.** `Subject.ENGLISH_LANGUAGE = "English Language"`
  works for display but is hostile to Graphiti group IDs (`subject:gcse-english`)
  and JSON stability. Decide between slug-style values or a separate `.slug`
  property. Defer the *decision* to `/system-design` but record the constraint
  here so `/system-design` picks it up.

### Smaller observations (record, don't necessarily action now)
- [ ] **O1 — ADR-013 gamification middleware integration seam.** Make the
  CompositeBackend route-based-permissions insertion point explicit so
  FEAT-PO-007 inherits the awareness.
- [ ] **O2 — ASSUM-007 Bedrock contingency.** Add a written contingency: if
  FEAT-PO-004 (Tue 22 Apr) shows Bedrock doesn't support Gemma 4 31B natively,
  which of the three DEC-07 workloads on GB10 gets squeezed? Decide this now,
  not at 3am on 11 May.
- [ ] **O3 — ADR-003 turn-level Coach feedback loss on abnormal termination.**
  Currently framed as single-event loss; in practice every active-turn
  observation is at risk. Flag for revisit during Phase 1 testing if real MCP
  disconnects are observed.
- [ ] **O4 — Diagram node budget (presentation nit).** system-context.md and
  container.md are "well under the 30-node threshold." Consider using more of
  the budget for the hackathon submission so judges unfamiliar with the stack
  don't have to zoom.
- [ ] **O5 — Graphiti seeding decision.** Reviewer agrees with the existing
  handoff: do NOT seed domain-model.md / system-context.md / container.md /
  assumptions.yaml as `full_doc`. Keep Graphiti as decision record, disk as
  reference library. Record this as a confirmed decision.

## Acceptance Criteria

- [ ] Every finding (F1–F5, O1–O5) has an explicit triage outcome:
      **accept / defer / reject** with rationale.
- [ ] For each accepted finding, a follow-up action is recorded — either an
      ADR edit, a config edit, a new implementation task created via
      `/task-create`, or a captured note with a clear destination (which file,
      which section).
- [ ] F1 (embedding dimension) either has a follow-up implementation task
      created OR is applied inline — this is a hard bug and must not be left
      as a note only.
- [ ] F4 (AWS region) includes a concrete verification step: check whether
      eu-west-2 Bedrock Custom Model Import supports Gemma 4 31B.
- [ ] A decision is recorded on whether `/system-design` can proceed (the
      reviewer's recommendation is **yes, after F1–F4**); if any newly
      surfaced finding changes that, the go/no-go is captured explicitly.
- [ ] Findings deferred to `/system-design` (at minimum F5) are listed in a
      single place so the `/system-design` prompt inherits them.

## Test Requirements

Not applicable — this is an analysis/decision task, not an implementation task.
Verification is via the decision log and the spawned follow-up tasks.

## Implementation Notes

Use `/task-review TASK-REV-C7D1 --mode=architectural` to execute. Expected
outputs:

1. **Decision log** appended to this task file (accept / defer / reject per
   finding, with rationale).
2. **Spawned implementation tasks** for each accepted finding requiring code
   or config changes. Likely tasks:
   - Fix ADR-007 + `.guardkit/graphiti.yaml` embedding dimensions (F1)
   - Edit ADR-008 rationale + add stdio-scope behavioural note (F2, F3)
   - Update ADR-015 region framing + verify eu-west-2 Bedrock availability (F4)
   - Edit ADR-013 to make CompositeBackend seam explicit (O1)
   - Add ASSUM-007 contingency to the Phase 0 build plan (O2)
3. **Carry-forward note** for `/system-design` listing items deferred there
   (F5, and any others).
4. **Go/no-go statement** on proceeding to `/system-design` Sunday morning.

## Test Execution Log

_Not applicable — analysis task. Verification is via the decision log below._

## Decision Log (populated by `/task-review` on 2026-04-19)

Full report: [.claude/reviews/TASK-REV-C7D1-review-report.md](../../.claude/reviews/TASK-REV-C7D1-review-report.md)

### Structural issues (pre-`/system-design`)

- **F1 — Embedding dimension mismatch.** **ACCEPT (spawn task).**
  Verified at `.guardkit/graphiti.yaml:14` and ADR-ARCH-007:52. nomic-embed-text-v1.5
  is natively 768-dim; no Matryoshka intent documented. Hard bug — blocks Phase 1
  seeding. Spawned as `TASK-PO-FIX-EMBED-DIM`.

- **F2 — `tutor_start_session` "long-running" rationale.** **ACCEPT (ADR-008 edit).**
  Verified at ADR-ARCH-008:37. Bundled with F3 as `TASK-PO-ADR008-SESSION-SCOPE`.

- **F3 — stdio child-process session scope.** **ACCEPT (ADR-008 behavioural note).**
  Verified at container.md:31 + assumptions.yaml ASSUM-003:45-53. Bundled with F2.

- **F4 — ADR-015 AWS region framing.** **ACCEPT (verify + edit).**
  Verified: ADR-ARCH-015:62 ("UK-adjacent") vs ASSUM-007:99-116 ("us-east-1 or
  us-west-2"). Spawned as `TASK-PO-ADR015-REGION`; verification step folds into
  FEAT-PO-004 on 22 April.

- **F5 — Subject enum value shape.** **DEFER to `/system-design`.**
  Verified at domain-model.md:366-368 vs ADR-014:38. Contract-shape decision, not
  architecture. Recorded in the carry-forward section of the review report so
  `/system-design` picks it up.

### Smaller observations

- **O1 — ADR-013 middleware integration seam.** **ACCEPT (one-line edit).**
  Spawned as `TASK-PO-ADR013-MIDDLEWARE-SEAM`.

- **O2 — ASSUM-007 Bedrock contingency.** **ACCEPT (user decision + capture).**
  Spawned as `TASK-PO-ASSUM007-CONTINGENCY`. Owner: user (priority ordering of the
  three DEC-07 GB10 workloads if Bedrock is out).

- **O3 — ADR-003 turn-level Coach feedback loss framing.** **DEFER (Phase 1 watch-list).**
  Verified at ADR-ARCH-003:74-76. Reviewer's own guidance: revisit if Phase 1
  testing sees real MCP disconnects.

- **O4 — Diagram node budget.** **DEFER (pre-submission polish).**
  Folds into FEAT-PO-005 submission write-up, not `/system-design`.

- **O5 — Graphiti seeding decision (do not seed reference prose).** **ACCEPT (record DEC).**
  Spawned as `TASK-PO-DEC09-NO-SEED-REF-DOCS` (actual DEC-NN to be allocated in
  `decisions-log-2026-04-17.md`).

### Go / No-Go on `/system-design`

**GO** to `/system-design` on Sunday morning, conditional on F1–F4 being applied first.
F1 is the only hard blocker; F2–F4 are low-effort ADR edits that prevent downstream
misframing. F5 is correctly scoped for `/system-design` (carry-forward noted). No new
finding surfaced during triage that changes the reviewer's original recommendation.

### Carry-Forward to `/system-design`

- **F5 — Subject enum value shape:** decide slug-style values vs `.slug` property vs
  display-map approach. Constraint: must align with ADR-014 `subject:gcse-english`
  group-ID convention without a per-MCP-call translation step.
