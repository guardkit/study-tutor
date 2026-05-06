# Review Report: TASK-REV-LCA1

**Task**: Plan: MCP LLM Player and Coach Adapters
**Mode**: decision  |  **Depth**: standard  |  **Generated**: 2026-05-06

## Executive Summary

The feature has a high-quality `/feature-spec` artefact (24 scenarios, 5 smoke,
15 assumptions all resolved at high or medium confidence) and a thorough design
brief that has already evaluated three Coach strategies (Path A LLM-driven,
Path B deterministic-rubric, Path C hybrid). **Path C is recommended** and was
ratified during /feature-spec. This review validates that recommendation,
fills in the implementation breakdown with complexity scores and integration
contracts, and flags the six medium-confidence assumptions for explicit
planning notes per Context A clarification.

**Recommendation**: Proceed with **Path C (hybrid)** in 5 subtasks (4 parallel + 1 sequential).
**Estimated effort**: 8–12 hours total across the wave structure.
**Risk level**: Medium — the load-bearing safety invariants (D3 two-provider,
ASSUM-008 structured-only revision, per-turn factory isolation) are well-specified
and have explicit acceptance criteria; the main residual risk is Coach LLM JSON
output reliability, mitigated by `parse_coach_output` validation + fallback path.

## Review Details

- **Mode**: Decision analysis
- **Depth**: Standard
- **Clarification (Context A)**: Focus=All, Trade-off=Balanced, Sequencing=keep-spec-shape, Calibration-fallback-AC=include
- **Knowledge graph context**: 57 items loaded (similar player-coach factories from sibling project, score computation patterns, MCP per-role handler maps, Coach defensive path validation)
- **Pre-existing constraints**:
  - `MCPAdapter.__init__` already accepts `orchestrator_factory: Any = None` (mcp/adapter.py:133) — boot smoke check not yet wired
  - `tutor_turn` already routes via `self._orchestrator_factory()` when supplied (adapter.py:289) but passes `{"session_id": session_id}` only — needs typed `SessionState` construction site
  - `PlayerCoachOrchestrator`, `validate_coach_config`, `parse_coach_output`, `evaluate_player_turn` all exist and unit-tested
  - `_default_player_model()` (`llm/client.py:47`) is the pattern to mirror for `_default_coach_model()`

## Findings

### F1 — Path C is the right call (validates spec recommendation)

**Evidence**:
- Path A risk (LLM JSON unreliability) is real but mitigated by existing `parse_coach_output` validation + orchestrator fallback routing (`decision=fallback`)
- Path B requires 6 production scorer implementations — non-trivial design surface deferred to Phase 2 calibration
- Path C is essentially Path A with stricter prompt steering toward per-criterion JSON. The deterministic post-processing (clamping, weighted_total, RubricFeedback assembly) is grep-checkable and lives outside the LLM
- The Graphiti graph confirms a precedent pattern: `ProductOwnerOutputHandler` does deterministic post-processing of LLM output in a sibling project — same shape

**Conclusion**: Path C ratified. Spec is correct.

### F2 — `MCPAdapter.__init__` needs the boot smoke check explicitly added

**Evidence**: `adapter.py:153` stores `_orchestrator_factory` but never invokes it at boot. AC-LCA-02 / AC-LCA-08 require the boot-time same-provider rejection.

**Recommendation**: Subtask 4 owns adding the smoke check (call `orchestrator_factory()` once in `__init__`, discard result, propagate `OrchestratorConfigurationError` / `CoachConfigurationError`). Subtask 4 also owns the env var helper, so the work is naturally co-located.

### F3 — `session_state` at the construction site is a typed-dataclass migration, not a greenfield design

**Evidence**: `adapter.py:292` currently passes `{"session_id": session_id}` to `orchestrator.run_turn`. The smoke test in `tests/smoke/test_tutoring_loop.py` uses richer dicts (e.g. `{"text_name": "macbeth"}`). Adapters need at minimum `student_id`, `text_name`, `topic`, `focus_aos` for prompt personalisation and quote-fidelity grounding.

**Recommendation**: Subtask 3 lands the typed `SessionState` dataclass and updates the construction site. Other adapter subtasks (1, 2) consume it via `Any` for now — only the construction site and the type-narrowing inside the adapters need the import. This minimises blast radius.

### F4 — Six medium-confidence assumptions need explicit planning notes (Context A Q3)

Per Context A clarification, all six assumptions are flagged for spotlight in the implementation guide:

