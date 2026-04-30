# GCSE English — Bring Your Own Sources

This directory is where you place the source material that will be ingested
into the RAG knowledge layer (FEAT-PRV4 / FEAT-PH1-004 — primary-text-RAG and
quote verifier). **Nothing in this directory is tracked by git**: the
`.gitignore` at the repo root excludes every PDF and text file under
`domains/*/sources/`, so your acquired materials stay on your machine.

The Phase 1 RAG grounding layer is now wired against the four-folder layout
documented below. The fine-tuned Gemma 4 weights still serve every Phase 0
fallback path; the corpus loader (`study_tutor.knowledge.corpus.load_corpus`,
TASK-PRV-002) walks this directory to populate the typed corpus that the
retriever (TASK-PRV-004) and quote verifier (TASK-PRV-005) consume.

For the design rationale and the empirical validation behind the chunking +
embedder choices see
[rag-grounding-design.md](../../../docs/research/ideas/rag-grounding-design.md)
and
[openwebui-rag-empirical-findings-2026-04-23.md](../../../docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md).

---

## 1. Folder layout — four source-typed buckets

The loader infers the chunk's `SourceType` from the immediate parent
directory name. There are **exactly four recognised folders**; anything
outside them is skipped with a structured log warning so a typo
(`primary-text` vs `primary_text`) is loud, not silent.

```
domains/gcse-english/sources/
├── primary_text/            -> SourceType.PRIMARY_TEXT
├── secondary_study_guide/   -> SourceType.SECONDARY_STUDY_GUIDE
├── secondary_critical/      -> SourceType.SECONDARY_CRITICAL
└── context_historical/      -> SourceType.CONTEXT_HISTORICAL
```

What goes in each folder:

| Folder | Contents | Examples |
|---|---|---|
| `primary_text/` | The literary work itself, in plain text. The verifier annotates verbatim quotations from these chunks with structured citations (act/scene/line for plays, chapter/paragraph for novels). | *Macbeth* play text, *A Christmas Carol* novel text |
| `secondary_study_guide/` | Study guides, revision notes, teaching material *about* the primary text. Quoted spans found here are rewritten with a deterministic attribution (`as one study guide notes, …`) — never framed as the primary author's words. | Mr Bruff guides, CGP / York Notes / Pearson Revise |
| `secondary_critical/` | Critical / scholarly essays and analyses. Treated the same as study guides for verification (deterministic attribution, no primary-author citation). | Open-access journal articles, public-domain critical introductions |
| `context_historical/` | Historical / cultural background that contextualises the primary text but is not directly about it. Reserved for future AO3-context-historical turns; **not** mixed into AO1/AO2 evidence retrieval. | Public-domain history of Jacobean theatre, biographies, contemporary letters |

`git status` after dropping files in here should show **no new files**. If
it lists a source file as untracked, stop and fix the `.gitignore` entry
before committing anything.

---

## 2. Primary text — Standard Ebooks is the canonical source

Per the FEAT-PRV4 design (R4 / ASSUM-004), **Standard Ebooks** is the
canonical primary-text source for everything in `primary_text/`. Standard
Ebooks publishes carefully-typeset, public-domain editions of literary
works as plain-text and EPUB downloads with no DRM. Their Shakespeare
editions in particular preserve the act/scene/line markers the loader's
citation-anchor inferer keys off, so a freshly-downloaded
`primary_text/macbeth.txt` is ready to ingest with no manual editing.

Recommended workflow for primary texts:

