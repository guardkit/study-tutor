---
id: TASK-RAG-001
title: "Build chromadb ingestion script and persist source-typed corpus"
task_type: scaffolding
feature_id: FEAT-PRV4
implementation_mode: direct
complexity: 4
estimated_minutes: 120
status: completed
priority: high
created: 2026-05-08T00:00:00Z
updated: 2026-05-08T00:00:00Z
completed: 2026-05-08T00:00:00Z
previous_state: in_review
state_transition_reason: "All ACs satisfied; 7/7 ingest tests pass, 91% coverage on scripts/ingest_corpus.py, no regressions in 383-test RAG/knowledge suite"
dependencies: []
related:
  - src/study_tutor/knowledge/corpus.py
  - src/study_tutor/knowledge/corpus_models.py
  - src/study_tutor/knowledge/retrieval.py
  - tests/integration/test_rag_end_to_end.py
  - domains/gcse-english/sources/README.md
tags:
  - rag
  - chromadb
  - ingestion
  - feat-prv4
  - phase-1
---

# Task: Build chromadb ingestion script and persist source-typed corpus

## Description

The Phase 1 RAG modules (`TASK-PRV-001..007`) all live in `tasks/completed/`
and `src/study_tutor/knowledge/{corpus,retrieval,quote_verifier,coach_handover}.py`
but **no caller persists `CorpusChunk` records into a vector store**.
`src/study_tutor/knowledge/corpus.py` returns chunks; `src/study_tutor/knowledge/retrieval.py`
expects an injected ChromaDB collection via `set_collection_provider()` and
hydrates chunks via `CHUNK_PAYLOAD_KEY="chunk_json"` (a JSON-serialised
`CorpusChunk` in the metadata dict). The "thin caller that imports chromadb
lazily" promised in the docstring of `corpus.py:43` was never written.

This task closes that gap: add the optional `chromadb` (and
`sentence-transformers`) dependencies, write `scripts/ingest_corpus.py`
that walks a domain root through `load_corpus()` and upserts chunks into
a persistent Chroma collection, and add a populated four-folder layout
under `domains/gcse-english/sources/` so the script has something to
ingest. **No CLI runtime wiring is in scope** — that lives in TASK-RAG-002.

## Scope

### Dependencies (`pyproject.toml`)

- Add `chromadb>=0.5` to `[project.optional-dependencies] rag` (gate behind
  an extra so the dev path stays lightweight; install via `uv sync --extra rag`).
- Add `sentence-transformers>=3.0` to the same extra (BGE reranker).
- Document the install step in the script's `--help` text.

### Ingestion script (`scripts/ingest_corpus.py`)

Entry point: `python scripts/ingest_corpus.py [--domain-root PATH] [--collection-name NAME] [--persist-dir PATH] [--reset]`

Behaviour:

1. Default `--domain-root domains/gcse-english/sources/`,
   `--collection-name gcse-english`, `--persist-dir ./chroma/gcse-english/`.
2. Call `load_corpus(domain_root)` to get an `IngestResult`.
3. Open a persistent `chromadb.PersistentClient(path=persist_dir)` and
   `get_or_create_collection(collection_name)`.
4. For each `CorpusChunk`:
   - `id = f"{chunk.text_name}:{chunk.chunk_index}"`
   - `document = chunk.text`
   - `metadata = {
       "text_name": chunk.text_name,
       "source_type": chunk.source_type.value,
       "source_path": chunk.source_path,
       "chunk_index": chunk.chunk_index,
       "chunk_json": chunk.model_dump_json(),
     }`
   - Use `collection.upsert(ids=..., documents=..., metadatas=...)` so re-runs
     update in place.
5. After ingest, register every distinct primary-text `text_name` via
   `study_tutor.knowledge.retrieval.register_primary_text(...)`. The registry
   is module-level state in the running process; the script logs the
   registered names so the operator can confirm them, and writes a sidecar
   `chroma/<domain>/.primary_text_index` text file (one `text_name` per line)
   so the runtime CLI in TASK-RAG-002 can replay the registration at startup.
