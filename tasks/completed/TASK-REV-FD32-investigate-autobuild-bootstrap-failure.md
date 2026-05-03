---
id: TASK-REV-FD32
title: Investigate autobuild FEAT-FD32 bootstrap failure
task_type: review
review_mode: debugging
review_depth: standard
status: review_complete
created: 2026-05-02T00:00:00Z
updated: 2026-05-02T00:00:00Z
priority: high
tags: [autobuild, guardkit, bootstrap, uv, investigation, decision-point]
complexity: 4
decision_required: true
related_feature: FEAT-FD32
related_history: docs/history/autobuild-FEAT-FD32-failed-run-1-history.md
test_results:
  status: pending
  coverage: null
  last_run: null
review_results:
  mode: debugging
  depth: standard
  decision: implement
  root_cause_confirmed: true
  fix_surface: guardkit_code
  blast_radius: all_uv_lock_projects
  recommended_followup: TASK-FIX-FD32-uv-bootstrap-command (in guardkit repo)
  followup_task_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/tasks/backlog/TASK-FIX-FD32-uv-bootstrap-command.md
  report_inline: true
  decision_recorded_at: 2026-05-02T00:00:00Z
---

# Task: Investigate autobuild FEAT-FD32 bootstrap failure

## Description

The first `guardkit autobuild feature FEAT-FD32` run aborted in Phase 1
(Setup) before any task was dispatched. The orchestrator created the shared
worktree at `.guardkit/worktrees/FEAT-FD32/` and copied all five task files,
but the Python environment bootstrap step failed and — because the manifest
declares `requires-python: >=3.11` — the smart default `bootstrap_failure_mode`
was `block`, so the whole run hard-failed.

Full transcript: [autobuild-FEAT-FD32-failed-run-1-history.md](../../docs/history/autobuild-FEAT-FD32-failed-run-1-history.md)

This is a **review / investigation** task: we need to understand the root
cause, decide on a fix path (GuardKit code change vs. local config workaround
vs. both), and produce a recommendation before any implementation work
starts. No code should be written under this task — implementation is a
follow-up.

## Observed Failure

From the run log:

```
INFO: Running install for python (pyproject.toml): uv pip sync uv.lock
WARNING: Install failed for python (pyproject.toml) with exit code 2:
stderr: error: Couldn't parse requirement in `uv.lock` at position 0
  Caused by: no such comparison operator "=", must be one of ~= == != <= >= < > ===
version = 1
        ^^^
```

Followed by:

```
ERROR: Bootstrap hard-fail: 0/1 install(s) succeeded for essential stack(s): python.
Manifest: .../FEAT-FD32/pyproject.toml
Manifest requires-python: >=3.11
```

## Initial Hypothesis (to verify)

`uv pip sync` is the **pip-compatible** sync command and expects a
`requirements.txt`-style file. The repo's `uv.lock` is uv's native TOML
lockfile (first line `version = 1`, second `revision = 3`). The pip-sync
parser tries to interpret that first line as a PEP 508 requirement and
rejects it.

The correct command for syncing a project from a uv.lock is `uv sync`
(project-aware, reads `pyproject.toml` + `uv.lock`). A plausible fix is
that GuardKit's environment bootstrap should detect the presence of
`uv.lock` and run `uv sync` instead of `uv pip sync uv.lock`.

This hypothesis must be **verified** as part of this review — do not
assume it is correct without checking GuardKit's bootstrap code and uv's
current CLI semantics.

## Investigation Scope

1. **Reproduce and confirm** the exact command GuardKit invokes.
   - Inspect `guardkit/orchestrator/environment_bootstrap.py` (path shown
     in the traceback module) to see how the install command is chosen.
   - Confirm whether the choice between `uv pip sync <file>` and
     `uv sync` depends on which manifest files are detected.

2. **Verify uv CLI semantics** for the installed uv version.
   - What does `uv pip sync` accept? (`requirements.txt`, not `uv.lock`.)
   - What does `uv sync` do when both `pyproject.toml` and `uv.lock`
     are present?
   - Is there a uv version mismatch between what GuardKit expects and
     what is installed?

3. **Determine the fix surface**.
   - Is this a bug in GuardKit's bootstrap logic? (Most likely.)
   - Is there a project-side workaround (e.g. delete/regenerate
     `uv.lock`, add a `requirements.txt` for bootstrap, or set
     `bootstrap_failure_mode: warn` in `.guardkit/config.yaml`)?
   - What does `--bootstrap-failure-mode warn` actually skip — would the
     downstream tasks still have a working venv, or would they all fail
     individually?

4. **Assess blast radius**.
   - Does this same failure block other features in this repo
     (e.g. FEAT-1773)?
   - Does it block other study-tutor work that depends on autobuild?
   - Is FEAT-PH2-GR-001 (the manually-driven Phase 2 work) affected, or
     can it proceed independently?

