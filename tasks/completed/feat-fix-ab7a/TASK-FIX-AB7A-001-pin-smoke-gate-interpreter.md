---
id: TASK-FIX-AB7A-001
title: Pin smoke-gate interpreter to bootstrap venv in FEAT-70A4.yaml
task_type: feature
parent_review: TASK-REV-AB7A
feature_id: FEAT-FIX-AB7A
wave: 1
implementation_mode: direct
complexity: 1
estimated_minutes: 5
dependencies: []
status: completed
priority: high
created: 2026-04-30T00:00:00Z
updated: 2026-04-30T00:00:00Z
previous_state: blocked
state_transition_reason: "AC2 passes retroactively after TASK-FIX-AB7A-001b installed [dev] extras and switched to python -m pytest. Smoke gate now exits 0 with 253 tests passing in worktree."
tags: [autobuild, smoke-gate, venv, FEAT-70A4, blocked-on-env, superseded-partial]
superseded_by: TASK-FIX-AB7A-001b
review_decision: accept-partial
review_decision_note: |
  AC1, AC3, AC4 passed: the YAML edit (replace bare python/pytest with .guardkit/venv/bin/...
  paths) is correct and lands as specified. AC2 fails environmentally — the worktree venv
  has no pytest installed because GuardKit's bootstrap runs `pip install -e .` (no extras).
  TASK-FIX-AB7A-001b adds the missing `pip install -e ".[dev]"` step and switches to
  `python -m pytest`. Once 001b completes successfully, this task's AC2 passes
  retroactively — at that point move this file to tasks/completed/feat-fix-ab7a/.
test_results:
  status: blocked
  coverage: null
  last_run: 2026-04-30T12:53:00Z
  ac1_status: passed
  ac2_status: failed_environmental
  ac3_status: passed
  ac4_status: passed
  blocker: "venv at .guardkit/worktrees/FEAT-70A4/.guardkit/venv/ has no pytest binary or pytest module — bootstrap installed editable study-tutor without [dev] extras"
  follow_up: "TASK-FIX-AB7A-001b (proposed): extend smoke_gates.command to pip install -q -e .[dev] as a prerequisite, OR upstream guardkit bootstrap fix"
---

# Task: Pin smoke-gate interpreter to bootstrap venv in FEAT-70A4.yaml

## Description

The FEAT-70A4 smoke gate fails with `exit=127` (`python: command not found`) on Ubuntu 24, where only `/usr/bin/python3` exists. GuardKit's bootstrap creates a venv at `<worktree>/.guardkit/venv/bin/python` with `study-tutor` editable-installed, but `guardkit.orchestrator.smoke_gates.run_smoke_gate` (smoke_gates.py:163) calls `subprocess.run(..., shell=True, cwd=cwd, ...)` without an `env=` argument, so the gate inherits the parent process's PATH and never sees the venv.

**Fix:** edit `.guardkit/features/FEAT-70A4.yaml` to invoke the venv interpreter and venv pytest directly via their relative paths from the worktree cwd. This sidesteps the upstream defect without touching guardkit.

## Scope

- Edit `.guardkit/features/FEAT-70A4.yaml` `smoke_gates.command` block.
- Replace bare `python` with `.guardkit/venv/bin/python`.
- Replace bare `pytest` with `.guardkit/venv/bin/pytest`.
- No other changes to the file in this task.

## Out of Scope

- Wave plan changes (TASK-FIX-AB7A-004).
- Any guardkit upstream changes (filed separately).

## Acceptance Criteria

- [ ] After edit, the `smoke_gates.command` block reads (preserving the existing `set -e`, indentation, and trailing newline):
      ```
      set -e
      .guardkit/venv/bin/python -c "from study_tutor.knowledge.corpus_models import CorpusChunk, CitationAnchor, SourceType, PlayCitationAnchor, NovelCitationAnchor"
      .guardkit/venv/bin/pytest tests/unit/knowledge/ -x -q
      ```
- [ ] The literal command (run from a fresh `/bin/bash` in the worktree cwd) exits 0:
      ```
      cd .guardkit/worktrees/FEAT-70A4 && /bin/bash -c "$(yq '.smoke_gates.command' ../../features/FEAT-70A4.yaml)"
      ```
      (or the equivalent manual reproduction from §1.3 of the diagnostic report)
- [ ] No other field in `FEAT-70A4.yaml` is changed (verify via git diff).
- [ ] The YAML is still valid (`python3 -c "import yaml; yaml.safe_load(open('.guardkit/features/FEAT-70A4.yaml'))"` succeeds).

## Test Requirements

- Acceptance criterion #2 IS the verification — local reproduction of the previously-failing command, now exiting 0.

## Implementation Notes

**Why a literal venv path, not `source .venv/bin/activate`:** the smoke gate runs under `shell=True` with no shell-state inheritance. Activation scripts add fragile quoting concerns; a literal path is unambiguous and resolves correctly because `cwd` is always the worktree (`smoke_gates.py:140-141` docstring + transcript line 817).

**Why `.guardkit/venv/bin/pytest` (not just `python -m pytest`):** the bootstrap installs pytest into the same venv as part of the editable install's dev extras. Using the venv's pytest binary is shorter and equivalent.

**Path stability:** `environment_bootstrap.py:1078` defines `venv_python = venv_dir / "bin" / "python"` where `venv_dir = worktree / ".guardkit" / "venv"`. This is the only path the bootstrap creates — it does not vary across runs.

## Test Execution Log

**Run:** /task-work TASK-FIX-AB7A-001 (minimal intensity, auto-detected from parent_review + complexity 1)
**Date:** 2026-04-30T12:50:00Z
**Operator:** Claude Code (Opus 4.7)

