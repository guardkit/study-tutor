---
id: TASK-VOX-R04
title: "Fix query_student_model to the Pollen tool ABC"
task_type: feature
parent_review: TASK-REV-RCH4
feature_id: FEAT-VOICE-004
wave: 1
implementation_mode: task-work
complexity: 3
dependencies: []
repo: fleet-gateway
---

# Fix query_student_model to the Pollen tool ABC (recon D1)

`query_student_model` uses the **rejected** shape (`parameters` + `async def run()`;
returns `str`) — per the README's 13-May gotchas it would not load or fire. Conform it to
the Pollen `core_tools.Tool` ABC so the robot can actually call it (unblocks R-G3 proof and
`celebrate_achievement` for the gamification track too).

## Acceptance criteria

- **AC-R04-1**: The tool exposes `parameters_schema` (not `parameters`) and implements
  `async def __call__(...)` (not `run()`).
- **AC-R04-2**: The tool returns a `dict` result (not a bare `str`), matching the ABC.
- **AC-R04-3**: The tool loads without error under the Pollen tool loader and is offered to
  the robot's Realtime session.
- **AC-R04-4**: A tool defined with the outdated shape is **not** loaded (guards the
  negative-case scenario).
- **AC-R04-5**: All modified files pass project-configured lint/format checks with zero
  errors.

## Seam Tests

Validates the tool-interface contract at the loader boundary.

```python
"""Seam test: verify query_student_model conforms to the Pollen tool ABC."""
import pytest


@pytest.mark.seam
def test_query_student_model_conforms_to_tool_abc():
    """The tool must expose parameters_schema + async __call__ and return a dict.

    Contract: Pollen core_tools.Tool ABC (parameters_schema + async __call__).
    """
    from external_tools.query_student_model import QueryStudentModel  # adjust import

    tool = QueryStudentModel()
    assert hasattr(tool, "parameters_schema"), "must expose parameters_schema"
    assert not hasattr(tool, "parameters"), "must not use the rejected 'parameters' field"
    assert callable(getattr(tool, "__call__", None)), "must implement async __call__"
```

## Coach validation

- Tool loads under the Pollen loader probe; ABC conformance asserted; lint clean.
