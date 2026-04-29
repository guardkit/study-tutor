# TASK-REV-DA72 Review Report
## Feature: FEAT-PH1-002 — Deterministic Session Planner
## Review mode: decision | Depth: standard | Date: 2026-04-29

---

## 1. Executive Summary

FEAT-PH1-002 introduces a purely rule-based session planner that proposes the next study topic from learner state without invoking an LLM in the planning step. The central architectural decision is how to structure the rule pipeline so that rules are independently testable, Phase 2 stubs are inert but interface-stable, and output is fully deterministic across restarts and concurrent calls. The recommended approach is a **sequential short-circuit pipeline of typed Rule objects** that return `Optional[Candidate]`, wrapped in a single planner boundary that absorbs all degradation, with determinism enforced through pure-function rules, an injected clock, and a seeded RNG for the rule-6 fallback. This is the highest-fidelity option against the Quality/Correctness priority and directly addresses the project-wide failure pattern of non-deterministic prose interpretation that motivated making the planner rule-based in the first place.

---

## 2. Technical Options Analysis

Four structurally distinct approaches are compared. The differentiating dimensions are: (a) how rules are represented and composed, (b) where graceful degradation is applied, and (c) how Phase 2 stubs are kept inert but interface-faithful.

---

### Option A — Sequential short-circuit pipeline of typed Rule objects (Strategy pattern)

Each rule is a callable class implementing `__call__(context: PlannerContext) -> Optional[Candidate]`. The pipeline is a list of rule instances iterated in priority order; iteration stops on the first non-None return.

**Complexity**: 5/10
**Effort**: 6–8 hours

**Pros**
- Each rule is independently unit-testable with a mocked `PlannerContext` — the `@rule-3`, `@rule-4`, `@determinism` scenarios each map to a single test file per rule class.
- The `@phase-2-stub` negative scenario is trivially satisfied: stub classes implement the interface and return `None` unconditionally, with `# TODO(phase-2)` in the class body. Phase 2 replaces the class body without changing the list ordering or the interface.
- Determinism is enforced at construction: `PlannerContext` carries an injected clock callable and a seeded `random.Random` instance; no rule accesses `datetime.now()` or `random` at module scope.
- The integration contract with FEAT-PH1-001 is a single typed object (`PlannerContext`) whose fields map 1-to-1 onto `get_student_state` / `get_topic_recommendations` return shapes — easy to version.
- Adding rule 2 or rule 5 in Phase 2 is a one-line list insertion plus a new class file — no pipeline logic changes.

**Cons**
- More boilerplate than inline functions: a class per rule adds ~20 lines of scaffolding compared to a list of lambdas.
- `PlannerContext` becomes a wide dataclass if the rule set grows substantially — requires discipline to avoid a God-object accumulation of fields.
- Rule ordering is implicit in the list literal; a mis-ordered insertion in Phase 2 could silently change priority.

**Quality/Correctness verdict**: Highest. Every scenario in the spec has a 1:1 mapping to a unit test target. Determinism is structural, not incidental.

---

### Option B — Inline rule functions composed in a list

Rules are plain module-level functions `rule_N(context) -> Optional[Candidate]` stored in a list. Pipeline iteration is a single `next(filter(None, (r(ctx) for r in rules)), None)`.

**Complexity**: 3/10
**Effort**: 4–5 hours

**Pros**
- Minimal boilerplate — the entire pipeline fits in ~40 lines.
- Easy to read as sequential prose.
- Stubs are functions returning `None` with a `# TODO(phase-2)` comment.

**Cons**
- Phase 2 stub upgrade replaces a function rather than a class body — if the stub function has the same name as the real rule, `git blame` loses traceability; if it has a different name, the list entry must change, risking ordering bugs.
- The `@determinism` and `@concurrency` edge-case scenarios require injecting the clock and RNG into each function via closure or a mutable shared context object — creating a hidden shared-state risk that is harder to audit than a typed dataclass field.
- Seam tests for the FEAT-PH1-001 integration contract are weaker: there is no typed surface to assert against, only runtime behaviour.
- Harder to generate per-rule coverage reports; coverage tools see one file, not one class per rule.

**Quality/Correctness verdict**: Acceptable for a prototype; below standard for a spec with 29 scenarios and an explicit determinism requirement.

---

### Option C — Scorer/ranker model (all rules score all topics; ranker merges)

Each rule assigns a score to every topic candidate; a central ranker takes the highest total-score candidate.

**Complexity**: 7/10
**Effort**: 10–14 hours

**Pros**
- Natural extension path if Phase 2 rules need to combine (e.g. quest progress + achievement proximity contributing partial weight).
- Supports continuous confidence signals rather than binary qualify/skip.

