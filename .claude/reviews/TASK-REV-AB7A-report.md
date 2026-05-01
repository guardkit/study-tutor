# Diagnostic Review: Failed Autobuild for FEAT-70A4

**Task:** [TASK-REV-AB7A](../../tasks/backlog/TASK-REV-AB7A-analyze-failed-autobuild-feat-70a4.md)
**Mode:** diagnostic | **Depth:** standard
**Generated:** 2026-04-30
**Source artifacts:**
- Transcript: [docs/history/autobuild-FEAT-70A4-failed-history.md](../../docs/history/autobuild-FEAT-70A4-failed-history.md) (869 lines)
- Orchestrator summary: [.guardkit/autobuild/FEAT-70A4/review-summary.md](../../.guardkit/autobuild/FEAT-70A4/review-summary.md)
- Events: [.guardkit/autobuild/FEAT-70A4/events.jsonl](../../.guardkit/autobuild/FEAT-70A4/events.jsonl)
- Feature spec: [.guardkit/features/FEAT-70A4.yaml](../../.guardkit/features/FEAT-70A4.yaml)
- Worktree: `.guardkit/worktrees/FEAT-70A4` (branch `autobuild/FEAT-70A4`, preserved)

---

## Executive Summary

The FEAT-70A4 autobuild **failed at the post-wave-2 smoke gate with exit=127** ("command not found"), halting before any of waves 3–5 could run. Three of seven planned tasks reached "approved" state (PRV-001, PRV-002, PRV-003); four remain unstarted (PRV-004, PRV-005, PRV-006, PRV-007). The worktree is preserved and the feature branch carries five `[guardkit-checkpoint]` commits.

**Two compounding root causes**, both reproducible and both fixable inside this feature spec without touching GuardKit upstream:

1. **Smoke gate invokes bare `python`**, but Ubuntu 24 systems ship only `/usr/bin/python3`. The bootstrap venv at `.guardkit/venv/bin/python` was correctly built and an editable install of `study-tutor` was present, but the smoke-gate hook neither prepends `.guardkit/venv/bin` to PATH nor honours `coach_pytest_interpreter`. **Reproduced locally** during this review (see §1.3).
2. **Wave 2 parallel-contention was real source-file contention, not infrastructure contention.** TASK-PRV-002 (corpus loader) and TASK-PRV-003 (decision function) both wrote step definitions to the same 888-line BDD glue file `features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py`. Their independent test verification failed in ~6.3 s each because the file was inconsistent at the moment of verification. Coach's conditional-approval rule fired and approved both anyway with `requires_infra=[]`, on the (incorrect) assumption that contention implies a transient infra issue.

**Secondary findings:**
- Coach SDK message-reader crashed 5× across the run, but every failure recovered via subprocess fallback; classification = transport, not blocking.
- Both PRV-002 and PRV-003 task files contained explicit `## Seam Tests` sections with code stubs, **but Players skipped them**. Coach correctly flagged "no seam/contract/boundary tests detected" four times. This is the most concerning latent issue — we have approved code whose contract tests were planned, written down, then never implemented or run.

**Recommended path:** [I]mplement a tight 4-task fix feature (smoke-gate interpreter pin, wave-3 serialisation, seam-test backfill, resume autobuild). The seam-test backfill is the load-bearing one — if those tests pass, the conditional approval was a lucky guess; if they fail, we caught real bugs. Resume from wave 3 with the existing worktree intact.

---

## Failure Timeline

| Time (UTC) | Event | Wave | Outcome |
|---|---|---|---|
| 16:38:41 | Bootstrap start | — | OK — venv created at `.guardkit/venv`, editable install via PEP 668 retry |
| 16:38:41 | `coach_pytest_interpreter` set to `.guardkit/venv/bin/python` (transcript line 60) | — | OK |
| 16:38:41 | Wave 1 start: TASK-PRV-001 (Pydantic models) | 1 | 1 turn, approved |
| 16:42:09 | Coach SDK reader fatal error #1 (PRV-001 t1) → subprocess fallback OK | — | Recovered |
| 16:42:17 | Wave 2 start: PRV-002 + PRV-003 in parallel (`worker_count=2`) | 2 | — |
| ~16:50:41 | Coach SDK reader fatal error #2 (PRV-002 t1) → subprocess fallback OK | 2 | Recovered |
| ~16:54:49 | Coach SDK reader fatal error #3 (PRV-003 t1) → subprocess fallback OK | 2 | Recovered |
| ~16:51:00 | PRV-003 turn 2 approved | 2 | Conditional (parallel_contention) |
| ~16:55:09 | PRV-002 turn 2 approved | 2 | Conditional (parallel_contention) |
| 17:02:08 / 17:05:44 | Coach SDK reader fatal errors #4, #5 → subprocess fallback OK | 2 | Recovered |
| 17:06:04 | Wave 2 complete; smoke gate fires | 2→3 | — |
| 17:06:04 | **Smoke gate exit=127 (`python: command not found`)** | — | **HARD FAIL** |
| 17:06:04 | Subsequent waves not started; worktree preserved | — | — |

