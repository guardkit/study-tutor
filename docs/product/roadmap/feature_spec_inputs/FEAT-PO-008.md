# Adaptive challenge and boss battle generation

## Description

Generate daily challenges and exam-style boss battles from the student's current revision state so that the engagement loop reinforces real learning rather than superficial clicking. Challenges must be tied to English behaviours the tutor can observe—such as quotation embedding, AO2 analysis, or reviewing yesterday's mistakes—and boss battles must feel like high-stakes exam practice unlocked through progression.

## Bounded Context

Gamification BC

## Source Documents

- gemma4-hackathon-submission-plan.md

## Constraints

- Must align rewards to authentic learning tasks
- Must use topic mastery and prior performance to choose challenge content
- Must support a hackathon-demo-friendly subset even if full implementation is deferred

## Dependencies

- FEAT-PO-005
- FEAT-PO-007

## Suggested Context Files

- src/gamification/engine.py
- src/agents/session_planner.py
- src/knowledge/student_model.py
