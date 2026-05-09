---
id: TASK-RAG-CC1
title: "Course-correct RAG ingestion: remove in-copyright deny-list, document docling workflow"
task_type: implementation
feature_id: FEAT-PRV4
parent_review: TASK-REV-RAG4
implementation_mode: task-work
complexity: 3
estimated_minutes: 60
status: completed
priority: high
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
completed: 2026-05-09T00:00:00Z
completed_location: tasks/completed/TASK-RAG-CC1/
previous_state: in_review
state_transition_reason: "Completed by /task-complete TASK-RAG-CC1"
blocks:
  - TASK-RAG-003  # spec rewrite is unblocked once this lands
related:
  - src/study_tutor/knowledge/corpus.py
  - tests/unit/knowledge/test_corpus.py
  - features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py
  - domains/gcse-english/sources/CONTRIBUTING-CORPUS.md
  - .guardkit/reviews/TASK-REV-RAG4-review-report.md
  - docs/reviews/REVIEW-RAG-COURSE-CORRECT-docling-integration.md
tags:
  - rag
  - corpus
  - docling
  - course-correction
  - feat-prv4
  - phase-1
test_results:
  status: passed
  coverage: null  # not measured under MINIMAL intensity
  last_run: 2026-05-09T00:00:00Z
  unit:
    file: tests/unit/knowledge/test_corpus.py
    passed: 18
    failed: 0
  bdd_task_prv_002:
    selector: "features/primary-text-rag-and-quote-verifier/ -m task_TASK_PRV_002"
    passed: 12
    failed: 0
  notes: |
    Full pytest tests/ features/ run shows pre-existing unrelated failures
    (graphiti_client_wiring, mcp.test_stdio_discipline, planner.test_protocols,
    NATS integration collection errors); confirmed against clean main via
    git stash. None caused or exacerbated by this task.
---

# Task: Course-correct RAG ingestion — remove in-copyright deny-list, document docling workflow

## Provenance

This task implements the single course-correction emitted from
[TASK-REV-RAG4](../../tasks/in_review/TASK-REV-RAG4-course-correct-rag-docling-integration.md).
The canonical design rationale is in
[REVIEW-RAG-COURSE-CORRECT-docling-integration.md](../../docs/reviews/REVIEW-RAG-COURSE-CORRECT-docling-integration.md);
the ratified review report (with the pre-check resolution and the call to
collapse three sub-changes into one task) is at
[.guardkit/reviews/TASK-REV-RAG4-review-report.md](../../.guardkit/reviews/TASK-REV-RAG4-review-report.md).

**Pre-check finding (already resolved in the review):**
`load_corpus()` is already extension-agnostic — `_iter_files` uses
`folder.rglob("*")` and `_process_file` reads UTF-8 with a corrupted-file
fallback. Dropping a docling-produced `.md` into a source-type folder
already works today. Therefore D1 (Change 1) is **docs-only**; no code
change is required to "accept .md output".

## Description

Three ratified decisions, one task:

- **D1 — Accept docling .md output (docs-only).** Document the docling
  workflow in `CONTRIBUTING-CORPUS.md` and add `.md` to the gitignore
  example block. No code change to `corpus.py` or `ingest_corpus.py`.
- **D2 — Remove `INCOPYRIGHT_TITLES` deny-list.** Drop the frozenset,
  the `RefusalReason.IN_COPYRIGHT_TITLE` enum variant, the
  `_match_incopyright_title` helper, and the deny-list refusal block in
  `_process_file`. Update module docstrings, unit tests, BDD scenario
  + step definitions accordingly. Keep `AQA_REFUSAL_PATTERN` and
  `RefusalReason.AQA_ASSESSMENT_MATERIAL` (pedagogical guard).
