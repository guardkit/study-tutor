# Review Report: TASK-DSP-008

**Task:** Review smoke-gate failure for FEAT-PH1-002 autobuild run
**Mode:** post-mortem (mapped to root-cause / decision analysis)
**Depth:** standard
**Date:** 2026-04-29
**Reviewer:** /task-review (Claude Opus 4.7)

---

## Executive Summary

FEAT-PH1-002 (Deterministic Session Planner) was reported `FAILED` by the
autobuild orchestrator, but **the failure is a misconfigured gate, not a
regression in the planner code**. All six implementation tasks
(TASK-DSP-001..006) were approved by the code reviewer, all five executed
waves passed, and the smoke gate command — when re-run inside the preserved
worktree — exits with **code 5 ("no tests collected")**, deselecting all 391
tests because neither `smoke` nor `feat-ph1-002` is registered as a pytest
marker and no test in `tests/` carries either marker.

**Disposition: PASS-WITH-FOLLOWUP.** Treat the planner work as functionally
complete; create `TASK-DSP-009` to author the smoke tests the gate was always
expecting; file a process-improvement note for GuardKit's `smoke_gates`
module so future exit-5 results are reported as a gate-config gap, not a
test failure.

---

## Review Details

- **Mode:** post-mortem (root cause + disposition)
- **Depth:** standard (~30 min — evidence is concentrated; deep theorizing not needed)
- **Worktree under review:** `.guardkit/worktrees/FEAT-PH1-002/`
- **Smoke command:** `pytest -m "feat-ph1-002 and smoke" -x --no-cov`
- **Reproduction performed:** yes (see Finding 1)

---

## Findings

### Finding 1 — Literal cause: pytest exit 5 / no tests collected (CONFIRMED)

Re-running the exact smoke command inside the preserved worktree reproduces
the failure deterministically:

```
collected 391 items / 391 deselected / 0 selected
=========================== 391 deselected in 0.21s ============================
PYTEST_EXIT=5
```

Pytest exit 5 is documented as **"no tests were collected"** — it is *not*
a test-failure signal. All 391 tests were deselected because the marker
expression `feat-ph1-002 and smoke` matched zero items.

**Hypothesis from the task description is fully confirmed.**

### Finding 2 — Markers `smoke` and `feat-ph1-002` are not registered

`[FEAT-PH1-002.yaml:46-53](../../.guardkit/features/FEAT-PH1-002.yaml#L46-L53)`
defines the smoke gate. The worktree's `pyproject.toml` registers only:

```toml
[tool.pytest.ini_options]
markers = [
    "seam: integration-contract seam tests between GuardKit tasks",
    "integration_contract: marks the specific contract under test (arg: contract name)",
]
```

Neither `smoke` nor `feat-ph1-002` appears. Because pytest's `markers` block
is a closed list, custom marker expressions silently match nothing rather
than warning about unknown markers.

### Finding 3 — No test under `tests/` carries either marker

A grep across the full worktree test tree finds:

- `@pytest.mark.seam` — 8 hits
- `@pytest.mark.integration_contract(...)` — 8 hits
- `@pytest.mark.parametrize`, `@pytest.mark.skipif`, `@pytest.mark.asyncio` — many
- `@pytest.mark.smoke` — **0 hits**
- `@pytest.mark.feat-ph1-002` (or any feature-id marker) — **0 hits**

