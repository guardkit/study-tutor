# Feature Spec Summary: MCP LLM Player and Coach Adapters

**Slug**: `mcp-llm-player-coach-adapters`
**Stack**: python
**Generated**: 2026-05-06
**Source brief**: `docs/research/ideas/llm-player-coach-adapters-brief.md`
**Scenarios**: 24 total (5 smoke)
**Assumptions**: 15 total (8 high / 7 medium / 0 low confidence)
**Review required**: No

## Scope

Wire production `LLMPlayerAdapter` and `LLMCoachAdapter` into a per-turn
`PlayerCoachOrchestrator` factory used by `MCPAdapter.tutor_turn`, replacing
the Phase-0 single-LLM shortcut. The Coach follows Path C (LLM emits
per-criterion JSON; deterministic post-processing assembles the verdict via
`parse_coach_output`). The two-provider invariant is enforced at boot via a
smoke check that invokes the factory once and discards the result. The
Player revision prompt carries only structured criterion pointers — no Coach
free-text reasoning ever crosses the channel.

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (`@key-example`) | 5 |
| Boundary conditions (`@boundary`) | 4 (2 Outlines with 7 examples) |
| Negative cases (`@negative`) | 5 |
| Edge cases (`@edge-case`) | 10 (4 base + 6 expansion) |
| Smoke (`@smoke`) | 5 |
| Invariants (`@invariant`) | 6 |
| Security (`@security`) | 3 |
| Concurrency (`@concurrency`) | 2 |
| Fallback (`@fallback`) | 3 |

## Smoke Set (`@feat-lca and @smoke`)

These are the Coach-blocking oracles — any failure in this set should fail
the build:

1. A learner turn returns the Phase-1 metadata shape
2. Each turn is served by a freshly-constructed orchestrator
3. The Coach adapter returns a fully-shaped verdict for a valid response
4. The MCP server refuses to boot when Player and Coach share a provider
5. A non-JSON Coach LLM response routes the turn to fallback

## Load-Bearing Invariants

The spec encodes these as `@invariant` scenarios — they are safety/security
constraints, not feature logic:

| Invariant | Where enforced | Scenarios |
|-----------|----------------|-----------|
| D3 two-provider — Coach provider must differ from Player provider exactly | `validate_coach_config` (`coach/factory.py:326`) + boot smoke check | C1, C2 |
| ASSUM-008 structured-only revision channel — no Coach free-text into Player prompt | `LLMPlayerAdapter.revise()` prompt assembly | A5, C5, E1 (security expansion) |
| Per-turn factory isolation — every turn gets a fresh orchestrator | `MCPAdapter` factory closure in `cli/main.py:serve` | A2, D1, F1 |
| Env var snapshot — `AGENT_MODELS__*` resolved once at boot | `MCPAdapter.__init__` smoke check | G3 |
| Boot-time failure surfaces, not first-turn — config errors visible before users connect | `MCPAdapter.__init__` re-raise | C1, D4 |

## Deferred Items

None. All four base groups and all three expansion sub-groups were accepted
in full.

## Open Assumptions (low confidence)

None. All 15 assumptions were resolved at high or medium confidence — no
human-only review required before proceeding to `/feature-plan`.

## Medium-Confidence Assumptions Worth Watching

These are accepted but should be verified during planning/implementation:

- **ASSUM-LCA-005**: Coach JSON extra-criteria policy = silently discard.
  Lock down via the `parse_coach_output` test suite during planning.
- **ASSUM-LCA-006**: Player revision prompt carries `criterion_id` +
  `target_score` only (excludes `suggested_focus`). If Coach calibration in
  Phase-2 wants `suggested_focus` for richer revisions, this becomes a
  follow-up.
- **ASSUM-LCA-007**: SessionState required vs optional fields. Once the
  typed dataclass lands, the optional fields' default values matter for the
  MCP adapter construction site.
- **ASSUM-LCA-008**: Env var snapshot at boot. Document this in
  `.env.example` so operators understand a restart is required after
  rotation.
- **ASSUM-LCA-010**: Coach prompt <300 words. Phase-2 calibration may push
  this longer; not blocking for the demo.
- **ASSUM-LCA-015**: `quote_verifier` / `coach_handover` both `None` on
  first cut. Stage their wiring as a follow-up subtask after this feature
  lands.

## Cross-References

- Source brief: `docs/research/ideas/llm-player-coach-adapters-brief.md`
- Predecessor task (BLOCK-3a only):
  `tasks/backlog/wave5-mcp-blockers/TASK-GR-WIRE-orchestrator-and-session-end.md`
- Parent demo task: `tasks/backlog/TASK-GR-DEMO-end-to-end-mcp-tutor-session.md`
- Phase-1 plan: `docs/research/ideas/phase-1-build-plan.md` (DEC-04 Coach
  LLM-driven decision context)
- ADR: `docs/architecture/decisions/ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md`
- ADR: `docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md`
- Existing surfaces consumed by this feature:
  - `src/study_tutor/tutoring/orchestrator.py:123` (`PlayerLike`)
  - `src/study_tutor/tutoring/orchestrator.py:152` (`CoachLike`)
  - `src/study_tutor/tutoring/orchestrator.py:333` (`PlayerCoachOrchestrator`)
  - `src/study_tutor/tutoring/coach/factory.py:326` (`validate_coach_config`)
  - `src/study_tutor/tutoring/coach/rubric.py:597` (`parse_coach_output`)
  - `src/study_tutor/tutoring/coach/rubric.py:715` (`evaluate_player_turn`)
  - `src/study_tutor/llm/client.py:47` (`_default_player_model` — pattern to mirror)

## New Surfaces Created by This Feature

- `src/study_tutor/tutoring/adapters/` (new package)
  - `llm_player_adapter.py` — `LLMPlayerAdapter` implementing `PlayerLike`
  - `llm_coach_adapter.py` — `LLMCoachAdapter` implementing `CoachLike`
  - `session_state.py` — typed `SessionState` dataclass
- `roles/tutor/prompts/coach.md` (new asset; <300 words for Phase-1 demo)
- `RoleConfig.load_coach_prompt()` — new method mirroring `load_player_prompt()`
- `_default_coach_model()` in `src/study_tutor/llm/client.py` — reads
  `AGENT_MODELS__COACH_MODEL`, raises `LLMProviderError` if unset
- `MCPAdapter.__init__(orchestrator_factory=...)` — new constructor parameter
  + boot-time smoke check
- `cli/main.py:serve` — `orchestrator_factory` closure construction

## Integration with /feature-plan

Anticipated subtask shape (per brief §"Notes for /feature-plan"):

1. `LLMPlayerAdapter` + revision prompt (parallel)
2. `LLMCoachAdapter` + Coach prompt + JSON parsing (parallel)
3. `SessionState` typed dataclass + MCP adapter construction site (parallel)
4. `_default_coach_model()` + env var + boot smoke check (parallel)
5. Integration smoke test wiring + CLI factory closure (sequential after 1–4)

Smoke gate after final subtask: `pytest -m "feat_lca and smoke"`

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "MCP LLM Player and Coach Adapters" \
      --context features/mcp-llm-player-coach-adapters/mcp-llm-player-coach-adapters_summary.md \
      --context docs/research/ideas/llm-player-coach-adapters-brief.md
