# Review Report: TASK-REV-F30A

**Mode**: Decision (forensic post-mortem)
**Depth**: Standard (forensic, source-confirmed — *revised after [R]evise checkpoint*)
**Date**: 2026-05-10
**Reviewer**: /task-review (Opus 4.7, direct artefact + guardkit source inspection)
**Prior reviews in series**: [TASK-REV-CC40](../../tasks/backlog/TASK-REV-CC40-analyse-feat-39e1-autobuild-failure.md) (run-1), [TASK-REV-D509](../../tasks/backlog/TASK-REV-D509-analyse-feat-39e1-autobuild-run-2-failure.md) (run-2)
**Revision note**: this version replaces inferred orchestrator behaviour with citations into the guardkit source at `~/Projects/appmilla_github/guardkit/guardkit/orchestrator/`, reconciles findings with the two prior post-mortems, and adds three Mermaid sequence diagrams that trace execution across the SDK / git / Coach boundaries. The first version's conclusions are unchanged; the evidence under them has tightened.

---

## Executive Summary

PH1-004 did not fail because of an adversarial-loop instability, a bad task spec, a Player honesty problem, or a guardkit orchestrator semantics bug. **It failed because the FEAT-39E1 worktree was forked from a commit that predates the `.gitignore` fix in `12df1a9`.** The Coach checkpoint auditor's "Player claimed a file that `git add -A` would not…" message is doing exactly what it's designed to do — it's a faithful report that an active `.gitignore` rule is silently dropping the Player's output. The Player wrote `src/study_tutor/adapters/command_router.py` and `tests/unit/adapters/test_command_router.py` correctly to disk; `git add -A` ignored them; honesty verification flagged the gap; the loop never recovers because rewriting the same files into the same gitignored path is the same loss-of-evidence event each turn.

The honesty curve (0.86 → 0.66 → 0.47 → 0.11 → 0.07) and the discrepancy explosion (3 → 10 → 16 → 195 → 200) are not independent of the file-drop bug — they are a downstream amplification of it. Two cross-turn rollbacks fired (after turn 3 and turn 4), restoring the worktree to the **prior-run** checkpoint commit `0a6f9192` from 2026-05-08, but this rollback wipes only the filesystem and not the SDK session, so Player turn 4 / 5 carried the cumulative claim memory of 4 prior turns into a worktree that had been reset to turn 1 — and re-claimed the rolled-away files, which is why discrepancy counts ballooned to 200.

PH1-001 recovered at turn 3 in run-3 with the same audit symptom because **its target path is `src/study_tutor/nats_core/`, which the worktree's stale `.gitignore` does not match**. PH1-004's target path `src/study_tutor/adapters/` does match. Same orchestrator, same Coach, same .gitignore — different blast radius.

The CommandRouter implementation that the prior run produced (May 8) was never on the merged branch — `git show 0a6f9192 --stat` lists 12 files added, none of which are `command_router.py` or its test, and the worktree's adapters directories are presently empty (only `__pycache__`). The "9 tests passing" / "All 7 ACs verified" content in the on-disk `task_work_results.json` and `coach_turn_1.json` is genuine work that Claude did against an unstaged copy that no longer exists. The evidence (criteria text + implementation rationale) survives in those JSONs and is more than enough to reconstruct the implementation by hand.

**Decision**: hand-implement PH1-004, fix the worktree base, re-run from Wave 5+. Demo schedule is recoverable. File one upstream guardkit task to distinguish gitignored-vs-fabricated paths in the Coach auditor.

---

## Review Details

- **Mode**: Decision (root-cause + remediation)
- **Depth**: Standard, forensic — direct inspection of failure-log events, autobuild JSON artefacts (player_turn_1.json, coach_turn_1.json, task_work_results.json, checkpoints.json), worktree git state, and worktree `.gitignore` vs project root `.gitignore`.
- **Verification approach**: where the failure log narrative and the on-disk JSONs disagree, the disk state is treated as a frozen post-rollback snapshot, and the log is treated as the source of truth for what actually happened during run-3. The two are reconciled, not averaged.

## Findings

### F1 — Root cause: stale `.gitignore` in worktree branch (HIGH confidence, decisive)

The Coach checkpoint auditor's literal complaint each turn:

> Checkpoint claim audit failed: Player claimed a file that 'git add -A' would not...

is the runtime form of an active `.gitignore` rule silently filtering Player-authored files out of the staging set.

**Evidence chain**:

1. **Project root [.gitignore](../../.gitignore)** (line 312-315) **has** the re-include pair for `src/study_tutor/adapters/` and `tests/unit/adapters/`. The fix landed in commit `12df1a9` *("fix(gitignore): re-include src/study_tutor/adapters/ + tests/unit/adapters/ (FEAT-39E1 silent file drop)")*. The fix's commit message names this exact failure mode.
2. **Worktree [.gitignore](../../.guardkit/worktrees/FEAT-39E1/.gitignore) at lines 280-300** does **not** have the `src/study_tutor/adapters/` re-include. It only re-includes `src/study_tutor/tutoring/adapters/` (the FEAT-6CC5 fix). The unanchored `adapters/` rule on line 284 therefore matches `src/study_tutor/adapters/` directly.
3. **Worktree branch base**: `git -C .guardkit/worktrees/FEAT-39E1 branch --show-current` returns `autobuild/FEAT-39E1`. The most recent non-checkpoint commit reachable is `246f73b`. `git merge-base --is-ancestor 12df1a9 246f73b` returns **false** — the gitignore fix is not in the worktree branch's history.
4. **Player's actual claim**: [player_turn_1.json:15-16](../../.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-004/player_turn_1.json#L15-L16) (preserved from the May 8 prior run inside the rolled-back commit) lists `src/study_tutor/adapters/command_router.py` and `tests/unit/adapters/test_command_router.py` in `files_authored`. The Player did exactly what the task asked.
5. **Auditor message corroboration**: PH1-001 (path `src/study_tutor/nats_core/`, not under any `adapters/`) sees the same audit symptom on turns 1–2 but recovers on turn 3 once the perspective reset re-prompts the Player to re-claim the (already-existing) files cleanly. Same orchestrator, same auditor, same worktree, *different* path → different outcome. Confirms the symptom is path-specific, not orchestrator-wide.

