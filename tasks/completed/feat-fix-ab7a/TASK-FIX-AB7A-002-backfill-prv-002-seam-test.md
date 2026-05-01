---
id: TASK-FIX-AB7A-002
title: Backfill seam test for TASK-PRV-002 (corpus loader → models contract)
task_type: feature
parent_review: TASK-REV-AB7A
feature_id: FEAT-FIX-AB7A
wave: 2
implementation_mode: task-work
complexity: 2
estimated_minutes: 20
dependencies:
  - TASK-FIX-AB7A-001
  - TASK-FIX-AB7A-001b
status: completed
priority: high
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
completed: 2026-04-30T00:00:00Z
previous_state: in_review
state_transition_reason: "All ACs verified; seam test passed; gate condition for FEAT-FIX-AB7A wave 4 cleared"
completed_location: tasks/completed/feat-fix-ab7a/
tags: [seam-test, contract-test, FEAT-70A4, FEAT-PRV-002, latent-bug-check]
test_results:
  status: passed
  coverage: null
  last_run: 2026-04-30T00:00:00Z
  command: ".guardkit/venv/bin/python -m pytest -m seam tests/unit/knowledge/test_seam_corpus_loader.py -v"
  passed: 1
  failed: 0
  duration_seconds: 0.02
  regression_check:
    command: ".guardkit/venv/bin/python -m pytest tests/unit/knowledge/ -x -q"
    passed: 254
    failed: 0
    duration_seconds: 8.67
---

# Task: Backfill seam test for TASK-PRV-002 (corpus loader → models contract)

## Description

TASK-PRV-002 was conditionally approved on the basis of `parallel_contention + all_gates_passed` despite its independent test verification failing in 6.3s — because both PRV-002 and PRV-003 raced to write the shared 888-line BDD glue file. The seam test for PRV-002's contract was **explicitly planned and stubbed in code** in the original task file (`tasks/backlog/primary-text-rag-and-quote-verifier/TASK-PRV-002-source-typed-corpus-loader.md:170-207`), but the Player did not implement it. The Coach validator flagged the gap ("no seam/contract/boundary tests detected for cross-boundary feature") but did not block.

This task implements the planned seam test as a **gate condition** for resuming the autobuild. If it fails locally, the conditionally-approved PRV-002 implementation has a real bug masked by the wave-2 contention — escalate to a code fix before resume.

## Scope

- Implement seam test at `tests/unit/knowledge/test_seam_corpus_loader.py`.
- Mark with `@pytest.mark.seam` and `@pytest.mark.integration_contract("SourceTypedCorpus")`.
- Validate that `study_tutor.knowledge.corpus.load_corpus()` emits `CorpusChunk` records with correctly-typed `CitationAnchor` discriminated-union members per the contract defined by TASK-PRV-001's models.
- Use `tmp_path` fixtures for play and novel sources to avoid touching real corpus.
- Run inside the worktree venv: `.guardkit/venv/bin/python -m pytest -m seam tests/unit/knowledge/test_seam_corpus_loader.py -v` (depends on TASK-FIX-AB7A-001b having installed `[dev]` extras into the venv).

## Out of Scope