**Total wall-clock:** 27m 22s. **Tasks completed:** 3/7.

---

## §1. Smoke-Gate Exit=127 — Root Cause

### 1.1 Evidence (from transcript lines 814–820)

```
INFO:guardkit.orchestrator.smoke_gates:Running smoke gate after wave 2: set -e
python -c "from study_tutor.knowledge.corpus_models import CorpusChunk, CitationAnchor, SourceType, PlayCitationAnchor, NovelCitationAnchor"
pytest tests/unit/knowledge/ -x -q
 (cwd=/home/.../FEAT-70A4, timeout=180s, expected_exit=0)
WARNING:guardkit.orchestrator.smoke_gates:Smoke gate failed after wave 2 (exit=127, expected=0)
```

The literal command came directly from `.guardkit/features/FEAT-70A4.yaml:142–151`:

```yaml
smoke_gates:
  after_wave: [2, 3, 4]
  command: |
    set -e
    python -c "from study_tutor.knowledge.corpus_models import CorpusChunk, CitationAnchor, SourceType, PlayCitationAnchor, NovelCitationAnchor"
    pytest tests/unit/knowledge/ -x -q
  expected_exit: 0
  timeout: 180
```

### 1.2 Why exit=127 specifically

- Exit 127 = shell's "command not found" sentinel.
- On Ubuntu 24 (this host), `which python` returns nothing; only `/usr/bin/python3` exists. PEP 394's "python = python2 or python3" stub is no longer installed by default.
- The orchestrator's bootstrap correctly:
  1. Tried `/usr/bin/python3 -m pip install -e .` (transcript line 53).
  2. Hit `error: externally-managed-environment` (PEP 668).
  3. Fell back to creating `.guardkit/venv` (line 54).
  4. Re-ran the editable install inside the venv (line 55) — succeeded (line 56).
  5. Set `coach_pytest_interpreter = .guardkit/venv/bin/python` (line 60).
- **But the smoke-gate executor (`guardkit.orchestrator.smoke_gates`) never propagated that interpreter into the hook subshell.** The bare `python` token in the YAML hit the system PATH (no `python`), not the venv (`.guardkit/venv/bin/python`).

### 1.3 Local reproduction (this review)

I ran the *exact* gate command from a clean shell, in the worktree cwd, with no venv activation:

```
$ /bin/bash -c 'set -e
python -c "from study_tutor.knowledge.corpus_models import ..."
pytest tests/unit/knowledge/ -x -q'
/bin/bash: line 2: python: command not found
```

Then verified the venv copy works:

```
$ .guardkit/venv/bin/python -c "from study_tutor.knowledge.corpus_models import \
    CorpusChunk, CitationAnchor, SourceType, PlayCitationAnchor, NovelCitationAnchor"
$ echo $?
0
```

Editable install confirmed:
- `.guardkit/venv/lib/python3.12/site-packages/study_tutor-0.1.0.dist-info/direct_url.json`:
  `{"dir_info": {"editable": true}, "url": "file:///.../FEAT-70A4"}`
- `_editable_impl_study_tutor.pth` is present, so the venv interpreter resolves the package to `src/study_tutor/`.

**Conclusion:** the package and tests are correct. The gate would have **passed** if invoked through the venv interpreter. This is a gate-config bug, not a code bug.

### 1.4 Fixes (ranked)

