"""Unit tests for ``_default_coach_model()`` (TASK-LCA-004 / AC-LCA-07).

The Coach-side counterpart of ``_default_player_model`` deliberately has
**no fallback default** (decision D-COACH-05). These tests pin that
contract: the helper must return the env-var value verbatim when set, and
must raise :class:`LLMProviderError` naming the env var literally when
unset or empty.

The companion ``_default_player_model`` parity test in
``tests/unit/llm/test_provider_resolution.py`` is intentionally left
untouched — that file is the integration-contract seam for the Player
side of the same SR-03 invariant; this file is the seam for the Coach
side.
"""

from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from study_tutor.llm.client import LLMProviderError, _default_coach_model


@pytest.mark.feat_lca
class TestDefaultCoachModel:
    """AC-LCA-07 + D-COACH-05: env-var-driven Coach provider resolution."""

    def test_returns_env_var_value_verbatim_when_set(self) -> None:
        """When ``AGENT_MODELS__COACH_MODEL`` is set, return it untransformed.

        The verbatim guarantee is load-bearing: the value flows directly
        into ``CoachConfig.provider`` and is compared by string equality
        against ``PlayerConfig.provider`` inside
        ``validate_coach_config`` (D3 invariant). Any silent
        canonicalisation (e.g. lowercasing) here would let the same
        provider with different casing slip past the same-provider
        rejection.
        """
        with patch.dict(
            os.environ, {"AGENT_MODELS__COACH_MODEL": "anthropic"}, clear=False
        ):
            assert _default_coach_model() == "anthropic"

        # Mixed case must round-trip unchanged so the D3 string-equality
        # comparison sees exactly what the operator typed.
        with patch.dict(
            os.environ, {"AGENT_MODELS__COACH_MODEL": "OpenAI"}, clear=False
        ):
            assert _default_coach_model() == "OpenAI"

    def test_raises_with_env_var_named_when_unset(self) -> None:
        """AC-LCA-07: unset env var → ``LLMProviderError`` naming the var.

        Operator-search-ergonomics: the env-var name appears literally in
        the error message so an operator can grep logs for
        ``AGENT_MODELS__COACH_MODEL`` and find the boot failure line
        without having to know the surrounding prose.
        """
        env_without = {
            k: v
            for k, v in os.environ.items()
            if k != "AGENT_MODELS__COACH_MODEL"
        }
        with patch.dict(os.environ, env_without, clear=True):
            with pytest.raises(LLMProviderError) as exc_info:
                _default_coach_model()
        assert "AGENT_MODELS__COACH_MODEL" in str(exc_info.value)

    def test_raises_with_env_var_named_when_empty_string(self) -> None:
        """AC-LCA-07: empty string is treated identically to unset.

        ``.env.example`` ships ``AGENT_MODELS__COACH_MODEL=`` (no value)
        as the placeholder, which dotenv loaders will surface as the
        empty string. We treat empty and whitespace-only the same as
        "operator did not configure this" so the boot smoke check fails
        loudly rather than silently passing an empty provider id into
        the orchestrator factory.
        """
        with patch.dict(
            os.environ, {"AGENT_MODELS__COACH_MODEL": ""}, clear=False
        ):
            with pytest.raises(LLMProviderError) as exc_info:
                _default_coach_model()
        assert "AGENT_MODELS__COACH_MODEL" in str(exc_info.value)

    def test_raises_when_whitespace_only(self) -> None:
        """Whitespace-only values are equivalent to empty (defensive).

        A stray space or newline in the env file would otherwise pass
        the truthiness check but produce a meaningless provider id.
        """
        with patch.dict(
            os.environ, {"AGENT_MODELS__COACH_MODEL": "   "}, clear=False
        ):
            with pytest.raises(LLMProviderError) as exc_info:
                _default_coach_model()
        assert "AGENT_MODELS__COACH_MODEL" in str(exc_info.value)

    def test_reads_env_at_call_time_not_import_time(self) -> None:
        """SR-03: the helper must consult ``os.environ`` on each call.

        Pre-imported reads would let a server boot succeed under one
        configuration and then silently keep that captured value across
        a runtime env-var update. Boot-time snapshot semantics are still
        correct (D-COACH-05) — this just guarantees the snapshot is
        taken when the smoke check runs, not at module import.
        """
        # Two patches in sequence; if the helper cached at import we would
        # see "first" both times.
        with patch.dict(
            os.environ, {"AGENT_MODELS__COACH_MODEL": "first"}, clear=False
        ):
            assert _default_coach_model() == "first"
        with patch.dict(
            os.environ, {"AGENT_MODELS__COACH_MODEL": "second"}, clear=False
        ):
            assert _default_coach_model() == "second"
