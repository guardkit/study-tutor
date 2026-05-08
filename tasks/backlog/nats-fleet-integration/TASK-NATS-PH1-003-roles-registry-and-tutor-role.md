---
id: TASK-NATS-PH1-003
title: Implement roles registry and tutor role with tool_to_command mapping
task_type: scaffolding
parent_review: TASK-REV-NATS-001
feature_id: FEAT-NATS
wave: 2
implementation_mode: direct
complexity: 3
estimated_minutes: 45
status: pending
priority: critical
created: 2026-05-08 00:00:00+00:00
updated: 2026-05-08 00:00:00+00:00
dependencies:
  - TASK-NATS-PH1-001
tags:
  - nats
  - scaffolding
  - roles
  - phase-1
---

# Task: Implement roles registry and tutor role with tool_to_command mapping

## Description

Create the role-registration pattern that mirrors specialist-agent's. study-tutor has only one role (`tutor`), but the shape must match for fleet parity. The `tool_to_command` map is the canonical place to declare aliases between MCP tool names (`tutor_start_session`, etc.) and internal canonical commands (`start_session`, etc.).

Reference: [specialist-agent/src/specialist_agent/roles/registry.py:18-54](../../../../specialist-agent/src/specialist_agent/roles/registry.py) and `roles/architect/__init__.py:32-47`.

## Scope

Create:

- `src/study_tutor/roles/__init__.py` — imports the tutor role to trigger registration on package import.
- `src/study_tutor/roles/registry.py` — `register_role(name, tool_to_command, ...)`, `get_role(name)`, `_ensure_roles_registered()` (idempotent). Mirror specialist-agent's structure closely.
- `src/study_tutor/roles/tutor/__init__.py` — calls `register_role("tutor", tool_to_command={...})`.

The `tool_to_command` map for tutor:

```python
{
    "tutor_start_session":  "start_session",
    "tutor_turn":           "tutor_turn",
    "tutor_session_status": "session_status",
    "tutor_session_end":    "end_session",
}
```

## Acceptance criteria

- [ ] `from study_tutor.roles.registry import get_role; get_role("tutor")` returns a non-None role descriptor.
- [ ] `get_role("tutor").tool_to_command` returns a 4-key dict matching the table above exactly.
- [ ] `_ensure_roles_registered()` is idempotent (calling it twice does not raise or duplicate-register).
- [ ] `get_role("nonexistent")` raises a clear, named exception (`UnknownRoleError` or equivalent).
- [ ] Unit tests cover: registry round-trip, idempotency, unknown role, mapping integrity.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation notes

The mapping itself is the linchpin of the **Bug #2 fix** (regression-guarded by TASK-NATS-PH1-004). Keep the map declared *here* (not in the router) so tests can assert it independently of the router's resolution logic.

## Coach validation

```bash
pytest tests/unit/roles/ -v
ruff check src/study_tutor/roles/ tests/unit/roles/
```
