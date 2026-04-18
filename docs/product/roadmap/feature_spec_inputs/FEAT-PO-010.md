# Subject-domain template for additional GCSE subjects

## Description

Create a reusable subject package pattern where each GCSE subject provides its own `GOAL.md`, source-material conventions, pedagogical style, and assessment-objective mapping while sharing the same tutoring harness. The template must make it straightforward to add Maths, French, or Spanish as configuration-led extensions, while preserving the fact that English is more analytical and other subjects may require very different tutoring behaviours.

## Bounded Context

Subject Domain BC

## Source Documents

- deepagents-patterns-review.md
- gemma4-hackathon-submission-plan.md

## Constraints

- Must require minimal or no core code changes for a new subject
- Must separate subject pedagogy from runtime orchestration
- Must support future subject-specific source acquisition rules

## Dependencies

- FEAT-PO-001

## Suggested Context Files

- src/domains/
- domains/gcse-maths/GOAL.md
- domains/gcse-french/GOAL.md
- domains/gcse-spanish/GOAL.md
