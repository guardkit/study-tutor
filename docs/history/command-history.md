and is this command complete and correct for these locations:
/system-arch \
  --from docs/research/ideas/phase-0-scope.md \
  --context docs/research/ideas/phase-0-build-plan.md \
  --context docs/research/ideas/decisions-log-2026-04-17.md \
  --context docs/research/ideas/state-of-the-project-and-phase-recommendation.md \
  --context docs/research/ideas/deepagents-patterns-review.md \
  --context /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md


All six referenced files exist, so the command will resolve. But two things to flag:

1. You're missing two context flags. You pasted the preview version at phase-0-build-plan.md:99-107 — marked "don't run it yet, want domain docs drafted first." The actual invocation at phase-0-build-plan.md:332-340 adds the two FEAT-PO-001 outputs, which is why this is the one to use now:


/system-arch \
  --from docs/research/ideas/phase-0-scope.md \
  --context docs/research/ideas/phase-0-build-plan.md \
  --context docs/research/ideas/decisions-log-2026-04-17.md \
  --context docs/research/ideas/state-of-the-project-and-phase-recommendation.md \
  --context docs/research/ideas/deepagents-patterns-review.md \
  --context /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md \
  --context domains/gcse-english/GOAL.md \
  --context docs/gamification/design.md
2. Relative paths require CWD = repo root. Five of the flags are relative (docs/..., domains/...), so run this from /Users/richardwoollcott/Projects/appmilla_github/study-tutor/, not from inside docs/research/ideas/. The one absolute path (specialist-agent) is fine either way.

The Coach criteria YAML isn't referenced as context here — that's correct; it's a skeleton and /system-arch doesn't need it.

/system-arch \
  --from docs/research/ideas/phase-0-scope.md \
  --context docs/research/ideas/phase-0-build-plan.md \
  --context docs/research/ideas/decisions-log-2026-04-17.md \
  --context docs/research/ideas/state-of-the-project-and-phase-recommendation.md \
  --context docs/research/ideas/deepagents-patterns-review.md \
  --context /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/docs/reference/cross-agent-lessons-from-specialist-agent.md \
  --context domains/gcse-english/GOAL.md \
  --context docs/gamification/design.md

  All 21 artefacts written (5 top-level + 16 ADRs; 2543 lines total).

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ARCHITECTURE DOCUMENTATION CREATED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


docs/architecture/
├── ARCHITECTURE.md                    (11 KB — index + summary)
├── domain-model.md                    (20 KB — bounded contexts, aggregates, events)
├── system-context.md                  (4.8 KB — C4 Level 1 Mermaid)
├── container.md                       (6.8 KB — C4 Level 2 Mermaid)
├── assumptions.yaml                   (11 KB — 18 assumptions)
└── decisions/
    ├── ADR-ARCH-001-ddd-structural-pattern.md
    ├── ADR-ARCH-002-three-layer-architecture.md
    ├── ADR-ARCH-003-async-graphiti-writeback.md
    ├── ADR-ARCH-004-python-deepagents-langchain-mcp-stack.md
    ├── ADR-ARCH-005-defer-dockerfile-to-phase-1.md
    ├── ADR-ARCH-006-dual-inference-path-ollama-bedrock.md
    ├── ADR-ARCH-007-graphiti-split-topology.md
    ├── ADR-ARCH-008-mcp-only-agent-access.md
    ├── ADR-ARCH-009-six-parity-surfaces-as-crosscutting.md
    ├── ADR-ARCH-010-pydantic-at-boundary-validation.md
    ├── ADR-ARCH-011-no-caching-rate-limiting-feature-flags-phase-0.md
    ├── ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md
    ├── ADR-ARCH-013-middleware-level-gamification-engine-future.md
    ├── ADR-ARCH-014-single-user-scalability-posture.md
    ├── ADR-ARCH-015-uk-on-device-data-residency.md
    └── ADR-ARCH-016-may-18-deadline-as-architectural-constraint.md
Graphiti seeding (Phase 4)
Graphiti is available (583 episodes already indexed). Proposed seeding plan:


# Architecture context (domain model + summary) → project_architecture
guardkit graphiti add-context docs/architecture/domain-model.md \
  --group project_architecture

guardkit graphiti add-context docs/architecture/ARCHITECTURE.md \
  --group project_architecture

guardkit graphiti add-context docs/architecture/system-context.md \
  --group project_architecture

guardkit graphiti add-context docs/architecture/container.md \
  --group project_architecture

guardkit graphiti add-context docs/architecture/assumptions.yaml \
  --group project_architecture

# All 16 ADRs → architecture_decisions
guardkit graphiti add-context docs/architecture/decisions/ \
  --group architecture_decisions
The 16 ADRs contain no secrets or raw unsanitised user input — the guardkit graphiti add-context CLI applies its own sanitisation during upload. Free-text has been paraphrased from source docs throughout.

Run these seeding commands now? [Y/n]

If Y, I'll execute each in sequence and report the updated episode counts. If n, the markdown artefacts are complete and queryable locally, and you can seed later with the same commands.

Your call:

Y
Executing seeding. This may take several minutes because Graphiti uses Gemini for per-chunk entity extraction (~1–3s per call).

All 16 ADRs seeded successfully. No failures, no manual retries needed.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
GRAPHITI SEEDING COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Artefact	Episodes	Nodes	Edges
ARCHITECTURE.md (project_overview)	1	31	49
ADR-ARCH-001 DDD structural pattern	1	20	22
ADR-ARCH-002 Three-layer architecture	1	12	13
ADR-ARCH-003 Async Graphiti write-back	1	12	9
ADR-ARCH-004 Python/deepagents/langchain/mcp stack	1	27	42
ADR-ARCH-005 Defer Dockerfile	1	20	22
ADR-ARCH-006 Dual inference path	1	18	23
ADR-ARCH-007 Graphiti split topology	1	12	12
ADR-ARCH-008 MCP-only agent access	1	30	44
ADR-ARCH-009 Six parity surfaces	1	15	14
ADR-ARCH-010 Pydantic-at-boundary	1	35	67
ADR-ARCH-011 No caching/rate-limit/flags	1	7	4
ADR-ARCH-012 deepagents 0.5.3 AsyncSubAgent	1	27	45
ADR-ARCH-013 Middleware gamification (future)	1	12	10
ADR-ARCH-014 Single-user scalability	1	9	8
ADR-ARCH-015 UK on-device residency	1	17	24
ADR-ARCH-016 18 May deadline	1	26	27
Total from this session	17	330	435
Graphiti total episodes: 732 (was 583 before /system-arch).

The four supplementary artefacts (domain-model.md, system-context.md, container.md, assumptions.yaml) are on disk and queryable locally but not yet seeded to Graphiti. /system-design and /system-plan will be able to query the architecture decisions and overview via Graphiti; they'll read the C4 diagrams and domain-model.md directly from disk.

Optional: seed the four supplementary artefacts as full_doc if you want richer Graphiti coverage? Most likely not worth it — the ADRs already encode the key decisions, and domain-model.md is a 500-line reference doc that's more useful as a file-system read.

/system-arch complete
Next steps:

Review docs/architecture/ARCHITECTURE.md — index + summary
Design API contracts: /system-design --from docs/architecture/ARCHITECTURE.md --context docs/research/ideas/phase-0-scope.md --context docs/research/ideas/phase-0-build-plan.md
Then /system-plan and per-feature /feature-spec → /feature-plan → autonomous build or task-work
Per the Phase 0 build plan, recommended timing for /system-design is Saturday evening 19 April or Sunday morning after domain docs are drafted — the architecture now has the context it needs.


/task-create please create a review task to analyse the feedback from claude desktop in /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/reviews/architecture/claude-desktop-review-system-arch-output.md
Bash Check task and review directories
IN
ls /Users/richardwoollcott/Projects/appmilla_github/study-tutor/tasks/ 2>/dev/null && ls /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/reviews/architecture/ 2>/dev/null