- **D3 — Update `CONTRIBUTING-CORPUS.md`.** Replace §3 ("In-copyright
  modern set texts — deny-list") with a short personal-use posture
  note. Add a docling-workflow section that references (does not
  transcribe) the working invocation in
  `agentic-dataset-factory/ingestion/docling_processor.py`.

## Scope

### Code: `src/study_tutor/knowledge/corpus.py`

Remove:

- `INCOPYRIGHT_TITLES` frozenset
  ([line 101-110](../../src/study_tutor/knowledge/corpus.py#L101-L110)).
- `RefusalReason.IN_COPYRIGHT_TITLE` enum variant
  ([line 121](../../src/study_tutor/knowledge/corpus.py#L121)).
- The deny-list refusal block in `_process_file`
  ([line 297-313](../../src/study_tutor/knowledge/corpus.py#L297-L313)).
- The `_match_incopyright_title` helper
  ([line 385-396](../../src/study_tutor/knowledge/corpus.py#L385-L396)).
- `INCOPYRIGHT_TITLES` from `__all__`
  ([line 568](../../src/study_tutor/knowledge/corpus.py#L568)).

Update docstrings:

- Top-of-file paragraph "Refusal vs. skip vs. error"
  ([line 23-35](../../src/study_tutor/knowledge/corpus.py#L23-L35)) —
  drop the in-copyright clause from the refusal description.
- `load_corpus` docstring
  ([line 180-181](../../src/study_tutor/knowledge/corpus.py#L180-L181)) —
  drop "in-copyright deny-list" from the refusal-gates list.

### Tests: `tests/unit/knowledge/test_corpus.py`

- Remove the `INCOPYRIGHT_TITLES` import
  ([line 19](../../tests/unit/knowledge/test_corpus.py#L19)).
- Remove `test_incopyright_titles_constant_lists_required_entries`
  ([line 196-211](../../tests/unit/knowledge/test_corpus.py#L196-L211)).
- Remove `test_incopyright_match_is_case_insensitive_with_punctuation`
  ([line 214-237](../../tests/unit/knowledge/test_corpus.py#L214-L237)).
- AQA tests stay unchanged.

### BDD: `features/primary-text-rag-and-quote-verifier/`

- `*.feature` line 214-219 — remove the scenario "An in-copyright modern
  set text placed under primary text is refused at ingestion" and any
  ASSUM-009 comment that pointed to it.
- `test_primary_text_rag_and_quote_verifier.py` — remove three step
  defs and trim one assertion:
  - `_given_in_copyright_set_text` ([line 572-582](../../features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py#L572-L582))
  - `_then_incopyright_refusal_recorded` ([line 778-792](../../features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py#L778-L792))
  - `_then_incopyright_advises_phase_2` ([line 795-810](../../features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py#L795-L810))
  - In `_then_file_not_ingested` ([line 727-745](../../features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py#L727-L745)),
    drop `corpus_context.files.get("in_copyright")` from the candidate
    lookup.

### Docs: `domains/gcse-english/sources/CONTRIBUTING-CORPUS.md`

- **§3 "In-copyright modern set texts — deny-list"
  ([line 134-158](../../domains/gcse-english/sources/CONTRIBUTING-CORPUS.md#L134-L158))**
  — replace entirely with a short "Personal-use posture" section
  explaining that this is a personal-use tool on the operator's own
  machine, materials are legally acquired, no redistribution; AQA
  pedagogical refusal is the only content gate.
- **Add a docling-workflow section** (suggest §1b or new §2, renumber
  downstream as needed). Standard mode for digital PDFs, VLM mode for
  scanned paperbacks. Output `.md` drops into the appropriate
  source-type subfolder. Run `python scripts/ingest_corpus.py`.
  Reference (do not transcribe) the working invocation at
  `agentic-dataset-factory/ingestion/docling_processor.py`.
- **§4 "What gets committed"
  ([line 173-178](../../domains/gcse-english/sources/CONTRIBUTING-CORPUS.md#L173-L178))**
  — add `.md` to the gitignore example block alongside `.txt`,
  `.xhtml`, `.pdf`, `.epub`.

## Acceptance criteria

- [x] `INCOPYRIGHT_TITLES`, `RefusalReason.IN_COPYRIGHT_TITLE`, and
      `_match_incopyright_title` are gone from `corpus.py`. `__all__`
      reflects the removal. Module + `load_corpus` docstrings no longer
      reference an in-copyright deny-list.
- [x] `AQA_REFUSAL_PATTERN`, `RefusalReason.AQA_ASSESSMENT_MATERIAL`,
      and `RefusalReason.PATH_TRAVERSAL` are unchanged. Existing AQA
      refusal tests still pass.
- [x] The two deny-list unit tests are removed from
      `tests/unit/knowledge/test_corpus.py`; the `INCOPYRIGHT_TITLES`
      import is removed; the rest of the file is untouched.
- [x] The deny-list BDD scenario and its three step defs are removed;
      `_then_file_not_ingested` no longer references `in_copyright`.
      All remaining BDD scenarios still pass.
- [x] A `.md` file dropped into a source-type folder is ingested and
      produces at least one chunk. Either an existing test already
      proves this or one new test does — implementer's call (a one-line
      `.md` fixture in the existing four-folder source-type test is
      sufficient).
- [x] `CONTRIBUTING-CORPUS.md` §3 no longer mentions a deny-list and
      describes the personal-use posture instead. A new docling-workflow
      section exists referencing
      `agentic-dataset-factory/ingestion/docling_processor.py`. The
      gitignore example block in §4 includes `.md`.
- [x] `pytest tests/ features/` is green.
- [x] No changes to `scripts/ingest_corpus.py`,
      `src/study_tutor/knowledge/corpus_models.py`, or
      `src/study_tutor/knowledge/retrieval.py`.

## Out of scope (do not touch)

- Header-aware markdown chunker — note as a follow-up only.
- Running docling on PDFs (operator work on the GB10).
- Re-embedding ADF chunks (operator re-processes from source PDFs).
- Rewriting `TASK-RAG-003` spec — separate task after this lands.
- Provider/embedding/persist-dir wiring in `ingest_corpus.py` — already
  aligned with DECISION-RAG-001 (TASK-RAG-001A).
- The Branch-2 retrieval scenario at `*.feature` line 48-49 ("A turn
  on an in-copyright text with no primary edition in the corpus skips
  retrieval and runs in Analysis Mode") — tests runtime behaviour, not
  the loader deny-list. Keep as-is. Optional re-wording is the
  implementer's call but not required.
- `tests/unit/knowledge/test_retrieval.py` line 638 — uses
  `"inspector_calls"` as a `text_name` fixture string. Independent of
  the deny-list. Leave.

## References

- Review report: [.guardkit/reviews/TASK-REV-RAG4-review-report.md](../../.guardkit/reviews/TASK-REV-RAG4-review-report.md)
- Canonical design doc: [docs/reviews/REVIEW-RAG-COURSE-CORRECT-docling-integration.md](../../docs/reviews/REVIEW-RAG-COURSE-CORRECT-docling-integration.md)
- Parent review task: [tasks/in_review/TASK-REV-RAG4-course-correct-rag-docling-integration.md](../../tasks/in_review/TASK-REV-RAG4-course-correct-rag-docling-integration.md)
- DECISION-RAG-001 — Unified ChromaDB approach (already aligned, do not modify)
- Working docling invocation: `agentic-dataset-factory/ingestion/docling_processor.py`
