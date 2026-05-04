# FEAT-FIX-AB7A — Unblock FEAT-70A4 Autobuild Resume

**Parent review:** [TASK-REV-AB7A](../../in_review/TASK-REV-AB7A-analyze-failed-autobuild-feat-70a4.md)
**Diagnostic report:** [.claude/reviews/TASK-REV-AB7A-report.md](../../../.claude/reviews/TASK-REV-AB7A-report.md)
**Source-traced addendum:** [.claude/reviews/TASK-REV-AB7A-addendum-source-traced.md](../../../.claude/reviews/TASK-REV-AB7A-addendum-source-traced.md)
**Worktree (preserved):** `.guardkit/worktrees/FEAT-70A4` on branch `autobuild/FEAT-70A4`

---

## Problem

The FEAT-70A4 autobuild (Primary-Text RAG + Quote Verifier) failed at the post-wave-2 smoke gate with `exit=127` ("`python: command not found`"), halting before waves 3–5 could run. Three of seven tasks reached `approved`; four are unstarted. Two compounding root causes were source-traced against the active editable install of guardkit at `/home/richardwoollcott/Projects/appmilla_github/guardkit`:

1. The smoke gate hook in `FEAT-70A4.yaml` invokes bare `python`, but Ubuntu 24 ships only `/usr/bin/python3`. GuardKit's bootstrap correctly created `.guardkit/venv` and editable-installed `study-tutor`, but `guardkit.orchestrator.smoke_gates.run_smoke_gate` does not propagate the bootstrap interpreter (no `env=` argument on its `subprocess.run`, no interpreter parameter in its signature).
2. Wave 2's "parallel contention" was not infrastructure contention — TASK-PRV-002 and TASK-PRV-003 both wrote step definitions to the same 888-line BDD glue file `features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py`. Their independent test verification ran against an inconsistent committed state. The conditional-approval rule's `parallel_contention` branch (`coach_validator.py:861-866`) approved both anyway because all Player gates passed.

## Solution

Five tasks land entirely inside this repo. None require guardkit changes.

| Wave | Task | Mode | Files | Effort | Status |
|---|---|---|---|---|---|
| 1 | [TASK-FIX-AB7A-001](../../blocked/feat-fix-ab7a/TASK-FIX-AB7A-001-pin-smoke-gate-interpreter.md) | direct | `.guardkit/features/FEAT-70A4.yaml` (smoke_gates section — partial: bare-`python` fix only) | 5 min | **blocked** (AC1/3/4 ✅, AC2 ❌ env) |
| 1 | [TASK-FIX-AB7A-001b](TASK-FIX-AB7A-001b-install-dev-extras-and-use-python-m-pytest.md) | direct | `.guardkit/features/FEAT-70A4.yaml` (smoke_gates section — adds [dev] install + `python -m pytest`) | 8 min | backlog |
| 2 | [TASK-FIX-AB7A-002](TASK-FIX-AB7A-002-backfill-prv-002-seam-test.md) | task-work | new `tests/unit/knowledge/test_seam_corpus_loader.py` | 20 min | backlog |
| 2 | [TASK-FIX-AB7A-003](TASK-FIX-AB7A-003-backfill-prv-003-seam-test.md) | task-work | new `tests/unit/knowledge/test_seam_retrieval_decision.py` | 20 min | backlog |
| 3 | [TASK-FIX-AB7A-004](TASK-FIX-AB7A-004-serialise-waves-in-feature-spec.md) | direct | `.guardkit/features/FEAT-70A4.yaml` (orchestration section) | 10 min | backlog |
| 4 | [TASK-FIX-AB7A-005](TASK-FIX-AB7A-005-resume-autobuild.md) | manual | `guardkit autobuild feature FEAT-70A4 --resume` | 25 min wall-clock | backlog |

**Why 001b exists (post-hoc):** Player ran 001 (the YAML edit) and the YAML lands correctly, but AC2 fails because the worktree venv has no pytest installed — `environment_bootstrap.py` runs `pip install -e .` without optional extras. pyproject.toml's `[dev]` group (pytest, pytest-asyncio, pytest-cov, pytest-bdd) is the canonical home; we install it idempotently as the first line of the smoke gate. Coach gates passed during the original failed run because Coach uses `sys.executable -m pytest` (GuardKit's interpreter) rather than the worktree venv. The smoke-gate hook has no path to that, so it must self-bootstrap.

**Wave structure note:** TASK-FIX-AB7A-001 and -004 both edit `FEAT-70A4.yaml` so they cannot run in parallel — they go in different waves. Tasks -002 and -003 edit different test files and CAN run in parallel; this also re-validates the parallel-execution path on a controlled boundary.

## Critical Pre-Resume Gate

After wave 3 (the seam-test backfill) completes, the operator must verify the gate conditions in §6 of the source-traced addendum. If either seam test fails locally, **do not run TASK-FIX-AB7A-005** — the conditional approval that PRV-002 or PRV-003 received was masking a real bug, and the resume would re-ingest contaminated state into wave 3+.

## Upstream Findings (Filed Separately)

Five GuardKit-side findings (smoke-gate interpreter resolution, conditional-approval rule, planner overlap detection, seam-test blocking, SDK reader transport) are filed as tasks against the guardkit repo at `/home/richardwoollcott/Projects/appmilla_github/guardkit`. They are NOT prerequisites for this feature — the local fixes are designed to work without them.
