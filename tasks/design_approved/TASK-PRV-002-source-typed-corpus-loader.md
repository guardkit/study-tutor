---
complexity: 5
consumer_context:
- consumes: SourceTypedCorpus
  driver: pydantic
  format_note: CorpusChunk + CitationAnchor union (kind-discriminated) consumed verbatim
    — citation_anchor is None for non-primary chunks
  framework: Pydantic v2 (BaseModel + discriminated union)
  task: TASK-PRV-001
dependencies:
- TASK-PRV-001
estimated_minutes: 75
feature_id: FEAT-PRV4
id: TASK-PRV-002
implementation_mode: task-work
parent_review: TASK-REV-PRV4
priority: high
related_features:
- FEAT-PH1-004
status: design_approved
tags:
- feat-ph1-004
- corpus
- ingestion
- copyright
- chunker
task_type: feature
test_results:
  coverage: null
  last_run: null
  status: pending
title: Source-typed corpus loader with copyright refusal
wave: 2
---

# Task: Source-typed corpus loader with copyright refusal

## Description

Implement `src/study_tutor/knowledge/corpus.py:load_corpus` — walks
the four-folder source tree, infers `SourceType` from parent
directory, refuses copyrighted material at the loader, chunks text
with citation-anchor metadata, and emits `CorpusChunk` records into
ChromaDB.

## Scope

- `load_corpus(root: Path) -> IngestResult` — recursively loads the
  four canonical source-type folders; emits one structured log per
  refusal/skip
- Source-type inference from parent directory name; unknown
  directory → skip with warning
- AQA assessment-material refusal: filename regex
  `r"(?i)(past[_-]?paper|mark[_-]?scheme|examiner[_-]?report)"` →
  refuse + structured log + reference publisher prohibition
- In-copyright deny-list refusal: case-insensitive substring match
  against filename stem against `INCOPYRIGHT_TITLES = {"inspector_calls",
  "blood_brothers", "dna", "lord_of_the_flies", "anita_and_me",
  "animal_farm"}` → refuse + structured log + advise per-student
  Phase 2 path
- Path-traversal safety: resolve every path against the corpus root;
  reject any file whose resolved path escapes the root
- Resilience to corrupted files: skip + structured log; rest of
  corpus loads
- Whitespace-only files: skip + structured log
- Empty primary-text folder: emit zero chunks, no error
- Citation-anchor inference (TASK-PRV-001's `CitationAnchor`
  union):
  - Plays: parse Standard Ebooks SCENE markers + line numbers
  - Novels: parse CHAPTER headings, paragraph index running count
  - Fallback to `citation_anchor=None` with a structured warning when
    inference fails
- Chunker adapted from
  `agentic-dataset-factory/ingestion/chunker.py` —
  `RecursiveCharacterTextSplitter` with `chunk_size=512`, `overlap=100`
  (per 23-Apr empirical findings §3d). Each chunk's metadata extends
  the ADF shape with `source_type`, `text_name`, `citation_anchor`
- ChromaDB persistence under `chroma/gcse-english/` (gitignored)

## Out of Scope

- `should_retrieve` decision function (TASK-PRV-003)
- Source-filtered retrieval (TASK-PRV-004)
- Quote verifier (TASK-PRV-005)
- Per-student in-copyright Text episodes (Phase 2)

## Acceptance Criteria

- [ ] Loading a four-folder corpus produces `CorpusChunk`s with
      correct `source_type` per folder (covers @key-example
      @ingestion scenario "loader infers source type")
- [ ] AQA past-paper-named file is refused; refusal log line
      references publisher prohibition (covers @negative @ingestion
      @copyright scenario)
- [ ] In-copyright modern set text in `primary_text/` is refused;
      log advises per-student Phase 2 path (covers @negative
      @ingestion @copyright scenario)
- [ ] Empty `primary_text/` folder produces zero chunks and no error
      (covers @boundary @ingestion scenario)
- [ ] Whitespace-only file is skipped with structured log (covers
      @boundary @ingestion scenario)
- [ ] Corrupted file in `primary_text/` is skipped; valid file in
      same folder still loads (covers @edge-case @ingestion
      @resilience scenario)
