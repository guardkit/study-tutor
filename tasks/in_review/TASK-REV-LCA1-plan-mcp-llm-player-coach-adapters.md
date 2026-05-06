---
id: TASK-REV-LCA1
title: "Plan: MCP LLM Player and Coach Adapters"
task_type: review
review_mode: decision
review_depth: standard
status: review_complete
priority: high
created: 2026-05-06T00:00:00+00:00
updated: 2026-05-06T01:00:00+00:00
review_results:
  mode: decision
  depth: standard
  findings_count: 6
  recommendations_count: 5
  recommended_path: path-c-hybrid
  estimated_subtasks: 5
  estimated_waves: 2
  aggregate_complexity: 6
  estimated_minutes: 435
  smoke_gate: 'pytest -m "feat_lca and smoke"'
  report_path: .claude/reviews/TASK-REV-LCA1-review-report.md
  awaiting: decision-checkpoint
complexity: 7
tags:
  - mcp
  - tutoring
  - player-adapter
  - coach-adapter
  - phase-1
  - review
  - decision-point
  - feat-lca
parent_task: TASK-GR-DEMO
related:
  - TASK-GR-WIRE
  - TASK-GR-PMT
  - TASK-GR-DEMO
context_files:
  - features/mcp-llm-player-coach-adapters/mcp-llm-player-coach-adapters_summary.md
  - docs/research/ideas/llm-player-coach-adapters-brief.md
  - src/study_tutor/tutoring/orchestrator.py
  - src/study_tutor/tutoring/coach/factory.py
  - src/study_tutor/tutoring/coach/rubric.py
  - src/study_tutor/llm/client.py
  - src/study_tutor/mcp/adapter.py
  - tests/smoke/test_tutoring_loop.py
feature_slug: mcp-llm-player-coach-adapters
decision_required: true
clarification:
  context_a:
    timestamp: 2026-05-06T00:00:00+00:00
    decisions:
      focus: all
      tradeoff: balanced
      assumptions_to_spotlight:
        - ASSUM-LCA-005
        - ASSUM-LCA-006
        - ASSUM-LCA-007
        - ASSUM-LCA-008
        - ASSUM-LCA-010
        - ASSUM-LCA-015
      sequencing_proposal: keep-4-parallel-1-sequential
      coach_calibration_fallback_ac: include-explicit-fallback
test_results:
  status: not_applicable
---

# Plan: MCP LLM Player and Coach Adapters

## Description

Wire production `LLMPlayerAdapter` and `LLMCoachAdapter` into a per-turn
`PlayerCoachOrchestrator` factory used by `MCPAdapter.tutor_turn`, replacing
the Phase-0 single-LLM shortcut. The Coach follows **Path C (hybrid)**: the
LLM emits per-criterion JSON, deterministic post-processing assembles the
verdict via `parse_coach_output`. The two-provider invariant (D3) is enforced
at boot via a smoke check that invokes the factory once and discards the
result. The Player revision prompt carries only structured criterion pointers
— no Coach free-text reasoning ever crosses the channel (ASSUM-008).

## Source Materials

- **Feature spec summary**: `features/mcp-llm-player-coach-adapters/mcp-llm-player-coach-adapters_summary.md`
  - 24 scenarios total (5 smoke, 6 invariants, 3 security, 2 concurrency, 3 fallback)
  - 15 assumptions (8 high / 7 medium confidence, 0 low — no human-only review required)
  - All four base groups + all three expansion sub-groups accepted in full
- **Source brief**: `docs/research/ideas/llm-player-coach-adapters-brief.md`
  - Full design analysis including Path A/B/C trade-off and recommendation (Path C)
  - Acceptance criteria sketches AC-LCA-01 through AC-LCA-10
  - 7 design decisions D-COACH-01 through D-COACH-07

## Scope (from spec)

### New surfaces created

- `src/study_tutor/tutoring/adapters/` (new package)
  - `llm_player_adapter.py` — `LLMPlayerAdapter` implementing `PlayerLike`
  - `llm_coach_adapter.py` — `LLMCoachAdapter` implementing `CoachLike`
  - `session_state.py` — typed `SessionState` dataclass
- `roles/tutor/prompts/coach.md` (new asset; <300 words for Phase-1 demo)
- `RoleConfig.load_coach_prompt()` — new method mirroring `load_player_prompt()`
- `_default_coach_model()` in `src/study_tutor/llm/client.py` — reads `AGENT_MODELS__COACH_MODEL`, raises `LLMProviderError` if unset
- `MCPAdapter.__init__(orchestrator_factory=...)` — new constructor parameter + boot-time smoke check
- `cli/main.py:serve` — `orchestrator_factory` closure construction

### Out of scope (already shipped or deferred)

- `tutor_session_end` wiring — already shipped by TASK-GR-WIRE
- `GraphitiWriteHelper` / `EventBus` / `GraphitiClient` construction — already shipped by TASK-GR-WIRE
- TopicConfidence write helper — that's TASK-GR-CONF
- Coach calibration — Phase-2 ("Saturday morning" task per TASK-REV-GRD5)
- Player prompt revision — that's TASK-GR-PMT
- Phase-1 deepagents `AsyncSubAgent` migration — downstream wave per DDR-002

## Load-Bearing Invariants

| Invariant | Where enforced | Scenarios |
|-----------|----------------|-----------|
| D3 two-provider — Coach provider must differ from Player provider exactly | `validate_coach_config` (`coach/factory.py:326`) + boot smoke check | C1, C2 |
| ASSUM-008 structured-only revision channel — no Coach free-text into Player prompt | `LLMPlayerAdapter.revise()` prompt assembly | A5, C5, E1 (security expansion) |
| Per-turn factory isolation — every turn gets a fresh orchestrator | `MCPAdapter` factory closure in `cli/main.py:serve` | A2, D1, F1 |
| Env var snapshot — `AGENT_MODELS__*` resolved once at boot | `MCPAdapter.__init__` smoke check | G3 |
| Boot-time failure surfaces, not first-turn — config errors visible before users connect | `MCPAdapter.__init__` re-raise | C1, D4 |

