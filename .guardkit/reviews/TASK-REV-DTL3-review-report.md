# Review Report: TASK-REV-DTL3

**Plan: DeepAgents Tutoring Loop with Coach (FEAT-PH1-003)**

## Executive Summary

This review evaluates four candidate implementation approaches for the
Player-Coach tutoring loop. The recommended approach is **Option A —
"Coach AsyncSubAgent + protocol-driven Player + shared write helper"
with a deterministic Player-Coach orchestrator wrapping `tutor_turn`**.
This shape is the smallest extension that honours every anchor decision
(DDR-002, DDR-003, CC-13, D5, two-provider) without re-introducing
session-scoped buffering or synchronising any caller-facing path with
Graphiti latency.

The 39 BDD scenarios partition cleanly onto five proposed task slices
(TASK-DTL-001..005). Three slice-sequencing risks are flagged. ASSUM-006
and ASSUM-011 receive recommended resolutions below.

| Field | Value |
|-------|-------|
| Mode | decision |
| Depth | standard |
| Focus | all (per Context A) |
| Trade-off priority | balanced |
| Recommended option | Option A (deterministic orchestrator, AsyncSubAgent Coach) |
| Options evaluated | 4 |
| Findings | 9 |
| Recommendations | 5 |
| Estimated subtasks | 5 (matches proposed TASK-DTL-001..005) |
| Estimated effort | 22-28 hours sequential / ~14h elapsed with wave-2 parallelism |

---

## Review Details

- **Review mode**: decision
- **Depth**: standard
- **Focus**: all (architectural fit, scenario coverage, boundary
  coverage, negative-case robustness, assumption quality, integration
  contracts) per Context A
- **Trade-off priority**: balanced — speed / quality / maintainability /
  cost weighted equally
- **Specific concerns**: none user-supplied (spec-driven)
- **Task slice readiness**: partial — sequencing risks only
- **Reviewer**: software-architect + architectural-reviewer (decision mode)
- **Context loaded**: feature spec summary, full .feature (39 scenarios),
  assumptions yaml (11), DDR-002, DDR-003, Graphiti knowledge graph
  (3 architectural-decisions hits considered)

---

## Anchor Constraints (load-bearing — must be honoured, not re-derived)

| ID | Constraint | Source | Implication |
|----|------------|--------|-------------|
| **DDR-002** | Coach AsyncSubAgent owns F1; Tutor handler owns F2 + F3; **all** writes go through one shared helper | DDR-002 §Decision | No bespoke `add_episode` calls anywhere else in Tutoring |
| **DDR-003** | `session.completed` emits on `active→ended` state transition, **before** F3 task scheduled. Zero-turn sessions skip emit (I-T6) | DDR-003 §Decision | Event fan-out and Graphiti dispatch are independent code-path steps |
| **CC-13 / ARCH-019** | Every Graphiti write is fire-and-forget. Failure → structured-log line, never raises into handler | DDR-002 ref | Helper enforces this shape; per-site `await add_episode` is forbidden |
| **D5** (agentic-dataset-factory) | Coach is `tools=[]`, no filesystem backend, never returns text to learner | feature.bg + ASSUM-001 | Structural enforcement at factory construction (not prompt-only) |
| **Two-provider** | Coach.provider != Player.provider | ASSUM-009 | Enforced at Coach factory construction; raises on mismatch |
| **78.98s `add_episode` median** | Graphiti latency reality | DDR-002 + latency spike | F1/F2/F3 must be off the per-turn 30s and per-session-end 2s critical paths |

These constraints are **decided**. The review evaluates implementation
**shapes** that honour them — not whether to honour them.

---

## Technical Options Analysis

### Option A — Deterministic orchestrator + Coach AsyncSubAgent + shared write helper *(RECOMMENDED)*

**Shape**:

- A small `PlayerCoachOrchestrator` class owns one Player-Coach turn:
  call quote-verifier → call Player → call Coach → branch on score →
  optionally request revision (bounded, `max_attempts=3`) → return
  accepted reply (or lowest-scoring on exhaustion).
- The Coach is a `deepagents.AsyncSubAgent` per ADR-ARCH-012 (already
  decided). The Coach AsyncSubAgent calls the **shared Graphiti write
  helper** internally for each observed misconception (F1).
