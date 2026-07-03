---
id: TASK-SMP2-02
title: "get_recent_misconceptions: window-filtered read with band-at-observation approximation"
task_type: feature
feature_id: FEAT-SMP-002
wave: 2
implementation_mode: task-work
complexity: 5
dependencies: [TASK-SMP2-01]
parent_feature_spec: features/student-model-postgres-store-reads/student-model-postgres-store-reads_summary.md
---

## Objective

Fill `PostgresStudentStore.get_recent_misconceptions`
(`src/study_tutor/knowledge/store/postgres.py:259-265`, currently `NotImplementedError`)
with a window-filtered SELECT over `misconception` that returns one
`student_model.Misconception` per row observed within `window_days`, newest first.

Signature is fixed by the port (`store/port.py:81-89`) — do not change it:

```python
async def get_recent_misconceptions(
    self, student_id: str, *, window_days: int = DEFAULT_MISCONCEPTION_WINDOW_DAYS,
) -> list[Misconception]:
```

`DEFAULT_MISCONCEPTION_WINDOW_DAYS = 30` (`store/port.py:49`). `Misconception` is the
**domain** entity (`student_model.py:286-307`): `text`, `topic_ref`, `observed_at`, and the
REQUIRED `confidence_band_at_observation: ConfidenceBand`.

## The band-at-observation gap (ASSUM-003 — read carefully)

The `misconception` table is `(id, student_id, topic_name, text, observed_at)` — it does
**NOT** persist band-at-observation, and the W1 write path never wrote it. But the domain
`Misconception` requires the field. **Resolution (approved):** approximate it at read time
from the learner's CURRENT confidence band for that topic — `LEFT JOIN topic_confidence tc
ON tc.student_id = m.student_id AND tc.topic_name = m.topic_name`, using
`COALESCE(tc.band, 'struggling')`. This is "band now", not "band then"; the field has no
downstream consumer (the planner and `MisconceptionSnapshot` use only topic/text/observed_at),
so the approximation is acceptable. Do NOT add a column or touch the write path.

## Scope

**In scope**
- `get_recent_misconceptions` body only: `SELECT m.topic_name, m.text, m.observed_at,
  COALESCE(tc.band, 'struggling') AS band FROM misconception m LEFT JOIN topic_confidence tc
  ON (tc.student_id = m.student_id AND tc.topic_name = m.topic_name) WHERE m.student_id = :sid
  AND m.observed_at >= :cutoff ORDER BY m.observed_at DESC`.
- Cutoff computed app-side: `datetime.now(timezone.utc) - timedelta(days=window_days)`,
  bound as `:cutoff`. Boundary is INCLUSIVE (`>=`) — a misconception observed exactly
  `window_days` ago is returned (matches the retired graph path's `>= misconception_cutoff`).
- Row → `Misconception(text=..., topic_ref=row.topic_name, observed_at=..., confidence_band_at_observation=row.band)`.
- Empty list for a student with no in-window rows AND for an unknown student.

**Out of scope**
- `get_student_state` → TASK-SMP2-03 (leave raising). Its `recent_misconceptions` will reuse
  the SAME 30-day window but projects to `MisconceptionSnapshot` (no band field) — different
  projection, that task's job.
- Session CRUD → FEAT-SMP-003 (leave raising). Write methods are DONE — do not touch.

## Acceptance Criteria

- [ ] Returns one `student_model.Misconception` per `misconception` row for the student whose
      `observed_at` is within the trailing `window_days`, newest `observed_at` first.
- [ ] The window boundary is inclusive: a row observed exactly `window_days` ago (to the day)
      is INCLUDED; one observed `window_days + 1` ago is EXCLUDED.
- [ ] A caller-supplied `window_days` (e.g. 7) narrows the result relative to the default 30.
- [ ] `confidence_band_at_observation` is populated from the learner's current
      `topic_confidence.band` for that topic via LEFT JOIN, defaulting to `"struggling"` when
      no confidence row exists for the topic.
- [ ] `text` and `observed_at` come straight from the row; `topic_ref` = `topic_name`.
- [ ] A student with no in-window misconceptions returns `[]`; an unknown `student_id` returns `[]`.
- [ ] `observed_at` is timezone-aware UTC; `student_id` and `cutoff` are bound parameters.
- [ ] DB/connection errors propagate (not swallowed) so `knowledge.store.reads` degrades to empty.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Coach Validation

```bash
docker run -d --rm --name smp2-02-pg -e POSTGRES_USER=study_tutor \
  -e POSTGRES_PASSWORD=test -e POSTGRES_DB=study_tutor -p 55432:5432 postgres:16
export STUDY_TUTOR_PG_DSN="postgresql://study_tutor:test@localhost:55432/study_tutor"
.venv/bin/python -m alembic upgrade head

.venv/bin/python -m pytest tests/integration/knowledge/store/test_postgres_get_recent_misconceptions.py -v
.venv/bin/python -m pytest tests/unit/knowledge/store/ -v
.venv/bin/ruff check src/study_tutor/knowledge/store/postgres.py
docker stop smp2-02-pg
```

## Implementation Notes

- Compute the cutoff in Python (`datetime.now(timezone.utc) - timedelta(days=window_days)`)
  and bind it — deterministic/testable, and keeps the DESC scan aligned with
  `misconception_recent_idx (student_id, observed_at DESC)`.
- The LEFT JOIN (not INNER) is essential: a misconception on a topic the learner has no
  `topic_confidence` row for must still be returned (with `"struggling"`), not dropped.
- `ConfidenceBand` is a `Literal`; `COALESCE(..., 'struggling')` yields a valid band string —
  no Pydantic coercion issue. Do not `confidence_band_for(...)` here (no percentage to map).

## Boundary-test discipline (read the retro)

Scope-guard tests may assert `NotImplementedError` ONLY for the SESSION-CRUD methods. Do NOT
assert it for `get_student_state` (TASK-SMP2-03 implements it) or re-assert it for
`get_topic_confidences` (already implemented in TASK-SMP2-01). No transient-state assertions.

## BDD Scenarios

- Reading recent misconceptions returns those observed within the recency window
- Misconceptions are included or excluded at the recency-window edge *(Scenario Outline: 29/30/31 days)*
- A narrower recency window excludes an otherwise-recent misconception
- A recent misconception is returned with a confidence band at observation
- Reading confidences and misconceptions for an unknown learner returns empty results *(misconceptions half)*
