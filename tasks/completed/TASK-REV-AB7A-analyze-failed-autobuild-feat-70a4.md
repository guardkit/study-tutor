---
id: TASK-REV-AB7A
title: "Analyze failed autobuild run for FEAT-70A4 (Primary-Text RAG + Quote Verifier)"
task_type: review
review_mode: diagnostic
review_depth: standard
status: review_complete
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
priority: high
tags: [autobuild, post-mortem, FEAT-70A4, smoke-gate, parallel-contention, diagnostic]
complexity: 5
context_files:
  - docs/history/autobuild-FEAT-70A4-failed-history.md
  - .guardkit/autobuild/FEAT-70A4/review-summary.md
  - .guardkit/features/FEAT-70A4.yaml
  - tasks/in_review/TASK-REV-PRV4-plan-primary-text-rag-and-quote-verifier.md
  - tasks/backlog/primary-text-rag-and-quote-verifier/
review_results:
  mode: diagnostic
  depth: standard
  decision: implement
  report_path: .claude/reviews/TASK-REV-AB7A-report.md
  addendum_path: .claude/reviews/TASK-REV-AB7A-addendum-source-traced.md
  findings_count: 5
  recommendations_count: 5
  revision: source-traced with C4 sequence diagrams
  implementation_feature: FEAT-FIX-AB7A
  implementation_path: tasks/backlog/feat-fix-ab7a/
  upstream_filings: 5
  completed_at: 2026-04-30T00:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Analyze failed autobuild run for FEAT-70A4 (Primary-Text RAG + Quote Verifier)

## Context

`guardkit autobuild feature FEAT-70A4 --verbose` (run 2026-04-30, "Fresh"
restart) ended in **FEATURE: FAILED** at 27m 22s with **3/7 tasks
completed**. The full transcript is captured at
[docs/history/autobuild-FEAT-70A4-failed-history.md](../../docs/history/autobuild-FEAT-70A4-failed-history.md);
the orchestrator-emitted summary lives at
`.guardkit/autobuild/FEAT-70A4/review-summary.md`.

The feature being built is the Phase-1 Primary-Text RAG + Source-Typed
Quote Verifier — the seven tasks were planned by
[TASK-REV-PRV4](../in_review/TASK-REV-PRV4-plan-primary-text-rag-and-quote-verifier.md)
and live under
[tasks/backlog/primary-text-rag-and-quote-verifier/](./primary-text-rag-and-quote-verifier/).
Because the run halted **before any merge**, the worktree is preserved at
`.guardkit/worktrees/FEAT-70A4` on branch `autobuild/FEAT-70A4`.

## Observed Failure Surface (from transcript)

1. **Wave 1 — TASK-PRV-001 (Pydantic models)** — SUCCESS, 1 turn, approved.
2. **Wave 2 — TASK-PRV-002 (corpus loader) + TASK-PRV-003 (retrieval-decision
   function), parallel** — both eventually approved, but with notable
   warnings:
   - Coach SDK message-reader fatal error on TASK-PRV-001 turn 1
     (`Command failed with exit code 1`) — recovered.
   - `coach_validator: Independent test verification failed for
     TASK-PRV-002 (classification=parallel_contention, confidence=high)`.
   - `Conditional approval for TASK-PRV-002: parallel contention failure
     (wave_size=2), all Player gates passed.` — independent tests
     **skipped** under the conditional-approval rule.
   - Seam-test recommendation surfaced: "no seam/contract/boundary tests
     detected for cross-boundary feature".
3. **Post-Wave-2 Smoke Gate — FAILED (exit=127)**:
   ```
   python -c "from study_tutor.knowledge.corpus_models import \
       CorpusChunk, CitationAnchor, SourceType, \
       PlayCitationAnchor, NovelCitationAnchor"
   pytest tests/unit/knowledge/ -x -q
   ```
   `exit=127` ⇒ command-not-found / interpreter resolution issue
   (or import resolution against a different Python). The orchestrator
   bootstrapped the venv at
   `.guardkit/worktrees/FEAT-70A4/.guardkit/venv/bin/python` and pinned
   Coach pytest to that interpreter, but the smoke-gate hook appears to
   have invoked the bare system `python`. Subsequent waves were not
   started; the worktree was preserved.