| # | Fix | Layer | Effort | Risk | Notes |
|---|---|---|---|---|---|
| 1.A | Edit `FEAT-70A4.yaml` to use `.guardkit/venv/bin/python` and `.guardkit/venv/bin/pytest` literally | feature spec | 5 min | none | Unblocks resume immediately. Recommended for [I]mplement. |
| 1.B | Activate venv first: `source .guardkit/venv/bin/activate && python -c …` | feature spec | 5 min | venv path may not exist on a fresh-restart bootstrap that names it differently | Less robust than 1.A. |
| 1.C | (Upstream) Have `guardkit.orchestrator.smoke_gates` pass `coach_pytest_interpreter` into hook env (PATH prepend, or substitute `python` token) | GuardKit | not in this feature's scope | low | File against guardkit; not blocking 70A4. |

**Recommendation:** apply 1.A as a single-line edit in `FEAT-70A4.yaml` and proceed.

---

## §2. Wave-2 Parallel Contention — Root Cause

### 2.1 What the orchestrator saw

Lines 676–680 (PRV-003) and 760–764 (PRV-002) — *identical* phrasing for both tasks:

```
WARNING: Independent test verification failed for TASK-PRV-003 (classification=parallel_contention, confidence=high)
INFO:    conditional_approval check: failure_class=parallel_contention, confidence=high,
         requires_infra=[], docker_available=True, all_gates_passed=True, wave_size=2
WARNING: Conditional approval for TASK-PRV-003: parallel contention failure (wave_size=2),
         all Player gates passed. Continuing to requirements check.
INFO:    Seam test recommendation: no seam/contract/boundary tests detected …
WARNING: Coach conditionally approved TASK-PRV-003 turn 2: infrastructure-dependent,
         independent tests skipped
```

Independent verification command (both tasks):
```
pytest features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py \
       tests/unit/knowledge/test_corpus.py \
       tests/unit/knowledge/test_retrieval.py -v --tb=short
```
Both runs failed in ~6.3 s. The transcript captures only the classification, not the failing assertions.

### 2.2 Why this is **not** infrastructure contention

The first hint is `requires_infra=[]` in the rule firing — there is no FalkorDB, no embedder, no shared port between PRV-002 and PRV-003 in this feature. The corpus loader (PRV-002) is pure-Python file I/O against a `tmp_path` fixture; the decision function (PRV-003) is pure-Python control flow with a stubbed `has_primary_text` lookup.

The actual shared resource is a **source file**:
- `features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py` (888 lines on disk now).
- Its own docstring (read during this review) declares:
  > **Step definitions for @task:TASK-PRV-002**: 7 corpus-loader scenarios …
  > **Step definitions for @task:TASK-PRV-003**: 5 retrieval-decision scenarios …
- Both tasks were instructed by the BDD plan to add their respective step defs to **this same module**.
- Both tasks ran in parallel against the **same worktree on the same branch** — the autobuild orchestrator does not branch-per-task within a wave.
- Git log on the file shows two `[guardkit-checkpoint] Turn 1 complete` commits (for PRV-002 and PRV-003) and two `Turn 2 complete` commits, all on `autobuild/FEAT-70A4` — they raced into the same file and one's writes overwrote/preceded the other's.
- The combined `pytest features/.../test_*.py tests/unit/knowledge/...` invocation collected step defs from *whatever the file looked like at that instant*. If PRV-002's commit landed last, PRV-003's step defs were missing, and pytest-bdd raised undefined-step errors. Vice-versa for PRV-002.
- The Player's *own* gates passed because each Player only ran its own task-scoped subset and committed to its own checkpoint, but the cross-task independent verification picked up the merged-but-inconsistent file state.

### 2.3 Cross-cutting evidence

- Coach `bdd_runner` is path-based (collects `.feature` and bridges to the sibling `test_<slug>.py` via `features/conftest.py` — the docstring even calls this out as the cause of a "previous turn" failure for PRV-003 t1).
- The conftest pattern guarantees that any feature with @task tags spread across multiple parallel tasks will share one `test_<slug>.py` glue module.
- This is therefore **structural** for any feature whose `/feature-plan` puts multiple tasks behind one BDD feature file — not specific to FEAT-70A4.

### 2.4 Fixes (ranked)