| Assumption | Subtask | Mitigation |
|------------|---------|-----------|
| ASSUM-LCA-005 (extra-criteria=discard) | 2 | `parse_coach_output` test suite already exists; add a discard-extra-criteria test case |
| ASSUM-LCA-006 (revise prompt: id+target only) | 1 | Make this an explicit AC — assert NO `suggested_focus` in revise prompt template |
| ASSUM-LCA-007 (SessionState optional fields) | 3 | Required: session_id, student_id. Optional with defaults: text_name=None, topic=None, focus_aos=(), mode="tutor" |
| ASSUM-LCA-008 (env var snapshot at boot) | 4 | Add operator note to `.env.example` — restart required after rotation |
| ASSUM-LCA-010 (Coach prompt <300 words) | 2 | Initial prompt draft kept minimal; calibration is Phase-2 follow-up |
| ASSUM-LCA-015 (quote_verifier/handover=None) | 5 | Document follow-up subtask in implementation guide; both stay `None` for first cut |

### F5 — Subtask 5 is genuinely sequential

**Evidence**: Subtask 5 (CLI factory closure + integration smoke) needs subtasks 1–4 *landed* (not merely typed) because:
- The factory closure imports `LLMPlayerAdapter`, `LLMCoachAdapter`, `_default_coach_model` — all three from waves 1, 2, 4
- The boot smoke check (Subtask 4) needs `MCPAdapter.__init__` mutated, but the integration smoke test exercises that mutation end-to-end
- AC-LCA-09 metadata-shape and AC-LCA-10 live-Lilymay smokes exercise the full closure

**Recommendation**: Keep the 4-parallel + 1-sequential shape from the spec (Q4 default).

### F6 — AC-LCA-10 needs explicit fallback wording (Context A Q5)

Per Context A clarification, AC-LCA-10 should be amended to permit two outcomes:
1. `attempts > 1` on at least one turn (Coach revision occurred — calibration is working)
2. **OR** the operator session log explicitly documents that Coach never disagreed — recorded as a known calibration gap, not a failure

This is the sole runtime behaviour AC where Phase-1 calibration cannot be guaranteed; treating zero-revision turns as a hard failure would create false negatives during the demo.

## Recommended Approach: Path C (hybrid)

### Subtask Breakdown

| # | Title | Wave | Mode | Complexity | Est. minutes |
|---|-------|------|------|------------|--------------|
| 1 | Implement `LLMPlayerAdapter` (respond + revise + structured-only revise prompt) | 1 | task-work | 5 | 90 |
| 2 | Implement `LLMCoachAdapter` + Coach prompt asset + JSON parsing path | 1 | task-work | 6 | 120 |
| 3 | Add `SessionState` typed dataclass + update MCP adapter construction site | 1 | task-work | 4 | 60 |
| 4 | Add `_default_coach_model()` + `AGENT_MODELS__COACH_MODEL` env var + boot smoke check in `MCPAdapter.__init__` | 1 | task-work | 4 | 75 |
| 5 | CLI `serve` factory closure + integration smoke tests (per-turn isolation, Phase-1 metadata shape, live Lilymay) | 2 | task-work | 5 | 90 |

**Aggregate complexity**: 6 (rolled up from individual scores)
**Total estimated effort**: ~7.25 hours implementation + buffer for revisions ≈ 8–12 hours
**Smoke gate after Wave 2**: `pytest -m "feat_lca and smoke"`

### Wave Structure

```
Wave 1 (parallel — Conductor recommended):
  TASK-LCA-001 (LLMPlayerAdapter)         [adapters/llm_player_adapter.py]
  TASK-LCA-002 (LLMCoachAdapter + prompt)  [adapters/llm_coach_adapter.py + roles/tutor/prompts/coach.md]
  TASK-LCA-003 (SessionState + MCP site)   [adapters/session_state.py + mcp/adapter.py:292]
  TASK-LCA-004 (env var + boot smoke)      [llm/client.py + mcp/adapter.py:__init__]

Wave 2 (sequential after Wave 1):
  TASK-LCA-005 (CLI closure + integration smokes) [cli/main.py:serve + tests/integration/]
```

**File-conflict analysis** confirms Wave 1 has no overlapping edit targets:
- TASK-LCA-001 only writes `src/study_tutor/tutoring/adapters/llm_player_adapter.py` (new file)
- TASK-LCA-002 only writes `src/study_tutor/tutoring/adapters/llm_coach_adapter.py` (new) + `roles/tutor/prompts/coach.md` (new)
- TASK-LCA-003 writes `src/study_tutor/tutoring/adapters/session_state.py` (new) + edits `src/study_tutor/mcp/adapter.py:292` (single line: `session_state=SessionState(...)`)
- TASK-LCA-004 edits `src/study_tutor/llm/client.py` (new function) + edits `src/study_tutor/mcp/adapter.py:__init__` (smoke-check call)

The two `mcp/adapter.py` edits (TASK-LCA-003 and TASK-LCA-004) target *different lines* — line 292 (call site) vs line 153 (constructor). Conductor merge can handle this cleanly. If it doesn't, sequence 003 → 004 inside Wave 1 with a fast hand-off.

### Integration Contracts (cross-task data flow)

Three contracts between subtasks must be specified to prevent integration-boundary bugs:

