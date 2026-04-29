---
id: TASK-DSP-005
title: plan_session pipeline and rule-6 fallback
task_type: feature
parent_review: TASK-REV-DA72
feature_id: FEAT-PH1-002
wave: 3
implementation_mode: task-work
complexity: 5
dependencies: [TASK-DSP-003, TASK-DSP-004]
estimated_minutes: 90
priority: high
tags: [phase-1, planner, pipeline, rule-6, fallback]
---

# Task: plan_session pipeline and rule-6 fallback

## Description

Compose the rule pipeline. `plan_session(student_id, topic_override,
*, clock, rng)` builds a `PlannerContext`, dispatches each rule in
order, short-circuits on the first non-`None` `Candidate`, falls back
to rule 6 (random selection from the developing band) when rules 1/3/4
all return `None`, and falls back to `_baseline_plan(...)` when even
the developing band is empty.

This is the core of Option A — the sequential short-circuit pipeline
of typed Rule objects. Determinism is enforced structurally: no
rule reads wall-clock time or module-level `random` state.

## Scope

- `plan_session(student_id: str, topic_override: str | None = None, *,
  clock: Callable[[], datetime] | None = None, rng: random.Random | None
  = None) -> SessionPlan`:

  ```python
  if rng is None:
      rng = random.Random()
  if clock is None:
      clock = datetime.utcnow

  context = await _build_planner_context(student_id, clock=clock,
                                         rng=rng,
                                         topic_override=topic_override)

  rules: list[Rule] = [
      Rule1LearnerOverride(context.topic_override),
      Rule2ActiveQuestStub(),
      Rule3WeakestStaleTopic(clock=clock),
      Rule4UnrevisitedMisconception(clock=clock),
      Rule5AchievementNearUnlockStub(),
  ]

  candidate = next((c for r in rules if (c := r(context)) is not None),
                   None)

  if candidate is not None:
      return _plan_from_candidate(candidate, fallback_used=None,
                                  context=context)

  developing = context.topics_in_band("developing")
  if developing:
      developing_sorted = sorted(developing, key=lambda t: t.topic_name)
      chosen = rng.choice(developing_sorted)
      return _plan_from_candidate(
          Candidate(topic_name=chosen.topic_name,
                    rule_source="rule-6",
                    confidence_percentage=chosen.confidence_percentage,
                    related_misconceptions=[],
                    rationale_fragment="rule-6 fallback: random "
                                       "selection from developing band"),
          fallback_used="rule-6",
          context=context,
      )

  return _baseline_plan(learner_state_available=True)
  ```

- `_plan_from_candidate(candidate, fallback_used, context)` builds the
  `SessionPlan`: looks up `focus_aos` for `candidate.topic_name` in
  `context.ao_mapping` (sets `ao_mapping_found=False` and `focus_aos=[]`
  when topic has no mapping), generates `opening_prompt` referencing
  the chosen topic, populates `rationale` from
  `candidate.rationale_fragment`.

- Rule 6 is part of `plan_session` itself, NOT a separate `Rule6Random`
  class — it operates after the rule list short-circuits and accesses
  `rng` directly.

## Acceptance Criteria

- [ ] Non-empty override → `rule_selected="rule-1"`, `fallback_used=None`
      (`@key-example @rule-1`).
- [ ] Struggling stale topic with no override → `rule_selected="rule-3"`
      (`@key-example @rule-3`).
- [ ] Two equally-weak topics, one with unrevisited misconception →
      `rule_selected="rule-4"` (`@key-example @rule-4`).
- [ ] Rules 1/3/4 all return `None` and developing band is non-empty
      → `rule_selected="rule-6"`, `fallback_used="rule-6"`,
      topic drawn from developing band (`@boundary @rule-6 @fallback`).
- [ ] **Gap test (TASK-REV-DA72 §5 Gap 1)**: rules 1/3/4 return `None`
      AND developing band is empty → `rule_selected="baseline"`,
      `fallback_used="baseline"`, no exception.
- [ ] Rule-6 with `rng=random.Random(42)` is reproducible: two calls
      with the same seed and same context return the same topic.
- [ ] Rule-6 sorts candidates by `topic_name` before sampling
      (so `random.Random(42)` output is stable across CPython versions).
- [ ] `opening_prompt` references the chosen `topic_name` exactly
      once and does NOT reuse a prior session's prompt verbatim
      (`@edge-case` opening-prompt scenario).
- [ ] Topic with no AO mapping yields `focus_aos=[]` and
      `ao_mapping_found=False` (`@edge-case @integration-boundary`
      AO-mapping scenario).
- [ ] Two consecutive `plan_session(...)` calls with identical state
      and seeded `rng` produce byte-identical `SessionPlan` instances
      (`@edge-case @determinism`).
- [ ] All modified files pass project-configured lint/format checks
      with zero errors.

## Implementation Notes

- Place in `src/study_tutor/planner/pipeline.py`.
- `_build_planner_context` lives in
  `src/study_tutor/planner/context_builder.py` and is the read boundary
  to FEAT-PH1-001. It calls `get_student_state`,
  `get_topic_recommendations`, and the misconception query helpers.
  TASK-DSP-006 wraps this builder in `asyncio.wait_for(timeout=5.0)`.
- Rule 6's `rng.choice` is invoked once per fallback. Production paths
  pass an unseeded `random.Random()`; tests pass a seeded one. Never
  call `random.seed()` at module scope — that breaks `@concurrency`
  by introducing mutable global state.
- The `:=` walrus inside `next((c for r in rules if (c := r(context))
  is not None), None)` evaluates each rule **once** even though the
  filter test references the same call. This avoids the "double
  evaluation" trap of `next(filter(None, (r(ctx) for r in rules)),
  None)` which would still call each rule twice in a naive read.