| # | Fix | Scope | Effort | Risk | Notes |
|---|---|---|---|---|---|
| 2.A | Serialise wave 2 in `FEAT-70A4.yaml`: split `[[PRV-002, PRV-003]]` into `[[PRV-002], [PRV-003]]` | feature spec | 5 min | adds ~5 min wall-clock to the run | Only matters at *resume* if rerunning; for the resume-from-wave-3 path, apply same to wave 3 (`[PRV-004, PRV-005]`) and wave 4 if any share a glue module. |
| 2.B | Backfill the planned seam tests for PRV-002 and PRV-003 (already authored as code stubs in their task files) and run them locally before resume — confirms whether the conditionally-approved code is actually correct | code | 30–45 min | none — purely additive | **Load-bearing.** If these tests pass, conditional approval was acceptable; if any fail, we have a real bug to fix before wave 3. |
| 2.C | Split BDD glue per task: have `/feature-plan` emit `test_<slug>__<task>.py` per parallel task | upstream guardkit / planner | not in scope | medium | File against guardkit; not blocking 70A4. |
| 2.D | Tighten conditional-approval rule: when `requires_infra=[]` AND `classification=parallel_contention`, require either serialised retry OR seam-test pass before approving | upstream guardkit | not in scope | low | File against guardkit. |

**Recommendation:** apply 2.A (serialise wave 3 onward in this feature) AND 2.B (backfill seam tests for PRV-002 and PRV-003) before resuming.

---

## §3. Conditional-Approval Rule — Fitness for FEAT-70A4

The current rule, paraphrased from the transcript firing:
> If a task fails independent test verification, and the failure is classified `parallel_contention` with high confidence, and all Player gates passed, and `wave_size > 1` — approve, skip independent tests, continue.

**Verdict for FEAT-70A4: tightening recommended, but this is an upstream concern.**

The rule was written for a different scenario: tasks that share a stateful service (FalkorDB, vector store, port-bound dev server). In those cases, parallel runs *do* produce non-deterministic test failures that resolve under serialised retry. The rule is correct for that case.

It is **wrong** for the case observed here, where the contended resource is a source file under the worktree's own `features/` tree. That is a genuine concurrent-write conflict; serialised retry would have caught it; conditional approval did not.

The signal the rule was missing: `requires_infra=[]`. With no declared infra dependency, "parallel contention" is far more likely to be source-file contention or test-fixture contention — neither of which is benign.

| Disposition | Rationale |
|---|---|
| **Keep rule for upstream features that declare infra** | Reasonable behaviour where retry is expensive and contention is provably transient. |
| **Tighten when `requires_infra=[]`** | Recommend: when classification = parallel_contention AND requires_infra=[], do NOT auto-approve — instead trigger one serialised retry of the *failing* task only. |
| **(local) Workaround for FEAT-70A4** | Serialise wave 2/3/4 in the feature spec (§2.4 fix 2.A) — sidesteps the rule entirely for this feature. |

This finding is filed for the upstream backlog; it is **not** in scope for an FEAT-70A4 fix feature.

---

## §4. Coach SDK Reader Fatal Errors — Frequency & Classification

5 occurrences across 27m 22s, all with the same signature:
```
Fatal error in message reader: Command failed with exit code 1
WARNING: SDK test execution failed (error_class=Exception), falling back to subprocess.
```

| # | Line | Time | Task / Turn | Recovery |
|---|---|---|---|---|
| 1 | 143 | 15:42:09 | PRV-001 t1 | Subprocess fallback OK |
| 2 | 422 | 15:50:41 | PRV-002 t1 | Subprocess fallback OK |
| 3 | 517 | 15:54:49 | PRV-003 t1 | Subprocess fallback OK |
| 4 | 669 | 16:02:08 | PRV-003 t2 | Subprocess fallback OK |
| 5 | 753 | 16:05:44 | PRV-002 t2 | Subprocess fallback OK |

**Pattern:** every Coach SDK invocation that ran a pytest subprocess hit the error on first attempt; every fallback succeeded. There is one failure per Coach test gate, perfectly correlated with the SDK transport boundary.

**Classification: TRANSPORT.** This is the Claude Agent SDK's message-reader subprocess crashing on an exit-1 path inside the SDK harness, not a study-tutor or test failure. Two pieces of evidence support this:
1. The error is identical across five completely different test commands (different cwds, different test files).
2. Every fallback succeeds when the same test command is re-run via plain subprocess — proving the test command itself is fine.

