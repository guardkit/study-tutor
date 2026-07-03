# Feature Spec Summary: Student Model Postgres Store

**Stack**: python
**Generated**: 2026-07-03T13:38:32Z
**Scenarios**: 28 total (4 smoke, 0 regression)
**Assumptions**: 13 total (2 resolved in spec review, 3 high / 5 medium / 3 low remaining)
**Review required**: Yes — 3 low-confidence assumptions remain (ASSUM-003/005/006); ASSUM-001 & ASSUM-002 resolved

## Scope

FEAT-SMP-001 / W1 of the student-model Postgres migration (ADR-ARCH-023): the JSONB schema + first
Alembic migration, the `ping` health check, and the synchronous transactional **write path** that
replaces the retired `GraphitiWriteHelper` F1/F2/F3 fire-and-forget flush points —
`record_session_completion` (session-end, atomic, idempotent on `session_id`), `record_misconception`
(F1), and `apply_confidence_update` (F2, band derived at write time). The reference schema
(`src/study_tutor/knowledge/store/schema_reference.sql`) is what the first migration encodes; the
runbook gate is **G7** (`alembic upgrade head`).

**Explicitly out of scope** (later waves): the read path (`get_student_state` /
`get_topic_confidences` / `get_recent_misconceptions`) → FEAT-SMP-002; session CRUD (`create_session`
/ `append_turn` / `list_sessions` / `get_turns` / `end_session`) → FEAT-SMP-003 (gated by G-CON); the
XP / streak / level / achievement / quest evaluation engine → Phase 2 (ADR-ARCH-013).

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 6 |
| Boundary conditions (@boundary) | 5 |
| Negative cases (@negative) | 3 |
| Edge cases (@edge-case) | 14 |

(Cross-cutting tags: `@migration` 4, `@write-path` 5, `@idempotency` 4, `@atomicity` 4,
`@concurrency` 3, `@security` 3, `@integration-boundary` 2, `@data-integrity` 3, `@smoke` 4.)

## Deferred Items

No scenario groups were deferred within this feature (Groups A–E all accepted). Deferred to later
**waves**: reads (FEAT-SMP-002), session persistence CRUD (FEAT-SMP-003, gated by G-CON), and the
gamification state engine (Phase 2).

## Open Assumptions (low confidence — verify before build)

- **ASSUM-003** — Write for an unknown learner is **rejected** (FK); alternative is auto-create.
- **ASSUM-005** — Prompt-injection rejection **dropped** (no extraction LLM remains); re-add only if a
  downstream surface feeds this text to an LLM.
- **ASSUM-006** — Standalone `record_misconception` (F1) is **append-only, no dedup** in W1; only
  `record_session_completion` is idempotent.

## Two cross-artifact conflicts this spec surfaced — both RESOLVED in spec review

1. **Band thresholds** — RESOLVED to **40/60/80**. `student_model.confidence_band_for` said 40/70/90;
   `gamification/design.md §6.1` + the hackathon plan §5.2 (Mastery at 80%, and the worked example
   "76% → one session → Macbeth Master") establish 80% as the Mastered entry. `confidence_band_for` +
   docstrings + the boundary test were updated to 40/60/80; the knowledge/planner/seeding suite re-ran
   with no new failures. (ASSUM-001)
2. **XP persistence** — RESOLVED. `session.xp_awarded` (`INTEGER NOT NULL DEFAULT 0 CHECK >= 0`) added
   to `schema_reference.sql`; idempotent via the `session_id` PK. Cumulative `total_xp`/`level`/`streak`
   on `student` documented as a Phase 2 addition. (ASSUM-002)

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "Student Model Postgres Store" \
      --context features/student-model-postgres-store/student-model-postgres-store_summary.md \
      --context src/study_tutor/knowledge/store/port.py \
      --context src/study_tutor/knowledge/store/postgres.py \
      --context src/study_tutor/knowledge/store/schema_reference.sql