OUT
backlog
blocked
completed
in_progress
in_review
claude-desktop-review-system-arch-output.md
Read claude-desktop-review-system-arch-output.md
Bash List existing tasks
IN
ls -la /Users/richardwoollcott/Projects/appmilla_github/study-tutor/tasks/backlog/ /Users/richardwoollcott/Projects/appmilla_github/study-tutor/tasks/in_progress/ /Users/richardwoollcott/Projects/appmilla_github/study-tutor/tasks/completed/ 2>/dev/null

OUT
/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tasks/backlog/:
total 0
drwxr-xr-x@ 2 richardwoollcott  staff   64 Apr 18 21:27 .
drwxr-xr-x@ 7 richardwoollcott  staff  224 Apr 18 21:27 ..

/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tasks/completed/:
total 0
drwxr-xr-x@ 2 richardwoollcott  staff   64 Apr 18 21:27 .
drwxr-xr-x@ 7 richardwoollcott  staff  224 Apr 18 21:27 ..

/Users/richardwoollcott/Projects/appmilla_github/study-tutor/tasks/in_progress/:
total 0
drwxr-xr-x@ 2 richardwoollcott  staff   64 Apr 18 21:27 .
drwxr-xr-x@ 7 richardwoollcott  staff  224 Apr 18 21:27 ..
Empty backlog. Creating the review task file now.

Write TASK-REV-C7D1-analyze-claude-desktop-arch-review.md
134 lines
---
id: TASK-REV-C7D1
title: Analyze Claude Desktop architecture review feedback
status: backlog
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

_Populated by `/task-review`._
Task created — stopping here as the command instructs.


✅ Task Created: TASK-REV-C7D1

📋 Task Details
Title: Analyze Claude Desktop architecture review feedback
Type: review (decision_required: true)
Priority: high
Status: backlog

REVIEW TASK DETECTED — use /task-review (not /task-work)
Next steps:

Run /task-review TASK-REV-C7D1 --mode=architectural to triage each finding (F1–F5, O1–O5).
Expect spawned implementation tasks for F1 (embedding dim), F2/F3 (ADR-008 edits), F4 (region/Bedrock verify), plus ADR-013/ASSUM-007 edits.
F5 (Subject enum) is explicitly flagged for carry-forward into /system-design.
Close with /task-complete TASK-REV-C7D1.
The one hard bug (embedding dimension 1024→768) is called out in acceptance criteria so it cannot be left as a note.

/task-review TASK-REV-C7D1 --mode=architectural


REVIEW COMPLETE: TASK-REV-C7D1 — Analyze Claude Desktop architecture review feedback

Outcome: .claude/reviews/TASK-REV-C7D1-review-report.md · task moved backlog → in_review.

Triage summary:

Accept	Defer	Reject
Structural (F1–F5)	F1, F2, F3, F4	F5	—
Observations (O1–O5)	O1, O2, O5	O3, O4	—
Go / No-Go: GO to /system-design Sunday morning, conditional on F1–F4 being applied first. F1 is the only hard blocker; F2–F4 are low-effort ADR edits. F5 is the single carry-forward into /system-design.

Six implementation tasks proposed (two waves):

Wave 1 — blocks /system-design:

TASK-PO-FIX-EMBED-DIM — Fix embedding_dimensions 1024→768 in ADR-007 + .guardkit/graphiti.yaml (F1)
TASK-PO-ADR008-SESSION-SCOPE — Edit ADR-ARCH-008 for tutor_start_session rationale + stdio session scope note (F2 + F3)
TASK-PO-ADR015-REGION — Verify eu-west-2 Bedrock Gemma 4 31B availability + rewrite ADR-ARCH-015 framing (F4; folds into FEAT-PO-004 on 22 Apr)
Wave 2 — non-blocking:
4. TASK-PO-ADR013-MIDDLEWARE-SEAM — One-line edit to ADR-ARCH-013 (O1)
5. TASK-PO-ASSUM007-CONTINGENCY — Capture Bedrock-out workload priority ordering (O2; user decision needed)
6. TASK-PO-DEC09-NO-SEED-REF-DOCS — Record DEC-NN in decisions-log (O5)

Decision Options:

[A]ccept — Approve findings; archive review. No subtasks auto-created; you'd handle the six edits however you prefer.
[R]evise — Request deeper analysis on specific findings.
[I]mplement — Auto-create the six subtasks under tasks/backlog/claude-desktop-review-fixes/ with IMPLEMENTATION-GUIDE + README, ready to run.
[C]ancel — Discard review, return task to backlog.
Your choice [A/R/I/C]?

TASK-REV-C7D1-review-report.md
I
You chose [I]mplement. Before creating files, a quick Context B clarification — the review is explicit enough that most defaults are sensible, so I'll propose a plan rather than walk through each question.

Proposed Implementation Configuration

Setting	Value	Why
Feature slug	claude-desktop-review-fixes	Derived from task title
Feature folder	tasks/backlog/claude-desktop-review-fixes/	Subfolder per [I]mplement convention
Approach	Single approach (already specified per-task in the review)	No alternatives proposed
Execution	Wave 1 parallel (3 tasks), Wave 2 parallel (3 tasks). Conductor-optional — tasks are small enough that sequential is also fine.	Wave 1 edits 3 different ADRs + 1 config = no file conflicts
Testing depth	Minimal (no production code touched; docs + one YAML config)	All six are doc/config edits; task 1 has one testable invariant (YAML value = 768)
Workspace names	cdr-fix-{1..6} if Conductor used, else none	Short, grep-able
Provenance	parent_review: TASK-REV-C7D1, feature_id: FEAT-CDR-C7D1 on every subtask	Enables traceability back to this review
Deviations from defaults worth flagging:

I'm not inserting the standard /task-work quality gates (phase 2.5 arch review, phase 4 test coverage) for docs-only tasks 2, 4, 6 — they'd fail the ≥80% coverage gate trivially because there's nothing to cover. Tagged as mode=direct instead.
Task 5 (O2 Bedrock contingency) is gated on a user decision I can't make; it's created in backlog but with an explicit "owner decision needed" note so it isn't picked up by autonomous build flows.
Confirm to proceed [Y/n]? Or tell me what to change (e.g. "make them all task-work", "skip task 5", "use Conductor").

[I]mplement complete.

Created tasks/backlog/claude-desktop-review-fixes/ with:

README.md — problem, solution, subtask summary
IMPLEMENTATION-GUIDE.md — wave-by-wave plan with suggested wording for each ADR edit
TASK-CDR-001 — F1, dim 1024→768 (task-work, complexity 2, Wave 1 blocker)
TASK-CDR-002 — F2+F3, ADR-008 edits (direct, complexity 2, Wave 1)
TASK-CDR-003 — F4, region verify + ADR-015 rewrite (task-work, complexity 3, Wave 1)
TASK-CDR-004 — O1, one-line ADR-013 edit (direct, complexity 1, Wave 2)
TASK-CDR-005 — O2, Bedrock contingency (user decision required, Wave 2)
TASK-CDR-006 — O5, record DEC-NN (direct, complexity 1, Wave 2)
Every subtask carries parent_review: TASK-REV-C7D1 and feature_id: FEAT-CDR-C7D1 for traceability. Parent review stays at tasks/in_review/TASK-REV-C7D1-...md with a full decision log appended and review report at .claude/reviews/TASK-REV-C7D1-review-report.md.

Next steps:

Run /task-work TASK-CDR-001 (the only real quality-gated task) when ready
Handle TASK-CDR-002 / TASK-CDR-003 / TASK-CDR-004 / TASK-CDR-006 as direct doc edits (no workflow overhead needed)
Come back to TASK-CDR-005 with the workload-priority decision before the 22 Apr Bedrock check
Kick off /system-design once Wave 1 is done

/task-review TASK-REV-C7D1 --mode=architectural

REVIEW COMPLETE: TASK-REV-C7D1 — Analyze Claude Desktop architecture review feedback

Outcome: .claude/reviews/TASK-REV-C7D1-review-report.md · task moved backlog → in_review.

Triage summary:

