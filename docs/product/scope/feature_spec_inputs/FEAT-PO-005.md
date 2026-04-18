# Structured agent workflow for tutoring interactions

## Description

The tutoring flow is implemented as a structured multi-step agent pattern with clear stages for task setup, learner input handling, and response generation rather than a single opaque completion call. This preserves predictable orchestration boundaries and makes the tutoring experience easier to reason about, test, and demo using the agent patterns reviewed in the product documents.

## Bounded Context

Orchestration and Demo BC

## Source Documents

- deepagents-patterns-review.md
- GCSE_English_AI_Tutor_Proposal.md

## Constraints

- Must use an explicit staged workflow informed by the reviewed agent patterns
- Must remain simple enough to deliver in MVP scope

## Dependencies

- FEAT-PO-001

## Suggested Context Files

None