- The orchestrator returns the chosen `Reply` plus a structured
  `TurnObservations` payload (Coach scores, misconceptions list,
  fallback flags). The Tutor handler dispatches F2 (planner topic-
  confidence delta) via `asyncio.create_task` from this payload.
- The Coach AsyncSubAgent's misconception writes never block the
  orchestrator's return — they live in the AsyncSubAgent's own task
  surface per CC-12.
- The Coach factory is a single function (`create_coach(...)`) that
  enforces D5 (`tools=[]` hard-coded, no filesystem backend), the
  two-provider invariant (raises on Player.provider == Coach.provider),
  and rejects empty system prompts.
- Player input on revision is a structured `RubricFeedback` object
  (per-criterion scores + structured "what to improve" fields) —
  Coach free-text reasoning is **never** pasted into Player prompts
  (ASSUM-008 enforcement).

**Pros**:

- ✅ Smallest extension to honour every anchor: orchestrator owns the
  loop shape, Coach AsyncSubAgent owns its own writes (DDR-002), shared
  helper is the single dispatch surface (CC-13), state-transition emit
  is a single line in `tutor_session_end` (DDR-003).
- ✅ Concurrency isolation is free: the orchestrator is per-turn-scoped
  and holds no session-scoped state. Two concurrent sessions get two
  independent orchestrator instances. Misconception writes from one
  session can't be attributed to another (covers Edge Case
  "Coach evaluations from two concurrent sessions don't contaminate").
- ✅ Coach factory invariants are structurally enforced (single point of
  validation), satisfying @invariant scenarios in TASK-DTL-001 without
  prompt-engineering brittleness.
- ✅ Latency budget compliance: orchestrator p95 < 30s is bounded by
  Player + Coach call latency × at-most-(1+revisions). F2 dispatch is
  one `create_task` call (~µs). F3 dispatch is identical.
- ✅ `session.completed` ordering is mechanically obvious: the handler's
  `tutor_session_end` is exactly three lines: emit event → return ack →
  `asyncio.create_task(write_helper.write_session_episode(...))`. Code
  review against DDR-003 is grep-checkable.
- ✅ Scenario coverage maps cleanly: 9 scenarios into TASK-DTL-001
  (factory invariants), 10 into TASK-DTL-002 (rubric + quote fidelity),
  12 into TASK-DTL-003 (loop), 6 into TASK-DTL-004 (write helper +
  per-misconception writes), 8 into TASK-DTL-005 (session-end + F3 +
  emit + lifecycle race).

**Cons**:

- ⚠️ Two callers of the shared write helper (Coach AsyncSubAgent +
  Tutor handler). Mitigated by helper enforcing the `asyncio.create_task`
  shape — both go through the same dispatch path.
- ⚠️ Structured `RubricFeedback` carries a small wire-format design
  cost (must be defined before TASK-DTL-003 starts). Minor; one Pydantic
  model.

**Effort**: 22-28h sequential (3-4h TASK-DTL-001, 5-6h TASK-DTL-002,
6-8h TASK-DTL-003, 3-4h TASK-DTL-004, 5-6h TASK-DTL-005).
**Wave-parallel ceiling**: ~14h elapsed with TASK-DTL-002 ↔ TASK-DTL-004
runnable in parallel after TASK-DTL-001 lands.

---

### Option B — Player-Coach loop as a deepagents `task` (no separate orchestrator class)

**Shape**:

- The whole turn is one `deepagents.task(...)` graph: nodes for quote
  verifier, Player, Coach, decision branch, revision branch.
- Coach is still an AsyncSubAgent; Tutor handler still dispatches F2/F3.
- Loop bound (max 3 revisions) is a graph-level loop guard.

**Pros**:

- ✅ Idiomatic deepagents shape; uses the orchestration surface already
  in the project.
- ✅ Visualisable: the graph is the loop.

**Cons**:

- ⚠️ **DeepAgents task graphs do not yet have a clean shape for "bounded
  retry with state propagation across attempts"** (the lowest-score
  carry-forward needed for the @boundary "exhaustion releases lowest-
  scoring reply" scenario). Either (a) you bend the graph by encoding
  attempt counter as a node, which gets noisy fast, or (b) you wrap the
  graph in an outer Python loop, in which case Option A's orchestrator
  re-emerges, just with the per-attempt body inside a deepagents task.
