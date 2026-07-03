---
id: TASK-SMP2-04
title: "Wire the Postgres student store into the serve boot (conditional on DSN)"
task_type: feature
feature_id: FEAT-SMP-002
wave: 4
implementation_mode: task-work
complexity: 3
dependencies: [TASK-SMP2-03]
parent_feature_spec: features/student-model-postgres-store-reads/student-model-postgres-store-reads_summary.md
---

## Objective

Call `build_student_store()` in the serve boot sequence so the wired `PostgresStudentStore` is
resolvable by `knowledge.store.provider.get_student_store()` at runtime — but **only when
`STUDY_TUTOR_PG_DSN` is set**, so DSN-less dev/CI keeps working (reads degrade to empty).

Without this, the planner repoint (TASK-SMP2-05) is inert: `get_student_store()` returns `None`
and every read degrades to empty forever (ASSUM-007). This task makes the reads real in production.

`build_student_store()` already exists (`src/study_tutor/knowledge/store/wiring.py:28`); it reads
`STUDY_TUTOR_PG_DSN`, constructs `PostgresStudentStore`, and calls `set_student_store(...)`. It
currently raises `KeyError` on a missing DSN — hence the guard here.

## Scope

**In scope**
- In the serve boot sequence in `src/study_tutor/cli/main.py` (alongside the existing
  `build_rag_providers(role_config)` call, ~`main.py:341` / `:497`), add:
  ```python
  if os.environ.get("STUDY_TUTOR_PG_DSN"):
      build_student_store()
  ```
  with a structured log line either way (wired / skipped-no-dsn). Import `build_student_store`
  from `study_tutor.knowledge.store.wiring`.
- Place it so it runs once at startup, before the orchestrator serves requests (same lifecycle
  point as RAG provider wiring).

**Out of scope**
- The planner repoint itself → TASK-SMP2-05.
- Changing `build_student_store()` internals — it is correct; only the CALLER decides whether to
  invoke it. (Do NOT make `build_student_store()` itself swallow a missing DSN — the guard belongs
  at the call site so the write path can still demand a hard failure elsewhere if needed.)
- Session-service wiring (`session/provider.py`) → out of scope (SMP-003 territory).

## Acceptance Criteria

- [ ] The serve boot calls `build_student_store()` exactly once when `STUDY_TUTOR_PG_DSN` is set
      in the environment, so `get_student_store()` returns a `PostgresStudentStore` afterwards.
- [ ] When `STUDY_TUTOR_PG_DSN` is unset, the boot does NOT call `build_student_store()`, does NOT
      raise, and `get_student_store()` remains `None` (reads degrade to empty — unchanged behaviour).
- [ ] A structured log line records which branch was taken (store wired vs skipped, no DSN) —
      never logging the DSN credentials.
- [ ] The wiring is idempotent/last-wins if boot runs twice in-process (mirrors
      `set_student_store` single-slot semantics) — no crash on a second call.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
# Boot-wiring is unit-testable without a live DB (build_student_store constructs the engine
# lazily; get_student_store() just checks the slot). No ephemeral PG required for this task.
.venv/bin/python -m pytest tests/unit/cli/test_serve_student_store_wiring.py -v
.venv/bin/python -m pytest tests/unit/knowledge/test_postgres_store_engine.py -v   # existing wiring tests
.venv/bin/ruff check src/study_tutor/cli/main.py
```

## Implementation Notes

- Match the existing boot idiom in `main.py` — find where `build_rag_providers(role_config)` is
  invoked and add the guarded student-store wiring adjacent to it, in the same startup function.
- Use `os.environ.get(...)` (truthy check), NOT `os.environ[...]`, for the guard — the whole point
  is to not raise when the DSN is absent.
- The unit test can monkeypatch `study_tutor.knowledge.store.wiring.build_student_store` and assert
  it is (a) called when the env var is set and (b) not called when unset — no real Postgres needed.
- Reset the provider slot in test teardown (`provider.reset_student_store()`), which
  `tests/unit/knowledge/store` fixtures already do.

## Boundary-test discipline (read the retro)

This task adds a call site; it does not change adapter method status. Do NOT add tests asserting
any store method raises `NotImplementedError` — the read methods are implemented by now and the
session methods are another feature's concern (assert those only in the adapter scope-guard, not here).

## BDD Scenarios

Supports (does not solely own): the planner-repoint scenarios in TASK-SMP2-05 rely on a wired
store to observe "real" reads in production. The unit behaviour (wired-when-DSN / skipped-otherwise)
is covered by this task's own tests; the feature file scenarios exercise the read behaviour that
this wiring enables.
