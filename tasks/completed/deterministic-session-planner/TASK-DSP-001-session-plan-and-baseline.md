---
id: TASK-DSP-001
title: SessionPlan dataclass and BaselineSession helper
task_type: declarative
parent_review: TASK-REV-DA72
feature_id: FEAT-PH1-002
wave: 1
implementation_mode: direct
complexity: 3
dependencies: []
estimated_minutes: 60
priority: high
tags:
- phase-1
- planner
- session-plan
- baseline
- declarative
status: in_review
autobuild_state:
  current_turn: 1
  max_turns: 5
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/study-tutor/.guardkit/worktrees/FEAT-PH1-002
  base_branch: main
  started_at: '2026-04-29T20:17:27.408118'
  last_updated: '2026-04-29T20:22:19.169095'
  turns:
  - turn: 1
    decision: approve
    feedback: null
    timestamp: '2026-04-29T20:17:27.408118'
    player_summary: Added the planner subpackage with the immutable SessionPlan Pydantic
      v2 model (frozen=True, extra='forbid'), a load_curriculum_defaults() helper
      that reads the new src/study_tutor/planner/data/curriculum_defaults.yaml via
      importlib.resources, and the _baseline_plan(learner_state_available) helper.
      Both branches set rule_selected='baseline' and fallback_used='baseline'; the
      no-state branch uses a code-baked topic + opening prompt so the planner can
      degrade safely even if the YAML is missing, whil
    player_success: true
    coach_success: true
---

# Task: SessionPlan dataclass and BaselineSession helper

## Description

Define the immutable `SessionPlan` Pydantic model that the deterministic
planner returns, and the `_baseline_plan(...)` helper used on degraded
paths. Also add `curriculum_defaults.yaml` with at least one
baseline-curriculum entry that the helper can draw from when learner
state is unavailable.

This is the shared output contract for every other DSP task — Wave 1
foundation, no runtime dependencies.

## Scope

- `SessionPlan` Pydantic model (`frozen=True`):
  - `topic_name: str`
  - `focus_aos: list[Literal["AO1", "AO2", "AO3", "AO4", "AO5", "AO6"]]`
  - `opening_prompt: str`
  - `suggested_duration_minutes: int` — default 20, range 10–45
    inclusive (ASSUM-002, signed off)
  - `related_misconceptions: list[str]`
  - `rationale: str`
  - `fallback_used: Literal["rule-6", "baseline"] | None`
  - `rule_selected: Literal["rule-1", "rule-3", "rule-4", "rule-6", "baseline"]`
  - `ao_mapping_found: bool`
  - `learner_state_available: bool`
- `_baseline_plan(learner_state_available: bool) -> SessionPlan` helper:
  - When `learner_state_available=False`: returns a fixed
    no-state-available plan with `rule_selected="baseline"`,
    `fallback_used="baseline"`, empty misconceptions, default duration.
  - When `learner_state_available=True`: draws topic + focus_aos from
    `curriculum_defaults.yaml`, with `rule_selected="baseline"`,
    `fallback_used="baseline"`.
- `curriculum_defaults.yaml` at a stable read path with at least one
  entry containing `topic_name`, `focus_aos` (non-empty), and
  `opening_prompt_template`.

## Acceptance Criteria

- [ ] `SessionPlan` instantiates and rejects missing required fields
      with a clear Pydantic validation error.
- [ ] `frozen=True` prevents post-construction mutation
      (`session_plan.topic_name = "x"` raises).
- [ ] `_baseline_plan(learner_state_available=False)` returns
      `rule_selected="baseline"` and `learner_state_available=False`.
- [ ] `_baseline_plan(learner_state_available=True)` draws topic from
      `curriculum_defaults.yaml`, never from a literal string.
- [ ] `suggested_duration_minutes` defaults to 20 and rejects values
      outside 10–45 inclusive.
- [ ] `focus_aos` rejects values outside the AO1–AO6 enum.
- [ ] `curriculum_defaults.yaml` exists, parses, and has at least one
      entry with non-empty `focus_aos`.
- [ ] All modified files pass project-configured lint/format checks
      with zero errors.

## Implementation Notes

- Pydantic v2 is the project standard (`from pydantic import BaseModel,
  Field`).
- Place model + helper in `src/study_tutor/planner/types.py` (new
  module) so the planner pipeline (TASK-DSP-005) can import without
  circular dependency on the rule modules.
- `curriculum_defaults.yaml` lives under
  `src/study_tutor/planner/data/curriculum_defaults.yaml`, packaged as
  package data.
- Producer artefact for the rest of the feature: `SessionPlan` model
  consumed by every DSP-002 onward task; `curriculum_defaults.yaml`
  consumed by TASK-DSP-003 and TASK-DSP-004.