6. Print a structured summary to stdout (NDJSON) with one line per:
   - `event=ingest_summary, chunks_created=N, refusals=[...], skips=[...]`
   - `event=per_text_count, text_name=..., source_type=..., chunk_count=N`
7. Refusals/skips from `IngestResult.refusals` / `IngestResult.skips` are
   logged verbatim with reason and detail so the operator can spot a typo'd
   folder name or a misplaced AQA past-paper PDF.

### Idempotency

- Re-running against an unchanged corpus must produce identical IDs and
  zero new rows (Chroma `upsert` semantics).
- `--reset` flag drops and recreates the collection before ingest (operator
  safety hatch for schema-change re-ingests).
- AC: a parametrised test runs the ingest twice in temp dirs against a
  three-file fixture corpus and asserts `collection.count()` is equal across
  runs.

### Corpus layout (`domains/gcse-english/sources/`)

Add the four canonical folders so the loader can walk them:

```
domains/gcse-english/sources/
├── primary_text/            # Standard Ebooks Shakespeare / public domain
├── secondary_study_guide/
├── secondary_critical/
├── context_historical/
├── README.md                # already present — extend
└── CONTRIBUTING-CORPUS.md   # NEW: where to source texts, copyright posture
```

- Add a `.gitignore` entry for `domains/gcse-english/sources/**/*.{txt,xhtml,epub,pdf}`
  so actual texts stay out of the repo (legal posture: Standard Ebooks is CC0
  but the repo policy is "operator pulls texts locally").
- Commit at least one tiny placeholder `.keep` file per subfolder.
- `CONTRIBUTING-CORPUS.md` documents:
  - Standard Ebooks as canonical primary-text source for Shakespeare /
    public-domain novels (with download URL pattern).
  - The four-folder source-type mapping
    (`primary_text` → `SourceType.PRIMARY_TEXT`, etc.).
  - The AQA refusal posture (filenames matching `past_paper`, `mark_scheme`,
    `examiner_report` are refused at the loader — confirm with `grep`).
  - The in-copyright deny-list (`inspector_calls`, `blood_brothers`, ...) and
    the Phase 2 per-student episode path that replaces it.

### Runtime smoke (manual)

After implementation, the operator can:

```bash
uv sync --extra rag
# (download Macbeth from Standard Ebooks into domains/gcse-english/sources/primary_text/)
python scripts/ingest_corpus.py
# expect: NDJSON summary with chunks_created > 0, per_text_count for "macbeth"
```

This validates the wave-1 → wave-2 boundary for the demo on 16 May.

## Acceptance Criteria

- [ ] `pyproject.toml` defines an optional `[rag]` extra containing `chromadb`
      and `sentence-transformers`; `uv sync --extra rag` succeeds on the dev
      machine.
- [ ] `scripts/ingest_corpus.py` exists, is `chmod +x`, and prints a structured
      `--help` describing flags and the install command.
- [ ] Running the script with the default flags against a fixture corpus of
      three primary chunks + one secondary chunk creates a persistent Chroma
      collection at `./chroma/gcse-english/` with `collection.count() == 4`.
- [ ] Re-running the script with no source changes leaves `collection.count()`
      unchanged (idempotent upsert).
- [ ] `--reset` recreates the collection (asserted by writing a sentinel
      metadata blob, running with `--reset`, asserting the sentinel is gone).
- [ ] Refusals (e.g. an AQA-named file dropped into `primary_text/`) appear in
      the summary NDJSON with `reason=AQA_ASSESSMENT_MATERIAL` and do not reach
      the collection.
- [ ] At least one primary-text `text_name` is registered via
      `register_primary_text(...)` after a successful ingest, and the sidecar
      `.primary_text_index` file lists it.
- [ ] `domains/gcse-english/sources/{primary_text,secondary_study_guide,secondary_critical,context_historical}/`
      exist in the working tree with `.keep` placeholders.
