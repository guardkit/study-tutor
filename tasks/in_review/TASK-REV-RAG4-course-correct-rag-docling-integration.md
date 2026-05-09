---
id: TASK-REV-RAG4
title: "Review: course-correct RAG ingestion to accept docling output and remove deny-list"
task_type: review
feature_id: FEAT-PRV4
status: review_complete
priority: high
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
review_results:
  mode: course-correction
  depth: standard
  decisions_ratified: [D1, D2, D3]
  pre_check_resolution: "load_corpus extension filter is already permissive (rglob('*') + UTF-8 read) — Change 1 collapses to docs-only"
  recommended_subtasks: 1
  report_path: .guardkit/reviews/TASK-REV-RAG4-review-report.md
  completed_at: 2026-05-09T00:00:00Z
tags:
  - rag
  - corpus
  - docling
  - course-correction
  - feat-prv4
  - phase-1
  - review
canonical_review: docs/reviews/REVIEW-RAG-COURSE-CORRECT-docling-integration.md
context_files:
  - docs/reviews/REVIEW-RAG-COURSE-CORRECT-docling-integration.md
  - src/study_tutor/knowledge/corpus.py
  - src/study_tutor/knowledge/corpus_models.py
  - scripts/ingest_corpus.py
  - domains/gcse-english/sources/CONTRIBUTING-CORPUS.md
related:
  - tasks/completed/TASK-RAG-001-chromadb-ingestion-script.md
  - tasks/completed/TASK-RAG-001A/
  - tasks/completed/TASK-RAG-002/TASK-RAG-002.md
  - tasks/backlog/TASK-RAG-003-end-to-end-rag-smoke-session.md
blocks:
  - TASK-RAG-003  # spec must be rewritten after course correction lands
does_not_block:
  - TASK-RAG-002  # already completed; CLI wiring is independent of corpus content
review:
  scope: course-correction
  canonical_doc: docs/reviews/REVIEW-RAG-COURSE-CORRECT-docling-integration.md
  decisions_to_ratify:
    - id: D1
      summary: "Accept docling .md output in load_corpus() / ingest_corpus.py"
      pre_check_required: "Confirm whether load_corpus() already accepts any extension (likely yes — corpus.py _iter_files uses rglob('*') with no suffix filter); if so, Change 1 is docs-only"
    - id: D2
      summary: "Remove INCOPYRIGHT_TITLES deny-list and RefusalReason.IN_COPYRIGHT_TITLE; keep AQA_REFUSAL_PATTERN as pedagogical guard"
    - id: D3
      summary: "Update CONTRIBUTING-CORPUS.md with docling workflow and personal-use posture"
  decisions_already_settled_in_doc:
    - "TASK-RAG-002 — proceed (CLI wiring independent of corpus content; already completed)"
    - "TASK-RAG-003 — leave; rewrite spec after Mr Bruff secondary content exists alongside Macbeth primary"
  out_of_scope:
    - "Running docling on PDFs (operator work on GB10)"
    - "Header-aware markdown chunker (note as follow-up only)"
    - "Re-embedding ADF chunks (re-process from source PDFs instead)"
    - "Rewriting TASK-RAG-003 spec (do after this lands)"
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Review — course-correct RAG ingestion to accept docling output and remove deny-list

## Description

Ratify the course correction defined in
[REVIEW-RAG-COURSE-CORRECT-docling-integration.md](../../docs/reviews/REVIEW-RAG-COURSE-CORRECT-docling-integration.md)
and produce the implementation subtask breakdown.

The review document is **canonical** and was pair-programmed in Claude Desktop.
This `/task-review` exists to:

1. Confirm decisions D1–D3 against the live codebase (one item — file
   extension handling in `load_corpus()` — is flagged "needs confirming" in
   the review doc itself).
2. Ratify the cross-task decisions already settled in the doc (TASK-RAG-002
   proceed, TASK-RAG-003 leave) so they have a formal review checkpoint.
3. Emit subtasks for the implementation work.

## Pre-implementation check (do this in the review, not later)

The review doc flags one item:

> Check what file extensions `load_corpus()` actually filters on. If it
> already accepts any file in the folder, Change 1 might be a pure
> documentation update rather than a code change.

Resolve this during `/task-review` by reading
[src/study_tutor/knowledge/corpus.py](../../src/study_tutor/knowledge/corpus.py)
end-to-end (look at `_iter_files`, `_process_file`, and any helpers they
call). The review's recommended subtask split depends on the answer:

- **If extension filter is already permissive** → Change 1 collapses to a
  docs-only update; the implementation task is mostly Change 2 + docs.
- **If extension filter is restrictive** → Change 1 needs a code change to
  accept `.md` (and `.xhtml` if Standard Ebooks EPUB extraction produces it).

Record the finding in the review report.

## Acceptance criteria for the review itself

- [ ] Read the canonical review doc end-to-end and ratify D1, D2, D3 (or
      flag any disagreement and resolve before emitting subtasks).
- [ ] Resolve the "needs confirming" extension-filter question against
      `corpus.py` and record the finding in the report.
- [ ] Confirm the AQA refusal (`AQA_REFUSAL_PATTERN`) stays — it is a
      pedagogical guard, not a copyright guard.
- [ ] Emit subtask breakdown for implementation. Suggested shape (revise
      based on pre-check finding):
      - **TASK-RAG-CC1**: Change 1 — accept `.md` (code change) **OR** docs
        update only, depending on pre-check.
      - **TASK-RAG-CC2**: Change 2 — remove `INCOPYRIGHT_TITLES` frozenset,
        `RefusalReason.IN_COPYRIGHT_TITLE` enum variant, and the matching
        check in `load_corpus()`. Update/remove any tests that asserted the
        deny-list behaviour. Keep AQA refusal regression test.
      - **TASK-RAG-CC3**: Update `CONTRIBUTING-CORPUS.md` — document the
        docling → markdown → drop-in workflow (point at
        `agentic-dataset-factory/ingestion/docling_processor.py` for the
        working CLI invocation rather than transcribing flags), remove the
        deny-list section, add personal-use posture note.
      - These may collapse into a single implementation task if all three
        are small enough — that judgment is part of the review output.
- [ ] Confirm the explicit out-of-scope items: do not run docling, do not
      add a header-aware chunker, do not rewrite TASK-RAG-003, do not touch
      `ingest_corpus.py` provider/embedding/persist-dir wiring.
- [ ] Produce a review report at
      `.guardkit/reviews/TASK-REV-RAG4-review-report.md` summarising
      findings, ratified decisions, pre-check resolution, and subtask
      breakdown.

## What the review must NOT do

- ❌ Re-litigate the decisions in the canonical review doc. The thinking is
      done; the job is to ratify, resolve the one open question, and emit
      subtasks.
- ❌ Recommend implementing TASK-RAG-003 against its current spec. The
      review doc explicitly invalidates that spec; it must be rewritten
      after course correction + docling processing produce real Mr Bruff
      secondary content.

## References

- Canonical review: [REVIEW-RAG-COURSE-CORRECT-docling-integration.md](../../docs/reviews/REVIEW-RAG-COURSE-CORRECT-docling-integration.md)
- DECISION-RAG-001 — Unified ChromaDB approach (already aligned, do not modify)
- ADR-FLEET-002 — Selective retrieval (don't suppress fine-tuned behaviour)
- Working docling invocation: `agentic-dataset-factory/ingestion/docling_processor.py`
- Source PDFs ready for re-processing post-task: `agentic-dataset-factory/domains/gcse-english-tutor/sources/`