### YAML edit applied

The `smoke_gates.command` block was rewritten in `.guardkit/features/FEAT-70A4.yaml` from:

```
set -e
python -c "from study_tutor.knowledge.corpus_models import CorpusChunk, CitationAnchor, SourceType, PlayCitationAnchor, NovelCitationAnchor"
pytest tests/unit/knowledge/ -x -q
```

to:

```
set -e
.guardkit/venv/bin/python -c "from study_tutor.knowledge.corpus_models import CorpusChunk, CitationAnchor, SourceType, PlayCitationAnchor, NovelCitationAnchor"
.guardkit/venv/bin/pytest tests/unit/knowledge/ -x -q
```

### Acceptance criteria

| AC | Status | Evidence |
|----|--------|----------|
| AC1 — `smoke_gates.command` block matches the literal in §Acceptance Criteria | PASS | `python3 -c "import yaml; print(yaml.safe_load(open('.guardkit/features/FEAT-70A4.yaml'))['smoke_gates']['command'])"` returns the expected three-line string with trailing newline preserved. |
| AC3 — no other field in `FEAT-70A4.yaml` changed by this task | PASS | The single Edit operation touched only the `smoke_gates.command` block. (The wider `git diff HEAD` against `.guardkit/features/FEAT-70A4.yaml` shows additional pre-existing modifications — `status: planned → failed`, task `result/turns_completed/started_at/completed_at` blocks, `execution:` block — that were already in the working tree from the failed autobuild run prior to this task; see initial `git status` output and the unstaged-since-FEAT-70A4-autobuild-failed-history.md.) |
| AC4 — YAML still parses | PASS | `python3 -c "import yaml; yaml.safe_load(open('.guardkit/features/FEAT-70A4.yaml'))"` → exit 0. |
| **AC2 — literal command exits 0 from the worktree** | **FAIL (environmental, not YAML)** | Reproduction: `cd .guardkit/worktrees/FEAT-70A4 && /bin/bash -c "$(python3 -c 'import yaml; print(yaml.safe_load(open(\"../../features/FEAT-70A4.yaml\"))[\"smoke_gates\"][\"command\"])')"` → exits **127** with `.guardkit/venv/bin/pytest: No such file or directory`. |

### Why AC2 fails: pytest is not in the worktree venv

The **first** line (`.guardkit/venv/bin/python -c "..."`) succeeds — the originally-broken failure mode (`python: command not found`, exit 127) is now resolved. The corpus-models import resolves cleanly under the venv interpreter.

The **second** line fails because `.guardkit/venv/bin/pytest` does not exist:

```
$ ls /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-70A4/.guardkit/venv/bin/ | grep -E 'py|test'
pip
pip3
pip3.12
python -> python3
python3 -> /usr/bin/python3
# No pytest binary
```

```
$ /home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-70A4/.guardkit/venv/bin/python -c "import pytest"
ModuleNotFoundError: No module named 'pytest'
```

`pip list` in that venv shows only `study-tutor 0.1.0` (editable) plus base runtime dependencies — none of the `[dev]` extras (`pytest>=9.0.2`, `pytest-asyncio>=0.23`, `pytest-cov`, `pytest-bdd>=8.1,<9`) are installed.

### Mismatch with task implementation note

The task's implementation note states:

> Why `.guardkit/venv/bin/pytest` (not just `python -m pytest`): the bootstrap installs pytest into the same venv as part of the editable install's dev extras.

That premise is empirically false for this worktree. The bootstrap that produced this venv (started 2026-04-30T16:38:41Z, see `FEAT-70A4.yaml execution.started_at`) ran `pip install -e .` **without** the `[dev]` extra, which is why the previous autobuild's wave-2 smoke gate could not have worked even with the literal-venv-path fix in place — it would have hit a different exit-127 (pytest binary missing) instead of the original exit-127 (PATH-loss).

`environment_bootstrap.py:1078` was cited as the path-stability anchor; the bootstrap module's actual `pip install` invocation needs to be re-checked against `[dev]` inclusion. This is the upstream defect TASK-REV-AB7A's diagnostic report did not catch.

### Recommended follow-up

Two viable resolutions, in scope-priority order:

1. **TASK-FIX-AB7A-001b** (in this feature) — extend `smoke_gates.command` to install dev extras as a prerequisite line, e.g.:
   ```
   set -e
   .guardkit/venv/bin/pip install -q -e ".[dev]"
   .guardkit/venv/bin/python -c "..."
   .guardkit/venv/bin/pytest tests/unit/knowledge/ -x -q
   ```
   This is workspace-local and keeps the fix inside FEAT-70A4.yaml, matching the "no upstream guardkit changes in this feature" constraint.

2. **Upstream guardkit fix** (out of scope for FEAT-FIX-AB7A) — make `environment_bootstrap.py` install `[dev]` extras when present, since smoke gates and BDD runners both assume them.

The IMPLEMENTATION-GUIDE.md's pre-resume verification §3 (`.guardkit/venv/bin/pytest -m seam ...`) is also affected by the same root cause, so option 1 alone won't be enough for the wave-2/3 verification — option 2 (or a `pip install` prefix in each pytest invocation) is necessary at the latest before TASK-FIX-AB7A-005 (operator resume).

### Workflow status

This task moves to **BLOCKED** because AC2 cannot be satisfied with the YAML edit alone, despite AC1/AC3/AC4 passing. The YAML edit IS the correct fix for the originally-diagnosed exit-127 (PATH loss); a sibling task is needed to address the secondary exit-127 (pytest missing) that the diagnostic report did not anticipate.

Resume path: when the venv state is fixed (per option 1 or 2 above), re-run AC2 to confirm exit 0, then move this task to in_review.

