# REVIEW-RAG-COURSE-CORRECT — Accept docling output, remove deny-list, align with fleet workflow

**Date:** 2026-05-09
**Author:** Rich (pair-programmed with Claude Opus 4.6 in Claude Desktop)
**Type:** Course correction review
**Scope:** `study-tutor` RAG ingestion pipeline — `scripts/ingest_corpus.py`, `src/study_tutor/knowledge/corpus.py`, `src/study_tutor/knowledge/corpus_models.py`
**Blocks:** TASK-RAG-003 (current spec is invalidated; must be rewritten after this lands)
**Does not block:** TASK-RAG-002 (CLI wiring is independent of corpus content)

---

## Problem Statement

The study-tutor's RAG ingestion pipeline was built around `load_corpus()` — a
text-only loader that walks a four-folder tree of `.txt` files, classifies by
subfolder, infers citation anchors from act/scene markers, and checks an
in-copyright deny-list. This was delivered in TASK-PRV-002 and wired into
`ingest_corpus.py` via TASK-RAG-001 / TASK-RAG-001A.

**This pipeline does not fit how we actually process source material.**

The fleet's proven PDF processing workflow is:

1. Run **docling** on the GB10 (standard mode for digital PDFs, VLM mode for
   scanned paperbacks via HP OfficeJet)
2. Docling produces structured markdown/JSON output
3. Chunk the output
4. Embed via llama-swap (`nomic-embed-text`, 768 dim)
5. Index into ChromaDB

This workflow is already working. Docling has successfully processed:
- **19 architecture books** (3 scanned via VLM mode) for the specialist-agent
  dataset factory — 1,102 records in `specialist-agent/data/rag_index/knowledge.jsonl`
- **7 Mr Bruff GCSE guides** for the study-tutor dataset factory — 3,850 chunks
  in `agentic-dataset-factory/chroma_data_backup/` (embedded with a different
  model, so need re-embedding, but the extraction is done)

The current `load_corpus()` cannot consume any of this output. It only reads
`.txt` files. When PDFs were provided during TASK-RAG-001 implementation,
the session repeatedly refused them (wrong format, in-copyright, image-scanned)
instead of routing through the proven docling pipeline. The net result was a
corpus containing only a single Standard Ebooks Macbeth `.txt` file.

**This review corrects three things:**

1. **Accept docling output** in the ingestion pipeline (Option B from the
   planning discussion)
2. **Remove the in-copyright deny-list** — this is a personal-use tool on
   the operator's own machine, not redistribution
3. **Rewrite TASK-RAG-003** to smoke-test against the real corpus (Mr Bruff
   guides + primary texts), not just the Standard Ebooks Macbeth excerpt

---

## What to keep (working correctly)

- `ingest_corpus.py` DECISION-RAG-001 alignment (TASK-RAG-001A): `OpenAIEmbeddingFunction`
  via llama-swap, `data/chroma/` persist dir, `gcse-english-v1` collection,
  env var support — all correct
- The four-folder source-type classification (`primary_text/`,
  `secondary_study_guide/`, `secondary_critical/`, `context_historical/`) —
  useful semantic distinction for `decide_retrieval()` logic
- Idempotent upsert, NDJSON summary, `.primary_text_index` sidecar — solid
  operational scaffolding
- `CorpusChunk` model and the `chunk_json` hydration contract with `retrieval.py`
  — the runtime consumer doesn't care how chunks were produced
- Citation anchor inference for primary Shakespeare text — genuinely useful for
  the quote fidelity rubric on plays
- AQA assessment material refusal (`past_paper`, `mark_scheme`,
  `examiner_report` pattern) — **keep this**; mark schemes in the retrieval
  corpus would short-circuit the Socratic questioning behaviour the fine-tune
  teaches. This is a pedagogical guard, not a copyright guard.
- The Standard Ebooks Macbeth `.txt` already in `primary_text/` — continues to
  work as a primary-text source alongside docling output

---

## Change 1: Accept docling markdown output in `load_corpus()` / `ingest_corpus.py`

### Current state

`corpus.py`'s `load_corpus(root)` walks the four subfolders and calls
`file_path.read_text(encoding="utf-8")` on each file. It likely filters on
file extension (needs confirming — check whether `.md` files are accepted or
only `.txt`).

### Target state

The ingestion workflow becomes:

```
PDF → docling (on GB10, standard or VLM mode) → .md file
  ↓
Drop .md into appropriate subfolder:
  domains/gcse-english/sources/secondary_study_guide/mr-bruff-macbeth.md
  domains/gcse-english/sources/primary_text/inspector-calls.md
  domains/gcse-english/sources/context_historical/victorian-era-context.md
  ↓
python scripts/ingest_corpus.py
  → load_corpus() reads .txt AND .md files
  → chunks each file
  → embeds via llama-swap
  → upserts into ChromaDB gcse-english-v1
```