5. **Recommend a path forward**.
   - Short-term unblock for FEAT-FD32 (workaround acceptable).
   - Long-term fix (likely a GuardKit PR upstream).
   - Whether to retry FEAT-FD32 now or defer until the fix lands.

## Acceptance Criteria

- [ ] Root cause confirmed with evidence (code reference in
      GuardKit + uv CLI behaviour reference).
- [ ] Hypothesis above is either validated or replaced with the correct
      explanation.
- [ ] Fix surface identified: GuardKit code change, local config change,
      or both — with file/line pointers where applicable.
- [ ] Blast radius assessed: which other features/tasks are blocked by
      the same issue.
- [ ] A clear recommendation document is produced with options, tradeoffs,
      and a recommended next step (typically a follow-up implementation
      task and/or a GuardKit upstream issue/PR).
- [ ] Decision checkpoint reached: [A]ccept findings / [I]mplement fix /
      [R]evise / [C]ancel.
- [ ] If [I]mplement is chosen, a follow-up implementation task is
      created (e.g. `TASK-FIX-FD32-uv-bootstrap-command`).

## Deliverables

- A short review report (in this task file's "Findings" section, or as
  a sibling doc under `docs/state/`) covering:
  - Root cause
  - Evidence (file:line references, command output)
  - Options considered
  - Recommendation
  - Follow-up task IDs (if any)

## Out of Scope

- Implementing the actual fix (handled by a follow-up task if approved).
- Re-running FEAT-FD32 autobuild (only after a fix or sanctioned
  workaround is in place).
- Modifying the FEAT-FD32 task plan itself — those tasks are unchanged;
  the issue is purely in the orchestrator's setup phase.

## Suggested Workflow

1. `/task-review TASK-REV-FD32 --mode=debugging`
2. Review findings at the decision checkpoint.
3. If approved for fix: `/task-create "Fix uv bootstrap command in GuardKit autobuild" prefix:FIX`
4. `/task-complete TASK-REV-FD32`

## Findings

### Root Cause (Confirmed)

GuardKit's bootstrap chooses the **wrong uv subcommand** when both
`pyproject.toml` and `uv.lock` are present.

