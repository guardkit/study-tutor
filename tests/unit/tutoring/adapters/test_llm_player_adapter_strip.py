"""Unit tests for ``_strip_think_tokens`` (TASK-PTS-001).

The fine-tuned Gemma 4 26B-A4B MoE Player model emits
``<think>...</think>`` reasoning blocks ahead of the student-facing
tutoring response. ``_strip_think_tokens`` is the Player-adapter-side
sanitiser that prevents those reasoning channels from reaching the
``tutor_response`` field on the orchestrator's envelope.

These tests target the helper directly (as a module-private pure
function) rather than going through ``LLMPlayerAdapter.respond`` /
``revise``: the helper has no adapter state, and direct tests avoid
materialising a ``RoleConfig`` plus a player-prompt file on disk.

Marked ``@pytest.mark.feat_lca`` so the FEAT-6CC5 smoke gate finds
them via ``pytest -m "feat_lca and smoke"`` (these are unit tests, not
smoke; they ride the per-feature marker but do not carry ``smoke``).
"""
from __future__ import annotations

import pytest

from study_tutor.tutoring.adapters.llm_player_adapter import (
    _strip_think_tokens,
)


pytestmark = pytest.mark.feat_lca


class TestStripThinkTokens:
    """Direct tests for the module-private ``_strip_think_tokens`` helper."""

    def test_strip_well_formed_think_block_removes_block_and_trims_leading_whitespace(
        self,
    ) -> None:
        """A single well-formed ``<think>...</think>`` block followed by
        a blank-line separator and the actual response is removed
        wholesale; the leading whitespace left by the strip is trimmed.
        """
        raw = "<think>\nReasoning here.\n</think>\n\nActual response."
        assert _strip_think_tokens(raw) == "Actual response."

    def test_strip_well_formed_think_block_with_multiple_blocks(self) -> None:
        """Multiple ``<think>...</think>`` blocks separated by content
        are all removed, leaving the non-think content intact.
        """
        raw = (
            "<think>First reasoning.</think>\n\n"
            "First response.\n\n"
            "<think>Second reasoning.</think>\n\n"
            "Second response."
        )
        # After stripping both blocks, the leading whitespace from the
        # first block's removal is ``lstrip``'d; mid-string whitespace
        # left by the second block's removal is preserved (the helper
        # only trims at the head — the model's natural ``\n\n``
        # paragraph breaks are part of legitimate response shape).
        result = _strip_think_tokens(raw)
        assert result.startswith("First response.")
        assert "Second response." in result
        assert "<think>" not in result
        assert "</think>" not in result
        assert "First reasoning." not in result
        assert "Second reasoning." not in result

    def test_strip_unclosed_think_prefix_uses_blank_line_delimiter(
        self,
    ) -> None:
        """When the model truncates ``</think>``, the dangling opener
        is stripped up to and including the first ``\\n\\n`` boundary
        the model uses between reasoning and response.
        """
        raw = "<think>\nReasoning with no close tag.\n\nActual response."
        assert _strip_think_tokens(raw) == "Actual response."

    def test_strip_passthrough_when_no_think_tags(self) -> None:
        """Output with no reasoning preamble is returned unchanged."""
        raw = "Plain tutoring response with no reasoning preamble."
        assert _strip_think_tokens(raw) == raw
