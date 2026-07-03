# Retro: AutoBuild Players wrote self-defeating "boundary" tests

**Date:** 2026-07-03
**Feature:** FEAT-SMP-001 — Student Model Postgres Store (W1)
**Tool:** `guardkit autobuild feature` (SDK harness)
**Severity:** Medium (one task hit `max_turns_exceeded`; two more stale tests slipped past the Coach and failed a full-suite run)
**Status:** Resolved (3 tests corrected by hand before merge)
**Tags:** autobuild, guardkit, player, coach, test-scoping, tdd
**Related:** [2026-07-03-autobuild-parallel-wave-worktree-pollution.md](./2026-07-03-autobuild-parallel-wave-worktree-pollution.md)

## Summary

Across FEAT-SMP-001 the Player repeatedly wrote tests that assert a **transient, point-in-time state of its own task** rather than a lasting invariant. Each was locally valid when written (so the Coach approved it), but became **false the moment a later task did its job** — a "self-defeating" test. Three instances:

1. **SMP-03** wrote `test_learner_state_writes_raise_not_implemented`, asserting the learner-state **write** methods raise `NotImplementedError`. But *implementing those three writes is exactly W1's deliverable* (SMP-04/05/06). It broke the instant SMP-04 landed `apply_confidence_update`, failing the between-wave smoke gate and driving **SMP-04 to `max_turns_exceeded`** (its Player couldn't fix a failing test that lived in another task's file).
2. **SMP-01** wrote `test_ac007_versions_dir_empty` (alembic `versions/` has no revisions) — false once SMP-02 adds the migration.
3. **SMP-01** wrote `test_ac011_no_tables_created` (asserting `versions/` empty) — same problem.

Instances 2 and 3 were in `tests/` (not `tests/unit/`), so the smoke gate (`pytest tests/unit`) never ran them; they only surfaced in my post-build full-suite verification.

## Root cause

- The Player, doing TDD for a single task, encodes the task's **momentary** post-conditions as assertions ("nothing else is implemented yet", "no migration yet", "no tables yet"). These read like reasonable "boundary" tests but are **not invariants** — the whole point of the following tasks is to make them false.
- The **Coach validates a task in isolation** (task-specific tests + a `tests/unit` smoke gate), so a stale test authored in task N is not re-run against task N+1's output. It passes at authoring time and detonates later — either at the next wave (if it lands in `tests/unit`) or silently until a full-suite run.
- The between-wave smoke gate caught #1 (because the offending test was in `tests/unit`), but as a *hard blocker on the wrong task*: SMP-04 was failed for a test defect it did not author and (by scope) should not edit.

## Evidence

```
# SMP-04, turn 5:
Runtime-parity check FAILED (exit=1, expected=0): set -e … pytest tests/unit
✗ TASK-SMP-04: FAILED (5 turns) max_turns_exceeded
# The single failing test:
FAILED tests/unit/knowledge/test_postgres_store_engine.py::TestNotImplementedBoundary::test_learner_state_writes_raise_not_implemented
```
The class docstring even scoped it correctly — *"AC-006: Read and session-CRUD methods still raise NotImplementedError"* — but the Player added a fourth method that asserts the **write** methods raise, contradicting the scope.

Post-build full-suite verification surfaced the SMP-01 pair:
```
FAILED tests/test_smp_01_alembic_setup.py::test_ac007_versions_dir_empty
FAILED tests/test_smp_01_alembic_setup.py::test_ac011_no_tables_created
```

## Impact

- SMP-04 burned its full 5-turn budget and failed, halting the run — despite its own implementation and tests being correct (its 19 integration tests passed).
- Two more stale tests would have made a full `pytest tests/` red on `main` had they not been caught in verification before merge.

## Resolution (what was fixed by hand)

- Deleted `test_learner_state_writes_raise_not_implemented` (kept the correct reads + session-CRUD `NotImplementedError` boundary tests).
- Removed `test_ac007_versions_dir_empty`; rescoped `test_ac011` to keep only its lasting invariant (`db.py` defines the shared metadata + engine factory, **no** `Table(`/`Column(`).
- Re-verified: smoke gate + full suite green (`1165 passed`; DB tests skip without a DSN, so CI-safe).

These were the only hand-edits to the autobuild output; **no `PostgresStudentStore` logic was changed** — all three were test-scoping fixes.

## Prevention / action items

- [ ] **Task specs should name the boundary explicitly and negatively.** For "leave the rest unimplemented" tasks, say *"assert `NotImplementedError` ONLY for the methods that are out of scope for the whole feature (reads → SMP-002, session CRUD → SMP-003) — never for methods a later task in THIS feature implements."* (The SMP-03 spec did say reads+session-CRUD; the Player over-added writes anyway, so make the negative explicit.)
- [ ] **Ban transient-state assertions in scaffold tasks.** "versions/ is empty", "no tables yet", "method X still raises" are point-in-time, not invariants. Prefer invariants: "`db.py` holds no `Table(`", "`alembic history` runs", "the migration is reversible".
- [ ] **Coach should run the whole-feature suite at the last wave** (or a `smoke_gate` on the final wave over `tests/`, not just `tests/unit`) to catch composition breaks a per-task Coach can't see. The `tests/`-vs-`tests/unit` split is exactly why instances #2/#3 slipped.
- [ ] **When a task hits `max_turns_exceeded` on a test it doesn't own, look upstream.** The failing assertion may belong to an earlier task; the current Player often can't/shouldn't fix it, so the loop can't converge.
- [ ] **Always run an independent full-suite verification before merging autobuild output** — the Coach's per-task green is necessary but not sufficient for composition.

## Links

- Merged feature: `main` @ `efe4fb0`.
- Sibling retro (the wave-2 stall): [parallel-wave worktree pollution](./2026-07-03-autobuild-parallel-wave-worktree-pollution.md).
