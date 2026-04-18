# Response Outcome Classification

## Description

The product classifies each assistant turn into a documented response outcome such as direct answer, clarification request, or constrained refusal so adjacent systems can interpret what happened in the conversation. This behaviour allows downstream monitoring and orchestration logic to distinguish whether the user received an answer, a follow-up question, or a policy-limited response.

## Bounded Context

Decision Policy

## Source Documents

- response-policy.md
- conversation-flow.md

## Constraints

- Must use the response outcomes named in the product documentation
- Must expose an interpretable outcome for each assistant turn

## Dependencies

- FEAT-PO-017

## Suggested Context Files

- docs/response-policy.md
- docs/conversation-flow.md