**Action:** not blocking, file upstream against guardkit / Claude Agent SDK. Subprocess fallback is doing exactly what it's supposed to. No FEAT-70A4 work item.

---

## §5. Seam-Test Gap

Coach validator flagged 4× during the run:
> `Seam test recommendation: no seam/contract/boundary tests detected for cross-boundary feature.`

The Coach heuristic is correct — but the more interesting fact is that **both task files explicitly planned seam tests with full code stubs**, and the Players ignored them.

| Task | Seam test planned in task file? | Test file expected | Implemented? |
|---|---|---|---|
| TASK-PRV-001 | Implicit (covered by `tests/unit/knowledge/test_seam_pydantic_entities.py`, present on disk) | ✓ | ✓ |
| TASK-PRV-002 | Yes — full stub at `tasks/backlog/.../TASK-PRV-002-source-typed-corpus-loader.md:164–207` (`test_corpus_chunk_carries_typed_citation_anchor`) | `tests/unit/knowledge/test_*seam*.py` or pytest marker `seam`/`integration_contract` | **No** — not in worktree's `tests/unit/knowledge/` listing |
| TASK-PRV-003 | Yes — full stub at `tasks/backlog/.../TASK-PRV-003-retrieval-decision-function.md:152–184` (`test_should_retrieve_returns_named_tuple_contract`) | Same | **No** |

The Players for both tasks chose to write their unit tests + BDD glue and skip the explicit `## Seam Tests` section. The Coach validator's heuristic for detecting seam tests (likely a `@pytest.mark.seam` or `*seam*.py` filename match) didn't find them — correctly — and it warned but did not block.

This is the most concerning finding of the review. The Coach approved code whose contract tests were planned, written down in spec, then never implemented or run, in a wave where parallel contention also blocked independent verification. **We have no positive evidence the conditionally-approved PRV-002 and PRV-003 implementations meet the contracts that PRV-004, PRV-005, PRV-006 will consume.**

**Concrete amendments:**

1. **TASK-PRV-002 backlog amendment:** add an explicit deliverable line: "Seam test from §Seam Tests of this task file is implemented in `tests/unit/knowledge/test_seam_corpus_loader.py` and passes with `pytest -m seam`". Same for **TASK-PRV-003** at `tests/unit/knowledge/test_seam_retrieval_decision.py`.
2. **(Upstream)** Coach validator should *block* (not warn) when a task file's `## Seam Tests` section contains a stub but no matching `@pytest.mark.seam` test was written. Detection signal: presence of `## Seam Tests` heading in task file + zero `@pytest.mark.seam` collections in the worktree. File upstream.
3. **(Upstream)** Player implementation prompt should include task `## Seam Tests` content as a non-skippable requirement. File upstream.

---

## §6. Resume Strategy

The worktree at `.guardkit/worktrees/FEAT-70A4` is intact on branch `autobuild/FEAT-70A4`. Five `[guardkit-checkpoint]` commits carry the PRV-001/002/003 work. The package is editable-installed in `.guardkit/venv`.

| Strategy | Pros | Cons | Verdict |
|---|---|---|---|
| **A: Resume from wave 3 (with fixes)** | Saves 27m of completed work; smoke-gate fix is one-line; seam-test backfill verifies conditional approvals were sound. | Inherits parallel-contention risk in wave 3 (PRV-004 + PRV-005 share the same BDD glue file). | **Recommended** — provided wave-3 is serialised (§2.4 2.A) and seam tests pass (§2.4 2.B). |
| **B: Fresh restart (with fixes)** | Clean slate; no risk of latent bug in conditionally-approved code. | Wastes 27m + cost; PRV-002/003 will likely produce *the same code*, since the spec is unchanged. | Only if seam-test backfill (§2.4 2.B) reveals real bugs in PRV-002/003. |
| **C: Hybrid** | Run seam tests now → branch on outcome: pass → strategy A; fail → strategy B for the affected task only. | Minor extra coordination. | **Optimal.** This is what the [I]mplement subtask list below encodes. |

---

## §7. Risk-Ranked Fix List

