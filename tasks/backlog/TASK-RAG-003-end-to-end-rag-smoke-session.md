---
id: TASK-RAG-003
title: "End-to-end RAG smoke session against real two-path corpus (primary + secondary)"
task_type: testing
feature_id: FEAT-PRV4
parent_review: TASK-REV-RAG4
implementation_mode: task-work
complexity: 5
estimated_minutes: 180
status: backlog
priority: high
created: 2026-05-08T00:00:00Z
updated: 2026-05-09T00:00:00Z
spec_revision: 2  # rewritten 2026-05-09 per TASK-REV-RAG4 ratification + post-CC1 reality
dependencies:
  - TASK-RAG-001  # ingestion script (completed)
  - TASK-RAG-002  # CLI provider + handover closure (completed)
  - TASK-RAG-CC1  # course correction (completed; .md ingestion + deny-list removal)
  - TASK-PRV-008  # citation-anchor MULTILINE fix (in progress / uncommitted)
related:
  - tests/integration/test_rag_end_to_end.py
  - tests/integration/test_mcp_lca_smoke.py
  - tests/smoke/
  - docs/talks/ddd-southwest-demo-strategy.md
  - .guardkit/reviews/TASK-REV-RAG4-review-report.md
  - scripts/reconstruct_corpus_from_adf.py  # one-shot bridge used during CC1 smoke
tags:
  - rag
  - smoke
  - demo-prep
  - feat-prv4
  - phase-1
  - ddd-southwest
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: End-to-end RAG smoke session against a real two-path corpus

## Provenance

This is a **rewrite** of the original TASK-RAG-003 spec. The previous version
fixtured off the Standard Ebooks Macbeth `.txt` only and asserted on
primary-text retrieval signals only. The canonical course-correction review
([REVIEW-RAG-COURSE-CORRECT-docling-integration.md](../../docs/reviews/REVIEW-RAG-COURSE-CORRECT-docling-integration.md))
explicitly invalidated that scope:

> The current TASK-RAG-003 is tightly coupled to the "Standard Ebooks Macbeth
> only" corpus … Do not implement TASK-RAG-003 as currently specced. Rewrite
> the spec after Changes 1 and 2 land, then implement.

[TASK-REV-RAG4](../../tasks/completed/TASK-REV-RAG4-course-correct-rag-docling-integration.md)
ratified that direction. CC1 has now landed and a real two-path corpus exists
on the dev box (Macbeth primary + 6 Mr Bruff secondary `.md` files
reconstructed via [scripts/reconstruct_corpus_from_adf.py](../../scripts/reconstruct_corpus_from_adf.py)).
PRV-008 fixed the `re.MULTILINE` regex bug that caused all primary chunks to
ship without citation anchors. The corpus is now ready to support a
two-retrieval-path smoke.

## Description

Validate that the wiring delivered by TASK-RAG-001 (ingestion) + TASK-RAG-002
(CLI provider + handover closure) grounds a live `tutor_turn` against a real
**two-text** corpus and surfaces the demo signals the DDD Southwest 16 May
talk depends on:

- **Primary path:** `event=orchestrator_turn_completed reason=retrieve:primary_present
  retrieval_mode=rerank attempts=N`, with `VerifierMetadata.primary_matches`
  populated and citation anchors resolved (Act/Scene/Line for plays,
  Chapter/Paragraph for novels).
- **Secondary path:** secondary chunks retrieved alongside primary, no
  citation anchors (anchor=None on `SECONDARY_STUDY_GUIDE` chunks),
  content available for grounding the Player's response.
- **AO3 bypass:** `event=orchestrator_turn_completed reason=ao3_only:training_first
  retrieval_skipped=True` on an AO3-only turn (zero retrieval calls).

This is the **Phase 1 G7 close-out gate** for FEAT-PRV4 — once this passes,
the RAG stack moves from "structurally complete (PRV-007 fake fixture)" to
"live-validated against a real corpus and a real Player," and the demo
strategy doc can mark Demo 3 as covering selective retrieval across primary
and secondary content.

