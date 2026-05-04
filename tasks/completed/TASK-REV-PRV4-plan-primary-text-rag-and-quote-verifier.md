---
id: TASK-REV-PRV4
title: "Plan: Primary-Text RAG and Source-Typed Quote Verifier"
task_type: review
status: review_complete
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
priority: high
tags: [feature-plan, rag, quote-verifier, source-typed, copyright, phase-1, FEAT-PH1-004]
complexity: 6
context_files:
  - features/primary-text-rag-and-quote-verifier/primary-text-rag-and-quote-verifier_summary.md
  - features/primary-text-rag-and-quote-verifier/primary-text-rag-and-quote-verifier.feature
  - features/primary-text-rag-and-quote-verifier/primary-text-rag-and-quote-verifier_assumptions.yaml
  - docs/research/ideas/phase-1-scope.md
  - docs/research/ideas/phase-1-build-plan.md
  - docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md
  - docs/research/ideas/cross-repo-rag-impact-analysis-2026-04-24.md
  - docs/research/ideas/copyright-training-data-analysis.md
  - domains/gcse-english/GOAL.md
  - domains/gcse-english/sources/README.md
  - src/study_tutor/knowledge/student_model.py
  - tasks/completed/deepagents-tutoring-loop/IMPLEMENTATION-GUIDE.md
  - tasks/completed/deepagents-tutoring-loop/TASK-DTL-002-rubric-and-quote-fidelity.md
  - /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/ingestion/chunker.py
  - /Users/richardwoollcott/Projects/appmilla_github/agentic-dataset-factory/ingestion/models.py
clarification:
  context_a:
    timestamp: 2026-04-30T00:00:00Z
    decisions:
      review_focus: all
      tradeoff_priority: quality
      specific_concerns:
        - coach_handover_contract
        - reuse_adf_chunker
        - false_positive_fuzzy_correction
    directives:
      - "Comprehensive analysis across architecture, safety invariants, copyright posture, and FEAT-PH1-003 integration"
      - "Optimise for verifier correctness and defence-in-depth invariants over delivery speed"
      - "Settle the verifier-rewritten-response handover shape so TASK-DTL-002's seam can rely on it"
      - "Decide chunker reuse posture (import-as-is vs copy-and-adapt vs citation-aware variant)"
      - "Address Open Question 3 — fuzzy-correction false positives when primary + secondary coexist"
review_results:
  mode: decision
  depth: standard
  recommended_option: "Option A — Three-module split (corpus / retrieval / verifier) with citation-aware chunker variant adapted from agentic-dataset-factory"
  options_count: 3
  subtask_count: 7
  estimated_effort_hours: "5-7 sequential / ~3-4h elapsed with wave-2 parallelism"
  confidence: high
  pre_implementation_signoffs:
    - "ASSUM-008 (AQA refusal: filename-pattern at loader, with deny-list fallback layer)"
    - "ASSUM-009 (in-copyright deny-list at loader: explicit titles list + advisory log line)"
    - "ASSUM-010 (secondary attribution phrase template: 'as one critic observes' / 'as one study guide notes' — single configurable string set)"
    - "ASSUM-011 (long-passage threshold: 30 words → ≤12 short embedded quote)"
    - "ASSUM-013 (embedder unavailability: 5s timeout per call → AnalysisMode fallback)"
    - "Cross-feature handover: VerifierResult metadata shape settled and consumed by TASK-DTL-002"
    - "Open Question 3 (false-positive fuzzy correction) addressed by primary-wins precedence + restricting fuzzy correction to primary-text source only"
  report_path: .guardkit/reviews/TASK-REV-PRV4-review-report.md
  completed_at: 2026-04-30T00:00:00Z
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Plan: Primary-Text RAG and Source-Typed Quote Verifier

## Description

Plan **FEAT-PH1-004** — the Phase 1 source-typed corpus loader, dynamic
retrieval-decision function, and four-way quote verifier for study-tutor.

This is a `/feature-plan` review task. It precedes implementation and produces:

1. A technical-options analysis covering the corpus ingestion seam,
   dynamic retrieval-decision logic (R2), AO3 retrieval bypass (R3),
   the four-way source-typed verifier (R1), and the Coach handover
   contract (consumed by TASK-DTL-002 / FEAT-PH1-003).
2. A recommended approach plus a subtask breakdown ready for [I]mplement.
3. Explicit risk callouts and recommended resolutions for the five
   low-confidence assumptions (ASSUM-008/009/010/011/013) and the four
   medium-confidence assumptions (ASSUM-005/006/007/012/015).
4. An obvious-risks task-slice sequencing assessment (full slicing
   handled by `/feature-plan` [I]mplement).

## Scope

- **Source-typed corpus loader** — directory-driven `SourceType`
  enum (primary_text / secondary_study_guide / secondary_critical /
  context_historical), `CorpusChunk` Pydantic model with
  `citation_anchor`, AQA-pattern + in-copyright deny-list refusal at
  loader, path-traversal safety, resilience to corrupted files.
- **Retrieval-decision function** — `should_retrieve(text_name,
  focus_aos) -> tuple[bool, str]` with the three branches: retrieve
  for primary-text-present + non-AO3-only; AnalysisMode skip for
  no-primary-text; AO3-only training-first bypass. Mixed AO3+AO1/AO2
  retrieves for non-AO3 evidence.
- **Source-filtered retrieval** — top-K=6, primary-first ordering,
  `BAAI/bge-reranker-v2-m3` baseline with graceful degradation to
  base similarity when reranker unavailable; embedder-unavailability
  → AnalysisMode fallback (5s timeout).
- **Quote verifier** — extract quotes (≥4 words), match against
  primary-text chunks first (whitespace/punctuation normalisation),
  produce one of four results: primary-annotated, secondary-rewritten,
  fuzzy-corrected (≤3 edit distance from **primary** only),
  no-match-stripped. Long-passage shortening (>30 → ≤12 words).
- **Coach handover contract** — verifier rewrites the response in
  place; verifier metadata accompanies the rewritten response so
  TASK-DTL-002's `score_rubric` can derive the `quote_fidelity`
  criterion score. `retrieval_skipped` reason surfaces in turn metadata
  so the Coach suppresses quote-fidelity down-rank in AnalysisMode.
- **Defence-in-depth invariants** — secondary phrasing never
  annotated as primary; cross-text spans never annotated against
  the wrong text's citation; fuzzy correction restricted to
  primary-text matches (closes Open Question 3).

## Review Findings

The full review report is at `.guardkit/reviews/TASK-REV-PRV4-review-report.md`.
Decision-checkpoint summary is presented inline in the
`/feature-plan` orchestrator output.

## Out of Scope

- **Embedding-based pre-generation grounding** (Phase B) —
  Phase 1 stays post-hoc verification only (per scope §Out of scope).
- **Per-student in-copyright `Text` episodes in Graphiti** (Phase 2).
- **Reranker tuning beyond the bge-reranker-v2-m3 baseline**.
- **AO3 context-historical corpus curation** — folder structure
  supported; populating the folder is a content task, not infra.

## Acceptance Criteria

- [x] Five low-confidence assumptions have recommended resolutions
- [x] Coach handover contract specified end-to-end (rewritten
      response + verifier metadata shape)
- [x] Open Question 3 (false-positive fuzzy correction) addressed
- [x] Chunker reuse posture decided (citation-aware variant
      adapted from agentic-dataset-factory)
- [x] Task slice sequencing — obvious risks only (full plan emitted
      by [I]mplement)

## Test Execution Log

[Populated by /task-work — N/A for review tasks]