### What needs changing

1. **File extension filter in `load_corpus()`**: Accept `.md` alongside `.txt`
   (and `.xhtml` if Standard Ebooks EPUB extraction produces that). Check the
   current implementation — it may already accept any file, in which case this
   is a no-op.

2. **Chunking for markdown**: Docling markdown has structure (headers, tables,
   bullet lists). The current chunker may be a naive text splitter designed for
   plain prose. Two options:
   - **Minimal**: treat docling markdown as plain text for chunking purposes.
     Headers become part of the chunk text, which is fine for embedding and
     retrieval. Loses some structure but works immediately.
   - **Better**: respect markdown header boundaries when chunking, so a chunk
     doesn't split mid-section. This is a small enhancement to the chunker.
     Not required for v1 but worth noting as a follow-up.

3. **Citation anchor inference**: `_infer_play_anchor` looks for `^Act [IVX]+`
   and `^Scene [IVX]+` at start-of-line. This will fire correctly on primary
   play text regardless of whether it came from Standard Ebooks `.txt` or
   docling-processed PDF `.md` (the act/scene markers are in the text either
   way). For secondary study guides (Mr Bruff), the anchor will return `None`,
   which is correct — secondary content doesn't have act/scene citations.

4. **Source type mapping**: The subfolder determines the `SourceType`. This
   works unchanged — the operator's job is to put docling output in the right
   folder. Document this in `CONTRIBUTING-CORPUS.md`.

### Docling processing instructions (for CONTRIBUTING-CORPUS.md)

Add a section documenting the workflow. The exact docling CLI syntax should be
confirmed against the version installed on the GB10 — the ADF's
`ingestion/docling_processor.py` has the working invocation. The key points:

- Standard mode for digital PDFs (Mr Bruff ebooks, Standard Ebooks, etc.)
- VLM mode for scanned paperbacks (Inspector Calls, Power & Conflict poems)
- Output goes into the appropriate source subfolder
- Run `ingest_corpus.py` after processing

---

## Change 2: Remove the in-copyright deny-list

### Current state

`corpus.py` contains:

```python
INCOPYRIGHT_TITLES: frozenset[str] = frozenset({
    "inspector_calls",
    "blood_brothers",
    "dna",
    "lord_of_the_flies",
    "anita_and_me",
    "animal_farm",
})
```

Files whose normalised `text_name` matches any of these are refused at ingest
with `RefusalReason.IN_COPYRIGHT_TITLE`.

### Target state

Remove `INCOPYRIGHT_TITLES` and the check that uses it. Keep the AQA assessment
material refusal (`AQA_REFUSAL_PATTERN`) — that's a pedagogical guard.

### Rationale

This is a personal-use tool running on the operator's own machine for a family
member's GCSE revision. The source material (Mr Bruff guides, scanned play
texts) was legally purchased. No redistribution occurs — the ChromaDB
collection lives on the GB10's local filesystem. The deny-list was designed
for a hypothetical open-source redistribution scenario that doesn't apply.

With the deny-list removed, the operator can ingest:
- Inspector Calls (scanned via HP OfficeJet → docling VLM → primary_text/)
- Power & Conflict poems (scanned → docling VLM → primary_text/)
- An Inspector Calls teacher resource pack (→ secondary_study_guide/)
- Any other legally purchased study material

### Implementation

1. Remove `INCOPYRIGHT_TITLES` frozenset from `corpus_models.py` (or
   `corpus.py`, wherever it lives)
2. Remove the `RefusalReason.IN_COPYRIGHT_TITLE` enum variant
3. Remove the check in `load_corpus()` that matches against the deny-list
4. Update or remove any tests that assert the deny-list behaviour
5. Update `CONTRIBUTING-CORPUS.md` to remove the deny-list documentation and
   replace with a note that the corpus is for personal use only

---

## Change 3: Rewrite TASK-RAG-003 spec

### Current spec problems

The current TASK-RAG-003 is tightly coupled to the "Standard Ebooks Macbeth
only" corpus:
- Fixtures built from a Macbeth excerpt
- Assertions on `PlayCitationAnchor` with `act == 1`
- Demo cue cards referencing only primary text retrieval signals
- No coverage of secondary study guide retrieval

### What the rewritten spec should cover

1. **Smoke test against real corpus**: Macbeth primary text (Standard Ebooks)
   + at least one Mr Bruff secondary guide (docling-processed). Two retrieval
   paths exercised:
   - Primary text: `reason=retrieve:primary_present`, `VerifierMetadata`
     with `primary_matches` populated, citation anchors present
   - Secondary study guide: `reason=retrieve:primary_present` (secondary
     chunks retrieved alongside primary), no citation anchors (anchor=None),
     content available for grounding