Accept	Defer	Reject
Structural (F1–F5)	F1, F2, F3, F4	F5	—
Observations (O1–O5)	O1, O2, O5	O3, O4	—
Go / No-Go: GO to /system-design Sunday morning, conditional on F1–F4 being applied first. F1 is the only hard blocker; F2–F4 are low-effort ADR edits. F5 is the single carry-forward into /system-design.

Six implementation tasks proposed (two waves):

Wave 1 — blocks /system-design:

TASK-PO-FIX-EMBED-DIM — Fix embedding_dimensions 1024→768 in ADR-007 + .guardkit/graphiti.yaml (F1)
TASK-PO-ADR008-SESSION-SCOPE — Edit ADR-ARCH-008 for tutor_start_session rationale + stdio session scope note (F2 + F3)
TASK-PO-ADR015-REGION — Verify eu-west-2 Bedrock Gemma 4 31B availability + rewrite ADR-ARCH-015 framing (F4; folds into FEAT-PO-004 on 22 Apr)
Wave 2 — non-blocking:
4. TASK-PO-ADR013-MIDDLEWARE-SEAM — One-line edit to ADR-ARCH-013 (O1)
5. TASK-PO-ASSUM007-CONTINGENCY — Capture Bedrock-out workload priority ordering (O2; user decision needed)
6. TASK-PO-DEC09-NO-SEED-REF-DOCS — Record DEC-NN in decisions-log (O5)

Decision Options:

[A]ccept — Approve findings; archive review. No subtasks auto-created; you'd handle the six edits however you prefer.
[R]evise — Request deeper analysis on specific findings.
[I]mplement — Auto-create the six subtasks under tasks/backlog/claude-desktop-review-fixes/ with IMPLEMENTATION-GUIDE + README, ready to run.
[C]ancel — Discard review, return task to backlog.
Your choice [A/R/I/C]?

TASK-REV-C7D1-review-report.md
I
You chose [I]mplement. Before creating files, a quick Context B clarification — the review is explicit enough that most defaults are sensible, so I'll propose a plan rather than walk through each question.

Proposed Implementation Configuration

Setting	Value	Why
Feature slug	claude-desktop-review-fixes	Derived from task title
Feature folder	tasks/backlog/claude-desktop-review-fixes/	Subfolder per [I]mplement convention
Approach	Single approach (already specified per-task in the review)	No alternatives proposed
Execution	Wave 1 parallel (3 tasks), Wave 2 parallel (3 tasks). Conductor-optional — tasks are small enough that sequential is also fine.	Wave 1 edits 3 different ADRs + 1 config = no file conflicts
Testing depth	Minimal (no production code touched; docs + one YAML config)	All six are doc/config edits; task 1 has one testable invariant (YAML value = 768)
Workspace names	cdr-fix-{1..6} if Conductor used, else none	Short, grep-able
Provenance	parent_review: TASK-REV-C7D1, feature_id: FEAT-CDR-C7D1 on every subtask	Enables traceability back to this review
Deviations from defaults worth flagging:

I'm not inserting the standard /task-work quality gates (phase 2.5 arch review, phase 4 test coverage) for docs-only tasks 2, 4, 6 — they'd fail the ≥80% coverage gate trivially because there's nothing to cover. Tagged as mode=direct instead.
Task 5 (O2 Bedrock contingency) is gated on a user decision I can't make; it's created in backlog but with an explicit "owner decision needed" note so it isn't picked up by autonomous build flows.
Confirm to proceed [Y/n]? Or tell me what to change (e.g. "make them all task-work", "skip task 5", "use Conductor").

Y

[I]mplement complete.

Created tasks/backlog/claude-desktop-review-fixes/ with:

README.md — problem, solution, subtask summary
IMPLEMENTATION-GUIDE.md — wave-by-wave plan with suggested wording for each ADR edit
TASK-CDR-001 — F1, dim 1024→768 (task-work, complexity 2, Wave 1 blocker)
TASK-CDR-002 — F2+F3, ADR-008 edits (direct, complexity 2, Wave 1)
TASK-CDR-003 — F4, region verify + ADR-015 rewrite (task-work, complexity 3, Wave 1)
TASK-CDR-004 — O1, one-line ADR-013 edit (direct, complexity 1, Wave 2)
TASK-CDR-005 — O2, Bedrock contingency (user decision required, Wave 2)
TASK-CDR-006 — O5, record DEC-NN (direct, complexity 1, Wave 2)
Every subtask carries parent_review: TASK-REV-C7D1 and feature_id: FEAT-CDR-C7D1 for traceability. Parent review stays at tasks/in_review/TASK-REV-C7D1-...md with a full decision log appended and review report at .claude/reviews/TASK-REV-C7D1-review-report.md.

Next steps:

Run /task-work TASK-CDR-001 (the only real quality-gated task) when ready
Handle TASK-CDR-002 / TASK-CDR-003 / TASK-CDR-004 / TASK-CDR-006 as direct doc edits (no workflow overhead needed)
Come back to TASK-CDR-005 with the workload-priority decision before the 22 Apr Bedrock check
Kick off /system-design once Wave 1 is done

all tasks implemented

✅ TASK-CDR-004 Completed

  File organization:
  - tasks/in_review/TASK-CDR-004-adr013-middleware-seam.md →
  tasks/completed/TASK-CDR-004/TASK-CDR-004.md
  - Acceptance criteria checked off in frontmatter/metadata (status: completed,
  completed: 2026-04-19)

  Graphiti capture: Task outcome queued to guardkit__task_outcomes.

  State transition: IN_REVIEW → COMPLETED. Parent-review finding O1 (ADR-013 missing
   ADR-012 insertion-point link) resolved. Wave 2 remaining in FEAT-CDR-C7D1:
  TASK-CDR-005 (user decision) and TASK-CDR-006 (in_review).

  Git commit of state files skipped — no docs/state/TASK-CDR-004/ artifacts were
  produced (doc-only micro task), and I don't commit without explicit user request.

✻ Cogitated for 57s

※ recap: Completed TASK-CDR-004 (Wave 2 of Claude Desktop review fixes): added the
  ADR-012 CompositeBackend seam reference to ADR-013 and moved the task to
  completed. Next: decide TASK-CDR-005 (GB10 workload trade-off) before 22 Apr.
  (disable recaps in /config)


Decision recorded in
  tasks/in_review/claude-desktop-review-fixes/TASK-CDR-005-assum007-contingency.md:
  - Priority 1 (non-negotiable): architect-agent training for DDD Southwest 16 May
  - Priority 2 (squeezed if needed): study-tutor re-fine-tune (18 Apr checkpoint is
  shippable)
  - Priority 3 (squeezed first): training-dataset expansion (waiting on more GCSE
  books)
  - Side decision: Bedrock hosting order = study-tutor first, architect second

  Doc edits landed:
  - docs/architecture/assumptions.yaml — ASSUM-007 revisit_trigger now names the
  priority ordering and explains the input-bound coupling.
  - docs/research/ideas/phase-0-build-plan.md — Bedrock-out contingency callout added
  under the Monday 21 April FEAT-PO-004 setup section, so it's in your face during the
   verification window.

  Task state: moved to in_review. All three acceptance criteria met (decision
  recorded, ASSUM-007 names the priority, build plan references the contingency).
  Ready for /task-complete TASK-CDR-005 when you've reviewed the wording.


TASK-CDR-006 — COMPLETED

  - Files organized: tasks/completed/TASK-CDR-006/TASK-CDR-006.md
  - State transition: IN_REVIEW → COMPLETED (frontmatter updated with completion
  date + location)
  - Graphiti capture (MCP, via deferred-tool load):
    - guardkit__task_outcomes — task completion episode
    - guardkit__project_decisions — DEC-09 decision episode

  Summary of work shipped:
  - Added DEC-09 "Reference prose stays on disk; Graphiti holds decisions only" to
  docs/research/ideas/decisions-log-2026-04-17.md, naming the four files
  (domain-model.md, system-context.md, container.md, assumptions.yaml) and
  referencing TASK-REV-C7D1 observation O5.
  - Updated intro line DEC-01 through DEC-08 → DEC-01 through DEC-09.


