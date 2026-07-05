---
id: TASK-APP1-05
title: "seed-students CLI (idempotent identity rows) + dev-only reset endpoint"
task_type: feature
feature_id: FEAT-APP-001
wave: 5
implementation_mode: task-work
complexity: 4
dependencies: [TASK-APP1-04]
parent_feature_spec: features/http-app-access-adapter/http-app-access-adapter_summary.md
---

## Objective

Close the seed gap found in the 2026-07-05 alignment review and give the Mac's
live suite its test isolation. Two small, sharply-scoped tools: an idempotent
Postgres student-identity seed, and the env-flag-gated dev reset.

## Scope

**In scope**
- `study-tutor seed-students` CLI subcommand: inserts `student` identity rows
  (idempotent — `ON CONFLICT DO NOTHING` semantics) for given student ids
  (default: the ids in the configured token table). Identity rows ONLY —
  baseline `topic_confidence` seeding explicitly stays with FEAT-SMP-004
  (its ASSUM-010); do not touch the graph seed script.
- `POST /__dev__/reset` on the HTTP app, mounted ONLY when
  `STUDY_TUTOR_HTTP_DEV_RESET` is set: truncates `session` + `session_turn`
  rows only — learner-state tables (`student`, `topic_confidence`,
  `misconception`, `achievement`, `quest`) untouched, so XP/streak/confidence
  survive. When the flag is off the route does not exist (unknown route, not a
  403).
- Both recorded values must match the binding doc's dev section (TASK-APP1-01)
  — conform to the doc.

**Out of scope**
- Compose wiring of the flag (TASK-APP1-06); any change to
  `scripts/seed_student_model.py` (FEAT-SMP-004's decision).

## Acceptance Criteria

- [ ] `seed-students` run twice against an ephemeral DB leaves exactly one row
      per student and does not modify existing learner state
- [ ] After seeding, `start_session` succeeds for both dev-token students
      (closes the FK gap: `session.student_id REFERENCES student`)
- [ ] Reset clears all sessions + turns; banked XP/streak/confidence rows are
      byte-identical before/after (asserted against an ephemeral DB)
- [ ] With the flag unset, `POST /__dev__/reset` is an unknown route; the prod
      compose flavour never sets the flag
- [ ] All modified files pass project-configured lint/format checks with zero
      errors

## Test Requirements

DB-backed tests against an ephemeral Postgres (skip when `STUDY_TUTOR_PG_DSN`
unset): seed idempotency, FK-gap closure, reset truncation scope, flag-off
route absence. Scope-guard: never the NAS.

## Coach Validation

- `pytest tests/unit/ -q` + the DB-backed tests with an ephemeral DSN exported.
- Verify the truncation SQL names ONLY `session` and `session_turn`.
