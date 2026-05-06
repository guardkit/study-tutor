# LLM Player + Coach Adapter Wiring — Feature Brief

**Status:** Draft brief for `/feature-spec` and `/feature-plan`
**Author:** Carve-out from TASK-GR-WIRE (Wave 5) — see "Provenance" below
**Target wave:** Wave 5 (Phase-1 gate closure) or Wave 6
**Predecessor:** TASK-GR-WIRE-orchestrator-and-session-end (BLOCK-3a only)

## Purpose

Wire the production `MCPAdapter.tutor_turn` path through `PlayerCoachOrchestrator.run_turn` instead of the Phase-0 single-LLM `LLMClient.generate` shortcut. Today the orchestrator + bounded revision loop + Coach factory + rubric pipeline are all in `src/study_tutor/tutoring/` and unit-tested, but **no production `PlayerLike` or `CoachLike` adapter exists** (only inline stubs in `tests/smoke/test_tutoring_loop.py:65-146`). Without these adapters, `cli/main.py:serve` cannot inject an `orchestrator_factory` into the MCP adapter, so the live runtime path is still Phase-0 and AC-DEMO-01.2 (Coach revision required) cannot be satisfied.

This feature designs and implements:

1. **`LLMPlayerAdapter`** — production `PlayerLike` wrapping `LLMClient` with `respond()` + `revise()` semantics.
2. **`LLMCoachAdapter`** — production `CoachLike` returning `CoachVerdict`. Strategy choice (deterministic rubric vs LLM-driven) is the load-bearing design decision below.
3. **Coach system prompt** — new asset at `roles/tutor/prompts/coach.md` (currently only `player.md` exists).
4. **`session_state` schema** — concrete shape the adapters consume (today the orchestrator's `session_state: Any` is unspecified at the protocol boundary).
5. **`AGENT_MODELS__COACH_MODEL` env var + `_default_coach_model()` helper** — enforces the two-provider invariant (`coach/factory.py:385`) at config-load time.
6. **`orchestrator_factory` closure in `cli/main.py:serve`** — per-turn construction; wired into `MCPAdapter(orchestrator_factory=...)`.
7. **Boot-time smoke check** at `MCPAdapter.__init__`: factory is invoked once and the result discarded, surfacing `OrchestratorConfigurationError` (e.g. same-provider Coach + Player) at server boot rather than at first user turn.

## Provenance

This feature was carved out of TASK-GR-WIRE (Wave 5) on 2026-05-05. The original task bundled BLOCK-1 (orchestrator wiring) and BLOCK-3a (`perform_session_end` wiring) on the rationale that they share a constructor. Investigation during /task-work surfaced that BLOCK-1 has substantial undesigned dependencies (Coach prompt, Coach output strategy, `session_state` shape, scorer wiring) that warrant a Propose-Review BDD spec rather than under-task-work-pressure design. BLOCK-3a is shipping standalone in TASK-GR-WIRE.

See `tasks/backlog/wave5-mcp-blockers/TASK-GR-WIRE-orchestrator-and-session-end.md` (post-narrowing) for the BLOCK-3a-only scope and the descope rationale.

## In scope

- `src/study_tutor/tutoring/adapters/` (new package): `llm_player_adapter.py`, `llm_coach_adapter.py`, plus a typed `SessionState` dataclass.
- `roles/tutor/prompts/coach.md` (new asset).
- `src/study_tutor/llm/client.py` extension: `_default_coach_model()` reading `AGENT_MODELS__COACH_MODEL` (no default — unset must raise a clear configuration error at boot, since the two-provider invariant requires explicit divergence from `AGENT_MODELS__REASONING_MODEL`).
- `src/study_tutor/cli/main.py:serve`: build `orchestrator_factory` closure, pass to `MCPAdapter`. Coordinates with TASK-GR-WIRE which already wires `write_helper` / `event_bus` / `graphiti_client`.
- `MCPAdapter.__init__`: invoke `orchestrator_factory()` once as a smoke check, discard result.
- `.env.example`: add `AGENT_MODELS__COACH_MODEL=` placeholder with documentation.
- Unit tests: per-turn factory isolation invariant; Player adapter `respond()`/`revise()` behaviour; Coach adapter verdict shape; smoke-check raises on same-provider config.
- Integration smoke: a 2-turn live session against the seeded Lilymay state showing the Phase-1 metadata shape (`tutor_response`, `decision`, `attempts`, `flagged_for_review`, `duration_seconds`).

## Out of scope

- `tutor_session_end` wiring (already shipped by TASK-GR-WIRE).
- `GraphitiWriteHelper` / `EventBus` / `GraphitiClient` construction (already shipped by TASK-GR-WIRE).
- TopicConfidence write helper — that's TASK-GR-CONF (consumes the `write_helper` injection point).
- Coach calibration (Phase-2 "Saturday morning" task per TASK-REV-GRD5).
- Player prompt revision (that's TASK-GR-PMT).
- Phase-1 deepagents `AsyncSubAgent` migration (DDR-002 says the existing `Coach` class is shape-compatible; that migration lands in a downstream wave).

## Architectural context (existing surfaces this feature must integrate with)

| Surface | File | Contract |
|---|---|---|
| `PlayerLike` Protocol | `src/study_tutor/tutoring/orchestrator.py:123-149` | `async respond(*, session_state, learner_message) -> str`; `async revise(*, session_state, learner_message, previous_response, rubric_feedback: list[RubricFeedback]) -> str`. **No free-text channel for Coach reasoning** (ASSUM-008). |
| `CoachLike` Protocol | `src/study_tutor/tutoring/orchestrator.py:152-170` | `async evaluate(*, session_state, learner_message, player_response) -> CoachVerdict`. Raises `CoachUnavailableError` on failure → orchestrator routes to unevaluated-turn fallback (`@negative @fallback`). |
| `PlayerCoachOrchestrator.__init__` | `src/study_tutor/tutoring/orchestrator.py:351-404` | Keyword-only DI: `player`, `coach`, `quote_verifier=None`, `coach_handover=None`, `on_flag=None`, `latency_budget_seconds`, `max_revision_attempts`. |
| `validate_loop_configuration` | `src/study_tutor/tutoring/orchestrator.py:249-308` | Refuses `route_coach_reasoning_to_learner=True`, `revision_input_channel != "rubric_feedback"`, or out-of-range `max_revision_attempts`. |
| `validate_coach_config` | `src/study_tutor/tutoring/coach/factory.py:326-397` | **D3 two-provider invariant**: rejects `coach_config.provider == player_config.provider` exactly (no canonicalisation). Surfaces as `CoachConfigurationError` (subclass of `ValueError`). |
| `evaluate_player_turn` | `src/study_tutor/tutoring/coach/rubric.py:715-805` | Deterministic rubric pipeline: `verify_quotes → score_rubric → dispatch misconceptions`. Requires a `ScorerMap` of 6 criterion scorers. |
| `parse_coach_output` | `src/study_tutor/tutoring/coach/rubric.py:597-650` | LLM-output → `CoachVerdict`. Accepts `CoachVerdict` / `dict` / JSON string. Raises `MalformedCoachOutputError` (subclass of `ValueError`). |
| `LLMClient` | `src/study_tutor/llm/client.py:56-107` | Sync, string-in / string-out. `LLMClient(provider=...).generate(prompt, system=None)`. Construct per call site (SR-03). |
| `_default_player_model` | `src/study_tutor/llm/client.py:47-53` | Reads `AGENT_MODELS__REASONING_MODEL` at call time; defaults to `"local"`. **Pattern to mirror for Coach.** |
| Player prompt | `roles/tutor/prompts/player.md` | Existing Phase-0 prompt; `RoleConfig.load_player_prompt()` returns it. |

## Key design decisions to surface in the BDD spec

These are the `@assumption` candidates the spec should call out for explicit user signoff (per the `/feature-spec` Propose-Review pattern).

### D-COACH-01: Coach evaluator strategy — LLM-driven vs deterministic-rubric

**Two viable paths:**

**Path A — LLM-driven Coach** (DEC-04 alignment per `phase-1-build-plan.md`):
- Coach adapter calls `LLMClient(provider=_default_coach_model()).generate(prompt=..., system=coach_system_prompt)`.
- LLM returns a JSON `CoachVerdict` payload.
- Adapter calls `parse_coach_output(raw)` → `CoachVerdict`.
- Misconceptions in the verdict are dispatched fire-and-forget via `Coach.schedule_misconception_write` (DDR-002).
- **Risk:** LLM JSON output reliability. `parse_coach_output` raises `MalformedCoachOutputError` on bad output; orchestrator routes to fallback. Need to budget for fallback rate during Lilymay seeded session.
- **Requires:** Coach system prompt (D-COACH-02), JSON-schema steering in the prompt, structured-output reliability target.

**Path B — Deterministic rubric Coach**:
- Coach adapter constructs a `ScorerMap` of 6 production scorers and calls `evaluate_player_turn(coach=..., player_response=..., turn_context=..., verifier=..., scorers=...)`.
- No LLM call on the Coach side.
- **Risk:** No production scorers exist (only test fixtures in `tests/unit/tutoring/coach/test_rubric.py`). Each criterion needs a defensible scoring algorithm (curriculum_accuracy, ao_alignment, scaffolding_depth, grade_appropriate_language, constructive_feedback, quote_fidelity).
- **Requires:** 6 scorer implementations — non-trivial design surface for rubric criteria.

**Path C — Hybrid** (LLM scores, deterministic clamp/parse): Coach LLM emits per-criterion scores in JSON; deterministic code computes weighted_total, clamps to [0,1], builds `RubricFeedback` for below-threshold criteria, dispatches misconceptions. This is essentially Path A with stricter prompt steering toward per-criterion output rather than verdict-level output, then letting `parse_coach_output` handle validation.

**Recommendation for spec:** Path C (hybrid) — gets the LLM signal while keeping the verdict shape deterministic and grep-checkable. Surfaces in spec as `@assumption ASSUM-COACH-01: LLM produces per-criterion JSON; deterministic post-processing builds verdict`.

### D-COACH-02: Coach system prompt content

No Coach prompt exists. Spec should call out the `@assumption` that the prompt:
- Instructs the LLM to score against the six rubric criteria with `0.0-1.0` numeric values + 1-sentence evidence each.
- Forbids free-text reasoning leaking into rubric_feedback (ASSUM-008).
- Returns JSON matching the `CoachVerdict` schema (or per-criterion subset under Path C).
- Lives at `roles/tutor/prompts/coach.md` and is loaded via a new `RoleConfig.load_coach_prompt()` method (mirrors `load_player_prompt()`).
- Initial draft kept short (<300 words) — Coach calibration is Phase-2 and the demo only requires plumbing-correct revision behaviour.

### D-COACH-03: `session_state` schema

The orchestrator threads `session_state: Any` through `Player.respond`, `Player.revise`, `Coach.evaluate`. Today MCP adapter passes `{"session_id": session_id}` — insufficient for any real adapter. Spec should propose a typed `SessionState` dataclass with:
- `session_id: str` (already there)
- `student_id: str` (the learner subject — adapters need it for prompt personalisation and Coach group-id construction)
- `text_name: str | None` (drives Coach quote-fidelity grounding; matches the smoke test's `{"text_name": "macbeth"}`)
- `topic: str | None` (from the planner's `SessionPlan.topic_name`)
- `focus_aos: tuple[str, ...]` (from `SessionPlan.focus_aos`)
- `mode: str = "tutor"` (matches `TurnContext.mode`)

Spec should call out the `@assumption` that this is the boundary type and adapters depend on it. The MCP adapter constructs it from cached `SessionPlan` + `TutorSession`.

### D-COACH-04: Player revision prompt template

The `revise()` contract takes `rubric_feedback: list[RubricFeedback]` (each with `criterion_id` + `suggested_focus` + `target_score`). Spec should propose a deterministic template (no LLM call to assemble it) that:
- Pastes the original learner message and the previous response.
- Lists each below-threshold criterion as a structured pointer (NOT free text).
- Instructs the Player to revise focusing on those criteria.
- Lives in `LLMPlayerAdapter` as a constant or `roles/tutor/prompts/player_revise.md`.

### D-COACH-05: Coach env var convention

Decision: introduce `AGENT_MODELS__COACH_MODEL` mirroring `AGENT_MODELS__REASONING_MODEL`. **No fallback default** — unset must raise at config-load. The two-provider invariant requires the operator to explicitly choose a Coach provider distinct from the Player.

`.env.example` updates:
```
AGENT_MODELS__REASONING_MODEL=local       # Player (Phase 0 default — GB10 fine-tune)
AGENT_MODELS__COACH_MODEL=                 # Coach — must differ from REASONING_MODEL (D3 invariant)
```

`_default_coach_model()` raises a clear `LLMProviderError` if unset.

### D-COACH-06: `quote_verifier` and `coach_handover` initial cut

Per TASK-GR-WIRE original spec: both can be `None` on first cut. Spec should call this out as an `@assumption` and stage their wiring as a follow-up subtask. With both `None`, the orchestrator skips the verifier and passes raw Player response to the Coach (FEAT-PH1-003 legacy path).

### D-COACH-07: `on_flag` callback

Wire to a logger-only callback emitting structured `event="orchestrator_turn_flagged"` log lines on `flagged_for_review=True` turns. No DB write, no metric backend (Phase-2 concern). Surfaces over-budget latency, exhaustion, and fallback dispatches in stderr for the demo.

## Acceptance criteria sketches (BDD-shape)

These are starting points for `/feature-spec` to expand into Gherkin scenarios.

**AC-LCA-01 (per-turn factory isolation, smoke):**
> Given an `MCPAdapter` constructed with an `orchestrator_factory`,
> When `tutor_turn` is invoked twice concurrently for two different sessions,
> Then each invocation receives a distinct `PlayerCoachOrchestrator` instance,
> And no `Coach` observation from session A appears in session B's verdict path.

**AC-LCA-02 (boot-time smoke check, key-example):**
> Given a `MCPAdapter` constructed with an `orchestrator_factory` whose Player and Coach share a provider,
> When the constructor runs the smoke check,
> Then `OrchestratorConfigurationError` (or `CoachConfigurationError`) is raised before the server starts serving.

**AC-LCA-03 (Player respond happy path, key-example):**
> Given an `LLMPlayerAdapter` wrapping `LLMClient(provider="local")`,
> When `respond(session_state=..., learner_message="Why does Macbeth murder Duncan?")` is called,
> Then the player prompt is sent as the system message and the learner_message as the user prompt,
> And the response string is returned verbatim from `LLMClient.generate`.

**AC-LCA-04 (Player revise structured-only, security):**
> Given an `LLMPlayerAdapter` and `rubric_feedback=[RubricFeedback(criterion_id="scaffolding_depth", suggested_focus="scaffolding_depth", target_score=0.7)]`,
> When `revise(...)` is called,
> Then the assembled prompt contains the criterion id and target score,
> And it contains NO Coach free-text or reasoning passthrough,
> And the response is returned verbatim from `LLMClient.generate`.

**AC-LCA-05 (Coach LLM verdict, key-example — Path A or C):**
> Given an `LLMCoachAdapter` configured with `AGENT_MODELS__COACH_MODEL=bedrock` (or any non-`local` provider),
> When `evaluate(session_state=..., learner_message=..., player_response=...)` is called,
> Then `LLMClient(provider="bedrock").generate(prompt=..., system=coach_system_prompt)` is invoked,
> And the LLM output is parsed via `parse_coach_output`,
> And a fully-shaped `CoachVerdict` is returned.

**AC-LCA-06 (Coach malformed-output fallback, negative):**
> Given an `LLMCoachAdapter` whose LLM returns a non-JSON string,
> When `evaluate(...)` is called,
> Then `MalformedCoachOutputError` is raised,
> And the orchestrator catches it and routes to the unevaluated-turn fallback (`decision=fallback`).

**AC-LCA-07 (env var enforcement, configuration):**
> Given `AGENT_MODELS__COACH_MODEL` is unset,
> When `_default_coach_model()` is called,
> Then a clear `LLMProviderError` is raised naming the missing env var.

**AC-LCA-08 (two-provider invariant at boot, configuration):**
> Given `AGENT_MODELS__REASONING_MODEL=local` and `AGENT_MODELS__COACH_MODEL=local`,
> When the MCP server boots,
> Then `CoachConfigurationError` is raised at the boot smoke check,
> And the error message names both providers and references the D3 invariant.

**AC-LCA-09 (Phase-1 metadata shape, integration):**
> Given the MCP server is running with Player and Coach wired to different providers,
> When `tutor_turn` is called via stdio MCP,
> Then the response dict has keys `tutor_response`, `decision`, `attempts`, `flagged_for_review`, `duration_seconds`,
> And `decision` is one of `accept | exhausted | fallback`.

**AC-LCA-10 (live session, smoke — operator-conducted):**
> Operator runs a 2-turn session against the seeded Lilymay state (post TASK-GR-PMT). At least one turn shows `attempts > 1` (Coach revision occurred) OR documents the calibration follow-up if Coach never disagrees.

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| LLM Coach JSON output unreliability under Path A | High | Path C (hybrid) — strict prompt steering + `parse_coach_output` validation; budget for fallback dispatches; capture fallback rate during Lilymay session for Phase-2 calibration |
| Coach prompt design under-specified | Medium | Spec calls out as `@assumption ASSUM-COACH-02`; initial draft kept minimal; calibration is Phase-2 |
| `session_state` shape breaking changes between adapters | Medium | Typed dataclass at the boundary (D-COACH-03); change requires explicit type signature update across all consumers |
| Per-turn factory closure captures wrong state | High | AC-LCA-01 unit test (per-turn isolation invariant); same shape as the originally-planned AC-WIRE-04 |
| Coach + Player same provider | High | AC-LCA-08 boot-time smoke check; D-COACH-05 forces explicit operator config |
| Coach calibration absent — Coach never disagrees during demo | Medium | Document for Phase-2 follow-up (per TASK-REV-GRD5); do not block this PR |
| Untyped `session_state: Any` lets fields drift | Low | D-COACH-03 typed dataclass; runtime asserts in adapters |

## Cross-references

- Predecessor task: `tasks/backlog/wave5-mcp-blockers/TASK-GR-WIRE-orchestrator-and-session-end.md` (BLOCK-3a only post-narrowing)
- Original review: `.claude/reviews/TASK-REV-GRD5-review-report.md` §AC-REV-05 (BLOCK-1 design rationale)
- Parent task: `tasks/backlog/TASK-GR-DEMO-end-to-end-mcp-tutor-session.md` (the demo this unblocks via AC-DEMO-01.2)
- Soft dependency: `TASK-GR-PMT` (Player prompt update — needed for honest Coach-revision evidence in AC-LCA-10)
- Phase-1 plan: `docs/research/ideas/phase-1-build-plan.md` (DEC-04 Coach LLM-driven decision context)
- ADR: `docs/architecture/decisions/ADR-ARCH-012-deepagents-0-5-3-asyncsubagent-coach.md`
- ADR: `docs/architecture/decisions/ADR-ARCH-019-async-graphiti-writeback-every-write-point.md`
- Existing surfaces:
  - `src/study_tutor/tutoring/orchestrator.py:123` (`PlayerLike`)
  - `src/study_tutor/tutoring/orchestrator.py:152` (`CoachLike`)
  - `src/study_tutor/tutoring/orchestrator.py:333` (`PlayerCoachOrchestrator`)
  - `src/study_tutor/tutoring/coach/factory.py:326` (`validate_coach_config`)
  - `src/study_tutor/tutoring/coach/rubric.py:715` (`evaluate_player_turn`)
  - `src/study_tutor/tutoring/coach/rubric.py:597` (`parse_coach_output`)
  - `src/study_tutor/llm/client.py:47` (`_default_player_model` — pattern to mirror)
  - `tests/smoke/test_tutoring_loop.py:65-146` (existing `PlayerLike` / `CoachLike` stubs — reference shape)
- Existing assets to extend:
  - `roles/tutor/role.yaml`
  - `roles/tutor/prompts/player.md`
  - `.env.example`

## Suggested feature slug

`mcp-llm-player-coach-adapters` (matches the `features/{slug}/` and `tasks/backlog/{slug}/` conventions used by previous Phase-1 features).

## Notes for `/feature-spec`

- Use **Path C (hybrid)** as the recommended Coach strategy unless the spec review surfaces a strong preference for Path A or B.
- The two-provider invariant (D3) and structured-only revision channel (ASSUM-008) are **load-bearing security/safety constraints** — make them explicit `@invariant` scenarios, not buried in implementation notes.
- `@smoke` set should be tight (3-5 scenarios): boot-time smoke check, per-turn isolation, happy-path turn round-trip, malformed-Coach fallback. Match the FEAT-PH1-003 smoke gate convention (`@feat_lca and @smoke` or similar marker).
- Per-criterion scorer design (Path B fallback or augmenting Path C) is out of scope for this feature — call it out as a follow-up if surfaced.

## Notes for `/feature-plan`

- Anticipate 4-5 subtasks: (1) `LLMPlayerAdapter` + revision prompt, (2) `LLMCoachAdapter` + Coach prompt + JSON parsing, (3) `SessionState` typed dataclass + MCP adapter construction site, (4) `_default_coach_model()` + env var + boot smoke check, (5) integration smoke test wiring + CLI factory closure.
- Wave structure: subtasks 1-4 can run parallel (no shared mutable state); subtask 5 is sequential after 1-4 land.
- Smoke gate after final wave: `pytest -m "feat_lca and smoke"` (or matching marker).
- Cross-feature integration contracts: `MCPAdapter.__init__(orchestrator_factory=...)` (consumer of this feature; producer is `cli/main.py:serve`); `PlayerCoachOrchestrator.__init__` (consumer; producer is the factory closure).