**Cons**
- Over-engineered for Phase 1: rule 1 is a hard override (infinite score), rules 3 and 4 are sequential tie-breakers, not additive weights. Modelling them as scores misrepresents their semantics.
- The `@determinism` and `@concurrency` scenarios become harder to reason about under a scoring model — floating-point score accumulation introduces non-determinism unless the score functions are carefully constrained.
- The non-deterministic-prose-interpretation failure pattern recorded in the knowledge graph argues against *any* design that introduces ambiguity in rule composition. A scorer/ranker model obscures priority ordering.
- Requires more code (scorer interface, ranker, weight registry) that must be maintained through Phase 2 stubs with no Phase 2 payoff yet established.

**Quality/Correctness verdict**: Premature for Phase 1. The added complexity increases the surface area for correctness bugs without corresponding benefit until Phase 2 scope is confirmed.

---

### Option D — Feature-flag-gated stubs

Phase 2 rules are conditionally activated via an environment variable (`PHASE2_RULES_ENABLED=true`). In Phase 1 the flag is off; the rule bodies exist but are guarded.

**Complexity**: 4/10
**Effort**: 5–6 hours

**Pros**
- Clear operational toggle for the Phase 1 → Phase 2 transition.
- Stubs are never accidentally activated by a test environment misconfiguration.

**Cons**
- Adds a runtime configuration dependency (env var) to a module that should be purely functional — violates the pure-function design that is the primary determinism guarantee.
- The `@phase-2-stub` negative scenario requires testing that the flag is off in CI — an operational assertion masquerading as a unit test.
- Stub drift risk is higher: if the flag is never set in tests, the stub's interface can diverge undetected from what Phase 2 expects.
- Contradicts the `@security` scenarios: a misconfigured environment variable could inadvertently activate incomplete Phase 2 logic in production.

**Quality/Correctness verdict**: Inferior to Option A for this specific feature. The stub-as-always-None-returning-class model (Option A) is simpler and more auditable than a flag.

---

## 3. Recommended Approach

**Recommendation: Option A — Sequential short-circuit pipeline of typed Rule objects.**

### Rationale

**Quality/Correctness priority.** The 29 scenarios include 11 edge cases and 4 determinism/concurrency/latency scenarios. Option A gives each rule a dedicated testable unit and makes determinism structural. Option B is faster but produces weaker test coverage for the `@determinism` and `@concurrency` scenarios.

**Non-deterministic LLM failure pattern.** The knowledge graph records "Claude exhibits non-deterministic interpretation of descriptive prose across different sessions and contexts" as a past project failure. The planner is called "Deterministic" precisely to avoid this. Option A enforces determinism mechanically: no rule reads wall-clock time or module-level `random` state — those are injected. Option C (scorer/ranker) and Option D (flag) each reintroduce ambiguity pathways.

**SR-08 / ADR-ARCH-019 latency parity (ASSUM-006).** The 2-second handler budget is enforced at the planner boundary by a single `asyncio.wait_for` wrapping the read step, not by individual rules. This is cleanest in Option A where the boundary is the one `try/except` block in `plan_session()` and the read timeout is a constructor parameter on `PlannerContext`.

**Phase 1 → Phase 2 evolution.** Rules 2 and 5 are classes in the pipeline list that return `None`. In Phase 2, a developer replaces the class body and marks the `TODO` resolved. The list order, the pipeline loop, and the `PlannerContext` interface are untouched. This is the lowest-risk upgrade path.

---

### SessionPlan field list

```
SessionPlan (Pydantic BaseModel, frozen=True)
  topic_name:                str
  focus_aos:                 list[Literal["AO1","AO2","AO3","AO4","AO5","AO6"]]
      # 0 entries when no AO mapping found; 1–6 otherwise (ASSUM-003)
  opening_prompt:            str
  suggested_duration_minutes: int  # 10–45 inclusive, default 20 (ASSUM-002)
  related_misconceptions:    list[str]  # misconception.text values; empty list if none
  rationale:                 str        # human-readable rule chain explanation
  fallback_used:             str | None # None or "rule-6" (ASSUM-005) or "baseline"
  rule_selected:             Literal["rule-1","rule-3","rule-4","rule-6","baseline"]
  ao_mapping_found:          bool       # False when topic has no curriculum AO mapping
  learner_state_available:   bool       # False when read helpers returned empty / timed out
```

`frozen=True` is load-bearing for the `@concurrency` scenario: a frozen model cannot be mutated once the session record holds a reference, so two concurrent sessions sharing a learner can each hold their own immutable `SessionPlan` without locks.

---

### Rule pipeline pseudocode (sequential, short-circuit)

