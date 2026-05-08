---
id: TASK-RAG-003
title: "End-to-end RAG smoke session against real Macbeth corpus"
task_type: testing
feature_id: FEAT-PRV4
implementation_mode: direct
complexity: 4
estimated_minutes: 90
status: backlog
priority: high
created: 2026-05-08T00:00:00Z
updated: 2026-05-08T00:00:00Z
dependencies:
  - TASK-RAG-001
  - TASK-RAG-002
related:
  - tests/integration/test_rag_end_to_end.py
  - tests/integration/test_mcp_lca_smoke.py
  - tests/smoke/
  - docs/talks/ddd-southwest-demo-strategy.md
tags:
  - rag
  - smoke
  - demo-prep
  - feat-prv4
  - phase-1
  - ddd-southwest
---

# Task: End-to-end RAG smoke session against real Macbeth corpus

## Description

Validates that the wiring delivered by TASK-RAG-001 (ingestion) +
TASK-RAG-002 (CLI provider + handover closure) actually grounds a live
`tutor_turn` against a real Standard Ebooks Macbeth corpus and surfaces
the demo signals the DDD Southwest 16 May talk depends on:

- `event=orchestrator_turn_completed reason=retrieve:primary_present
  retrieval_mode=rerank attempts=N`
- `event=orchestrator_turn_completed reason=ao3_only:training_first
  retrieval_skipped=True` on an AO3-only turn
- `VerifierMetadata.primary_matches` populated with annotated Act/Scene/Line
  citations when the Player quotes Macbeth verbatim.

This is the **Phase 1 G7 close-out gate** for FEAT-PRV4 — once this
passes, the RAG stack moves from "structurally complete (PRV-007 fake
fixture)" to "live-validated against a real corpus and a real Player",
and the demo strategy doc can mark Demo 3 as covering selective
retrieval, not just Player–Coach.

## Scope

### 1. Operator runbook (`docs/state/rag-runtime-validation.md`)

A four-paragraph Phase-1-validation doc that the operator (Rich) can
follow to bring the RAG runtime up cleanly:

1. **Ingest** — `uv sync --extra rag`, drop Macbeth from Standard Ebooks
   into `domains/gcse-english/sources/primary_text/`, run
   `python scripts/ingest_corpus.py`, expect NDJSON summary with
   `chunks_created > 0` and `per_text_count text_name=macbeth`.
2. **Boot** — `study-tutor serve` with
   `STUDY_TUTOR_CHROMA_DIR=./chroma/gcse-english/`, confirm the boot smoke
   logs include `event=collection_provider_wired
   collection=gcse-english primary_texts=[macbeth ...]`.
3. **Drive a turn** — issue a `tutor_start_session` MCP call for
   `student_id=lilymay` against a planned Macbeth topic; then
   `tutor_turn` with a learner message that invites a quotation
   ("Show me where Lady Macbeth questions Macbeth's manhood").
4. **Verify the signals** — confirm in the log pane:
   `reason=retrieve:primary_present`, `retrieval_mode=rerank` (or
   `no_rerank`), `quote_fidelity` score in the Coach verdict,
   `primary_matches` citations in turn metadata.

### 2. Live integration smoke (`tests/smoke/test_rag_runtime_smoke.py`)

A pytest module marked `@pytest.mark.smoke` and `@pytest.mark.requires_chroma`
that runs end-to-end against a real (small) Chroma persist dir baked from a
public-domain Macbeth excerpt fixture:

- **Setup:** the fixture seeds a temp `./chroma/<test>/` from
  `tests/fixtures/macbeth_excerpt.txt` (3-4 short scenes, public domain) by
  invoking `scripts/ingest_corpus.py` as a subprocess.
- **Boot:** import the CLI's `_build_orchestrator_factory` and the RAG
  provider builder; run them against the temp persist dir.
- **Drive a turn:** stub out only the LLM Player and Coach (use the
  existing `LLMPlayerAdapter` test doubles); leave retrieval and verifier
  REAL.
- **Assert:** the closing TurnResult contains `verifier_metadata` with at
  least one `primary_matches` entry whose `citation_anchor` is a
  `PlayCitationAnchor`. The structured log line for the turn contains
  `reason=retrieve:primary_present` and a `retrieval_mode` field.
- **AO3 path:** rerun with `focus_aos={"AO3"}`; assert
  `retrieval_skipped_reason="ao3_only:training_first"` and the fake
  Chroma collection's `query` was not called.

This complements (does not replace) the existing
`tests/integration/test_rag_end_to_end.py` which uses a hand-built fake.

### 3. Demo cue card (`docs/talks/rag-demo-cues.md`)

A one-page cue card that Rich can put on the lectern during the talk:

- Three example turns and the expected log-line shape for each.
- The expected `reason=` strings to point at on the screen.
- A fallback path: what to say / show if `chromadb` import fails on
  conference WiFi (the `event=rag_disabled` graceful-degradation log
  line plus a fallback to the canonical "selective retrieval works
  because the model already knows Macbeth" narrative).

### 4. Validation report (`docs/state/rag-runtime-validation.md`)

After the smoke runs green and a manual operator session has been driven,
update the validation doc with:

- The actual log lines captured from the manual session
  (sanitised — no live FalkorDB contents).
- The latency of one round-trip turn including retrieval and reranking.
- A `gate_status` block: `G7_phase_1_close_out: PASS` (or notes on what's
  blocking).

## Acceptance Criteria

- [ ] `tests/smoke/test_rag_runtime_smoke.py` exists and is gated by
      `@pytest.mark.requires_chroma` so CI without the `[rag]` extra
      simply skips.
- [ ] `pytest -m "smoke and requires_chroma" tests/smoke/test_rag_runtime_smoke.py`
      passes locally on the dev box (Mac / GB10) after `uv sync --extra rag`.
- [ ] The smoke test asserts both branches: retrieve-and-verify path
      (primary_text Macbeth, AO1/AO2) AND AO3 bypass path
      (focus_aos={"AO3"}, no retrieval call).
- [ ] `docs/state/rag-runtime-validation.md` exists and contains:
      operator runbook, captured log lines from the manual session,
      latency note, `G7_phase_1_close_out` gate status.
- [ ] `docs/talks/rag-demo-cues.md` exists with three cue-card turns and
      the expected `reason=` strings.
- [ ] A manual operator session has been driven once end-to-end from
      `tutor_start_session` through `tutor_turn` against a freshly-ingested
      Macbeth corpus, with the log lines captured into the validation doc.
- [ ] No regression in the existing `tests/integration/test_rag_end_to_end.py`
      (still passes with the fake Chroma fixture; it is the unit-level
      complement to this smoke test).

## Test Requirements

The smoke test itself is the deliverable. Additional checks:

- **Latency budget:** the smoke test asserts a single end-to-end
  `tutor_turn` (with retrieval + rerank + verify) completes in under 10s
  on a stubbed Player/Coach. Real Player/Coach latency is out of scope
  — we measure only the RAG slice.
- **Idempotency proof:** the smoke test runs `scripts/ingest_corpus.py`
  twice in setup; the second invocation must not change `collection.count()`
  (defence-in-depth on TASK-RAG-001's idempotency AC).
- **Secondary chunk handling:** the fixture includes one
  `secondary_study_guide` chunk; the smoke test verifies that a Player
  response containing a study-guide phrasing is rewritten via the
  `SECONDARY_ATTRIBUTION_TEMPLATES` path (not annotated as a primary
  citation).

## Implementation Notes

- The smoke test should NOT require the BGE reranker — the test stubs
  `set_reranker_factory` to raise `ImportError` so `mode="no_rerank"` is
  exercised, and a separate parametrised case stubs a fake reranker to
  exercise `mode="rerank"`. This keeps CI from needing the 568 MB
  cross-encoder model.
- The fixture Macbeth excerpt MUST be public domain. The clean source is
  Standard Ebooks (CC0) — copy 3-4 short scenes into
  `tests/fixtures/macbeth_excerpt.txt` and credit the source in the
  fixture file header.
- Capture log lines from the manual operator session by configuring the
  CLI's logger to write JSON to a file: `study-tutor serve --log-level DEBUG
  2> /tmp/rag-smoke.log`, then `grep event=orchestrator_turn_completed
  /tmp/rag-smoke.log` to extract the lines for the validation doc.
- The cue card lives in `docs/talks/` alongside the demo strategy doc so
  the talk-prep artefacts cluster.

## Out of scope

- Productionising the validation doc into a CI gate (it's an operator
  artefact, not a CI step — too brittle to gate CI on a real LLM call).
- Performance tuning of the reranker or the chunker (Phase 2).
- Driving a Lilymay-stamped session against the live Synology FalkorDB
  graph from inside the smoke test — graphiti integration is a separate
  cross-cutting concern; this task validates the RAG slice only.

## References

- [tests/integration/test_rag_end_to_end.py](../../tests/integration/test_rag_end_to_end.py) — fake-fixture sibling
- [tests/integration/test_mcp_lca_smoke.py](../../tests/integration/test_mcp_lca_smoke.py) — pattern for serve-bootstrap smoke
- [docs/talks/ddd-southwest-demo-strategy.md](../../docs/talks/ddd-southwest-demo-strategy.md) — Demo 3 signal requirements
- [tasks/completed/TASK-PRV-007-integration-smoke-and-sources-readme.md](../completed/TASK-PRV-007-integration-smoke-and-sources-readme.md)
- [tasks/completed/TASK-GR-DEMO/](../completed/TASK-GR-DEMO/) — sibling Phase-1 close-out gate (Graphiti slice)