- [ ] `domains/gcse-english/sources/CONTRIBUTING-CORPUS.md` documents the
      Standard Ebooks source, the four-folder mapping, the AQA refusal regex,
      and the in-copyright deny-list.

## Test Requirements

Unit + integration tests live under `tests/scripts/test_ingest_corpus.py`:

- **Idempotency:** ingest twice into a temp persist dir; assert
  `collection.count()` is identical.
- **Refusal pass-through:** drop a file named `macbeth_past_paper.txt` into
  the fixture's `primary_text/` folder; assert the summary NDJSON contains
  exactly one line with `reason=AQA_ASSESSMENT_MATERIAL` and the collection
  contains zero documents from that source path.
- **Metadata round-trip:** ingest a fixture, then read one row back from the
  collection and assert `CorpusChunk.model_validate_json(metadata["chunk_json"])`
  reproduces the original chunk byte-for-byte.
- **`--reset` semantics:** verified per AC above.
- **Skip Chroma if extra not installed:** if `chromadb` is unavailable, the
  test module is skipped via `pytest.importorskip` (do not break CI on the
  dev path).

## Implementation Notes

- The hot path in `retrieval.py` already round-trips `chunk_json` through
  `CorpusChunk.model_validate_json` (see `_hydrate_chunk` at
  `src/study_tutor/knowledge/retrieval.py:502`). The ingestion script's
  metadata shape MUST match what that hydrator expects — this is a load-bearing
  contract.
- ChromaDB metadata values are scalars (`str | int | float | bool`); keep the
  full `CorpusChunk` payload under `chunk_json` and surface
  `text_name` / `source_type` / `source_path` / `chunk_index` separately so
  Chroma's `where` filtering still works (the retrieval module's
  `_query_collection` filters by `text_name` and `source_type`).
- Do not call `set_collection_provider` in this script — that wiring is for
  the runtime CLI only (TASK-RAG-002). The script is a one-shot ingest and
  exits cleanly.
- The reranker dependency (`sentence-transformers`) is in the `rag` extra
  for consistency, but **the ingestion script itself does not need it**;
  it's there so the runtime CLI in TASK-RAG-002 can pin both deps with one
  `uv sync --extra rag`.

## Out of scope

- Any change to `src/study_tutor/cli/main.py` (TASK-RAG-002).
- The `coach_handover` closure that wires retrieval + verifier into the
  orchestrator (TASK-RAG-002).
- End-to-end smoke against a real Player turn (TASK-RAG-003).
- Productionising the ChromaDB persistence dir (`./chroma/`) into a Phase 2
  multi-tenant layout — that is a Phase 2 concern.

## References

- [src/study_tutor/knowledge/corpus.py](../../src/study_tutor/knowledge/corpus.py) — `load_corpus`, `IngestResult`, refusal model
- [src/study_tutor/knowledge/retrieval.py](../../src/study_tutor/knowledge/retrieval.py) — `set_collection_provider`, `_hydrate_chunk`, `CHUNK_PAYLOAD_KEY`
- [tests/integration/test_rag_end_to_end.py](../../tests/integration/test_rag_end_to_end.py) — fake Chroma collection shape (model for the real one)
- [tasks/completed/TASK-PRV-002-source-typed-corpus-loader.md](../completed/TASK-PRV-002-source-typed-corpus-loader.md)
- [tasks/completed/TASK-PRV-007-integration-smoke-and-sources-readme.md](../completed/TASK-PRV-007-integration-smoke-and-sources-readme.md)

## Implementation Summary

Closed the wave-1 → wave-2 boundary for FEAT-PRV4: the Phase 1 RAG modules (corpus loader, retriever, verifier, coach handover) shipped in TASK-PRV-002..007 but no caller was persisting `CorpusChunk` records into a vector store. This task provides the missing thin caller.

