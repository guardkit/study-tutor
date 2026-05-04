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


/system-design --from docs/architecture/ARCHITECTURE.md --context docs/research/ideas/phase-0-scope.md --context docs/research/ideas/phase-0-build-plan.md


✅ /system-design complete
Graphiti seeding: 7/7 episodes added

File	Type	Result
docs/design/README.md	project_overview	✓ 10n / 6e
docs/design/contracts/API-tutoring.md	full_doc	✓ 15n / 12e (retry)
docs/design/contracts/API-mcp-transport.md	full_doc	✓ 15n / 13e
docs/design/contracts/API-inference-runtime.md	full_doc	✓ 15n / 12e
docs/design/models/DM-tutoring.md	full_doc	✓ 17n / 7e
docs/design/models/DM-inference-runtime.md	full_doc	✓ 13n / 20e
docs/design/models/DM-mcp-transport.md	full_doc	✓ 13n / 8e
Total: 98 nodes, 78 edges in project_design group on FalkorDB at whitestocks.

Reference artefacts retained on disk only (not seeded — they're machine-readable schemas):

docs/design/mcp-tools.json — JSON Schema for the 4 MCP tools
docs/design/events-schema.yaml — Shared Kernel B event vocabulary
Build plan updated with both design decisions (D1: Tutoring schema P0-only; D2: tutor_start_session reclassified sync) and the recommended /system-design --focus="<context>" invocations for P1 (Knowledge & Curriculum, Student Model) and P2 (Gamification).

Next:

/system-plan --from docs/design/README.md --context docs/architecture/ARCHITECTURE.md --context docs/research/ideas/phase-0-scope.md --context docs/research/ideas/phase-0-build-plan.md to ground feature-level planning.
/arch-refine to update domain-model.md §7.1 SR-07 wording for tutor_start_session per D2.
When phase-1-scope.md is ready, re-run /system-design --focus="Knowledge & Curriculum" and /system-design --focus="Student Model".




/system-plan --from docs/design/README.md --context docs/architecture/ARCHITECTURE.md --context docs/research/ideas/phase-0-scope.md --context docs/research/ideas/phase-0-build-plan.md

Roadmap written. Graphiti reachable (738 episodes seeded; architecture_decisions group has 100 episodes).

✅ /system-plan OUTPUT

Created: docs/planning/feature-roadmap.md

Contents:

§2 — Architecture follow-ups: D1 (TutorSession P0 shape) + D2 (tutor_start_session sync) → bundle into one /arch-refine session before Phase 1 wires Graphiti
§3 — Phase 0 close-out: FEAT-PO-004 Bedrock + clean-machine walkthrough (ready-to-run /feature-spec invocation included)
§4 — Phase 1 features (PH1-001..004) with bounded-context mapping, ADR refs, and /feature-spec invocations; flags new SR-08 / SR-09 cross-cutting concerns
§5 — Phase 2 sketch (PH2-001..003) — full invocations deferred to 1 May Phase 2 /system-plan re-run
§6 — Feature dependency graph (Mermaid) — PH1-001 is the fan-out hub; D1/D2 dashed (arch-refine, not features); PH1-003 is the Phase 1 integration sink
§7 — Phase timeline gantt — DDD Southwest 13–16 May absorption marked critical; Bedrock and Graphiti spike parallel-safe
§8 — Recommended next commands in execution order
§9 — Conformance check (no contradictions vs 16 ADRs; Shared Kernel B producer/consumer roles match events-schema.yaml)
No architecture refinement performed — user picked [F]; ARCHITECTURE.md, ADRs, domain-model, and design contracts all unchanged.

📥 Graphiti seeding (offered)

Tier 2 connectivity confirmed (FalkorDB on whitestocks, vLLM on GB10, embeddings on promaxgb10-41b1:8001).

The roadmap belongs in the architecture_decisions group (sequencing context for upcoming feature-plans). Recommended:


guardkit graphiti add-context docs/planning/feature-roadmap.md \
  --group architecture_decisions
Seed the roadmap to Graphiti now? [Y/n]

Seeded. 1 episode added (3 nodes, 2 edges) in 44s. Warnings are non-blocking — they're project_overview-schema heuristics that don't apply to a sequencing doc.

📋 /system-plan complete

Action	Result
Mode	Refine → hand-off ([F])
Architecture refinement	None — ARCHITECTURE.md, ADRs, domain-model unchanged
Output	docs/planning/feature-roadmap.md (210 lines, 2 Mermaid diagrams)
Graphiti seeding	✓ architecture_decisions group
Architecture follow-ups identified	D1, D2, SR-08, SR-09 — bundle into one /arch-refine
Recommended next command:


/arch-refine \
  --target docs/architecture/domain-model.md \
  --context docs/design/README.md \
  --context docs/research/ideas/phase-0-build-plan.md \
  --context docs/research/ideas/phase-1-scope.md
That clears D1 + D2 + adds SR-08 / SR-09 before the Sat 26 Apr Graphiti spike kicks off Phase 1. Then Phase 0 close-out: /feature-spec + /feature-plan for FEAT-PO-004 Bedrock validation.

Final Summary
Created (1):

docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md
Modified (9):

ADR-ARCH-008 — status block flipped to "Partially superseded by ADR-ARCH-017"; classification table struck through with pointer; original rationale preserved verbatim with supersession warning above it.
ARCHITECTURE.md:161 — index status updated; new row for ADR-ARCH-017.
domain-model.md §7.1 — table row + footnote citing ADR-ARCH-017.
container.md:30 — C4 description.
design/README.md §3 D2 + §7.4 — both follow-up notes marked resolved with ADR-ARCH-017 reference.
phase-0-scope.md §SR-07 — header + table + reversion conditions + FEAT-PO-002 bullet.
phase-0-build-plan.md:246 — SR-07 verification step.
adapter.py:5 — module docstring.
server.py:4 + L29-32 — module docstring + the load-bearing registered tool description (the canonical SR-07 contract that ships to Claude Desktop).
Phase 8 — Graphiti Seeding (offered, not auto-run)
The new and superseded ADRs should be seeded into the architecture_decisions group. The guardkit graphiti add-context CLI handles sanitisation. Suggested commands:


guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md \
  --group architecture_decisions

guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-008-mcp-only-agent-access.md \
  --group architecture_decisions
Re-seeding ADR-ARCH-008 captures the new "Partially superseded" status block in the knowledge graph so Graphiti queries return the current state (not the pre-supersession version).

Staleness flagging (Phase 5 of /arch-refine) is what update_entity_metadata({stale: True}) does in the canonical flow — it tags downstream nodes that referenced ADR-ARCH-008's classification so /system-design will report them on next run. I haven't run that step (no direct Graphiti write access in this command shape) — the affected downstream artefacts are listed in the ADR-ARCH-017 §"Affected downstream artefacts" section and have already been edited in this run, so the staleness flag would fire and immediately resolve. Worth running if you want the audit trail intact, no-op functionally.

Want me to run the two seeding commands? Y/N — or hold off if you'd prefer to commit first and seed as a separate step.

please can you run the seeding commands

Re-seed complete — ADR-ARCH-008 now reflects the partial-supersession status in the knowledge graph. Final results:

Graphiti seeding summary:

ADR	Status	Nodes	Edges	Invalidated	Duration
ADR-ARCH-017 (new)	seeded	9	26	0	~3min
ADR-ARCH-008 (re-seed)	overwritten	30	41	0	~6min
The vLLM duplicate-detection warnings on ADR-ARCH-008 are non-fatal — the model returned out-of-range indices for duplicate_facts and Graphiti handled it gracefully. Both ADRs are now queryable via mcp__graphiti__search_nodes / search_memory_facts against the architecture_decisions group.

Note on invalidated=0: Graphiti preserved both the old and new ADR-ARCH-008 facts with timestamps rather than invalidating prior ones — that's the canonical temporal-superseding behaviour. Queries return the most recent facts by updated_at, but the historical "Accepted, classification stable across phases" assertion remains in the graph for audit. This is what we want.

/arch-refine — complete
Final state of the refinement:

1 new ADR (ADR-ARCH-017) and 1 partial supersession (ADR-ARCH-008).
8 downstream artefacts updated to reflect the sync classification — domain-model, container.md, ARCHITECTURE.md index, design/README.md, phase-0-scope.md, phase-0-build-plan.md, adapter.py, server.py.
8/8 MCP unit tests passing — the runtime tool description on tutor_start_session now matches handler behaviour, resolving the SR-07 violation.
Both ADRs seeded into Graphiti with full audit trail.
The Phase 0 SR-07 contract is now consistent end-to-end: ADR → architecture text → design docs → scope/build-plan docs → registered MCP tool description → handler behaviour. Phase 1's reversion path is documented and conditional on the Graphiti latency spike measurement.

Ready to commit when you are. Suggested commit subject: arch: reclassify tutor_start_session as sync (ADR-ARCH-017, supersedes ARCH-008 SR-07).

The wrap-up already completed in the prior turn when the task-notification fired — the scheduled wakeup raced with the actual completion notification. Re-stating the final state for clarity:

Both seeds confirmed complete:

ADR-ARCH-017 (new) — 9 nodes, 26 edges, 0 invalidated, ~3min
ADR-ARCH-008 (re-seed) — 30 nodes, 41 edges, 0 invalidated, ~6min
Noteworthy from logs:

vLLM duplicate_facts warnings on ADR-ARCH-008 — model returned out-of-range indices; Graphiti handled gracefully, non-fatal.
invalidated=0 is correct — Graphiti preserves both old and new facts with timestamps rather than deleting prior ones (canonical temporal-superseding behaviour). Recency-ordered queries return the new "Partially superseded" status; the historical "Accepted / stable across phases" claim stays in the graph for audit.
Full refinement is done: 1 new ADR, 1 partial supersession, 8 downstream artefacts aligned, 8/8 MCP tests green, both ADRs seeded. SR-07 contract now consistent end-to-end. No further work pending — ready for commit when you want.


Build-plan punch-list updated — D2 marked CLOSED with ADR-ARCH-017 reference, header date bumped to 2026-04-27.

On the next steps you pasted
Your two /system-design --focus=... commands are correct in shape, but the sequencing in phase-1-scope.md:72 says the Graphiti latency spike must run first:

Before any schema work, measure the three-hop latency end-to-end. This resolves DEC-02 / DEC-08 ambiguity and locks SR-08 + the Phase 0 MCP tool classification.

So the right order is:

Graphiti latency spike — measures add_episode and search_nodes latencies on the FalkorDB Synology + Gemini + GB10 split topology. Per phase-1-scope.md L83-85, the result determines:
Whether SR-08 (async write-back) is "still defensive shape" (latency <2s) or "load-bearing throughout features" (latency >5s).
Whether the SR-07 classification we just locked in ADR-ARCH-017 holds (sync), or needs reversion to long-running (if search_nodes median > ~3s).
Bundle SR-08 + SR-09 (+ any SR-07 reversion) into one /arch-refine. This is the recommendation the /system-plan summary made. After the spike the inputs are concrete.
Then your two /system-design --focus= re-runs — Knowledge & Curriculum and Student Model. They'll consume the ADR-ified SR-08 and the spike result.
What's still open from /system-plan's four-item bundle
Item	Status	What's needed
D1 — TutorSession P0-only shape	✅ No action (fits within architecture envelope; you confirmed earlier)	—
D2 — tutor_start_session sync	✅ CLOSED via ADR-ARCH-017	—
SR-08 — Graphiti write-back asynchrony	📝 Documented in phase-1-scope.md §SR-08; not yet in any ADR	Spike result → /arch-refine to elevate to a CC alongside SR-01–07 (likely refines ADR-ARCH-009)
SR-09 — Runtime LLM parameter explicitness	📝 Documented in phase-1-scope.md §SR-09; not yet in any ADR	Spike-independent; can /arch-refine ADR-ARCH-009 to add SR-09 anytime
The /system-plan bundle recommendation makes sense because SR-08 + SR-09 + potential SR-07 reversion all touch ADR-ARCH-009 ("Six parity surfaces as load-bearing CC") — so refining ARCH-009 once with all three is cleaner than three separate runs.

Suggested sequence

# 1. Run the Graphiti latency spike (per phase-1-scope.md §"Graphiti latency spike").
#    Produces the empirical numbers that lock SR-08 and confirm/revert SR-07.
#    Targets per phase-1-scope.md L83-85: add_episode median, search_nodes median.

# 2. Post-spike: bundle SR-08 + SR-09 (+ SR-07 reversion if needed) into one /arch-refine.
#    Likely refines ADR-ARCH-009 (six parity surfaces → eight) — though ARCH-017's reversion
#    rule already covers SR-07, so the bundle may shrink to just SR-08/09 if the spike
#    confirms <3s search_nodes latency.

/arch-refine --adr=ADR-ARCH-009 \
  --context docs/research/ideas/phase-1-scope.md \
  --context <spike-results-doc>

# 3. Then the Phase 1 design re-runs (your pasted commands):

/system-design --focus="Knowledge & Curriculum" \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/rag-grounding-design.md \
  --context docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md

/system-design --focus="Student Model" \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md \
  --context docs/architecture/decisions/ADR-ARCH-007-graphiti-split-topology.md

# 4. In parallel (independent of P1): Phase 0 close-out for FEAT-PO-004 Bedrock validation.
/feature-spec FEAT-PO-004
/feature-plan FEAT-PO-004
Optional — if you want to skip the spike-first sequencing
If the Graphiti spike is going to slip and you want to unblock Phase 1 design work now, you can run the two /system-design --focus= commands using the current SR-07 sync classification (ADR-ARCH-017) and accept that SR-08 stays as a phase-1-scope.md item rather than a CC. The risk is: if the spike later forces an SR-07 reversion, the design artefacts produced by the focus runs will need re-running. Probably not worth the rework — better to do the spike first.

Recommendation: spike Saturday morning as originally planned, then bundle-refine, then design re-runs. That's the path of least churn.

thanks, please can you rovide details on how to run : 1. Run the Graphiti latency spike (per phase-1-scope.md §"Graphiti latency spike").
Let me read the spike spec in phase-1-scope.md and check whether any spike scaffolding already exists in the repo.


Spike results — clear and decisive
Operation	Min	Median	Max	Verdict
add_episode	78.1s	78.98s	134.4s	>>> 5s threshold
search_nodes	0.07s	0.07s	0.11s	<<< 1s threshold
search_memory_facts	0.07s	0.08s	0.08s	fast
The add_episode numbers are dominated by the LLM extraction step (Qwen2.5-14B FP8 on GB10 reasoning over the JSON payload — ~80s per call, cold-start gave run 1 the 134s outlier). Search operations hit only the embedding endpoint + FalkorDB cypher and complete in tens of milliseconds.

What this means for the architecture
1. SR-08 (Graphiti async write-back) — CRITICAL, not defensive.

At ~79s median, a synchronous add_episode at session-end would make the student wait over a minute for tutor_session_end to return. SR-08 isn't just "defensive shape" — it's load-bearing. The right pattern per phase-1-scope.md L83 is: fire-and-forget from multiple write points (session-end is the obvious one, but also misconception-observed during turns, and confidence-delta proposals from the Coach), not a single session-end batch.

This needs to be elevated to an ADR — likely refining ADR-ARCH-009 (six parity surfaces) to seven, with SR-08 joining SR-01–07 as a load-bearing CC.

2. ADR-ARCH-017 / SR-07 (sync tutor_start_session) — CONFIRMED with massive margin.

search_nodes at 0.07s is 40× faster than the 3s reversion threshold in ARCH-017's footnote. The sync classification holds. The Phase 1 student-model read at session start (the original concern that motivated long-running) costs ~70ms — completely negligible. No /arch-refine follow-up needed for ARCH-017.

3. DEC-02 / DEC-08 — resolved.

What this changes about your next-step sequence
The plan you pasted earlier had the Phase 1 design re-runs after a /arch-refine for SR-08/SR-09. That bundle is now narrower:

No need to refine ADR-ARCH-017 (SR-07) — the spike confirmed it.
SR-08 still needs ADR treatment — but with a much stronger forcing function (the 79s number) than before.
SR-09 (runtime LLM parameter explicitness) is unchanged by the spike — still wants ADR treatment.
Suggested updated sequence:


# 1. /arch-refine for SR-08 + SR-09 — cite the spike numbers as the empirical
#    basis. Likely refines ADR-ARCH-009 (six → eight parity surfaces).
/arch-refine --adr=ADR-ARCH-009 \
  --context docs/research/ideas/graphiti-latency-spike-results.md \
  --context docs/research/ideas/phase-1-scope.md

# 2. Then your two Phase 1 design re-runs as previously planned.
/system-design --focus="Knowledge & Curriculum" ...
/system-design --focus="Student Model" ...
Files to review/commit
New: scripts/graphiti_latency_spike.py — reproducible benchmark script
New: docs/research/ideas/graphiti-latency-spike-results.md — generated results doc with auto-derived decision verdicts
Suggested commit subject: spike: graphiti latency on vLLM-GB10 stack (add_episode 79s, search 70ms) — captures both the load-bearing finding (SR-08 critical) and the configuration-pinning detail (vLLM, not Gemini).

The throwaway latency-spike-2026-04-27 group was cleaned from the graph automatically — no leftover spike data in architecture_decisions.

Where the project stands
Phase 0 SR-07 contract: clean end-to-end. ADR ↔ architecture text ↔ design ↔ scope ↔ build-plan ↔ runtime tool description ↔ handler behaviour all consistent.
Phase 1 latency budget: measured. 79s writes, 70ms reads — these are the numbers feature specs and the Coach pattern need to plan against.
Open follow-up before P1 design re-runs: one /arch-refine to elevate SR-08 (and add SR-09) — the spike just gave it a strong empirical foundation.
please provide the full command syntax for : Open follow-up before P1 design re-runs: one /arch-refine to elevate SR-08 (and add SR-09) — the spike just gave it a strong empirical foundation.
Full command for the SR-08 + SR-09 refinement

/arch-refine --adr=ADR-ARCH-009 \
  "elevate SR-08 (Graphiti async write-back) and SR-09 (runtime LLM parameter explicitness) from phase-1-scope.md items to load-bearing cross-cutting concerns alongside SR-01..07; spike confirms 79s add_episode median makes async non-negotiable" \
  --context docs/research/ideas/graphiti-latency-spike-results.md \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md


/arch-refine --adr=ADR-ARCH-003 \
  --context docs/research/ideas/graphiti-latency-spike-results.md \
  "broaden async write-back scope from session-end-only to every Graphiti write point per CC-13 (ARCH-018)"



All in-place updates landed cleanly. Now Graphiti seeding.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌱 GRAPHITI SEEDING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Tier 1 check passed (.guardkit/graphiti.yaml has enabled: true). The add_episode median is 78.98s per the latency spike — which is exactly the rule ARCH-019 is encoding — so I will offer the seeding commands for explicit user execution rather than running them inline (a minutes-long block in this command is precisely what CC-13 says to avoid).

Recommended seeding commands (run when convenient — they will block for several minutes per the latency spike):


guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md \
  --group architecture_decisions

guardkit graphiti add-context docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md \
  --group architecture_decisions
Staleness flagging: the design / planning artefacts listed in the impact analysis are recorded inside ADR-ARCH-019's "Downstream artefacts flagged stale" section (matching ARCH-018's pattern); /system-design and /feature-spec will pick them up on next run. I did not invoke arch_sp.update_entity_metadata(...) programmatically because a) the /arch-refine command spec describes that as a Graphiti API call requiring runtime SDK access from the command harness (not directly available in this session), and b) the ARCH-019 markdown surface is the canonical staleness record that downstream commands read.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ ARCHITECTURE DECISION REFINED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ADR-ARCH-003: Status changed to "Superseded by ADR-ARCH-019"
  ADR-ARCH-019: Created (supersedes ADR-ARCH-003)
                Scope: async Graphiti write-back at every write point
                Evidence: 2026-04-27 latency spike — add_episode median 78.98s
                CC anchor: CC-13 (ARCH-018)