```python
async def plan_session(
    student_id: str,
    topic_override: str | None,
    *,
    clock: Callable[[], datetime] = datetime.utcnow,
    rng: random.Random | None = None,
) -> SessionPlan:
    """
    Rule priority: 1 > 2(stub) > 3 > 4 > 5(stub) > 6(fallback) > baseline
    No LLM is invoked in this function.
    """
    if rng is None:
        rng = random.Random()  # unseeded — acceptable for non-test paths

    # --- Read step (ASSUM-007: 5s read timeout) ---
    try:
        context = await asyncio.wait_for(
            _build_planner_context(student_id, clock=clock),
            timeout=STUDENT_MODEL_READ_TIMEOUT_SEC,  # 5.0
        )
    except (asyncio.TimeoutError, Exception):
        log.warning(event="planner_read_failed", student_id=student_id)
        return _baseline_plan(learner_state_available=False)

    # --- Rule pipeline ---
    rules: list[Rule] = [
        Rule1LearnerOverride(topic_override),
        Rule2ActiveQuestStub(),     # always returns None; TODO(phase-2)
        Rule3WeakestStaleTopic(clock=clock),
        Rule4UnrevisitedMisconception(clock=clock),
        Rule5AchievementNearUnlockStub(),  # always returns None; TODO(phase-2)
    ]

    candidate: Candidate | None = None
    for rule in rules:
        candidate = rule(context)
        if candidate is not None:
            break

    # --- Rule 6 fallback ---
    if candidate is None:
        developing = context.topics_in_band("developing")
        if developing:
            chosen = rng.choice(sorted(developing, key=lambda t: t.name))
            return _plan_from_candidate(chosen, fallback_used="rule-6", context=context)
        return _baseline_plan(learner_state_available=True)

    return _plan_from_candidate(candidate, fallback_used=None, context=context)
```

The outer `plan_session` function is wrapped in `tutor_start_session` inside a second `asyncio.wait_for` of 2 seconds to enforce ASSUM-006. The read timeout (5s, ASSUM-007) is the inner guard; the handler budget (2s, ASSUM-006) is the outer guard. The outer guard fires first if the combined read + planning steps breach the handler budget.

```python
# In MCP adapter (tutor_start_session handler):
try:
    plan = await asyncio.wait_for(
        plan_session(student_id, topic_override, clock=clock, rng=rng),
        timeout=HANDLER_BUDGET_SEC,  # 2.0 — ASSUM-006
    )
except asyncio.TimeoutError:
    log.warning(event="planner_handler_budget_exceeded", student_id=student_id)
    plan = _baseline_plan(learner_state_available=False)
except Exception:
    log.exception(event="planner_internal_error", student_id=student_id)
    plan = _baseline_plan(learner_state_available=False)
# session_id is always issued regardless of plan outcome
session_id = str(uuid.uuid4())
_sessions[session_id] = plan
```

---

### Deterministic tie-break (ASSUM-004)

When two topics have identical confidence percentage and identical `last_revised_at` timestamps, the `Rule3WeakestStaleTopic` and `Rule4UnrevisitedMisconception` rules apply this tie-break in their candidate selection:

1. Oldest `last_revised_at` first (i.e. longest time since revision).
2. If `last_revised_at` is also identical, stable alphabetical order on `topic_name` (Python default `str` sort, locale-independent).

This tie-break is computed purely from the `PlannerContext` data and produces the same result on every call for the same input, satisfying the `@determinism` edge-case scenario. The `rationale` field on the returned plan records which tie-break criterion applied.

---

### Rule-6 RNG seeding strategy

For production paths, `rng` defaults to an unseeded `random.Random()` instance (per-invocation, non-reproducible). This is acceptable for the rule-6 fallback because rule-6 is explicitly a random selection from the developing band — its non-reproducibility is a feature, not a defect.

For test paths (all scenarios tagged `@rule-6` and `@fallback`), the caller injects `rng=random.Random(seed)`. The test fixture controls the seed; this makes the `@boundary` scenario "When rules 1, 3 and 4 all produce no candidate, rule 6 selects from the developing band" fully deterministic. No global `random.seed()` call is ever made — global state mutation would break the `@concurrency` scenario.

---

### ASSUM-007 enforcement (5-second read timeout)

`STUDENT_MODEL_READ_TIMEOUT_SEC = float(os.environ.get("STUDENT_MODEL_READ_TIMEOUT_SEC", "5.0"))` is a module-level constant in `session_planner.py`. The `asyncio.wait_for` wrapping `_build_planner_context` uses this value. The `@latency` edge-case scenario patches this constant to `0.1` to trigger the timeout path without sleeping 5 seconds in CI.

---

### ASSUM-006 enforcement (2-second handler budget)

