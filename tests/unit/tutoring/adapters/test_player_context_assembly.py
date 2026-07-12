"""Prompt-assembly unit tests for the Player context block + memory window.

S-R4 spec §2.5 (Session-context block) and §2.6 / R13 (in-session memory
window): the Player weaves typed ``SessionState`` context and a truncated
transcript into the generation prompt. These tests pin the block content and
the oldest-first truncation behaviour, and prove a bare state produces the
exact single-message prompt (no context, no history).
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from study_tutor.roles.loader import RoleConfig
from study_tutor.tutoring.adapters.llm_player_adapter import (
    _APPROX_CHARS_PER_TOKEN,
    _TRANSCRIPT_WINDOW_TOKEN_CAP,
    _TRANSCRIPT_WINDOW_TURNS,
    LLMPlayerAdapter,
    _assemble_session_context_block,
    _build_transcript_history,
)
from study_tutor.tutoring.adapters.session_state import (
    SessionState,
    TranscriptTurn,
)


@pytest.fixture
def role_config(tmp_path: Path) -> RoleConfig:
    prompt_path = tmp_path / "player.md"
    prompt_path.write_text("SYSTEM", encoding="utf-8")
    return RoleConfig(
        id="tutor",
        name="Tutor Agent",
        description="test",
        player_prompt_path=prompt_path,
        criteria_path=None,
    )


# ---------------------------------------------------------------------------
# Session-context block (§2.5)
# ---------------------------------------------------------------------------


class TestContextBlock:
    def test_bare_state_produces_empty_block(self) -> None:
        state = SessionState(session_id="s", student_id="lilymay")
        assert _assemble_session_context_block(state) == ""

    def test_full_context_block_content(self) -> None:
        state = SessionState(
            session_id="s",
            student_id="lilymay",
            text_name="Macbeth",
            topic="Ambition",
            topic_confidence_band="struggling",
            weakest_topics=("Ambition", "Imagery"),
            recent_misconceptions=("Thinks Macbeth is purely evil",),
            grade_target="7",
        )
        block = _assemble_session_context_block(state)
        # Topic + text
        assert "- Topic: Ambition (text: Macbeth)" in block
        # design §6.1 band phrasing (not the raw band literal)
        assert "needs more work" in block
        assert "struggling" not in block
        # weakest topics + misconceptions
        assert "Weak spots to strengthen: Ambition, Imagery" in block
        assert "Misconceptions to revisit: Thinks Macbeth is purely evil" in block
        # GOAL.md §7 grade register (Grade 7 → what-how-why chain cue)
        assert "Grade 7 target:" in block
        assert "what-how-why chain" in block

    def test_band_phrasing_maps_all_bands(self) -> None:
        phrasings = {
            "struggling": "needs more work",
            "developing": "coming along",
            "secure": "feeling confident",
            "mastered": "really strong",
        }
        for band, phrase in phrasings.items():
            state = SessionState(
                session_id="s",
                student_id="lilymay",
                topic="T",
                topic_confidence_band=band,
            )
            assert phrase in _assemble_session_context_block(state)

    def test_unknown_grade_falls_back_to_grade6_register(self) -> None:
        state = SessionState(
            session_id="s", student_id="lilymay", topic="T", grade_target="99"
        )
        block = _assemble_session_context_block(state)
        assert "Grade 99 target:" in block
        # falls back to the Grade-6 register cue
        assert "what-how-why chain" in block


# ---------------------------------------------------------------------------
# In-session memory window (§2.6 / R13)
# ---------------------------------------------------------------------------


class TestTranscriptWindow:
    def test_empty_transcript_yields_no_history(self) -> None:
        state = SessionState(session_id="s", student_id="lilymay")
        assert _build_transcript_history(state) == []

    def test_role_mapping_tutor_to_assistant(self) -> None:
        state = SessionState(
            session_id="s",
            student_id="lilymay",
            transcript=(
                TranscriptTurn(role="user", content="hi"),
                TranscriptTurn(role="tutor", content="hello"),
            ),
        )
        history = _build_transcript_history(state)
        assert history == [
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "hello"},
        ]

    def test_window_truncates_to_last_n_turns_oldest_first(self) -> None:
        # 20 short turns; only the last _TRANSCRIPT_WINDOW_TURNS survive.
        turns = tuple(
            TranscriptTurn(role="user" if i % 2 == 0 else "tutor", content=f"t{i}")
            for i in range(20)
        )
        state = SessionState(
            session_id="s", student_id="lilymay", transcript=turns
        )
        history = _build_transcript_history(state)
        assert len(history) == _TRANSCRIPT_WINDOW_TURNS
        # Oldest dropped first: first surviving turn is t(20 - N).
        first_kept = 20 - _TRANSCRIPT_WINDOW_TURNS
        assert history[0]["content"] == f"t{first_kept}"
        assert history[-1]["content"] == "t19"

    def test_token_cap_drops_oldest_until_within_budget(self) -> None:
        # A handful of large turns (each near the whole budget) forces the
        # token cap (not the turn-count cap) to drop oldest first.
        char_cap = _TRANSCRIPT_WINDOW_TOKEN_CAP * _APPROX_CHARS_PER_TOKEN
        big = "x" * (char_cap // 2 + 10)  # two of these already exceed the cap
        turns = (
            TranscriptTurn(role="user", content="OLD-" + big),
            TranscriptTurn(role="tutor", content="MID-" + big),
            TranscriptTurn(role="user", content="NEW-" + big),
        )
        state = SessionState(
            session_id="s", student_id="lilymay", transcript=turns
        )
        history = _build_transcript_history(state)
        # Oldest dropped until within budget; the newest turn is always kept.
        assert history[-1]["content"].startswith("NEW-")
        assert not any(h["content"].startswith("OLD-") for h in history)


# ---------------------------------------------------------------------------
# End-to-end weaving through respond (§2.5 + §2.6)
# ---------------------------------------------------------------------------


class TestRespondWeaving:
    @pytest.mark.asyncio
    async def test_bare_state_prompt_is_byte_identical_single_message(
        self, role_config: RoleConfig
    ) -> None:
        """No context, no transcript ⇒ generate(prompt, system) unchanged."""
        adapter = LLMPlayerAdapter(role_config=role_config)
        state = SessionState(session_id="s", student_id="lilymay")
        with patch(
            "study_tutor.tutoring.adapters.llm_player_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = "ok"
            await adapter.respond(session_state=state, learner_message="ping")
        MockClient.return_value.generate.assert_called_once_with("ping", "SYSTEM")

    @pytest.mark.asyncio
    async def test_context_and_history_are_passed_to_generate(
        self, role_config: RoleConfig
    ) -> None:
        adapter = LLMPlayerAdapter(role_config=role_config)
        state = SessionState(
            session_id="s",
            student_id="lilymay",
            topic="Ambition",
            topic_confidence_band="developing",
            transcript=(
                TranscriptTurn(role="user", content="earlier q"),
                TranscriptTurn(role="tutor", content="earlier a"),
            ),
        )
        with patch(
            "study_tutor.tutoring.adapters.llm_player_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = "ok"
            await adapter.respond(
                session_state=state, learner_message="current q"
            )
        args = MockClient.return_value.generate.call_args.args
        prompt, system, history = args
        assert "Session context:" in prompt
        assert prompt.endswith("current q")
        assert system == "SYSTEM"
        assert history == [
            {"role": "user", "content": "earlier q"},
            {"role": "assistant", "content": "earlier a"},
        ]