| Rank | ID | Fix | Effort | Risk if skipped | Layer |
|---|---|---|---|---|---|
| **P0** | FIX-AB7A-001 | Pin smoke gate to `.guardkit/venv/bin/python` and `.guardkit/venv/bin/pytest` in `FEAT-70A4.yaml` | 5 min | Resume blocks at wave 3 with same exit=127 | feature spec |
| **P0** | FIX-AB7A-002 | Backfill seam tests for PRV-002 and PRV-003 (stubs already in task files); run them locally before resume | 30–45 min | We resume on potentially broken contracts; PRV-004/005/006 fail downstream with hard-to-localise errors | code (worktree) |
| **P1** | FIX-AB7A-003 | Serialise waves 3 and 4 in `FEAT-70A4.yaml` orchestration.parallel_groups (wave 3 = PRV-004 then PRV-005; wave 4 = PRV-006 alone) | 10 min | Wave 3 hits the same shared-BDD-glue contention, conditional approval re-fires, seam tests still missing | feature spec |
| **P1** | FIX-AB7A-004 | Resume autobuild: `guardkit autobuild feature FEAT-70A4 --resume` | ~25 min wall-clock | Feature stays half-done | run |
| **P2** | (upstream) | File guardkit issues for: smoke_gates interpreter resolution, conditional-approval rule when `requires_infra=[]`, seam-test detection blocking, parallel-edit overlap detection in planner | 30 min | Pattern repeats on the next feature | upstream guardkit |

Total local effort to unblock FEAT-70A4: **~50 min of edits + ~25 min wall-clock of autobuild = ~75 min** vs. the 27 min already spent.

---

## §8. Subtasks for [I]mplement (if chosen)

If you choose **[I]mplement** at the decision checkpoint, the following subtask list is ready to feed into `/feature-plan` as `FEAT-FIX-AB7A`:

1. **TASK-FIX-AB7A-001** — Pin smoke-gate interpreter (P0, complexity 1, ~5 min)
   - Edit `.guardkit/features/FEAT-70A4.yaml:142–151`: replace bare `python` and `pytest` with `.guardkit/venv/bin/python` and `.guardkit/venv/bin/pytest`.
   - Verify: run the gate locally from a clean shell — must exit 0.
   - Single file, no parallelism.

2. **TASK-FIX-AB7A-002** — Backfill seam test for TASK-PRV-002 (P0, complexity 2, ~20 min)
   - Implement the stub from `tasks/backlog/primary-text-rag-and-quote-verifier/TASK-PRV-002-source-typed-corpus-loader.md:170–207` at `tests/unit/knowledge/test_seam_corpus_loader.py`.
   - Mark with `@pytest.mark.seam` and `@pytest.mark.integration_contract("SourceTypedCorpus")`.
   - Run inside worktree venv: `.guardkit/venv/bin/pytest -m seam tests/unit/knowledge/test_seam_corpus_loader.py`.
   - Acceptance: passes; if it fails, escalate to a code fix subtask before resume.

3. **TASK-FIX-AB7A-003** — Backfill seam test for TASK-PRV-003 (P0, complexity 2, ~20 min)
   - Mirror of 002 against `tasks/backlog/.../TASK-PRV-003-retrieval-decision-function.md:158–184` at `tests/unit/knowledge/test_seam_retrieval_decision.py`.
   - Acceptance same as 002.
   - **Parallelisable with FIX-AB7A-002** (different files, no shared BDD glue).

4. **TASK-FIX-AB7A-004** — Serialise waves 3+ in feature spec (P1, complexity 1, ~10 min)
   - Edit `.guardkit/features/FEAT-70A4.yaml:127–135` `orchestration.parallel_groups` to: `[[PRV-001], [PRV-002, PRV-003], [PRV-004], [PRV-005], [PRV-006], [PRV-007]]` — wave 3 onward becomes serial.
   - Optional: keep wave 2 as-is since PRV-002/003 are already approved; this only affects the unstarted waves.

5. **TASK-FIX-AB7A-005** — Resume autobuild (P1, complexity 1, run-only)
   - `guardkit autobuild feature FEAT-70A4 --resume`
   - Acceptance: smoke gate after wave 3 passes; PRV-004/005/006/007 reach approved; final smoke gate passes.

**Execution waves for the fix feature:**
- Wave 1: FIX-AB7A-001 (alone)
- Wave 2: FIX-AB7A-002 + FIX-AB7A-003 (parallel — different test files, no glue conflict)
- Wave 3: FIX-AB7A-004 (alone)
- Wave 4: FIX-AB7A-005 (run-only)

---

## §9. Out-of-Scope (filed for upstream guardkit)