The single occurrence of the word "smoke" in the worktree tests is a
docstring in `tests/unit/mcp/test_adapter.py:1` ("Smoke tests for MCPAdapter
handler shape (TASK-PO02-005)") — that test does not carry the actual
`@pytest.mark.smoke` decorator and is therefore irrelevant to the gate.

### Finding 4 — No implementation task was asked to author smoke tests

Auditing the acceptance criteria of TASK-DSP-001 through TASK-DSP-006:

| Task | Mentions `smoke`? | Mentions `feat-ph1-002` marker? | Test markers required |
|------|------------------|---------------------------------|-----------------------|
| TASK-DSP-001 | No | No (only as `feature_id` frontmatter) | none specified |
| TASK-DSP-002 | No | No (only as `feature_id` frontmatter) | none specified |
| TASK-DSP-003 | No | No (only as `feature_id` frontmatter) | none specified |
| TASK-DSP-004 | No | No (only as `feature_id` frontmatter) | `@pytest.mark.seam` + `integration_contract` |
| TASK-DSP-005 | No | No (only as `feature_id` frontmatter) | none specified |
| TASK-DSP-006 | No | No (only as `feature_id` frontmatter) | `@pytest.mark.seam` + `integration_contract` |

The string `feat-ph1-002` only appears in each task's frontmatter as the
`feature_id` and `worktree_path` — **never** as a pytest-marker requirement.
The two tasks that call out marker decorators (DSP-004, DSP-006) require
seam/contract markers, which is a different test category from smoke.

**Conclusion:** The smoke-gate config in `FEAT-PH1-002.yaml` was added
without a corresponding "author smoke tests" task — the gate was wired to a
target that never existed. This is an authoring gap in the feature spec, not
a defect in any of the six implementation tasks.

### Finding 5 — All six implementation tasks were independently approved

Per `[review-summary.md](../../.guardkit/autobuild/FEAT-PH1-002/review-summary.md)`
and the orchestrator's per-task `result.final_decision`:

- TASK-DSP-001 → approved (1 turn)
- TASK-DSP-002 → approved (1 turn)
- TASK-DSP-003 → approved (3 turns)
- TASK-DSP-004 → approved (2 turns)
- TASK-DSP-005 → approved (1 turn)
- TASK-DSP-006 → approved (2 turns)

Task success rate: 100%. SDK ceiling hits: 0. Waves 1–5 all PASS. The only
red signal in the entire run is the smoke gate after Wave 5.

### Finding 6 — Orchestrator currently conflates exit 5 with exit 1

The history log records:

```
[autobuild-history:1592]  Smoke gate failed after wave 5 (exit=5, expected=0)
[autobuild-history:1593]  ✗ Smoke gate failed after wave 5 (exit=5, expected=0).
                          Subsequent waves not started; worktree preserved at ...
```

Both exit 5 (no tests collected — *config gap*) and exit 1 (tests collected
and failing — *real regression*) currently produce the same `FAILED` outcome
and the same "subsequent waves not started" effect. From an operational
standpoint these have very different meanings: exit 5 should usually be a
**warning about the gate itself**, while exit 1 is a **stop-the-line signal
about the code under test**.

---

## Disposition

**FEAT-PH1-002 should be considered actually-passing, with one follow-up
required to wire the smoke gate to real tests.**

Justification:

1. 100% task approval, 100% wave success up to and including Wave 5.
2. The single failure signal (smoke gate) does not reflect the planner's
   behavior at all — it reflects the absence of any test that the gate's
   marker expression could select.
3. The implementation tasks were never asked to author smoke tests, so this
   is not a missed acceptance criterion at the task level — it is a missing
   acceptance criterion at the **feature** level.
4. The preserved worktree contains 391 collectable tests, all
   non-smoke-marked. Those tests passed under their own (non-gate) runs
   during each wave's normal Phase 4 testing, which is what produced the
   per-task approvals.

---

## Decision Matrix — Minimum Fix

| Option | What | Score | Effort | Risk | Recommendation |
|--------|------|-------|--------|------|----------------|
| (a) | Add smoke tests + register markers in this task and re-run gate | 6/10 | M | Scope creep — this is a *review* task | ✗ Defer |
| (b) | Remove / relax the smoke-gate config until smoke tests exist | 3/10 | S | Removes a useful insurance gate; encodes the wrong norm | ✗ Reject |
| (c) | Treat as gap-discovery; create `TASK-DSP-009` to author smoke tests; mark feature pass-with-followup | 9/10 | S (this task) + M (follow-up) | Lowest — preserves the gate as a future quality signal and keeps responsibilities separate | **✓ Recommended** |

**Recommendation: Option (c).** This is consistent with the task's own
"Out of Scope" section ("Fixing the gate inside this task — this is a
*review*. Implementation goes into a follow-up task.") and with the
suggested follow-up name in the task body
(`TASK-DSP-009-author-feat-ph1-002-smoke-tests`).

---

## Recommendations

### R1 — Pass FEAT-PH1-002 with followup *(disposition)*

Mark the feature as functionally complete. The autobuild status field
`status: failed` in `[FEAT-PH1-002.yaml:7](../../.guardkit/features/FEAT-PH1-002.yaml#L7)`
should be reconciled with the recommended disposition once the followup
is in place — either flip to `passed` and link to the followup, or
introduce a `passed_with_followup` value if the schema permits.

### R2 — Create `TASK-DSP-009-author-feat-ph1-002-smoke-tests` *(follow-up implementation)*

**Scope of TASK-DSP-009 (draft):**

1. Register the two markers in `pyproject.toml`:
   ```toml
   [tool.pytest.ini_options]
   markers = [
       "seam: ...",
       "integration_contract: ...",
       "smoke: fast end-to-end-ish smoke tests for autobuild gates",
       "feat-ph1-002: tests scoped to the Deterministic Session Planner feature",
   ]
   ```
2. Author **at least one** smoke test that exercises `plan_session` end-to-end
   (e.g. happy-path Rule 1, plus the rule-6 fallback) carrying both
   `@pytest.mark.smoke` and `@pytest.mark.feat-ph1-002`. Place under
   `tests/smoke/test_session_planner.py` (new directory) or extend an existing
   file — implementer's choice.
3. Locally re-run the exact gate command and confirm exit 0 with ≥1 test
   selected.
4. Re-run the autobuild orchestrator's smoke gate (or simulate it) to
   confirm the gate now passes.
5. Update `[FEAT-PH1-002.yaml]` `status` field accordingly.

Acceptance: `pytest -m "feat-ph1-002 and smoke" -x --no-cov` exits 0 with
`selected ≥ 1`.

Estimated complexity: 3. Estimated effort: 30–45 min.

### R3 — File a GuardKit `smoke_gates` enhancement *(process improvement)*

The orchestrator's `smoke_gates` module should distinguish exit 5 from other
non-zero exits when reporting:

- **exit 5 (no tests collected):** report as `GATE_NOT_WIRED` /
  `BLOCKED_CONFIG`. Surface a hint such as
  *"smoke gate matched 0 tests — verify markers are registered and at least
  one test carries the marker expression."* Optionally let this be a soft
  warning rather than a hard fail (configurable per feature).
- **exit 1 (tests failed):** keep current `FAILED` semantics — this is a
  real regression signal.
- **exit 2 / 3 / 4:** keep current handling (collection errors, internal
  errors, etc.).

This change would have routed the FEAT-PH1-002 run to a much clearer
operator message and avoided the misleading `FEATURE RESULT: FAILED`
display when nothing in the planner had actually regressed.

The gate command source-of-truth and the orchestrator failure log are at
`[FEAT-PH1-002.yaml:46-53](../../.guardkit/features/FEAT-PH1-002.yaml#L46-L53)`
and
`[autobuild-FEAT-PH1-002-history.md:1591-1594](../../docs/history/autobuild-FEAT-PH1-002-history.md#L1591-L1594)`
respectively.

### R4 — Add a feature-spec lint *(optional, longer term)*

A static check at feature-spec-load time could verify, for every smoke gate
defined in a feature YAML, that the marker expression resolves to ≥1
collectable test in the worktree before allowing the autobuild run to
start. This would catch the same class of gap one phase earlier (planning,
not Wave-N execution).

---

## Acceptance Criteria Coverage

The task's six acceptance criteria are satisfied as follows:

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Cause confirmed by running exact command in worktree | ✓ Finding 1 — exit 5 / 0 selected reproduced |
| 2 | Marker registration + `@pytest.mark` usage audited | ✓ Findings 2 & 3 — only `seam` / `integration_contract` registered; zero smoke marks |
| 3 | TASK-DSP-001..006 reviewed for smoke acceptance criteria | ✓ Finding 4 — none of the six required smoke tests |
| 4 | Disposition recommendation written with justification | ✓ Disposition section — pass-with-followup |
| 5 | Concrete next-action chosen + follow-up task drafted | ✓ R2 — Option (c), TASK-DSP-009 draft |
| 6 | Note logged for orchestrator (exit-5 vs exit-1) | ✓ R3 — smoke_gates enhancement note |

---

## Decision Options (Phase 5 Checkpoint)

- **[A]ccept** — Approve findings; mark TASK-DSP-008 review_complete; flip
  FEAT-PH1-002 disposition to pass-with-followup.
- **[R]evise** — Request deeper analysis (e.g., trace whether any earlier
  feature in the project has the same pattern, or model the orchestrator
  change in more detail).
- **[I]mplement** — Auto-create implementation task(s) for R2 (smoke tests)
  and optionally R3 (orchestrator note) under
  `tasks/backlog/deterministic-session-planner/`.
- **[C]ancel** — Discard this review.

**Recommended next step:** [I]mplement R2 only (TASK-DSP-009). R3 is a
GuardKit-side change and belongs in the GuardKit project, not study-tutor.

---

## Appendix — Evidence Index

- Reproduced smoke command output: see Finding 1
- `[pyproject.toml — markers block]` (worktree)
- `[FEAT-PH1-002.yaml:46-53](../../.guardkit/features/FEAT-PH1-002.yaml#L46-L53)` — gate config
- `[review-summary.md](../../.guardkit/autobuild/FEAT-PH1-002/review-summary.md)` — 100% task pass
- `[autobuild-FEAT-PH1-002-history.md:1591-1635](../../docs/history/autobuild-FEAT-PH1-002-history.md#L1591-L1635)`
  — gate failure log + wave/task summary
- `[TASK-DSP-001..006]` acceptance criteria — none mention smoke