please implement FEAT-PO-002
FEAT-PO-002 is the weekend-scale critical-path feature (~9 hrs of planned work per phase-0-build-plan.md:82): full Python package scaffold, MCP adapter with 4 tools, LLM provider abstraction (Ollama + Bedrock), tutor session state, six parity surfaces, CLI, and tests. The build plan itself tags it "Reviewer-in-loop … critical path, parity surfaces" — not a single-shot autonomous build.

Before I start, pick a lane:

GuardKit-native (recommended): I run /feature-plan FEAT-PO-002 to break it into reviewable tasks, then we work them one by one via /task-work with you reviewing each. Matches the plan's stated reviewer-in-loop guidance and the workflow in .claude/CLAUDE.md.
One-shot implementation: I implement the full weekend plan in one go right now — scaffold, MCP adapter, LLM client, session, tests, parity surfaces. Faster but you'll be reviewing a very large diff with no checkpoints, and MCP/Ollama wiring genuinely needs a local smoke test I can't run for you.
Scaffold only: I lay down pyproject.toml, directory skeleton, .env.example, .mcp.json, empty modules per the "Files changed" table at phase-0-build-plan.md:428, and you drive the substantive code yourself with /task-work.
Which lane? My recommendation is (1) given the critical-path flag and the number of judgment calls (provider-resolution rules, SR-01–SR-07 parity-surface choices, role manifest shape) that benefit from your sign-off before code lands.

1
feature-plan skill
Starting Context A clarification (review scope), then creating the review task and running the decision analysis.

Agent:Context A: review scope clarification
IN
Execute clarification for feature planning.

CONTEXT TYPE: review_scope

FEATURE: FEAT-PO-002 — Fine-tuned English tutoring runtime over local deployment

FEATURE BACKGROUND (authoritative context the user already has in their repo):
- Roadmap entry: docs/product/roadmap/roadmap.md:102 ("FEAT-PO-002: Fine-tuned English tutoring runtime over local deployment")
- Bounded Context: Tutoring Runtime BC
- Depends on: FEAT-PO-001 (domain config — not yet built either)
- Detailed build plan already exists: docs/research/ideas/phase-0-build-plan.md (the user currently has this open in their IDE)
- Complexity: 6/10 per the build plan ranking
- Scope summary: Python package scaffold (pyproject.toml, src/study_tutor/), MCP adapter with 4 tools (tutor_start_session, tutor_turn, tutor_status, tutor_end_session), LLM provider abstraction (Ollama local + AWS Bedrock Custom Model Import), tutor session state management, CLI entry point, role manifest (roles/tutor/), .mcp.json, .env.example, six parity surfaces (SR-01 to SR-07) including stdio discipline and provider-resolution rules, unit tests for stdio discipline and provider resolution

ESTIMATED COMPLEXITY: 6/10

FLAGS:
  --no-questions: false
  --with-questions: false
  --defaults: false
  --answers: (none)

SPECIAL NOTE: This feature already has a highly detailed hour-by-hour build plan in docs/research/ideas/phase-0-build-plan.md. The review focus should arguably be narrower than a typical greenfield review — the technical options are largely decided (Python, MCP SDK, Ollama, Bedrock). The open questions are more about task decomposition granularity, review cadence, and whether to lock to the existing plan or reopen technical options.

Ask the user about:
1. Review focus — given the existing detailed plan, is the review confirming the plan (light) or re-evaluating options (full)?
2. Trade-off priority (speed to weekend demo vs. code quality vs. learnings)
3. Any specific concerns to address (parity surfaces, provider abstraction, MCP transport, etc.)

Return ClarificationContext with review preferences.
Read roadmap.md (lines 96-125)
The clarifier has three questions. I'll present them and wait for your answers before proceeding.

CLARIFICATION — FEAT-PO-002 Review Scope

The plan in phase-0-build-plan.md is unusually detailed, so the questions are about how the review relates to it — not re-litigating decisions already made.

Q1 — Review stance

A — Confirm the plan (light). Build plan authoritative. Review checks consistency, produces a task breakdown mirroring the plan. No tech options reopened.
B — Confirm + targeted spot-checks. Authoritative for most, but validate 2–3 thin assumptions (e.g. LiteLLM proxy risk, SR-01 stdio impl, Bedrock region).
C — Full re-evaluation. Plan is one input, not the answer.
D — Recommend (AI decides).
Default: B.

Q2 — Priority trade-off

Hackathon deadline is 18 May 2026; Phase 0 also underpins Phase 1.

