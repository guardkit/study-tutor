# Feature Spec Summary: DeepAgents Tutoring Loop with Coach

**Stack**: python
**Generated**: 2026-04-29
**Scenarios**: 39 total (5 smoke, 0 regression)
**Assumptions**: 11 total (5 high / 4 medium / 2 low confidence)
**Review required**: Yes (2 low-confidence assumptions remain — ASSUM-006, ASSUM-011)

## Scope

This specification covers FEAT-PH1-003: every learner-facing tutor turn passes through a Player-Coach loop where an evaluation-only Coach scores the Player's response against a six-criterion weighted rubric (curriculum accuracy, AO alignment, scaffolding depth, grade-appropriate language, constructive feedback, quote fidelity), accepts at-or-above the threshold, and otherwise drives a bounded Player revision cycle. It also covers session-end summary generation (topics, AOs, turn count, duration, narrative, misconceptions) and the fire-and-forget Graphiti write-back ownership at the three flush points (F1 Coach misconception writes, F2 planner topic-confidence updates, F3 session-end episode), with the `session.completed` event decoupled from Graphiti write success per DDR-003. Out of scope: Player prompt content, planner ranking logic (FEAT-PH1-002), retrieval/quote-verifier internals (FEAT-PH1-004), gamification consumers of `session.completed`.

## Scenario Counts by Category

| Category | Count |
|----------|-------|
| Key examples (@key-example) | 8 |
| Boundary conditions (@boundary) | 8 |
| Negative cases (@negative) | 7 |
| Edge cases (@edge-case) | 16 |
| Smoke (@smoke) | 5 |
| Regression (@regression) | 0 |

## Tag Footprint

| Tag | Count | Meaning |
|-----|-------|---------|
| `@coach-shape` | 8 | Structural Coach factory invariants (no tools, two-provider, etc.) |
| `@rubric` | 6 | Six-criterion weighted scoring |
| `@async` | 9 | Fire-and-forget Graphiti dispatch surface |
| `@quote-fidelity` | 5 | Integration with the source-typed quote verifier (FEAT-PH1-004) |
| `@revision-loop` | 6 | Player revision under Coach feedback |
| `@session-end` / `@summary` | 6 | F3 flush + narrative summary |
| `@misconception` | 4 | F1 flush — Coach-owned write per DDR-002 |
| `@events` | 3 | Shared Kernel B emit semantics per DDR-003 |
| `@security` | 4 | Prompt-injection / adversarial corpus / sanitisation |
| `@concurrency` | 4 | Two-session isolation, simultaneous dispatches, lifecycle race |
| `@invariant` | 5 | Hard architectural rules (D5, two-provider, never-learner-facing) |

## Task Tag Distribution (proposed)

| Task tag | Approx scenarios | Slice |
|----------|------------------|-------|
| `@task:TASK-DTL-001` | 9 | Coach factory + structural invariants (no-tools, empty-prompt, two-provider, adversarial-content) |
| `@task:TASK-DTL-002` | 10 | Coach rubric + quote-fidelity integration + verifier-failure path |
| `@task:TASK-DTL-003` | 12 | Player-Coach loop wiring, revision policy, latency, fallback, concurrency |
| `@task:TASK-DTL-004` | 6 | Async write helper + per-observation misconception writes + simultaneous dispatch + drain |
| `@task:TASK-DTL-005` | 8 | Session-end summary + F3 write + `session.completed` emit + lifecycle race |

`/feature-plan` Step 11 (`bdd-linker`) will refine this distribution against the actual subtasks it generates.

## Deferred Items

None. All proposed groups (A/B/C/D + edge-case expansion S/I/L) accepted.

## Open Assumptions (low confidence)

- **ASSUM-006** — Behaviour when Coach reasoning exceeds the 200-word cap (default: recorded in full but flagged for session-end review). The cap is stated; the behaviour at 201+ is inferred. Confirm with prompt-engineering review when the Coach prompt is finalised.
- **ASSUM-011** — Shutdown grace window for in-flight Graphiti writes (default: 5 seconds). Not stated in FEAT-PH1-003; the figure is a defensible default. Confirm against the shared write helper's planned `drain()` surface in TASK-GSM-004.

## Anchor Decisions Honoured

- **DDR-002** — Coach AsyncSubAgent owns its own misconception writes (F1). The Tutor handler dispatches F2 (planner topic-confidence) and F3 (session-end). Both go through a single shared Graphiti write helper.
- **DDR-003** — `session.completed` emits on the active→ended state transition, BEFORE the F3 Graphiti write task is scheduled. No `session.persisted` follow-up event. Sessions with zero tutor turns must not emit `session.completed` (I-T6).
- **CC-13 / ADR-ARCH-019** — Every Graphiti write site is fire-and-forget. Failures emit a structured-log line; they never raise into the caller-facing handler.
- **D5 (agentic-dataset-factory)** — Coach is `tools=[]`, no filesystem backend, never returns text to the learner. Construction-time checks enforce structurally rather than relying on prompt instructions.
- **Two-provider invariant** — Coach and Player must use different providers; enforced at Coach factory construction.

## Integration with /feature-plan

This summary can be passed to `/feature-plan` as a context file:

    /feature-plan "DeepAgents Tutoring Loop with Coach" \
      --context features/deepagents-tutoring-loop/deepagents-tutoring-loop_summary.md \
      --context features/deepagents-tutoring-loop/deepagents-tutoring-loop.feature \
      --context features/deepagents-tutoring-loop/deepagents-tutoring-loop_assumptions.yaml \
      --context docs/research/ideas/phase-1-scope.md \
      --context docs/research/ideas/phase-1-build-plan.md \
      --context docs/design/decisions/DDR-002-coach-async-subagent-owns-graphiti-writes.md \
      --context docs/design/decisions/DDR-003-session-completed-emits-on-state-transition.md \
      --context docs/design/contracts/API-tutoring.md

`/feature-plan` Step 11 will run `bdd-linker` to map the 39 scenarios onto the
generated subtasks and replace the placeholder `@task:TASK-DTL-NNN` tags with
the real task IDs.
