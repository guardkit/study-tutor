# Feature: DeepAgents Tutoring Loop with Coach (FEAT-PH1-003)

**Generated:** 2026-04-29 by `/feature-plan` from [TASK-REV-DTL3](../TASK-REV-DTL3-plan-deepagents-tutoring-loop-with-coach.md)
**Phase:** Phase 1
**Stack:** python (Python 3.14, deepagents 0.5.3, Pydantic v2, asyncio, pytest)
**Status:** planned (5 subtasks)

---

## Problem

Every learner-facing tutor turn must be evaluated by a Coach against a
six-criterion weighted rubric (curriculum accuracy, AO alignment,
scaffolding depth, grade-appropriate language, constructive feedback,
quote fidelity), accepting at-or-above the 0.70 threshold and otherwise
driving a bounded Player revision cycle. At session end, a narrative
summary is generated and the session episode is persisted. Throughout,
the Coach owns its own per-observation misconception writes and the
Tutor handler dispatches the planner topic-confidence delta and the
session-end episode write — all through a single shared write helper,
all fire-and-forget per CC-13, none on the caller-facing path.

## Solution

A small `PlayerCoachOrchestrator` class owns each turn end-to-end. The
Coach is a deepagents `AsyncSubAgent` (per ADR-ARCH-012) constructed
via a `create_coach(...)` factory that enforces D5 (`tools=[]`, no
filesystem backend, never learner-facing), the two-provider invariant,
and the empty-prompt boundary structurally — not via prompt
instruction. The shared `GraphitiWriteHelper` (TASK-GSM-004) is the
single `add_episode` call site. `session.completed` emits on the
`active → ended` state transition BEFORE the F3 write task is scheduled
(DDR-003).

See [IMPLEMENTATION-GUIDE.md §2](IMPLEMENTATION-GUIDE.md#2-data-flow--read--write-paths)
for the data-flow diagram (the most important diagram in this guide).

## Subtasks (5)

| ID | Title | Wave | Complexity | Est. Min | Dependencies |
|----|-------|------|------------|----------|--------------|
| [TASK-DTL-001](TASK-DTL-001-coach-factory-structural-invariants.md) | Coach factory and structural invariants | 1 | 5 | 75 | — |
| [TASK-DTL-002](TASK-DTL-002-rubric-and-quote-fidelity.md) | Coach rubric scoring and quote-fidelity integration | 2 | 6 | 90 | TASK-DTL-001 |
| [TASK-DTL-003](TASK-DTL-003-orchestrator-revision-loop-concurrency.md) | Player-Coach orchestrator with bounded revision loop and concurrency isolation | 2 | 7 | 120 | TASK-DTL-001 |
| [TASK-DTL-004](TASK-DTL-004-async-write-helper-consumer-misconceptions.md) | Async write helper consumer for per-misconception writes (F1) | 1 | 5 | 75 | — |
| [TASK-DTL-005](TASK-DTL-005-session-end-summary-f3-emit-lifecycle.md) | Session-end summary, F3 episode write, session.completed emit, lifecycle race, and shutdown drain | 3 | 6 | 90 | TASK-DTL-003, TASK-DTL-004 |

**Total**: 22-28h sequential / **~14h elapsed** with parallel-when-safe wave 1 + wave 2.

## Wave Execution

```
Wave 1 (parallel-safe):
  ├─ TASK-DTL-001  Coach factory + invariants (ships GraphitiWriteHelper protocol)
  └─ TASK-DTL-004  Coach-side misconception dispatch + sanitiser

Wave 2 (parallel-safe; depends on Wave 1):
  ├─ TASK-DTL-002  Rubric scoring + quote-verifier seam
  └─ TASK-DTL-003  PlayerCoachOrchestrator + revision policy + concurrency

Wave 3 (sequential; depends on Waves 1 + 2):
  └─ TASK-DTL-005  Session-end + F3 + session.completed + drain integration
```

## Anchor Decisions Honoured

- **DDR-002** — Coach AsyncSubAgent owns F1; Tutor handler owns F2/F3;
  one shared helper.
- **DDR-003** — `session.completed` emits on state transition, BEFORE
  F3 task is scheduled.
- **CC-13 / ADR-ARCH-019** — Every Graphiti write fire-and-forget;
  failures log only.
- **D5** — Coach `tools=[]`, no filesystem backend, never learner-facing
  (structural enforcement at factory).
- **Two-provider invariant** — Coach.provider != Player.provider
  (factory-enforced).

## Resolved Low-Confidence Assumptions

- **ASSUM-006** — Coach reasoning > 200 words: recorded in full +
  `reasoning_long: bool = True` flag. No truncation, no rejection.
  (Recorded as design decision; no spec change required.)
- **ASSUM-011** — Shutdown grace: `GRAPHITI_DRAIN_WINDOW = 5.0`
  constant exposed by TASK-GSM-004's helper. Default consumed by
  TASK-DTL-005 with no per-call override.

## Cross-feature Dependencies

**Producers** (this feature consumes):
- TASK-GSM-002 (episode types — `MisconceptionObservation`, `SessionCompletedEpisode`)
- TASK-GSM-003 (Graphiti client wrapper)
- TASK-GSM-004 (async write helper — load-bearing; see [§4 of guide](IMPLEMENTATION-GUIDE.md#4-integration-contracts))

**Consumers** (this feature produces):
- FEAT-PH1-002 (planner consumes Coach observations indirectly via F2)
- FEAT-PH1-001 (student-state queries consume what F1, F2, F3 write)

## Files Generated

- `IMPLEMENTATION-GUIDE.md` — full implementation guide with 4 mandatory
  Mermaid diagrams (data flow, integration contract sequence, task
  dependency graph, §4 cross-feature integration contracts)
- `TASK-DTL-001-coach-factory-structural-invariants.md`
- `TASK-DTL-002-rubric-and-quote-fidelity.md`
- `TASK-DTL-003-orchestrator-revision-loop-concurrency.md`
- `TASK-DTL-004-async-write-helper-consumer-misconceptions.md`
- `TASK-DTL-005-session-end-summary-f3-emit-lifecycle.md`
- `.guardkit/features/FEAT-PH1-003.yaml` — structured feature file for
  AutoBuild integration

## Next Steps

1. Review [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) — especially
   §2 (data flow) and §4 (integration contracts).
2. Confirm cross-feature dependency surface with TASK-GSM-004 owner
   (helper interface in §4).
3. Begin Wave 1: `/task-work TASK-DTL-001` and `/task-work TASK-DTL-004`
   in parallel (or sequentially, your choice).
4. After Wave 1 lands, proceed to Wave 2: `/task-work TASK-DTL-002` and
   `/task-work TASK-DTL-003` in parallel.
5. After Waves 1+2 land, proceed to Wave 3: `/task-work TASK-DTL-005`.
6. Run smoke gate: `pytest -m "feat-ph1-003 and smoke" -x --no-cov`.

Or autonomously: `/feature-build FEAT-PH1-003`.
