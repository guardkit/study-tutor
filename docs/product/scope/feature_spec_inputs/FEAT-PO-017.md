# Confidence-Based Response Policy

## Description

The assistant applies a documented confidence policy to decide whether it should answer directly, provide a qualified response, or seek clarification before proceeding. This policy gives session orchestration a stable decision signal without requiring the full evaluation harness to be active in the conversation loop.

## Bounded Context

Decision Policy

## Source Documents

- ambiguity-policy.md
- response-policy.md

## Constraints

- Must align with documented confidence and ambiguity thresholds
- Must support direct answer, qualified answer, and clarification outcomes

## Dependencies

None

## Suggested Context Files

- docs/ambiguity-policy.md
- docs/response-policy.md
