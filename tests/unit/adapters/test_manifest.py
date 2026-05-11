"""Tests for ``study_tutor.adapters.manifest._tutor_manifest_factory``.

Covers PH1-002 acceptance criteria:
  - happy path returns a valid AgentManifest
  - exactly 4 ToolCapability entries with the canonical tutor_* names
  - >=1 IntentCapability (Bug #5 regression guard)
  - agent_id boundary cases (kebab-case pass / fail)
  - registration with InMemoryManifestRegistry succeeds (seam contract)
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from nats_core.manifest import AgentManifest, InMemoryManifestRegistry
from study_tutor.adapters.manifest import _tutor_manifest_factory


CANONICAL_TOOL_NAMES = {
    "tutor_start_session",
    "tutor_turn",
    "tutor_session_status",
    "tutor_session_end",
}


def test_factory_returns_valid_agent_manifest():
    manifest = _tutor_manifest_factory("gcse-tutor")
    assert isinstance(manifest, AgentManifest)
    assert manifest.agent_id == "gcse-tutor"


def test_factory_produces_exactly_four_tools_with_canonical_names():
    manifest = _tutor_manifest_factory("gcse-tutor")
    assert len(manifest.tools) == 4
    assert {t.name for t in manifest.tools} == CANONICAL_TOOL_NAMES


def test_factory_produces_at_least_one_intent_bug5_guard():
    """Bug #5: InMemoryManifestRegistry.register rejects empty intents."""
    manifest = _tutor_manifest_factory("gcse-tutor")
    assert len(manifest.intents) >= 1


def test_factory_intents_use_tutoring_pattern():
    manifest = _tutor_manifest_factory("gcse-tutor")
    patterns = {intent.pattern for intent in manifest.intents}
    assert "tutoring.*" in patterns


def test_tool_parameter_schemas_match_adapter_signatures():
    """Required-fields contract with study_tutor.mcp.adapter signatures."""
    manifest = _tutor_manifest_factory("gcse-tutor")
    by_name = {t.name: t for t in manifest.tools}

    assert by_name["tutor_start_session"].parameters["required"] == [
        "student_id"
    ]
    assert set(by_name["tutor_turn"].parameters["required"]) == {
        "session_id",
        "user_message",
    }
    assert by_name["tutor_session_status"].parameters["required"] == [
        "session_id"
    ]
    assert by_name["tutor_session_end"].parameters["required"] == [
        "session_id"
    ]


async def test_manifest_registers_into_in_memory_manifest_registry():
    """Seam test: AgentManifest passes nats_core registry validation."""
    manifest = _tutor_manifest_factory("gcse-tutor")
    registry = InMemoryManifestRegistry()
    await registry.register(manifest)
    assert await registry.get("gcse-tutor") == manifest


@pytest.mark.parametrize(
    "valid_id",
    [
        "gcse-tutor",
        "tutor",
        "a",
        "agent-1",
        "x-y-z-9",
    ],
)
def test_kebab_case_agent_ids_are_accepted(valid_id):
    manifest = _tutor_manifest_factory(valid_id)
    assert manifest.agent_id == valid_id


@pytest.mark.parametrize(
    "invalid_id",
    [
        "GCSE-Tutor",   # uppercase letters
        "gcse_tutor",   # underscore
        "1-tutor",      # starts with digit
        "",             # empty
        "-tutor",       # starts with hyphen
        "tutor!",       # special character
        "Gcse-tutor",   # initial uppercase
    ],
)
def test_non_kebab_agent_ids_raise_validation_error(invalid_id):
    with pytest.raises(ValidationError):
        _tutor_manifest_factory(invalid_id)
