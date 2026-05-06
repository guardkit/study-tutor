# Feature: MCP LLM Player and Coach Adapters

**Feature ID**: FEAT-6CC5
**Slug**: `mcp-llm-player-coach-adapters`
**Parent review**: TASK-REV-LCA1
**Status**: Planned (5 subtasks ready for implementation)
**Recommended path**: Path C (hybrid) — LLM emits per-criterion JSON, deterministic post-processing assembles verdict

## Problem

The Phase-0 `MCPAdapter.tutor_turn` path uses a single-LLM `LLMClient.generate`
shortcut. The full `PlayerCoachOrchestrator` + Coach factory + rubric pipeline
exists in `src/study_tutor/tutoring/` and is unit-tested, but **no production
`PlayerLike` or `CoachLike` adapter exists** — only inline stubs in
`tests/smoke/test_tutoring_loop.py`. Without these adapters, `cli/main.py:serve`
cannot inject an `orchestrator_factory` into the MCP adapter, so the live
runtime path stays Phase-0 and AC-DEMO-01.2 (Coach revision required) cannot be
satisfied.

## Solution

Wire the production orchestrator into `MCPAdapter.tutor_turn` via a per-turn
`orchestrator_factory` closure constructed in `cli/main.py:serve`. The factory
builds fresh `LLMPlayerAdapter` and `LLMCoachAdapter` instances on every turn
(per-turn isolation invariant). The Coach uses **Path C (hybrid)**: the LLM
emits per-criterion JSON; deterministic post-processing via
`parse_coach_output` assembles the `CoachVerdict`. The two-provider invariant
(D3) is enforced at boot via a smoke check that invokes the factory once and
discards the result.

## Subtasks

| # | ID | Title | Wave | Complexity | Mode |
|---|-----|-------|------|------------|------|
| 1 | TASK-LCA-001 | Implement LLMPlayerAdapter (respond + revise) with structured-only revise prompt | 1 | 5 | task-work |
| 2 | TASK-LCA-002 | Implement LLMCoachAdapter (Path C hybrid) + coach.md prompt + JSON parsing | 1 | 6 | task-work |
| 3 | TASK-LCA-003 | Add SessionState typed dataclass and update MCP adapter construction site | 1 | 4 | task-work |
| 4 | TASK-LCA-004 | Add `_default_coach_model()` helper, env var, and MCPAdapter boot smoke check | 1 | 4 | task-work |
| 5 | TASK-LCA-005 | Wire CLI orchestrator_factory closure and integration smokes | 2 | 5 | task-work |

**Total complexity**: 6/10 aggregate
**Estimated effort**: 8–12 hours
**Smoke gate**: `pytest -m "feat_lca and smoke"`

## Wave Structure

- **Wave 1** (parallel, Conductor recommended): TASK-LCA-001, TASK-LCA-002, TASK-LCA-003, TASK-LCA-004 — no file conflicts
- **Wave 2** (sequential after Wave 1): TASK-LCA-005 — integration

## Load-Bearing Invariants

- **D3 two-provider** — Coach provider must differ from Player provider exactly
- **ASSUM-008 structured-only revision** — no Coach free-text leaks into Player prompt
- **Per-turn factory isolation** — every turn gets a fresh orchestrator
- **Env-var snapshot at boot** — server restart required after rotation
- **Boot-time failure surfaces, not first-turn** — config errors visible before serving

## Acceptance Criteria

10 acceptance criteria (AC-LCA-01 through AC-LCA-10) covering boot smoke check,
per-turn isolation, structured-only revision, Path C verdict shape, malformed-
output fallback, env-var enforcement, two-provider invariant, Phase-1 metadata
shape, and live Lilymay session (with calibration-fallback wording per Context
A Q5). See per-task files for full ACs.

## Documentation

- **Implementation guide** (with Mermaid diagrams + §4 Integration Contracts): [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md)
- **Review report**: [.claude/reviews/TASK-REV-LCA1-review-report.md](../../../.claude/reviews/TASK-REV-LCA1-review-report.md)
- **Source brief**: [docs/research/ideas/llm-player-coach-adapters-brief.md](../../../docs/research/ideas/llm-player-coach-adapters-brief.md)
- **Feature spec summary**: [features/mcp-llm-player-coach-adapters/mcp-llm-player-coach-adapters_summary.md](../../../features/mcp-llm-player-coach-adapters/mcp-llm-player-coach-adapters_summary.md)

## Next Steps

1. Read [IMPLEMENTATION-GUIDE.md](./IMPLEMENTATION-GUIDE.md) — diagrams + integration contracts
2. Run Wave 1 in parallel: `/task-work TASK-LCA-001` (in workspace 1), `/task-work TASK-LCA-002` (in workspace 2), etc.
3. After Wave 1 completes: `/task-work TASK-LCA-005`
4. Run smoke gate: `pytest -m "feat_lca and smoke" -x`
5. Operator-conducted live Lilymay session (AC-LCA-10)

For autonomous execution after the structured YAML is produced:
`/feature-build FEAT-6CC5`
