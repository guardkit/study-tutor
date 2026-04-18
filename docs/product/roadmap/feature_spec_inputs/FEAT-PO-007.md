# Gamification state model and event engine

## Description

Define Pydantic models and domain logic for XP, levels, streaks, achievements, quests, daily challenges, and boss battles, then wire those state transitions to tutoring events such as session completion, quote usage, topic mastery gains, and timed practice. The engine must behave like a deterministic rules layer over the student model so the product can consistently award progress and unlocks instead of relying on ad hoc LLM judgement.

## Bounded Context

Gamification BC

## Source Documents

- deepagents-patterns-review.md
- gemma4-hackathon-submission-plan.md

## Constraints

- Must be designed for a single learner, not leaderboards
- Must persist state in Graphiti or a Graphiti-backed store
- Must be clean enough to include in the public repo

## Dependencies

- FEAT-PO-004

## Suggested Context Files

- src/gamification/models.py
- src/gamification/engine.py
- src/gamification/graphiti_store.py
