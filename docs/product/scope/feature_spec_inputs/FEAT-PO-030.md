# Session Turn Progression

## Description

The session orchestration advances a conversation turn by turn, carrying forward the active objective, prior assistant commitments, and user-provided context. It determines whether the next turn should answer directly, invoke a tool-backed step, or request clarification under the documented conversation flow.

## Bounded Context

Session Orchestration

## Source Documents

- conversation-flow.md
- session-lifecycle.md

## Constraints

- Must maintain continuity across multiple turns in the same session
- Must follow the documented turn progression and lifecycle states

## Dependencies

- FEAT-PO-017

## Suggested Context Files

- docs/conversation-flow.md
- docs/session-lifecycle.md