**Code reference**: [environment_bootstrap.py:480-481](file:///Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/environment_bootstrap.py#L480-L481)

```python
if has_uv_lock and uv_available:
    return ["uv", "pip", "sync", "uv.lock"]
```

This is the *only* code path that emits a `uv ... sync` command in
GuardKit (verified by `grep -rn "uv.*sync" guardkit/`); there is no
correct `uv sync` fallback elsewhere.

**Why it fails** — confirmed against the installed uv (uv 0.11.2 via
Homebrew, `uv pip sync --help`):

> Sync an environment with a `requirements.txt` or `pylock.toml` file
> Usage: `uv pip sync [OPTIONS] <SRC_FILE>...`

`uv pip sync` only accepts:
- `requirements.txt` (PEP 508 syntax), or
- `pylock.toml` (PEP 751 standard lockfile).

It does **not** accept `uv.lock` — that is uv's **native** TOML lockfile
(distinct format from PEP 751 `pylock.toml`). When pointed at `uv.lock`,
uv's pip-sync front-end tries to parse it as a PEP 508 requirements file
and chokes on the very first line:

```
version = 1
```

…because `=` is not a valid PEP 508 comparison operator (the legal set
is `~= == != <= >= < > ===` — note the doubled `==`). Hence the exact
error in the run log:

```
error: Couldn't parse requirement in `uv.lock` at position 0
  Caused by: no such comparison operator "=", must be one of ~= == != <= >= < > ===
version = 1
        ^^^
```

The correct command for a `pyproject.toml` + `uv.lock` project is
**`uv sync`** (project-aware; reads both files and provisions the venv).
`uv sync --help` confirms:

> Update the project's environment

The hypothesis in the task brief is **validated as written**.

### Why the Hard-Fail Triggered

[feature_orchestrator.py:1382-1418](file:///Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py#L1382-L1418)
runs the bootstrap gate when:

1. `bootstrap_failure_mode == "block"` — the smart default at
   [feature_orchestrator.py:1341-1380](file:///Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py#L1341-L1380)
   sets `block` whenever any manifest declares `requires-python`. Our
   `pyproject.toml` has `requires-python = ">=3.11"` ([pyproject.toml:9](file:///Users/richardwoollcott/Projects/appmilla_github/study-tutor/pyproject.toml#L9)),
   so `block` was applied automatically.
2. `installs_attempted > 0` — yes, one install was attempted.
3. `installs_failed == installs_attempted` — yes, 1/1 failed.
4. At least one detected stack is essential — Python is essential.

All four held, so the orchestrator raised `FeatureOrchestrationError`
before Wave 1 dispatched. Behaviour is correct given the (broken)
upstream signal — the gate did its job; the bug is purely the install
command.

### Fix Surface

| Layer | File / Path | Change | Risk |
|---|---|---|---|
| **Primary (upstream)** | [`environment_bootstrap.py:481`](file:///Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/environment_bootstrap.py#L481) | Replace `["uv", "pip", "sync", "uv.lock"]` with `["uv", "sync", "--frozen"]` (or `--locked` for stricter mismatch behaviour). | Low — single line, one call site, isolated to the `has_uv_lock and uv_available` branch. |
| **Comment matrix** | [`environment_bootstrap.py:396-404`](file:///Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/environment_bootstrap.py#L396-L404) | Update doc comment so row 2 reads `uv sync --frozen` instead of `uv pip sync uv.lock`. | None. |
| **Test coverage** | (likely `tests/orchestrator/test_environment_bootstrap.py` in guardkit) | Update any test that asserts on the exact argv `["uv", "pip", "sync", "uv.lock"]`; add a regression test that pins the new argv and (ideally) a smoke test that runs the command against a real uv.lock fixture in CI. | Low. |
| **Local config workaround (no code change)** | `.guardkit/config.yaml` — does not exist in this repo | Create with `bootstrap_failure_mode: warn` to downgrade the hard-fail. **Not recommended** — see "Workaround viability" below. | High — masks broken bootstrap. |
| **Local file workaround** | Temporarily rename / delete `uv.lock` before each autobuild run so the matrix falls through to `pip install -e .`. | **Not recommended** — drops lockfile fidelity, easy to forget to restore. | High. |

User owns both repos (`appmilla_github/guardkit/` and
`appmilla_github/study-tutor/`), so the upstream fix is a one-line edit
in code they already control — there is **no need** for a workaround.

#### Workaround viability — `bootstrap_failure_mode: warn`

`warn` only suppresses the orchestrator's *gate* — the install itself
still fails, so the worktree's venv is **not** populated. Each task
spawned in a wave would then run inside a worktree with no editable
install of the project, and any task that imports the package or its
dependencies would fail at import time. This isn't a viable unblock for
FEAT-FD32; downstream tasks need a working venv.

A halfway workaround would be: let the bootstrap fail with `warn`, then
run `uv sync` manually inside the worktree before resuming. This works
in principle but is brittle (every fresh worktree needs the manual
step), defeats the orchestrator's resume model, and leaves the bug live
for every other repo. Not recommended over the one-line upstream fix.

### Blast Radius

- **FEAT-FD32 (this run)** — blocked. ✓ confirmed in run log.
- **FEAT-1773 (study-tutor sibling feature)** — would fail identically.
  Both features share the same worktree-bootstrap path and the same
  `pyproject.toml` + `uv.lock`. Manifest detection is repo-wide, not
  feature-scoped.
- **All GuardKit-managed projects with `pyproject.toml` + `uv.lock` +
  uv-on-PATH and no `[tool.uv.sources]` block** — same failure. This is
  the modern uv-managed Python project layout, which is the recommended
  shape; the bug is broadly impactful for any consumer that has updated
  to a recent uv (the install matrix comment claims this code path was
  designed for exactly this case, so it has been broken for a while).
- **FEAT-PH2-GR-001 (manually-driven Phase 2 Graphiti work)** — **not
  affected**. That feature is being driven through `/task-work` against
  the user's existing top-level venv (already populated via direct
  `uv sync`), bypassing the autobuild orchestrator entirely. The
  Graphiti integration work can proceed independently.
- **Future `/feature-build` runs in this repo** — all blocked until the
  upstream fix lands.

### Options Considered

| # | Option | Pros | Cons | Recommendation |
|---|---|---|---|---|
| 1 | **Fix upstream in `appmilla_github/guardkit/` (line 481)** + update comment + add regression test, then re-run FEAT-FD32. | Permanent fix; benefits FEAT-1773 and every future feature; user owns the repo so no PR-dance required; one-line code change. | Need to pick `--frozen` vs `--locked` (minor decision); should also bump or pin a guardkit re-install if it's installed via pipx/uvx so the fix is picked up. | **Yes — primary path.** |
| 2 | Local config workaround (`bootstrap_failure_mode: warn` in `.guardkit/config.yaml`). | No code change. | Doesn't actually populate the venv → wave tasks will fail at import. Doesn't help FEAT-1773. | No. |
| 3 | Pre-populate worktree venv manually, then resume. | Sidesteps the gate without code change. | Brittle; defeats orchestrator design; bug stays live everywhere else. | No. |
| 4 | Defer FEAT-FD32 until upstream fix lands "naturally". | Zero immediate work. | Doesn't unblock anything; the user maintains the upstream so "naturally" means "we still have to write it". | No. |

### Recommendation

**Option 1.** Single follow-up implementation task in the
`appmilla_github/guardkit/` repo:

- **Title**: `Fix uv bootstrap command: use 'uv sync --frozen' for uv.lock projects`
- **Scope**:
  1. Change [`environment_bootstrap.py:481`](file:///Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/environment_bootstrap.py#L481) from `["uv", "pip", "sync", "uv.lock"]` to `["uv", "sync", "--frozen"]`.
  2. Update the matrix comment at [`environment_bootstrap.py:396-404`](file:///Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/environment_bootstrap.py#L396-L404).
  3. Update / add a regression test against the exact argv (and ideally
     a smoke test that runs the command against a fixture `uv.lock`).
  4. Reinstall guardkit in the user's environment so the new code is
     picked up by the `guardkit` CLI on PATH.
- **Why `--frozen` over `--locked`**: `--frozen` skips re-locking and
  asserts the lockfile matches `pyproject.toml`'s constraints; this is
  the correct semantics for an orchestrator that wants reproducible
  builds and should never mutate the lockfile during bootstrap.
  `--locked` errors if the lockfile is out of date — also acceptable,
  arguably preferable as a louder failure mode. Either is a valid
  choice; flag it for the implementer.
- **Verification**: After the fix, re-run
  `guardkit autobuild feature FEAT-FD32 --verbose` and confirm Phase 1
  Setup completes (worktree venv populated, Wave 1 dispatched).

The fix should be created as `TASK-FIX-FD32-uv-bootstrap-command` in
the **guardkit repo** (not study-tutor — the code lives there), tagged
as related to this review.

After verification, FEAT-1773 and FEAT-FD32 are both unblocked.

### Evidence Summary

- **Run log**: [docs/history/autobuild-FEAT-FD32-failed-run-1-history.md](../../docs/history/autobuild-FEAT-FD32-failed-run-1-history.md) — `uv pip sync uv.lock` at line 31, parse error at 33-36, hard-fail at 40-48.
- **Buggy code**: [environment_bootstrap.py:481](file:///Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/environment_bootstrap.py#L481).
- **Stale doc comment**: [environment_bootstrap.py:401](file:///Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/environment_bootstrap.py#L401).
- **Hard-fail gate**: [feature_orchestrator.py:1382-1418](file:///Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py#L1382-L1418) and smart-default at [1341-1380](file:///Users/richardwoollcott/Projects/appmilla_github/guardkit/guardkit/orchestrator/feature_orchestrator.py#L1341-L1380).
- **uv CLI behaviour**: `uv pip sync --help` (uv 0.11.2 Homebrew) — accepts `requirements.txt` / `pylock.toml`, not `uv.lock`. `uv sync --help` — "Update the project's environment".
- **Local manifests**: [pyproject.toml:9](file:///Users/richardwoollcott/Projects/appmilla_github/study-tutor/pyproject.toml#L9) `requires-python = ">=3.11"`; [uv.lock:1-3](file:///Users/richardwoollcott/Projects/appmilla_github/study-tutor/uv.lock#L1-L3) `version = 1` / `revision = 3` / `requires-python = ">=3.11"`. No `[tool.uv.sources]` in pyproject.
- **No `.guardkit/config.yaml`** exists in this repo, confirming the smart-default `block` mode is in effect.

### Acceptance Criteria — Status

- [x] Root cause confirmed with evidence (GuardKit code reference + uv CLI behaviour reference).
- [x] Hypothesis validated as written.
- [x] Fix surface identified with file/line pointers.
- [x] Blast radius assessed (FEAT-1773 also blocked; FEAT-PH2-GR-001 not affected; broad impact on uv-managed GuardKit consumers).
- [x] Recommendation produced with options + tradeoffs + recommended next step.
- [x] Decision checkpoint reached — **`[I]mplement`** chosen on 2026-05-02.
- [x] Follow-up implementation task created in the guardkit repo:
      [`TASK-FIX-FD32-uv-bootstrap-command.md`](file:///Users/richardwoollcott/Projects/appmilla_github/guardkit/tasks/backlog/TASK-FIX-FD32-uv-bootstrap-command.md)
      — backlog, complexity 2, scope = one-line code change + comment matrix update + test-argv update + reinstall + cross-repo verification re-run of FEAT-FD32.

### Decision

`[I]mplement` — see follow-up task linked above. This review can be
closed with `/task-complete TASK-REV-FD32` once the user is ready.

## Implementation Notes

_Not applicable — this is a review task. No code changes here._

## Test Execution Log

_Not applicable for review tasks._
