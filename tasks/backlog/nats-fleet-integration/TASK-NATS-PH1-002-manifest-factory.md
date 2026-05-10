---
id: TASK-NATS-PH1-002
title: Implement tutor manifest factory with 4 ToolCapabilities and >=1 IntentCapability
task_type: declarative
parent_review: TASK-REV-NATS-001
feature_id: FEAT-NATS
wave: 2
implementation_mode: direct
complexity: 3
estimated_minutes: 60
status: backlog
priority: critical
created: 2026-05-08 00:00:00+00:00
updated: 2026-05-10 00:00:00+00:00
reopened_reason: "FEAT-39E1 autobuild approved this task on 2026-05-08 with a coach-attested player_summary claiming 'Implemented _tutor_manifest_factory in src/study_tutor/adapters/manifest.py', but git history shows that file was never created in any commit. Re-opened on 2026-05-10 because cli/main.py:_build_nats_runtime imports study_tutor.adapters.manifest which does not exist. Root-cause investigation tracked under TASK-INV-AB1."
dependencies:
  - TASK-NATS-PH1-001
tags:
  - nats
  - declarative
  - manifest
  - phase-1
  - bug-5
---

# Task: Implement tutor manifest factory with 4 ToolCapabilities and >=1 IntentCapability

## Description

Build the `_tutor_manifest_factory(agent_id)` function that produces an `AgentManifest` advertising study-tutor's 4 commands as `ToolCapability` entries plus at least one `IntentCapability` (Bug #5 regression guard — `InMemoryManifestRegistry.register` rejects empty intents arrays).

Mirror the structure of [specialist-agent/src/specialist_agent/adapters/manifest.py](/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/adapters/manifest.py) lines 23-218 — particularly the architect role's manifest at lines 42-76 (3 IntentCapabilities + ToolCapabilities) and the product-owner role at lines 243-281.

## Scope

Create `src/study_tutor/adapters/manifest.py` with:

- `_tutor_manifest_factory(agent_id: str) -> AgentManifest` that returns an `AgentManifest` for the tutor role.
- Four `ToolCapability` entries — one per MCP tool: `tutor_start_session`, `tutor_turn`, `tutor_session_status`, `tutor_session_end`. Each with a clear description and parameter schema mirroring the existing MCP tool surface.
- At least one `IntentCapability` with `pattern="tutoring.*"` and signal phrases (e.g. "help me revise", "tutor me on", "explain", "session", "GCSE", subject names) so jarvis's intent router can dispatch.
- `agent_id` validation: kebab-case, regex `^[a-z][a-z0-9-]*$` (inherited from `nats-core`'s schema).

## Acceptance criteria

- [ ] `_tutor_manifest_factory("gcse-tutor")` returns a valid `AgentManifest` (Pydantic validation passes).
- [ ] `manifest.tools` has exactly 4 entries (`tutor_start_session`, `tutor_turn`, `tutor_session_status`, `tutor_session_end`).
- [ ] `manifest.intents` has length >= 1 (Bug #5 regression guard).
- [ ] `_tutor_manifest_factory(agent_id)` raises `ValidationError` for non-kebab-case agent_id (e.g. `"GCSE-Tutor"`, `"gcse_tutor"`, `"1-tutor"`, `""`).
- [ ] Unit tests cover: happy path, agent_id boundary cases (kebab vs not), tool count assertion, intent count >= 1 assertion.
- [ ] All modified files pass project-configured lint/format checks with zero errors.

## Implementation notes

Reference: [specialist-agent/src/specialist_agent/adapters/manifest.py:42-76](/Users/richardwoollcott/Projects/appmilla_github/specialist-agent/src/specialist_agent/adapters/manifest.py) (architect role manifest) and `:243-281` (product-owner role manifest).

Tool parameter schemas: cross-reference [src/study_tutor/mcp/server.py](../../../src/study_tutor/mcp/server.py) lines 19-58 where the same tools are registered for MCP — keep parameter names and types identical.

## Seam Tests

The following seam test validates the integration contract with the producer task. Implement this test to verify the boundary before integration.

```python
"""Seam test: verify AgentManifest contract from TASK-NATS-PH1-002."""
import pytest
from nats_core.manifest import InMemoryManifestRegistry
from study_tutor.adapters.manifest import _tutor_manifest_factory


@pytest.mark.seam
@pytest.mark.integration_contract("AgentManifest")
def test_agent_manifest_format():
    """Verify AgentManifest matches the expected format.

    Contract: Manifest has agent_id matching ^[a-z][a-z0-9-]*$, exactly 4 tools, and >=1 intent (Bug #5 guard).
    Producer: TASK-NATS-PH1-002
    """
    manifest = _tutor_manifest_factory("gcse-tutor")

    assert manifest.agent_id == "gcse-tutor"
    assert len(manifest.tools) == 4, f"Expected 4 tools, got: {len(manifest.tools)}"
    assert len(manifest.intents) >= 1, "Bug #5 regression: empty intents array not allowed"

    registry = InMemoryManifestRegistry()
    registry.register(manifest)
```

## Coach validation

```bash
pytest tests/unit/adapters/test_manifest.py -v
ruff check src/study_tutor/adapters/manifest.py tests/unit/adapters/test_manifest.py
```
