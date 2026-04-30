---
id: TASK-PRV-004
title: Source-filtered retrieval with reranker degradation
task_type: feature
parent_review: TASK-REV-PRV4
feature_id: FEAT-PRV4
wave: 3
implementation_mode: task-work
complexity: 5
estimated_minutes: 70
dependencies:
- TASK-PRV-002
- TASK-PRV-003
status: pending
priority: high
tags:
- feat-ph1-004
- retrieval
- chromadb
- reranker
- resilience
related_features:
- FEAT-PH1-004
test_results:
  status: pending
  coverage: null
  last_run: null
consumer_context:
- task: TASK-PRV-002
  consumes: SourceTypedCorpus
  framework: "ChromaDB (where filter on source_type + text_name metadata)"
  driver: chromadb
  format_note: "ChromaDB collection filtered via where={'source_type': ..., 'text_name': ...} returns CorpusChunk-shaped records"
- task: TASK-PRV-003
  consumes: RetrievalDecision
  framework: "Python NamedTuple"
  driver: stdlib
  format_note: "Skip retrieval if RetrievalDecision.retrieve == False; pass reason into turn metadata"
---

# Task: Source-filtered retrieval with reranker degradation

## Description

Implement `src/study_tutor/knowledge/retrieval.py:retrieve` —
source-filtered ChromaDB similarity search with reranker baseline,
graceful degradation when the reranker is unavailable, and
defence-in-depth AQA exclusion at retrieval time.

## Scope

- `retrieve(query: str, text_name: str, focus_aos: set[str], top_k:
  int = 6) -> list[CorpusChunk]` — the primary read entry point
- ChromaDB filter: `{"text_name": text_name}` AND
  `{"source_type": {"$in": [primary, secondary_*]}}` (excludes
  `context_historical` for non-AO3 turns)
- Primary-first ordering: results sorted such that all
  `PRIMARY_TEXT` chunks come before any `SECONDARY_*` chunks at
  equal score
- Top-K limit (`ASSUM-001` confirmed: K=6); when fewer than K
  primary chunks exist, fill with secondary up to K
- Reranker: `BAAI/bge-reranker-v2-m3` CPU-only baseline. Optional —
  module-level constant `RERANKER_MODEL = "BAAI/bge-reranker-v2-m3"`
  with `try`/`except ImportError` guard for graceful degradation
- When reranker unavailable: return chunks ordered by base
  similarity; emit a `mode="no_rerank"` flag in turn metadata
- Defence-in-depth AQA exclusion: filter out any chunk whose
  `source_path` matches the AQA filename regex even if it slipped
  past ingestion (overlap with TASK-PRV-002 refusal — the safety
  invariant is enforced at both points)
- Empty result handling: when `text_name` has no chunks (e.g.
  Inspector Calls), return `[]` and the orchestrator records the
  reason `no primary-text edition available` in turn metadata

## Out of Scope

- The decision function itself (TASK-PRV-003 already shipped)
- Quote verifier (TASK-PRV-005)
- Coach handover wiring (TASK-PRV-006)

## Acceptance Criteria

- [ ] Filtered retrieval prefers primary-text chunks over secondary
      at equal score (covers @key-example @smoke @retrieval
      @primary scenario "retrieves source-filtered chunks")
- [ ] Top-K boundary: 7 available primary chunks → 6 returned;
      0 available → empty list; 3 → 3 returned (covers @boundary
      @retrieval Scenario Outline)
- [ ] Retrieval for a `text_name` with no primary edition returns
      `[]` and the orchestrator records `no primary-text edition
      available` reason (covers @negative @retrieval scenario)
- [ ] AQA-pattern filename in chunk metadata is excluded at
      retrieval-time even if present in the collection (covers
      @negative @retrieval @copyright scenario)
- [ ] Reranker unavailability does not block the turn — chunks
      returned in base similarity order with `mode="no_rerank"`
      recorded (covers @edge-case @retrieval @resilience scenario)
- [ ] Filter excludes `context_historical/` chunks for non-AO3
      turns (the four-folder layout invariant)
- [ ] All modified files pass project-configured lint/format checks
      with zero errors

## Test Requirements

- [ ] Unit test: primary-first ordering at equal score (fixture
      with 3 primary + 3 secondary chunks at the same similarity)
- [ ] Parametrised unit test: top-K boundary (0/3/6/7 available →
      0/3/6/6 returned)
- [ ] Unit test: empty corpus for `text_name` returns `[]`
- [ ] Unit test: reranker import-failure path (mock `ImportError`)
      returns chunks without rerank
- [ ] Unit test: AQA-pattern filename in metadata is filtered out
- [ ] Integration test (with a small fixture corpus): retrieve for
      Macbeth + AO1+AO2 returns primary-first chunks with citation
      anchors

## Seam Tests

```python
"""Seam test: verify retrieval honours the SourceTypedCorpus contract
and the RetrievalDecision skip path."""
import pytest
from study_tutor.knowledge.corpus_models import CorpusChunk, SourceType
from study_tutor.knowledge.retrieval import retrieve


@pytest.mark.seam
@pytest.mark.integration_contract("SourceTypedCorpus")
def test_retrieve_returns_primary_first_with_citation_anchors(small_corpus):
    """Verify retrieve() returns CorpusChunk objects with primary-text
    chunks ordered first, and that primary chunks carry
    citation_anchor.

    Contract: retrieve() consumes the SourceTypedCorpus contract
    and emits chunks downstream to TASK-PRV-005 (verifier reads
    citation_anchor directly).
    """
    chunks = retrieve("witches in macbeth", "macbeth",
                      focus_aos={"AO1", "AO2"})

    primary = [c for c in chunks if c.source_type is SourceType.PRIMARY_TEXT]
    secondary = [c for c in chunks if c.source_type is not SourceType.PRIMARY_TEXT]

    # Primary-first ordering invariant
    if primary and secondary:
        primary_max_idx = max(chunks.index(c) for c in primary)
        secondary_min_idx = min(chunks.index(c) for c in secondary)
        assert primary_max_idx < secondary_min_idx, \
            "primary chunks must come before secondary chunks"

    for chunk in primary:
        assert chunk.citation_anchor is not None, \
            "primary chunks must carry citation_anchor"
```

## Implementation Notes

**Why reranker is optional, not required:** the 23-Apr empirical
findings showed the reranker improves retrieval quality but
~568 MB download from HuggingFace is a one-time cost and CI may
not have the model cached. ImportError + structured-log fallback
keeps the test surface fast and the demo robust.

**Why AQA exclusion is enforced at both ingestion and retrieval:**
defence in depth. If a file slips past the ingestion regex (typo,
new filename pattern), the retrieval-time filter is the safety net.
The cost is minimal — the filter is a regex over a metadata field
already present in every chunk record.

**Why `context_historical` is excluded for non-AO3 turns:** the
folder is reserved for AO3-context-historical retrievals; mixing
it into AO1/AO2 evidence retrieval would dilute the result list
with material that's pedagogically wrong for the criterion. AO3
mixed-mode retrieval is a future enhancement (Phase 1 only ships
the folder structure, not the AO3 retrieval path itself).

## Test Execution Log

[Populated by /task-work]
