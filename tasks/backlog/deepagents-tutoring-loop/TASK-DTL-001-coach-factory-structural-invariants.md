---
id: TASK-DTL-001
title: Coach factory and structural invariants
task_type: feature
parent_review: TASK-REV-DTL3
feature_id: FEAT-PH1-003
wave: 1
implementation_mode: task-work
complexity: 5
estimated_minutes: 75
dependencies: []
status: backlog
created: 2026-04-29T00:00:00Z
updated: 2026-04-29T00:00:00Z
priority: high
tags: [feat-ph1-003, deepagents, coach, factory, invariants, D5, two-provider, FEAT-PH1-003]
related_features:
  - FEAT-PH1-003
related_tasks:
  - TASK-GSM-002  # Episode types — consumed in CoachVerdict for misconception payloads
  - TASK-GSM-004  # Async write helper — Coach AsyncSubAgent receives the helper at construction
consumer_context:
  - task: TASK-GSM-004
    consumes: GraphitiWriteHelper
    framework: "deepagents 0.5.3 AsyncSubAgent (per ADR-ARCH-012)"
    driver: "asyncio.create_task — fire-and-forget per CC-13"
    format_note: "Helper's write_misconception(student_id, misconception_payload) coroutine MUST be invocable from inside the Coach AsyncSubAgent task surface without awaiting completion. The AsyncSubAgent passes the helper instance into the Coach via constructor injection; do not import the helper module-globally."
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Coach factory and structural invariants

## Description

Create the Coach factory function (`create_coach`) that constructs an
evaluation-only Coach `AsyncSubAgent` (per ADR-ARCH-012) with all
load-bearing structural invariants enforced at construction time —
not via prompt instruction. Also defines the `CoachVerdict`,
`CriterionScore`, `RubricFeedback`, and `MisconceptionObservation`
Pydantic models that the Coach output schema is shaped against.

This task lands the smallest unit that downstream waves consume:
the `Coach` type and the `CoachVerdict` shape.

## Scope

- `create_coach(player_config, system_prompt, write_helper, ...)`
  factory function that:
  - Hard-codes `tools=[]` (D5 invariant)
  - Refuses non-empty tools list at the call site (defensive — caller
    cannot subvert tools list)
  - Refuses empty `system_prompt` with a clear error (ASSUM-005 boundary)
  - Refuses Coach configured with the same provider as Player
    (two-provider invariant per ASSUM-009)
  - Refuses any filesystem backend argument (D5 invariant — the factory
    has no `fs_backend` parameter exposed)
  - Returns a `Coach` (AsyncSubAgent subclass) instance with the shared
    Graphiti write helper injected for F1 misconception writes
- Pydantic v2 models in `src/study_tutor/tutoring/coach/models.py`:
  - `CriterionScore`: per-criterion score (0.0-1.0) + brief evidence string
  - `RubricFeedback`: structured "what to improve" fields, one per
    criterion below threshold (NOT free-text — ASSUM-008 enforcement)
  - `MisconceptionObservation`: misconception payload type that flows
    to the shared helper's `write_misconception(...)` (sourced from
    TASK-GSM-002 episode types)
  - `CoachVerdict`: weighted total + decision ("accept"|"revise") +
    list of `CriterionScore` + list of `MisconceptionObservation` +
    `reasoning: str` field (any length) + `reasoning_long: bool` flag
    set in post-init validation if `len(reasoning.split()) > 200`
    (ASSUM-006 resolution)
- `validate_coach_config(...)` helper that consolidates the four
  construction-time invariants in one place (per Finding F2 of
  TASK-REV-DTL3 review report)
- The Coach AsyncSubAgent itself ships as a thin wrapper over the
  evaluator function; it dispatches F1 misconception writes via
  `asyncio.create_task(self._write_helper.write_misconception(...))`
  inside its own task surface (DDR-002)

## Out of Scope

- Coach prompt content (the `system_prompt` is passed in by the caller
  for now; final prompt text is a separate concern landing later)
- Rubric scoring logic (TASK-DTL-002)
- Player-Coach orchestrator (TASK-DTL-003)
- Shared write helper implementation (TASK-GSM-004 — this task only
  consumes its protocol)

## Acceptance Criteria

- [ ] `create_coach(...)` returns a `Coach` (AsyncSubAgent) with
      `tools == []` regardless of any caller-supplied tools argument
- [ ] `create_coach(system_prompt="")` raises a clear error before
      any agent is constructed (covers @boundary scenario "Constructing
      the Coach with an empty system prompt fails before the agent is
      built")
- [ ] `create_coach(tools=[<anything>])` raises a clear error
      indicating tools are forbidden (covers @negative @invariant
      scenario "A Coach configuration that includes any tools is
      rejected at construction")
- [ ] `create_coach(...)` raises if Coach.provider == Player.provider
      (covers @negative @invariant @coach-shape scenario "A Coach
      configured to use the same provider as the Player is refused at
      construction")
- [ ] `create_coach(...)` exposes no filesystem-backend parameter; type
      checker / signature inspection confirms (covers D5 invariant)
- [ ] `CoachVerdict.reasoning` accepts arbitrary length text;
      `reasoning_long` flag is True iff `len(reasoning.split()) > 200`
      (covers @boundary @coach-shape Scenario Outline "Coach reasoning
      at and around the length cap is recorded as expected" — 199, 200,
      201 word inputs)
- [ ] `RubricFeedback` is a structured Pydantic model with named fields
      per criterion; the model has no free-text dump field that could
      smuggle Coach prose into Player prompts (covers ASSUM-008 +
      @edge-case @security @revision-loop scenario "Directive-shaped
      Coach text on a rejected turn is not obeyed by the Player on
      revision")
- [ ] Coach AsyncSubAgent's misconception write site uses
      `asyncio.create_task(self._write_helper.write_misconception(...))`
      — no `await self._write_helper...` direct call (covers CC-13 +
      DDR-002)
- [ ] All modified files pass project-configured lint/format checks
      with zero errors

## Test Requirements

- [ ] Unit tests for `validate_coach_config` covering all four invariant
      branches independently (no-tools, non-empty-prompt, two-provider,
      no-fs-backend)
- [ ] Unit tests for `CoachVerdict.reasoning_long` flag at 199, 200,
      201 words
- [ ] Property test: `RubricFeedback` schema has no free-text "raw" or
      "reasoning_passthrough" field (defensive against future field
      additions that would re-enable the prose-injection channel)
- [ ] Construction-time test: `create_coach` returns a `Coach` whose
      `.tools` attribute is `[]` even when caller passes a non-empty
      tools list (defensive — covered by raise, but also asserted
      post-construction)

## Implementation Notes

**Why a single `validate_coach_config` helper:**
Finding F2 of the review identified four distinct construction-time
invariants. Co-locating them in one validator keeps them grep-checkable
and prevents drift if a future invariant is added (e.g. a per-criterion
weight sanity check).

**Why `RubricFeedback` is a structured model with no free-text field:**
Per ASSUM-008 and the @security @revision-loop scenario, Coach prose
must never be pasted into the Player's revision prompt. Making the
revision-feedback model structured-only means an accidental future
"helpful" change that adds a `notes: str` field would surface as a
visible model change rather than a silent prompt-injection vector.

**Why the Coach is an AsyncSubAgent even on day 1:**
ADR-ARCH-012 + DDR-002 commit to the AsyncSubAgent shape. The inner
evaluator function can be a thin async function for now; landing the
AsyncSubAgent boundary today avoids a Phase 2 migration tax.

## Test Execution Log

[Populated by /task-work]