2. **AO3 bypass**: Still valid — `focus_aos={"AO3"}` should produce
   `reason=ao3_only:training_first` and zero retrieval calls

3. **Demo cue cards**: Update for DDD Southwest to show both retrieval paths —
   the audience should see the selective retrieval thesis across primary and
   secondary content

4. **Operator runbook**: Updated to reflect the docling workflow (process PDF
   → drop .md → ingest → serve → verify signals)

### Recommendation

Do not implement TASK-RAG-003 as currently specced. Rewrite the spec after
Changes 1 and 2 land, then implement. TASK-RAG-002 (CLI wiring) can proceed
independently.

---

## Existing ADF chunks — re-process, don't bridge

The 3,850 chunks in `agentic-dataset-factory/chroma_data_backup/` were embedded
with a different model (not `nomic-embed-text`) and use a different metadata
schema (`source_file`, `page_number`, `docling_mode` — not `CorpusChunk`).
Bridging these requires both re-embedding and schema translation.

**Recommended approach:** Re-run docling on the original Mr Bruff PDFs (still
at `agentic-dataset-factory/domains/gcse-english-tutor/sources/`). The PDFs
are small (< 3 MB each), docling runs in seconds on the GB10, and re-processing
gives you consistent chunking and metadata. The resulting `.md` files go into
`study-tutor/domains/gcse-english/sources/secondary_study_guide/`.

Source PDFs available for re-processing:

| PDF | ADF chunks | Target folder |
|---|---|---|
| `Lang-Guide-4th-edition-Sept-2025-5fgv5j.pdf` | 540 | `secondary_study_guide/` |
| `Literature-Guide-June-21st-2025-ebook-9dkdzh.pdf` | 572 | `secondary_study_guide/` |
| `Macbeth203rd20edition-hvhcex.pdf` | 680 | `secondary_study_guide/` (Mr Bruff commentary, not the play) |
| `Mr-Bruffs-Guide-to-An-Inspector-Calls-2nd-edition.pdf` | 623 | `secondary_study_guide/` (now ingestible with deny-list removed) |
| `Mr-Bruffs-Guide-to-Christmas-Carol-Feb2022-xx7wta.pdf` | 492 | `secondary_study_guide/` |
| `Power-and-Conflict-Guide-2nd--wsazur.pdf` | 605 | `secondary_study_guide/` |
| `Practice-paper-2nd-edition-l2zc7o.pdf` | 338 | **Refused** by AQA_REFUSAL_PATTERN (correct) |

---

## Task sequencing after this review

```
1. This review → implement (course correction)
   - Change 1: accept .md files in load_corpus()
   - Change 2: remove INCOPYRIGHT_TITLES deny-list
   - Update CONTRIBUTING-CORPUS.md with docling workflow
   - Update tests

2. TASK-RAG-002 (CLI wiring) → can proceed in parallel
   - Wires providers + coach_handover closure
   - Independent of corpus content/shape

3. Docling processing (operator, on GB10)
   - Re-run docling on Mr Bruff PDFs
   - Run docling on scanned Inspector Calls / Power & Conflict
   - Drop .md output into appropriate source subfolders
   - Run ingest_corpus.py

4. TASK-RAG-003 rewrite → then implement
   - Smoke test against real corpus (primary + secondary)
   - Updated demo cue cards
   - Updated operator runbook
```

---

## References

- [DECISION-RAG-001 — Unified ChromaDB approach](../../../guardkit/docs/decisions/DECISION-RAG-001-unified-chromadb-approach.md)
- [ADR-FLEET-002 — Selective retrieval](../../docs/decisions/) (always-on RAG suppresses fine-tuned behaviour)
- [scripts/ingest_corpus.py](../../scripts/ingest_corpus.py)
- [src/study_tutor/knowledge/corpus.py](../../src/study_tutor/knowledge/corpus.py)
- [src/study_tutor/knowledge/corpus_models.py](../../src/study_tutor/knowledge/corpus_models.py)
- [agentic-dataset-factory/ingestion/docling_processor.py](../../../agentic-dataset-factory/ingestion/docling_processor.py) — working docling invocation
- [agentic-dataset-factory/domains/gcse-english-tutor/sources/](../../../agentic-dataset-factory/domains/gcse-english-tutor/sources/) — Mr Bruff PDFs for re-processing
- [tasks/backlog/TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md](../../tasks/backlog/TASK-RAG-002-cli-wire-retrieval-and-coach-handover.md)
- [tasks/backlog/TASK-RAG-003-end-to-end-rag-smoke-session.md](../../tasks/backlog/TASK-RAG-003-end-to-end-rag-smoke-session.md) — to be rewritten
