# Tool Invocation Handoff

## Description

When a documented tool route is selected, the conversation hands off the task context needed for that tool-backed step and resumes the session when the step is complete. The handoff preserves the user's active objective so the tool result can be incorporated into the next conversational turn.

## Bounded Context

Tool Use

## Source Documents

- tool-selection.md
- integration-overview.md
- session-lifecycle.md

## Constraints

- Must preserve relevant task context during tool-backed steps
- Must support returning control to the conversation after tool use

## Dependencies

- FEAT-PO-029
- FEAT-PO-030

## Suggested Context Files

- docs/tool-selection.md
- docs/integration-overview.md
- docs/session-lifecycle.md