## Acceptance Criteria (from brief)

- [ ] **AC-LCA-01** Per-turn factory isolation (smoke): two concurrent `tutor_turn` calls receive distinct `PlayerCoachOrchestrator` instances; no Coach observation crosses sessions
- [ ] **AC-LCA-02** Boot-time smoke check (key-example): `MCPAdapter.__init__` raises `OrchestratorConfigurationError` / `CoachConfigurationError` if Player + Coach share a provider, before serving begins
- [ ] **AC-LCA-03** Player respond happy path (key-example): `LLMPlayerAdapter.respond()` sends player prompt as system, learner_message as user; returns `LLMClient.generate` output verbatim
- [ ] **AC-LCA-04** Player revise structured-only (security): assembled prompt contains `criterion_id` + `target_score`, contains NO Coach free-text passthrough
- [ ] **AC-LCA-05** Coach LLM verdict (key-example, Path C): `evaluate()` invokes `LLMClient(provider=COACH_MODEL).generate(prompt, system=coach_prompt)`; output parsed via `parse_coach_output`; returns fully-shaped `CoachVerdict`
- [ ] **AC-LCA-06** Coach malformed-output fallback (negative): non-JSON Coach output → `MalformedCoachOutputError` → orchestrator routes to `decision=fallback`
- [ ] **AC-LCA-07** Env var enforcement (configuration): unset `AGENT_MODELS__COACH_MODEL` → `_default_coach_model()` raises clear `LLMProviderError` naming the missing env var
- [ ] **AC-LCA-08** Two-provider invariant at boot (configuration): same provider for both → `CoachConfigurationError` with both providers named + D3 reference
- [ ] **AC-LCA-09** Phase-1 metadata shape (integration): `tutor_turn` response has `tutor_response`, `decision`, `attempts`, `flagged_for_review`, `duration_seconds`; `decision ∈ {accept, exhausted, fallback}`
- [ ] **AC-LCA-10** Live session (smoke, operator-conducted): 2-turn Lilymay session shows `attempts > 1` (Coach revision) OR explicitly documents the calibration follow-up if Coach never disagrees (per Q5 Context A clarification)

## Medium-Confidence Assumptions to Spotlight (Q3 Context A clarification)

All six flagged for explicit planning notes / acceptance-gate wiring:

1. **ASSUM-LCA-005** — Coach JSON extra-criteria policy = silently discard. Lock down via the `parse_coach_output` test suite during planning
2. **ASSUM-LCA-006** — Player revision prompt carries `criterion_id` + `target_score` only (excludes `suggested_focus`). Phase-2 calibration may want `suggested_focus` for richer revisions — follow-up
3. **ASSUM-LCA-007** — `SessionState` required vs optional fields. Once typed dataclass lands, optional defaults matter for MCP adapter construction site
4. **ASSUM-LCA-008** — Env var snapshot at boot. Document in `.env.example` so operators understand a restart is required after rotation
5. **ASSUM-LCA-010** — Coach prompt <300 words. Phase-2 calibration may push longer; not blocking for the demo
6. **ASSUM-LCA-015** — `quote_verifier` / `coach_handover` both `None` on first cut. Stage their wiring as a follow-up subtask after this feature lands

## Anticipated Subtask Shape (per brief §"Notes for /feature-plan")

Wave structure: subtasks 1–4 parallel; subtask 5 sequential after 1–4 land.

1. `LLMPlayerAdapter` + revision prompt template (parallel)
2. `LLMCoachAdapter` + Coach prompt + JSON parsing (parallel)
3. `SessionState` typed dataclass + MCP adapter construction site (parallel)
4. `_default_coach_model()` + env var + boot smoke check (parallel)
5. Integration smoke test wiring + CLI factory closure (sequential after 1–4)

Smoke gate after final wave: `pytest -m "feat_lca and smoke"`

## Cross-Feature Integration Contracts (anticipated §4)

- `MCPAdapter.__init__(orchestrator_factory=...)` — consumer of this feature; producer is `cli/main.py:serve` factory closure
- `PlayerCoachOrchestrator.__init__` — consumer; producer is the factory closure
- `AGENT_MODELS__COACH_MODEL` env var — produced by operator config; consumed by `_default_coach_model()` → `LLMCoachAdapter`

## Review Scope (Context A clarification)

- **Focus**: All areas (technical correctness, architecture, security/safety invariants, testability)
- **Trade-off priority**: Balanced (speed/quality/maintainability weighted equally)
- **Subtask sequencing**: Keep 4-parallel + 1-sequential as specified in brief
- **Coach calibration fallback AC**: Include explicit fallback wording on AC-LCA-10 (zero-revision turns are a known calibration gap, not a test failure)

## Test Requirements

- Unit tests for `LLMPlayerAdapter.respond()` and `revise()` (per-turn isolation, structured-only revision channel)
- Unit tests for `LLMCoachAdapter.evaluate()` (verdict shape, malformed-output fallback)
- Unit tests for `_default_coach_model()` (env var enforcement)
- Unit tests for `MCPAdapter.__init__` boot smoke check (same-provider rejection)
- Integration test for per-turn factory isolation (AC-LCA-01)
- Integration smoke test for Phase-1 metadata shape (AC-LCA-09)
- Operator-conducted live Lilymay smoke (AC-LCA-10)

## Implementation Notes

[To be populated by /task-review with technical options analysis and recommended approach]

## Test Execution Log

[Automatically populated by /task-work]