Updated files (in-place):

docs/architecture/decisions/ADR-ARCH-003-async-graphiti-writeback.md — status → superseded
docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md — new
docs/architecture/ARCHITECTURE.md:148, 158, 174 — Phase 1 description, index entries
docs/architecture/container.md:30, 38, 74, 82, 106-107 — labels and explanatory note
docs/architecture/domain-model.md:338, 443-444, 466-468, 492-494 — write-back semantics
Flagged stale (recorded in ADR-ARCH-019; not modified in this run):

docs/design/README.md line 70 · docs/design/contracts/API-tutoring.md lines 119, 133 · docs/design/events-schema.yaml lines 185-186 · docs/planning/feature-roadmap.md lines 74, 81, 100-102 · docs/gamification/design.md line 482
C4 re-review: Not triggered — topology unchanged (same containers, same relationships); only label text on existing relationships was refreshed in-place.

Next steps:

Run the two guardkit graphiti add-context commands above to seed the architecture_decisions group.
Run /system-design — it will detect and report the design-artefact staleness flags listed in ARCH-019.
When /feature-spec for FEAT-PH1-001 runs, point it at ADR-ARCH-019 (not ARCH-003) and let it pick up the broadened scope for Coach misconception logging and Planner topic-confidence updates.


/system-design --focus="MCP Transport" \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md \
  --context docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md \
  --context docs/architecture/decisions/ADR-ARCH-017-tutor-start-session-sync-classification.md \
  --context docs/research/ideas/graphiti-latency-spike-results.md