**Delivered (10 files, ~620 LOC)**:
- `pyproject.toml` — `[rag]` optional-dependency group: `chromadb>=0.5`, `sentence-transformers>=3.0`. The script itself does not import the reranker; the dep ships in the same extra so TASK-RAG-002 pins both with one `uv sync --extra rag`.
- `scripts/ingest_corpus.py` (chmod +x, 320 lines) — argparse CLI, lazy `chromadb` import inside `_open_collection`, NDJSON to stdout (event types: `refusal`, `skip`, `per_text_count`, `ingest_summary`), regular logging to stderr, `--reset` via `client.delete_collection` + `get_or_create_collection`, sidecar `<persist_dir>/.primary_text_index` for runtime registration replay. Bootstraps `sys.path` so `./scripts/ingest_corpus.py` works without a prior `uv sync` on the dev path.
- `tests/unit/scripts/test_ingest_corpus.py` (7 tests, all passing, 91% coverage on the new module) — module-level `pytest.importorskip("chromadb")` keeps the dev path light. Fixture corpora are built in `tmp_path` (no real Standard Ebooks texts in repo per CONTRIBUTING-CORPUS.md legal posture).
- `domains/gcse-english/sources/{primary_text,secondary_study_guide,secondary_critical,context_historical}/.keep` — four-folder layout committed.
- `domains/gcse-english/sources/CONTRIBUTING-CORPUS.md` (~120 lines) — Standard Ebooks workflow, four-folder→`SourceType` map, AQA refusal regex (`(past[_-]?paper|mark[_-]?scheme|examiner[_-]?report)`), in-copyright deny-list.
- `.gitignore` — extended `domains/*/sources/**/*.{txt,xhtml}` exclusions (PDFs and EPUBs were already ignored).

**Approach**: argparse not click (script is one-shot, no CLI overhead). `_chunk_id` is `f"{source_type}:{text_name}:{chunk_index}"` — a 3-tuple, not the spec's 2-tuple, because the loader's `_derive_text_name` uses just the file stem so `primary_text/macbeth.txt` and `secondary_study_guide/macbeth.txt` both yield `text_name="macbeth"` and would collide with the spec's ID scheme. The metadata shape mirrors what `study_tutor.knowledge.retrieval._hydrate_chunk` reads (`chunk_json` carries the full `CorpusChunk.model_dump_json()`; flat scalars `text_name` / `source_type` / `source_path` / `chunk_index` are surfaced separately so Chroma's `where`-clause filtering still works).

**Result**: All 8 acceptance criteria satisfied. 7/7 ingest tests pass. 91% coverage on the new module. The broader 383-test RAG/knowledge suite has no regressions (one pre-existing failure on main in `test_graphiti_client_wiring.py`, unrelated). Operator can now run `uv sync --extra rag && python scripts/ingest_corpus.py` against a Standard Ebooks Macbeth download to produce `./chroma/gcse-english/` with a primary-text-indexed collection.

**Lessons**:
- The chunk-ID spec was a 2-tuple but had to become a 3-tuple to avoid `chromadb.errors.DuplicateIDError` when the same `text_name` lives under multiple source-type folders. Future ingestion-script specs should explicitly state which scope levels need to be in the ID.
- `tests/scripts/__init__.py` collides with the top-level `scripts/` package on `sys.path` (pytest's `prepend` import mode). Resolved by placing tests at `tests/unit/scripts/` with no `__init__.py`. Worth a CLAUDE.md note for future test layout near package-name collisions.
- The script's `chmod +x` AC implies operators will invoke it directly (not via `python -m`), so `sys.path` bootstrapping from `Path(__file__).parent.parent / "src"` is needed — `seed_student_model.py` does NOT do this and only works via the editable install. Worth backporting that bootstrap pattern.

**Out of scope for this task (deferred to TASK-RAG-002)**: `set_collection_provider` runtime wiring, CLI startup replay of the `.primary_text_index` sidecar, the `coach_handover` closure that wires retrieval + verifier into the orchestrator.