- [ ] Path-traversal file is rejected; refusal log names the
      attempt (covers @edge-case @ingestion @security scenario)
- [ ] Plays produce chunks with `PlayCitationAnchor` (act/scene/line);
      novels produce chunks with `NovelCitationAnchor`
      (chapter/paragraph) (covers @edge-case @verify @integration
      @citation scenario)
- [ ] No chunk carries an unset/default source-type label (covers
      @key-example @ingestion scenario)
- [ ] All modified files pass project-configured lint/format checks
      with zero errors

## Test Requirements

- [ ] Unit test: source-type inference for each of the four folders
- [ ] Unit test: AQA filename regex catches `past_paper.pdf`,
      `Mark-Scheme.pdf`, `examiner_report_2024.pdf`
- [ ] Unit test: in-copyright deny-list catches `inspector_calls.txt`
      and `Inspector-Calls.txt` (case-insensitive)
- [ ] Unit test: path traversal — `../etc/passwd` placed in
      `primary_text/` is rejected
- [ ] Unit test: corrupted-file resilience using a fixture with one
      valid + one corrupted file
- [ ] Unit test: empty folder produces empty chunk list and an
      `IngestResult` with `chunks_created=0`
- [ ] Unit test: citation-anchor inference produces a
      `PlayCitationAnchor` for a Standard Ebooks Macbeth fixture
      and a `NovelCitationAnchor` for a Christmas Carol fixture

## Seam Tests

The following seam test validates the integration contract with
TASK-PRV-001's models:

```python
"""Seam test: verify loader emits CorpusChunk with correctly-typed
CitationAnchor union per the SourceTypedCorpus contract."""
import pytest
from study_tutor.knowledge.corpus_models import (
    CorpusChunk, PlayCitationAnchor, NovelCitationAnchor, SourceType,
)


@pytest.mark.seam
@pytest.mark.integration_contract("SourceTypedCorpus")
def test_corpus_chunk_carries_typed_citation_anchor(tmp_path):
    """Verify CorpusChunk objects from load_corpus carry the
    discriminated CitationAnchor union, not a plain dict.

    Contract: corpus loader emits CorpusChunk; primary chunks carry
    a non-None citation_anchor of the correct kind for the text type.
    Producer: TASK-PRV-001 (models)
    Consumer: this task (loader); TASK-PRV-005 (verifier reads
    citation_anchor directly from chunk metadata, never re-parses
    text).
    """
    # Fixture: place a small play under primary_text/ and load.
    # ... (concrete fixture during implementation)
    chunks = []  # await load_corpus(tmp_path)

    primary_play_chunks = [
        c for c in chunks
        if c.source_type is SourceType.PRIMARY_TEXT
        and c.text_name == "macbeth"
    ]

    assert primary_play_chunks, "expected primary-text chunks for play"
    for chunk in primary_play_chunks:
        assert chunk.citation_anchor is not None, \
            "primary-text chunks must carry citation_anchor"
        assert isinstance(chunk.citation_anchor, PlayCitationAnchor), \
            f"plays must carry PlayCitationAnchor, got {type(chunk.citation_anchor)}"
```

## Implementation Notes

**Why adapt the ADF chunker rather than import it as a dependency:**
agentic-dataset-factory is a separate repo; adding it as a build
dependency for a 30-line `RecursiveCharacterTextSplitter` wrapper
adds cross-repo coupling that the Phase 1 timeline can't absorb.
Copying the shape of `chunker.py` into `corpus.py` and extending the
metadata dict with source-typed fields is the simpler path.

**Why citation-anchor inference is best-effort:** Standard Ebooks
markup is regular but not perfectly machine-readable. A failed
inference (e.g. mid-scene chunk boundary) sets
`citation_anchor=None` and emits a structured warning — the
verifier handles None gracefully (it won't annotate a citation it
doesn't have). This is cheaper than blocking ingestion on perfect
parsing.

**Why ChromaDB persistence is gitignored:** the corpus contains
copyrighted study-guide content; only the pipeline code is public.
See `domains/gcse-english/sources/README.md §4`.

## Test Execution Log

[Populated by /task-work]