✅ /system-design --focus="MCP Transport" complete
Updated artefacts:


docs/design/
├── README.md                                              (§3 + §5 + §7 + §8 refreshed)
├── contracts/
│   └── API-mcp-transport.md                               (§1 + §5 + §6 + §10; new §5.5 + §5.6)
├── models/
│   └── DM-mcp-transport.md                                (§1 + §2 + §6 + §10; new I-MCP8 + I-MCP9)
├── mcp-tools.json                                         (design_decisions block; new description_field_semantics; tutor_session_end description)
└── decisions/
    └── DDR-001-mcp-descriptions-do-not-enumerate-graphiti-writes.md   (NEW)
Contradiction detection: ✓ No contradictions against the 19 architecture ADRs.
OpenAPI validation: N/A — no REST surface (per ADR-ARCH-008; unchanged).
C4 L3 review gate: N/A — MCP Transport has 3 internal components, threshold (>3) not met.
JSON validation: ✓ mcp-tools.json parses; tool list and decision references intact.

Out-of-focus stale references (flagged by ADR-018/019, not swept this run):

API-tutoring.md §3.4 (still cites ADR-ARCH-003 directly)
events-schema.yaml (ADR-ARCH-003 reference)
CC-14 (num_ctx / num_predict) coverage in DM-tutoring.md / DM-inference-runtime.md
Recommend /system-design --focus="Tutoring" and /system-design --focus="Inference Runtime" next to finish closing those.

Recommended next steps:

Confirm Graphiti seeding (above) — or defer.
When implementing the next Phase 1 PR that touches src/study_tutor/mcp/server.py, add the DDR-001 substring test and the I-MCP8 handler-latency test documented in API-mcp-transport.md §10 and DM-mcp-transport.md §6.
Run /system-design --focus="Tutoring" to close the remaining stale references in the Tutoring contract (tutor_session_end row + events-schema).


/system-design --focus="Tutoring" \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md \
  --context docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md \
  --context docs/research/ideas/graphiti-latency-spike-results.md

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ SYSTEM DESIGN COMPLETE — Tutoring (refresh)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Modified: docs/design/
  ├── README.md                              (refresh log + DDR-002/003 + C4 L3 row)
  ├── contracts/
  │   └── API-tutoring.md                    (Δ1–Δ6 + Δ9: ADR-019/CC-13 alignment, F1/F2/F3 references, DDR-001/002/003 cross-refs)
  ├── models/
  │   └── DM-tutoring.md                     (Δ7–Δ9: I-T7 invariant, §11 flush points, persistence narrative)
  └── events-schema.yaml                     (Δ10: ARCH-003 → ARCH-019; emit_decoupled flag; DDR-003 rationale)

Created:
  ├── decisions/
  │   ├── DDR-002-coach-async-subagent-owns-graphiti-writes.md
  │   └── DDR-003-session-completed-emits-on-state-transition.md
  └── diagrams/
      └── tutoring-c4-l3.md                  (8-component C4 L3, approved at gate)

Out of scope (still pending):
  • DM-inference-runtime.md / API-inference-runtime.md — CC-14 invariants
    Recommended: /system-design --focus="Inference Runtime"

Contradiction detection: ✓ no conflicts vs 19 architecture ADRs
C4 L3 review gate: ✓ approved
OpenAPI validation: N/A (no REST surface in Phase 0; ADR-ARCH-008)



/system-design --focus="Inference Runtime" \
  --from docs/architecture/ARCHITECTURE.md \
  --context docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md \
  --context docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md


✅ SYSTEM DESIGN COMPLETE — /system-design --focus="Inference Runtime" (2026-04-27 PM late)
Closes the last outstanding ADR-018/019 stale-reference item flagged in docs/design/README.md §5 / §7.6.

Files updated / created

docs/design/
├── README.md                                 (logged 2026-04-27 PM-late refresh; closed Inference Runtime sweep)
├── contracts/
│   └── API-inference-runtime.md              (Δ1–Δ5: header refresh; §4 split client/Modelfile; §5 invariants 6 & 7; §7.2 CC-14 smoke tests; §8/§9 out-of-scope + open question)
├── models/
│   └── DM-inference-runtime.md               (Δ6–Δ8: §4 split; I-IR7 / I-IR8 invariants; §6 Modelfile relationship; §8 out-of-scope alignment)
└── decisions/
    └── DDR-004-num-ctx-modelfile-owned-not-client.md  (NEW — Modelfile-vs-client locus; CC-14 conformance via two-part smoke test)
Design decisions captured
DDR-004 — num_ctx is owned by the Ollama Modelfile, not by LLMClient. CC-14 conformance is enforced by a smoke test (ollama show <model> --modelfile | grep PARAMETER and runner-log inspection of llama_new_context_with_model: n_ctx = N), not by a per-request client check. OLLAMA_NUM_PREDICT (env var, default 2048) is the operator override for num_predict, not the CC-14 floor (≥ 1500 — Modelfile-default).
Contradiction detection
✓ No contradictions against the 19 architecture ADRs or DDR-001/002/003. Deltas implement ADR-ARCH-018's CC-14 mandate; non-Ollama-provider extension recorded as an open question rather than a conflict.

C4 L3 review gate
Skipped. Inference Runtime confirmed ≤ 3 internal components (LLMClient + provider-resolution helpers + lazy httpx-on-Ollama path; the Modelfile is a configuration artefact). Threshold not met.

OpenAPI validation
Skipped. No REST surface in Inference Runtime (it has no external protocol surface — internal Python interface only).


/feature-spec "Graphiti Student Model — entities, relationships, episodes, query helpers, seeding script, async write-back" \
  --from docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/phase-1-build-plan.md \
  --context docs/research/ideas/phase-0-validation.md \
  --context docs/research/ideas/graphiti-latency-spike-results.md \
  --context domains/gcse-english/GOAL.md \
  --context docs/architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md \
  --context docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md \
  --context docs/design/decisions/DDR-002-coach-async-subagent-owns-graphiti-writes.md \
  --context docs/design/decisions/DDR-003-session-completed-emits-on-state-transition.md \
  --context /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/tools/graphiti_client.py \
  --context /Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/tools/graphiti_query.py


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC COMPLETE: Graphiti Student Model
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files written:

features/graphiti-student-model/graphiti-student-model.feature
features/graphiti-student-model/graphiti-student-model_assumptions.yaml
features/graphiti-student-model/graphiti-student-model_summary.md
Scenarios: 38 total
@key-example: 8   @boundary: 9
@negative: 7      @edge-case: 14
@smoke: 4         @regression: 0

Assumptions: 8 total
high: 4 (auto-proceed)
medium: 3 (Coach review recommended)
low: 1 (human review required)

REVIEW REQUIRED: 1 low-confidence assumption needs verification

ASSUM-007 — process-shutdown grace period of 30 seconds. See assumptions YAML for verification notes.
Deferred: 0 scenario groups

Architectural anchors honoured: ADR-ARCH-019 (every-write-point async), DDR-002 (Coach owns own writes), DDR-003 (event-emit decoupled from write success), CC-13, LES1 §3 (graceful module load).

Cross-repo discrepancy surfaced: fleet:appmilla (scope doc) vs appmilla-fleet (specialist-agent) — study-tutor follows scope doc, recorded in ASSUM-008.

Next steps:


Review: features/graphiti-student-model/graphiti-student-model.feature
Pass to feature-plan:
  /feature-plan "Graphiti Student Model" \
    --context features/graphiti-student-model/graphiti-student-model_summary.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

/feature-plan "Graphiti Student Model" \
    --context features/graphiti-student-model/graphiti-student-model_summary.md


 FEATURE PLANNING COMPLETE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE: Graphiti Student Model (FEAT-PH1-001)
FEATURE ID: FEAT-1773
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Created
📁 tasks/backlog/graphiti-student-model/

README.md
IMPLEMENTATION-GUIDE.md — data flow + sequence + dependency diagrams + §4 Integration Contracts + risk register + conformance tests
6 subtask markdown files with task_type, parent_review, feature_id, wave, implementation_mode, consumer_context, and seam test stubs
📁 .guardkit/features/FEAT-1773.yaml — AutoBuild-ready, with smoke_gates block (after_wave_1..4) including the CC-13 single-call-site audit between Wave 2 and Wave 3

📁 tasks/in_review/TASK-REV-7DC0-plan-graphiti-student-model.md — review task moved with decision: implement recorded

📁 features/graphiti-student-model/graphiti-student-model.feature — 38/38 scenarios tagged:

16 → TASK-GSM-004 (async helper, the load-bearing slice)
13 → TASK-GSM-005 (query helpers)
5 → TASK-GSM-001 (entities)
2 → TASK-GSM-006 (seeding)
1 → TASK-GSM-002 (episodes)
1 → TASK-GSM-003 (client wrapper)
Wave Structure

Wave 1 (parallel): TASK-GSM-001 (entities) + TASK-GSM-002 (episodes)
Wave 2 (parallel): TASK-GSM-003 (client) + TASK-GSM-004 (async helper)
Wave 3 (single):   TASK-GSM-005 (query helpers)
Wave 4 (single):   TASK-GSM-006 (seeding script)
Total work: 9.5h · With parallelism: ~7.5h elapsed

Run It

/feature-build FEAT-1773      # autonomous AutoBuild
# or per-task:
/task-work TASK-GSM-001        # start with Wave 1

GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-1773 --verbose 



/feature-spec "Deterministic Session Planner — SessionPlan type, rules 1/3/4 implemented, MCP integration" \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/phase-1-build-plan.md \
  --context src/study_tutor/knowledge/student_model.py \
  --context src/study_tutor/mcp/adapter.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC COMPLETE: Deterministic Session Planner
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files written:
  features/deterministic-session-planner/deterministic-session-planner.feature
  features/deterministic-session-planner/deterministic-session-planner_assumptions.yaml
  features/deterministic-session-planner/deterministic-session-planner_summary.md

Scenarios: 29 total
  @key-example: 7   @boundary: 6
  @negative: 6      @edge-case: 11
  @smoke: 4         @regression: 0

Assumptions: 8 total
  high: 2 (auto-proceed)
  medium: 6 (Coach review recommended)
  low: 0

Deferred: 0 scenario groups

Next steps:
  Review: features/deterministic-session-planner/deterministic-session-planner.feature
  Pass to feature-plan:
    /feature-plan "Deterministic Session Planner" \
      --context features/deterministic-session-planner/deterministic-session-planner_summary.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━