- Modifying `corpus.py` (only test code in this task).
- Backfilling PRV-003's seam test (TASK-FIX-AB7A-003).
- Registering the `seam` marker if not already present (handled in PRV-001's deliverables; if missing, fix in this task as a one-line `pyproject.toml` change).

## Acceptance Criteria

- [ ] File `tests/unit/knowledge/test_seam_corpus_loader.py` exists in the worktree.
- [ ] File contains a test `test_corpus_chunk_carries_typed_citation_anchor` (or similarly named, mirroring the stub at `tasks/backlog/primary-text-rag-and-quote-verifier/TASK-PRV-002-source-typed-corpus-loader.md:180-207`).
- [ ] Test imports the four canonical names from `study_tutor.knowledge.corpus_models`: `CorpusChunk`, `PlayCitationAnchor`, `NovelCitationAnchor`, `SourceType`.
- [ ] Test sets up a primary-text play fixture under `tmp_path`, calls `load_corpus(tmp_path)`, and asserts:
      - At least one `CorpusChunk` is returned.
      - Every primary-text play chunk has `chunk.citation_anchor is not None`.
      - Every primary-text play chunk has `isinstance(chunk.citation_anchor, PlayCitationAnchor)`.
- [ ] Test runs successfully under `.guardkit/venv/bin/python -m pytest -m seam tests/unit/knowledge/test_seam_corpus_loader.py -v` (TASK-FIX-AB7A-001b must have completed first to ensure pytest is in the venv).
- [ ] Test exits 0. (If non-zero — STOP. Do not advance to TASK-FIX-AB7A-004. Open a code-fix subtask against `corpus.py`.)
- [ ] Test code passes the project's lint/format checks.

## Test Requirements

The test file IS the deliverable. It must:
- [ ] Be collected by `pytest -m seam` (i.e. carry `@pytest.mark.seam`).
- [ ] Be hermetic (no network, no real corpus, no env-dependent paths).
- [ ] Run in <2s wall-clock.

## Implementation Notes

**Reference stub** (verbatim from `tasks/backlog/primary-text-rag-and-quote-verifier/TASK-PRV-002-source-typed-corpus-loader.md:170-207`):

```python
"""Seam test: verify loader emits CorpusChunk with correctly-typed
CitationAnchor union per the SourceTypedCorpus contract."""
import pytest
from study_tutor.knowledge.corpus_models import (
    CorpusChunk, PlayCitationAnchor, NovelCitationAnchor, SourceType,
)


@pytest.mark.seam
@pytest.mark.integration_contract("SourceTypedCorpus")
def test_corpus_chunk_carries_typed_citation_anchor(tmp_path):
    # Fixture: place a small play under primary_text/ and load.
    chunks = []  # await load_corpus(tmp_path)

    primary_play_chunks = [
        c for c in chunks
        if c.source_type is SourceType.PRIMARY_TEXT
        and c.text_name == "macbeth"
    ]

    assert primary_play_chunks, "expected primary-text chunks for play"
    for chunk in primary_play_chunks:
        assert chunk.citation_anchor is not None
        assert isinstance(chunk.citation_anchor, PlayCitationAnchor)
```

The stub uses `await load_corpus(tmp_path)` but the actual `corpus.load_corpus()` is synchronous (per the PRV-002 task spec). The implementation should drop the `await` and create a real fixture (e.g. write a small Standard Ebooks-style play file under `tmp_path / "primary_text" / "macbeth.txt"`).

**Why this is a hard gate:** the only safety net the conditional-approval rule did NOT provide is a test that reads the real contract surface. If `load_corpus` is silently emitting plain dicts instead of typed `CitationAnchor` instances, this test fails. PRV-005 (verifier) consumes `chunk.citation_anchor` via `isinstance` checks — so a contract violation here cascades into wave 4.

## Test Execution Log

### Phase 4: Seam test (AC gate)

```
$ cd .guardkit/worktrees/FEAT-70A4
$ .guardkit/venv/bin/python -m pytest -m seam \
    tests/unit/knowledge/test_seam_corpus_loader.py -v

============================= test session starts ==============================
platform linux -- Python 3.12.3, pytest-9.0.3, pluggy-1.6.0
rootdir: /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-70A4
configfile: pyproject.toml
plugins: asyncio-1.3.0, anyio-4.13.0, cov-7.1.0, bdd-8.1.0, langsmith-0.7.38

tests/unit/knowledge/test_seam_corpus_loader.py::test_corpus_chunk_carries_typed_citation_anchor PASSED [100%]

============================== 1 passed in 0.02s ===============================
```

**Result:** PASSED. The PRV-002 contract is honoured by the conditionally-approved
`load_corpus` implementation. No code fix required; latent-bug-check clean.

### Regression check: full knowledge unit test suite

```
$ .guardkit/venv/bin/python -m pytest tests/unit/knowledge/ -x -q
254 passed in 8.67s
```

**Result:** PASSED. Adding the seam test introduces no regression in the
existing knowledge module test suite.

## Acceptance Criteria — Verification

- [x] File `tests/unit/knowledge/test_seam_corpus_loader.py` exists in the worktree.
- [x] File contains a test `test_corpus_chunk_carries_typed_citation_anchor`.
- [x] Test imports the four canonical names from `study_tutor.knowledge.corpus_models`:
      `CorpusChunk`, `PlayCitationAnchor`, `NovelCitationAnchor`, `SourceType`.
- [x] Test sets up a primary-text play fixture under `tmp_path`, calls
      `load_corpus(tmp_path)`, and asserts on `result.chunks` (note:
      `load_corpus` returns `IngestResult`; the AC was written before that
      detail was finalised — `result.chunks` is the documented surface and
      what PRV-005 will iterate).
- [x] Test runs successfully under `.guardkit/venv/bin/python -m pytest -m seam ...`.
- [x] Test exits 0. **Latent-bug-check clean — wave 4 may proceed once 003 also passes.**
- [x] Test code passes syntax + compile checks. (No project-level linter
      configured; followed the same style as `test_seam_pydantic_entities.py`.)
- [x] Marker `@pytest.mark.seam` collected by `pytest -m seam` (verified by
      pytest selecting only this one test under the `-m seam` filter).
- [x] Hermetic — no network, no real corpus, `tmp_path` only.
- [x] Runs in <2s wall-clock (0.02s).

## Implementation Notes (executor)

The stub in PRV-002 used `await load_corpus(tmp_path)` and treated the return
value as an iterable of chunks. The real `load_corpus` is **synchronous** and
returns `IngestResult` (with `.chunks: list[CorpusChunk]`). The test was
adapted accordingly: `result = load_corpus(tmp_path); chunks = result.chunks`.

Fixture choice: a small Macbeth-style play with `ACT I` / `SCENE 1` markers
and several short content lines. Because the loader's anchor inferer needs a
complete `(act, scene, line)` state before the chunk's start offset, leading
the fixture with the act/scene headings guarantees every chunk emitted gets a
`PlayCitationAnchor` — which is what AC#4 requires.

The test additionally asserts `not isinstance(anchor, NovelCitationAnchor)` to
guard the discriminated-union behaviour against a future regression where the
`kind` literal is loosened or both branches accidentally accept the same data.

## Result

Phase 4 (Testing) gate cleared. Phase 4.5 (Fix Loop) not entered — first run
passed. Phase 5 (Code Review) — file compiles, follows existing seam-test
style conventions, no project-level linter to run. Phase 5.5 (Plan Audit) —
skipped per MINIMAL intensity (no implementation plan exists).

Task transitions: BACKLOG → IN_PROGRESS → IN_REVIEW.