| Contract | Producer | Consumer | Format |
|----------|----------|----------|--------|
| `SessionState` schema | TASK-LCA-003 | TASK-LCA-001, TASK-LCA-002 (adapters consume via the typed parameter) | `@dataclass(frozen=True)` with required (`session_id: str`, `student_id: str`) and optional (`text_name: str \| None = None`, `topic: str \| None = None`, `focus_aos: tuple[str, ...] = ()`, `mode: str = "tutor"`) fields |
| `_default_coach_model()` semantics | TASK-LCA-004 | TASK-LCA-002 (LLMCoachAdapter calls it at construction) | `() -> str` — returns provider name; raises `LLMProviderError` with message naming `AGENT_MODELS__COACH_MODEL` if env var unset/empty |
| Orchestrator factory return type | TASK-LCA-005 (CLI closure) | TASK-LCA-004 (MCPAdapter boot smoke check) | `() -> PlayerCoachOrchestrator` — synchronous closure; no args; constructs Player+Coach+Orchestrator on each call |

### Risks (from brief, validated)

| Risk | Severity | Mitigation (committed) |
|------|----------|----------------------|
| LLM Coach JSON output unreliability under Path A/C | High | Path C strict prompt steering + `parse_coach_output` validation + orchestrator fallback routing (decision=fallback) |
| Coach prompt design under-specified | Medium | <300-word draft for Phase-1; calibration is Phase-2 follow-up (ASSUM-LCA-010) |
| `session_state` shape drift between adapters | Medium | Typed dataclass at the boundary (TASK-LCA-003); type-checked via mypy |
| Per-turn factory closure captures wrong state | High | AC-LCA-01 unit test enforces per-turn isolation; same shape as originally-planned AC-WIRE-04 |
| Coach + Player same provider | High | AC-LCA-08 boot smoke check; D-COACH-05 env var requires explicit operator config |
| Coach calibration absent — never disagrees during demo | Medium | AC-LCA-10 fallback wording (Q5 Context A) — documented as Phase-2 follow-up, not failure |

## Decision Matrix

| Path | Score | Effort | Risk | Recommendation |
|------|-------|--------|------|----------------|
| Path A (LLM-driven, full verdict JSON) | 6/10 | 8–12h | High (JSON reliability) | Not recommended |
| Path B (deterministic rubric, 6 scorers) | 4/10 | 20–30h | Medium (scope blowout) | Defer to Phase-2 calibration |
| **Path C (hybrid: LLM per-criterion JSON, deterministic clamp/parse)** | **9/10** | **8–12h** | **Medium (mitigated)** | **✅ Recommended** |

## Recommendations Summary

1. **Implement `LLMPlayerAdapter`** — `respond()` and `revise()` with structured-only prompt template (no Coach free-text)
2. **Implement `LLMCoachAdapter` + Coach prompt asset** — Path C hybrid; `<300` word coach.md; per-criterion JSON output parsed via `parse_coach_output`
3. **Add `SessionState` typed dataclass + update MCP adapter call site** — required (session_id, student_id) + optional (text_name, topic, focus_aos, mode)
4. **Add `_default_coach_model()` + env var + boot smoke check** — mirrors `_default_player_model()`; raises if `AGENT_MODELS__COACH_MODEL` unset
5. **Wire CLI `orchestrator_factory` closure + integration smokes** — per-turn isolation, Phase-1 metadata shape, AC-LCA-10 live-Lilymay (with calibration-fallback wording per Context A Q5)

## Decision Checkpoint

The review is complete. Identified **5 subtasks across 2 waves** with **Path C (hybrid)** as the recommended Coach strategy.

```
DECISION CHECKPOINT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Review complete for: Plan: MCP LLM Player and Coach Adapters

Options:
  [A]ccept   - Approve findings; archive review
  [R]evise   - Request deeper analysis on a specific area
  [I]mplement - Create implementation tasks (5 subtasks across 2 waves)
  [C]ancel   - Discard plan
```

## Context Used

From the Graphiti knowledge graph (Phase 2.5 of /feature-plan):
- **Path C precedent** — sibling-project `ProductOwnerOutputHandler` does deterministic post-processing of LLM output (validates the hybrid pattern is grep-checkable)
- **Coach defensive paths** — sibling project's Coach `FileNotFoundError` on missing manifest informs Subtask 5's integration-smoke wiring (verify `RoleConfig.load_coach_prompt()` finds `roles/tutor/prompts/coach.md` before Coach LLM is invoked)
- **MCP per-role handler maps** (USES_PER_ROLE_MAPS) — confirms the MCPAdapter's `tutor_turn` path is the canonical place to mount the orchestrator factory
- **SR-03 provider resolution** — already enforced in `tutor_turn`; the new `_default_coach_model()` must follow the same call-time-resolution pattern
- **Score computation: weighted_score - penalties = adjusted_score** — confirms `parse_coach_output` is the right deterministic post-processor for Path C verdict assembly
