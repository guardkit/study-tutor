"""Unit tests for :class:`LLMPlayerAdapter` (TASK-LCA-001).

Covers the §4 SessionState contract (consumer side) plus the
load-bearing ASSUM-008 / ASSUM-LCA-006 invariant: the prompt the
adapter feeds to ``LLMClient.generate`` on revise carries **only**
``criterion_id`` and ``target_score`` from each :class:`RubricFeedback`
entry. ``suggested_focus`` and every Coach-side free-text field
(evidence, reasoning) must be absent from the assembled prompt — this
is the security boundary between Coach and Player and the negative
test below is the regression trip-wire.

Marked with ``@pytest.mark.feat_lca`` so the FEAT-6CC5 smoke gate
selects them via ``pytest -m "feat_lca and smoke"`` (these are unit
tests, not smoke; they ride the per-feature marker but do not carry
``smoke``).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from study_tutor.roles.loader import RoleConfig
from study_tutor.tutoring.adapters.llm_player_adapter import LLMPlayerAdapter
from study_tutor.tutoring.adapters.session_state import SessionState
from study_tutor.tutoring.coach import RubricFeedback
from study_tutor.tutoring.orchestrator import PlayerLike


pytestmark = pytest.mark.feat_lca


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def role_config(tmp_path: Path) -> RoleConfig:
    """A ``RoleConfig`` whose ``player_prompt_path`` points at a tmp
    file so :meth:`LLMPlayerAdapter.__init__` can read it once at
    construction without needing a live ``roles/tutor`` tree.
    """
    prompt_path = tmp_path / "player.md"
    prompt_path.write_text(
        "You are a GCSE tutor. Answer in markdown.", encoding="utf-8"
    )
    return RoleConfig(
        id="tutor",
        name="Tutor Agent",
        description="test",
        player_prompt_path=prompt_path,
        criteria_path=None,
    )


@pytest.fixture
def session_state() -> SessionState:
    """A representative ``SessionState`` with the optional fields set."""
    return SessionState(
        session_id="sess-abc",
        student_id="lilymay",
        text_name="Macbeth",
        topic="Themes",
        focus_aos=("AO1", "AO3"),
        mode="tutor",
    )


# ---------------------------------------------------------------------------
# Protocol conformance + construction
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    """``LLMPlayerAdapter`` must satisfy the ``PlayerLike`` Protocol."""

    def test_implements_player_like_protocol(
        self, role_config: RoleConfig
    ) -> None:
        """``isinstance(adapter, PlayerLike)`` succeeds because
        ``PlayerLike`` is ``@runtime_checkable`` and the adapter exposes
        both ``respond`` and ``revise`` coroutines.
        """
        adapter = LLMPlayerAdapter(role_config=role_config)
        assert isinstance(adapter, PlayerLike)

    def test_constructor_loads_player_prompt_eagerly(
        self, role_config: RoleConfig
    ) -> None:
        """The player prompt is cached at construction so per-turn
        invocations don't reload it from disk. We verify the cached
        value is the file contents, not the path itself.
        """
        adapter = LLMPlayerAdapter(role_config=role_config)
        assert adapter._player_prompt == (
            "You are a GCSE tutor. Answer in markdown."
        )


# ---------------------------------------------------------------------------
# respond() — happy path
# ---------------------------------------------------------------------------


class TestRespond:
    """Tests for :meth:`LLMPlayerAdapter.respond`."""

    @pytest.mark.asyncio
    async def test_respond_calls_llm_client_with_player_prompt_and_returns_string(
        self, role_config: RoleConfig, session_state: SessionState
    ) -> None:
        """``respond`` builds an ``LLMClient`` and calls ``generate``
        with the learner message as the prompt and the cached player
        prompt as the system message; the returned string is forwarded
        verbatim.
        """
        adapter = LLMPlayerAdapter(role_config=role_config)

        with patch(
            "study_tutor.tutoring.adapters.llm_player_adapter.LLMClient"
        ) as MockClient:
            instance = MockClient.return_value
            instance.generate.return_value = "Macbeth's ambition drives the plot."

            result = await adapter.respond(
                session_state=session_state,
                learner_message="Why does Macbeth murder Duncan?",
            )

        assert result == "Macbeth's ambition drives the plot."
        instance.generate.assert_called_once_with(
            "Why does Macbeth murder Duncan?",
            "You are a GCSE tutor. Answer in markdown.",
        )

    @pytest.mark.asyncio
    async def test_respond_resolves_provider_at_call_time(
        self,
        role_config: RoleConfig,
        session_state: SessionState,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """SR-03: provider resolution reads the env var on every call,
        not at adapter construction. Setting ``AGENT_MODELS__REASONING_MODEL``
        between two ``respond`` calls must surface in two distinct
        ``LLMClient(provider=...)`` constructions.
        """
        adapter = LLMPlayerAdapter(role_config=role_config)

        with patch(
            "study_tutor.tutoring.adapters.llm_player_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = "ok"

            monkeypatch.setenv("AGENT_MODELS__REASONING_MODEL", "local")
            await adapter.respond(
                session_state=session_state, learner_message="hello"
            )
            monkeypatch.setenv("AGENT_MODELS__REASONING_MODEL", "bedrock")
            await adapter.respond(
                session_state=session_state, learner_message="hello"
            )

        providers = [call.kwargs.get("provider") for call in MockClient.call_args_list]
        assert providers == ["local", "bedrock"]

    @pytest.mark.asyncio
    async def test_respond_accepts_session_state_via_attribute_access(
        self, role_config: RoleConfig
    ) -> None:
        """The §4 contract mandates attribute access on ``SessionState``
        — never subscript. Constructing a ``SessionState`` (which has no
        ``__getitem__``) and passing it through ``respond`` proves the
        adapter does not regress to dict-style access; if it did, this
        call would raise ``TypeError: 'SessionState' object is not
        subscriptable`` before reaching the LLM mock.
        """
        adapter = LLMPlayerAdapter(role_config=role_config)
        state = SessionState(session_id="s", student_id="lilymay")

        with patch(
            "study_tutor.tutoring.adapters.llm_player_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = "ok"
            result = await adapter.respond(
                session_state=state, learner_message="ping"
            )

        assert result == "ok"


# ---------------------------------------------------------------------------
# revise() — assembly + LLM invocation
# ---------------------------------------------------------------------------


class TestRevise:
    """Tests for :meth:`LLMPlayerAdapter.revise`."""

    @pytest.mark.asyncio
    async def test_revise_returns_llm_response_verbatim(
        self, role_config: RoleConfig, session_state: SessionState
    ) -> None:
        adapter = LLMPlayerAdapter(role_config=role_config)
        feedback = [
            RubricFeedback(
                criterion_id="curriculum_accuracy",
                suggested_focus="ao1-themes",
                target_score=0.8,
            )
        ]

        with patch(
            "study_tutor.tutoring.adapters.llm_player_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = "Improved answer."
            result = await adapter.revise(
                session_state=session_state,
                learner_message="Why does Macbeth murder Duncan?",
                previous_response="Because he's evil.",
                rubric_feedback=feedback,
            )

        assert result == "Improved answer."

    @pytest.mark.asyncio
    async def test_revise_with_empty_rubric_feedback(
        self, role_config: RoleConfig, session_state: SessionState
    ) -> None:
        """Degenerate path: an empty ``rubric_feedback`` list still
        produces a syntactically valid prompt and forwards to
        ``LLMClient.generate`` — the orchestrator is not expected to
        invoke ``revise`` with no feedback (an accept verdict has none),
        but the Protocol allows it and we must not crash.
        """
        adapter = LLMPlayerAdapter(role_config=role_config)

        with patch(
            "study_tutor.tutoring.adapters.llm_player_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = "still ok"
            result = await adapter.revise(
                session_state=session_state,
                learner_message="hello",
                previous_response="prior",
                rubric_feedback=[],
            )

        assert result == "still ok"
        prompt_arg = MockClient.return_value.generate.call_args.args[0]
        # No rubric bullets — but the original message and previous
        # response must still be present for the LLM to ground its
        # revision on something.
        assert "hello" in prompt_arg
        assert "prior" in prompt_arg

    @pytest.mark.asyncio
    async def test_revise_with_multiple_criteria_renders_each_bullet(
        self, role_config: RoleConfig, session_state: SessionState
    ) -> None:
        """Every ``RubricFeedback`` entry produces exactly one bullet of
        the form ``criterion_id: <id>; target_score: <score>``.
        """
        adapter = LLMPlayerAdapter(role_config=role_config)
        feedback = [
            RubricFeedback(
                criterion_id="curriculum_accuracy",
                suggested_focus="ao1",
                target_score=0.85,
            ),
            RubricFeedback(
                criterion_id="quote_fidelity",
                suggested_focus="ao2",
                target_score=0.70,
            ),
            RubricFeedback(
                criterion_id="ao_alignment",
                suggested_focus="ao3",
                target_score=0.60,
            ),
        ]

        with patch(
            "study_tutor.tutoring.adapters.llm_player_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = "rev"
            await adapter.revise(
                session_state=session_state,
                learner_message="msg",
                previous_response="prev",
                rubric_feedback=feedback,
            )

        prompt_arg = MockClient.return_value.generate.call_args.args[0]
        assert "criterion_id: curriculum_accuracy; target_score: 0.85" in prompt_arg
        assert "criterion_id: quote_fidelity; target_score: 0.70" in prompt_arg
        assert "criterion_id: ao_alignment; target_score: 0.60" in prompt_arg


# ---------------------------------------------------------------------------
# revise() — load-bearing security assertions (ASSUM-008 / ASSUM-LCA-006)
# ---------------------------------------------------------------------------


class TestReviseSecurityInvariant:
    """Negative tests for the revise prompt-assembly security boundary.

    These are the regression trip-wires for ASSUM-008: a future change
    that adds ``suggested_focus`` (or any Coach free-text field) into
    the assembled prompt will fail here.
    """

    @pytest.mark.asyncio
    async def test_assembled_prompt_excludes_suggested_focus_text(
        self, role_config: RoleConfig, session_state: SessionState
    ) -> None:
        """``suggested_focus`` is the structured-vocabulary field on
        ``RubricFeedback`` that nevertheless still carries Coach-side
        text. Per ASSUM-LCA-006 it MUST NOT reach the Player prompt.
        We use a recognisable sentinel string so the assertion targets
        the leak path explicitly.
        """
        adapter = LLMPlayerAdapter(role_config=role_config)
        sentinel = "DELETE-THIS-COACH-TEXT-IF-YOU-SEE-IT"
        feedback = [
            RubricFeedback(
                criterion_id="curriculum_accuracy",
                suggested_focus=sentinel,
                target_score=0.8,
            )
        ]

        with patch(
            "study_tutor.tutoring.adapters.llm_player_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = "ok"
            await adapter.revise(
                session_state=session_state,
                learner_message="learner",
                previous_response="prev",
                rubric_feedback=feedback,
            )

        prompt_arg = MockClient.return_value.generate.call_args.args[0]
        system_arg = MockClient.return_value.generate.call_args.args[1]
        assert sentinel not in prompt_arg, (
            "suggested_focus leaked into revise prompt — re-opens the "
            "ASSUM-008 prose channel"
        )
        # System prompt is the static player.md and must not have been
        # mutated to carry feedback either.
        assert sentinel not in system_arg

    @pytest.mark.asyncio
    async def test_assembled_prompt_excludes_coach_evidence_and_reasoning(
        self,
        role_config: RoleConfig,
        session_state: SessionState,
    ) -> None:
        """The orchestrator hands the adapter only the
        ``rubric_feedback`` list from a verdict, but a future caller
        bug could conceivably pass a richer container. This test
        verifies the assembly routine itself does not accept any
        non-``RubricFeedback`` shape that would carry evidence /
        reasoning — and that even when ``suggested_focus`` happens to
        contain evidence-like prose, that prose is dropped.
        """
        adapter = LLMPlayerAdapter(role_config=role_config)
        evidence_like = "The student wrote: 'Macbeth is bad' (line 12)."
        feedback = [
            RubricFeedback(
                criterion_id="quote_fidelity",
                suggested_focus=evidence_like,
                target_score=0.5,
            )
        ]

        prompt = LLMPlayerAdapter._assemble_revise_prompt(
            learner_message="msg",
            previous_response="prev",
            rubric_feedback=feedback,
        )

        # The evidence-shaped string from suggested_focus must not
        # surface in the assembled prompt.
        assert evidence_like not in prompt
        assert "Macbeth is bad" not in prompt
        # But the structured pointers must still be present.
        assert "criterion_id: quote_fidelity" in prompt
        assert "target_score: 0.50" in prompt

    @pytest.mark.asyncio
    async def test_assembled_prompt_contains_only_documented_fields(
        self, role_config: RoleConfig
    ) -> None:
        """Property-style assertion: for every ``RubricFeedback``
        attribute that exists in the model schema, only ``criterion_id``
        and ``target_score`` may appear in the assembled prompt. Any
        other field name (``suggested_focus`` is the current third one)
        MUST be absent. This is a forward-looking guard: if the schema
        gains a new free-text field in future, this test fails until
        the assembly routine is reviewed.
        """
        feedback = [
            RubricFeedback(
                criterion_id="curriculum_accuracy",
                suggested_focus="ao1-themes",
                target_score=0.8,
            )
        ]
        prompt = LLMPlayerAdapter._assemble_revise_prompt(
            learner_message="msg",
            previous_response="prev",
            rubric_feedback=feedback,
        )

        allowed_fields = {"criterion_id", "target_score"}
        rubric_fields = set(RubricFeedback.model_fields.keys())
        forbidden_fields = rubric_fields - allowed_fields

        for field_name in forbidden_fields:
            # The literal field-name token (e.g. ``suggested_focus``)
            # must not appear in the prompt — both as a label and as a
            # rendered value if the field happened to be a fixed slug.
            assert field_name not in prompt, (
                f"forbidden RubricFeedback field {field_name!r} appears in "
                f"assembled revise prompt; security boundary violated"
            )

    def test_assembled_prompt_includes_learner_message_and_previous_response(
        self,
    ) -> None:
        """Positive companion: the two pieces of context the Player
        legitimately needs (the original learner message and its own
        previous response) must be present so revision is grounded.
        """
        feedback: list[RubricFeedback] = []
        prompt = LLMPlayerAdapter._assemble_revise_prompt(
            learner_message="UNIQUE-LEARNER-TOKEN-1",
            previous_response="UNIQUE-PREVIOUS-TOKEN-2",
            rubric_feedback=feedback,
        )
        assert "UNIQUE-LEARNER-TOKEN-1" in prompt
        assert "UNIQUE-PREVIOUS-TOKEN-2" in prompt