/feature-plan "Deterministic Session Planner" \
      --context features/deterministic-session-planner/deterministic-session-planner_summary.md


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ FEATURE PLANNING COMPLETE — FEAT-PH1-002 Deterministic Session Planner
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Artefacts Created
Path	Contents
.guardkit/features/FEAT-PH1-002.yaml	Structured feature file. 7 tasks, 6 waves, smoke_gates configured. AutoBuild-ready.
.guardkit/reviews/TASK-REV-DA72-review-report.md	Decision-mode review (463 lines): 4 options, recommendation, risks, gap analysis, subtask breakdown.
tasks/in_review/TASK-REV-DA72-plan-deterministic-session-planner.md	Review task, status review_complete, frontmatter records sign-offs.
tasks/backlog/deterministic-session-planner/README.md	Feature README.
tasks/backlog/deterministic-session-planner/IMPLEMENTATION-GUIDE.md	Full guide with 3 mandatory Mermaid diagrams (data flow, integration contracts, task dependency graph) + §4 contracts + sign-off block + smoke gates documentation.
tasks/backlog/deterministic-session-planner/TASK-DSP-001..007	7 task files with task_type, parent_review, feature_id, consumer_context (where applicable), and seam tests.
features/deterministic-session-planner/deterministic-session-planner.feature	All 29 scenarios now carry @task:TASK-DSP-XXX tags — R2 BDD oracle activated.
features/deterministic-session-planner/deterministic-session-planner_assumptions.yaml	Updated with verbatim sign-off wordings for ASSUM-006/007/008.
Summary
Approach: Option A — Sequential short-circuit pipeline of typed Rule objects (Strategy pattern). Determinism enforced structurally via injected clock + seeded random.Random.
7 tasks across 6 waves, ~14h wave-parallel ceiling. Wave 3 has TASK-DSP-003 + TASK-DSP-004 in parallel (auto-named Conductor workspaces deterministic-session-planner-wave3-1/2).
All 29 BDD scenarios tagged at confidence 0.83–0.93 (zero below threshold, zero already tagged).
Pre-flight validation green: no schema errors, no parallel-group conflicts, smoke_gates active for waves 5 & 6 (pytest -m "feat-ph1-002 and smoke").
All sign-offs resolved with measured data: ASSUM-006 (2s budget) + ASSUM-007 (5s read timeout) — both confirmed against the 0.07s/0.08s Graphiti read medians (28×–25× headroom). ASSUM-008 (SessionCompletedEpisode.topics_covered: list[str]) — locked against TASK-GSM-002.
Next Step

/feature-build FEAT-PH1-002
or, manually:


