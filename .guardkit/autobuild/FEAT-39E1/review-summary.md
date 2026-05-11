# Autobuild Review Summary: FEAT-39E1

**Status:** FAILED  
**Generated:** 2026-05-10 19:56 UTC

## Metrics

| Metric | Value |
|--------|-------|
| Total tasks | 18 |
| Total turns | 19 |
| Avg turns/task | 2.71 |
| Waves executed | 5 |
| First-attempt pass rate | 43% |

## Per-Task Outcomes

| Task | Wave | Turns | Outcome | Decision | Notes |
|------|------|-------|---------|----------|-------|
| TASK-NATS-PH1-001 | 1 | 3 | PASSED | already_completed |  |
| TASK-NATS-PH1-002 | 2 | 1 | PASSED | already_completed |  |
| TASK-NATS-PH1-003 | 2 | 1 | PASSED | already_completed |  |
| TASK-NATS-PH1-007 | 2 | 1 | PASSED | already_completed |  |
| TASK-NATS-PH1-006 | 3 | 4 | PASSED | already_completed |  |
| TASK-NATS-PH1-004 | 4 | 5 | PASSED | already_completed |  |
| TASK-NATS-PH1-005 | 5 | 4 | FAILED | timeout_budget_exhausted |  |

## Quality Metrics

- Task success rate: 86%
- First-turn approvals: 3/7
- SDK ceiling hits: 0

## Turn Efficiency

| Metric | Value |
|--------|-------|
| Avg turns/task | 2.7 |
| Single-turn tasks | 3 |
| Multi-turn tasks | 4 |
| Avg SDK turns/invocation | 39.2 |

## Key Findings

- Tasks required multiple turns before failing: TASK-NATS-PH1-005. Review coach feedback logs for recurring patterns.
