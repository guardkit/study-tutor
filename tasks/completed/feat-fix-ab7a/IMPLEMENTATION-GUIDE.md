# FEAT-FIX-AB7A Implementation Guide

## Wave Plan

```
Wave 1: TASK-FIX-AB7A-001  (alone — touches FEAT-70A4.yaml)
        TASK-FIX-AB7A-001b (sequential follow-up — also touches FEAT-70A4.yaml; SUPERSEDES 001's AC2)
Wave 2: TASK-FIX-AB7A-002 + TASK-FIX-AB7A-003 (parallel — different test files)
Wave 3: TASK-FIX-AB7A-004 (alone — also touches FEAT-70A4.yaml; cannot parallel with 001/001b)
Wave 4: TASK-FIX-AB7A-005 (alone — operator-run resume)
```

**Why 001b exists:** Player ran 001 and discovered AC2 fails because the worktree venv has no pytest installed (`environment_bootstrap.py` runs `pip install -e .` without extras; pyproject.toml's `[dev]` extras with pytest et al. are not installed). 001's YAML edit is correct as far as it goes; 001b adds an idempotent `pip install -e ".[dev]"` to the smoke gate command and switches `.guardkit/venv/bin/pytest` → `.guardkit/venv/bin/python -m pytest`. After 001b completes, 001 can be moved from `tasks/blocked/` to `tasks/completed/`.

**Why wave 1 and wave 3 cannot merge:** they both edit `.guardkit/features/FEAT-70A4.yaml`. The whole point of this feature is to fix exactly this kind of source-overlap-in-parallel hazard, so we model the fix the right way.

**Why wave 2 is parallel:** the seam tests are in two separate, never-shared test files. This run also serves as a controlled re-validation of the parallel-execution path now that we understand its hazards.

## Execution Order

1. `/task-work TASK-FIX-AB7A-001` — pin smoke-gate interpreter to venv path **(DONE — partially complete; AC1/3/4 passed, AC2 blocked; see `tasks/blocked/feat-fix-ab7a/TASK-FIX-AB7A-001-...md`)**
2. `/task-work TASK-FIX-AB7A-001b` — install [dev] extras + switch to `python -m pytest` (unblocks 001's AC2 retroactively)
3. `/task-work TASK-FIX-AB7A-002` AND `/task-work TASK-FIX-AB7A-003` (parallel OK)
4. **Pre-resume gate (mandatory):** run the verification commands below. If any fail, especially the seam tests, halt and triage.
5. `/task-work TASK-FIX-AB7A-004` — serialise wave 3 of FEAT-70A4
6. Operator-run: `guardkit autobuild feature FEAT-70A4 --resume`

## Pre-Resume Verification (between Wave 3 and Wave 4)

```bash
cd /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-70A4

# 0. (one-time after 001b lands; idempotent thereafter) install [dev] extras
.guardkit/venv/bin/python -m pip install --quiet --disable-pip-version-check -e ".[dev]"
.guardkit/venv/bin/python -c "import pytest; print(pytest.__version__)"   # expect >=9.0.2

# 1. venv interpreter resolves the editable install
.guardkit/venv/bin/python -c "from study_tutor.knowledge.corpus_models import \
  CorpusChunk, CitationAnchor, SourceType, PlayCitationAnchor, NovelCitationAnchor"

# 2. existing knowledge unit tests pass
.guardkit/venv/bin/python -m pytest tests/unit/knowledge/ -x -q

# 3. NEW seam test for PRV-002 passes
.guardkit/venv/bin/python -m pytest -m seam tests/unit/knowledge/test_seam_corpus_loader.py -v

# 4. NEW seam test for PRV-003 passes
.guardkit/venv/bin/python -m pytest -m seam tests/unit/knowledge/test_seam_retrieval_decision.py -v

# 5. updated smoke gate command runs cleanly (mirrors what GuardKit will execute)
/bin/bash -c 'set -e
.guardkit/venv/bin/python -m pip install --quiet --disable-pip-version-check -e ".[dev]"
.guardkit/venv/bin/python -c "from study_tutor.knowledge.corpus_models import \
  CorpusChunk, CitationAnchor, SourceType, PlayCitationAnchor, NovelCitationAnchor"
.guardkit/venv/bin/python -m pytest tests/unit/knowledge/ -x -q'
```

All six must exit 0 before TASK-FIX-AB7A-005. (Step 0 is a precondition for the rest; it's also baked into step 5's smoke-gate-equivalent so the autobuild's runtime gate self-heals if pytest gets removed.)

## What Makes This Non-Regressive

- All edits are scoped to `FEAT-70A4.yaml` and new test files — no other feature's autobuild behaviour changes.
- The `.guardkit/venv/bin/python` path is created by every bootstrap (verified in `environment_bootstrap.py:1078`); the relative path resolves from the worktree cwd that `smoke_gates` always uses.
- Wave serialisation only affects FEAT-70A4's plan; default planner behaviour for other features is untouched.
- The seam-test backfill is purely additive code. If they fail, that's diagnostic — escalate before resuming.
- `--resume` re-bootstraps the venv idempotently and picks up from wave 3 (`feature_orchestrator.py:892-913`).

## Failure Branching

If TASK-FIX-AB7A-002 (PRV-002 seam test) **fails** when run locally:
- Open a new TASK-FIX-AB7A-002b for the actual code fix in `src/study_tutor/knowledge/corpus.py`
- Do NOT proceed to wave 3 until 002b is approved and 002 passes
- This is the safety net that the `parallel_contention` conditional approval did not provide

Same branching for TASK-FIX-AB7A-003 (PRV-003 seam test) → TASK-FIX-AB7A-003b on `retrieval.py`.
