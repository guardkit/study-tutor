---
complexity: 4
consumer_context:
- consumes: PydanticEntities
  driver: pydantic
  format_note: Client returns / accepts entity instances; type imports from student_model.py
  framework: Pydantic v2 (BaseModel)
  task: TASK-GSM-001
- consumes: GroupIdConstants
  driver: stdlib
  format_note: All search/write calls must pass group_ids constructed from STUDENT_GROUP_PREFIX
    / SUBJECT_GROUP_PREFIX / FLEET_GROUP_ID — no raw string literals matching these
    patterns elsewhere
  framework: string constants
  task: TASK-GSM-001
created: 2026-04-27 00:00:00+00:00
dependencies:
- TASK-GSM-001
- TASK-GSM-002
estimated_minutes: 90
feature_id: FEAT-1773
id: TASK-GSM-003
implementation_mode: task-work
parent_review: TASK-REV-7DC0
priority: high
status: design_approved
tags:
- graphiti
- client
- lazy-import
- graceful-degradation
- falkordb
task_type: feature
title: Implement Graphiti client wrapper with lazy import and graceful degradation
updated: 2026-04-27 00:00:00+00:00
wave: 2
---

# Task: Implement Graphiti client wrapper with lazy import and graceful degradation

## Description

Build the `GraphitiClient` wrapper that owns the lifecycle of a `graphiti-core` client against FalkorDB on the Synology NAS, with two load-bearing properties:

1. **Lazy import** — the module loads successfully when `graphiti-core` is not installed (per LES1 §3 + Group D `@module-load` scenario in the feature spec). Use a `try: import graphiti_core` block at function-call time, not at module top.
2. **Graceful degradation** — when the client cannot be constructed (library absent, FalkorDB unreachable, config invalid), the factory returns `None` and logs a structured warning. Callers must handle `client is None` without raising.

Per the build plan (Saturday afternoon, step 6) and the lazy-import shape from `specialist-agent/src/specialist_agent/tools/graphiti_client.py`.

## Scope

**Module** (`src/study_tutor/knowledge/graphiti_client.py`):

- `GraphitiConnectionConfig` — Pydantic config dataclass with: `falkor_host`, `falkor_port`, `database`, `llm_provider` (default `"gemini"`), `llm_model` (default `"gemini-2.5-pro"`), `embedder_url` (GB10:8001), `timeout_seconds` (default 5.0 per ASSUM-005).
- `GraphitiClient` — thin wrapper owning the `graphiti-core` client. Methods restricted to:
  - `async def healthcheck() -> bool` — calls a cheap query (e.g. `RETURN 1` on the driver) with the configured timeout
  - `async def close() -> None` — closes the driver
  - `client_or_none` property — exposes the underlying graphiti-core client (or None if unavailable)
- `async def get_client(config: GraphitiConnectionConfig) -> GraphitiClient | None` — factory with full graceful-degradation path:
  1. If `graphiti-core` import fails → log warning, return `None`
  2. If FalkorDB connection fails → log warning, return `None`
  3. If `healthcheck()` fails within `timeout_seconds` → log warning, return `None`
  4. Otherwise return `GraphitiClient`

**Module-level structured logger** with consistent fields: `event`, `error_class`, `falkor_host`, `degraded` (bool), `latency_ms`.

## Acceptance Criteria

- [ ] Module imports successfully when `graphiti-core` is uninstalled (verified by integration test that runs in a venv without graphiti-core)
- [ ] `get_client()` returns `None` (not raises) when graphiti-core is absent, FalkorDB is unreachable, or healthcheck times out
- [ ] `GraphitiConnectionConfig` rejects invalid values (negative port, non-positive timeout)
- [ ] `healthcheck()` honours `timeout_seconds` (5s default per ASSUM-005)
- [ ] Structured log line on every degradation path: `event=graphiti_client_degraded` with `error_class`, `falkor_host`, `degraded=true`
- [ ] `close()` is idempotent and safe to call when client is None
- [ ] Module docstring references the lazy-import pattern from specialist-agent
- [ ] All modified files pass project-configured lint/format checks with zero errors