## Why two-path matters

The selective-retrieval thesis is the fine-tune knows the canon (Macbeth) +
the RAG fills the gaps (Mr Bruff commentary, scanned set texts). A
Macbeth-only smoke can't show the gap-filling half. A play-only smoke can't
exercise the "secondary chunk retrieved without an anchor" code path that
distinguishes commentary from primary text in the Coach handover.

The rewritten spec covers both paths so the demo cue cards can show **the
same retrieval engine** producing structurally different `primary_matches`
behaviour depending on what was retrieved — primary chunks carry annotated
citations; secondary chunks carry source attribution but no anchor. That's
the visible artefact of selective retrieval doing the right thing.

## Scope

### 1. Operator runbook (`docs/state/rag-runtime-validation.md`)

A Phase-1-validation doc the operator (Rich) follows to bring the RAG runtime
up cleanly. Six steps now (was four):

1. **Process source PDFs through docling** (operator, on GB10) — for each
   in-copyright set text the operator legally owns:
   - Standard mode for digital PDFs (Mr Bruff guides, Standard Ebooks `.txt`
     already works without docling)
   - VLM mode for scanned paperbacks (Inspector Calls scanned via HP
     OfficeJet, etc.)
   - Reference (do not transcribe) the working invocation in
     `agentic-dataset-factory/ingestion/docling_processor.py`
   - Output `.md` files into the appropriate source-type subfolder:
     - Plays / novels (whole works) → `primary_text/`
     - Mr Bruff guides, study guides → `secondary_study_guide/`
     - Scholarly essays → `secondary_critical/`
     - Historical context → `context_historical/`
2. **Ingest** — `uv sync --extra rag`, ensure llama-swap is reachable on
   `localhost:9000` (or set `LLM_EMBEDDINGS_BASE_URL`), then
   `python scripts/ingest_corpus.py`. Expected NDJSON summary:
   `chunks_created` ≥ a few hundred, `refusals=0`,
   `per_text_count` lines for both primary and secondary texts.
3. **Verify ingestion** — `python -c` snippet (provided in the runbook) that
   queries the persist dir and asserts: ≥1 `PRIMARY_TEXT` chunk has a
   `PlayCitationAnchor` (proves PRV-008 fix is live); ≥1
   `SECONDARY_STUDY_GUIDE` chunk has `citation_anchor=None` (correct for
   secondary content).
4. **Boot** — `study-tutor serve` with appropriate env vars; confirm boot
   smoke logs include `event=collection_provider_wired
   collection=gcse-english-v1 primary_texts=[macbeth, ...]`.
5. **Drive a turn** — `tutor_start_session` for `student_id=lilymay` against
   a planned topic; then `tutor_turn` with three messages:
   - Primary-quoting: "Show me where Lady Macbeth questions Macbeth's
     manhood" → expect `reason=retrieve:primary_present`, `primary_matches`
     populated, anchors present.
   - Secondary-leaning: "What does Mr Bruff say about Macbeth's
     hallucinations as a sign of guilt?" → expect
     `reason=retrieve:primary_present` (secondary chunks retrieved alongside
     primary), `primary_matches` may be empty or populated depending on
     Player's response, secondary chunks visible in retrieval log.
   - AO3-only: "Compare Macbeth's ambition to Lady Macbeth's" with
     `focus_aos={"AO3"}` → expect `reason=ao3_only:training_first`,
     `retrieval_skipped=True`, no Chroma `query` call.
6. **Verify the signals** — confirm in the log pane: all three `reason=`
   strings, `quote_fidelity` score in the Coach verdict for the
   primary-quoting turn, `primary_matches` citations in turn metadata.

### 2. Live integration smoke (`tests/smoke/test_rag_runtime_smoke.py`)

A pytest module marked `@pytest.mark.smoke` and `@pytest.mark.requires_chroma`
that runs end-to-end against a real (small) Chroma persist dir baked from
**two** public-domain fixtures:

- **Setup:** the fixture seeds a temp `<tmp_path>/chroma/` from
  `tests/fixtures/macbeth_excerpt.txt` (3-4 short scenes, public domain via
  Standard Ebooks CC0) AND
  `tests/fixtures/macbeth_study_notes_excerpt.md` (a paragraph of
  commentary-style prose written for the test, not derived from in-copyright
  Mr Bruff content) by invoking `scripts/ingest_corpus.py` as a subprocess.
  - Note: the smoke fixture must be CI-safe (public domain or test-original).
    The reconstructed Mr Bruff files in `domains/.../secondary_study_guide/`
    are operator-only artefacts and must NOT be checked in or used as test
    fixtures.
- **Embedding**: smoke stubs the embedding function with a deterministic
  hash-based vector (no llama-swap dependency on CI). The runbook (§1) is
  the path that exercises the real llama-swap embedding pipeline.
- **Boot:** import the CLI's `_build_orchestrator_factory` and the RAG
  provider builder; run them against the temp persist dir.
- **Drive a turn:** stub out only the LLM Player and Coach (use the existing
  `LLMPlayerAdapter` test doubles); leave retrieval and verifier REAL.
- **Assert (primary path):** the closing TurnResult contains
  `verifier_metadata` with at least one `primary_matches` entry whose
  `citation_anchor` is a `PlayCitationAnchor` with all three of `act`,
  `scene`, `line` populated. The structured log line for the turn contains
  `reason=retrieve:primary_present` and a `retrieval_mode` field.
- **Assert (secondary path):** when the Player response includes a phrase
  that only appears in the secondary fixture, the verifier's
  `secondary_attribution` (or equivalent — match TASK-PRV-005's actual
  surface) is set; **no** `primary_matches` entry is incorrectly annotated
  with a primary citation for the secondary phrase.
- **Assert (AO3 bypass):** rerun with `focus_aos={"AO3"}`; assert
  `retrieval_skipped_reason="ao3_only:training_first"` and the Chroma
  collection's `query` was not called.
- **Assert (no anchor on secondary):** spot-check that
  `SECONDARY_STUDY_GUIDE` chunks ingested by the test have
  `citation_anchor=None` after `chunk_json` round-trip — confirms the
  schema-translation contract.

This complements (does not replace) the existing
`tests/integration/test_rag_end_to_end.py` which uses a hand-built fake.

### 3. Demo cue card (`docs/talks/rag-demo-cues.md`)

A one-page cue card Rich puts on the lectern during the talk:

- **Three example turns** mapped to the three retrieval paths above
  (primary-quoting, secondary-leaning, AO3-only). For each: the learner
  prompt, the expected `reason=` string, the expected `primary_matches`
  shape, the talking point.
- **The "selective retrieval" payoff slide narrative**: "Same retrieval
  engine. Different result depending on AO focus and whether the Player's
  response triggers primary or secondary grounding. The fine-tune carries
  the canon; RAG fills the gaps."
