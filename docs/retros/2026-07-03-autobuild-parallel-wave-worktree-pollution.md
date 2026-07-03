# Retro: AutoBuild parallel-wave pollution in a shared worktree

**Date:** 2026-07-03
**Feature:** FEAT-SMP-001 — Student Model Postgres Store (W1)
**Tool:** `guardkit autobuild feature` (SDK harness, `GUARDKIT_HARNESS=sdk`)
**Severity:** High (two failed runs, ~90 min wall-clock burned before diagnosis)
**Status:** Resolved (workaround) · Root cause is a guardkit-autobuild limitation, not study-tutor code
**Tags:** autobuild, guardkit, orchestration, worktree, parallelism
**Related:** [2026-07-03-autobuild-self-defeating-boundary-tests.md](./2026-07-03-autobuild-self-defeating-boundary-tests.md)

## Summary

AutoBuild executes a feature's tasks **wave by wave**, and tasks within a wave run **in parallel inside one shared git worktree**. FEAT-SMP-001's plan put co-located tasks in the same wave (`[SMP-02, SMP-03]`, `[SMP-04, SMP-05]`). Because those tasks edit overlapping store modules (`postgres.py`, `db.py`, `wiring.py`) and the same test dirs, the two parallel Players stepped on each other; the Coach's mid-turn isolated snapshots caught each other's half-written state, tests failed transiently, and both tasks ended in `context_pollution_stall` ("no passing checkpoint to roll back to"). Run 1 died at Wave 2 with 1/7 tasks done.

The fix was to **serialize the waves** (one task per wave). Re-run, SMP-02 and SMP-03 each passed in a **single turn** — proving the code was always correct and the only problem was concurrent tasks sharing a worktree.

## Timeline

| Run | Duration | Outcome |
|---|---|---|
| Run 1 | ~28 min | ✗ Wave 2 (`SMP-02 ∥ SMP-03`) both `unrecoverable_stall`; 1/7 done; `stop_on_failure` halted |
| Run 2 (serialized) | ~60 min | ✓ SMP-01/02/03 (SMP-02, SMP-03 each **1 turn**); SMP-04 failed for an unrelated reason (see linked retro) |
| Run 3 | ~78 min | ✓ 7/7 |

## Root cause

- `guardkit autobuild feature` runs `orchestration.parallel_groups` waves with tasks in a wave executed concurrently against a **single shared worktree** (`.guardkit/worktrees/FEAT-SMP-001`).
- Store/adapter features are the worst case: nearly every task touches the same handful of modules (the adapter class, the shared metadata, the DI wiring) and the same test packages. Concurrent edits + the Coach's per-task isolated-snapshot test runs produce transient, inconsistent trees.
- The perspective-reset / checkpoint machinery then detects "context pollution" but, with no green checkpoint to roll back to (every early checkpoint was mid-collision), declares `unrecoverable_stall`.

## Evidence

```
✗ TASK-SMP-02: unrecoverable_stall (3 turns)  — context_pollution_stall_no_checkpoint
✗ TASK-SMP-03: unrecoverable_stall (3 turns)  — context_pollution_stall_no_checkpoint
Wave 2 ✗ FAILED: 0 passed, 2 failed
```
Coach's isolated run mid-collision: `test-orchestrator status=failed … tests_run=22 tests_failed=8 in 1.1s`.

Yet the **final** worktree tree (post-collision) passed cleanly: running the same two test files afterwards gave `24 passed, 0 failed`. After serialization, SMP-02 and SMP-03 were each `approved on turn 1`.

## Impact

- ~90 min wall-clock + SDK tokens across two failed/partial runs before the root cause was clear.
- Misleading failure signature: `context_pollution_stall` reads like a Player quality problem, but it was an orchestration/isolation problem — the code was correct throughout.

## Resolution (what unblocked it)

1. **Serialized `orchestration.parallel_groups`** in `.guardkit/features/FEAT-SMP-001.yaml` to one task per wave (5 waves → 7 waves), and set `recommended_parallel: 1`.
2. Stood up an **ephemeral Postgres** (`docker run postgres:16` on `:5455`) and exported `STUDY_TUTOR_PG_DSN` so the Coach's DB tests ran for real instead of skipping.
3. Resumed with `--resume`; AutoBuild re-read the serialized waves, skipped the already-approved tasks, and ran the rest one at a time.

## Prevention / action items

- [ ] **Plan store/adapter features as serial waves by default.** When multiple tasks in a wave write the same modules, don't parallelise them — put each in its own wave in `orchestration.parallel_groups`. Only parallelise tasks that touch **disjoint** files.
- [ ] **There is no `--max-parallel` flag on `autobuild feature`** — serialization must be encoded in the feature YAML's `parallel_groups`. (Confirmed via `--help`.) Consider filing a guardkit request for a `--serial` / `--max-parallel 1` flag, and/or per-task worktree isolation for parallel waves.
- [ ] **Provide the Coach a real dependency substrate.** For DB-backed features, export `STUDY_TUTOR_PG_DSN` → an **ephemeral** Postgres (never the NAS/durable instance) before launching, so DB tests validate for real rather than skipping. Pre-pull `postgres:16` locally (the GB10 didn't have it cached; the pull once timed out a 2-min command).
- [ ] **Treat `context_pollution_stall` on parallel waves as an isolation smell first**, not a Player-quality problem — check whether the wave's tasks share files before assuming the implementation is wrong.

## Links

- Merged feature: `main` @ `efe4fb0` (squash of `autobuild/FEAT-SMP-001`).
- Sibling retro (the SMP-04 blocker): [self-defeating boundary tests](./2026-07-03-autobuild-self-defeating-boundary-tests.md).