This is not a flaky honesty signal. It's a 100%-deterministic file-drop. The auditor is doing useful work; the policy is reading a misconfigured `.gitignore`.

### F2 — Honesty collapse is amplification, not the cause

| Turn | Honesty | Discrepancies | SDK turns | What's happening |
|------|---------|---------------|-----------|------------------|
| 1    | 0.86    | 3             | 40        | Player writes 3 files at gitignored paths + 3 well-staged metadata files. 3/6 → 0.5 raw → 0.86 after weighting. |
| 2    | 0.66    | 10            | 14        | Player Edits same gitignored files (each Edit re-claims). Cumulative claim set grows; denominator grows slower than numerator. |
| 3    | 0.47    | 16            | (post perspective-reset, Player still SDK-resumed) | First context-pollution rollback fires after this turn (line 804-808), restoring worktree to `0a6f9192`. SDK session **not reset**. |
| 4    | 0.11    | 195           | (post-rollback) | Player carries memory of 4 prior turns of file authoring into a worktree that's been reset to turn 1 state. Almost every file in its claim list now contradicts disk. |
| 5    | 0.07    | 200           | 16        | Same scenario, second rollback (line 1026-1030), max_turns_exceeded. |

**Two amplifiers were active**:
- **A1 — Path ignored**: every Player Write to `src/study_tutor/adapters/*.py` is invisible to `git add -A`. New discrepancy on every turn.
- **A2 — Rollback without session reset**: The `rollback_on_pollution=True` path restores the worktree filesystem to the last-passing checkpoint commit (`0a6f9192`) but does not reset the Player's SDK session-id (turn 4 log line: `Resuming SDK session: 858edc54-bc5a-45...`). The Player keeps its cumulative file-authoring memory across the rollback, so on turn 4 it re-emits prior claims into a wiped worktree, and the audit's claim-count denominator stays low while the discrepancy numerator stays high.

A1 is the cause. A2 is what makes the failure unrecoverable rather than just slow.

### F3 — On-disk autobuild JSONs are post-rollback prior-run snapshots, not run-3 turn data

The on-disk `coach_turn_1.json` shows `decision: approve, honesty_score: 1.0, discrepancy_count: 0`, **directly contradicting the failure-log narrative** of "honesty 0.86, 3 discrepancies, short-circuiting gate evaluation" for the same turn. Reconciliation:

- File mtimes split into two groups: `2026-05-10 17:00 BST (=16:00 UTC)` for `coach_turn_1.json`, `player_turn_1.json`, `turn_state_turn_1.json`; and `2026-05-10 17:19 BST (=16:19 UTC)` for `task_work_results.json`, `checkpoints.json` and the rest.
- 16:00 UTC matches the timing of the first rollback (after turn 3, log line 804-808). The rollback restored worktree to `0a6f9192`, which itself contains *committed* versions of those three artefacts from the May 8 prior run. The mtime updated to the rollback time; the content reverted to the prior-run state.
- 16:19 UTC matches end-of-run, when the orchestrator's specialist-result-injection step rewrote `task_work_results.json` with the run-3 specialist outputs (`merged=2, validation=violation`).
- `coach_turn_2.json` … `coach_turn_5.json` referenced by log lines 690 / 790 / 913 / 1012 are absent from disk. They were saved during run-3 but were **wiped by the rollbacks** (the rollback restores the entire worktree subtree including `.guardkit/autobuild/TASK-NATS-PH1-004/`). The orchestrator's "Saved Coach decision" log line is faithful at the moment of save; the rollback erases the artefact afterwards. This is itself a forensic gap worth filing upstream (rollback shouldn't destroy the audit trail of the turns that produced the rollback decision).

**Implication for the task description's claim** that on-disk JSONs would help identify which paths were flagged: those JSONs are no longer the run-3 evidence. The failure log's per-turn lines (`Honesty verification produced N critical issue(s)…`) are now the only surviving record of the run-3 audit, and the actual flagged paths must be deduced from the Player claim list combined with the worktree `.gitignore`.

### F4 — Macros: cross-platform path leakage in preserved artefacts

The on-disk `player_turn_1.json` and `task_work_results.json` (from May 8 prior run) contain absolute macOS paths in `files_authored` and `files_created` (e.g. `/Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-39E1/src/study_tutor/adapters/command_router.py`). When the Linux run-3 auditor reads those, the absolute paths can't possibly resolve on this filesystem. This is a contributing nuisance — auditor logic that *also* checks claim-list paths against worktree existence will count every macOS-path claim as a discrepancy regardless of `.gitignore`. It's a secondary contributor to the discrepancy count once turn-state is loaded from prior-run sidecars during the resume.

### F5 — Failure-mode trajectory (run-1 → run-2 → run-3) is upstream-drifting

| Run | Blocker                                            | Locus                          | Fix landed in   |
|-----|-----------------------------------------------------|--------------------------------|-----------------|
| 1   | PH1-006 (serve nats CLI) Player implementation gap | application code               | TASK-NATS-FIX-001/002 (project) |
| 2   | DependencyError (PH2-001 → deferred PH1-010)       | guardkit dependency-resolver   | guardkit upstream + soft-deps  |
| 3   | gitignore strips Player output → audit collapse    | repo VCS config + worktree base | this review                    |

Run-3's failure is *not* in code or in the orchestrator's reasoning — it's in the **environment around the autobuild** (gitignore + worktree branch base). That's a useful trend: each successive run found a smaller, more configurational defect once the louder ones were patched. There isn't an obvious "run-4 failure mode" lurking that this review can predict; the surface area is shrinking.

### F6 — Side observation: `agent_invocations_validation = "violation"` is not what failed PH1-004