These are real findings but belong upstream, not in FEAT-70A4 or its fix feature:

- **GK-UPSTREAM-1:** `guardkit.orchestrator.smoke_gates` should honour `coach_pytest_interpreter` (or PATH-prepend the bootstrap venv `bin/`).
- **GK-UPSTREAM-2:** Conditional-approval rule should NOT auto-approve when `classification=parallel_contention` AND `requires_infra=[]`. Recommend serialised retry of the failing task instead.
- **GK-UPSTREAM-3:** `/feature-plan` should detect parallel-task source-file overlap (especially shared BDD glue under `features/<slug>/test_*.py`) and emit a planner warning.
- **GK-UPSTREAM-4:** Coach validator should BLOCK (not warn) when a task file's `## Seam Tests` section is non-empty but no `@pytest.mark.seam` tests are collected from the worktree.
- **GK-UPSTREAM-5:** Coach SDK message-reader transport hits `Command failed with exit code 1` 1× per pytest gate. Investigate; subprocess fallback works but the noise is non-zero cost.

---

## §10. Decision Options

| Option | What it does |
|---|---|
| **[A]ccept** | Mark TASK-REV-AB7A as REVIEW_COMPLETE. Findings filed; no implementation triggered. Worktree remains preserved; you'd have to apply fixes manually. |
| **[I]mplement** | Spawn `FEAT-FIX-AB7A` at `tasks/backlog/feat-fix-ab7a/` with the 5 subtasks in §8. After fix-feature completes, run `guardkit autobuild feature FEAT-70A4 --resume` (this is FIX-AB7A-005). |
| **[R]evise** | Deepen analysis on a specific surface — likely candidates: (i) actually run PRV-002/003 seam tests *now* and re-enter [I] with definitive pass/fail evidence, or (ii) ask GuardKit upstream maintainers about smoke-gate interpreter handling before designing the local fix. |
| **[C]ancel** | Discard review, return TASK-REV-AB7A to backlog. Not recommended — the diagnosis is settled. |

**Recommendation: [I]mplement** — diagnostics are settled, fix surface is small, and we keep 27m of completed work intact.

---

## Appendix A — Smoke-Gate Reproduction (verbatim)

Commands run in this review session inside the preserved worktree:

```
$ pwd
/home/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-70A4

$ /bin/bash -c 'set -e
python -c "from study_tutor.knowledge.corpus_models import CorpusChunk, CitationAnchor, SourceType, PlayCitationAnchor, NovelCitationAnchor"
pytest tests/unit/knowledge/ -x -q'
/bin/bash: line 2: python: command not found
EXIT=127

$ .guardkit/venv/bin/python -c "from study_tutor.knowledge.corpus_models import \
    CorpusChunk, CitationAnchor, SourceType, PlayCitationAnchor, NovelCitationAnchor"
$ echo $?
0

$ which python
(empty — not installed)

$ which python3
/usr/bin/python3
```

## Appendix B — Editable Install Verification

```
$ cat .guardkit/venv/lib/python3.12/site-packages/study_tutor-0.1.0.dist-info/direct_url.json
{"dir_info": {"editable": true},
 "url": "file:///home/.../.guardkit/worktrees/FEAT-70A4"}

$ ls .guardkit/venv/lib/python3.12/site-packages/study_tutor-0.1.0.dist-info/
INSTALLER  METADATA  RECORD  REQUESTED  WHEEL  direct_url.json  entry_points.txt  licenses
```

## Appendix C — Files Touched by Wave 2

Both PRV-002 and PRV-003 wrote to:
- `features/primary-text-rag-and-quote-verifier/test_primary_text_rag_and_quote_verifier.py` (888 lines, shared BDD glue — root cause of contention)

PRV-002 also wrote:
- `src/study_tutor/knowledge/corpus.py` (loader implementation)
- `tests/unit/knowledge/test_corpus.py` (unit tests)

PRV-003 also wrote:
- `src/study_tutor/knowledge/retrieval.py` (decision function)
- `tests/unit/knowledge/test_retrieval.py` (unit tests)

Neither wrote:
- `tests/unit/knowledge/test_seam_corpus_loader.py` (planned for PRV-002, missing)
- `tests/unit/knowledge/test_seam_retrieval_decision.py` (planned for PRV-003, missing)
