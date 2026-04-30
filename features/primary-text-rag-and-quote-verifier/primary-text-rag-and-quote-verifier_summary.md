# Feature Spec Summary: Primary-Text RAG and Source-Typed Quote Verifier

**Feature ID**: FEAT-PH1-004
**Stack**: python
**Generated**: 2026-04-30
**Scenarios**: 34 total (5 smoke, 0 regression)
**Assumptions**: 15 total (6 high / 4 medium / 5 low confidence)
**Review required**: Yes — 5 low-confidence assumptions need human verification

## Scope

Operationalises FEAT-PH1-004 from `phase-1-scope.md` and the four
recommendations (R1–R4) from the 23-Apr OpenWebUI empirical findings.
Covers three modules: a source-typed corpus loader, a dynamic
retrieval-decision function, and a quote verifier that distinguishes
primary-text matches, secondary-source rewrites, fuzzy corrections,
and no-match strips. The verifier is the seam consumed by the Coach
rubric's `quote_fidelity` criterion (FEAT-PH1-003 / TASK-DTL-002).

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 8 |
| Boundary conditions (@boundary) | 5 |
| Negative cases (@negative) | 6 |
| Edge cases (@edge-case) | 15 (9 from initial + 6 from expansion) |
| Smoke (@smoke) | 5 |

The 5 smoke scenarios cover the three retrieval-decision branches
(retrieve / Analysis Mode / AO3 bypass) and the two load-bearing
verifier outcomes (primary-text annotation, secondary-source rewrite).

## Behavioural Surfaces Specified

- **Source-typed corpus**: four-folder layout (`primary_text`,
  `secondary_study_guide`, `secondary_critical`, `context_historical`)
  with directory-driven source-type inference at ingestion.
- **Dynamic retrieval decision (R2)**: pre-turn check returning
  `(retrieve, reason)` based on whether the session's text has a
  primary edition in the corpus and on the focus AOs.
- **AO3 retrieval bypass (R3)**: AO3-only turns answer from training;
  mixed AO3+AO1/AO2 turns retrieve for the non-AO3 evidence.
- **Source-typed quote verification (R1)**: four match types —
  primary annotated, secondary rewritten, fuzzy corrected, no-match
  stripped.
- **Copyright safety**: AQA assessment material refused at ingestion
  and excluded at retrieval; in-copyright modern texts refused from
  the primary-text folder.
- **Defence-in-depth invariants**: secondary phrasing never returned
  as the author's words; cross-text mismatches never annotated against
  the wrong text's citation; long passages reduced to short embedded
  quotations.
- **Resilience**: corpus loader survives corrupted files; retrieval
  proceeds without a reranker when the reranker is unavailable;
  embedder unavailability falls back to Analysis Mode.
- **Coach handover contract**: the verifier-rewritten response (not
  the original) is what the Coach evaluates; verifier metadata
  accompanies the response so the Coach can score quote fidelity.

## Open Assumptions (low confidence)

These five must be verified before TASK-DTL-002 / FEAT-PH1-004 build
work begins:

- **ASSUM-008** — AQA-material refusal mechanism (filename pattern vs
  manual curation vs both).
- **ASSUM-009** — In-copyright deny-list contents and enforcement
  point (loader-side check vs human curation alone).
- **ASSUM-010** — Secondary-source rewrite attribution phrasing (must
  be agreed with the GOAL.md tone before code lands).
- **ASSUM-011** — Long-passage shortening threshold (30 words → ≤12
  proposed; needs Rich/teacher review against §6.1 of GOAL.md).
- **ASSUM-013** — Embedding-service unavailability detection
  (5-second proposal needs validation against actual nomic-embed
  latency on GB10).

Four medium-confidence assumptions (ASSUM-005, ASSUM-006, ASSUM-007,
ASSUM-012, ASSUM-015) are Coach-review territory — present them
during plan review and convert to high-confidence once decisions
land.

## Cross-Feature Dependencies

This feature is consumed by:

- **FEAT-PH1-003 / TASK-DTL-002** — the Coach's `quote_fidelity`
  rubric criterion calls into the quote verifier. The verifier-
  rewritten response is the version the Coach scores
  (Group E, Coach-handover scenario).

This feature consumes:

- **FEAT-PH1-001** — the student model's `Text` entity tells the
  retrieval-decision function which primary text the session is on.
- **FEAT-PH1-002** — the planner's `focus_aos` tells the retrieval-
  decision function whether AO3 is in play.

## Excluded From This Spec (per `phase-1-scope.md` §Out of scope)

- User-supplied in-copyright texts cached in a per-student Graphiti
  `Text` episode (Phase 2).
- Embedding-based pre-generation grounding (Phase B; Phase 1 stays
  post-hoc verification only).
- Reranker tuning beyond the proven `BAAI/bge-reranker-v2-m3`
  baseline.

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "Primary-Text RAG and Source-Typed Quote Verifier" \
      --context features/primary-text-rag-and-quote-verifier/primary-text-rag-and-quote-verifier_summary.md

`/feature-plan` Step 11 (`bdd-linker`) will append `@task:TASK-XXX`
tags to each scenario as task slices are generated. Recommended
slicing follows the three-module structure of FEAT-PH1-004:

- **Slice 1: corpus loader** — Group A8, B4, B5, C1, C2, D5, D6
  (8 scenarios covering ingestion, source-type inference, copyright
  refusals, resilience, and security).
- **Slice 2: retrieval-decision + source-filtered retrieval** —
  Group A1, A2, A3, B3, C3, C6, D1, D7, D8, D9, E4 (11 scenarios
  covering the three decision branches, Top-K boundary, AQA
  exclusion at retrieval, mixed-mode, and resilience without
  reranker / embedder).
- **Slice 3: quote verifier** — Group A4, A5, A6, A7, B1, B2, C4,
  C5, D2, D3, D4, E1, E2, E3, E5, E6 (16 scenarios covering the
  four match types, span-length and edit-distance boundaries,
  safety invariants, integration with Coach handover, and citation
  shapes).

Total 34 scenarios → 3 slices, with Slice 3 the largest (verifier is
the load-bearing seam consumed by FEAT-PH1-003).
