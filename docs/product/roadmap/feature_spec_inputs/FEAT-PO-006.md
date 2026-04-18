# DeepAgents tutoring loop with quality monitor

## Description

Implement an interactive tutoring harness where the tutor generates a response, a background Coach evaluates pedagogical quality, and the system can refine or flag low-quality guidance before it reaches the student or before it is stored as a successful turn. The loop must enforce behaviours already established in the Player-Coach pattern—curriculum accuracy, AO alignment, grade-appropriate language, and scaffold-first teaching—while operating in a live session rather than a batch dataset factory.

## Bounded Context

Session Orchestration BC

## Source Documents

- deepagents-patterns-review.md
- gemma4-hackathon-submission-plan.md

## Constraints

- Coach must remain evaluative and not become a second student-facing tutor
- Must be compatible with current local serving path and later vLLM migration
- Must not introduce latency that makes sessions unusable for a teenager

## Dependencies

- FEAT-PO-002
- FEAT-PO-004
- FEAT-PO-005

## Suggested Context Files

- src/agents/tutor_agent.py
- src/agents/quality_monitor.py
- src/knowledge/rag_retrieval.py