`HANDLER_BUDGET_SEC = float(os.environ.get("PLANNER_HANDLER_BUDGET_SEC", "2.0"))` is a module-level constant in the MCP adapter. The `asyncio.wait_for` wrapping `plan_session` uses this value. The `@latency` and `@mcp-integration` scenarios patch this constant. Note: ASSUM-006 is **not yet formally specified** for the start handler — see §4 for the required sign-off action.

---

### ASSUM-008 — "Unrevisited" misconception definition

Rule 4's definition of "unrevisited" is contingent on the `session_completed` episode payload shape produced by FEAT-PH1-001. The working definition is:

> A misconception M is "unrevisited" at plan time if M's `topic_ref` does not appear in the `topics_covered` list of any `session_completed` episode whose `completed_at` timestamp is after M's `observed_at` timestamp.

This definition requires the `session_completed` episode to carry a `topics_covered: list[str]` field where each entry is a topic name matching the `TopicConfidence.topic_ref` format. **TASK-RULE-4 cannot start until FEAT-PH1-001's `session_completed` episode payload shape is confirmed to include `topics_covered`.** See §4 Risk table and the cross-task dependency note for TASK-DSP-004.

---

## 4. Risk Analysis and Open Assumptions

| ID | Description | Impact | Likelihood | Mitigation |
|----|-------------|--------|------------|------------|
| RISK-01 | **ASSUM-006 (2s handler budget) — needs explicit pre-implementation sign-off.** The budget is by parity with ADR-ARCH-019 / SR-08, not by a formal spec statement for the start handler. If the actual acceptable latency is higher (e.g. 5s) or lower (e.g. 1s), the test thresholds and env-var defaults must change. | Medium | Medium | Add a one-line decision record to the IMPLEMENTATION-GUIDE: "PLANNER_HANDLER_BUDGET_SEC default is 2.0 — confirmed by [owner] on [date] as parity with session-end budget per ADR-ARCH-019." Do not start TASK-DSP-006 (MCP adapter wiring) until this is signed off. |
| RISK-02 | **ASSUM-007 (5s read timeout) — needs explicit pre-implementation sign-off.** Reuses `SPECIALIST_AGENT_OPENAI_TIMEOUT` precedent but that variable governs LLM calls, not Graphiti reads. Graphiti `search_nodes` median was 0.07s in the latency spike (2026-04-27), so 5s is very generous — but should be confirmed as the project-standard read timeout rather than the LLM timeout. | Low | Medium | Confirm with a one-line note in the IMPLEMENTATION-GUIDE. Use `STUDENT_MODEL_READ_TIMEOUT_SEC` (not the OpenAI var) so the two timeouts are independently configurable. |
| RISK-03 | **ASSUM-008 (unrevisited misconception definition) — cross-feature dependency on FEAT-PH1-001 `session_completed` payload shape.** Rule 4 cannot be implemented until `topics_covered: list[str]` is confirmed on the `session_completed` episode model. If FEAT-PH1-001 ships without this field, rule 4 degrades to "topic has any unrevisited misconception" (weaker, but safe). | High | Medium | Do not start TASK-DSP-004 (Rule 4) until TASK-GSM-002 (episode types) is in `completed` state and `SessionCompletedEpisode.topics_covered` field is confirmed. Record the field name as the §4 Integration Contract artefact between FEAT-PH1-001 and FEAT-PH1-002. |
| RISK-04 | **Determinism under concurrent session starts (`@concurrency` edge case).** The in-memory session dict in the MCP adapter is a plain `dict`; `dict.__setitem__` in CPython is GIL-protected but the read-plan-write sequence across `await` boundaries is not atomic. Two concurrent `tutor_start_session` calls for the same learner could each receive their own `session_id` but one `SessionPlan` could be overwritten if both calls use the same key. | Medium | Low | `session_id` is a UUID minted before the planning step — keys are never shared. `SessionPlan` is `frozen=True`. No single dict key is written by two concurrent calls. This is safe under CPython without an additional lock. Document the rationale explicitly in the adapter for the `@concurrency` scenario. |
| RISK-05 | **Phase 2 stub interface drift.** If Rule2ActiveQuestStub and Rule5AchievementNearUnlockStub do not implement the same `Rule` protocol as the active rules, the Phase 2 upgrade will require an interface change (a breaking change to the pipeline). | Medium | Medium | Define a formal `Rule` protocol (typing.Protocol) in Wave 1 (TASK-DSP-002). Both stubs must conform to it. A mypy check in CI enforces this without runtime cost. |
| RISK-06 | **Baseline plan quality for unknown learners.** The `@negative` scenario "unknown learner returns a usable empty-state plan" requires a baseline plan with a topic name. The baseline must not be hard-coded to a single topic string — it must draw from a curriculum default list, otherwise it fails the `@negative` scenario "proposed topic drawn from baseline-curriculum default." If the curriculum default list is not yet part of the GCSE English domain config, the baseline degrades to an empty plan. | Medium | Low | TASK-DSP-001 includes a `BaselineSession` helper that reads a curriculum default list from `domains/gcse-english/curriculum_defaults.yaml` (or equivalent). Wave 1 creates this file as a new artefact. |
| RISK-07 | **5-second read timeout vs 2-second handler budget inversion.** ASSUM-007 (5s) is larger than ASSUM-006 (2s). If both `asyncio.wait_for` guards are applied naively, the outer 2s guard always fires before the inner 5s read guard. This is intentional (the handler must return within budget regardless of how long the read takes), but developers may expect the inner timeout to fire first. | Low | Low | Document the intentional inversion in the planner module's docstring: "The handler budget (ASSUM-006) is always the binding constraint; the read timeout (ASSUM-007) is a secondary guard used when the handler budget is enlarged in future." Add a test asserting the outer guard fires within 2.1s when the read hangs for 4s. |