1. Download the plain-text edition from
   [standardebooks.org](https://standardebooks.org/) for any work that's
   in the public domain (most pre-1928 GCSE set texts: Shakespeare,
   Dickens, Stevenson, Brontë, Conan Doyle, etc.).
2. Save it as `domains/gcse-english/sources/primary_text/<title>.txt`
   using a lowercase, hyphen-free filename — the file's stem becomes the
   chunk's `text_name` (e.g. `macbeth.txt` → `text_name="macbeth"`).
3. Re-run the loader; the fresh chunks are tagged
   `SourceType.PRIMARY_TEXT` and carry a typed
   `PlayCitationAnchor` / `NovelCitationAnchor` derived from the
   structural markers in the source.

**Modern in-copyright set texts** (e.g. *An Inspector Calls*, *Anita and
Me*) are deliberately **not** sourced this way — see §3 below.

---

## 3. What the loader refuses to ingest

The loader (TASK-PRV-002, `study_tutor.knowledge.corpus`) refuses two
classes of material at the folder boundary, so no ChromaDB write ever sees
them:

### 3.1 AQA assessment material — refused unconditionally

AQA's assessment-material licence explicitly prohibits any use of past
papers, mark schemes, or examiner reports "in any manner or for any
purposes in connection with the training of Artificial Intelligence
powered tools or technologies". This includes RAG context.

The loader matches the `AQA_REFUSAL_PATTERN` regex (case-insensitive,
substring of the filename) against every file before ingestion:

```
(past[_-]?paper|mark[_-]?scheme|examiner[_-]?report)
```

A filename matching that pattern is logged as a refusal and dropped — no
chunks are produced. The same pattern is duplicated as defence-in-depth
inside the retriever (`AQA_FILENAME_PATTERN`); if a record ever slips
past ingestion, the retrieval-time filter catches it. Both regexes are
intentionally independent — if you change one, evaluate the other
separately.

The AQA *specification* (the curriculum document describing paper
structure and AOs) is factual reference material and is **not** refused —
treat it the same way any textbook publisher references it. See
[../GOAL.md §2](../GOAL.md) for the distinction between specification and
assessment materials.

### 3.2 In-copyright modern set texts — deny-list

Modern set texts where the digital edition is gated behind a publisher
licence are matched against an in-copyright deny-list and refused at the
loader. Per-student access for these texts goes via the Phase 2 path
(an authenticated per-student episode) rather than bulk ingestion into
the shared corpus. This is the load-bearing reason `primary_text/` is
canonically populated from Standard Ebooks: every text that's free to
ingest is also free to redistribute as a typeset edition, and every text
that isn't free to ingest is handled out-of-band.

### 3.3 What this means in practice

Do **not** drop the following into any subfolder, even for private use:

- AQA past papers, mark schemes, examiner reports — refused.
- Scanned or downloaded copies of print-only study guides where you do
  not own the digital edition. The pipeline requires a legitimately
  acquired source; DRM circumvention is out of scope.
- Anything you have not paid for or been licensed to use.

Refusals are emitted as structured log lines (`logger.warning` with
`event="corpus_refusal"`) so the corpus owner can audit what didn't make
it in. Skips (whitespace-only files, binary/corrupted files, files
outside the four canonical folders) are logged separately so the rest of
the corpus still loads when one file is malformed.

---

## 4. What gets published, what stays private

| Artefact | In this repo? | Why |
|----------|---------------|-----|
| This README | ✅ Yes | Explains what to acquire; no copyrighted content |
| Source files you add to this directory | ❌ No | Gitignored; your acquired materials stay yours |
| ChromaDB collection built from those sources | ❌ No | Intermediate computational copy; not distributed |
| `train.jsonl` (synthetic training data) | ❌ No | Derived from copyrighted RAG context |
| Fine-tuned LoRA adapter / merged GGUF weights | ❌ No | Not distributed in this repo |
| Gemma 4 base model | ❌ No | Pulled from Google/Ollama registries at runtime |
| Pipeline code | ✅ Yes (via `agentic-dataset-factory`) | Source-agnostic; no copyrighted content embedded |

The "pipeline is open, data is private" split is the project's core
compliance stance and is explained in full in
[docs/licensing.md](../../../docs/licensing.md) and
[copyright-training-data-analysis.md](../../../docs/research/ideas/copyright-training-data-analysis.md).

The ingestion pipeline itself continues to live in the separate
[`agentic-dataset-factory`](https://github.com/appmilla/agentic-dataset-factory)
repository; the loader in this repo (TASK-PRV-002) handles the
read-and-classify side of the boundary, and `agentic-dataset-factory`
handles the synthetic-training-data side.

---

## 5. Troubleshooting

- **`git status` lists one of my source files as a new file.** The
  `.gitignore` entry didn't catch it. Check the file's extension
  (`.PDF` vs `.pdf` — the gitignore is case-sensitive) and the path. Add
  a more specific ignore line before committing.
- **The loader logs `corpus_refusal` for a file I expected to ingest.**
  The filename matches either the AQA pattern (`past_paper`,
  `mark_scheme`, `examiner_report`) or the in-copyright deny-list. If
  the match is a false positive (e.g. a critical essay whose title
  happens to contain "mark scheme"), rename the file before ingesting.
- **The loader logs `unknown_folder_skipped`.** A subfolder name doesn't
  match any of the four canonical buckets in §1. Move the file into one
  of `primary_text/`, `secondary_study_guide/`, `secondary_critical/`,
  or `context_historical/`.
- **A primary-text chunk has `citation_anchor = None`.** The Standard
  Ebooks file's structural markers (`ACT I` / `SCENE 1`, or chapter
  headings) didn't parse cleanly. The loader emits a structured warning
  with the offending offset; either fix the source file's markers or
  accept the missing anchor (the verifier treats `None` as "no anchor
  available" rather than blocking ingestion).
- **ChromaDB query returns chunks from the wrong book.** Check the
  per-book `text_name` tagging in the loader output — the file's stem
  is the default `text_name`. Rename files clearly before ingesting.
- **Ingestion is slow.** First-time embeddings for a full corpus on CPU
  take ~20 minutes; use the GB10-served embedder (port 8001) for a
  sub-minute run.

---

*Source layout owned by FEAT-PRV4. Loader behaviour is documented
inline in `src/study_tutor/knowledge/corpus.py`; the verifier contract
the loader feeds is documented in
`src/study_tutor/knowledge/quote_verifier.py`.*
