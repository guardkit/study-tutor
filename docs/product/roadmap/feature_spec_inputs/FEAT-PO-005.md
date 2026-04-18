# Session planner using Graphiti recommendations

## Description

Build a session planning component that proposes the next revision activity from the student model, taking into account weakest topics, recent sessions, streak opportunities, and available challenge types. The planner must turn Graphiti state into a concrete English revision plan such as quotation practice, essay planning, AO2 language analysis, or literature theme revision before the tutoring conversation begins.

## Bounded Context

Session Orchestration BC

## Source Documents

- deepagents-patterns-review.md
- gemma4-hackathon-submission-plan.md

## Constraints

- Must work for both tutor-suggested and student-chosen sessions
- Must be grounded in persisted student state, not random topic selection
- Must support future gamification triggers

## Dependencies

- FEAT-PO-004

## Suggested Context Files

- src/agents/session_planner.py
- src/knowledge/student_model.py
- src/config/tutor_config.yaml
