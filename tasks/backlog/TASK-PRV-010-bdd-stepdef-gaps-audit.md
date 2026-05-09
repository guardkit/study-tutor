---
id: TASK-PRV-010
title: "Audit and repair 124 missing BDD step definitions in primary-text-rag-and-quote-verifier"
task_type: bugfix
feature_id: FEAT-PRV4
implementation_mode: task-work
complexity: 6
estimated_minutes: 240
status: backlog
priority: medium
created: 2026-05-09T00:00:00Z
updated: 2026-05-09T00:00:00Z
related:
  - features/primary-text-rag-and-quote-verifier/primary-text-rag-and-quote-verifier.feature
  - features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py
  - features/conftest.py
tags:
  - bdd
  - testing
  - documentation-debt
  - feat-prv4
  - phase-1
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Audit and repair BDD step-definition gaps

## Provenance

Surfaced during TASK-PRV-008 verification (2026-05-09) when running the
full `pytest tests/ features/` suite. 286 test parametrizations failed,
all with the same root cause: 124 unique `StepDefinitionNotFoundError`
cases.

Sample failure:
```
pytest_bdd.exceptions.StepDefinitionNotFoundError:
  Step definition is not found:
  Given "the corpus contains a play and a 19th-century novel as primary texts".
  Line 409 in scenario "A play and a novel coexist in the corpus and produce
  citations in their respective conventions" in the feature
  "features/primary-text-rag-and-quote-verifier/primary-text-rag-and-quote-verifier.feature"
```

This is **pre-existing documentation debt**, not introduced by CC1 or
PRV-008. The BDD scenarios were drafted into the `.feature` file but
never had matching `@given/@when/@then` decorators added to the test
module.

## Description

Audit the gap between scenario phrases in
`primary-text-rag-and-quote-verifier.feature` and step decorators in
`test_primary_text_rag_and_quote_verifier.py`. For each missing phrase,
decide one of three dispositions:

1. **Implement** — the scenario is current and useful; write the missing
   `@given/@when/@then` decorators against the existing production
   surface (loader, retrieval, verifier).
2. **Adapt** — the scenario is current but the phrasing has drifted from
   the implemented surface; update the scenario phrasing in the
   `.feature` file to match an existing step decorator (preserves the
   scenario, fixes the wording).
3. **Remove** — the scenario reflects a behaviour that was never
   implemented or was deliberately scoped out (e.g., references the
   deleted in-copyright deny-list scenarios that CC1 already cleaned up).
   Remove the scenario from the `.feature` file with a comment noting
   the removal rationale.

Disposition 1 (Implement) is the default unless the scenario is clearly
out-of-scope or stale.

## Scope

### Phase 1: Audit (tracking artefact)

Produce `docs/state/bdd-stepdef-audit.md` listing each of the 124 unique
missing phrases with:
- The scenario(s) it appears in
- Recommended disposition (Implement / Adapt / Remove)
- Rationale for the disposition

A two-column table is sufficient. Don't re-litigate every scenario from
scratch — group obvious clusters (e.g., "all scenarios about deny-list
refusal → Remove because CC1 dropped that surface").

### Phase 2: Repair (per-disposition)

- **Implement**: write `@given/@when/@then` decorators against the
  current production surface in
  `test_primary_text_rag_and_quote_verifier.py`. Use existing fixtures
  (`bdd_context`, `corpus_context`) where they fit.
- **Adapt**: edit the `.feature` file's scenario phrasing to match an
  existing decorator. Preserve scenario tags
  (`@TASK-PRV-XXX`, `@security`, etc.).
- **Remove**: delete the scenario from the `.feature` file. Add a brief
  HISTORY note in the audit doc explaining why.

### Phase 3: Verify

- `pytest features/primary-text-rag-and-quote-verifier/ -q` runs to
  completion with **zero** `StepDefinitionNotFoundError`. Tests may
  legitimately FAIL (assertion errors) on production-surface drift — that
  is in-scope for this task only if the test failure points at obviously
  incorrect production behaviour (raise as a separate task), otherwise
  flag in the audit doc.
- Existing passing tests still pass (no regression).

## Acceptance criteria

- [ ] `docs/state/bdd-stepdef-audit.md` exists with all 124 unique
      missing phrases categorised by disposition.
- [ ] Every "Implement" disposition has a matching decorator in
      `test_primary_text_rag_and_quote_verifier.py`.
- [ ] Every "Adapt" disposition has the corresponding scenario phrasing
      updated in the `.feature` file.
- [ ] Every "Remove" disposition has the corresponding scenario deleted
      from the `.feature` file with a HISTORY note in the audit doc.
- [ ] `pytest features/primary-text-rag-and-quote-verifier/` exits with
      zero `StepDefinitionNotFoundError` (assertion failures from real
      production-surface drift are noted, not blocking).
- [ ] No tests that currently pass start failing (regression guard).

## Out of scope

- Fixing assertion-failure tests that point at real production-surface
  drift — file as separate tasks. This task closes the
  *step-definition* gap, not behavioural correctness.
- Adding new BDD scenarios beyond what's already in the `.feature` file.
- Changing the BDD framework, fixture style, or `conftest.py` plumbing.
- Coverage of FEAT-PRV4 outside the
  `primary-text-rag-and-quote-verifier` feature directory.

## Implementation notes

- The bulk of the missing phrases are likely concentrated in a few
  scenario clusters (corpus loading variants, retrieval variants, quote
  verifier variants). Implementing one decorator often unblocks many
  parametrisations — expect non-linear progress.
- Remove dispositions should reference the canonical course-correction
  review and TASK-RAG-CC1 if they trace to deny-list-related scenarios
  that CC1 invalidated.
- Be careful not to introduce *test-only* helpers that duplicate
  production logic — step defs should drive the real production surface
  (loader, retrieval, verifier) rather than reimplementing it.

## References

- [features/primary-text-rag-and-quote-verifier/primary-text-rag-and-quote-verifier.feature](../../features/primary-text-rag-and-quote-verifier/primary-text-rag-and-quote-verifier.feature) — the scenarios
- [features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py](../../features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py) — the step-def module
- [features/conftest.py](../../features/conftest.py) — shared BDD plumbing
- [tasks/completed/TASK-RAG-CC1/TASK-RAG-CC1.md](../completed/TASK-RAG-CC1/TASK-RAG-CC1.md) — note: removed scenarios for the deny-list
- [tasks/completed/TASK-PRV-008/](../completed/TASK-PRV-008/) — context where this gap was discovered
