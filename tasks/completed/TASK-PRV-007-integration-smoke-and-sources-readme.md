---
complexity: 3
dependencies:
- TASK-PRV-004
- TASK-PRV-005
- TASK-PRV-006
estimated_minutes: 45
feature_id: FEAT-PRV4
id: TASK-PRV-007
implementation_mode: task-work
parent_review: TASK-REV-PRV4
priority: high
related_features:
- FEAT-PH1-004
status: completed
updated: '2026-04-30T22:20:00Z'
tags:
- feat-ph1-004
- testing
- integration
- documentation
task_type: testing
test_results:
  coverage: null
  last_run: null
  status: pending
title: Integration smoke + sources README update
wave: 5
---

# Task: Integration smoke + sources README update

## Description

End-to-end integration test exercising the full retrieval → verify
→ Coach pipeline against a small fixture corpus, plus an updated
`domains/gcse-english/sources/README.md` reflecting the four-folder
source-typed layout.

## Scope

- New test file `tests/integration/test_rag_end_to_end.py`
  exercising:
  1. **Retrieve-and-verify path:** Macbeth session, AO1+AO2, with
     a fixture primary-text + study-guide corpus → retrieval
     returns primary-first chunks; Player produces a response with
     a Shakespeare verbatim quote and a study-guide phrase →
     verifier annotates the primary quote with citation, rewrites
     the secondary phrase with attribution
  2. **AnalysisMode skip path:** Inspector Calls session (no
     primary text in fixture corpus) → `should_retrieve` returns
     False with `analysis_mode:no_primary_text`; verifier still
     runs but quote-fidelity is suppressed in metadata
  3. **AO3 bypass path:** Macbeth session with `focus_aos =
     {"AO3"}` only → `should_retrieve` returns False with
     `ao3_only:training_first`
- Update `domains/gcse-english/sources/README.md` to:
  - Replace the Phase 0 "place all PDFs in any subdirectory" guidance
    with the four-folder layout (`primary_text/`,
    `secondary_study_guide/`, `secondary_critical/`,
    `context_historical/`)
  - Document Standard Ebooks as the canonical primary-text source
    (per R4 / ASSUM-004)
  - Document the AQA refusal mechanism + in-copyright deny-list
  - Reference TASK-PRV-002's loader behaviour
  - Preserve the §4 "What gets published, what stays private" table
    and §5 troubleshooting

## Out of Scope

- Coach's `score_rubric.quote_fidelity` mapping (TASK-DTL-002 — out
  of scope here, in scope there)
- New BDD scenarios — this task validates existing scenarios end
  to end
- `agentic-dataset-factory` ingestion-pipeline integration
  (continues to live in the separate repo per the readme split)

## Acceptance Criteria

- [ ] `tests/integration/test_rag_end_to_end.py` runs in <30s
      against the fixture corpus
- [ ] Retrieve-and-verify path produces the expected
      `VerifierMetadata` shape (one `PrimaryMatch`, one
      `SecondaryRewrite`)
- [ ] AnalysisMode path produces an empty retrieve list and
      `retrieval_skipped_reason="analysis_mode:no_primary_text"` in
      metadata
- [ ] AO3-bypass path produces an empty retrieve list and
      `retrieval_skipped_reason="ao3_only:training_first"` in
      metadata
- [ ] `domains/gcse-english/sources/README.md` reflects the
      four-folder layout and Standard Ebooks as canonical
- [ ] README still says "nothing in this directory is tracked by
      git" — preservation of the public/private boundary
- [ ] Smoke test fixture is small (~3 chunks per text — enough to
      exercise paths, fast to load)
- [ ] All modified files pass project-configured lint/format checks
      with zero errors

## Test Requirements

- [ ] Integration test: retrieve-and-verify path
- [ ] Integration test: AnalysisMode skip path
- [ ] Integration test: AO3-bypass path
- [ ] README markdown lints clean (no broken links to phase-1-scope
      or empirical findings docs)

## Implementation Notes

**Why a small fixture corpus, not the real Standard Ebooks files:**
the integration test must run in CI in <30s and must not depend on
external downloads. A 3-chunks-per-text fixture is enough to
exercise the precedence ordering, AnalysisMode, and AO3 bypass.

**Why the README update lives in this task and not TASK-PRV-002:**
the README is the user-facing onboarding doc; updating it after the
loader is verified end-to-end (Wave 5) ensures the doc matches
shipped behaviour, not aspirational behaviour.

**Why three integration paths and not more:** the four-folder
loader, four-branch decision, and five-precedence verifier all have
their own focused unit tests in their own tasks. Integration is
about wiring, not exhaustive permutation; three paths cover the
three production-relevant flows (retrieve, AnalysisMode, AO3).

## Test Execution Log

[Populated by /task-work]