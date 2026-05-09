---
review_id: TASK-REV-RAG4
title: "Review: course-correct RAG ingestion to accept docling output and remove deny-list"
mode: course-correction
depth: standard
date: 2026-05-09
canonical_doc: docs/reviews/REVIEW-RAG-COURSE-CORRECT-docling-integration.md
decisions_ratified: [D1, D2, D3]
status: review_complete
---

# Review Report — TASK-REV-RAG4

## Executive summary

The canonical review doc
[REVIEW-RAG-COURSE-CORRECT-docling-integration.md](../../docs/reviews/REVIEW-RAG-COURSE-CORRECT-docling-integration.md)
is **ratified**. D1, D2, D3 stand. The single "needs confirming" item — the
file-extension behaviour of `load_corpus()` — is resolved against the live
code: **the loader is already extension-agnostic**, so D1 (Change 1) collapses
to a docs-only update.

Net effect: one implementation task carries the whole course correction.

## Pre-check resolution

> **Open question in the canonical doc:**
> *Check what file extensions `load_corpus()` actually filters on. If it
> already accepts any file in the folder, Change 1 might be a pure
> documentation update rather than a code change.*

**Finding: extension filter is already permissive.**

Evidence in [src/study_tutor/knowledge/corpus.py](../../src/study_tutor/knowledge/corpus.py):

