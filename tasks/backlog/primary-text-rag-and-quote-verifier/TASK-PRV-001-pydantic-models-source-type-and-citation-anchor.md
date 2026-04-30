---
id: TASK-PRV-001
title: Define Pydantic models for source type and citation anchor
task_type: declarative
parent_review: TASK-REV-PRV4
feature_id: FEAT-PRV4
wave: 1
implementation_mode: direct
complexity: 2
estimated_minutes: 25
dependencies: []
status: pending
priority: high
tags:
- feat-ph1-004
- pydantic
- models
- foundation
related_features:
- FEAT-PH1-004
- FEAT-PH1-003
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Define Pydantic models for source type and citation anchor

## Description

Foundation models consumed by every other subtask. Stack-agnostic
declaratives only — no I/O, no ChromaDB, no business logic.

## Scope

- `SourceType(str, Enum)` with four values: `PRIMARY_TEXT`,
  `SECONDARY_STUDY_GUIDE`, `SECONDARY_CRITICAL`, `CONTEXT_HISTORICAL`
- `PlayCitationAnchor` Pydantic model: `kind: Literal["play"]`,
  `act: int`, `scene: int`, `line: int`
- `NovelCitationAnchor` Pydantic model: `kind: Literal["novel"]`,
  `chapter: int`, `paragraph: int`
- `CitationAnchor = Annotated[Play|Novel, Field(discriminator="kind")]`
  — Pydantic v2 discriminated union
- `CorpusChunk` Pydantic model: `text`, `source_type`, `source_path`,
  `text_name`, `citation_anchor: CitationAnchor | None`, `chunk_index`
- Module location: `src/study_tutor/knowledge/corpus_models.py`

## Out of Scope

- Corpus loader logic (TASK-PRV-002)
- Verifier metadata models (TASK-PRV-005 — VerifierMetadata is
  intentionally co-located with the verifier, not in this module)

## Acceptance Criteria

- [ ] `SourceType` enum exposes all four values matching the
      filesystem layout (covers @key-example @ingestion scenario
      "loader infers source type from folder")
- [ ] `CitationAnchor` is a Pydantic v2 discriminated union — given
      `{"kind":"play","act":5,"scene":1,"line":35}`, parses as
      `PlayCitationAnchor`; `{"kind":"novel","chapter":3,"paragraph":7}`
      parses as `NovelCitationAnchor`
- [ ] `CorpusChunk` allows `citation_anchor=None` (for non-primary
      chunks) and rejects unknown `source_type` values
- [ ] `text_name` field is a non-empty string (Pydantic constraint)
- [ ] Module imports cleanly with no Graphiti / ChromaDB / file I/O
      dependencies
- [ ] All modified files pass project-configured lint/format checks
      with zero errors

## Test Requirements

- [ ] Unit test: `SourceType` enum membership (all four values)
- [ ] Unit test: `PlayCitationAnchor` round-trips through
      `model_dump()` / `model_validate()`
- [ ] Unit test: `NovelCitationAnchor` round-trips
- [ ] Unit test: discriminator dispatch — wrong `kind` raises
      `ValidationError`
- [ ] Unit test: `CorpusChunk` accepts `citation_anchor=None` for
      `SECONDARY_STUDY_GUIDE` and rejects empty `text_name`

## Implementation Notes

**Why a discriminated union and not a single CitationAnchor model
with Optional fields:** discriminated unions give us exhaustiveness
checking — adding a new citation kind (e.g. poetry) becomes a
type-system change rather than a runtime guess about which fields
apply. The verifier's match logic uses
`isinstance(anchor, PlayCitationAnchor)` rather than
`anchor.act is not None`, which is much harder to misuse.

**Why models live in `corpus_models.py`, not `corpus.py`:**
TASK-PRV-005 (verifier) consumes these models without needing the
loader code — keeping models in a dedicated module avoids importing
ChromaDB transitively into the verifier's test surface.

## Test Execution Log

[Populated by /task-work]
