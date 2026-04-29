# Feature Spec Summary: Deterministic Session Planner

**Stack**: python
**Generated**: 2026-04-29
**Scenarios**: 29 total (4 smoke, 0 regression)
**Assumptions**: 8 total (2 high / 6 medium / 0 low confidence)
**Review required**: No

## Scope

Specifies the Phase 1 deterministic session planner (FEAT-PH1-002): the
`SessionPlan` shape, the active ranking rules (1 — learner override, 3 —
weakest stale topic, 4 — topic with recent unrevisited misconception), the
rule-6 fallback (random selection from the developing band), and the
integration with `tutor_start_session` on the MCP adapter. Phase 2 rules
(2 active-quest and 5 achievement-near-unlock) are required to exist as
stubs but never select a topic. The planner reads via the FEAT-PH1-001
query helpers and degrades to a baseline plan when those helpers cannot
return state.

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 7 |
| Boundary conditions (@boundary) | 6 |
| Negative cases (@negative) | 6 |
| Edge cases (@edge-case) | 11 |

## Deferred Items

None — all four originally-proposed groups and all six edge-case-expansion
scenarios were accepted in curation.

## Open Assumptions (low confidence)

None — all eight assumptions resolved at high or medium confidence.

The medium-confidence assumptions worth re-checking during plan review:

- ASSUM-002 — default `suggested_duration_minutes` of 20 (acceptable
  range 10–45 minutes) is convention, not specification
- ASSUM-003 — `focus_aos` cardinality bounds (1–6)
- ASSUM-004 — tie-break order (oldest-last-studied first, stable
  alphabetical) is a determinism choice, not a specified one
- ASSUM-006 — 2-second `tutor_start_session` handler budget mirrors the
  session-end budget by parity with ADR-ARCH-019 / SR-08
- ASSUM-007 — 5-second student-model read timeout reuses the
  specialist-agent precedent
- ASSUM-008 — "unrevisited" misconception definition depends on the
  FEAT-PH1-001 `session_completed` episode payload shape

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "Deterministic Session Planner" \
      --context features/deterministic-session-planner/deterministic-session-planner_summary.md