- `_iter_files` ([line 225-229](../../src/study_tutor/knowledge/corpus.py#L225-L229))
  uses `folder.rglob("*")` and yields any regular file. **No suffix filter.**
- `_process_file` ([line 316](../../src/study_tutor/knowledge/corpus.py#L316))
  reads via `file_path.read_text(encoding="utf-8")`. UTF-8 decode failure
  routes to `SkipReason.CORRUPTED_FILE`
  ([line 318-328](../../src/study_tutor/knowledge/corpus.py#L317-L328)) — it
  does not abort the walk.
- AQA pattern matching is filename-based regardless of extension
  ([line 281](../../src/study_tutor/knowledge/corpus.py#L281)), so AQA refusal
  works on `.pdf`, `.txt`, `.md` alike.
- Citation-anchor inference (`_infer_play_anchor`,
  [line 485-523](../../src/study_tutor/knowledge/corpus.py#L485-L523)) keys
  off `^\s*act\s+...` / `^\s*scene\s+...` regexes on stripped lines. These
  fire correctly on docling markdown (act/scene markers carry through).
- Chunker (`_chunk_text`,
  [line 412-443](../../src/study_tutor/knowledge/corpus.py#L412-L443)) is
  prose-oriented but markdown-safe — header lines just become part of the
  chunk text. No structural assumptions about plain text.

**Implication:** dropping a docling-produced `.md` file into
`primary_text/`, `secondary_study_guide/`, etc. **already works today**.
There is no code change required for Change 1. The work is entirely
documentation.

**Pedantic exception:** `_infer_play_anchor`'s line-counting walks every
non-heading non-empty line of the *full file text*. On a docling-produced
markdown of a play, `# `, `## `, `*italic*`, table rows, etc. would all
count as content lines, giving citation-anchor `line` numbers that don't
match a Standard Ebooks line count. This only matters for the existing
Standard Ebooks Macbeth `.txt` flow (already working) and for any future
docling-processed *primary play text*. Out of scope for this course
correction (the doc explicitly defers a header-aware chunker as a
follow-up). Noting it for completeness.

## Ratified decisions

### D1 — Accept docling .md output (RATIFIED, scope: docs-only)

**Decision:** the ingestion pipeline accepts docling markdown output by
operator dropping `.md` files into the appropriate source-type subfolder,
then running `python scripts/ingest_corpus.py`.

**Codebase status:** already supported. No `corpus.py` or
`ingest_corpus.py` change needed.

**Implementation surface (docs only):**

- `domains/gcse-english/sources/CONTRIBUTING-CORPUS.md` §1 "Standard
  Ebooks is the canonical primary-text source" — augment with a §1b (or
  new section) covering the docling workflow:
  - Standard mode for digital PDFs / VLM mode for scanned paperbacks
  - Output `.md` goes in the appropriate source-type subfolder
  - Run `ingest_corpus.py` after processing
  - Reference (do not transcribe) the working invocation in
    `agentic-dataset-factory/ingestion/docling_processor.py`
- `domains/gcse-english/sources/CONTRIBUTING-CORPUS.md` §4 "What gets
  committed" — add `.md` to the gitignore example block
  ([line 173-178](../../domains/gcse-english/sources/CONTRIBUTING-CORPUS.md#L173-L178)),
  matching the existing `.txt`/`.xhtml`/`.pdf`/`.epub` entries.

### D2 — Remove INCOPYRIGHT_TITLES deny-list (RATIFIED, scope: code + tests + docs)

**Decision:** drop the in-copyright deny-list entirely. Keep
`AQA_REFUSAL_PATTERN` as the pedagogical guard.

**Implementation surface:**

Code (`src/study_tutor/knowledge/corpus.py`):

- Remove `INCOPYRIGHT_TITLES` frozenset
  ([line 101-110](../../src/study_tutor/knowledge/corpus.py#L101-L110)).
- Remove `RefusalReason.IN_COPYRIGHT_TITLE` enum variant
  ([line 121](../../src/study_tutor/knowledge/corpus.py#L121)).
- Remove the deny-list refusal block in `_process_file`
  ([line 297-313](../../src/study_tutor/knowledge/corpus.py#L297-L313)).
- Remove the `_match_incopyright_title` helper
  ([line 385-396](../../src/study_tutor/knowledge/corpus.py#L385-L396)).
- Remove `INCOPYRIGHT_TITLES` from `__all__`
  ([line 568](../../src/study_tutor/knowledge/corpus.py#L568)).

Module docstring updates (`corpus.py`):

- Top-of-file paragraph "Refusal vs. skip vs. error"
  ([line 23-35](../../src/study_tutor/knowledge/corpus.py#L23-L35))
  currently says "AQA assessment material, in-copyright modern set
  texts, files outside the corpus root via path-traversal symlinks". Drop
  the in-copyright clause.
- The `load_corpus` docstring "Each file inside a recognised folder is
  run through the refusal gates (path-traversal, AQA, in-copyright
  deny-list)" ([line 180-181](../../src/study_tutor/knowledge/corpus.py#L180-L181))
  — drop "in-copyright deny-list".

Unit tests (`tests/unit/knowledge/test_corpus.py`):

- Remove the `INCOPYRIGHT_TITLES` import
  ([line 19](../../tests/unit/knowledge/test_corpus.py#L19)).
- Remove `test_incopyright_titles_constant_lists_required_entries`
  ([line 196-211](../../tests/unit/knowledge/test_corpus.py#L196-L211)).
- Remove `test_incopyright_match_is_case_insensitive_with_punctuation`
  ([line 214-237](../../tests/unit/knowledge/test_corpus.py#L214-L237)).
- AQA tests stay unchanged.

BDD feature + step definitions (`features/primary-text-rag-and-quote-verifier/`):

- `*.feature` line 214-219 — remove the scenario "An in-copyright modern
  set text placed under primary text is refused at ingestion".
- `test_primary_text_rag_and_quote_verifier.py`:
  - Remove `_given_in_copyright_set_text`
    ([line 572-582](../../features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py#L572-L582)).
  - Remove `_then_incopyright_refusal_recorded`
    ([line 778-792](../../features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py#L778-L792)).
  - Remove `_then_incopyright_advises_phase_2`
    ([line 795-810](../../features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py#L795-L810)).
  - In `_then_file_not_ingested`
    ([line 727-745](../../features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py#L727-L745)),
    drop the `corpus_context.files.get("in_copyright")` clause.

**Out-of-scope (note for the implementer, do not touch):**

- The Branch-2 retrieval scenario at `*.feature` line 48-49 ("A turn on
  an in-copyright text with no primary edition in the corpus skips
  retrieval and runs in Analysis Mode") and its
  `_given_in_copyright_no_primary` step
  ([line 223-235](../../features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py#L223-L235)).
  This scenario tests a *runtime* behaviour ("no primary edition in
  corpus → analysis mode"), not the loader-side deny-list. With the
  deny-list removed, the operator *could* ingest Inspector Calls via
  docling — but if they haven't, the analysis-mode path still applies.
  The scenario language is mildly aspirational ("in-copyright" as a
  proxy for "not yet in corpus") but semantically intact. The
  implementer may optionally reword the Gherkin to drop the
  "in-copyright" framing; not required.
- `tests/unit/knowledge/test_retrieval.py` line 638 uses
  `"inspector_calls"` as a `text_name` fixture argument. Independent of
  the deny-list — leave alone.
- `scripts/ingest_corpus.py` — no deny-list references, no changes
  required.
- `corpus_models.py` — no deny-list references, no changes required
  (the canonical doc speculated INCOPYRIGHT_TITLES might live there; it
  doesn't, it's in `corpus.py`).

### D3 — CONTRIBUTING-CORPUS.md update (RATIFIED, scope: docs-only)

**Decision:** rewrite §3 of `CONTRIBUTING-CORPUS.md` from "In-copyright
deny-list" to a brief "Personal-use posture" note; add the docling
workflow under §1 (or a new §1b).

**Implementation surface:**

- `domains/gcse-english/sources/CONTRIBUTING-CORPUS.md`
  - **§3 "In-copyright modern set texts — deny-list"
    ([line 134-158](../../domains/gcse-english/sources/CONTRIBUTING-CORPUS.md#L134-L158))**
    — replace entirely with a short personal-use posture note: this is a
    personal-use tool on the operator's own machine for legally-acquired
    materials, no redistribution; the AQA pedagogical refusal is the only
    content gate; per-student Phase 2 path is no longer load-bearing
    (the bullet at line 152-157 referencing it should be reworded or
    removed).
  - **Docling workflow** — add a new section (suggest §1b or a new §2,
    renumbering downstream). Reference, do not transcribe, the working
    invocation in
    `agentic-dataset-factory/ingestion/docling_processor.py`. Standard
    mode for digital PDFs, VLM mode for scanned paperbacks. `.md` output
    drops into the appropriate source-type subfolder. Run
    `ingest_corpus.py`.
  - **§4 "What gets committed"
    ([line 173-178](../../domains/gcse-english/sources/CONTRIBUTING-CORPUS.md#L173-L178))**
    — add `.md` to the gitignore example block.

## Cross-task ratification (formalising what the doc settled)

These are listed in the canonical doc as "decisions already settled" but
deserve a formal review checkpoint:

- **TASK-RAG-002 (CLI wire retrieval and coach handover) — proceed
  unblocked.** CLI wiring is independent of corpus content. This review
  does not block it.
- **TASK-RAG-003 (end-to-end RAG smoke session) — leave on the
  backlog, do not implement against current spec.** The current spec
  fixtures off the Standard Ebooks Macbeth `.txt` only and asserts on
  primary-text retrieval signals only. After this course correction
  lands and Mr Bruff secondary content is processed via docling and
  ingested, the spec must be rewritten to cover both retrieval paths
  (primary + secondary). That rewrite is **not** a subtask of this
  course correction.

## Acceptance-criteria checklist (from TASK-REV-RAG4)

- [x] Read the canonical review doc end-to-end and ratify D1, D2, D3.
- [x] Resolve the "needs confirming" extension-filter question against
      `corpus.py` and record the finding in the report.
- [x] Confirm the AQA refusal (`AQA_REFUSAL_PATTERN`) stays — it is a
      pedagogical guard, not a copyright guard. (Kept.)
- [x] Emit subtask breakdown — see "Subtask breakdown" below.
- [x] Confirm the explicit out-of-scope items: not running docling, not
      adding a header-aware chunker, not rewriting TASK-RAG-003, not
      touching `ingest_corpus.py` provider/embedding/persist-dir wiring.
      (Confirmed; none of these are in the subtask scope.)
- [x] Produce this review report at
      `.guardkit/reviews/TASK-REV-RAG4-review-report.md`.

## Subtask breakdown

### Recommendation: collapse to a single implementation task

The canonical task allowed for collapsing TASK-RAG-CC1/CC2/CC3 "if all
three are small enough — that judgment is part of the review output".
**Collapse is the right call** because:

1. The pre-check resolution turned Change 1 into docs-only, eliminating
   the code/docs split that justified separate tasks.
2. Code (D2) and docs (D2 + D3) are the same conceptual change ("remove
   the in-copyright deny-list and reflect that everywhere"). Splitting
   creates a window where `corpus.py` and `CONTRIBUTING-CORPUS.md`
   disagree.
3. Total work is small: ~40 LOC removed from `corpus.py`, ~50 lines
   removed/altered in tests, ~30 lines rewritten in
   `CONTRIBUTING-CORPUS.md`. One atomic commit.
4. YAGNI — three tasks where one suffices is the same kind of process
   over-engineering the canonical doc was correcting at the design layer.

### TASK-RAG-CC1 — Course-correct RAG ingestion (single task)

**Title:** Course-correct RAG ingestion: remove in-copyright deny-list,
document docling workflow.

**Scope (in one task):**

- D2: remove `INCOPYRIGHT_TITLES`, `RefusalReason.IN_COPYRIGHT_TITLE`,
  `_match_incopyright_title`, the deny-list refusal block in
  `_process_file`, and the corresponding entry in `__all__` from
  `src/study_tutor/knowledge/corpus.py`.
- D2: update the `corpus.py` module docstring + `load_corpus` docstring
  to drop in-copyright references.
- D2: remove the two unit tests for the deny-list in
  `tests/unit/knowledge/test_corpus.py` and the `INCOPYRIGHT_TITLES`
  import.
- D2: remove the BDD scenario "An in-copyright modern set text placed
  under primary text is refused at ingestion" from the `.feature` file
  and its three step definitions
  (`_given_in_copyright_set_text`, `_then_incopyright_refusal_recorded`,
  `_then_incopyright_advises_phase_2`); remove the `in_copyright` clause
  from `_then_file_not_ingested`.
- D1 + D3: rewrite §3 of `CONTRIBUTING-CORPUS.md` to a personal-use
  posture note; add a docling-workflow section (referencing
  `agentic-dataset-factory/ingestion/docling_processor.py`); add `.md`
  to the gitignore example block in §4.

**Acceptance criteria:**

- [ ] `INCOPYRIGHT_TITLES` and `RefusalReason.IN_COPYRIGHT_TITLE` are
      gone from `corpus.py` and from `__all__`.
- [ ] `AQA_REFUSAL_PATTERN`, `RefusalReason.AQA_ASSESSMENT_MATERIAL`,
      and `RefusalReason.PATH_TRAVERSAL` remain unchanged.
- [ ] Existing AQA refusal tests still pass.
- [ ] The deny-list scenario is removed from the BDD feature file; all
      remaining scenarios still pass against unchanged code.
- [ ] A `.md` file dropped into `primary_text/` (or any source-type
      folder) under a new fixture is ingested and produces at least one
      chunk — covered by either an existing test or one new test
      asserting `.md` ingestion is successful (operator's call).
- [ ] `CONTRIBUTING-CORPUS.md` §3 no longer mentions a deny-list;
      describes personal-use posture; references the docling workflow
      and points at
      `agentic-dataset-factory/ingestion/docling_processor.py` for the
      working CLI invocation.
- [ ] `pytest tests/ features/` is green.

**Out of scope (do not touch):**

- `scripts/ingest_corpus.py` (no deny-list refs, no changes needed).
- `corpus_models.py` (deny-list lives in `corpus.py`, not here).
- Header-aware markdown chunker (note as a follow-up only — out of scope).
- Running docling on PDFs (operator work on the GB10).
- Re-embedding ADF chunks (re-process from source PDFs instead — operator).
- Rewriting `TASK-RAG-003` spec (do after this lands, separate task).

**Estimated complexity:** 2–3 (mechanical removal of a feature with full
test coverage; docs rewrite of one section + one new section).

**Suggested mode:** standard (`/task-work TASK-RAG-CC1`). Not micro
(touches multiple files including BDD), not TDD (the work is *removal*
of a refusal path; tests get deleted, not authored).

## Decision checkpoint

Review is complete. Three options:

- **[A]ccept** — ratify findings; capture to Graphiti (if available);
  proceed to creating TASK-RAG-CC1 as the single implementation task.
- **[R]evise** — flag any ratification you disagree with and request
  re-analysis of that decision.
- **[I]mplement** — emit TASK-RAG-CC1 directly into `tasks/backlog/`
  with frontmatter (`parent_review: TASK-REV-RAG4`,
  `feature_id: FEAT-PRV4`, etc.) and proceed.
- **[C]ancel** — discard.

## References

- Canonical doc:
  [docs/reviews/REVIEW-RAG-COURSE-CORRECT-docling-integration.md](../../docs/reviews/REVIEW-RAG-COURSE-CORRECT-docling-integration.md)
- Loader: [src/study_tutor/knowledge/corpus.py](../../src/study_tutor/knowledge/corpus.py)
- Loader models: [src/study_tutor/knowledge/corpus_models.py](../../src/study_tutor/knowledge/corpus_models.py)
- Ingest script: [scripts/ingest_corpus.py](../../scripts/ingest_corpus.py)
- Operator doc: [domains/gcse-english/sources/CONTRIBUTING-CORPUS.md](../../domains/gcse-english/sources/CONTRIBUTING-CORPUS.md)
- Unit tests: [tests/unit/knowledge/test_corpus.py](../../tests/unit/knowledge/test_corpus.py)
- BDD feature + steps:
  [features/primary-text-rag-and-quote-verifier/](../../features/primary-text-rag-and-quote-verifier/)
- Working docling invocation:
  `agentic-dataset-factory/ingestion/docling_processor.py`