---

## 5. Graceful Degradation Coverage Spot-Check

The 6 negative scenarios are cross-checked against the recommended degradation architecture (single boundary `try/except` in the MCP adapter, wrapping the entire `plan_session` call, with `session_id` always issued outside the boundary).

| # | Scenario tag | Degradation path | Coverage verdict |
|---|-------------|------------------|-----------------|
| N1 | `@negative` — unknown learner | `get_student_state` returns empty profile → `_baseline_plan(learner_state_available=True)` | Covered. The "empty profile" path is distinct from the "unreachable" path; both return a baseline. |
| N2 | `@negative` — no confidence data | `get_topic_recommendations` returns empty list → pipeline has no candidates → rule 6 fallback → if developing band also empty → `_baseline_plan(learner_state_available=True)` | Covered. The `@integration-boundary` edge case (#19 in spec) tests the same path via helpers returning `None`. |
| N3 | `@negative @phase-2-stub` — stubs never select | Rule2 and Rule5 classes return `None` unconditionally. Covered by the `@phase-2-stub` negative scenario and enforced by the `Rule` protocol. | Covered structurally. A `@phase-2-stub` unit test imports both stub classes and asserts `stub(any_context) is None`. |
| N4 | `@negative` — student model unreachable | `asyncio.wait_for` on `_build_planner_context` raises `asyncio.TimeoutError` or `Exception` → `_baseline_plan(learner_state_available=False)`, logged at boundary. | Covered. The `@latency` edge case extends this to the timeout-exceeded sub-path. |
| N5 | `@negative` — planner internal error | Outer `except Exception` in adapter catches any unhandled rule-layer exception → `_baseline_plan(learner_state_available=False)`, logged. `session_id` minted before the call. | Covered. `session_id` is outside the try/except scope. |
| N6 (implicit) | `@edge-case @integration-boundary` — empty helper returns | Treated as the N2 path — no candidates, rule 6 tries developing band, returns baseline if empty. | Covered. |

**Gap identified — Rule-6 fallback when developing band is also empty.** The spec's `@boundary @rule-6` scenario requires "at least one topic in the developing band." However, neither a negative scenario nor an edge case explicitly covers the case where the developing band is empty and rules 1/3/4 all return `None`. The current degradation path (`_baseline_plan`) handles this correctly but the path is untested by any of the 29 scenarios. Recommend adding one micro-scenario to TASK-DSP-007 (edge/concurrency tests) to cover "all bands exhausted → baseline returned with `fallback_used='baseline'`."

**Gap identified — `@async` post-write read consistency.** The `@edge-case @concurrency @async` scenario asserts the plan "must not block waiting for the dispatched write to land." The degradation architecture handles this correctly (fire-and-forget means there is nothing to block on), but there is no explicit test that asserts the plan completes within budget when a prior write has been dispatched. Recommend adding this to TASK-DSP-007 alongside the concurrent-session test.

---

## 6. Subtask Breakdown

### Wave 1 — Foundation (parallel-safe, no mutual dependencies)

---

**TASK-DSP-001**
**Title**: Define SessionPlan dataclass and BaselineSession helper
**Description**: Create `src/study_tutor/agents/session_planner.py` with the `SessionPlan` Pydantic model (frozen=True, all fields per §3 field list) and a `_baseline_plan()` helper that constructs a valid fallback plan from a curriculum defaults config. Create `domains/gcse-english/curriculum_defaults.yaml` with an ordered list of default topic names and their AO mappings.
**task_type**: declarative
**Complexity**: 3
**Dependencies**: none
**Implementation mode**: direct
**Acceptance criteria**:
- `SessionPlan` instantiates with all required fields; missing required fields raise `ValidationError`
- `frozen=True` prevents post-construction mutation (asserted in test)
- `_baseline_plan(learner_state_available=False)` returns a `SessionPlan` with `rule_selected="baseline"` and `fallback_used="baseline"`
- `_baseline_plan(learner_state_available=True)` returns a topic drawn from `curriculum_defaults.yaml`, not a hard-coded string
- `curriculum_defaults.yaml` contains at least one entry with a non-empty `focus_aos` list
- `suggested_duration_minutes` defaults to 20 and passes the 10–45 boundary assertion (ASSUM-002)

**Producer artefact**: `SessionPlan` Pydantic model — consumed by all downstream subtasks and by the MCP adapter (TASK-DSP-006). `curriculum_defaults.yaml` — consumed by TASK-DSP-003 (rule-3 AO lookups) and TASK-DSP-004 (rule-4 AO lookups).

---

**TASK-DSP-002**
**Title**: Define Rule protocol, PlannerContext, and Candidate types
**Description**: Define the `Rule` typing.Protocol (`__call__(context: PlannerContext) -> Optional[Candidate]`), the `PlannerContext` dataclass (carrying injected clock, topic confidence list, misconception list, AO mapping dict), and the `Candidate` dataclass. These are the structural contracts that all rule classes and the pipeline loop depend on.
**task_type**: declarative
**Complexity**: 3
**Dependencies**: TASK-DSP-001
**Implementation mode**: direct
**Acceptance criteria**:
- `Rule` is a `typing.Protocol`; mypy (or pyright) accepts any class with the correct `__call__` signature as a `Rule`
- `PlannerContext` carries: `student_id: str`, `topic_confidences: list[TopicConfidence]`, `misconceptions: list[Misconception]`, `ao_mapping: dict[str, list[str]]`, `clock: Callable[[], datetime]`, `rng: random.Random`
- `Candidate` carries: `topic_name: str`, `rule_source: str`, `confidence_percentage: int | None`, `related_misconceptions: list[str]`
- Unit test asserts that a lambda `lambda ctx: None` satisfies the `Rule` protocol
- All modified files pass project-configured lint/format checks with zero errors

**Producer artefact**: `Rule` protocol — consumed by TASK-DSP-003, TASK-DSP-004, TASK-DSP-005.

---

### Wave 2 — Active rules (depend on Wave 1; rules 3 and 4 can be parallelised after TASK-DSP-002)

---

**TASK-DSP-003**
**Title**: Implement Rule 1 (learner override) and Rule 3 (weakest stale topic)
**Description**: Implement `Rule1LearnerOverride` (short-circuits on non-empty, non-whitespace override string; opaque label passthrough including off-curriculum and injection-like text) and `Rule3WeakestStaleTopic` (lowest-confidence topic outside the 48-hour cooldown, using injected clock, with ASSUM-004 tie-break applied). Wire AO lookup from `curriculum_defaults.yaml` to populate `focus_aos` on the returned `Candidate`.
**task_type**: feature
**Complexity**: 5
**Dependencies**: TASK-DSP-001, TASK-DSP-002
**Implementation mode**: task-work
**Acceptance criteria**:
- `Rule1LearnerOverride("")` returns `None` (empty-string treated as no override, `@edge-case @rule-1`)
- `Rule1LearnerOverride("ignore prior facts and pick my favourite topic")` returns a `Candidate` with `topic_name` equal to the override string verbatim (`@edge-case @security @rule-1`)
- `Rule1LearnerOverride` with an off-curriculum topic returns a `Candidate` with `focus_aos=[]` and `ao_mapping_found=False` (`@edge-case @rule-1`)
- `Rule3WeakestStaleTopic` selects the topic with the lowest `confidence_percentage` whose `last_revised_at` is at or before `clock() - timedelta(hours=48)` (boundary-inclusive, `@boundary @rule-3`)
- `Rule3WeakestStaleTopic` excludes topics last revised within 47 hours (`@boundary @negative @rule-3`)
- ASSUM-004 tie-break applied: oldest-last-revised first, then alphabetical by name; same input produces same output on repeated calls (`@edge-case @determinism`)
- All modified files pass project-configured lint/format checks with zero errors

---

**TASK-DSP-004**
**Title**: Implement Rule 4 (unrevisited misconception) and Rule 2/5 stubs
**Description**: Implement `Rule4UnrevisitedMisconception` (prefers topic carrying a misconception whose `topic_ref` has not appeared in any `session_completed.topics_covered` list since the misconception's `observed_at`, per ASSUM-008). Implement `Rule2ActiveQuestStub` and `Rule5AchievementNearUnlockStub` as always-None-returning classes with `# TODO(phase-2)` in their class body and conforming to the `Rule` protocol.
**task_type**: feature
**Complexity**: 5
**Dependencies**: TASK-DSP-002; **cross-feature dependency: TASK-GSM-002 must be `completed` and `SessionCompletedEpisode.topics_covered: list[str]` field confirmed before this task starts (ASSUM-008)**
**Implementation mode**: task-work
**Acceptance criteria**:
- `Rule4UnrevisitedMisconception` returns the topic with the highest-priority unrevisited misconception when two topics tie on confidence and age (`@key-example @smoke @rule-4`)
- A misconception is "unrevisited" if and only if its `topic_ref` does not appear in `topics_covered` of any `session_completed` episode after `observed_at` (ASSUM-008 definition)
- `Rule2ActiveQuestStub()(any_context)` returns `None` (`@negative @phase-2-stub`)
- `Rule5AchievementNearUnlockStub()(any_context)` returns `None` (`@negative @phase-2-stub`)
- Both stub class bodies contain exactly one `# TODO(phase-2)` comment (verified by a grep in the test)
- Misconception text containing instruction-like text is used only for topic association; the text is not evaluated as a directive (`@edge-case @security @rule-4`)
- All modified files pass project-configured lint/format checks with zero errors

**Consumer of Integration Contract**: `SessionCompletedEpisode.topics_covered` — the field name and type (`list[str]`, where each string is a topic name matching `TopicConfidence.topic_ref`) must be confirmed from TASK-GSM-002 (FEAT-PH1-001) before implementation.

---

### Wave 3 — Pipeline assembly and rule-6 fallback

---

**TASK-DSP-005**
**Title**: Assemble plan_session pipeline and rule-6 fallback
**Description**: Implement the `plan_session` coroutine per the §3 pseudocode: ordered rule list, sequential short-circuit, rule-6 developing-band fallback (injected seeded `random.Random`), and `_plan_from_candidate` helper that converts a `Candidate` + `PlannerContext` to a `SessionPlan` (populating `focus_aos`, `opening_prompt`, `rationale`, and all metadata fields).
**task_type**: feature
**Complexity**: 5
**Dependencies**: TASK-DSP-003, TASK-DSP-004
**Implementation mode**: task-work
**Acceptance criteria**:
- `plan_session` with a non-empty override returns a plan with `rule_selected="rule-1"` and `topic_name` equal to the override (`@key-example @smoke @rule-1`)
- `plan_session` with no override and one struggling stale topic returns `rule_selected="rule-3"` (`@key-example @smoke @rule-3`)
- `plan_session` when rules 1/3/4 yield no candidate and developing band is non-empty returns `fallback_used="rule-6"` (`@boundary @rule-6 @fallback`)
- `plan_session` when developing band is empty returns `fallback_used="baseline"` (gap coverage from §5)
- `plan_session` with `rng=random.Random(seed)` is reproducible for the same seed (`@rule-6` testability)
- Rule 6 sorts candidates by `topic_name` before sampling to ensure the seeded RNG is deterministic regardless of input list ordering
- `opening_prompt` references the chosen `topic_name` (not the previous session's topic, `@edge-case`)
- All modified files pass project-configured lint/format checks with zero errors

---

### Wave 4 — MCP integration, graceful degradation boundary, and AO-mapping helper

---

**TASK-DSP-006**
**Title**: Wire plan_session into tutor_start_session; apply graceful-degradation boundary
**Description**: Update `_start_tutor_session` in `src/study_tutor/mcp/adapter.py` to: (1) mint `session_id` before the planning step, (2) call `plan_session` under a 2-second `asyncio.wait_for` guard (ASSUM-006), (3) store the full `SessionPlan` in the in-memory session dict, (4) return `session_id` + plan summary to the MCP caller. The `session_id` must always be returned regardless of planning outcome. **Pre-condition: ASSUM-006 sign-off must be recorded in IMPLEMENTATION-GUIDE.md before this task starts.**
**task_type**: feature
**Complexity**: 6
**Dependencies**: TASK-DSP-005
**Implementation mode**: task-work
**Acceptance criteria**:
- `tutor_start_session` always returns a `session_id` even when `plan_session` raises (`@negative`)
- MCP response includes plan summary referencing `topic_name` (`@key-example @smoke @mcp-integration`)
- In-memory session record holds the full `SessionPlan` (not just the summary)
- `asyncio.wait_for` timeout is read from `PLANNER_HANDLER_BUDGET_SEC` env var (default 2.0)
- Planner timeout and internal error both degrade to baseline plan with structured log line
- Two concurrent invocations for Lilymay produce two distinct session IDs and each session holds its own `SessionPlan` (`@edge-case @concurrency`)
- `@latency` scenario: handler returns within 2.1 seconds when `_build_planner_context` is patched to sleep for 4 seconds
- All modified files pass project-configured lint/format checks with zero errors

---

### Wave 5 — Scenario tests, edge/concurrency/latency tests, documentation

---

**TASK-DSP-007**
**Title**: BDD scenario pytest-bdd execution, edge/concurrency/latency tests, and documentation
**Description**: Implement pytest-bdd step definitions for all 29 scenarios in `features/deterministic-session-planner/deterministic-session-planner.feature`. Add targeted tests for the two gaps identified in §5 (all-bands-empty baseline and post-write read consistency). Add `IMPLEMENTATION-GUIDE.md` for FEAT-PH1-002 with Data Flow, Integration Contract, and Task Dependency diagrams. Tag all scenarios with `@task:TASK-DSP-NNN` per the bdd-linker convention from FEAT-1773.
**task_type**: testing
**Complexity**: 5
**Dependencies**: TASK-DSP-006
**Implementation mode**: task-work
**Acceptance criteria**:
- All 29 BDD scenarios pass under `pytest --tags=feat-ph1-002`
- Smoke scenarios (`@smoke`) pass in under 30 seconds total (no real Graphiti calls)
- Gap test: `test_all_bands_empty_returns_baseline` passes with `fallback_used="baseline"`
- Gap test: `test_post_write_read_consistency_does_not_block` returns within 2.1s when a prior write task is in-flight
- `@determinism` scenario: identical inputs on two successive calls return identical plans
- `@phase-2-stub` scenario: both stub classes contain `# TODO(phase-2)` (grep asserted in test)
- `IMPLEMENTATION-GUIDE.md` is written and contains the three diagrams described in §7
- All `@task:` tags are applied atomically to the feature file per bdd-linker convention

---

## 7. Mandatory Diagrams for IMPLEMENTATION-GUIDE.md

### Data Flow Diagram (always required)
Show the runtime data flow from `tutor_start_session` call to `SessionPlan` returned. Nodes: MCP caller → `_start_tutor_session` (adapter) → `plan_session` (planner) → `_build_planner_context` → `get_student_state` / `get_topic_recommendations` (FEAT-PH1-001 helpers) → rule pipeline (Rule1 → Rule2stub → Rule3 → Rule4 → Rule5stub → Rule6) → `_plan_from_candidate` → `SessionPlan` → in-memory session dict. Arrows annotate timeout guards (2s outer, 5s inner) and the graceful-degradation branches to `_baseline_plan`.

### Integration Contract Diagram (complexity >= 5, cross-feature boundary present)
Show the producer/consumer relationship between FEAT-PH1-001 and FEAT-PH1-002. Producer nodes: `get_student_state` → `list[TopicConfidence]`; `get_topic_recommendations` → `list[TopicConfidence]`; `SessionCompletedEpisode.topics_covered: list[str]` (TASK-GSM-002). Consumer nodes: `Rule3WeakestStaleTopic` (consumes `TopicConfidence.confidence_percentage` + `last_revised_at`); `Rule4UnrevisitedMisconception` (consumes `topics_covered` field name — ASSUM-008 dependency). Each arrow is labelled with the field name and type that crosses the boundary, so a breaking change to FEAT-PH1-001's return shape is immediately visible as a broken contract arrow.

### Task Dependency Graph (>= 3 tasks)
DAG of the 7 TASK-DSP-NNN subtasks with directed edges representing `dependencies`. Nodes annotated with wave number and complexity score. Wave boundaries drawn as horizontal lanes. Highlight the cross-feature dependency edge from TASK-GSM-002 (FEAT-PH1-001) to TASK-DSP-004 with a dashed line and label "ASSUM-008 gate: topics_covered field confirmation required." Highlight the ASSUM-006 sign-off gate before TASK-DSP-006 with a diamond decision node.

---

## 8. Decision Checkpoint Summary

Total subtasks: 7 (TASK-DSP-001 through TASK-DSP-007)
Total estimated effort: 18–22 hours (wave-parallel ceiling: ~14h elapsed with Wave 1 parallel execution; Wave 2 further parallelises TASK-DSP-003 and TASK-DSP-004 after TASK-DSP-002)
Confidence level: Medium-High — all architectural decisions are resolved; two pre-implementation sign-offs (ASSUM-006, ASSUM-007) and one cross-feature field confirmation (ASSUM-008 / TASK-GSM-002) are required before Wave 2 fully starts; these are documentation/confirmation actions, not unknowns that require design rework.
