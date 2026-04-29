---
id: TASK-DSP-002
title: Rule protocol, PlannerContext, and Candidate types
task_type: declarative
parent_review: TASK-REV-DA72
feature_id: FEAT-PH1-002
wave: 1
implementation_mode: direct
complexity: 3
dependencies: [TASK-DSP-001]
estimated_minutes: 45
priority: high
tags: [phase-1, planner, protocol, declarative]
---

# Task: Rule protocol, PlannerContext, and Candidate types

## Description

Define the structural contract every ranking rule conforms to. This
locks the Phase 2 stub interface from day one — Phase 2 implementations
of rules 2 and 5 will replace stub class bodies without changing the
ordering, the dispatch loop, or `PlannerContext`.

`PlannerContext` carries every field the rules need plus the injected
`clock` and seeded `rng` that make determinism structural rather than
incidental.

## Scope

- `Rule` as `typing.Protocol`:

  ```python
  class Rule(Protocol):
      def __call__(self, ctx: PlannerContext) -> Candidate | None: ...
  ```

- `PlannerContext` dataclass:
  - `student_id: str`
  - `topic_confidences: list[TopicConfidence]` — read from FEAT-PH1-001
    `get_student_state` / `get_topic_recommendations`
  - `misconceptions: list[Misconception]`
  - `ao_mapping: Mapping[str, list[AOCode]]` — topic_name → focus AOs
  - `topic_override: str | None` — empty string is treated as `None`
  - `clock: Callable[[], datetime]` — injected, never `datetime.utcnow`
    captured at module scope
  - `rng: random.Random` — seeded in tests, fresh `random.Random()` in
    production
  - Helper: `topics_in_band(band: Literal["struggling", "developing",
    "secure"]) -> list[TopicConfidence]`

- `Candidate` dataclass:
  - `topic_name: str`
  - `rule_source: Literal["rule-1", "rule-3", "rule-4", "rule-6"]`
  - `confidence_percentage: float | None` — `None` for off-curriculum
    overrides
  - `related_misconceptions: list[str]`
  - `rationale_fragment: str` — explains why this rule selected this
    candidate (becomes part of `SessionPlan.rationale`)

## Acceptance Criteria

- [ ] `Rule` is a `typing.Protocol` (structural typing, no inheritance
      required).
- [ ] mypy `--strict` accepts a class with a conforming `__call__`
      signature as a `Rule` without explicit subclassing.
- [ ] Plain lambda `lambda ctx: None` satisfies the `Rule` protocol in
      a unit test (verifies covariant return type).
- [ ] `PlannerContext` exposes `topics_in_band("struggling" |
      "developing" | "secure")` and rejects unknown band names.
- [ ] `Candidate` is immutable (`frozen=True` dataclass or `Pydantic
      frozen`).
- [ ] Tests cover the empty-string override → `topic_override` is
      normalised to `None` in `PlannerContext` factory.
- [ ] All modified files pass project-configured lint/format checks
      with zero errors.

## Implementation Notes

- Place in `src/study_tutor/planner/protocols.py`.
- `clock` and `rng` are injected via `PlannerContext.__init__`; default
  factories in the production builder use `datetime.utcnow` and
  `random.Random()` respectively.
- `topics_in_band` is the abstraction that lets rules avoid hard-coded
  band thresholds — band classification lives on `TopicConfidence`.
- Producer artefact: `Rule`, `PlannerContext`, `Candidate` consumed by
  TASK-DSP-003, TASK-DSP-004, TASK-DSP-005.
