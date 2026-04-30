# Feature: Primary-Text RAG and Source-Typed Quote Verifier

**Feature ID:** FEAT-PH1-004
**Phase:** Phase 1
**Parent review:** [TASK-REV-PRV4](../../in_review/TASK-REV-PRV4-plan-primary-text-rag-and-quote-verifier.md)
**Spec:** [features/primary-text-rag-and-quote-verifier/](../../../features/primary-text-rag-and-quote-verifier/)
**Approach:** Option A — Three-module split with citation-aware chunker variant
**Stack:** python (Python 3.14, Pydantic v2, ChromaDB, BAAI/bge-reranker-v2-m3 baseline)

---

## Why this feature

The 23 April OpenWebUI empirical session showed that **always-on
retrieval against a partial corpus actively degrades a well-trained
model below its no-retrieval baseline**. For texts the fine-tune has
memorised (Shakespeare), direct generation beats retrieval; for
in-copyright modern texts (An Inspector Calls, Blood Brothers) the
school-supplied PDFs are the only legitimate route.

This feature operationalises the four R-numbered recommendations from
that session:

- **R1** — source-typed quote verifier with primary/secondary/fuzzy/no-match
  taxonomy
- **R2** — dynamic retrieval decision (skip when no primary text in corpus)
- **R3** — AO3 retrieval bypass (training-data-first for context)
- **R4** — Standard Ebooks as the canonical primary-text source

It is the load-bearing dependency for the Coach's `quote_fidelity`
rubric criterion in **TASK-DTL-002 / FEAT-PH1-003**.

---

## Subtasks

| ID | Name | Wave | Mode | Complexity | Dependencies |
|---|---|---|---|---|---|
| TASK-PRV-001 | Citation anchor & source-type Pydantic models | 1 | direct | 2 | — |
| TASK-PRV-002 | Source-typed corpus loader | 2 | task-work | 5 | PRV-001 |
| TASK-PRV-003 | Retrieval-decision function (R2 + R3) | 2 | task-work | 4 | PRV-001 |
| TASK-PRV-004 | Source-filtered retrieval with reranker degradation | 3 | task-work | 5 | PRV-002, PRV-003 |
| TASK-PRV-005 | Source-typed quote verifier (R1) | 3 | task-work | 6 | PRV-002 |
| TASK-PRV-006 | Coach handover seam (`VerifierMetadata` contract) | 4 | task-work | 4 | PRV-005 |
| TASK-PRV-007 | Integration smoke + sources README update | 5 | task-work | 3 | PRV-004, PRV-005, PRV-006 |

**Total:** 7 subtasks · **5 waves** · 5–7h sequential / ~3–4h elapsed

---

## Execution strategy

- **Wave 1:** TASK-PRV-001 alone (Pydantic models all downstream tasks consume)
- **Wave 2 (parallel-safe):** TASK-PRV-002 + TASK-PRV-003 (different modules)
- **Wave 3 (parallel-safe):** TASK-PRV-004 + TASK-PRV-005 (different modules; verifier does not depend on retrieval)
- **Wave 4:** TASK-PRV-006 alone (wires verifier output into Coach's `score_rubric`)
- **Wave 5:** TASK-PRV-007 alone (end-to-end smoke + sources README)

Conductor parallelism is **recommended** for Waves 2 and 3.

---

## Pre-implementation sign-offs

All five low-confidence assumptions and four medium-confidence
assumptions have mechanism-level resolutions in the review report.
See [.guardkit/reviews/TASK-REV-PRV4-review-report.md §3](../../../.guardkit/reviews/TASK-REV-PRV4-review-report.md).

| Assumption | Resolution |
|---|---|
| ASSUM-008 AQA refusal | Filename-pattern regex + deny-list defence-in-depth |
| ASSUM-009 In-copyright deny-list | Explicit `INCOPYRIGHT_TITLES` constant; case-insensitive |
| ASSUM-010 Secondary attribution | `SECONDARY_ATTRIBUTION_TEMPLATES` tuple; deterministic pick |
| ASSUM-011 Long-passage threshold | >30 words → ≤12-word densest analytical span |
| ASSUM-013 Embedder unavailability | 5s per-call timeout → AnalysisMode |
| ASSUM-005 Citation anchors | `play` (act/scene/line) vs `novel` (chapter/paragraph) Pydantic union |
| ASSUM-006 Skip-reason strings | `analysis_mode:no_primary_text`, `ao3_only:training_first`, `analysis_mode:embedder_timeout` |
| ASSUM-007 AO3 mixed-mode | AO3-only → bypass; mixed → retrieve for non-AO3 |
| ASSUM-012 Normalisation | Symmetric whitespace/punctuation/quote/case normalisation |
| ASSUM-015 Cross-text mismatch | Paraphrase rewrite + softened certainty |

---

## Next steps

1. Read [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) — load-bearing data-flow, integration contracts, and §4 cross-task contracts.
2. Start with Wave 1: `/task-work TASK-PRV-001`
3. Run Wave 2 in parallel (Conductor recommended): `TASK-PRV-002`, `TASK-PRV-003`
4. Run Wave 3 in parallel: `TASK-PRV-004`, `TASK-PRV-005`
5. Wave 4: `TASK-PRV-006` (Coach handover wiring)
6. Wave 5: `TASK-PRV-007` (integration smoke)

Or, for autonomous build: `/feature-build FEAT-PRV4`
