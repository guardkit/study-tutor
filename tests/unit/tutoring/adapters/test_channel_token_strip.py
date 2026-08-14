"""Unit tests for the channel-marker sanitiser (2026-08-14 leak).

The model behind the ``gemma4-tutor`` alias emits a second scaffolding
family alongside ``<think>``: pipe-delimited channel markers. Seven of
22 tutor rows (32%) in session ``b07d8924`` persisted them, and Rich
confirmed they rendered in the phone app — a 14-year-old reading model
internals inside her own tutoring transcript.

The raw strings below are the persisted rows, taken from
``session_turn`` before the backfill, so these tests fail against the
pre-fix code for the reason the child saw.

Marked ``@pytest.mark.feat_lca`` to ride the same per-feature marker as
the sibling ``<think>`` strip tests.
"""
from __future__ import annotations

import pytest

from study_tutor.tutoring.adapters.llm_player_adapter import (
    _IncrementalThinkFilter,
    _sanitised_or_flagged,
    _strip_model_scaffolding,
)


pytestmark = pytest.mark.feat_lca


#: Turn 43, the row quoted in fleet-gateway's finding.
TURN_43 = (
    "<|channel>thought\n<channel|>That's a great question to start with! "
    "At Grade 7 level, we need to go beyond just identifying metaphors."
)
#: Turn 13 — an unclosed header carrying an internal context identifier,
#: with real tutoring on the very next line.
TURN_13 = (
    "<|channel>thought\nm_context_001_528_500\nThat's a really important "
    "concept to understand for Macbeth! Let me ask you something first:\n\n"
    "Think about the moment when Macbeth is planning to murder King Duncan."
)
#: Turn 25 — the marker pair repeated seven times before any content.
TURN_25 = "<|channel>thought\n<channel|>" * 7 + "That's a really insightful point."
#: Turn 27 — scaffolding end to end; the model produced no tutoring.
TURN_27 = "<|channel>thought\n<channel|>"


class TestStripChannelTokens:
    """Batch sanitisation of the persisted-row shapes."""

    def test_closed_header_pair_is_removed_leaving_the_reply(self) -> None:
        assert _strip_model_scaffolding(TURN_43) == (
            "That's a great question to start with! At Grade 7 level, we "
            "need to go beyond just identifying metaphors."
        )

    def test_repeated_header_pairs_are_all_removed(self) -> None:
        """Turn 25 stacked seven pairs; one pass must clear every one."""
        assert _strip_model_scaffolding(TURN_25) == (
            "That's a really insightful point."
        )

    def test_unclosed_header_drops_the_context_id_but_keeps_the_lesson(
        self,
    ) -> None:
        """The strip is line-oriented, not blank-line-delimited.

        A ``<think>``-style strip-to-``\\n\\n`` would have eaten "That's a
        really important concept…" — the first paragraph of the actual
        tutoring — because turn 13 puts content on the line straight after
        the internal identifier.
        """
        cleaned = _strip_model_scaffolding(TURN_13)
        assert cleaned.startswith("That's a really important concept")
        assert "m_context_" not in cleaned
        assert "Think about the moment" in cleaned

    def test_reply_that_is_only_scaffolding_sanitises_to_empty(self) -> None:
        assert _strip_model_scaffolding(TURN_27) == ""

    def test_all_scaffolding_reply_is_logged_as_an_error(self, caplog) -> None:
        """An empty bubble must never be silent — turn 27's failure mode."""
        with caplog.at_level("ERROR"):
            assert _sanitised_or_flagged(TURN_27) == ""
        assert "scaffolding end to end" in caplog.text

    def test_clean_reply_is_untouched_and_logs_nothing(self, caplog) -> None:
        clean = "A metaphor compares two things without using 'like' or 'as'."
        with caplog.at_level("ERROR"):
            assert _sanitised_or_flagged(clean) == clean
        assert caplog.text == ""

    def test_stray_marker_mid_reply_loses_the_marker_not_the_text(self) -> None:
        """Markers only — the tutoring around one survives."""
        raw = "Metaphor is direct.<|im_end|> Simile uses 'like'."
        assert _strip_model_scaffolding(raw) == (
            "Metaphor is direct. Simile uses 'like'."
        )

    def test_inequalities_are_not_mistaken_for_markers(self) -> None:
        """``<`` is ordinary maths; only pipe-delimited markers go."""
        raw = "If x < 5 and y > 2, then x - y < 3."
        assert _strip_model_scaffolding(raw) == raw

    def test_think_blocks_still_stripped_alongside_channel_markers(self) -> None:
        raw = "<think>Plan the question.</think>\n\n<|channel>thought\n<channel|>What is a metaphor?"
        assert _strip_model_scaffolding(raw) == "What is a metaphor?"


class TestIncrementalFilterChannelMarkers:
    """The ``/ws`` frame stream must be as clean as the persisted row.

    fleet-gateway's finding flagged this explicitly: a fix at persistence
    alone would leave the token frames leaking.
    """

    @staticmethod
    def _run(tokens: list[str]) -> str:
        filt = _IncrementalThinkFilter()
        out = "".join(filt.feed(t) for t in tokens)
        return out + filt.flush()

    def test_marker_split_across_model_tokens_never_escapes(self) -> None:
        """The 2026-08-03 ``<think>`` regression, in the channel family.

        Model tokenisation splits ``<|channel>`` into pieces; a per-token
        equality check sees none of them and streams the lot.
        """
        tokens = ["<", "|chan", "nel>tho", "ught\n", "<chan", "nel|>", "A met", "aphor."]
        assert self._run(tokens) == "A metaphor."

    def test_content_streams_after_an_unclosed_header(self) -> None:
        """Turn 13's shape must not cost the whole turn's streaming.

        Once the header line and its identifier line have arrived, the
        reply releases incrementally — first word out at the first content
        token, not held to end-of-stream.
        """
        filt = _IncrementalThinkFilter()
        assert filt.feed("<|channel>thought\n") == ""
        assert filt.feed("m_context_001_528_500\n") == ""
        assert filt.feed("That's a really ") == "That's a really "
        assert filt.feed("important concept.") == "important concept."
        assert filt.flush() == ""

    def test_incremental_output_matches_the_batch_strip(self) -> None:
        """The two planes must agree — the filter's own invariant."""
        for raw in (TURN_43, TURN_13, TURN_25, TURN_27):
            tokens = [raw[i : i + 3] for i in range(0, len(raw), 3)]
            assert self._run(tokens) == _strip_model_scaffolding(raw), raw[:40]