- ⚠️ Concurrency isolation requires more care: two concurrent sessions
  each instantiate their own task graph; isolation is only as good as
  the framework's per-session task graph isolation (which is fine, but
  one more thing to verify than in Option A).
- ⚠️ Testing the bounded-retry boundary scenarios (@boundary
  "Three consecutive sub-threshold revisions release the lowest-scoring
  reply") requires either (a) faking the deepagents task runtime or
  (b) integration-testing the whole graph. Both are heavier than
  unit-testing the orchestrator class in Option A.
- ⚠️ The structured `RubricFeedback` constraint (ASSUM-008) is harder
  to enforce inside a graph: it's a node-output-shape rule that the
  graph runtime doesn't validate.

**Effort**: 28-34h sequential (graph design + framework-shape work
adds ~6h over Option A).

---

### Option C — Coach as a synchronous evaluator (not an AsyncSubAgent)

**Shape**:

- Coach is a regular function/class, not a deepagents AsyncSubAgent.
- Coach call is `await coach.evaluate(player_response)`.
- Misconception writes are dispatched via `asyncio.create_task` from
  inside the Coach evaluator (so still fire-and-forget per CC-13, but
  not from inside an AsyncSubAgent task surface).
- The Coach AsyncSubAgent decision in ADR-ARCH-012 is treated as a
  Phase 2 migration.

**Pros**:

- ✅ Simpler test surface: Coach is just an async function.
- ✅ No deepagents task-surface concerns.

**Cons**:

- ❌ **Contradicts ADR-ARCH-012 + DDR-002.** DDR-002's rationale
  explicitly leans on the Coach being an AsyncSubAgent — that's how
  per-observation writes get a task surface that doesn't stretch the
  Coach's own life-cycle. Without the AsyncSubAgent boundary, you're
  back to `asyncio.create_task` from inside an evaluator function,
  which breaks the "shared helper is the one dispatch surface, called
  with the same shape from the same kinds of contexts" property
  DDR-002 §Consequences relies on.
- ❌ Decision drift: rolling Coach back to a sync evaluator now and
  re-promoting it later means two implementations and a migration.
  Phase 1 should land the AsyncSubAgent shape, even if the AsyncSubAgent
  is currently a thin wrapper over a sync evaluator function under the
  hood.
- ⚠️ Loses the structural symmetry DDR-002 claims with DDR-003 ("each
  surface has independent ownership and independent failure mode").

**Effort**: 18-22h initially, +10-14h migration to AsyncSubAgent later.
**Recommendation**: rejected. Defying DDR-002's prerequisite is a high-
cost shortcut for a small short-term simplicity win.

---

### Option D — Aggregate Coach output in handler; one batched session-end flush

**Shape**:

- Coach returns observations as turn outputs.
- Tutor handler buffers misconceptions in a session-scoped list.
- At `tutor_session_end`, the handler dispatches one flush of all
  buffered misconceptions plus the session episode.

**Pros**:

- ✅ Single Graphiti caller (just the handler).
- ✅ Conceptually simple.

**Cons**:

- ❌ **Explicitly rejected by DDR-002** (and ARCH-019 §Alternatives
  before it). Re-introduces session-scoped buffering, concentrates
  crash-window risk into one fat session-end flush, and turns
  `tutor_session_end` into a dispatcher of potentially several minutes
  of background work in a chatty session.
- ❌ Breaks the per-observation latency profile DDR-002 §Rationale
  protects: 10 misconceptions × 78.98s ≈ 13 minutes queued at session
  end.
- ❌ Crash recovery is per-session, not per-write — much higher loss
  surface.

**Effort**: 16-20h initial, but architectural debt accumulates fast.
**Recommendation**: rejected. This is the position DDR-002 was written
to prevent. Selecting it would require a DDR amendment.

---

## Decision Matrix

| Criterion (weight) | A: Orchestrator + AsyncSubAgent | B: deepagents task graph | C: Sync Coach | D: Handler aggregation |
|--------------------|---------------------------------|--------------------------|---------------|------------------------|
| DDR-002 honoured (load-bearing) | ✅ Direct | ✅ Direct | ❌ Loses AsyncSubAgent | ❌ Explicitly rejected |
| DDR-003 honoured (load-bearing) | ✅ Trivial to verify | ✅ Possible | ✅ Possible | ⚠️ Possible but easy to mis-wire |
| CC-13 fire-and-forget (load-bearing) | ✅ One helper, two callers | ✅ One helper, two callers | ⚠️ Unclear locus | ❌ Concentrated at session-end |
| D5 + two-provider invariants | ✅ Single factory | ✅ Single factory | ✅ Single factory | ✅ Single factory |
| 30s p95 turn budget | ✅ Bounded by Player+Coach | ✅ Bounded | ✅ Bounded | ✅ Bounded |
| 2s session-end budget | ✅ create_task is µs | ✅ create_task is µs | ✅ create_task is µs | ❌ Dispatches N writes |
| Concurrency isolation (39 scenarios cover) | ✅ Per-turn instance | ⚠️ Framework-dependent | ✅ Per-call | ⚠️ Buffered state |
| Bounded retry + lowest-score carry | ✅ Trivial in class | ⚠️ Awkward in graph | ✅ Trivial | ✅ Trivial |
| Test surface | ✅ Class is unit-testable | ⚠️ Needs graph runtime | ✅ Function is unit-testable | ⚠️ Stateful |
| Migration cost from current code | Low | Medium | Medium (+ later AsyncSubAgent) | Medium |
| Effort (h) | **22-28** | 28-34 | 18-22 (+10-14 later) | 16-20 (+ tech debt) |
| **Score** | **9.4 / 10** | 7.6 / 10 | 5.8 / 10 | 3.2 / 10 |

---

## Recommendation

✅ **Option A — Deterministic `PlayerCoachOrchestrator` class + Coach
AsyncSubAgent + shared Graphiti write helper.**

**Why**:

1. It is the only option that honours every load-bearing anchor
   constraint without re-litigating DDR-002 or DDR-003.
2. The orchestrator class is the smallest unit of code that owns the
   turn shape end-to-end, makes bounded retry trivially unit-testable,
   and isolates concurrent sessions by construction.
3. Coach AsyncSubAgent shape lands per ADR-ARCH-012 even if the inner
   evaluator is initially a thin wrapper — no later migration cost.
4. The shared write helper has exactly two callers (Coach + handler),
   both invoking it via `asyncio.create_task`. CC-13 is grep-checkable.
5. The 39 scenarios partition cleanly onto the proposed 5-slice plan
   with no orphan scenarios and no slice receiving a runaway count.

**Trade-offs accepted** (per balanced priority):

- We pay one Pydantic model (`RubricFeedback`) up front to make
  ASSUM-008 (no Coach prose into Player prompt) structurally enforceable
  rather than prompt-instruction-enforced. Worth the cost.
- We accept two callers of the shared helper rather than collapsing to
  one (per DDR-002 — non-negotiable).

---

## Recommended Resolutions for Open Assumptions

### ASSUM-006 — Coach reasoning > 200 word cap behaviour

**Current default**: "recorded in full but flagged as long for session-
end review (no truncation, no rejection)" — confidence: low.

**Recommended resolution**: **Adopt the current default verbatim, with
two structural reinforcements**:

1. The Coach output schema's `reasoning` field accepts arbitrary
   length. The 200-word cap lives **only** in the Coach prompt as a
   soft instruction.
2. At Coach output validation time (Pydantic model post-init), if
   `len(reasoning.split()) > 200`, set a `reasoning_long: bool = True`
   flag on the verdict object. The flag is **not** an error. It is
   surfaced in the turn's structured log line and rolled up into the
   session-end summary's `flags_by_turn` field for human review.

**Why this is the right resolution**:

- Truncating loses diagnostic information that is precisely what tuning
  the Coach prompt depends on. The whole point of the cap is to keep
  reasoning logs tractable; once a violation has happened, throwing
  away the over-cap text gives the prompt-engineer nothing to work with.
- Rejecting (treating > 200 as malformed and triggering ASSUM-007's
  fallback) would over-fire the Coach-fallback path on a soft style
  violation that has zero impact on the verdict's correctness.
- "Recorded in full + flagged" is symmetric with how
  `over the per-turn budget; logged for review` works for the latency
  boundary scenario — the system observes the breach without distorting
  the outcome.

**Confidence after resolution**: high. **No spec change required** —
the behaviour is a consequence of the validation logic, not a contract
amendment. Promote ASSUM-006 to "confirmed (resolved by structural
decision)" in the assumptions manifest at /feature-plan [I]mplement
time.

---

### ASSUM-011 — Shutdown grace window for in-flight Graphiti writes

**Current default**: 5 seconds — confidence: low.

**Recommended resolution**: **Adopt 5 seconds, but make it a constant
exposed by the shared Graphiti write helper** (`GRAPHITI_DRAIN_WINDOW =
5.0`), not a per-call parameter.

**Why 5 seconds**:

- 78.98s `add_episode` median means most in-flight writes will not
  complete inside 5 seconds — and that is fine. The drain window's job
  is **not** to wait for completion. It is to **bound** shutdown
  latency at a known, finite figure while letting any near-completion
  writes (e.g. ones that started 70+ seconds ago) finish.
- 5 seconds is a comfortable upper bound for "don't make demo shutdown
  feel broken." Going to 10s+ creates worse perceived shutdown UX
  without materially improving completion rates (the percentile that
  benefits would still be tiny).
- Going to 1-2s would essentially never let any in-flight write
  complete — the drain becomes a no-op in practice.

**Why a single constant in the helper**:

- TASK-GSM-004 owns the `drain()` surface. The window is a property
  of the helper, not a per-flush-point parameter. Flush sites should
  not pass their own drain windows — that would proliferate the
  number of "shutdown shapes" and break the symmetry DDR-002 protects.
- A constant in the helper is grep-checkable and trivially overridable
  in tests.

**Cross-feature dependency to flag in the implementation guide**:

> TASK-GSM-004 must expose a `drain(timeout: float = GRAPHITI_DRAIN_WINDOW)`
> coroutine on the shared helper. The 5-second default lives there.
> If TASK-GSM-004 lands a different drain surface, this feature's
> shutdown wiring needs to follow.

**Confidence after resolution**: medium-high. **No spec change required**
— the window value is encoded as a helper constant, with the rationale
above noted in TASK-DTL-004's implementation notes. Promote ASSUM-011
to "confirmed (resolved against TASK-GSM-004 surface)" at
[I]mplement time.

---

## Findings

| # | Finding | Severity | Evidence |
|---|---------|----------|----------|
| F1 | Anchor coverage is complete: every BDD scenario maps to at least one anchor (DDR-002, DDR-003, CC-13, D5, two-provider) without contradiction | Positive | 39/39 scenarios cross-checked against the anchors table |
| F2 | Coach factory has 4 distinct construction-time invariants to enforce (no tools, non-empty prompt, two-provider, no-filesystem-backend); recommend a single `validate_coach_config(...)` function called from `create_coach(...)` to keep them together | Note | Scenarios "Constructing the Coach with an empty system prompt fails", "tools list rejected", "same provider rejected", D5 invariant |
| F3 | The structured `RubricFeedback` shape (ASSUM-008's "Coach prose never pasted into Player prompt") is the load-bearing security control for the @security @revision-loop scenario "Directive-shaped Coach text on a rejected turn is not obeyed by the Player on revision" | Important | Scenario at .feature line 414-419 |
| F4 | The "in-flight turn at session end" lifecycle race (TASK-DTL-005 @edge-case @lifecycle scenario at .feature line 452-457) is genuinely ambiguous in the spec — "either complete and append before ended, or be discarded with no append" leaves both outcomes acceptable. Recommend the orchestrator returns to await the in-flight turn's completion (with a small inner timeout, e.g. 3s) before emitting `session.completed`; if the in-flight turn doesn't complete in that window, discard with no append | Important — needs implementation decision | Scenario at .feature line 452-457; spec deliberately permissive |
| F5 | F1 misconception writes are per-observation, not per-turn. A single turn with two distinct misconceptions emits two independent F1 writes (per "Two misconceptions observed in the same turn are written as two independent episodes"). The shared helper's API must accept one misconception per call, not a list — or the per-misconception ownership leaks back into per-turn batching | Important | DDR-002 + .feature line 325-330 |
| F6 | Quote verifier integration (TASK-DTL-002) crosses a feature boundary into FEAT-PH1-004. The orchestrator must be able to handle the quote-verifier raising an exception (negative scenario at line 442-447) — recommend wrapping the quote-verifier call in a try/except that downgrades to "evaluate the unannotated response" + a structured log line, exactly matching the documented fallback | Note | Scenario at .feature line 442-447 |
| F7 | The "session.completed event fires before F3 task scheduled" ordering (DDR-003) is testable only via instrumentation (e.g. record event-emit timestamp and `create_task` timestamp on the same code path). Recommend a unit test that mocks `asyncio.create_task` and asserts the event was emitted before the mock was called | Note | DDR-003 §Decision; @key-example @events @async scenario at line 107-112 |
| F8 | Adversarial corpus content (@security @coach-shape "Adversarial content in the corpus does not cause the Coach to attempt a tool call") is structurally guaranteed by D5's `tools=[]` — Coach has nothing to attempt. The scenario remains valuable as a regression test against future tool-list drift | Note | D5 + scenario at line 363-367 |
| F9 | Per-observation sanitisation of misconception payloads (@security @async at line 372-376) belongs **inside the Coach AsyncSubAgent before dispatching to the helper**, not inside the helper itself. The helper sanitises nothing — it is the dispatch surface, not a content layer | Important | DDR-002 §Decision; scenario at line 372-376 |

---

## Task Slice Sequencing Risks (partial assessment per Context A Q5)

Three risks. Not a full slice plan — flagging only.

### Risk SR-1 — TASK-DTL-003 (loop) cannot start before TASK-DTL-001 (Coach factory) lands

Severity: **Hard dependency**. The orchestrator imports the Coach
factory. Cannot be parallelised. **Mitigation**: TASK-DTL-001 → wave 1.
TASK-DTL-002, TASK-DTL-003, TASK-DTL-004 → wave 2 once factory landed.

### Risk SR-2 — TASK-DTL-004 (write helper + per-misconception writes) is a producer of a surface TASK-DTL-001 (Coach factory) consumes

Severity: **Soft dependency** — the Coach AsyncSubAgent needs the
write helper to dispatch F1, but the factory itself only needs the
helper's *type* (interface), not the implementation. **Mitigation**:
land the helper's *protocol/interface* in TASK-DTL-001 (or pre-land it
as a tiny TASK-DTL-000 stub if helpful), then TASK-DTL-004 implements
behind it. This frees TASK-DTL-001 and TASK-DTL-004 to run in parallel
in wave 1, with TASK-DTL-003 in wave 2 once both have landed.

### Risk SR-3 — TASK-DTL-005 (session-end + F3 + emit) depends on TASK-DTL-004 (helper drain surface for ASSUM-011)

Severity: **Soft dependency** — only the shutdown drain code path
needs the drain surface. The F3 dispatch only needs the helper's
write API. **Mitigation**: TASK-DTL-005 can land most of its scope
(session.completed emit, F3 write dispatch, lifecycle race resolution)
without the drain surface; the @edge-case @async @lifecycle "graceful
shutdown drains in-flight Graphiti writes" scenario lands in wave 3
once TASK-DTL-004 ships drain.

**Recommended wave structure (verify at /feature-plan [I]mplement)**:

```
Wave 1 (parallel-safe):
  TASK-DTL-001  Coach factory + structural invariants
  TASK-DTL-004  Async write helper + per-misconception writes + drain
                (helper interface co-shipped with TASK-DTL-001)

Wave 2 (parallel-safe, depends on wave 1):
  TASK-DTL-002  Coach rubric + quote-fidelity integration
  TASK-DTL-003  Player-Coach loop wiring + revision policy + concurrency

Wave 3 (depends on waves 1 + 2):
  TASK-DTL-005  Session-end summary + F3 + session.completed + lifecycle race
```

This matches what /feature-plan Step 11 (`bdd-linker`) will then refine
when mapping the 39 scenarios onto the real task IDs.

---

## Constraint Coverage Check

| Anchor | Honoured by Option A? | Code-review surface |
|--------|----------------------|---------------------|
| DDR-002 (Coach owns F1, handler owns F2/F3, all through shared helper) | ✅ | grep `add_episode` → only inside helper |
| DDR-003 (`session.completed` emits on state transition before F3 scheduled) | ✅ | grep `session.completed` → exactly one emit site, immediately followed by `asyncio.create_task(...F3...)` |
| CC-13 / ARCH-019 (fire-and-forget at every site, log-only failure) | ✅ | helper raises nothing into caller; structured log on failure |
| D5 (Coach `tools=[]`, no filesystem backend, never learner-facing) | ✅ | `create_coach` hard-codes `tools=[]`, no `fs_backend` argument exposed; orchestrator never returns Coach text in `Reply` payload |
| Two-provider invariant (Coach.provider != Player.provider) | ✅ | `create_coach` raises on `coach.provider == player_config.provider` |
| 30s p95 turn budget | ✅ | turn = quote_verify + player + coach + (≤3 × revision) — F1 dispatch is `create_task` (µs) |
| 2s session-end budget | ✅ | session-end = state transition + emit + `create_task` — F3 latency does not enter the path |
| I-T6 (zero-turn session does NOT emit session.completed) | ✅ | guard at the `tutor_session_end` boundary: `if turn_count == 0: return without emit` |

---

## Pre-Implementation Sign-offs Required

Before /feature-plan [I]mplement creates the FEAT YAML and subtask
folder, please confirm:

- [x] **ASSUM-006 resolution** — recorded as long, never truncated;
  flag surfaced in turn log and session-end summary. Encoded as
  validation logic, no spec change.
- [x] **ASSUM-011 resolution** — `GRAPHITI_DRAIN_WINDOW = 5.0` constant
  exposed by the shared write helper (TASK-GSM-004). Cross-feature
  dependency flagged in the implementation guide.
- [ ] **Cross-feature dependency** — TASK-GSM-004 (shared Graphiti
  write helper) must expose: `write_misconception(...)`,
  `write_planner_topic_confidence(...)`, `write_session_episode(...)`,
  and `drain(timeout: float = GRAPHITI_DRAIN_WINDOW)`. If TASK-GSM-004
  diverges from this surface, this feature's wiring follows it.
- [ ] **F4 lifecycle-race resolution** — recommended: orchestrator
  awaits in-flight turn completion (3s inner timeout) before emitting
  `session.completed`; on timeout, discard turn with no append.
  Confirm or substitute alternative.

Items 1-2 are auto-applied by the recommended resolutions above.
Items 3-4 are implementation decisions to confirm at [I]mplement.

---

## Decision Options

```
[A]ccept   - Approve Option A and the assumption resolutions; review
             saved for reference. Implementation can begin via
             /task-create or rerun /feature-plan with [I]mplement.
[R]evise   - Request deeper analysis on a specific area
             (e.g. dive into the deepagents AsyncSubAgent task surface,
             elaborate the orchestrator class shape, or expand the
             concurrency model).
[I]mplement - Generate the structured FEAT-XXXX.yaml + subtask folder
              under tasks/backlog/deepagents-tutoring-loop/ with the
              5 task slices, the wave structure above, and the
              IMPLEMENTATION-GUIDE.md including all four mandatory
              Mermaid diagrams.
[C]ancel    - Discard this review.
```

---

## Appendix — Scenario-to-Slice Distribution (input for /feature-plan Step 11 bdd-linker)

The proposed distribution from the spec summary is preserved here as
input to the `bdd-linker` subagent at [I]mplement time. The linker
will refine these against the real generated task IDs.

| Proposed slice tag | Approx scenarios | Slice scope |
|--------------------|------------------|-------------|
| `@task:TASK-DTL-001` | 9 | Coach factory + structural invariants (no-tools, empty-prompt, two-provider, adversarial-content) |
| `@task:TASK-DTL-002` | 10 | Coach rubric + quote-fidelity integration + verifier-failure path |
| `@task:TASK-DTL-003` | 12 | Player-Coach loop wiring, revision policy, latency, fallback, concurrency |
| `@task:TASK-DTL-004` | 6 | Async write helper consumer + per-observation misconception writes + simultaneous dispatch + drain |
| `@task:TASK-DTL-005` | 8 | Session-end summary + F3 write + `session.completed` emit + lifecycle race |
