---
id: TASK-PRV-009
title: "Add PoetryCitationAnchor to support Power and Conflict (and other primary poetry) ingestion"
task_type: feature
feature_id: FEAT-PRV4
parent_task: TASK-RAG-003
implementation_mode: task-work
complexity: 4
estimated_minutes: 150
status: backlog
priority: medium
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
related:
  - src/study_tutor/knowledge/corpus_models.py
  - src/study_tutor/knowledge/corpus.py
  - src/study_tutor/knowledge/retrieval.py
  - tests/unit/knowledge/test_corpus.py
  - tests/unit/knowledge/test_corpus_models.py
  - tasks/backlog/TASK-RAG-003-end-to-end-rag-smoke-session.md
tags:
  - rag
  - corpus
  - citation-anchor
  - poetry
  - power-and-conflict
  - feat-prv4
  - phase-1
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: PoetryCitationAnchor for primary-text poetry

## Provenance

Surfaced during TASK-RAG-003 spec rewrite (2026-05-09). The AQA Power and
Conflict anthology is one of the GCSE set texts the operator wants to
ingest as `primary_text/`. Once docling-VLM-processed (the anthology is
typically scanned), the resulting `.md` lands in `primary_text/` correctly
— but every chunk gets `citation_anchor=None` because the schema only
supports `PlayCitationAnchor` (Act/Scene/Line) and `NovelCitationAnchor`
(Chapter/Paragraph). There's no anchor type for "poem N, line M".

## Description

Add a third member to the `CitationAnchor` discriminated union for poetry
primary texts, plus the matching inferer in `corpus.py`, plus tests.

After this lands:
- A docling-VLM `.md` of the Power and Conflict anthology dropped into
  `primary_text/` produces chunks with `PoetryCitationAnchor(poem_title=...,
  line=N)` instead of `None`.
- `VerifierMetadata.primary_matches` can carry per-poem citations — e.g.
  "Ozymandias, line 14" — for the quote-fidelity rubric.
- TASK-RAG-003's smoke test gains a third primary anchor type to spot-check
  if a poetry fixture is added.

## Scope

### Schema (`src/study_tutor/knowledge/corpus_models.py`)

```python
class PoetryCitationAnchor(BaseModel):
    """Citation anchor for a chunk drawn from a poem (poem title + line)."""
    model_config = ConfigDict(extra="forbid")
    kind: Literal["poetry"] = "poetry"
    poem_title: str = Field(min_length=1)
    line: int

CitationAnchor = Annotated[
    Union[PlayCitationAnchor, NovelCitationAnchor, PoetryCitationAnchor],
    Field(discriminator="kind"),
]
```

Update `__all__`.

### Inferer (`src/study_tutor/knowledge/corpus.py`)

Add a `_POEM_TITLE_PATTERN` that matches a likely poem-title line. Two
heuristics are reasonable; pick the one that round-trips cleanly through
docling output of the AQA anthology:

- **Markdown-aware:** `^\s*##?\s+(.+)$` (matches `# Ozymandias` or
  `## London`). Docling's standard mode often emits headers as `## `.
- **Standalone-line heuristic:** a non-empty line where the next blank line
  is followed by content, and the line contains no sentence punctuation
  (`.`, `?`, `!`). This catches all-caps-or-titlecase standalone titles
  even without markdown formatting.

Add `_infer_poem_anchor(file_text, char_offset)` modelled on
`_infer_play_anchor`:
- Walk lines, track `current_poem_title` from `_POEM_TITLE_PATTERN` matches
- Count non-empty non-title lines within each poem
- On the first content line at/past `char_offset`, capture
  `(current_poem_title, line_count)` and return `PoetryCitationAnchor`
- Return `None` if no title has been seen by `char_offset` (front-matter
  region — the anthology will have an editor's preface).

Update `_infer_citation_anchor` to dispatch in this order:
1. `_ACT_PATTERN.search(file_text)` → play
2. `_CHAPTER_PATTERN.search(file_text)` → novel
3. `_POEM_TITLE_PATTERN.search(file_text)` → poetry  *(new)*
4. else `None`

Update the patterns in `corpus.py` to carry `re.MULTILINE` (consistency
with PRV-008).

### Tests (`tests/unit/knowledge/test_corpus.py` and
`tests/unit/knowledge/test_corpus_models.py`)