A — Speed to demo (submittable by Wed 23 Apr). Cut anything off critical path.
B — Code quality and parity-surface rigour. SR-01–SR-07 non-negotiable.
C — Balanced (existing plan's weekend-code / weekday-ops split).
D — Recommend.
Default: C.

Q3 — Specific concerns (multi-select, comma-separated)

Parity surfaces (SR-01 stdio, SR-03 provider resolution) — correctness of specialist-agent pattern transfer
Provider abstraction — Ollama→Bedrock routing, LiteLLM-on-GB10 proxy risk
MCP transport + tool contract (tutor_start_session long-running, SR-07 description≡behaviour)
Session state design — in-memory for Phase 0, must not block Graphiti in Phase 1
Task decomposition granularity — are plan breakpoints the right GuardKit boundaries?
Bedrock ops sequencing — contingency and Mon/Tue robustness
None — standard scope review
Default: 1, 3, 5.

You can answer all three at once (e.g. B, C, 1,3,5) or accept all defaults with defaults.

accept defaults


Context A settled (B / C / 1,3,5). Creating the review task now.

Review report written to .claude/reviews/TASK-REV-PO02-review-report.md.

📋 Decision Checkpoint — TASK-REV-PO02
Approach score: 82/100 (plan is sound; -18 for residual MCP/LLM seam risk + one ambiguous-ownership file)

Key findings (3 spot-checks)
Parity tests should shift left — write test_stdio_discipline.py and test_provider_resolution.py Saturday evening at first commit, not Sunday morning. Catches SR-01/SR-03 violations 12 hours sooner.
SR-07 violation in tutor_session_end description — plan's description ("triggers async Graphiti write in Phase 1") doesn't match Phase-0 behaviour (no-op). Must say "marks session ended" in Phase 0 with a TODO(phase-1) comment.
Ollama cold-start can blow the 30s tutor_turn ceiling on first call — add a no-op warm-up generate() in tutor_start_session handler. One-line mitigation.
Decision-point resolutions (D1–D5)
D1: roles/tutor/role.yaml → FEAT-PO-002 owns structure; FEAT-PO-001 owns prompt content.
D2: Two code tests (SR-01, SR-03) + one verification-checklist subtask for SR-02/04/06/07. No per-surface over-testing.
D3: Bedrock stub only in FEAT-PO-002 (NotImplementedError); real impl in FEAT-PO-004.
D4: scripts/mcp-wrapper.sh → FEAT-PO-002 (runtime glue, not packaging).
D5: Reviewer-in-loop /task-work per plan's explicit guidance. No AutoBuild.
Proposed breakdown: 7 subtasks, 3 waves
Wave	Tasks	Parallel	Hrs
1 — Foundation	PO02-001 (scaffold), PO02-002 (role manifest)	yes	1.5
2 — Runtime	PO02-003 (LLM client), PO02-004 (session), PO02-005 (MCP+CLI+wrapper)	003+004 parallel, 005 serial	4.0
3 — Hardening	PO02-006 (parity tests), PO02-007 (smoke test)	yes	2.0
Four Integration Contracts drafted (AGENT_MODELS__REASONING_MODEL env, role manifest path, tutor session interface, LLM client interface) — ensures consumers build against fixed producer contracts.

Your choice
[A] Accept — save the 7-task plan for later, don't scaffold now
[R] Revise — re-run with different focus (e.g. Phase 1 forward-compat, or re-open tech options)
[I] Implement — I create subtask markdown files, IMPLEMENTATION-GUIDE.md with Mermaid diagrams, and .guardkit/features/FEAT-PO-002.yaml; task-work starts from TASK-PO02-001
[C] Cancel — discard
A / R / I / C?

TASK-REV-PO02-review-report.md
I

📋 Implementation Preferences (Context B)
Three quick choices before I scaffold:

Q1 — Testing depth

[T] TDD for all 7 subtasks
[S] Standard — quality gates + the two parity unit tests from the plan (default)
[M] Minimal — compilation + smoke test only
Q2 — Task frontmatter

[V] Verbose — full §4 contract block in every consumer
[L] Lean — contract block only where format is non-obvious (default)
Q3 — Implementation mode

[C] Conservative — /task-work for all 7
[M] Mixed — /task-work for the 5 substantive tasks; direct for PO02-002 (role manifest) and PO02-007 (smoke test) (default)
Reply S L M, or defaults to accept all recommendations, or override any subset (e.g. T L C).

defaults

FEAT-PO-002 planning complete.

✅ FEATURE PLANNING COMPLETE — FEAT-PO-002
Created:

tasks/backlog/feat-po-002-tutoring-runtime/ — 7 subtasks, README, IMPLEMENTATION-GUIDE with 3 Mermaid diagrams
.guardkit/features/FEAT-PO-002.yaml — structured feature file (4 waves, 7.5h estimate)
.claude/reviews/TASK-REV-PO02-review-report.md — approach score 82/100
Review task moved to in_review with status review_complete and decision: implement.

Execution plan:

Wave	Tasks	Mode	Total
1	PO02-001 (scaffold), PO02-002 (role manifest)	task-work + direct	~1.5h
2	PO02-003 (LLM client), PO02-004 (session), PO02-005 (MCP+CLI+wrapper)	task-work	~4h
3	PO02-006 (parity tests), PO02-007 (smoke test)	task-work + direct	~2h
Three review findings baked into acceptance criteria: shift-left parity tests, SR-07 tutor_session_end wording fix, Ollama cold-start warm-up.

Four Integration Contracts documented in §4 of the guide; consumer_context blocks on TASK-PO02-003 (env var) and TASK-PO02-005 (role path) where format is non-obvious.

Start implementation:


/task-work TASK-PO02-001

✅ Task Work Complete — TASK-PO02-001

  Stack: Python 3.11 (scaffolding task, complexity 3)
  Mode: Minimal (auto-detected: parent_review + complexity ≤4)
  Duration: ~10 min

  Acceptance Criteria — all passed

  ┌─────┬───────────────────────────────────────────────────────────────────────────┬────────┐
  │  #  │                                 Criterion                                 │ Status │
  ├─────┼───────────────────────────────────────────────────────────────────────────┼────────┤
  │     │ pyproject.toml with package study_tutor, Python ≥3.11, entrypoint         │        │
  │ 1   │ study-tutor = study_tutor.cli.main:serve, [providers] extra with 5        │ ✅     │
  │     │ LangChain integrations                                                    │        │
  ├─────┼───────────────────────────────────────────────────────────────────────────┼────────┤
  │ 2   │ .venv created + pip install -e '.[providers]' succeeded                   │ ✅     │
  ├─────┼───────────────────────────────────────────────────────────────────────────┼────────┤
  │ 3   │ SR-04: pip show passes for all 5 providers                                │ ✅     │
  ├─────┼───────────────────────────────────────────────────────────────────────────┼────────┤
  │ 4   │ src/study_tutor/{cli,llm,mcp,session}/__init__.py tree, empty, imports    │ ✅     │
  │     │ cleanly                                                                   │        │
  ├─────┼───────────────────────────────────────────────────────────────────────────┼────────┤
  │ 5   │ .env.example with <angle-bracket> placeholders +                          │ ✅     │
  │     │ AGENT_MODELS__REASONING_MODEL=local default (SR-06)                       │        │
  ├─────┼───────────────────────────────────────────────────────────────────────────┼────────┤
  │ 6   │ AGENTS.md with ALWAYS/NEVER/ASK for Tutor role                            │ ✅     │
  ├─────┼───────────────────────────────────────────────────────────────────────────┼────────┤
  │ 7   │ .mcp.json template with study-tutor stanza                                │ ✅     │
  ├─────┼───────────────────────────────────────────────────────────────────────────┼────────┤
  │ 8   │ .gitignore includes .venv/, .env, __pycache__/, *.pyc, dist/, build/,     │ ✅     │
  │     │ *.egg-info/                                                               │        │
  ├─────┼───────────────────────────────────────────────────────────────────────────┼────────┤
  │ 9   │ command_history.md first entry = /feature-plan FEAT-PO-002                │ ✅     │
  └─────┴───────────────────────────────────────────────────────────────────────────┴────────┘

  State transition

  BACKLOG → IN_PROGRESS → IN_REVIEW at
  tasks/in_review/feat-po-002-tutoring-runtime/TASK-PO02-001-*.md

  Next

  /task-work TASK-PO02-002 (Role manifest + player prompt shell) — Wave 1 foundation continues.

Task complete. Created the role manifest shell for TASK-PO02-002:

  - roles/tutor/role.yaml — minimal manifest mirroring specialist-agent's shape
  (role.id/name/description, player.prompt_file, coach.criteria_file). Omitted optional blocks
  (session, output, knowledge_graph, mode_inference, fleet) per the task note to not invent fields
   not obviously needed for Phase 0.
  - roles/tutor/prompts/player.md — placeholder with the FEAT-PO-001 handoff comment.
  - roles/tutor/criteria/ already existed with definitions.yaml in place (FEAT-PO-001 territory).

  Paths in role.yaml are written repo-root-relative (roles/tutor/...) per AC-5, aligning with the
  bash wrapper's cd to repo root in TASK-PO02-005.


  🎉 Task Completed — TASK-PO02-003

  State transition

  in_review → completed · moved to tasks/completed/TASK-PO02-003/TASK-PO02-003.md

  Acceptance criteria — all ✅

  - src/study_tutor/llm/client.py exposes LLMClient and _default_player_model() ✅
  - _default_player_model() reads env at call time, falls back to "local" ✅
  - LLMClient(provider).generate(prompt, system=None) -> str sync interface ✅
  - provider="local" → Ollama HTTP via httpx (configurable OLLAMA_BASE_URL / OLLAMA_MODEL) ✅
  - provider="bedrock" → NotImplementedError("Bedrock provider wired by FEAT-PO-004") with no
  boto3/langchain-aws import ✅
  - No hard-coded provider anywhere (asserted via module-source inspection test) ✅

  Quality gates

  - Tests: 7/7 passing
  - Coverage: 100% (32/32 stmts on client.py)
  - Full suite: 12/12 passing (7 new + 5 pre-existing session tests)

  Knowledge capture

  [Graphiti] Task outcome captured to knowledge graph (via MCP add_memory, queued async).

  Uncommitted changes

  - src/study_tutor/llm/client.py (new)
  - tests/unit/llm/__init__.py, tests/unit/llm/test_provider_resolution.py (new)
  - pyproject.toml (httpx dep + pytest markers)
  - tasks/completed/TASK-PO02-003/TASK-PO02-003.md (moved from tasks/in_review/)
  - Parent dir tasks/backlog/feat-po-002-tutoring-runtime/TASK-PO02-003-llm-client.md is now
  gone (moved).

  Feature rollup (FEAT-PO-002, wave 2)

  3 of 7 tasks done (PO02-001, PO02-002, PO02-003). Unblocks: TASK-PO02-005 (MCP adapter CLI
  wrapper) per the feature's dependency chain.

  Run /task-work TASK-PO02-004 (tutor-session) or TASK-PO02-005 (MCP adapter) when ready.


🎉 TASK-PO02-004 Complete

  State: IN_REVIEW → COMPLETED
  Location: tasks/completed/TASK-PO02-004/TASK-PO02-004.md

  Deliverables:
  - src/study_tutor/session/tutor_session.py — TutorSession/TutorTurn dataclasses, SessionStore,
  module-level singleton
  - tests/unit/session/test_tutor_session.py — 5/5 passing

  Quality gates: compilation ✅, tests 100% ✅ (coverage skipped per minimal intensity)

  📝 Graphiti Knowledge Capture:
  - Task outcome → guardkit__task_outcomes
  - Architectural decision (Phase 0 pure-dataclass contract) → guardkit__project_decisions

  Feature progress: FEAT-PO-002 wave 2 task complete — tutor_session module is now the session
  substrate for Phase 0; Phase 1 Graphiti writer can consume it directly without re-shaping.

  Git commit skipped (no docs/state/ files for this task, and repo state is outside the task-work
  scope).

  Task Work Complete — TASK-PO02-005

  Stack: Python (FastMCP + Click)
  Intensity: LIGHT (feature subtask, complexity 6)
  State: BACKLOG → IN_REVIEW

  Files created:
  - src/study_tutor/roles/loader.py — YAML manifest loader, paths resolved from Path.cwd()
  (SR-02 anchor)
  - src/study_tutor/mcp/adapter.py — MCPAdapter with 4 async handlers; _default_player_model()
  resolved per call (SR-03); asyncio.create_task warm-up on tutor_start_session
  - src/study_tutor/mcp/server.py — create_mcp_server() registers the 4 tools with
  SR-07-compliant descriptions
  - src/study_tutor/cli/main.py — click.group → serve subcommand; logging to stderr, banner via
  click.echo(err=True) (SR-01)
  - scripts/mcp-wrapper.sh — chmod +x; cd to absolute repo, sources .env, defaults
  AGENT_MODELS__REASONING_MODEL=local, exec's study-tutor serve
  - tests/unit/mcp/test_adapter.py — 6 smoke tests including SR-07 description check
  - README.md — claude_desktop_config.json snippet + SR-01/SR-02 rationale
  - pyproject.toml — entry point flipped to study_tutor.cli.main:cli (group)
  - .mcp.json — switched study-tutor entry to wrapper path

  Quality gates:
  - Tests: 18/18 pass (6 new + 12 existing)
  - SR-01 smoke: stdout 0 bytes after 2s serve; all output on stderr ✅
  - SR-02 smoke: wrapper invoked from /tmp — role.yaml resolved from abs repo root ✅
  - study-tutor serve --help exposes the expected flags
  - Server lists exactly 4 tools; tutor_session_end description = "Marks session ended." (no
  Graphiti leakage)

  Deferred to TASK-PO02-006: formal tests/unit/mcp/test_stdio_discipline.py parity suite.

✻ Cogitated for 6m 17s

※ recap: Goal: ship FEAT-PO-002 Phase-0 tutoring MCP runtime. Just finished TASK-PO02-005
  (adapter, CLI, bash wrapper) — 18/18 tests pass, task moved to in_review. Next: run
  /task-complete TASK-PO02-005, then start TASK-PO02-006 (stdio-discipline parity tests).
  (disable recaps in /config)

  Task Work Complete — TASK-PO02-006

  State: backlog → in_progress → in_review

  Deliverables

  - tests/unit/mcp/test_stdio_discipline.py (new, 2 tests) — spawns real study-tutor serve with stdin
  closed, asserts zero stdout bytes in the 3-s startup window and banner lands on stderr (SR-01).
  - tests/unit/llm/test_provider_resolution.py — added
  test_adapter_handlers_do_not_reference_provider_string_literals: strips docstrings/comments from
  adapter.py then greps for provider literals (local, bedrock, openai, anthropic, gemini). Closes SR-03
  gap.
  - .claude/reviews/TASK-PO02-006-parity-log.md — full parity log with commands run, output captured,
  per-SR verdict, and final Six parity surfaces: GREEN line.

  Results

  - All 21 tests pass (.venv/bin/pytest tests/).
  - SR-01 & SR-03 code-verified; SR-02/04/06/07 shell-verified; SR-05 documented pass-through.
  - One minor AC-text adjustment documented in the log: SR-02's grep '^cd /' was written for an inline
  path; the wrapper uses the idiomatic REPO_ROOT="/…"; cd "$REPO_ROOT" pattern. The log verifies the same
   invariant with grep '^REPO_ROOT="/' + no-$PWD check.
  - No drift fixed in source tasks — prior tasks shipped the parity invariants correctly.


  Gate: 🟢 GREEN — FEAT-PO-002 is submittable

  Full log at .claude/reviews/TASK-PO02-007-smoke-log.md.

  Every hard acceptance criterion in TASK-PO02-007 is met: Ollama reachable, config backed up, study-tutor registered with exactly 4 tools,
  session lifecycle clean (start → turn → end → status:ended), turn latencies ~11–13s (well under the 15s budget and the 30s acceptance
  bound), coherent tutor-appropriate responses.

  Three ⚠️ items are content-quality defects, not integration defects, and the task note explicitly says "exact content does not" matter for
   the gate. Logged as follow-ups:

  1. Quote fidelity (HIGH — priority for production). Fabricated Macbeth quotes ("mortal coats… unmaculate me" vs real "mortal thoughts…
  unsex me here"). This is the RAG-layer problem; right place to fix it, right time to sequence it — before multi-subject expansion.
  2. Truncation at ~mid-paragraph. Likely Ollama default num_predict cap. Check src/study_tutor/llm/client.py — it currently sends no
  explicit token ceiling in the payload.
  3. First-token artefact in Session 1 ("He'to manipulate"). Single occurrence, park as watch-list.
  4. Stale default in client.py:19 — gcse-tutor-gemma4-31b:Q4_K_M should be gcse-tutor-gemma4-moe:latest. .env overrides correctly so
  runtime is fine; fallback default is wrong.

  Want me to open follow-up task files for #1 and #2, or leave them in the log for now?

✻ Cooked for 1m 46s

※ recap: Implementing TASK-PO02-007 (Phase 0 end-of-Saturday smoke test for study-tutor MCP) — gate is GREEN, FEAT-PO-002 submittable. Next:
   decide whether to open follow-up task files for the quote-fidelity and truncation defects, or leave them in the log.

❯ please create the follow up tasks

 Created tasks/backlog/po02-smoke-followups/ with a README and three task files:

  ┌────────────────────────────────────┬──────────┬────────────┬────────────────────────────────────────────────────────────────────────┐
  │                Task                │ Priority │ Complexity │                                 Notes                                  │
  ├────────────────────────────────────┼──────────┼────────────┼────────────────────────────────────────────────────────────────────────┤
  │ TASK-PO02F-001 — Scope RAG         │          │            │ Scoping only; likely becomes FEAT-PO-006. Produce                      │
  │ grounding for quote fidelity       │ high     │ 5          │ docs/research/ideas/rag-grounding-design.md. Sequence before           │
  │                                    │          │            │ multi-subject expansion.                                               │
  ├────────────────────────────────────┼──────────┼────────────┼────────────────────────────────────────────────────────────────────────┤
  │ TASK-PO02F-002 — Set explicit      │          │            │ Root cause of the Macbeth mid-sentence truncation. ~10 LOC + 1 test,   │
  │ num_predict ceiling on Ollama      │ high     │ 2          │ new OLLAMA_NUM_PREDICT env var (default 2048).                         │
  │ requests                           │          │            │                                                                        │
  ├────────────────────────────────────┼──────────┼────────────┼────────────────────────────────────────────────────────────────────────┤
  │ TASK-PO02F-003 — Fix stale         │ low      │ 1 (micro)  │ Corrects client.py:18-19 defaults that reference the speculative       │
  │ DEFAULT_OLLAMA_MODEL fallback      │          │            │ gb10.tailnet host and -31b model tag.                                  │
  └────────────────────────────────────┴──────────┴────────────┴────────────────────────────────────────────────────────────────────────┘

  The Session 1 first-token artefact ("He'to manipulate") is not in a task — it's on the README's watch list. Promote to a file only if it
  recurs.

✻ Crunched for 2m 10s

※ recap: Goal was implementing TASK-PO02-007 (Claude Desktop smoke test for FEAT-PO-002); gate is GREEN and three follow-up tasks are filed
  in tasks/backlog/po02-smoke-followups/. Next action: decide whether to schedule TASK-PO02F-002 (num_predict fix) now or close out
  FEAT-PO-002 first.

  /task-work TASK-PO02F-001

  Task complete. State: backlog → in_progress → in_review.

  Deliverable: docs/research/ideas/rag-grounding-design.md

  Decision summary (all 5 acceptance criteria addressed):

  1. Corpus: Folger TEI for Shakespeare, Project Gutenberg for PD novels. In-copyright texts (An Inspector Calls — Priestley d. 1984 →
  copyright to 2055, Blood Brothers, DNA) get an analysis-mode policy — paraphrase, don't verbatim-quote. Verifier enforces.
  2. Retrieval shape: Post-hoc verification as MVP (option c), embedded-context (option b) as Phase B. Tool-call grounding (a) deferred to
  Phase C — fine-tuned Gemma 4 is not reliable enough at tool-use and the extra RTT blows the 15s budget.
  3. Indexing: Speech-level for Shakespeare, paragraph-level for prose. Flat-text + SQLite FTS5 for the verifier (ships without Graphiti
  infra); FalkorDB + nomic-embed on GB10 (reuses DEC-02 stack) for Phase B. One group_id per text.
  4. Eval: tests/quote_fidelity/golden_quotes.yaml seeded from the smoke's known fabrications (unsex me here, raven, dagger) + innocent
  flower as control. Target: fabrication rate <5% Phase A, <1% Phase B.
  5. Hand-off: 6-subtask breakdown for FEAT-PO-006, sequenced before multi-subject expansion.

  Research/scoping task — no code, no tests, no build. Quality gates don't apply; the acceptance criterion is "doc exists and decides the
  approach", which it does.


  🏁 Task Complete: TASK-PO02F-001

  📁 Files organized
    tasks/completed/TASK-PO02F-001/TASK-PO02F-001.md
    docs/research/ideas/rag-grounding-design.md (deliverable — lives in research tree)

  🔄 State: in_review → completed

  📝 Graphiti knowledge capture (via MCP)
    ✅ guardkit__task_outcomes — "Task Completion: TASK-PO02F-001"
    ✅ guardkit__project_decisions — "Decision: FEAT-PO-006 — post-hoc quote verifier as MVP"

  ⏭️  Git commit skipped
    Commit the task move + design doc manually when you're ready:
      git add tasks/completed/TASK-PO02F-001/ docs/research/ideas/rag-grounding-design.md tasks/backlog/po02-smoke-followups/
      git commit -m "Complete TASK-PO02F-001 — RAG grounding scope doc for quote fidelity"

  Next steps (handed off): promote docs/research/ideas/rag-grounding-design.md into FEAT-PO-006 via /feature-plan when you want to build the
   verifier. The 6-subtask breakdown at the bottom of the doc is ready to consume.

✻ Worked for 1m 38s

※ recap: Goal was to scope a RAG grounding layer to stop the tutor fabricating Shakespeare quotes; TASK-PO02F-001 is complete, with the
  design doc at docs/research/ideas/rag-grounding-design.md. Next: commit the task move and design doc, then promote to FEAT-PO-006 via
  /feature-plan.


/task-work TASK-PO02F-002

 Task Work Complete — TASK-PO02F-002

  State: backlog → in_review

  Changes:
  - src/study_tutor/llm/client.py: added DEFAULT_OLLAMA_NUM_PREDICT = 2048, new _resolve_num_predict() helper (SR-03
  call-time read, validates int > 0), injected options.num_predict into Ollama payload.
  - tests/unit/llm/test_provider_resolution.py: extended existing payload assertion for default (2048); added
  test_local_provider_uses_env_num_predict_at_call_time (override) and
  test_local_provider_falls_back_to_default_on_bad_num_predict (bad values fall back, not crash).
  - .env.example: documented OLLAMA_NUM_PREDICT=2048 beside the other Ollama settings.

  Tests: 23/23 pass (10/10 in the LLM suite, incl. 2 new).

  AC status:
  - ✅ num_predict added to payload (under options, per Ollama API)
  - ✅ Configurable via OLLAMA_NUM_PREDICT, default 2048, read at call time
  - ✅ Documented in .env.example
  - ✅ Unit tests assert default + override + bad-value fallback
  - ⚠️ Not verified by me: (a) live reproduction of the Macbeth truncation against the GB10 Ollama — requires network
  access to the tailnet; (b) the manual MCP stdio re-run. Both need your box. The code path is straightforward and
  unit-verified, but the "observe truncation disappears" AC is still open until you run it.

✻ Worked for 2m 33s

※ recap: Goal: raise Ollama's num_predict ceiling so GCSE essay scaffolds stop truncating. Code and unit tests are
  done (23/23 pass) and TASK-PO02F-002 is in review. Next: run the Macbeth prompt through the live MCP stdio path to
  confirm the truncation is gone.


/task-work TASK-PO02F-003

✅ TASK-PO02F-003 — Complete (in_review)

  Changes applied:
  - src/study_tutor/llm/client.py:18 — DEFAULT_OLLAMA_BASE_URL → http://localhost:11434
  - src/study_tutor/llm/client.py:19 — DEFAULT_OLLAMA_MODEL → gcse-tutor-gemma4-moe:latest
  - tests/unit/llm/test_provider_resolution.py:69,80 — arbitrary literal env values updated to localhost for consistency (test behavior
  unchanged — it still overrides env vars explicitly)

  Tests: 23/23 unit tests passing (pytest tests/unit)

  Deliberately NOT modified (per AC "historical artefacts"):
  - tasks/completed/*, .claude/reviews/*-smoke-log.md, docs/history/*, command_history.md
  - docs/research/ideas/phase-0-*.md — these reference the ~/fine-tuning/output/gcse-tutor-gemma4-31b/ training directory, which is a real
  past filesystem path (the 31B Dense LoRA run), not the serving tag. Updating would rewrite history.
  - Module docstring mention of "GB10 over Tailscale" on client.py:5 — outside AC scope; flag for the plan owner if they want a follow-up
  hygiene task.

  Task moved to tasks/in_review/po02-smoke-followups/. Ready for human review / /task-complete.


  implement phase-0-build-plan.md → Sunday 20 April → Afternoon (FEAT-PO-003)

FEAT-PO-003 Sunday afternoon tail is done. Closed the two gaps flagged in the status table and hardened .gitignore per the plan's §4.

Changes

domains/gcse-english/sources/README.md — bring-your-own-sources guide: tested (Mr Bruff) + alternatives (CGP/York Notes/Pearson/Collins), explicit AQA exclusion, directory layout, Phase 1 ingestion command (aspirational until FEAT-PO-006 lands), public/private split, troubleshooting.
docs/licensing.md — operational licensing summary: repo code (MIT), Gemma 4 base (Google terms), fine-tuned adapter/GGUF/train.jsonl (not distributed), third-party source material including AQA prohibition, runtime dependencies, downstream can/cannot.
.gitignore — added study-tutor section: domains/*/sources/**/*.pdf (+ .PDF, .epub), chroma/, chroma_data*/, train.jsonl, *.gguf, *.safetensors, models/, adapters/, merged-*/, stdio logs.
Gates passed

SR-06: .env.example uses <placeholder> form only — no real-looking secrets.
Pre-commit scan: no stray .pdf, .gguf, or .safetensors anywhere outside .venv/.
Dummy-PDF drop test: git check-ignore confirmed .gitignore:219 blocks both domains/gcse-english/sources/__dummy.pdf and a nested mrbruff/__nested.pdf.
One flag for you

The plan (17 Apr) specified Apache 2.0, but the LICENSE that actually landed on 12 Apr is MIT. I documented it as MIT and noted the discrepancy in docs/licensing.md §1 rather than silently swapping the licence — that's a call for you to make, especially before the Kaggle IP rules are read.

Not touched: docs/research/ideas/phase-0-build-plan.md (already dirty in your working tree). Once you're ready, the status-table row for FEAT-PO-003 can flip from 🟡 to ✅.

implement phase-0-build-plan.md → Sunday 20 April → Evening (FEAT-PO-005 kickoff)

I'll implement the Sunday 20 April Evening section — FEAT-PO-005 kickoff: three submission doc stubs in docs/submission/.

Let me first check for referenced context so the stubs reflect the actual submission plan.

Context confirmed — 13 required sections for the write-up (from phase-0-scope.md:267-280), 5-scene demo structure, and an empty video shell. Creating the three stubs.

Write technical-writeup.md
62 lines
# Study Tutor — Technical Write-Up

**Submission:** Gemma 4 Good Hackathon (Kaggle × Google DeepMind)
**Deadline:** 18 May 2026, 23:59 UTC
**Status:** 🔲 Stub — populated incrementally through Phases 0–2. Target feature-complete: 10 May 2026. Final polish: 17–18 May.

> This is a living document. Each section is a titled stub with a one-line note. Content is added as each phase lands so the final write-up is a synthesis, not a sprint.

---

## 1. Problem Statement

> *Lilymay, AI tutors, teenage engagement, privacy — why a 15-year-old won't open a revision tool on a Tuesday evening, and why a cloud-hosted AI tutor isn't an acceptable answer.*

## 2. Solution Overview

> *Three-layer architecture at a glance: fine-tuned Gemma 4 31B on-device (behaviour), RAG over licensed sources (knowledge), gamification layer (engagement).*

## 3. Pipeline Methodology

> *How the training data was produced — agentic dataset factory, Player–Coach adversarial generation, Unsloth fine-tuning harness. Why this yields better training data than hand-curation.*

## 4. Fine-Tuning Specifics

> *Gemma 4 31B Dense base, LoRA adapter, ShareGPT format, 75/25 `<think>` ratio, ~1,736 examples, ~2h 5min on GB10, final loss 0.7015. Training data provenance and filtering.*

## 5. Architecture

> *Phase 1 Ollama-on-GB10 runtime + Phase 2 Graphiti student model + DeepAgents Player–Coach loop + gamification state engine. Where each layer lives and how they compose.*

## 6. Gamification Design

> *Single-user engagement mechanics — personal growth over competition. XP economy, level progression, achievements, streaks, daily challenges, Boss Battle exam mode. See `docs/gamification/design.md` for the full spec.*

## 7. On-Device Deployment

> *GB10 under the desk → Ollama → GGUF Q4_K_M. Zero cloud calls in the default path. Privacy story: no student data leaves the home network.*

## 8. Bedrock Migration Path

> *AWS Bedrock Custom Model Import as the scale-to-zero fallback for demo week and multi-user scenarios. Cost profile (~$1.50–$3.00 per 5-min session), cold-start behaviour, when to route traffic where.*

## 9. Multi-Subject Expansion

> *Domain-agnostic pipeline — adding a subject is a `domains/{subject}/GOAL.md` plus a `sources/` directory, not a code change. Architecture demonstration, not Phase 0 implementation.*

## 10. Copyright and Provenance

> *Bring-your-own-sources public repo pattern. What the repo ships vs. what users acquire themselves. Training-data provenance chain. See `copyright-training-data-analysis.md`.*

## 11. Evaluation

> *What we measured (quote fidelity, AO coverage, coach-criteria pass rate, session completion) and what we deliberately did not (leaderboard-style benchmarks — wrong frame for a single-student tutor).*

## 12. Roadmap

> *Reachy Mini embodied interface, mobile surface, multi-subject expansion, Graphiti-backed long-term student model, Boss Battle exam mode.*

## 13. Acknowledgements

> *Pollen Robotics (Reachy), Unsloth (fine-tuning framework), Ollama (runtime), Anthropic (Claude — build harness), Google DeepMind (Gemma 4 base model), and the GCSE English teachers whose open pedagogy informed the Assessment Objective framing.*
Write demo-script.md
68 lines
# Demo Video — Script

**Target runtime:** ~3.5 minutes (within the hackathon's 3–5 minute window)
**Phase:** 🔲 Stub — scene shape only. Content populated during Phase 2.
**Status:** Skeleton

---

## Scene 1 — Working Today (30s)

> *Open WebUI, GB10 under the desk, Lilymay prompts the tutor about a Macbeth scene. Response streams from the fine-tuned Gemma 4. No cloud call. Screen recording + ambient shot of the box.*

**Beats:**
- [ ] …
- [ ] …
- [ ] …

---

## Scene 2 — Architecture Reveal (60s)

> *Cut to the three-layer diagram. Voice-over walks through fine-tune (behaviour) → RAG (knowledge) → gamification (engagement). Reveal MCP transport — Claude Desktop calling `tutor_turn` against the same model.*

**Beats:**
- [ ] …
- [ ] …
- [ ] …

---

## Scene 3 — Gamification Story (60s)

> *Dashboard mockup: XP earned this session, level progression, near-unlockable achievement, streak. The point the hackathon cares about: will a teenager actually open this on a Tuesday evening? Boss Battle mode teaser.*

**Beats:**
- [ ] …
- [ ] …
- [ ] …

---

## Scene 4 — Reachy / Vision (30s)

> *Reachy Mini "Scholar" reporting progress conversationally — "How's revision going?" Live if the robots have arrived by record date (per DEC-06 gate), otherwise pre-recorded or mocked-up scenario audio.*

**Beats:**
- [ ] …
- [ ] …

---

## Scene 5 — Roadmap (30s)

> *Graphiti adaptive student model, multi-subject expansion (Maths, Science), mobile surface, the system getting smarter over time. Close on the GitHub repo URL.*

**Beats:**
- [ ] …
- [ ] …

---

## Production Notes

- [ ] Capture screen recordings during the Phase 2 build, not at the end — raw footage accumulates as the feature ships
- [ ] GorillaPod + sleeve adapter for any walk-and-talk inserts
- [ ] Lilymay on-camera is optional — screen-only is fine per risk table
- [ ] Narration written after scenes are cut, not before
Write video-outline.md
64 lines
# Demo Video — Storyboard Outline

**Companion to:** [demo-script.md](./demo-script.md)
**Phase:** 🔲 Stub — empty shell. Shot list and storyboard drafted during Phase 2.
**Status:** Skeleton

---

## Shot List

> *One row per shot. Fill in during Phase 2 as screen recordings and B-roll accumulate.*

| # | Scene | Shot | Duration | Source | Notes |
|---|-------|------|----------|--------|-------|
| 1 |       |      |          |        |       |
| 2 |       |      |          |        |       |
| 3 |       |      |          |        |       |

---

## Scene-by-Scene Storyboard

### Scene 1 — Working Today

> *Sketch the frame: screen-only? Ambient box shot? Over-the-shoulder?*

- [ ] …

### Scene 2 — Architecture Reveal

> *How the three-layer diagram is introduced on screen — static image, animated reveal, or annotated live demo?*

- [ ] …

### Scene 3 — Gamification Story

> *Dashboard mockup presentation. Static screenshots vs. animated walkthrough vs. live interaction.*

- [ ] …

### Scene 4 — Reachy / Vision

> *Live robot footage vs. pre-recorded vs. mocked-up. Branch point set by DEC-06 gate on 4 May.*

- [ ] …

### Scene 5 — Roadmap

> *Closing frame — GitHub URL, submission team, any acknowledgements visible on-screen.*

- [ ] …

---

## B-Roll / Assets Checklist

- [ ] GB10 hardware shot (ambient, on-desk)
- [ ] Screen recording: Open WebUI Macbeth session
- [ ] Screen recording: Claude Desktop `tutor_turn` call
- [ ] Three-layer architecture diagram (exportable SVG/PNG)
- [ ] Gamification dashboard mockup (React artifact or static HTML from Phase 2)
- [ ] Reachy footage — live or placeholder
- [ ] Repo URL / close card
FEAT-PO-005 kickoff landed — three submission doc stubs in docs/submission/:

technical-writeup.md — 13 titled sections from phase-0-scope.md:267-280, each with a one-line note
demo-script.md — 5-scene skeleton (30s + 60s + 60s + 30s + 30s, ~3.5 min)
video-outline.md — storyboard-lite shell with shot list, per-scene sketches, B-roll checklist
This closes Phase 0 punch-list item #2. Want me to commit, and should I also knock out item #3 while I'm here (FEAT-PO-003 tail: domains/gcse-english/sources/README.md + docs/licensing.md) per the Sunday plan? Or commit these three first and stop?



