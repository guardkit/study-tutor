---
complexity: 4
consumer_context:
- consumes: SourceTypedCorpus
  driver: pydantic
  format_note: Consumes SourceType enum to query primary-text presence by source_type
    filter
  framework: Pydantic v2 (BaseModel)
  task: TASK-PRV-001
dependencies:
- TASK-PRV-001
estimated_minutes: 50
feature_id: FEAT-PRV4
id: TASK-PRV-003
implementation_mode: task-work
parent_review: TASK-REV-PRV4
priority: high
related_features:
- FEAT-PH1-004
- FEAT-PH1-002
- FEAT-PH1-003
status: completed
updated: '2026-04-30T22:20:00Z'
tags:
- feat-ph1-004
- retrieval
- decision
- ao3-bypass
- analysis-mode
task_type: feature
test_results:
  coverage: null
  last_run: null
  status: pending
title: Dynamic retrieval-decision function (R2 + R3)
wave: 2
---

# Task: Dynamic retrieval-decision function (R2 + R3)

## Description

Implement `src/study_tutor/knowledge/retrieval.py:should_retrieve` —
the pre-Player decision function. Encodes the empirical R2 (dynamic
retrieval decision) and R3 (AO3 retrieval bypass) recommendations
from the 23-Apr OpenWebUI session.

## Scope

- Module-level reason-string constants:
  - `REASON_NO_PRIMARY = "analysis_mode:no_primary_text"`
  - `REASON_AO3_ONLY = "ao3_only:training_first"`
  - `REASON_EMBEDDER_TIMEOUT = "analysis_mode:embedder_timeout"`
  - `REASON_RETRIEVE_PRIMARY = "retrieve:primary_present"`
  - `REASON_RETRIEVE_MIXED = "retrieve:mixed_ao3"`
- Module-level constant: `EMBEDDER_TIMEOUT_SECONDS = 5.0`
- `RetrievalDecision = NamedTuple("RetrievalDecision", [
  ("retrieve", bool), ("reason", str), ("mode", str)])` —
  `mode` is one of `"retrieve" | "analysis_mode" | "ao3_bypass" |
  "mixed"`
- `has_primary_text(text_name: str) -> bool` — corpus index lookup
- `should_retrieve(text_name: str, focus_aos: set[str]) ->
  RetrievalDecision` with the four-branch decision tree:
  1. `focus_aos == {"AO3"}` → bypass (`REASON_AO3_ONLY`)
  2. `not has_primary_text(text_name)` → AnalysisMode
     (`REASON_NO_PRIMARY`)
  3. `"AO3" in focus_aos and len(focus_aos) > 1` → retrieve mixed
     (`REASON_RETRIEVE_MIXED`, `mode="mixed"`)
  4. Otherwise → retrieve primary (`REASON_RETRIEVE_PRIMARY`)
- Embedder availability probe (used by upstream caller, exposed as
  `embedder_available_within(timeout_s) -> bool` returning True if
  the embedding service responds within the timeout); on timeout,
  the orchestrator forces a `(False, REASON_EMBEDDER_TIMEOUT,
  "analysis_mode")` return regardless of the four-branch outcome.

## Out of Scope

- Source-filtered retrieval and reranker handling (TASK-PRV-004)
- Quote verifier (TASK-PRV-005)
- Coach handover wiring (TASK-PRV-006)

## Acceptance Criteria

- [ ] Branch 1 (AO3-only) returns `(False, REASON_AO3_ONLY,
      "ao3_bypass")` (covers @key-example @smoke @retrieval
      @ao3-bypass scenario)
- [ ] Branch 2 (no primary text in corpus) returns `(False,
      REASON_NO_PRIMARY, "analysis_mode")` (covers @key-example
      @smoke @retrieval @analysis-mode scenario)
- [ ] Branch 3 (mixed AO3 + AO1/AO2) returns `(True,
      REASON_RETRIEVE_MIXED, "mixed")` (covers @edge-case @retrieval
      @ao3 mixed-mode scenario)
- [ ] Branch 4 (primary present, non-AO3-only) returns `(True,
      REASON_RETRIEVE_PRIMARY, "retrieve")` (covers @key-example
      @smoke @retrieval @primary scenario)
- [ ] AO3-only with empty `context_historical/` folder still
      bypasses (covers @edge-case @retrieval @ao3 scenario for
      empty context-historical)
- [ ] Embedder unavailability (sleep > 5s) → `(False,
      REASON_EMBEDDER_TIMEOUT, "analysis_mode")` (covers @edge-case
      @retrieval @resilience scenario)
- [ ] Reason strings are module-level constants (tests assert
      `decision.reason is REASON_AO3_ONLY`, never literal compare)
- [ ] All modified files pass project-configured lint/format checks
      with zero errors

## Test Requirements

- [ ] Parametrised unit test covering all four branches plus the
      embedder-timeout override (5 cases)
- [ ] Unit test: AO3-only with `focus_aos = {"AO3"}` bypasses even
      when primary text exists in corpus
- [ ] Unit test: mixed `focus_aos = {"AO1", "AO2", "AO3"}` returns
      retrieve, mode="mixed"
- [ ] Unit test: empty `focus_aos` set behaves as non-AO3 (defaults
      to retrieve when primary present)
- [ ] Unit test: embedder probe with sleep-stub > 5s triggers
      analysis-mode override
- [ ] Unit test: reason string identity check (constants, not
      literals)

## Seam Tests

The following seam test validates the RetrievalDecision contract
consumed by TASK-PRV-004 and TASK-PRV-006:

```python
"""Seam test: verify should_retrieve returns the RetrievalDecision
contract shape consumed by retrieval and Coach handover."""
import pytest
from study_tutor.knowledge.retrieval import (
    should_retrieve, RetrievalDecision,
    REASON_NO_PRIMARY, REASON_AO3_ONLY,
    REASON_RETRIEVE_PRIMARY, REASON_RETRIEVE_MIXED,
)


@pytest.mark.seam
@pytest.mark.integration_contract("RetrievalDecision")
def test_should_retrieve_returns_named_tuple_contract():
    """Verify the four-branch decision tree returns the
    RetrievalDecision named tuple with module-level reason
    constants.

    Contract: should_retrieve(text_name, focus_aos) → (retrieve,
    reason, mode); reason values are module-level constants.
    Consumers: TASK-PRV-004 (skips retrieval if retrieve=False),
    TASK-PRV-006 (forwards reason into VerifierMetadata).
    """
    # Branch identity assertions — reason values are constants
    decision = should_retrieve("nonexistent_text", {"AO1", "AO2"})
    assert isinstance(decision, RetrievalDecision)
    assert decision.reason is REASON_NO_PRIMARY  # identity, not equality
```

## Implementation Notes

**Why a NamedTuple, not a Pydantic model:** the decision is
returned from a hot-path pre-Player check; tuple unpacking is
zero-cost. Pydantic validation is unnecessary because the function
itself is the source of truth — we never deserialise a
`RetrievalDecision` from JSON.

**Why reason strings are module-level constants:** the @key-example
scenarios assert against literal reason strings; if we ever rename
`"analysis_mode:no_primary_text"`, tests should fail loudly via
identity check on the constant, not silently still match a stale
literal. ASSUM-006 confirmed.

**Why mixed-mode returns retrieve=True with mode="mixed":** the
session metadata records `mode` separately from `retrieve` so the
Coach can apply different scoring posture for AO3 portions of a
mixed-mode response without re-running the decision function.

## Test Execution Log

[Populated by /task-work]