Unit tests for the schema:
- `test_poetry_citation_anchor_round_trips_through_pydantic`
- `test_citation_anchor_discriminator_routes_poetry_kind`

Unit tests for the inferer:
- `POETRY_FIXTURE` constant: 2-3 short poems with markdown title headers
  (`## Ozymandias`, `## London`), separated by blank lines, each 4-6 lines.
- `test_loader_infers_poetry_anchor_per_chunk` — load fixture, assert at
  least one chunk has `PoetryCitationAnchor` with correct `poem_title` and
  `line ≥ 1`.
- `test_poetry_anchor_returns_none_in_anthology_front_matter` — fixture
  with editor preface before the first poem; chunks in the preface region
  return `None`.
- `test_loader_handles_play_novel_poetry_in_same_corpus_run` — a corpus
  with a play primary, novel primary, and poetry primary; each produces
  the right anchor type. Mirrors the existing
  `test_a_play_and_a_novel_coexist_in_the_corpus_...` BDD intent.

### Optional: retrieval surface (`src/study_tutor/knowledge/retrieval.py`)

If the verifier surface (TASK-PRV-005) does anything anchor-type-specific,
extend it to handle the poetry case. Most likely: nothing changes —
`isinstance(anchor, PoetryCitationAnchor)` is a new branch in any
anchor-formatting code, and the round-trip through `chunk_json` already
works because Pydantic v2 discriminated-union parsing uses `kind`.

## Acceptance criteria

- [ ] `PoetryCitationAnchor` defined in `corpus_models.py` with
      `poem_title: str` (min_length=1) and `line: int`, plus `kind:
      Literal["poetry"]` as the discriminator.
- [ ] `CitationAnchor` discriminated union includes the new variant.
- [ ] `_POEM_TITLE_PATTERN` and `_infer_poem_anchor` added to `corpus.py`;
      dispatcher updated; all three patterns carry `re.MULTILINE`.
- [ ] Unit tests cover: schema round-trip, discriminator routing, anchor
      inference at chunk level, front-matter `None` case, mixed-corpus
      coexistence.
- [ ] Existing `PlayCitationAnchor` and `NovelCitationAnchor` tests still
      pass unchanged.
- [ ] Loader run against a docling-processed Power and Conflict `.md`
      drops in `primary_text/`, produces ≥80% of chunks with a populated
      `PoetryCitationAnchor` (front-matter / editor-preface region may
      legitimately remain `None`).
- [ ] Loader run against the existing Mr Bruff `secondary_study_guide/`
      `.md` files still produces `citation_anchor=None` (poetry inferer
      must NOT fire on secondary content — only on `PRIMARY_TEXT` chunks
      via `source_type` gating in `_process_file`).

## Out of scope

- AQA Power and Conflict anthology operator processing (separate operator
  workflow on the GB10 — docling VLM mode).
- Poem-title canonicalisation (e.g., normalising "OZYMANDIAS",
  "Ozymandias", "Ozymandias by Percy Bysshe Shelley" to a single
  canonical key). Treat the title as captured verbatim from the markdown
  header for v1.
- Cross-poem chunk boundaries — if a chunk spans two poems' boundary,
  pick the title of the poem the chunk *starts* in. No new behaviour
  beyond what `_chunk_text` already does.
- Stanza-level granularity (some poems have meaningful stanzas).
  v1 uses line numbers only; stanza support can be a future enhancement.

## References

- [tasks/backlog/TASK-RAG-003-end-to-end-rag-smoke-session.md](TASK-RAG-003-end-to-end-rag-smoke-session.md) §"Out of scope" — where this task is referenced
- [tasks/completed/TASK-PRV-008/](../completed/TASK-PRV-008/) — sibling regex fix; this task should not regress its `re.MULTILINE` change
- [src/study_tutor/knowledge/corpus_models.py](../../src/study_tutor/knowledge/corpus_models.py)
- [src/study_tutor/knowledge/corpus.py](../../src/study_tutor/knowledge/corpus.py)
