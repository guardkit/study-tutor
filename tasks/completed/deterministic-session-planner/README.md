# FEAT-PH1-002 — Deterministic Session Planner

Phase 1 deterministic, rule-based session planner that proposes the
next study topic from learner state at the start of every tutoring
session, without invoking an LLM in the planning step.

**Parent review**: [TASK-REV-DA72](../../in_review/TASK-REV-DA72-plan-deterministic-session-planner.md)
**Approach**: Sequential short-circuit pipeline of typed `Rule` objects (Strategy pattern).

---

## Problem

The Phase 0 tutoring runtime returned hard-coded session plans. Phase 1
must adapt: each session's topic should reflect the learner's
current confidence map, the topics that are stale, and the
misconceptions that have not yet been revisited. The planner must be
**deterministic** — same inputs, same plan, even across concurrent
calls — so tests are stable and the Coach's `ao_alignment` scoring
contract holds. This rules out an LLM in the planning path.

## Solution

A pipeline of five typed `Rule` objects iterated in priority order:

1. **Rule 1 — learner override** (short-circuits ranking)
2. **Rule 2 — active-quest** (Phase 2 stub, returns `None`)
3. **Rule 3 — weakest stale topic** (48-hour cooldown, deterministic tie-break)
4. **Rule 4 — recent unrevisited misconception**
5. **Rule 5 — achievement-near-unlock** (Phase 2 stub, returns `None`)

If all five return `None`, **rule 6** picks randomly from the
developing band. If even that is empty, the **baseline plan** ships.
The entire pipeline sits inside a single graceful-degradation
boundary in the MCP adapter — `session_id` is always issued, and no
failure mode propagates to the caller.

Determinism is **structural**: rules accept an injected `clock` and
seeded `random.Random` via `PlannerContext`. No rule reads
`datetime.now()` or `random` from module scope.

## Subtasks (7 across 5 waves)

| Wave | Task | Title | Mode |
|------|------|-------|------|
| 1 | [TASK-DSP-001](TASK-DSP-001-session-plan-and-baseline.md) | SessionPlan dataclass and BaselineSession helper | direct |
| 1 | [TASK-DSP-002](TASK-DSP-002-rule-protocol-and-context.md) | Rule protocol, PlannerContext, and Candidate types | direct |
| 2 | [TASK-DSP-003](TASK-DSP-003-rule-1-and-rule-3.md) | Rule 1 (learner override) and Rule 3 (weakest stale topic) | task-work |
| 2 | [TASK-DSP-004](TASK-DSP-004-rule-4-and-stubs.md) | Rule 4 (unrevisited misconception) and Rule 2/5 stubs | task-work |
| 3 | [TASK-DSP-005](TASK-DSP-005-pipeline-and-rule-6.md) | plan_session pipeline and rule-6 fallback | task-work |
| 4 | [TASK-DSP-006](TASK-DSP-006-mcp-adapter-and-degradation.md) | Wire plan_session into tutor_start_session and graceful-degradation boundary | task-work |
| 5 | [TASK-DSP-007](TASK-DSP-007-bdd-scenarios-and-guide.md) | BDD scenario execution, gap tests, and IMPLEMENTATION-GUIDE update | task-work |

Wave 1 and Wave 2 each have two parallel-safe tasks (Conductor
workspaces auto-named: `deterministic-session-planner-wave{N}-{i}`).
Waves 3–5 are sequential.

## Pre-implementation Sign-offs

All three medium-confidence assumptions resolved with measured data
on **2026-04-29**:

- **ASSUM-006** (2s `tutor_start_session` budget) — confirmed.
  Spike measured Graphiti reads `<0.2s` total, **>1.8s headroom**.
- **ASSUM-007** (5s student-model read timeout) — confirmed.
  Same data, **25× headroom**.
- **ASSUM-008** ("unrevisited misconception" depends on
  `SessionCompletedEpisode.topics_covered: list[str]`) — confirmed.
  TASK-GSM-002 in FEAT-PH1-001 implements the field.

Verbatim sign-off wordings in
[features/deterministic-session-planner/deterministic-session-planner_assumptions.yaml](../../../features/deterministic-session-planner/deterministic-session-planner_assumptions.yaml).

## Cross-feature Contract

The planner consumes
**`SessionCompletedEpisode.topics_covered: list[str]`** produced by
[TASK-GSM-002](../graphiti-student-model/TASK-GSM-002-episode-types.md)
in FEAT-PH1-001. Format constraint: list of plain topic-name strings
matching `Topic.name`. TASK-DSP-004 ships the seam test
`test_session_completed_episode_topics_covered_format` which validates
the contract at the boundary.

## Coverage

- 29 BDD scenarios in
  [features/deterministic-session-planner/deterministic-session-planner.feature](../../../features/deterministic-session-planner/deterministic-session-planner.feature)
  (4 smoke, 7 key-example, 6 boundary, 6 negative, 11 edge-case)
- 2 gap tests added in TASK-DSP-007:
  - `test_all_bands_empty_returns_baseline`
  - `test_post_write_read_consistency_does_not_block`
- Smoke scenarios serve as the feature-level smoke gate (R3) between
  waves under autobuild.

## Effort

- **Total**: 18–22 hours
- **Wave-parallel ceiling**: ~14 hours elapsed (Wave 1 + 2 done in
  parallel, Waves 3–5 sequential)

## See Also

- [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md) — full architecture
  with diagrams (data flow, integration contracts, task dependency
  graph) and integration-contract tables.
- [Review report](../../../.guardkit/reviews/TASK-REV-DA72-review-report.md)
  — full decision-mode analysis with options, risks, and rationale.
- [Spec summary](../../../features/deterministic-session-planner/deterministic-session-planner_summary.md)
- [FEAT-PH1-001 (graphiti-student-model)](../graphiti-student-model/README.md) —
  the producer of the read helpers and the `topics_covered` field.

## Next Step

```bash
/feature-build FEAT-PH1-002
# or, manually:
/task-work TASK-DSP-001
```