## Test Requirements

- Unit tests in `tests/unit/knowledge/test_graphiti_client.py`:
  - Module imports succeed when graphiti-core mock raises ImportError
  - `get_client()` returns None with logged warning on each degradation branch (mock the failure points)
  - `GraphitiConnectionConfig` validation
  - `close()` on a None-backed client is a no-op
- Integration tests in `tests/integration/test_graphiti_client_integration.py` (gated on Synology FalkorDB availability):
  - `get_client()` returns a working `GraphitiClient` against the real Synology FalkorDB
  - `healthcheck()` succeeds in < 5s
  - Module-load test: launch a subprocess in a venv without graphiti-core, import the module, assert no ImportError

## Implementation Notes

- **Do not** call `add_episode` or `search_*` from this module. Those concerns belong to TASK-GSM-004 and TASK-GSM-005. This module's job is config + lifecycle + degradation, nothing else.
- The lazy-import must happen at function-call time (`def get_client():` body), not at module top. A top-level `try: import graphiti_core` runs at import time and would still fail if graphiti-core has a side-effect on its own import path.
- Keep this module **synchronous-friendly at module load** — only `async` methods are async. No `asyncio.run` at module scope.
- This is a **boundary task** — it bridges `graphiti-core` (external) into our typed surface. Consider this when reviewing for seam test coverage.

## Seam Test Recommendation

This task crosses an external-service boundary (FalkorDB + graphiti-core). Recommended seam tests:
- Mock-based seam test for graphiti-core absent (subprocess in clean venv)
- Boundary test for FalkorDB unreachable (point at unused port; assert None + log line)

## §4 Integration Contract Producer

This task produces two contracts consumed by downstream slices:

1. **GraphitiClient** — `GraphitiClient | None` from `get_client(config)`. Consumed by TASK-GSM-005 (query helpers call into the wrapped client) and TASK-GSM-006 (seeding writes via the helper, which uses this client).
2. **FalkorDBConnection** — `GraphitiConnectionConfig` schema. Consumed by TASK-GSM-005, TASK-GSM-006.

See `IMPLEMENTATION-GUIDE.md §4` for full contract specifications.

## Seam Tests

```python
"""Seam test: verify PydanticEntities + GroupIdConstants contracts from TASK-GSM-001."""
import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("PydanticEntities")
def test_pydantic_entities_format():
    """Verify PydanticEntities contract is honoured by the client wrapper.

    Contract: Client returns / accepts entity instances; type imports from student_model.py
    Producer: TASK-GSM-001
    """
    from study_tutor.knowledge.student_model import Student, Topic
    from study_tutor.knowledge.graphiti_client import GraphitiConnectionConfig

    assert Student is not None
    assert Topic is not None
    # Config must be importable without graphiti-core present
    cfg = GraphitiConnectionConfig(
        falkor_host="localhost",
        falkor_port=6379,
        database="test",
        embedder_url="http://localhost:8001",
    )
    assert cfg.timeout_seconds == 5.0  # ASSUM-005


@pytest.mark.seam
@pytest.mark.integration_contract("GroupIdConstants")
def test_group_id_constants_format():
    """Verify GroupIdConstants contract is honoured by the client wrapper.

    Contract: All search/write calls must pass group_ids constructed from
              STUDENT_GROUP_PREFIX / SUBJECT_GROUP_PREFIX / FLEET_GROUP_ID
              — no raw string literals matching these patterns elsewhere.
    Producer: TASK-GSM-001
    """
    from study_tutor.knowledge.student_model import (
        STUDENT_GROUP_PREFIX,
        SUBJECT_GROUP_PREFIX,
        FLEET_GROUP_ID,
    )

    # Format assertions derived from §4 contract:
    assert STUDENT_GROUP_PREFIX == "student:"
    assert SUBJECT_GROUP_PREFIX == "subject:"
    assert FLEET_GROUP_ID == "fleet:appmilla"  # study-tutor convention per phase-1-scope.md
```