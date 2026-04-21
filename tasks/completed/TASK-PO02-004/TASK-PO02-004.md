---
id: TASK-PO02-004
title: In-memory tutor session state
status: completed
created: 2026-04-20T00:00:00Z
updated: 2026-04-20T13:15:00Z
completed: 2026-04-20T13:15:00Z
completed_location: tasks/completed/TASK-PO02-004/
previous_state: in_review
priority: high
task_type: feature
tags: [phase-0, session, in-memory]
complexity: 3
parent_review: TASK-REV-PO02
feature_id: FEAT-PO-002
wave: 2
implementation_mode: task-work
dependencies: [TASK-PO02-001]
estimated_minutes: 45
test_results:
  status: passed
  coverage: null
  last_run: 2026-04-20T13:00:00Z
  notes: |
    5/5 unit tests passing in tests/unit/session/test_tutor_session.py
    Covers: create, append_turn, get, end, list_active, default-store singleton,
    missing-session error paths, UUID4 uniqueness.
---

# In-memory tutor session state

## Description

Implement `src/study_tutor/session/tutor_session.py` — a minimal, in-memory session store for Phase 0. Holds `TutorSession` dataclasses keyed by `session_id`, with a turn log. Explicitly **no persistence** in Phase 0; Phase 1 adds Graphiti-backed persistence.

**Critical non-functional requirement (per Integration Contract #3 in the review):** the session data model must remain a plain dataclass (easily serialisable), not a stateful engine. Phase 1 Graphiti integration hinges on this.

## Acceptance Criteria

- [ ] `TutorSession` dataclass with fields: `session_id: str`, `subject: str`, `topic: str | None`, `started_at: datetime`, `turns: list[TutorTurn]`, `status: Literal["active", "ended"]`.
- [ ] `TutorTurn` dataclass with fields: `role: Literal["user", "tutor"]`, `content: str`, `timestamp: datetime`.
- [ ] `SessionStore` class (process-scoped in-memory dict): `create(subject, topic) -> TutorSession`, `get(session_id) -> TutorSession`, `append_turn(session_id, role, content) -> None`, `end(session_id) -> None`, `list_active() -> list[str]`.
- [ ] `session_id` is a UUID4 string.
- [ ] Module-level singleton `_store: SessionStore` is the default instance; tests can inject their own.
- [ ] No filesystem I/O, no database, no network. Everything lives in the process.
- [ ] No async methods. Keep the interface synchronous for Phase 0 (MCP handlers are already async; they call into sync methods just fine).
- [ ] Unit test at `tests/unit/session/test_tutor_session.py` covering: create → append_turn → get → end round-trip.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation Notes

- **Do not** add a `save()` / `load()` / `to_json()` method. Serialisation belongs to the Phase 1 Graphiti writer, not the session module itself.
- **Do not** add an LRU cache or eviction policy. Phase 0 leaks session memory across process lifetime — acceptable, since sessions are ended by Claude Desktop turn-taking and MCP servers are short-lived.
- The `end()` method just flips `status` — no Graphiti write, no log dump. Per the D-level note in the review, `tutor_session_end`'s MCP handler description must be "marks session ended" (not "triggers async Graphiti write").

## Reference Files

- Plan: [docs/research/ideas/phase-0-build-plan.md:139, :441](../../../docs/research/ideas/phase-0-build-plan.md#L139)
- Review report Integration Contract #3: [.claude/reviews/TASK-REV-PO02-review-report.md](../../.claude/reviews/TASK-REV-PO02-review-report.md)
