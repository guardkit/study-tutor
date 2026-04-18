# Clarification Handling

## Description

The session can detect when a user request is ambiguous, incomplete, or internally inconsistent and can pause forward progress to request a targeted clarification. Clarification handling keeps the conversation moving by narrowing uncertainty to the smallest missing decision needed for the next step, while preserving the current session context.

## Bounded Context

Session Orchestration

## Source Documents

- conversation-flow.md
- ambiguity-policy.md

## Constraints

- Must ask for clarification only when the next step cannot be completed reliably from available context
- Must preserve session context across clarification turns

## Dependencies

- FEAT-PO-017

## Suggested Context Files

- docs/conversation-flow.md
- docs/ambiguity-policy.md