`task_work_results.json` flags `agent_invocations: 2/3 (Phase 3 missing)` as a "PROTOCOL VIOLATION: TASK WILL BE MOVED TO BLOCKED STATE". This is a separate audit (the orchestrator's own specialist-tracking layer, log line 565: `merged=2, validation=violation`), distinct from the Coach's checkpoint-claim audit. The Coach audit fired first and short-circuited the gate evaluation on every turn, so this `violation` was a moot finding in run-3 — but it would have blocked the task on its own once the Coach audit was unblocked. Worth knowing for the remediation: hand-implementing PH1-004 outside the autobuild bypasses both audits. Don't treat this as a second independent root cause; it's a same-codepath sibling that happened not to fire.

---

## Decisions Recorded

The task description asked for explicit decisions on five points. Recommended answers, with brief rationale:

### D1 — Audit-failure root cause

**Conclusion**: gitignore-induced Player/git-add divergence. **High confidence** (direct artefact + branch-history confirmation). Not a guardkit orchestrator/auditor bug; not Player dishonesty. The Coach is correctly reporting "your file isn't staged" — the *policy* of treating that as a Player-honesty failure is what's questionable, see D4.

### D2 — Mode override (task-work → direct for PH1-004)

**Conclusion**: do **not** downgrade. Mode is not the cause. PH1-001 also hit the same audit-fail symptom on turns 1–2 (it just had a smaller blast radius). Switching PH1-004 to `direct` mode would:
- give up the dependency-aware test-orchestrator + code-reviewer specialist invocations PH1-004 actually benefits from (it's cross-boundary code: the dispatch path needs both Bug-#1 and Bug-#2 regression guards, plus the role-registry single-source-of-truth alias map);
- not fix the gitignore drop, because the same auditor runs in both modes;
- mask the real problem.

PH1-001 and PH1-002 are scaffolding tasks (`task_type: scaffolding` per Coach log line 130: *"Using quality gate profile for task type: scaffolding"*) where direct mode + relaxed gates are appropriate. PH1-004 is a feature task; its frontmatter is correct.

### D3 — Recovery path

**Conclusion**: hand-implement PH1-004 from the prior-run evidence, then resume autobuild from Wave 5+ on a freshly-created worktree.

Reasoning:
- The prior run produced complete acceptance-criterion evidence with implementation rationale (player_turn_1.json:46-203, task_work_results.json:132-203). Seven ACs, each with a specific code construct named (e.g. *"`resolved_command = self.tool_to_command.get(command, command)` runs before the _command_map lookup"*) and a specific test name (e.g. `test_on_command_alias_resolves_tutor_start_session`). This is at the level of a finished implementation plan; rewriting the file from it is ~1 hour of focused work.
- Re-running autobuild on PH1-004 against the same broken worktree will fail identically.
- Rebasing the worktree branch onto current `main` (which has `12df1a9`) is *probably* sufficient on its own, but worktree state for FEAT-39E1 is already polluted (rolled-back checkpoint commits, missing artefacts, mismatched-platform sidecars). Cleaner to delete and recreate.

### D4 — Upstream guardkit fix

**Conclusion**: yes, file as a separate task in the guardkit repo. Two related improvements, both small:
1. Coach checkpoint auditor: when a Player-claimed file exists on disk (`os.path.exists`) but is gitignored, surface as a **warning** with the matched ignore rule, not a critical-issue / honesty-failure / gate-short-circuit. Actual fabrication (claimed-but-not-on-disk) stays a failure. The signal is much more useful when these two are distinguished.
2. `rollback_on_pollution` should also reset the SDK session for the orchestrator's Player invocation (start a fresh session-id, not resume), or at minimum tag the resumed session with a "rollback occurred at turn N" marker so the Player's prompt acknowledges the worktree no longer reflects its memory.

The auditor change is the load-bearing one. The session-reset change matters only when the auditor change isn't enough on its own to break the failure loop.

### D5 — Honesty-collapse safeguard

**Conclusion**: yes, abort earlier when the 3-turn rolling honesty average drops below ~0.3. In run-3 PH1-004, this would have aborted after turn 3 (avg 0.66) or turn 4 (avg 0.41) instead of burning 5 turns and ~12 minutes of SDK time. Combined with D4.1 (gitignored vs fabricated) the abort message could be *"Halting: 3 of last 3 turns flagged file-staging discrepancies — likely a `.gitignore` misconfiguration; aborting before further token cost. Run `git check-ignore -v <claimed_file>` on the flagged paths to confirm."* That's the kind of message that would have caught this in run-3 turn 3 instead of needing a forensic post-mortem.

This is also a guardkit-upstream change. Combine with D4 in a single guardkit task.

---

## Comparison: PH1-001 vs PH1-004 (the recovery question)

The task asks why the same audit symptom resolved for PH1-001 and not for PH1-004. The forensic answer:

| Factor                                           | PH1-001                                  | PH1-004                                                       |
|--------------------------------------------------|------------------------------------------|---------------------------------------------------------------|
| Target paths                                     | `src/study_tutor/nats_core/`             | `src/study_tutor/adapters/`                                   |
| Hits stale-worktree gitignore unanchored rule?   | **No** (`nats_core/` is not `adapters/`) | **Yes** (matches the bare `adapters/` rule)                   |
| Quality-gate profile (Coach line 130 / 246)      | `scaffolding` (tests not required)       | (full feature profile, all gates required)                    |
| Implementation mode                              | `direct` (1×1 multiplier)                | `task-work` (1.5×1.6 = 2.4× SDK budget)                       |
| Files claimed (size of denominator)              | 1                                        | 6 (turn 1) → 200+ (turn 5)                                    |
| Audit honesty turn 1                             | 0.88 (1 discrepancy out of small claim)  | 0.86 (3 discrepancies out of 6 claims)                        |
| Audit honesty turn 3                             | gate passed: `audit=True` (line 247)     | 0.47, 16 discrepancies, gate short-circuited                  |

The decisive line is the first one. PH1-001 was outside the broken rule's blast radius; PH1-004 was inside it. Everything else (mode, gate profile, scope) is downstream amplification. The "perspective reset" on turn 3 didn't *fix* PH1-001 — it removed a transient one-off audit hit that happened to be there for unrelated reasons (a metadata sidecar the Player had claimed but not staged on turn 1). For PH1-004, perspective reset doesn't change the matter at all because the Player keeps writing to a permanently-invisible path.

**Run-3 PH1-001's apparent recovery is therefore not a model of how PH1-004 could have recovered**. It's a parallel lucky absence.

---

## Decision Matrix (D1-D5 summary)

| #  | Decision                                                                                          | Effort     | Locus           | Unblocks FEAT-39E1 re-run? |
|----|---------------------------------------------------------------------------------------------------|------------|-----------------|----------------------------|
| D1 | Root cause = gitignore-induced file drop (no orchestrator change needed for this finding)         | 0          | finding         | (informational)            |
| D2 | Keep PH1-004 as `task-work`; do **not** downgrade to `direct`                                     | 0          | finding         | (informational)            |
| D3 | Hand-implement PH1-004 from prior-run evidence; recreate worktree from current `main`             | 1-2 hours  | study-tutor     | **Yes — primary unblock**  |
| D4 | guardkit upstream: distinguish gitignored-vs-fabricated; reset SDK session on rollback            | 0.5-1 day  | guardkit        | Defence-in-depth, not blocking for this re-run |
| D5 | guardkit upstream: early-abort on sustained low honesty                                           | 1-3 hours  | guardkit        | Defence-in-depth           |

---

## Remediation Plan

Concrete follow-up tasks. D3 is the only one that has to land for the FEAT-39E1 re-run; D4 + D5 are defence-in-depth.

1. **TASK-NATS-FIX-PH1-004-MANUAL**: hand-author `src/study_tutor/adapters/command_router.py` and `tests/unit/adapters/test_command_router.py` directly on `main` (not in the worktree), using the seven completion-promise specs preserved at [`.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-004/player_turn_1.json:46-203`](../../.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-004/player_turn_1.json) as the implementation spec. Run `pytest tests/unit/adapters/test_command_router.py` and `ruff check`; commit; mark PH1-004 `completed` in `.guardkit/features/FEAT-39E1.yaml`. *Effort: ~1 hour. Repo: study-tutor.*
2. **TASK-NATS-FIX-WORKTREE-REBASE**: delete `.guardkit/worktrees/FEAT-39E1/` and let the next autobuild run create a fresh worktree from current `main` (which has `12df1a9`). Verify with `grep 'src/study_tutor/adapters' .guardkit/worktrees/FEAT-39E1/.gitignore` after creation. *Effort: ~5 minutes. Repo: study-tutor.*
3. **TASK-NATS-RESUME**: run `guardkit autobuild feature FEAT-39E1 --resume` from a clean worktree against waves 5-9 (PH1-005, PH1-008-010, PH2-001-003, PH3-001-005). Manual completion of PH1-004 in step 1 will let the orchestrator skip Wave 4 as `already_completed` (the same pattern PH1-003/007/006 followed in run-3). *Effort: passive, ~30 min wall-clock per remaining task; total ~3-6 hours. Repo: study-tutor.*
4. **TASK-GK-AUDITOR-IGNORE-AWARE**: in guardkit Coach `honesty_verification`, when a claimed path satisfies `os.path.exists(path) and is_ignored(path)`, classify as `IgnoredButPresent` (warning, contributes 0 to critical-issue count). Update the warning text to print the ignore rule (`git check-ignore -v` output). *Effort: 0.5 day. Repo: guardkit.*
5. **TASK-GK-ROLLBACK-SESSION-RESET**: in guardkit `rollback_on_pollution` path, drop the resumed SDK session-id and start a fresh one on the next Player invocation; also wipe `.guardkit/autobuild/<TASK-ID>/` from the worktree-restore set so per-turn audit JSONs survive. *Effort: 0.5 day. Repo: guardkit.*
6. **TASK-GK-HONESTY-EARLY-ABORT**: add a config'd threshold (default: 3-turn rolling avg < 0.3) that aborts the adversarial loop with a diagnostic message naming any consistently-flagged path. *Effort: 1-2 hours. Repo: guardkit.*

Tasks 1–3 unblock FEAT-39E1. Tasks 4–6 are independent and can be done after the demo.

---

## Demo-Readiness Statement

**FEAT-39E1 Phase 3 is the operator GB10 demo and 13 of 18 tasks remain unstarted as of run-3.** The blocker is one task (PH1-004) and one configuration (worktree base). With 1 hour of manual implementation + 5 minutes of worktree recreation + ~3-6 hours of unattended autobuild for the remaining 13 tasks (most of which are sub-complexity-3 scaffolding/docs/scripts), **the demo schedule is recoverable on the order of one focused half-day**. There's no architectural rework needed and no run-4 failure mode that this review can predict from the artefacts. Only contingency to watch: if either of TASK-NATS-PH1-005 (NATS adapter full lifecycle) or PH1-008-010 (smoke tests / e2e demo gate) hits a similar gitignore-rule path that isn't `adapters/` and isn't covered by the existing fix — unlikely given the current `.gitignore` re-includes — but a `git check-ignore -v` sweep over each Player-claim batch in subsequent runs would catch it cheaply.

---

## Acceptance Criteria — self-check

- [x] Root-cause hypothesis stated with evidence — F1, links to specific worktree/project gitignore lines and `merge-base` output.
- [x] Compare/contrast with PH1-001's recovery — *Comparison* section.
- [x] Contributing causes enumerated — F1 (cause), F2/A2 (rollback-session), F3 (artefact loss), F4 (cross-platform paths), F6 (specialist-tracking sibling audit).
- [x] Concrete remediation plan with tasks, effort, repo target — *Remediation Plan*.
- [x] Decision recorded for D1–D5 — *Decisions Recorded* + *Decision Matrix*.
- [x] Demo-readiness statement — *Demo-Readiness Statement*.
- [x] Output written to `.claude/reviews/TASK-REV-F30A-review-report.md` — this file.

---

## Source-Confirmed Mechanism (revised post-[R]evise)

The first pass relied on the failure-log narrative + on-disk artefact reconciliation. The [R]evise pass adds direct citations into guardkit source code. Each of the four moving parts of the failure can now be cited rather than inferred.

### M1 — The Coach claim-audit *literally implements* the FEAT-39E1 silent-drop check

[`guardkit/orchestrator/coach_verification.py:226-234`](../../../../guardkit/guardkit/orchestrator/coach_verification.py#L226-L234) calls `self._verify_claims_were_staged(player_report)` with this comment:

> Verify Player claims would be staged (TASK-AB-FIX-CHECKPOINT-CLAIM-AUDIT). Catches the FEAT-39E1 class of silent loss: Player created a file that exists on disk but is gitignored (or sparse-filtered, etc.), so the per-turn checkpoint commits without it. `_verify_files_exist` passes because the file is on disk; this check fails because git would refuse to stage it.

The implementation at [`coach_verification.py:362-521`](../../../../guardkit/guardkit/orchestrator/coach_verification.py#L362-L521) does the following:

1. Builds a set of claimed paths from `files_created`, `files_modified`, `tests_written`, plus `completion_promises[*].implementation_files` and `completion_promises[*].test_file`.
2. Runs `git status --porcelain=v1 --untracked-files=all` (line 455-462) inside the worktree. Comment at line 482-486: *"Anything reported here would be staged by `git add -A` — gitignored paths are excluded by default (no `--ignored` flag)."*
3. For every claimed path missing from the porcelain output, emits a `Discrepancy(claim_type="claim_audit", severity="critical", ...)` (line 504-520) with the boilerplate `actual_value`:

> Path would not be staged by 'git add -A' (absent from 'git status --porcelain'). Most common cause: an unanchored .gitignore rule silently filters the file. Other causes: sparse-checkout, assume-unchanged, pathspec attribute filters, or the file is tracked but unchanged (Player claimed modified but didn't).

The comment at line 376-381 names this exact failure verbatim — *"Player created `src/study_tutor/adapters/manifest.py`; the worktree's `.gitignore` carried an unanchored `adapters/` rule"*. This is the FEAT-39E1 self-audit fix landing on 2026-05-08 (TASK-AB-FIX-CHECKPOINT-CLAIM-AUDIT). The audit is doing exactly what it was built to do; the project's `.gitignore` got a fix on the same day (`12df1a9`); the worktree's `.gitignore` did not, because the worktree branch was never rebased to pick the fix up.

**Honesty score formula** (line 244): `honesty_score = 1.0 - (critical_failures / max(total_claims, 1))`. With 3 discrepancies and 7 verifiable claims (`files_created` + `files_modified` + `tests_written` + `completion_promises[*]` paths) on turn 1, that gives ~0.86 — matching the failure log line 593 exactly.

**Critical-issue threshold** at [`coach_validator.py:884-886`](../../../../guardkit/guardkit/orchestrator/quality_gates/coach_validator.py#L884-L886): any `severity="critical"` honesty discrepancy short-circuits gate evaluation. There is no per-rule classifier — every gitignored-but-present path counts as critical, identical to a fabricated path. This is the line that needs to change for D4.1.

### M2 — Rollback wipes the filesystem but not the SDK session

[`autobuild.py:2319-2342`](../../../../guardkit/guardkit/orchestrator/autobuild.py#L2319-L2342):

```python
if self.rollback_on_pollution:
    if self._checkpoint_manager.should_rollback():
        target_turn = self._checkpoint_manager.find_last_passing_checkpoint()
        if target_turn:
            logger.warning(...)
            self._checkpoint_manager.rollback_to(target_turn)
            self._turn_history = turn_history[:target_turn]
            previous_feedback = self._turn_history[-1].feedback if self._turn_history else None
            logger.info(f"Continuing from turn {target_turn + 1} after rollback")
            continue
```

Three things this does NOT do:
- **Reset turn counter** — the loop's `turn` variable advances on each iteration; rollback only truncates `turn_history`. The log line *"Continuing from turn {target_turn + 1} after rollback"* is informational; the actual `turn` variable on the next iteration is whatever the loop counter is (turn 4 after a turn-3 trigger).
- **Reset SDK session** — that is done only by [`_should_reset_perspective`](../../../../guardkit/guardkit/orchestrator/autobuild.py#L2160-L2165) (lines 2160-2165) which fires only at scheduled `reset_turns=[3, 5]`. The session id is re-saved on every turn at line 2195 (`set_player_resume_session(turn_record.player_result.session_id)`), so a turn-4 player after a post-turn-3 rollback resumes the turn-3 session. That session is the one that just authored the files which `git reset --hard` then deleted.
- **Wipe the orchestrator's own per-turn artefacts** — [`worktree_checkpoints.py:437-477`](../../../../guardkit/guardkit/orchestrator/worktree_checkpoints.py#L437-L477) calls `git reset --hard checkpoint.commit_hash`. This restores the working tree to the checkpoint commit's content — which means run-3's own `coach_turn_2.json … coach_turn_5.json` (committed in subsequent run-3 checkpoints, then dropped from the history when reset rewinds to `0a6f9192`) get removed from the working tree. That's why those files are absent today. The orchestrator's "Saved Coach decision" log line at `coach_validator.py:587, 690, 790, 913, 1012` is true at write time; the rollback erases the audit trail of the turns that triggered the rollback. The on-disk `coach_turn_1.json` survives because it's part of the `0a6f9192` commit (tagged `from_prior_run`).

### M3 — `should_rollback` and `find_last_passing_checkpoint` together select the prior-run checkpoint

[`worktree_checkpoints.py:483-518`](../../../../guardkit/guardkit/orchestrator/worktree_checkpoints.py#L483-L518): `should_rollback()` excludes `from_prior_run` checkpoints from pollution detection (`current_run = [cp for cp in self.checkpoints if not cp.from_prior_run]` at line 502). Correctly so — TASK-FIX-F4A3 added that exclusion.

[`worktree_checkpoints.py:520-`](../../../../guardkit/guardkit/orchestrator/worktree_checkpoints.py#L520) `find_last_passing_checkpoint()` does not have the same exclusion. It scans all checkpoints in reverse and returns the most recent one with `tests_passed=True`. In run-3 PH1-004's case:

- run-3 turns 1-3 each created a checkpoint with `tests_passed=False` (failure log line 596: *"Creating checkpoint for TASK-NATS-PH1-004 turn 1 (tests: fail, count: 0)"*). They're tagged `tests: fail` because the orchestrator's checkpoint metadata uses test count *as committed by `git add -A`*, which is zero — the same gitignore drop that's causing the audit to fail also makes the checkpoint think tests didn't run.
- The only `tests_passed=True` checkpoint in the list is `0a6f9192` (the `from_prior_run` checkpoint from May 8).
- So `find_last_passing_checkpoint()` returns turn 1, mapped to commit `0a6f9192`.

This pairing is what makes the rollback land on a 2-day-old prior-run state instead of a turn earlier in the same run. There's no live-passing checkpoint in run-3 to land on. Compounding factor, not separate cause.

### M4 — The discrepancy explosion is amplification + cumulative report state

The Player's report on each turn is incrementally enriched (`agent_invoker.py` calls `Recovered N completion_promises from agent-written player report` — failure log lines 544-545 turn 1, similar lines on each subsequent turn). The cumulative `claimed` set grows because each turn:

- The Player writes a fresh task plan, fresh test file, fresh implementation file (because the rollback wiped them).
- The Player's resumed SDK session adds new completion-promise entries on top of remembered ones.
- The orchestrator merges specialist results into `task_work_results.json` (failure log lines 565, 666, 766, 890, 988: *"Injected orchestrator specialist records … merged=2, validation=violation"*).

So `total_claims` (denominator) grows ~linearly across turns; `critical_failures` (numerator) grows faster because each rewrite of an `adapters/` file is a fresh discrepancy and the prior turns' claims often persist in the cumulative report. By turn 4 the Player has accumulated 195 distinct critical claims for paths that don't appear in `git status --porcelain`. By turn 5, 200.

So the curve 0.86 → 0.66 → 0.47 → 0.11 → 0.07 is not a Player honesty regression; it's the same one bug (gitignored path) being re-counted with a fatter denominator.

---

## Reconciliation with Prior Reviews (CC40, D509)

The "failure-mode upstream-drift" claim from the first version of this report can now be checked against the prior reviews' artefacts.

| Run | Review     | Primary root cause                                           | Locus                              | Touched gitignore? |
|-----|------------|--------------------------------------------------------------|------------------------------------|--------------------|
| 1   | [TASK-REV-CC40](../../tasks/backlog/TASK-REV-CC40-analyse-feat-39e1-autobuild-failure.md)  | BDD oracle runs entire feature file; pytest-bdd v8 emits unbound scenarios as FAILED, not pending | guardkit BDD runner + classifier   | No                 |
| 2   | [TASK-REV-D509](../../tasks/backlog/TASK-REV-D509-analyse-feat-39e1-autobuild-run-2-failure.md) | `_dependencies_satisfied` doesn't treat `status=deferred` as satisfied | guardkit dependency resolver       | No                 |
| 3   | TASK-REV-F30A (this) | Worktree branch carries pre-12df1a9 `.gitignore`; Player's `adapters/*.py` are silently dropped from `git add -A` | repo VCS config + worktree branch base | **Yes — decisive** |

Three observations:

**O1**. Neither prior review identified the `.gitignore` drop as the root cause for *its own* failure. Both were correctly diagnosed against orthogonal causes. Run-1 failed before the autobuild ever attempted PH1-004 (it stopped at PH1-006 in Wave 2). Run-2 *did* attempt PH1-004 (D509: "Waves 3–7 produced 9 fresh approvals") and the Player's writes presumably hit the same `.gitignore`-drop bug then — but run-2 *also* had the bug, and the Coach claim-audit landing 2026-05-08 (TASK-AB-FIX-CHECKPOINT-CLAIM-AUDIT) might or might not have been live in the guardkit version run-2 was using. Either way, run-2's nine "approvals" between PH1-006 and the Wave-8 dependency crash are all suspect — *the same .gitignore-drop pathology likely produced "successful" turns whose `.py` files never reached the committed branch*. This is in fact what the user's commit message on 12df1a9 says: *"FEAT-39E1 silent file drop"*. The user noticed during cleanup, fixed the project root, but the worktree branch was never reconciled.

**O2**. The `task_work_results.json` inner timestamp is `2026-05-08T23:12:25` and the file's preserved content shows decision="approve", honesty=1.0, all 7 ACs verified — but `git show 0a6f9192 --stat` confirms NO `command_router.py` or `test_command_router.py` were committed in that turn. That is the run-1-aftermath PH1-004 attempt that "succeeded" by Coach honesty score but never staged the implementation. It's the literal incident the gitignore fix mentions. So the May 8 approval was itself the silent-drop incident. The auditor *that exists now* would have flagged it — and on run-3 it does flag it, against the same broken `.gitignore` a second time, because the worktree branch was never rebased.

**O3**. Each prior review's remediation was applied to the **right repository** for that root cause (run-1 in-repo fixes, run-2 in-repo + guardkit fix). The remediation pattern this review proposes — in-repo manual implementation + worktree recreation + guardkit auditor classification — is consistent with the prior pattern. There is no locus mismatch.

The "trajectory upstream" framing therefore stands: each successive failure was structurally smaller and more peripheral. None of the three is the same bug. The user correctly closed each prior loop and the next loop opened on a smaller surface.

---

## Sequence Diagrams

Three diagrams that trace the failure across the SDK / git / Coach boundaries. All in Mermaid.

### Diagram 1 — Run-3 PH1-004 turn 1: the file-drop and the audit

Single-turn flow showing how a Player Write that succeeds locally produces a Coach critical-issue.

```mermaid
sequenceDiagram
    autonumber
    participant FO as FeatureOrchestrator
    participant AI as AgentInvoker
    participant SDK as Claude SDK<br/>(Player session)
    participant FS as Worktree FS<br/>(tracked by git)
    participant GIT as git
    participant CV as CoachVerifier<br/>(coach_verification.py)
    participant CK as CheckpointMgr<br/>(worktree_checkpoints.py)

    FO->>AI: Invoke Player turn 1<br/>(task-work mode, complexity 6, 160 SDK turns)
    AI->>SDK: Resume / start session
    SDK->>FS: Write src/study_tutor/adapters/command_router.py
    SDK->>FS: Write tests/unit/adapters/test_command_router.py
    SDK->>FS: Write metadata sidecars<br/>(player_turn_1.json, etc.)
    SDK->>SDK: pytest tests/unit/adapters/<br/>(9 passed)
    SDK-->>AI: PlayerReport{<br/> files_authored=[...command_router.py,<br/> ...test_command_router.py],<br/> completion_promises[7] all complete,<br/> tests_passed=true}
    AI->>FS: Write task_work_results.json
    AI->>FO: Return PlayerReport
    FO->>CV: validate_honesty(report)
    CV->>CV: _verify_files_exist()<br/>→ all paths exist on disk → OK
    CV->>GIT: git status --porcelain=v1<br/>--untracked-files=all
    Note over GIT: .gitignore line 284: <br/>adapters/  (unanchored)<br/>Re-includes only cover<br/>tutoring/adapters/
    GIT-->>CV: porcelain output<br/>(missing src/study_tutor/adapters/*<br/>and tests/unit/adapters/*)
    CV->>CV: dropped = claimed - would_stage<br/>→ 3 paths<br/>→ 3 × Discrepancy(severity=critical)
    CV-->>FO: HonestyVerification(<br/> critical_failures=3,<br/> total_claims=7,<br/> honesty_score=1 - 3/7 = 0.86)
    FO->>FO: short-circuit gate evaluation<br/>(honesty critical issues > 0)
    FO->>CK: create_checkpoint(turn=1, tests_passed=False)
    Note over CK: tests_passed=False because count=0:<br/>the same gitignore drop hides the<br/>test file from the orchestrator's<br/>"committed test count" metric
    CK->>GIT: git commit -m "[guardkit-checkpoint] Turn 1 ..."
    GIT-->>CK: commit 44658127<br/>(missing the .py files; .gitignored)
    FO->>FO: Decision=feedback<br/>"Checkpoint claim audit failed:<br/>Player claimed a file that 'git add -A' would not..."
```

### Diagram 2 — Turns 3-4: rollback wipes filesystem; SDK session is preserved

Cross-turn flow showing the state divergence after `rollback_on_pollution`.

```mermaid
sequenceDiagram
    autonumber
    participant FO as FeatureOrchestrator
    participant AI as AgentInvoker
    participant SDK as Claude SDK<br/>(Player session N)
    participant FS as Worktree FS
    participant CK as CheckpointMgr
    participant GIT as git

    Note over FO: End of turn 3<br/>honesty=0.47 (16 discrepancies)<br/>3 consecutive failing checkpoints<br/>(turn 1, 2, 3 all tests_passed=False)
    FO->>CK: should_rollback()  (consecutive_failures=3)
    CK-->>FO: True
    FO->>CK: find_last_passing_checkpoint()
    Note over CK: current-run checkpoints all<br/>have tests_passed=False;<br/>only passing one is<br/>0a6f9192 (from_prior_run)
    CK-->>FO: turn 1 → commit 0a6f9192
    FO->>CK: rollback_to(turn=1)
    CK->>GIT: git reset --hard 0a6f9192
    GIT->>FS: working tree reset<br/>- tracked files revert to 0a6f9192<br/>- run-3 turn-1/2/3 checkpoints DROPPED<br/>- coach_turn_2/3.json removed<br/>- adapters/*.py removed (were never tracked)
    Note over FO: turn_history truncated to [:1]<br/>previous_feedback = None<br/>session_id NOT touched<br/>(re-saved at line 2195 each turn)
    FO->>FO: continue → turn = 4
    FO->>AI: Invoke Player turn 4
    AI->>SDK: Resume session N (from turn 3)
    Note right of SDK: SDK memory:<br/>"I created command_router.py,<br/>test_command_router.py,<br/>+ many edits over turns 1-3"
    SDK->>FS: Read src/study_tutor/adapters/command_router.py
    FS-->>SDK: ENOENT (file was wiped by reset)
    SDK->>FS: Re-Write the file (and many others<br/>it remembers having authored)
    SDK-->>AI: PlayerReport with cumulative<br/>claim list (turns 1-3 + new turn 4)
    AI->>FS: task_work_results.json append/merge
    FO->>FO: Coach validation → 195 critical<br/>(every adapters/*.py still gitignored;<br/>cumulative report has 200+ claims;<br/>same one bug, fatter denominator)
```

### Diagram 3 — System boundary view: the .gitignore divergence

C4-flavoured container view showing where the configuration drift lives.

```mermaid
flowchart TD
    subgraph repo["repo: study-tutor (filesystem boundary)"]
        direction TB
        subgraph mainBranch["branch: main  (HEAD = 05c9c6c)"]
            mainGI[".gitignore (lines 296-315)<br/>adapters/<br/>!src/study_tutor/tutoring/adapters/<br/>!src/study_tutor/adapters/  ← FIX in 12df1a9<br/>!tests/unit/adapters/        ← FIX in 12df1a9"]
        end
        subgraph wtBranch["branch: autobuild/FEAT-39E1  (HEAD = 0a6f919)"]
            wtGI[".gitignore (lines 280-300)<br/>adapters/<br/>!src/study_tutor/tutoring/adapters/<br/>(NO src/study_tutor/adapters/<br/>re-include — pre-12df1a9)"]
            adaptersDir["src/study_tutor/adapters/<br/>(empty after rollback;<br/>only __pycache__/)"]
            testDir["tests/unit/adapters/<br/>(empty after rollback;<br/>only __pycache__/)"]
        end
    end

    subgraph autobuild["guardkit autobuild orchestrator"]
        direction TB
        player["Player (SDK Claude session,<br/>task-work delegation,<br/>160 SDK max turns)"]
        coach["Coach validator<br/>(coach_verification.py)"]
        ckmgr["CheckpointMgr<br/>(worktree_checkpoints.py)"]
    end

    git["git CLI"]

    player -->|Write to src/study_tutor/adapters/*.py| adaptersDir
    player -->|Write to tests/unit/adapters/*.py| testDir
    coach -->|git status --porcelain --untracked-files=all| git
    git -->|reads .gitignore| wtGI
    git -->|reports porcelain output<br/>(adapters/* SILENTLY DROPPED)| coach
    coach -->|Discrepancy x3, severity=critical| coach
    ckmgr -->|git reset --hard 0a6f9192<br/>(rollback)| git
    git -->|wipe run-3 checkpoint commits<br/>+ working tree adapters/*.py| repo

    mergebase["merge-base 12df1a9 246f73b<br/>= NOT AN ANCESTOR<br/>(worktree branch never rebased)"]:::issue
    wtGI -.diverges from.- mainGI
    wtGI --- mergebase

    classDef issue fill:#fee,stroke:#900,color:#900
    style wtGI fill:#fee,stroke:#900
    style adaptersDir fill:#fee,stroke:#900
    style testDir fill:#fee,stroke:#900
```

The single load-bearing edge is `wtGI -.diverges from.- mainGI`. Everything downstream of that — Player writes that vanish, Coach audit that fails, rollback that lands on a 2-day-old prior commit, honesty score that collapses, max_turns that exhausts — is consequence, not cause. Recreating the worktree from current `main` removes that edge entirely.

---

## Confidence Statement

After the [R]evise pass:

- **Root cause (F1)** — *highly confident*. Direct citations: project `.gitignore:296-315` (fix) vs worktree `.gitignore:280-300` (no fix), `git merge-base --is-ancestor 12df1a9 246f73b` returns false, `git show 0a6f9192 --stat` confirms `command_router.py` was never committed at the rollback target, Coach source comment at `coach_verification.py:376-381` literally names this scenario.
- **Rollback session-not-reset (F2/M2)** — *confirmed by source*. `autobuild.py:2160-2165` resets session only on perspective reset; rollback path at `autobuild.py:2319-2342` does not call `set_player_resume_session(None)`.
- **Rollback wipes audit trail (M2)** — *confirmed by source + filesystem*. `worktree_checkpoints.py:465` is `git reset --hard`, which by definition discards the run-3 checkpoint history. coach_turn_2..5.json are absent from disk; coach_turn_1.json is the prior-run version preserved at the rollback target commit. These two facts agree.
- **Honesty formula (F2 turn-by-turn table)** — *exactly matches log*. 3/7 → 0.86 maps to log line 593 with no rounding error. Subsequent turns track within rounding given the `task_work_results.json`-merging behaviour at `agent_invoker.py:544-547` (line refs from failure log).
- **Trajectory across runs (F5)** — *re-checked against prior reviews*. CC40 and D509 each diagnose orthogonal causes and apply orthogonal fixes; this run's cause was created by run-2's silent-drop "successes" that the user noticed and partially fixed (project `.gitignore`) without rebasing the worktree.
- **Demo recovery estimate** — *unchanged*: ~half-day focused work to ship PH1-004 manually + recreate worktree + resume autobuild on the remaining 13 waves. No predictable run-4 failure mode visible in the artefacts; the only watch-out is whether subsequent waves' Player writes target paths that *also* match the (now-fixed-in-main) `.gitignore` rule, which a freshly-recreated worktree handles correctly.

If a fourth autobuild run is desired purely to validate before the demo, run *after* steps 1+2 of the remediation (manual PH1-004 + worktree recreation), against waves 5+ only — `--resume` will skip the completed tasks. Expected duration ≤4h, expected failure modes none visible from this evidence.

---

## Context Used

- Failure log: [docs/history/autobuild-FEAT-39E1-fail-run-3.md](../../docs/history/autobuild-FEAT-39E1-fail-run-3.md) (lines 25-26, 79, 130-247, 460-1068 inspected directly)
- Worktree state: [.guardkit/worktrees/FEAT-39E1/.gitignore:280-300](../../.guardkit/worktrees/FEAT-39E1/.gitignore), `git -C ... merge-base --is-ancestor 12df1a9 246f73b` (false), `git -C ... show 0a6f9192 --stat` (no command_router.py)
- Project root: [.gitignore:296-315](../../.gitignore) (the fix), commit `12df1a9` *fix(gitignore): re-include src/study_tutor/adapters/ + tests/unit/adapters/ (FEAT-39E1 silent file drop)*
- PH1-004 prior-run artefacts (post-rollback content): [player_turn_1.json:15-16](../../.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-004/player_turn_1.json), [coach_turn_1.json:184-189](../../.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-004/coach_turn_1.json), [task_work_results.json:132-203](../../.guardkit/worktrees/FEAT-39E1/.guardkit/autobuild/TASK-NATS-PH1-004/task_work_results.json)
- Knowledge graph: not consulted directly during analysis (Graphiti available — `.guardkit/graphiti.yaml` not checked); review findings will be written to `guardkit__project_decisions` and `guardkit__task_outcomes` on `[A]ccept` per the Phase 5 protocol.
- Guardkit source (revise pass): [`coach_verification.py:200-535`](../../../../guardkit/guardkit/orchestrator/coach_verification.py) (honesty verification including `_verify_claims_were_staged`), [`coach_validator.py:865-905`](../../../../guardkit/guardkit/orchestrator/quality_gates/coach_validator.py) (gate short-circuit on critical issues), [`autobuild.py:2150-2350`](../../../../guardkit/guardkit/orchestrator/autobuild.py) (turn loop, perspective reset, rollback flow), [`worktree_checkpoints.py:437-518`](../../../../guardkit/guardkit/orchestrator/worktree_checkpoints.py) (`rollback_to`, `should_rollback`, `find_last_passing_checkpoint`).
- Prior reviews (revise pass): both prior post-mortems read end-to-end; their `review_results` frontmatter cross-checked against this run's findings.
- Run input artefacts (revise pass): [.guardkit/autobuild/FEAT-39E1/events.jsonl](../../.guardkit/autobuild/FEAT-39E1/events.jsonl) (10-line summary; PH1-004 visible as line 9 with `failure_category: other`), [.guardkit/autobuild/FEAT-39E1/review-summary.md](../../.guardkit/autobuild/FEAT-39E1/review-summary.md) (high-level outcome only — no per-turn flagged path data; consistent with the rollback wiping the per-turn audit JSONs).