/task-work TASK-DSP-001
Two minor side effects worth noting: I had to collapse two multi-line And steps in the feature Background (the Gherkin parser doesn't accept continuation lines), and the feature YAML's smoke_gates schema accepts a single SmokeGates object (not the after_wave_N: [commands] form documented in feature-plan.md) — so smoke gates fire after waves 5 & 6 with one shared pytest invocation rather than per-wave shell commands.


GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-PH1-002 --verbose

════════════════════════════════════════════════════════════
FEATURE RESULT: SUCCESS
════════════════════════════════════════════════════════════

Feature: FEAT-PH1-002 - Deterministic Session Planner
Status: COMPLETED
Tasks: 7/7 completed
Total Turns: 11
Duration: 21m 55s

                                  Wave Summary
╭────────┬──────────┬────────────┬──────────┬──────────┬──────────┬─────────────╮
│  Wave  │  Tasks   │   Status   │  Passed  │  Failed  │  Turns   │  Recovered  │
├────────┼──────────┼────────────┼──────────┼──────────┼──────────┼─────────────┤
│   1    │    1     │   ✓ PASS   │    1     │    -     │    1     │      -      │
│   2    │    1     │   ✓ PASS   │    1     │    -     │    1     │      -      │
│   3    │    2     │   ✓ PASS   │    2     │    -     │    5     │      -      │
│   4    │    1     │   ✓ PASS   │    1     │    -     │    1     │      -      │
│   5    │    1     │   ✓ PASS   │    1     │    -     │    2     │      -      │
│   6    │    1     │   ✓ PASS   │    1     │    -     │    1     │      -      │
╰────────┴──────────┴────────────┴──────────┴──────────┴──────────┴─────────────╯

Execution Quality:
  Clean executions: 7/7 (100%)

SDK Turn Ceiling:
  Invocations: 1
  Ceiling hits: 0/1 (0%)

Worktree: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-PH1-002
Branch: autobuild/FEAT-PH1-002

Next Steps:
  1. Review: cd /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-PH1-002
  2. Diff: git diff main
  3. Merge: git checkout main && git merge autobuild/FEAT-PH1-002
  4. Cleanup: guardkit worktree cleanup FEAT-PH1-002
INFO:guardkit.cli.display:Final summary rendered: FEAT-PH1-002 - completed
INFO:guardkit.orchestrator.review_summary:Review summary written to /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/FEAT-PH1-002/review-summary.md
✓ Review summary: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/FEAT-PH1-002/review-summary.md
INFO:guardkit.orchestrator.feature_orchestrator:Feature orchestration complete: FEAT-PH1-002, status=completed, completed=7/7


 /feature-complete FEAT-PH1-002


/feature-spec "DeepAgents Tutoring Loop with Coach — Player-Coach integration, Coach rubric, session-end summary, async Graphiti write-back" \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/phase-1-build-plan.md \
  --context roles/tutor/prompts/coach.md \
  --context /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/agents/coach.py \
  --context src/study_tutor/mcp/adapter.py


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC COMPLETE: DeepAgents Tutoring Loop with Coach
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files written:
  features/deepagents-tutoring-loop/deepagents-tutoring-loop.feature
  features/deepagents-tutoring-loop/deepagents-tutoring-loop_assumptions.yaml
  features/deepagents-tutoring-loop/deepagents-tutoring-loop_summary.md

Scenarios: 39 total
  @key-example: 8     @boundary: 8
  @negative: 7        @edge-case: 16
  @smoke: 5           @regression: 0

Assumptions: 11 total
  high: 5 (auto-proceed)
  medium: 4 (Coach review recommended)
  low: 2 (human review required)

REVIEW REQUIRED: 2 low-confidence assumptions need verification
  - ASSUM-006: Coach reasoning behaviour beyond the 200-word cap
  - ASSUM-011: Shutdown grace window (5 seconds) for in-flight Graphiti writes
  See: features/deepagents-tutoring-loop/deepagents-tutoring-loop_assumptions.yaml

Deferred: 0 scenario groups

Anchor decisions honoured:
  DDR-002, DDR-003, CC-13 / ADR-ARCH-019, D5 (Coach evaluation-only),
  Two-provider invariant (enforced at construction)

Next steps:
  Review: features/deepagents-tutoring-loop/deepagents-tutoring-loop.feature
  Pass to feature-plan:
    /feature-plan "DeepAgents Tutoring Loop with Coach" \
      --context features/deepagents-tutoring-loop/deepagents-tutoring-loop_summary.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Note on @task: tags — I used placeholder IDs TASK-DTL-001..005 matching the natural slice boundaries (Coach factory, rubric+verifier, loop+revision, async writes, session-end). /feature-plan Step 11 (bdd-linker) will replace these with the real task IDs once the subtasks are generated.






/feature-plan "DeepAgents Tutoring Loop with Coach" \
      --context features/deepagents-tutoring-loop/deepagents-tutoring-loop_summary.md


FEATURE PLANNING COMPLETE — FEAT-PH1-003
DeepAgents Tutoring Loop with Coach

Generated artefacts

📁 tasks/backlog/deepagents-tutoring-loop/
   ├── README.md
   ├── IMPLEMENTATION-GUIDE.md       (4 mandatory Mermaid diagrams + §4 contracts)
   ├── TASK-DTL-001-coach-factory-structural-invariants.md          [Wave 1, complexity 5]
   ├── TASK-DTL-002-rubric-and-quote-fidelity.md                    [Wave 2, complexity 6]
   ├── TASK-DTL-003-orchestrator-revision-loop-concurrency.md       [Wave 2, complexity 7]
   ├── TASK-DTL-004-async-write-helper-consumer-misconceptions.md   [Wave 1, complexity 5]
   └── TASK-DTL-005-session-end-summary-f3-emit-lifecycle.md        [Wave 3, complexity 6]

📁 .guardkit/features/FEAT-PH1-003.yaml
   • 5 tasks, 3 waves, smoke_gates wired (after_wave: [3])
   • AC-quality review: 0 unverifiable criteria

📁 .guardkit/reviews/TASK-REV-DTL3-review-report.md
   • 4 options evaluated, Option A recommended (9.4/10)
   • ASSUM-006 + ASSUM-011 resolutions documented

📁 tasks/in_review/TASK-REV-DTL3-... (review task moved, status: review_complete)
Wave Execution

Wave 1 (parallel-safe):  TASK-DTL-001 ‖ TASK-DTL-004
Wave 2 (parallel-safe):  TASK-DTL-002 ‖ TASK-DTL-003
Wave 3 (sequential):     TASK-DTL-005
Effort: 22-28h sequential / ~14h elapsed with parallel waves
Smoke gate: pytest -m "feat-ph1-003 and smoke" -x --no-cov after Wave 3
BDD linker (Step 11): skipped — .feature already carries @task:TASK-DTL-NNN tags matching the canonical IDs we generated

Anchors honoured
DDR-002 (Coach owns F1, handler owns F2/F3, single helper) · DDR-003 (session.completed emits before F3 task scheduled) · CC-13 (fire-and-forget) · D5 (Coach tools=[], structural enforcement) · two-provider invariant · 30s p95 turn budget · 2s session-end budget · I-T6 zero-turn guard

Resolved low-confidence assumptions
ASSUM-006 → record reasoning in full + reasoning_long: bool = True flag (no truncation, no rejection)
ASSUM-011 → GRAPHITI_DRAIN_WINDOW = 5.0 constant on TASK-GSM-004 helper (consumed via default by TASK-DTL-005)
Cross-feature dependency to confirm
⚠️ TASK-GSM-004 (shared async write helper) must expose: write_misconception(...), write_session_episode(...), and drain(timeout=GRAPHITI_DRAIN_WINDOW). See §4 Integration Contracts for the consumer expectations.

Next steps
Review the data-flow diagram (§2) — most important artefact.
Confirm TASK-GSM-004's helper surface against §4 contracts.
Begin Wave 1: /task-work TASK-DTL-001 ‖ /task-work TASK-DTL-004.
Or autonomously: /feature-build FEAT-PH1-003.


GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-PH1-003 --verbose 


════════════════════════════════════════════════════════════
FEATURE RESULT: SUCCESS
════════════════════════════════════════════════════════════

Feature: FEAT-PH1-003 - DeepAgents Tutoring Loop with Coach
Status: COMPLETED
Tasks: 5/5 completed
Total Turns: 7
Duration: 68m 6s

                                  Wave Summary
╭────────┬──────────┬────────────┬──────────┬──────────┬──────────┬─────────────╮
│  Wave  │  Tasks   │   Status   │  Passed  │  Failed  │  Turns   │  Recovered  │
├────────┼──────────┼────────────┼──────────┼──────────┼──────────┼─────────────┤
│   1    │    2     │   ✓ PASS   │    2     │    -     │    4     │      -      │
│   2    │    2     │   ✓ PASS   │    2     │    -     │    2     │      -      │
│   3    │    1     │   ✓ PASS   │    1     │    -     │    1     │      -      │
╰────────┴──────────┴────────────┴──────────┴──────────┴──────────┴─────────────╯

Execution Quality:
  Clean executions: 5/5 (100%)

SDK Turn Ceiling:
  Invocations: 5
  Ceiling hits: 0/5 (0%)

                                  Task Details
╭──────────────────────┬────────────┬──────────┬─────────────────┬──────────────╮
│ Task                 │ Status     │  Turns   │ Decision        │  SDK Turns   │
├──────────────────────┼────────────┼──────────┼─────────────────┼──────────────┤
│ TASK-DTL-001         │ SUCCESS    │    2     │ approved        │      17      │
│ TASK-DTL-004         │ SUCCESS    │    2     │ approved        │      26      │
│ TASK-DTL-002         │ SUCCESS    │    1     │ approved        │      37      │
│ TASK-DTL-003         │ SUCCESS    │    1     │ approved        │      30      │
│ TASK-DTL-005         │ SUCCESS    │    1     │ approved        │      37      │
╰──────────────────────┴────────────┴──────────┴─────────────────┴──────────────╯

Worktree: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-PH1-003
Branch: autobuild/FEAT-PH1-003

Next Steps:
  1. Review: cd /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-PH1-003
  2. Diff: git diff main
  3. Merge: git checkout main && git merge autobuild/FEAT-PH1-003
  4. Cleanup: guardkit worktree cleanup FEAT-PH1-003
INFO:guardkit.cli.display:Final summary rendered: FEAT-PH1-003 - completed
INFO:guardkit.orchestrator.review_summary:Review summary written to /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/FEAT-PH1-003/review-summary.md
✓ Review summary: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/FEAT-PH1-003/review-summary.md
INFO:guardkit.orchestrator.feature_orchestrator:Feature orchestration complete: FEAT-PH1-003, status=completed, completed=5/5






/feature-spec "Primary-text RAG + source-typed quote verifier" \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/phase-1-build-plan.md \
  --context docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md \
  --context docs/research/ideas/cross-repo-rag-impact-analysis-2026-04-24.md \
  --context docs/research/ideas/copyright-training-data-analysis.md \
  --context src/study_tutor/knowledge/student_model.py \
  --context tasks/completed/deepagents-tutoring-loop/TASK-DTL-002-rubric-and-quote-fidelity.md \
  --context tasks/completed/deepagents-tutoring-loop/IMPLEMENTATION-GUIDE.md \
  --context domains/gcse-english/GOAL.md \
  --context domains/gcse-english/sources/README.md \
  --context /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/ingestion/chunker.py \
  --context /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/ingestion/models.py












/feature-plan "Primary-Text RAG and Source-Typed Quote Verifier" \
  --context features/primary-text-rag-and-quote-verifier/primary-text-rag-and-quote-verifier_summary.md \
  --context features/primary-text-rag-and-quote-verifier/primary-text-rag-and-quote-verifier.feature \
  --context features/primary-text-rag-and-quote-verifier/primary-text-rag-and-quote-verifier_assumptions.yaml \
  --context docs/research/ideas/phase-1-scope.md \
  --context docs/research/ideas/phase-1-build-plan.md \
  --context docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md \
  --context docs/research/ideas/cross-repo-rag-impact-analysis-2026-04-24.md \
  --context docs/research/ideas/copyright-training-data-analysis.md \
  --context domains/gcse-english/GOAL.md \
  --context domains/gcse-english/sources/README.md \
  --context src/study_tutor/knowledge/student_model.py \
  --context tasks/completed/deepagents-tutoring-loop/IMPLEMENTATION-GUIDE.md \
  --context tasks/completed/deepagents-tutoring-loop/TASK-DTL-002-rubric-and-quote-fidelity.md \
  --context /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/ingestion/chunker.py \
  --context /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/ingestion/models.py


Feature Planning Complete: FEAT-70A4
Feature: Primary-Text RAG and Source-Typed Quote Verifier
Phase: Phase 1 (FEAT-PH1-004)
Status: Plan ready · all quality gates passed

What was created
Review artefacts
TASK-REV-PRV4 — review task with Context A/B decisions logged
.guardkit/reviews/TASK-REV-PRV4-review-report.md — full technical-options analysis + recommended approach
Feature structure
tasks/backlog/primary-text-rag-and-quote-verifier/
README.md
IMPLEMENTATION-GUIDE.md — data-flow + sequence + dependency diagrams + §4 Integration Contracts (3 contracts)
7 subtask files (TASK-PRV-001 through TASK-PRV-007) with task_type, consumer_context, seam tests, and lint-compliance ACs
Orchestration
.guardkit/features/FEAT-70A4.yaml — 5 waves, smoke gates after waves 2/3/4
Pre-flight validation: ✅ PASSED (7 tasks, 5 waves, 418 estimated minutes)
AC-quality review: ✅ 0 unverifiable acceptance criteria
BDD activation (R2)
34 scenarios tagged across 5 tasks in primary-text-rag-and-quote-verifier.feature:
TASK-PRV-005 (verifier): 16 scenarios
TASK-PRV-002 (loader): 7
TASK-PRV-003 (decision): 5
TASK-PRV-004 (retrieval): 5
TASK-PRV-006 (Coach handover): 1
Wave plan
Wave	Tasks	Notes
1	TASK-PRV-001	Pydantic models foundation
2 (parallel)	TASK-PRV-002, TASK-PRV-003	Loader + decision (different modules)
3 (parallel)	TASK-PRV-004, TASK-PRV-005	Retrieval + verifier
4	TASK-PRV-006	Coach handover seam
5	TASK-PRV-007	Integration smoke + sources README
Pre-implementation sign-offs (settled in review)
All five low-confidence assumptions (ASSUM-008/009/010/011/013) and four medium-confidence assumptions (ASSUM-005/006/007/012/015) have mechanism-level resolutions documented. Open Question 3 (false-positive fuzzy correction) closed via primary-wins precedence + restricting fuzzy correction to primary-text source only.

Next steps

# Manual / interactive
/task-work TASK-PRV-001                    # Wave 1
# Wave 2 in parallel (Conductor recommended)
/task-work TASK-PRV-002
/task-work TASK-PRV-003
# Wave 3 in parallel
/task-work TASK-PRV-004
/task-work TASK-PRV-005
# Then sequentially
/task-work TASK-PRV-006
/task-work TASK-PRV-007

# Or autonomous
/feature-build FEAT-70A4
This unblocks TASK-DTL-002 (quote_fidelity rubric criterion in FEAT-PH1-003) and clears the G1 critical-path gap in phase-1-build-plan.md ahead of the Friday 2 May target.


GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-70A4 --verbose


════════════════════════════════════════════════════════════
FEATURE RESULT: FAILED
════════════════════════════════════════════════════════════

Feature: FEAT-70A4 - Primary-Text RAG and Source-Typed Quote Verifier
Status: FAILED
Tasks: 3/7 completed
Total Turns: 5
Duration: 27m 22s

                                  Wave Summary                                   
╭────────┬──────────┬────────────┬──────────┬──────────┬──────────┬─────────────╮
│  Wave  │  Tasks   │   Status   │  Passed  │  Failed  │  Turns   │  Recovered  │
├────────┼──────────┼────────────┼──────────┼──────────┼──────────┼─────────────┤
│   1    │    1     │   ✓ PASS   │    1     │    -     │    1     │      -      │
│   2    │    2     │   ✓ PASS   │    2     │    -     │    4     │      -      │
╰────────┴──────────┴────────────┴──────────┴──────────┴──────────┴─────────────╯

Execution Quality:
  Clean executions: 3/3 (100%)

SDK Turn Ceiling:
  Invocations: 2
  Ceiling hits: 0/2 (0%)

                                  Task Details                                   
╭──────────────────────┬────────────┬──────────┬─────────────────┬──────────────╮
│ Task                 │ Status     │  Turns   │ Decision        │  SDK Turns   │
├──────────────────────┼────────────┼──────────┼─────────────────┼──────────────┤
│ TASK-PRV-001         │ SUCCESS    │    1     │ approved        │      -       │
│ TASK-PRV-002         │ SUCCESS    │    2     │ approved        │      16      │
│ TASK-PRV-003         │ SUCCESS    │    2     │ approved        │      19      │
╰──────────────────────┴────────────┴──────────┴─────────────────┴──────────────╯

Worktree: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-70A4
Branch: autobuild/FEAT-70A4

Next Steps:
  1. Review failed tasks: cd /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-70A4
  2. Check status: guardkit autobuild status FEAT-70A4
  3. Resume: guardkit autobuild feature FEAT-70A4 --resume
INFO:guardkit.cli.display:Final summary rendered: FEAT-70A4 - failed
INFO:guardkit.orchestrator.review_summary:Review summary written to /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/FEAT-70A4/review-summary.md
✓ Review summary: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/FEAT-70A4/review-summary.md
INFO:guardkit.orchestrator.feature_orchestrator:Feature orchestration complete: FEAT-70A4, status=failed, completed=3/7



/task-create please create a review task to anlayse the failed autobuild feature run in /home/richardwoollcott/Projects/appmilla_github/study-tutor/docs/history/autobuild-FEAT-70A4-failed-history.md


✅ Task Created: TASK-REV-AB7A

📋 Task Details
Title: Analyze failed autobuild run for FEAT-70A4 (Primary-Text RAG + Quote Verifier)
Type: review (diagnostic, standard depth)
Priority: high
Status: backlog
Tags: [autobuild, post-mortem, FEAT-70A4, smoke-gate, parallel-contention, diagnostic]
Complexity: 5

📑 Source artefact
docs/history/autobuild-FEAT-70A4-failed-history.md (869 lines)

🔍 Failure surfaces scoped for review
1. Post-wave-2 smoke-gate exit=127 (interpreter/import-path mismatch suspected)
2. Wave-2 parallel-contention warning on TASK-PRV-002 (independent tests skipped)
3. Conditional-approval policy fit for a pure-Python loader feature
4. Recurring Coach SDK message-reader fatal errors
5. Missing seam/contract tests for cross-boundary work

📁 File Location
tasks/backlog/TASK-REV-AB7A-analyze-failed-autobuild-feat-70a4.md

Next Steps:
1. Review task scope and acceptance criteria
2. When ready: /task-review TASK-REV-AB7A --mode=diagnostic
3. After [A]/[I]/[R]/[C] decision: /task-complete TASK-REV-AB7A
The task captures all five diagnostic threads — exit=127 on the post-wave-2 smoke gate is the headline failure (wave 1+2 had already passed), with the parallel-contention conditional-approval rule and the missing seam tests as secondary concerns worth ruling on before any resume.

/task-review TASK-REV-AB7A --mode=diagnostic


Diagnostic complete. Report written to .claude/reviews/TASK-REV-AB7A-report.md.

REVIEW COMPLETE — TASK-REV-AB7A
Mode: diagnostic | Depth: standard | Findings: 5 | Recommendations: 5 fix subtasks

Two compounding root causes (both reproduced locally)
Smoke gate exit=127 — FEAT-70A4.yaml invokes bare python; Ubuntu 24 ships only python3. The bootstrap venv at .guardkit/venv/bin/python was correctly built with an editable install of study-tutor, but guardkit.orchestrator.smoke_gates doesn't honour coach_pytest_interpreter. I reproduced exit=127 from a clean shell and confirmed the venv copy passes (Appendix A).
Wave-2 "parallel contention" was source-file contention — TASK-PRV-002 and TASK-PRV-003 both wrote step definitions to the same 888-line BDD glue file features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py. Independent verification ran a combined pytest against an inconsistent file. Coach's conditional-approval rule fired with requires_infra=[] — a signal the rule should have treated as "not infra contention, don't auto-approve."
Most concerning finding (latent)
Both PRV-002 and PRV-003 task files contained explicit ## Seam Tests sections with full code stubs. Players ignored them. Coach flagged "no seam/contract/boundary tests detected" 4× but didn't block. We have approved code whose contracts (consumed by PRV-004/005/006) have never been verified.

Decision Options
[A]ccept	File findings only. Worktree stays preserved; you apply fixes manually.
[I]mplement	Create FEAT-FIX-AB7A with 5 subtasks (smoke-gate pin, 2 parallel seam-test backfills, wave-3 serialisation, autobuild resume). ~50 min edits + ~25 min wall-clock. Recommended.
[R]evise	Deepen analysis — e.g. run PRV-002/003 seam tests now to settle whether conditional approval was sound.
[C]ancel	Discard. Not recommended; diagnosis is settled.
5 upstream-guardkit findings (smoke_gates interpreter resolution, conditional-approval requires_infra=[] rule, planner overlap detection, seam-test blocking, SDK reader transport noise) are filed in §9 of the report — out of scope for this fix feature.

Your choice [A/I/R/C]?

autobuild-FEAT-70A4-failed-history.md
[R]evise are the suggested tasks for this repo or guardkit? Please dig deeper and trace the execution flow across system and technological boundaries and creatre C4 sequence diagrams to validate your findings. We need to ensure no regressions are introduced into autobuild as we have a lot of critical development to do


Addendum written: .claude/reviews/TASK-REV-AB7A-addendum-source-traced.md

REVIEW REVISED — Source-Traced + C4 Diagrams
Scope answer (the question you asked first)
All 5 FIX-AB7A- subtasks land in THIS repo. Zero require guardkit changes.*

Layer	Tasks	Files
THIS repo (study-tutor)	FIX-AB7A-001 (smoke-gate pin), 002 (PRV-002 seam), 003 (PRV-003 seam), 004 (wave serialisation), 005 (resume)	.guardkit/features/FEAT-70A4.yaml + 2 new test files
GuardKit upstream (separate repo)	GK-UPSTREAM-1..5	filed for the future, do not block resume
GuardKit is editable-installed at /home/richardwoollcott/Projects/appmilla_github/guardkit — I read the active source.

What the source confirmed (3 critical findings)
Smoke-gate is uniquely broken. smoke_gates.run_smoke_gate(config, cwd, wave_number) has no interpreter parameter and subprocess.run(...) at line 163 has no env= argument. Every other GuardKit shell-out does inject the venv PATH (e.g., coach_validator.py:2452). And the build_venv_env helper at command_models.py:79-96 only checks .venv/bin, while bootstrap creates .guardkit/venv/bin — so the helper would have returned None even if smoke_gates had called it. Two compounding upstream defects.

The existing TASK-ABFIX-005 isolation cannot fix our parallel-contention class. It snapshots the worktree to a tempdir to defend against concurrent mutation during test execution. Both PRV-002 and PRV-003 had committed conflicting edits to the shared 888-line BDD glue before either Coach phase started — the snapshot preserved the contaminated state. No upstream rule change would have caught this; serialisation is the durable fix.

The conditional-approval parallel_contention branch at coach_validator.py:861-866 does NOT check requires_infra — by design (TASK-ABFIX-005 deliberately broadened it). Sound for transient infra contention, unsound for source-file conflicts. Our fix sidesteps the whole rule by removing the source of the conflict (serialise wave 3).

Diagrams included in addendum
§1 C4 L1 System Context — shows the worktree as a shared-write hazard and smoke-gate as the only consumer that bypasses the venv
§2 Bootstrap → Smoke-Gate Sequence — proves the interpreter mismatch with verbatim source quotes
§3 Wave-2 Parallel Sequence — proves the BDD-glue file contention pattern
§4 Conditional-Approval Decision Tree — shows which branch fired and why
§5 Resume-with-fixes Sequence — proves the local fix is byte-for-byte non-regressive for other features
Pre-resume gate conditions (now mandatory, see §6 of addendum)
5 commands the operator runs in this repo before --resume. If any fail (especially the seam tests), do NOT resume — escalate to a code-fix subtask. This is the safety net the conditional-approval rule didn't provide.

Decision options (re-presented)
[A]ccept	File findings; manual fix later.
[I]mplement	Spawn FEAT-FIX-AB7A with 5 subtasks (all local). Optionally also draft text for the 5 GK-UPSTREAM-* GitHub issues against the guardkit repo. Recommended.
[R]evise again	Further drilling. Suggest: read the actual diff in the BDD glue file between turn-1 and turn-2 commits to prove the file-contention hypothesis with a literal three-way merge view.
[C]ancel	Discard. Not recommended.
Your choice [A/I/R/C]? (And: do you want the GK-UPSTREAM-* issue drafts bundled if you choose [I]?)

TASK-REV-AB7A-addendum-source-traced.md
[I]mplement and can you use the task toll to invoke /task-create on the guardkit repo directly-I don't bother with github issues


[I]mplement Complete
What was created
In this repo (study-tutor) — FEAT-FIX-AB7A
Parent review task moved: tasks/in_review/TASK-REV-AB7A-analyze-failed-autobuild-feat-70a4.md — status: review_complete, decision: implement, linked to feat-fix-ab7a folder
Implementation feature folder: tasks/backlog/feat-fix-ab7a/
README.md
IMPLEMENTATION-GUIDE.md — wave plan + pre-resume verification commands
TASK-FIX-AB7A-001 — pin smoke-gate interpreter (wave 1, direct, ~5 min)
TASK-FIX-AB7A-002 — backfill PRV-002 seam test (wave 2, task-work, ~20 min)
TASK-FIX-AB7A-003 — backfill PRV-003 seam test (wave 2, task-work, ~20 min)
TASK-FIX-AB7A-004 — serialise wave 3 (wave 3, direct, ~10 min)
TASK-FIX-AB7A-005 — resume autobuild (wave 4, manual, ~25 min wall-clock)
In the guardkit repo — 5 upstream tasks (high → low priority)
Task	Priority	What
TASK-FIX-A7B1	high	smoke_gates: honour bootstrap venv interpreter
TASK-FIX-A7B2	high	tighten parallel_contention conditional approval (detect source-file conflicts)
TASK-FIX-A7B3	medium	/feature-plan: warn/auto-serialise on wave-internal source overlap
TASK-FIX-A7B4	medium	Coach should BLOCK (not warn) on planned-but-unimplemented seam tests
TASK-FIX-A7B5	low	investigate Claude Agent SDK message-reader transport failures
All five live at /home/richardwoollcott/Projects/appmilla_github/guardkit/tasks/backlog/TASK-FIX-A7B*.md, follow the local convention (external_reference block, task_type: bugfix, AC-NNN numbering), and cite verified file:line refs in active guardkit source. No git operations performed — they're sitting in the repo's own backlog ready for the guardkit team to pick up.

Recommended next step

/task-work TASK-FIX-AB7A-001
Then waves 2–4 per IMPLEMENTATION-GUIDE.md. The seam-test gate between wave 3 and wave 4 is mandatory — if either seam test fails locally, halt and triage before resume. That's the safety net the conditional-approval rule didn't provide.


════════════════════════════════════════════════════════════
FEATURE RESULT: SUCCESS
════════════════════════════════════════════════════════════

Feature: FEAT-70A4 - Primary-Text RAG and Source-Typed Quote Verifier
Status: COMPLETED
Tasks: 7/7 completed
Total Turns: 9
Duration: 54m 59s

                                  Wave Summary                                   
╭────────┬──────────┬────────────┬──────────┬──────────┬──────────┬─────────────╮
│  Wave  │  Tasks   │   Status   │  Passed  │  Failed  │  Turns   │  Recovered  │
├────────┼──────────┼────────────┼──────────┼──────────┼──────────┼─────────────┤
│   1    │    1     │   ✓ PASS   │    1     │    -     │    1     │      -      │
│   2    │    2     │   ✓ PASS   │    2     │    -     │    4     │      -      │
│   3    │    1     │   ✓ PASS   │    1     │    -     │    1     │      -      │
│   4    │    1     │   ✓ PASS   │    1     │    -     │    1     │      -      │
│   5    │    1     │   ✓ PASS   │    1     │    -     │    1     │      -      │
│   6    │    1     │   ✓ PASS   │    1     │    -     │    1     │      -      │
╰────────┴──────────┴────────────┴──────────┴──────────┴──────────┴─────────────╯

Execution Quality:
  Clean executions: 7/7 (100%)

SDK Turn Ceiling:
  Invocations: 4
  Ceiling hits: 0/4 (0%)

                                  Task Details                                   
╭──────────────────────┬────────────┬──────────┬─────────────────┬──────────────╮
│ Task                 │ Status     │  Turns   │ Decision        │  SDK Turns   │
├──────────────────────┼────────────┼──────────┼─────────────────┼──────────────┤
│ TASK-PRV-001         │ SKIPPED    │    1     │ already_comple… │      -       │
│ TASK-PRV-002         │ SKIPPED    │    2     │ already_comple… │      -       │
│ TASK-PRV-003         │ SKIPPED    │    2     │ already_comple… │      -       │
│ TASK-PRV-004         │ SUCCESS    │    1     │ approved        │      30      │
│ TASK-PRV-005         │ SUCCESS    │    1     │ approved        │      26      │
│ TASK-PRV-006         │ SUCCESS    │    1     │ approved        │      48      │
│ TASK-PRV-007         │ SUCCESS    │    1     │ approved        │      37      │
╰──────────────────────┴────────────┴──────────┴─────────────────┴──────────────╯

Worktree: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-70A4
Branch: autobuild/FEAT-70A4

Next Steps:
  1. Review: cd /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-70A4
  2. Diff: git diff main
  3. Merge: git checkout main && git merge autobuild/FEAT-70A4
  4. Cleanup: guardkit worktree cleanup FEAT-70A4
INFO:guardkit.cli.display:Final summary rendered: FEAT-70A4 - completed
INFO:guardkit.orchestrator.review_summary:Review summary written to /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/FEAT-70A4/review-summary.md
✓ Review summary: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/autobuild/FEAT-70A4/review-summary.md
INFO:guardkit.orchestrator.feature_orchestrator:Feature orchestration complete: FEAT-70A4, status=completed, completed=7/7




can we create the phase-2-build-plan now before we have actually implemented FEAT-70A4? Or is it safer to wait for that to build first?
Drafting now is the safer-than-it-sounds option, because the contracts FEAT-70A4 will produce — VerifierMetadata, RetrievalDecision, source-type chunk shape — are already documented in the IMPLEMENTATION-GUIDE before implementation, so Phase 2's "what does this build on" surface is settled. The original Phase 1 plan also schedules this for Thursday (today) precisely so that drafting and the Friday FEAT-70A4 finish run in parallel rather than serially.

The tradeoff: anything that depends on Phase 1 empirical outcomes — Coach calibration, real turn latencies, ingestion-pipeline integration friction, observed misconception patterns — should be flagged as "to revise after Phase 1 closes" rather than locked in. So: draft it now, but with explicit "TBD after Phase 1 measures X" markers wherever the plan would otherwise pretend to know something it can't yet.

Want me to read phase-2-scope.md and draft a phase-2-build-plan.md skeleton in that shape?

yes please proceed use extra thinking/don't rush let's get this right first time

Phase 2 Build Plan Drafted
File: docs/research/ideas/phase-2-build-plan.md — 8,494 words, 32 sections.

Verification
All 10 phase-2-scope.md success criteria explicitly addressed (gamification engine, session-end response, dashboard, demo video, tech writeup, submission form, repo gate-check, Reachy outcome, validation gate, Lilymay informal marker)
8 TBD markers consolidated with revisit triggers + default-if-unresolved fallbacks
All day labels calendar-true for May 2026 — 30 April = Thursday, 1 May = Friday, 2-3 May = Saturday-Sunday, 18 May = Monday. The scope and Phase-1-build-plan have a slight date-label drift (they call 1 May "Thursday"); I noted this explicitly at the top under "Date-label convention" and used calendar-true throughout my own scheduling so the day-by-day plan maps onto real Saturdays and Sundays
Branching for FEAT-PH1-004 outcome — Path A (verifier ships) and Path B (5-criterion fallback) both accommodated; Phase 2 build plan structure is identical under either
Reachy go/no-go scheduled for the natural calendar slot Sunday 3 May with a note that DEC-06's literal "4 May" string can be honoured by slipping to Monday evening
Day-by-day shape
Sat 2 May — Validation gate + system-arch refresh + FEAT-PH2-001 spec/plan/Wave 1 + Session 1 capture (working-today)
Sun 3 May — FEAT-PH2-001 Waves 3–5 + Reachy go/no-go + tech writeup gamification section
Mon 4 May — FEAT-PH2-001 verification + multi-session run
Tue 5 May — FEAT-PH2-002 spec + first Claude Design pass
Wed 6 May — Dashboard polish OR fallback + Session 2 capture (architecture reveal)
Thu 7 May — FEAT-PH2-003 spec + demo script + first edit pass
Fri 8 May — Session 3 capture + Phase 2 close-out tag
Sat 9 May → Sat 16 May — Polish track (tech writeup, demo edit, repo gate-check, submission form, Reachy capture if applicable)
Sun 17 May / Mon 18 May — Buffer + deadline
Three load-bearing TBD-revisit triggers
Friday 1 May evening — FEAT-PH1-004 build outcome → Path A or Path B
Saturday 2 May AM — Real turn p50/p95 + Coach signal quality (from Phase 1 demo session log)
Tuesday 5 May evening — Claude Design quality bar → polish iteration vs hand-coded fallback
The plan is revisable on Saturday 2 May morning if the validation gate surfaces drift not anticipated here.


Thanks I've just had a text message to confirm delivery of the first Reachy Mini robot for Friday 8th May - please can you revisit the build plan with that additonal scope/context


Summary of the Reachy revision
Material changes:

Go/no-go gate moves from speculative Sunday 3 May → Saturday 9 May (post-delivery unbox + SDK hello-world). Five evaluation criteria with hardware-state focus.
Live Reachy segment elevates from possible-fallback to likely-outcome. Capture target Wednesday 13 May (~1.5h capture session, parent-query scenario).
Future-vision segment becomes the late-stage fallback only if Saturday's go/no-go fails or integration is blocked by Tuesday's capture-readiness checkpoint.
Reachy integration thread runs in parallel Sat 9 → Tue 12 May per DEC-06 — outside Phase 2's day-by-day, ~6-8h additional outside the table.
Schedule deltas:

Sun 3 May: 5h → 3h (Reachy slot freed for recovery slack)
Sat 9 May: 3h → 4h (Reachy unbox AM + tech writeup PM)
Wed 13 May: 1h → 2-3h (Reachy capture + demo video polish)
Fri 15 May: now contingent on Wed capture quality
Risk register updated — dropped "hardware doesn't arrive" (resolved); added "unbox blocks DOA", "integration learning curve > 4 days", "delivery slips past 8 May despite confirmation".

10-day Reachy thread runway from delivery to submission deadline — feasible for the 30-second demo segment per the conversation starter doc, tight for anything more ambitious.

Want me to push, or hold for review?























/feature-spec "Graphiti runtime integration repair — wire local LLM + embedder via llama-swap on GB10:9000 (no cloud APIs per DECISION-DF-001); load config from .guardkit/graphiti.yaml; mirror guardkit's canonical OpenAIGenericClient/OpenAIEmbedder pattern; re-seed Lilymay; run end-to-end MCP demo" \
  --context tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md \
  --context docs/research/ideas/phase-1-validation.md \
  --context src/study_tutor/knowledge/graphiti_client.py \
  --context src/study_tutor/knowledge/queries.py \
  --context src/study_tutor/knowledge/async_write.py \
  --context src/study_tutor/knowledge/student_model.py \
  --context src/study_tutor/knowledge/episodes.py \
  --context scripts/seed_student_model.py \
  --context tests/unit/knowledge/test_async_write.py \
  --context .guardkit/graphiti.yaml \
  --context ../guardkit/guardkit/knowledge/graphiti_client.py \
  --context ../guardkit/docs/research/dgx-spark/README.md \
  --context ../guardkit/docs/research/dgx-spark/RESULTS-v3-production-deployment.md \
  --context ../guardkit/docs/research/dgx-spark/llama-swap-config.yaml




━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEATURE SPEC COMPLETE: Graphiti Runtime Integration Repair
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Files written:
  features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair.feature
  features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair_assumptions.yaml
  features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair_summary.md

Scenarios: 24 total (22 blocks; 2 outlines × 2 examples)
  @key-example: 5    @boundary: 4
  @negative: 5       @edge-case: 11
  @smoke: 6          @regression: 1

Group breakdown:
  A Key examples · 5    B Boundary · 4    C Negative · 4
  D Edge cases · 5      E Security · 2    F Concurrency · 2
  G Integration · 2

Assumptions: 3 total
  high: 0
  medium: 3 (Coach review recommended)
  low: 0

Dropped after review: 3 (tutor-turn budget, smoke-test budget, rate-limit
burst size) — moved to implementer_hints in the assumptions manifest.

Deferred: 0

Next steps:
  Review:  features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair.feature
  Pass to feature-plan:
    /feature-plan "Graphiti Runtime Integration Repair" \
      --context features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair_summary.md \
      --context tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━




/feature-plan "Graphiti Runtime Integration Repair" \
  --context features/graphiti-runtime-integration-repair/graphiti-runtime-integration-repair_summary.md \
  --context tasks/backlog/TASK-PH2-GR-001-graphiti-runtime-integration-repair.md

Feature Planning Complete: FEAT-FD32
Feature: Graphiti Runtime Integration Repair
Review: TASK-REV-GR1A (78/100, complete)
Parent task: TASK-PH2-GR-001 (now linked to feature + 5 subtasks)

Generated artefacts
Artifact	Path
Feature YAML	.guardkit/features/FEAT-FD32.yaml
Implementation guide (with Mermaid + §4)	tasks/backlog/graphiti-runtime-integration-repair/IMPLEMENTATION-GUIDE.md
README	tasks/backlog/graphiti-runtime-integration-repair/README.md
Review report	.claude/reviews/TASK-REV-GR1A-review-report.md
Wave structure (5 waves, sequential)
Wave	Task	task_type	Complexity
1	TASK-GR-LOAD	feature	4
2	TASK-GR-WIRE	feature	5
3	TASK-GR-SMOK	testing	4
4	TASK-GR-SEED	feature	4
5	TASK-GR-DEMO	feature	3
Pipeline checks
✅ Mermaid diagrams (data flow + integration sequence + task dependency graph) present in IMPLEMENTATION-GUIDE.md
✅ §4 Integration Contracts: 4 contracts (GraphitiConnectionConfig, WiredGraphitiClient, LilymaySeed, MCP session episode)
✅ Seam test stubs in every consumer task (TASK-GR-WIRE, TASK-GR-SMOK, TASK-GR-SEED, TASK-GR-DEMO)
✅ consumer_context blocks on all consumer tasks
✅ task_type field on every task (CoachValidator profile selection works)
✅ Lint compliance AC on every feature/refactor task
✅ AC-quality linter: 0 unverifiable ACs detected
✅ Pre-flight validation: FeatureLoader.validate_feature() returns no issues
✅ smoke_gates: configured to fire constructor-shape tests after Waves 2 and 3 (catches the silent-default bug class this whole feature exists to repair)
✅ Step 11 BDD-linker: status=skipped, reason=all_tagged (idempotency — all 24 scenarios already @task:TASK-PH2-GR-001)
Next steps

# Sequential (recommended for first run)
/task-work TASK-GR-LOAD

# Or autobuild (per Q2 = D)
/feature-build FEAT-FD32
Wave 5 (TASK-GR-DEMO) is human-in-the-loop and requires Claude Desktop with the study-tutor MCP server — autobuild will pause for the live session per AC-DEMO-01.


GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-FD32 --verbose



/task-create please create a review task to investigate the failing autobuild feature in /Users/richardwoollcott/Projects/appmilla_github/study-tutor/docs/history/autobuild-FEAT-FD32-failed-run-1-history.md


/task-review TASK-REV-FD32 --mode=debugging



GUARDKIT_AUTOBUILD_TASK_TIMEOUT_FLOOR=4500 \
         guardkit autobuild feature FEAT-FD32 --resume






Operator follow-ups still owed (per the manual completions in TASK-GR-SEED + TASK-GR-DEMO):
  1. Live FalkorDB seed + read-back evidence (TASK-GR-SEED playbook)
  2. Live Claude Desktop tutoring session driving G3/G4/G5/G6/G13 evidence into the scaffolded tables in phase-1-validation.md and
  graphiti-latency-spike-results.md


/task-work TASK-GR-SEED


Outcome — Wave 5 retry: still red, but for a different reason
Seed run 5: 13min wall-clock, 25 scheduled / 3 succeeded / 22 failed. Verify confirms graph still empty for student-lilymay. Task moved to tasks/blocked/. phase-1-validation.md updated with full Wave 5 retry findings, R-WAVE5-03 + R-WAVE5-04 entries, and updated AC-SEED-XX status table.

The actual blocker (R-WAVE5-03)
Wave 4's narrative was wrong about what was breaking. The vLLM rate-limit story (R-WAVE5-01) was a plausible misreading of partial logs — the real issue is a hard graphiti-core × FalkorDB × RediSearch incompatibility:

graphiti-core's GroupIdValidationError only allows [A-Za-z0-9_-] → forced project to use student-lilymay
graphiti-core's RediSearch fulltext query parses student-lilymay as student NOT lilymay → query syntax error
First 3 writes succeed (empty RELATES_TO index, no entity-resolution lookup); writes 4-25 fail (index now populated, every lookup hits the broken query)
Independently corroborated through MCP: mcp__graphiti__search_nodes(query="Lilymay", group_ids=["student-lilymay"]) returns the same RediSearch syntax error — meaning AC-SEED-02 as written is currently unverifiable through MCP at all.

Decision required — three remediation paths
#	Path	Blast radius	Trade-off
1	Monkey-patch graphiti-core to escape group_ids in fulltext query construction (\- or {}-wrapping per RediSearch escaping rules). Lives in study_tutor.knowledge.graphiti_client, intercepting the FalkorDB driver at import time.	Smallest. Group_id format stays student-lilymay; no downstream code touched.	Carries an upstream-dependency wart; needs to be revisited when graphiti-core releases a fix.
2	Migrate group_id format dash → underscore (student_lilymay, subject_english_literature, fleet_appmilla).	Touches the post-a210472 normalisation surface: student_model.py, the test fixtures updated in that commit, operator docs that cite the dash form, the noted-divergent specialist-agent reference.	No upstream wart, but reopens a migration that already shipped.
3	Switch graph backend FalkorDB → Neo4j. Lucene fulltext syntax doesn't treat - as NOT.	Largest. Cascades into ADR-ARCH-018 / ADR-ARCH-019 territory.	Overkill for this issue alone; only worth it if other Neo4j-vs-FalkorDB tradeoffs are already in play.
My read: option 1 is the right next move — smallest blast radius, validates the diagnosis, unblocks the seed, leaves option 2 available later if upstream graphiti-core stays unfixed for a long time. But this is a real architectural choice and I shouldn't make it for you.

There's also a secondary signal worth flagging: R-WAVE5-04 (Connection closed by server reappearing on read-only paths during verify) — Wave 4 marked AC-SEED-06 as "no escalation observed", but it's now intermittently reappearing. May need a separate FalkorDB-side investigation regardless of which R-WAVE5-03 path you pick.

Which path do you want to take, or do you want to investigate further first?


please provide details of what you are recommending for option 1 - where does graphiti-core live? Is it guardkit repo source code or the actual open source getzep repo? My honest take on graphiti is its a buggy piece of shit - half my work seems to be working around bugs etc in it not working and everytime I think it's all ok and we can move on there is something else.

Fair venting — and the validation doc backs it up empirically: this is now the 5th distinct graphiti-core workaround in the project (Read API mismatch, Write API mismatch, GroupIdValidationError migration, OpenAI default LLM client, and now the RediSearch dash-as-NOT bug). That's signal, not noise. Let me get you the concrete details before you decide.


Where graphiti-core lives
It's the upstream getzep package (PyPI: graphiti-core), pinned >=0.29,<0.30 in your pyproject.toml, installed at .venv/lib/python3.14/site-packages/graphiti_core/. Not vendored anywhere in your repo or in guardkit. Source repo: github.com/getzep/graphiti. So a "monkey-patch" means importing graphiti-core normally, then mutating its functions at runtime from your own code in study_tutor/knowledge/.

The smoking gun
Look at falkordb_driver.py:406-410:


# Escape group_ids with quotes to prevent RediSearch syntax errors
# with reserved words like "main" or special characters like hyphens
escaped_group_ids = [f'"{gid}"' for gid in group_ids]
group_values = '|'.join(escaped_group_ids)
group_filter = f'(@group_id:{group_values})'
Upstream already tried to fix this exact bug. The comment explicitly mentions "special characters like hyphens." But the fix is wrong — wrapping in double-quotes does NOT prevent RediSearch from parsing the dash inside as a NOT operator. The runtime error proves it: query is (@group_id:"student-lilymay") (quotes present in the actual SQL we logged), syntax error at offset 19 (the dash).

Same broken code is duplicated in falkordb/operations/search_ops.py:105-107 — both call sites would need patching.

The correct RediSearch escape for hyphens is either backslash-escape (\-) or verbatim-brace wrap ({student-lilymay} — RediSearch treats the contents as opaque). Quotes alone don't cut it.

What the patch actually looks like
A new file src/study_tutor/knowledge/graphiti_patches.py, ~40 lines:


"""R-WAVE5-03 — graphiti-core 0.29 fails to escape dashes in RediSearch
fulltext queries on FalkorDB. Upstream attempted a fix in
falkordb_driver.py:406-410 (double-quote wrap) but the fix is wrong:
RediSearch still parses dashes as NOT operators inside double quotes.

This patch overrides both call sites with brace-wrapped verbatim values,
which RediSearch treats as opaque tokens. Remove once upstream ships a
real fix (track issue: TBD — open against getzep/graphiti).
"""
from graphiti_core.driver import falkordb_driver
from graphiti_core.driver.falkordb.operations import search_ops

_STOPWORDS = falkordb_driver.STOPWORDS  # reuse upstream's stopword list


def _brace_wrap(group_ids):
    return [f'{{{gid}}}' for gid in group_ids]


def _patched_build_fulltext_query(self, query, group_ids=None, max_query_length=128):
    falkordb_driver.validate_group_ids(group_ids)
    if not group_ids:
        group_filter = ''
    else:
        group_filter = f'(@group_id:{"|".join(_brace_wrap(group_ids))})'
    sanitized = self.sanitize(query)
    words = [w for w in sanitized.split() if w and w.lower() not in _STOPWORDS]
    sanitized = ' | '.join(words)
    if len(sanitized.split(' ')) + len(group_ids or '') >= max_query_length:
        return ''
    return group_filter + ' (' + sanitized + ')'


def _patched_search_ops_query(query, group_ids=None, max_query_length=...):
    # mirror image of above — same brace-wrap fix
    ...


def install():
    falkordb_driver.FalkorDriver.build_fulltext_query = _patched_build_fulltext_query
    search_ops._build_falkor_fulltext_query = _patched_search_ops_query
Then in graphiti_client.py, add from .graphiti_patches import install as _install_patches; _install_patches() at the top so the patch is in place before any FalkorDriver instance is constructed.

Risks I'd flag before doing this:

Upstream's "fix" already shipped, untested against real FalkorDB. That's a process-smell on the getzep side. Whatever tests they ran for the double-quote version, they didn't actually run the query through RediSearch with a non-empty index. My patch needs the same scrutiny — write it, then run the seed end-to-end (the 3-good-then-22-bad pattern only manifests once the index has data, so a 5-write smoke test would falsely look green).
Two call sites is a code-smell — getzep duplicated the function. Version 0.30 might add a third call site or refactor the duplication, and either move re-bakes the patch.
Brace-wrap may interact with multi-value group_id queries ((@group_id:val1|val2)) — would need to test that a query targeting multiple group_ids still parses. Backslash-escape is the safer bet on that axis but uglier on the eye.
Time: ~1h to write + smoke-test the patch, ~30-60min to re-run seed, ~15min to verify + flip G2/G3. Total ~2-3 hours.

On the broader frustration — that's a real signal
You're not wrong, and the project history backs it up. Counting from the validation doc + this session:

#	Bug	Workaround
1	get_client(config) defaulted to OpenAI 401	Wave 2 wired LLM/embedder explicitly
2	Read API mismatch (search_nodes doesn't exist)	New _read_student_partition seam in queries.py
3	Write API mismatch (add_episode kwargs wrong)	_add_episode_kwargs helper in async_write.py
4	GroupIdValidationError rejects colons	Migrated student: → student- (commit a210472)
5	RediSearch dashes-as-NOT — and upstream's "fix" doesn't work	This task
That's five distinct upstream defects in a few weeks, on a single integration. Bug #5 is especially concerning because the upstream fix attempt makes it look like getzep tested it, and they didn't. If anything, that's a stronger argument for considering whether to keep paying the graphiti tax.

A few alternatives worth at least naming, even if you stick with option 1 for now:

Replace graphiti-core with a thin direct-FalkorDB layer. Your project's actual surface is small (get_student_state, _perform_write, the seed), and a custom writer + querier might be a few hundred lines. You'd lose graphiti's entity-resolution / fact-extraction, but a glance at the seed says you're not really using those — the seed has structured data, not free text needing extraction.
Drop graph framing entirely. A flat learner profile in JSONB on Postgres (or sqlite) covers the read/write surface the project currently uses. Phase 2 features that genuinely need a graph can adopt one later.
Open an upstream issue + wait. The dashes-as-NOT bug is a 5-line fix and trivially demonstrable; an active maintainer should land it fast. But "fast" upstream usually means weeks, and you have FEAT-FD32 to land.
Keep paying the graphiti tax (option 1). Pragmatic if you're attached to the entity-resolution / temporal-fact features for Phase 2+ — but the bug-rate suggests budgeting time for #6.
Happy to do any of: (a) write + smoke-test the option-1 patch, (b) sketch what a graphiti-replacement layer would look like for your actual usage, (c) draft the upstream issue, (d) something else. What's the call?

So my one-liner pick: /task-review TASK-FORK-PATCH --mode=decision --depth=standard --no-questions from the graphiti fork dir.





GUARDKIT_LOG_LEVEL=DEBUG guardkit autobuild feature FEAT-1773 --verbose 