4. **Final tally** — completed: TASK-PRV-001, TASK-PRV-002, TASK-PRV-003.
   Not started: TASK-PRV-004 (source-filtered retrieval + reranker),
   TASK-PRV-005 (verifier), TASK-PRV-006 (Coach handover seam),
   TASK-PRV-007 (integration smoke + sources README).

## Scope of Review

### In scope

- **Root-cause the smoke-gate `exit=127`** — confirm whether the gate
  invoked the system Python (PEP 668 path) instead of the bootstrap
  venv interpreter, and whether the package was installed editable
  into that venv. Inspect:
  - `guardkit.orchestrator.smoke_gates` interpreter resolution vs
    `coach_pytest_interpreter` set on Phase 1.
  - `.guardkit/features/FEAT-70A4.yaml` smoke-gate `cwd` / shell flag.
  - The actual import path: did the worktree contain
    `src/study_tutor/knowledge/corpus_models.py` or a flat-layout
    equivalent at the time the gate ran?
- **Root-cause the wave-2 parallel-contention failure on
  TASK-PRV-002** — what shared resource (FalkorDB? embedder? file
  locks under the shared worktree?) caused independent test
  verification to fail. Decide whether `wave_size=2` is safe for
  this feature or whether wave-2 should serialise.
- **Conditional-approval policy review** — the orchestrator
  approved TASK-PRV-002 *despite* independent test failure on the
  basis of `parallel_contention + all_gates_passed + docker_available`.
  Is that the right rule for THIS feature (pure-Python loader, no
  infra dependency)? Should the policy require Docker-isolation
  or wave-1 retry instead?
- **Coach SDK reader fatal error** — recurring `Fatal error in
  message reader: Command failed with exit code 1`. Determine if
  this is a Claude Agent SDK transport issue, a flaky subprocess,
  or symptomatic of a bigger problem (resource exhaustion, FD
  limit, embedder timeout).
- **Seam-test gap** — the Coach validator flagged "no seam/contract/
  boundary tests detected for cross-boundary feature". Decide
  whether TASK-PRV-002 / 003 should have been planned with
  contract tests, and whether the `/feature-plan` output (TASK-REV-PRV4)
  needs amendment.

### Out of scope

- Re-running the autobuild (a follow-up `[I]mplement` task will own
  that, after the diagnostic is signed off).
- Re-litigating the FEAT-70A4 plan itself (TASK-REV-PRV4 is the owner
  of plan-quality concerns; this review only feeds back deltas).
- Changes to GuardKit smoke-gate machinery beyond what's needed to
  unblock this feature (broader tooling changes belong upstream in
  guardkit).

## Acceptance Criteria

- [ ] Single root cause (or ranked hypothesis set) identified for
      the post-wave-2 smoke-gate `exit=127`, with the offending
      command line and the interpreter/path mismatch documented.
- [ ] Wave-2 parallel-contention failure traced to a specific
      shared resource, with a recommendation: serialise wave 2,
      or fence the contended resource, or accept conditional approval.
- [ ] Conditional-approval rule evaluated against this feature's
      risk profile; recommendation made (keep / tighten / skip).
- [ ] Coach SDK reader fatal-error frequency tabulated across the
      transcript; classification (transport / resource / app) made.
- [ ] Seam-test gap acknowledged with a concrete amendment to the
      backlog tasks (which task gains contract tests, where they live).
- [ ] Decision-checkpoint output ready: **[A]ccept** (file findings,
      no further action) / **[I]mplement** (spawn fix tasks) /
      **[R]evise** (deeper analysis needed) / **[C]ancel**.
- [ ] If [I]mplement chosen: subtask list drafted for the fix
      feature (e.g. smoke-gate interpreter pin, wave-2 serialisation,
      contract-test backfill) ready to feed into `/feature-plan`.

## Deliverables

- Diagnostic report at `.claude/reviews/TASK-REV-AB7A-report.md`
  covering:
  - Timeline of the failure (turn-by-turn, with timestamps).
  - Root-cause analysis per failure surface above.
  - Recommended resume strategy (resume-from-wave-3 vs fresh).
  - Risk-ranked fix list with effort estimates.
- Updated frontmatter on this task with `review_results.decision` set.
- (If implementing) link to the spawned fix-feature folder.

## Test Execution Log

[Populated by /task-review — N/A for analysis tasks]
