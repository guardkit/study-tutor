---
id: TASK-VOX-R05
title: "Port query_student_model onto the Postgres-backed read via :8100"
task_type: feature
parent_review: TASK-REV-RCH4
feature_id: FEAT-VOICE-004
wave: 2
implementation_mode: task-work
complexity: 5
dependencies: [TASK-VOX-R04]
repo: fleet-gateway
consumer_context:
  - task: TASK-APP-001
    consumes: STUDY_TUTOR_HTTP_8100
    framework: "httpx (connect-per-call, bearer)"
    driver: "httpx"
    format_note: "Reads the student's durable record via the study-tutor HTTP adapter on :8100; bearer-authenticated, student derived server-side"
---

# Port query_student_model onto the Postgres-backed read via :8100 (recon D2)

`query_student_model` reads Graphiti (group `student-lilymay`), whose data is **frozen**
since the Postgres migration and whose write path FEAT-SMP-004 tears down. Re-point the read
at the durable store via the study-tutor HTTP adapter on `:8100` — the same surface
`ask_tutor` uses.

## Acceptance criteria

- **AC-R05-1**: The tool reads the student's learning record via the study-tutor HTTP
  adapter on `:8100` (bearer, connect-per-call), returning the student's **current durable**
  record.
- **AC-R05-2**: **No** read comes from the retired Graphiti graph — the `student-lilymay`
  group read path is removed.
- **AC-R05-3**: httpx errors degrade gracefully (the tool returns a usable "unavailable"
  result rather than raising into the Realtime session).
- **AC-R05-4**: The ABC shape from R04 is preserved (`parameters_schema` + async `__call__`
  + dict return).
- **AC-R05-5**: All modified files pass project-configured lint/format checks with zero
  errors.

## Seam Tests

```python
"""Seam test: query_student_model reads the durable store via :8100, not Graphiti."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("STUDY_TUTOR_HTTP_8100")
def test_query_student_model_reads_via_8100_not_graphiti():
    """The read must go to the :8100 adapter and never to the frozen graph.

    Contract: HTTP GET against the study-tutor adapter on :8100 (bearer).
    Producer: TASK-APP-001 (HTTP adapter, already live)
    """
    # Inject an httpx MockTransport; assert the request targets the :8100 base URL,
    # carries the bearer header, and that no graphiti client is constructed.
    pass
```

## Coach validation

- MockTransport seam test green; grep confirms no Graphiti import/read remains; lint clean.
