# Graphiti student profile and topic confidence model

## Description

Model the student in Graphiti as persistent entities and relationships covering subject, text, topic, assessment objective, misconception, session history, confidence level, and recent activity. The model must remember what Lilymay studied previously, which English topics are secure or weak, and which misconceptions need revisiting so later tutoring turns can adapt to her actual revision history rather than starting from scratch.

## Bounded Context

Student Model BC

## Source Documents

- deepagents-patterns-review.md
- gemma4-hackathon-submission-plan.md

## Constraints

- Must support English first but be extensible to Maths, French, and Spanish
- Must represent topic confidence and misconception tracking explicitly
- Must persist enough state to drive recommendations and gamification

## Dependencies

- FEAT-PO-001
- FEAT-PO-002

## Suggested Context Files

- src/knowledge/student_model.py
- src/gamification/graphiti_store.py
- docs/adr/
