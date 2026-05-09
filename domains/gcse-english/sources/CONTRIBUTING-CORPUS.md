# Contributing to the GCSE English corpus

This document is the operator-facing guide to populating
`domains/gcse-english/sources/`. The user-facing overview lives in
[`README.md`](./README.md); this file is the *short, copy-pasteable* version
for someone who has just cloned the repo and wants to ingest a corpus.

For the design rationale (R4 / ASSUM-004), see
[`docs/research/ideas/rag-grounding-design.md`](../../../docs/research/ideas/rag-grounding-design.md)
and the empirical chunking findings in
[`docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md`](../../../docs/research/ideas/openwebui-rag-empirical-findings-2026-04-23.md).

---

## Folder layout — one folder per `SourceType`

The loader (`study_tutor.knowledge.corpus.load_corpus`, TASK-PRV-002) walks
exactly four canonical folders and infers the chunk's `SourceType` from the
parent directory name. Anything outside these four is skipped with a
structured warning.

| Folder | `SourceType` | Holds |
|---|---|---|
| `primary_text/` | `PRIMARY_TEXT` | The literary work itself, plain text |
| `secondary_study_guide/` | `SECONDARY_STUDY_GUIDE` | Study guides, revision notes, teaching material |
| `secondary_critical/` | `SECONDARY_CRITICAL` | Critical / scholarly essays |
| `context_historical/` | `CONTEXT_HISTORICAL` | Historical / cultural background (Phase 2 surface) |

Each folder ships with a `.keep` placeholder so the structure is committed
even when no operator-acquired material is present. **No source files are
ever committed** — see §4 below.

---

## 1. Standard Ebooks is the canonical primary-text source

[Standard Ebooks](https://standardebooks.org/) publishes carefully-typeset,
public-domain editions of literary works as plain-text and EPUB downloads
with no DRM. Their Shakespeare editions in particular preserve the
`act` / `scene` / `line` markers the loader's citation-anchor inferer keys
off (see `_infer_play_anchor` in `src/study_tutor/knowledge/corpus.py`).

### Recommended workflow

1. Find the work on standardebooks.org. Most pre-1928 GCSE set texts are
   available: Shakespeare, Dickens, Stevenson, Brontë, Conan Doyle, etc.
2. Download the **plain-text** edition (`.txt`). XHTML works too; PDF is
   discouraged because the chunker is line-oriented.
3. Save it as `primary_text/<title>.txt` using a lowercase, hyphen-free
   filename. The file's stem becomes the chunk's `text_name`:

   ```
   domains/gcse-english/sources/primary_text/macbeth.txt   →  text_name = "macbeth"
   ```

4. Run the ingestion script (TASK-RAG-001):

   ```bash
   uv sync --extra rag
   python scripts/ingest_corpus.py
   ```

   Expected stdout (one NDJSON object per line):

   ```json
   {"event": "ingest_summary", "chunks_created": 412, "refusals": 0, "skips": 0}
   {"event": "per_text_count", "text_name": "macbeth", "source_type": "PRIMARY_TEXT", "chunk_count": 412}
   ```

The ChromaDB collection is persisted to `data/chroma/` (gitignored). A
sidecar `.primary_text_index` lists the registered `text_name`s so the
runtime CLI in TASK-RAG-002 can replay registration at startup.

---

## 1a. Embeddings & topology

Per [DECISION-RAG-001 — Unified ChromaDB approach for fleet
RAG](../../../guardkit/docs/decisions/DECISION-RAG-001-unified-chromadb-approach.md)
(accepted 2026-05-07), the ingestion script and the runtime retriever both
share a single fleet-wide ChromaDB pattern:

| Concern | Setting | Override |
|---|---|---|
| Embeddings endpoint | llama-swap at `http://localhost:9000/v1` | `LLM_EMBEDDINGS_BASE_URL` |
| Embedding model | `nomic-embed-text` (v1.5, 768 dim) | `LLM_EMBEDDINGS_MODEL` |
| Auth | `not-needed` (llama-swap ignores it) | `LLM_EMBEDDINGS_API_KEY` |
| Persist directory | `data/chroma/` (per-project root) | `CHROMA_PERSIST_DIR` |
| Collection name | `gcse-english-v1` (versioned) | `CHROMA_COLLECTION` |

CLI flags on `scripts/ingest_corpus.py` (`--persist-dir`, `--collection-name`)
still win over env vars.

**Ingestion runs on the GB10** where llama-swap and the persist dir are both
localhost — zero network hops for embedding or storage. The fleet shares
the persist root across collections (e.g. a future `gcse-maths-v1` lives in
the same `data/chroma/` directory as a separate collection), which is the
shape Chroma is designed for. The specialist-agent (architect role) follows
the same pattern with its own `architect-knowledge-v1` collection — see
DECISION-RAG-001 §4.

---

## 2. AQA assessment material is refused unconditionally

AQA's assessment-material licence prohibits use of past papers, mark
schemes, and examiner reports "in any manner or for any purposes in
connection with the training of Artificial Intelligence powered tools or
technologies". The loader enforces this at the folder boundary with the
following regex (case-insensitive, substring match against the filename):

```
(past[_-]?paper|mark[_-]?scheme|examiner[_-]?report)
```

A filename matching that pattern is logged as a refusal and dropped — no
chunks are produced. The same regex is duplicated as defence-in-depth in
the retriever (`AQA_FILENAME_PATTERN` in
`src/study_tutor/knowledge/retrieval.py`); if a record ever slipped past
ingestion, the retrieval-time filter catches it.

You can confirm the regex location with:

```bash
grep -n "AQA_REFUSAL_PATTERN" src/study_tutor/knowledge/corpus.py
grep -n "AQA_FILENAME_PATTERN" src/study_tutor/knowledge/retrieval.py
```

The AQA *specification* (the curriculum document describing paper
structure and AOs) is factual reference material and is **not** refused —
treat it the same way any textbook publisher references it.

---

## 3. Personal-use posture

This is a personal-use tool running on the operator's own machine for a
family member's GCSE revision. Source materials (Mr Bruff guides,
scanned play texts, etc.) are legally acquired by the operator and the
ChromaDB collection lives on the local filesystem only — there is no
redistribution, no shared service, and no public corpus. The only
content gate the loader enforces is the AQA pedagogical refusal in §2.

