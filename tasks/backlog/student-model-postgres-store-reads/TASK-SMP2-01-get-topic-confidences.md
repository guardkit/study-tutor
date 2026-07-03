---
id: TASK-SMP2-01
title: "get_topic_confidences: read per-topic confidence entities from Postgres"
task_type: feature
feature_id: FEAT-SMP-002
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
parent_feature_spec: features/student-model-postgres-store-reads/student-model-postgres-store-reads_summary.md
---

## Objective

Fill `PostgresStudentStore.get_topic_confidences` (`src/study_tutor/knowledge/store/postgres.py:256-257`,
currently `raise NotImplementedError`) with a single SELECT over `topic_confidence`
that returns one `student_model.TopicConfidence` per row for the given student,
newest `last_revised_at` first.

Signature is fixed by the port (`store/port.py:74-79`) — do not change it:

```python
async def get_topic_confidences(self, student_id: str) -> list[TopicConfidence]:
```

`TopicConfidence` is the **domain** entity from `student_model.py:310-336`
(`student_ref`, `topic_ref`, `percentage`, `band`, `last_revised_at`) — NOT the
`TopicConfidenceSnapshot` read-projection used by `get_student_state`. Map each row:
`student_ref=student_id`, `topic_ref=row.topic_name`, `percentage=row.percentage`,
`band=row.band`, `last_revised_at=row.last_revised_at`.

## Scope

**In scope**
- `get_topic_confidences` body only: one parameterised `SELECT topic_name, percentage,
  band, last_revised_at FROM topic_confidence WHERE student_id = :sid ORDER BY
  last_revised_at DESC` on the shared async engine (constructor already holds
  `self._engine`/`self._pool`).
- Row → `TopicConfidence` projection (band read back verbatim from the column — it was
  derived at write time via `confidence_band_for`, ASSUM-001, so no re-derivation here).
- Empty list for a student with no rows AND for an unknown student (no distinction —
  both are `[]`, per FakeStudentStore parity).

**Out of scope**
- `get_recent_misconceptions` → TASK-SMP2-02; `get_student_state` → TASK-SMP2-03. Leave
  them raising `NotImplementedError`.
- Session CRUD (`create_session`/`get_session`/`list_sessions`/`append_turn`/`get_turns`/
  `end_session`) → FEAT-SMP-003 (gated by G-CON). Leave raising `NotImplementedError`.
- The write methods are DONE (W1) — do not touch them.

## Acceptance Criteria

- [ ] `get_topic_confidences("lilymay")` returns one `student_model.TopicConfidence` per
      `topic_confidence` row for that student, with `student_ref`, `topic_ref` (=`topic_name`),
      `percentage`, `band`, and `last_revised_at` populated from the row.
- [ ] Rows are ordered newest `last_revised_at` first.
- [ ] The stored `band` is returned verbatim (read-back matches what the write path derived;
      e.g. a 72% row reads back band `"secure"`, a 45% row reads back `"developing"`).
- [ ] A student with zero `topic_confidence` rows returns `[]` (empty list, not an error).
- [ ] An unknown `student_id` returns `[]` (no student existence pre-check required —
      an absent student simply has no rows).
- [ ] `last_revised_at` is returned as a timezone-aware UTC `datetime` (TIMESTAMPTZ column).
- [ ] `student_id` is passed as a bound parameter (no SQL string interpolation).
- [ ] DB/connection errors are NOT swallowed here — they propagate so the `knowledge.store.reads`
      wrapper can degrade to empty (do not add a try/except that returns `[]` on failure).
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

Adapter behaviour runs against an EPHEMERAL Postgres only (throwaway container on a
NON-5434 port). NEVER the NAS durable instance (runbook scope rule).

```bash
docker run -d --rm --name smp2-01-pg -e POSTGRES_USER=study_tutor \
  -e POSTGRES_PASSWORD=test -e POSTGRES_DB=study_tutor -p 55432:5432 postgres:16
export STUDY_TUTOR_PG_DSN="postgresql://study_tutor:test@localhost:55432/study_tutor"
.venv/bin/python -m alembic upgrade head

.venv/bin/python -m pytest tests/integration/knowledge/store/test_postgres_get_topic_confidences.py -v
.venv/bin/python -m pytest tests/unit/knowledge/store/ -v
.venv/bin/ruff check src/study_tutor/knowledge/store/postgres.py
docker stop smp2-01-pg
```

## Implementation Notes

- Reuse the engine-acquisition shape the write methods already use (`if self._pool ...
  elif self._engine ...`). Use `engine.connect()` (read-only, no transaction needed) with
  `sqlalchemy.text(...)` and a bound `:sid` param, or a Core `select()` over a lightweight
  `Table` def mirroring the write helpers' style — match the existing file idiom.
- Do NOT re-derive the band with `confidence_band_for` — the column is authoritative
  (a mismatch would be a write-path bug, out of scope here).
- Return `TopicConfidence` (domain, `student_ref`/`topic_ref`), NOT `TopicConfidenceSnapshot`
  (`topic_name`). This is the field-name trap — get it right; TASK-03 uses the Snapshot.

## Boundary-test discipline (read the retro)

Per `docs/retros/2026-07-03-autobuild-self-defeating-boundary-tests.md`: a scope-guard
test here may assert `NotImplementedError` ONLY for the SESSION-CRUD methods (out of scope
for the WHOLE FEAT-SMP-002 feature). It must NOT assert `NotImplementedError` for
`get_recent_misconceptions` or `get_student_state` — TASK-SMP2-02/03 implement those and a
transient-state assertion would detonate the moment they land. Never assert transient state.

## BDD Scenarios

From `features/student-model-postgres-store-reads/student-model-postgres-store-reads.feature`
(exercise `get_topic_confidences`):

- Reading per-topic confidences returns one entry per topic carrying its band
- A stored confidence percentage reads back with the boundary-correct band *(Scenario Outline)*
- Reading confidences for a learner with no topics returns an empty list
- Reading confidences and misconceptions for an unknown learner returns empty results *(confidences half)*
- Learner-state timestamps are returned as timezone-aware UTC