- **A fallback path**: what to say / show if `chromadb` import fails on
  conference WiFi (the `event=rag_disabled` graceful-degradation log line +
  fallback to "selective retrieval works because the model already knows
  Macbeth — RAG would augment with Mr Bruff commentary if available").

### 4. Validation report (`docs/state/rag-runtime-validation.md`)

After the smoke runs green and a manual operator session has been driven,
update the validation doc with:

- The actual log lines captured from the manual session (sanitised — no
  live FalkorDB contents).
- Per-turn timing: ingestion duration, end-to-end `tutor_turn` latency
  (with retrieval + rerank + verify), retrieval-only latency.
- A `gate_status` block: `G7_phase_1_close_out: PASS` (or notes on what's
  blocking).
- The corpus state at validation time: `text_name`s ingested, source-type
  distribution, citation-anchor coverage rate (was 0% pre-PRV-008, expect
  ≥90% for plays with front matter post-fix).

## Acceptance Criteria

- [ ] `tests/smoke/test_rag_runtime_smoke.py` exists, gated by
      `@pytest.mark.requires_chroma` so CI without the `[rag]` extra simply
      skips. Embedding function is stubbed (no llama-swap requirement).
- [ ] `pytest -m "smoke and requires_chroma" tests/smoke/test_rag_runtime_smoke.py`
      passes locally on the dev box (Mac / GB10) after `uv sync --extra rag`.
- [ ] The smoke test asserts **all three** branches:
      - Primary-quoting (primary_text, AO1/AO2) — `primary_matches` with
        `PlayCitationAnchor`, `reason=retrieve:primary_present`.
      - Secondary-leaning — secondary chunk retrieved, secondary
        attribution path exercised, no false primary annotation.
      - AO3 bypass (focus_aos={"AO3"}) — no retrieval call,
        `reason=ao3_only:training_first`.
- [ ] The smoke test asserts that `SECONDARY_STUDY_GUIDE` chunks
      ingested into Chroma round-trip through `chunk_json` with
      `citation_anchor=None` (confirms post-CC1 `.md` ingestion contract).
- [ ] `docs/state/rag-runtime-validation.md` exists and contains:
      operator runbook (six steps including docling), captured log lines
      from the manual session, latency notes, `G7_phase_1_close_out` gate
      status, citation-anchor coverage rate.
- [ ] `docs/talks/rag-demo-cues.md` exists with three cue-card turns
      (primary, secondary, AO3-only) and the expected `reason=` strings
      for each.
- [ ] A manual operator session has been driven once end-to-end from
      `tutor_start_session` through `tutor_turn` against a freshly-ingested
      corpus that includes BOTH primary text (Macbeth at minimum) AND
      secondary content (≥1 Mr Bruff guide). Log lines captured into the
      validation doc.
- [ ] No regression in the existing
      `tests/integration/test_rag_end_to_end.py` (still passes with the
      fake Chroma fixture; it is the unit-level complement to this smoke).

## Test Requirements

The smoke test itself is the deliverable. Additional checks:

- **Latency budget:** the smoke test asserts a single end-to-end
  `tutor_turn` (with retrieval + rerank + verify) completes in under 10s
  on a stubbed Player/Coach. Real Player/Coach latency is out of scope —
  we measure only the RAG slice.
- **Idempotency proof:** the smoke test runs `scripts/ingest_corpus.py`
  twice in setup; the second invocation must not change `collection.count()`
  (defence-in-depth on TASK-RAG-001's idempotency AC).
- **Two-path retrieval verification:** at least one assertion checks that
  a single `tutor_turn` retrieves chunks from both `primary_text/` and
  `secondary_study_guide/` (not necessarily the SAME turn for the primary
  vs secondary assertions — they can be separate turns within the same
  test function or parametrised cases).
- **Citation-anchor regression guard:** at least one primary chunk
  retrieved through the smoke must have a fully-populated
  `PlayCitationAnchor` (act, scene, line). This catches any regression of
  PRV-008.

## Implementation Notes

- The smoke test should NOT require the BGE reranker — stub
  `set_reranker_factory` to raise `ImportError` so `mode="no_rerank"` is
  exercised, and a separate parametrised case stubs a fake reranker to
  exercise `mode="rerank"`. This keeps CI from needing the 568 MB
  cross-encoder model.
- The Macbeth fixture excerpt MUST be public domain (Standard Ebooks CC0).
  Copy 3-4 short scenes into `tests/fixtures/macbeth_excerpt.txt` and
  credit the source in the fixture file header.
- The secondary fixture MUST be test-original (not derived from
  in-copyright sources). Write 1-2 paragraphs of commentary-style prose
  about Macbeth's themes for `tests/fixtures/macbeth_study_notes_excerpt.md`.
  Include a header / metadata block to prove provenance ("Original
  test-only commentary, not derived from any commercial study guide").
- Capture log lines from the manual operator session by configuring the
  CLI's logger to write JSON to a file: `study-tutor serve --log-level DEBUG
  2> /tmp/rag-smoke.log`, then `grep event=orchestrator_turn_completed
  /tmp/rag-smoke.log` to extract the lines for the validation doc.
- The cue card lives in `docs/talks/` alongside the demo strategy doc so
  the talk-prep artefacts cluster.
- The reconstructed Mr Bruff `.md` files in
  `domains/gcse-english/sources/secondary_study_guide/` are an operator
  artefact (in-copyright; gitignored). They are useful for the **manual
  operator session** but MUST NOT be referenced from the smoke test code
  or checked in.

## Out of scope

- **Power and Conflict poetry anthology ingestion.** The current schema
  has `PlayCitationAnchor` (Act/Scene/Line) and `NovelCitationAnchor`
  (Chapter/Paragraph) but no `PoetryCitationAnchor`. Power and Conflict
  poems can be dropped into `primary_text/` and they'll be retrievable,
  but every chunk will land with `citation_anchor=None`. Add a
  `PoetryCitationAnchor` (with `poem_title` + `line`) and corresponding
  inferer as a separate task. Filed as TASK-PRV-009 (poetry-anchor
  follow-up).
- **`.md` in repo `.gitignore`.** CC1 added `.md` to the example block in
  `CONTRIBUTING-CORPUS.md` but did not propagate to the actual `.gitignore`
  at repo root. The reconstructed Mr Bruff files currently show as
  "Untracked" instead of being ignored. Small follow-up — file as
  TASK-RAG-CC2 (gitignore alignment).
- **BDD step-definition gaps.** Pre-existing condition surfaced during
  PRV-008 verification: 124 unique `StepDefinitionNotFoundError` cases in
  `features/primary-text-rag-and-quote-verifier/`. Scenarios in the
  `.feature` file reference Given/When/Then phrases with no matching
  decorators. Independent of RAG-003 scope; file as a separate
  documentation-debt task.
- **Productionising the validation doc into a CI gate** (it's an operator
  artefact, not a CI step — too brittle to gate CI on a real LLM call).
- **Performance tuning of the reranker or the chunker** (Phase 2).
- **Driving a Lilymay-stamped session against the live Synology FalkorDB
  graph from inside the smoke test** — graphiti integration is a separate
  cross-cutting concern; this task validates the RAG slice only.

## References

- [.guardkit/reviews/TASK-REV-RAG4-review-report.md](../../.guardkit/reviews/TASK-REV-RAG4-review-report.md) — review that ratified the spec rewrite
- [docs/reviews/REVIEW-RAG-COURSE-CORRECT-docling-integration.md](../../docs/reviews/REVIEW-RAG-COURSE-CORRECT-docling-integration.md) — canonical course-correction doc
- [tests/integration/test_rag_end_to_end.py](../../tests/integration/test_rag_end_to_end.py) — fake-fixture sibling
- [tests/integration/test_mcp_lca_smoke.py](../../tests/integration/test_mcp_lca_smoke.py) — pattern for serve-bootstrap smoke
- [docs/talks/ddd-southwest-demo-strategy.md](../../docs/talks/ddd-southwest-demo-strategy.md) — Demo 3 signal requirements
- [tasks/completed/TASK-PRV-007-integration-smoke-and-sources-readme.md](../completed/TASK-PRV-007-integration-smoke-and-sources-readme.md)
- [tasks/completed/TASK-RAG-CC1/TASK-RAG-CC1.md](../completed/TASK-RAG-CC1/TASK-RAG-CC1.md) — course correction (deny-list removed, .md ingestion documented)
- [tasks/completed/TASK-PRV-008/](../completed/TASK-PRV-008/) — citation-anchor MULTILINE fix (prerequisite for primary-path anchor assertions in this smoke)
- [scripts/reconstruct_corpus_from_adf.py](../../scripts/reconstruct_corpus_from_adf.py) — one-shot bridge that produces the operator's Mr Bruff `.md` corpus (not used by the smoke test itself)