The previous in-copyright deny-list (TASK-PRV-002) was designed for a
hypothetical open-source redistribution scenario that does not apply
here; it was removed in TASK-RAG-CC1 alongside the introduction of the
docling-based ingestion workflow in §3a.

---

## 3a. Docling-based ingestion for PDFs and scanned material

Standard Ebooks (§1) covers the public-domain primary texts. For
everything else — Mr Bruff study guides, scanned paperbacks of modern
set texts, Power & Conflict poems, etc. — the workflow runs through
[docling](https://github.com/docling-project/docling):

1. **Standard mode** for digital PDFs (Mr Bruff ebooks, exam-board PDFs
   that aren't refused by §2).
2. **VLM mode** for scanned paperbacks (e.g. an Inspector Calls
   paperback scanned via the operator's HP OfficeJet).
3. The output is a structured markdown (`.md`) file.
4. Drop the `.md` file into the appropriate source-type subfolder
   (§ "Folder layout" — primary text under `primary_text/`,
   secondary commentary under `secondary_study_guide/`, etc.).
5. Run `python scripts/ingest_corpus.py`.

The loader is extension-agnostic (`_iter_files` walks `rglob('*')` and
reads UTF-8), so a `.md` file ingests identically to a `.txt` file. No
code change is required to accept docling output — only this
documentation.

The working docling invocation lives in the dataset-factory repo at
[`agentic-dataset-factory/ingestion/docling_processor.py`](https://github.com/appmilla/agentic-dataset-factory).
That script is the source of truth for CLI flags and is intentionally
not transcribed here so this file does not drift out of sync with the
processor's actual behaviour.

> **Optional follow-up:** the current chunker is line-oriented and
> ignores markdown structure. A header-aware chunker that respects
> docling's heading boundaries is a worthwhile enhancement but not
> required for v1 — see the FEAT-PRV4 backlog.

---

## 4. What gets committed, what stays private

| Artefact | Committed? | Why |
|---|---|---|
| This file, `README.md` | ✅ | Structure + sourcing guidance |
| `.keep` placeholders in each folder | ✅ | Preserves folder layout |
| Source files you add (`.txt`, `.md`, `.xhtml`, `.epub`, `.pdf`) | ❌ | Gitignored; your acquired materials stay yours |
| ChromaDB collection (`data/chroma/`) | ❌ | Gitignored; rebuildable from sources |
| `.primary_text_index` sidecar | ❌ | Gitignored (lives next to the chroma dir) |

The `.gitignore` entry that enforces this (extended in TASK-RAG-001):

```
domains/*/sources/*.{pdf,PDF,epub,txt,md,xhtml}
domains/*/sources/**/*.{pdf,PDF,epub,txt,md,xhtml}
chroma/
data/chroma/
```

`git status` after dropping a source file should show **no new files**.
If it lists one, stop and fix the `.gitignore` before committing.

---

## 5. Re-ingesting and resetting

The script is idempotent: re-running it against an unchanged corpus
produces zero new rows (Chroma `upsert` semantics, deterministic IDs of
the form `<text_name>:<chunk_index>`).

If you change the chunker tuning, citation-anchor inference, or any other
schema-affecting code path, drop and recreate the collection:

```bash
python scripts/ingest_corpus.py --reset
```

`--reset` deletes the collection before ingest. Use this when re-ingesting
after a schema change; do **not** use it for routine re-runs.

---

## 6. Where to ask

- **Loader behaviour** — module docstring of
  `src/study_tutor/knowledge/corpus.py` is the single source of truth.
- **Retrieval contract** — `src/study_tutor/knowledge/retrieval.py` documents
  the `chunk_json` metadata shape the ingestion script must match.
- **Legal posture** — [`docs/licensing.md`](../../../docs/licensing.md).

The "pipeline is open, data is private" split is the project's compliance
stance. The ingestion pipeline itself continues to live in the separate
[`agentic-dataset-factory`](https://github.com/appmilla/agentic-dataset-factory)
repository for the synthetic-training-data side; the loader and ingestion
script in this repo handle the read-and-classify side of that boundary.
