# GCSE English — Bring Your Own Sources

This directory is where you place the study-guide PDFs that will be ingested
into the RAG knowledge layer. **Nothing in this directory is tracked by
git**: the `.gitignore` at the repo root excludes every PDF under
`domains/*/sources/`, so your acquired materials stay on your machine.

Phase 0 of the tutor runs purely from the fine-tuned Gemma 4 weights and
does not require anything in this directory. You only need to populate it
once the Phase 1 RAG grounding layer lands (FEAT-PO-006 — see
[rag-grounding-design.md](../../../docs/research/ideas/rag-grounding-design.md)
and the empirical validation in
[openwebui-rag-empirical-findings-2026-04-23.md](../../../docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md)).

---

## 1. What to acquire

The tutor is source-agnostic. Any GCSE English study guide that comes as a
DRM-free PDF or can be exported to PDF from its native format will work.
The following have been used or evaluated by the project team:

### Tested

- **Mr Bruff** GCSE English guides (mrbruff.com) — sold as DRM-free PDF
  direct from the author. These were the source material for the first
  fine-tune; the pipeline has been validated end-to-end against them.
  Titles used: Macbeth, *A Christmas Carol*, *An Inspector Calls*, *Power
  and Conflict* poetry anthology. Per-title pricing, no subscription.

### Known alternatives (not yet tested in this pipeline)

- **CGP** GCSE English Literature and Language revision guides — sold in
  print; the PDF/online version is bundled via the CGP "Online Edition"
  code printed inside the book.
- **York Notes** (Pearson) — title-per-text study guides sold as print and
  Kindle. PDF availability varies; check the publisher's page before
  purchase.
- **Pearson Revise** / **Collins Revision** — broad-coverage revision
  guides. Typically print-primary; digital companions are patchy.

### Do NOT add

The following must not be placed in this directory, even for private use
on your own machine — the tutor's domain contract (see
[../GOAL.md §6](../GOAL.md)) and the
[copyright-training-data-analysis.md](../../../docs/research/ideas/copyright-training-data-analysis.md)
rationale preclude them:

- **AQA past papers, mark schemes, examiner reports.** AQA explicitly
  prohibits any use of its assessment materials "in any manner or for any
  purposes in connection with the training of Artificial Intelligence
  powered tools or technologies". This includes RAG context.
- **Scanned or downloaded copies of print-only study guides where you do
  not own the digital edition.** The pipeline requires a legitimately
  acquired source; DRM circumvention is out of scope for this project.
- **Anything you have not paid for or been licensed to use.**

The AQA *specification* (the curriculum document describing paper
structure and AOs) is factual reference material and is treated the same
way any textbook publisher references it — see GOAL.md §2 for the
distinction between specification and assessment materials.

---

## 2. Where to put them

The layout below is a suggestion; the ingestion pipeline is source-agnostic
about subdirectories and will recurse. Use whatever shape makes it easy for
you to see what you have.

```
domains/gcse-english/sources/
├── mrbruff/
│   ├── macbeth.pdf
│   ├── a-christmas-carol.pdf
│   ├── an-inspector-calls.pdf
│   └── power-and-conflict.pdf
├── cgp/
│   └── gcse-english-literature.pdf
└── york-notes/
    └── jekyll-and-hyde.pdf
```

`git status` after dropping files in here should show **no new files**. If
it lists any PDF as untracked, stop and fix the `.gitignore` entry before
committing anything.

---

## 3. How ingestion runs (Phase 1, not yet wired in)

The ingestion pipeline itself lives in the separate
[`agentic-dataset-factory`](https://github.com/appmilla/agentic-dataset-factory)
repository and will be reused by this project once FEAT-PO-006 (RAG
grounding) lands. Until then, the tutor runs entirely on the fine-tuned
Gemma 4 weights via Ollama on GB10 and does not consult this directory.

The target invocation, once wired, will look like:

```bash
# From the repo root, with the .venv active
.venv/bin/study-tutor ingest \
    --domain gcse-english \
    --sources domains/gcse-english/sources \
    --chroma chroma/gcse-english
```

The expected steps inside that command are:

1. **Docling PDF extraction** — each PDF processed in Docling's standard
   mode into markdown-ish chunks with section/page metadata.
2. **Chunking** — 512-token windows with 64-token overlap (tuned against
   the empirical findings from 23 Apr 2026).
3. **Embedding** — `nomic-embed-text-v1.5` served from GB10 on port 8001.
4. **ChromaDB persist** — collection `gcse-english`, persisted under
   `chroma/` at the repo root (also gitignored).

The Phase 1 build plan will link to the exact command reference once the
pipeline is integrated.

---

## 4. What gets published, what stays private

| Artefact | In this repo? | Why |
|----------|---------------|-----|
| This README | ✅ Yes | Explains what to acquire; no copyrighted content |
| Source PDFs you add to this directory | ❌ No | Gitignored; your acquired materials stay yours |
| ChromaDB collection built from those PDFs | ❌ No | Intermediate computational copy; not distributed |
| `train.jsonl` (synthetic training data) | ❌ No | Derived from copyrighted RAG context |
| Fine-tuned LoRA adapter / merged GGUF weights | ❌ No | Not distributed in this repo |
| Gemma 4 base model | ❌ No | Pulled from Google/Ollama registries at runtime |
| Pipeline code | ✅ Yes (via `agentic-dataset-factory`) | Source-agnostic; no copyrighted content embedded |

The "pipeline is open, data is private" split is the project's core
compliance stance and is explained in full in
[docs/licensing.md](../../../docs/licensing.md) and
[copyright-training-data-analysis.md](../../../docs/research/ideas/copyright-training-data-analysis.md).

---

## 5. Troubleshooting

- **`git status` lists one of my PDFs as a new file.** The `.gitignore`
  entry didn't catch it. Check the file's extension (`.PDF` vs `.pdf` —
  the gitignore is case-sensitive) and the path. Add a more specific
  ignore line before committing.
- **Docling extraction fails on a specific PDF.** Usually a scanned image
  PDF rather than a text PDF. Re-export from the source application, or
  OCR it locally before placing it here.
- **ChromaDB query returns chunks from the wrong book.** Check the
  per-book metadata tagging in the ingestion output — the filename is
  the default `source` tag. Rename files clearly before ingesting.
- **Ingestion is slow.** First-time embeddings for a full Mr Bruff
  library on CPU take ~20 minutes; use the GB10-served embedder
  (port 8001) for a sub-minute run.

---

*Phase 0 placeholder: ingestion pipeline integration tracked under FEAT-PO-006. Revisit this README when that feature lands so the commands above stop being aspirational.*
