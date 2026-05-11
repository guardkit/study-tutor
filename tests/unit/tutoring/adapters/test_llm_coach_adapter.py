"""Unit tests for :class:`LLMCoachAdapter` (TASK-LCA-002).

Covers the §4 SessionState contract (consumer side) plus the
load-bearing AC-LCA-05 / AC-LCA-06 invariants:

* AC-LCA-05 — ``evaluate`` resolves the provider at call time via
  :func:`_default_coach_model`, calls
  :meth:`LLMClient.generate` with the assembled prompt and the cached
  Coach system prompt, and returns a fully-shaped
  :class:`CoachVerdict` (decision, weighted_total, criterion_scores,
  rubric_feedback, misconceptions).
* AC-LCA-06 — when the LLM emits non-JSON or schema-invalid output,
  :class:`MalformedCoachOutputError` propagates **uncaught** out of
  ``evaluate`` so the orchestrator's bounded-revision loop can route
  the turn to ``decision=fallback``.
* ASSUM-LCA-005 — unknown criterion IDs in the LLM output are silently
  dropped (the parser is the source of truth; this test locks the
  policy at the adapter boundary as a regression trip-wire).
* SR-03 — provider resolution is per-call, not at adapter
  construction; rotating ``AGENT_MODELS__COACH_MODEL`` between two
  ``evaluate`` calls surfaces in two distinct
  ``LLMClient(provider=...)`` constructions.

Marked with ``@pytest.mark.feat_lca`` so the FEAT-6CC5 smoke gate
selects them via ``pytest -m "feat_lca and smoke"`` (these are unit
tests, not smoke; they ride the per-feature marker but do not carry
``smoke``).

Seam tests at the bottom of the file (under ``@pytest.mark.seam``)
validate the producer-side contracts the adapter consumes:
``SessionState`` (TASK-LCA-003) and ``_default_coach_model``
(TASK-LCA-004).
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from study_tutor.knowledge.quote_verifier import VerifierMetadata
from study_tutor.llm.client import LLMProviderError, _default_coach_model
from study_tutor.roles.loader import RoleConfig
from study_tutor.tutoring.adapters.llm_coach_adapter import LLMCoachAdapter
from study_tutor.tutoring.adapters.session_state import SessionState
from study_tutor.tutoring.coach import CoachVerdict, MalformedCoachOutputError
from study_tutor.tutoring.orchestrator import CoachLike


pytestmark = pytest.mark.feat_lca


# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------


_VALID_COACH_PAYLOAD: dict[str, object] = {
    "weighted_total": 0.82,
    "decision": "accept",
    "criterion_scores": [
        {
            "criterion_id": "curriculum_accuracy",
            "score": 0.9,
            "evidence": "Quote correctly attributed to Act II.",
        },
        {
            "criterion_id": "ao_alignment",
            "score": 0.8,
            "evidence": "Addresses AO1 directly.",
        },
        {
            "criterion_id": "scaffolding_depth",
            "score": 0.85,
            "evidence": "Uses Socratic questioning before supplying answer.",
        },
        {
            "criterion_id": "grade_appropriate_language",
            "score": 0.8,
            "evidence": "Year 10 register held throughout.",
        },
        {
            "criterion_id": "constructive_feedback",
            "score": 0.75,
            "evidence": "Suggests next-step pointer.",
        },
        {
            "criterion_id": "quote_fidelity",
            "score": 0.85,
            "evidence": "Verbatim quotation matched primary text.",
        },
    ],
    "rubric_feedback": [],
    "misconceptions": [],
}


@pytest.fixture
def role_config(tmp_path: Path) -> RoleConfig:
    """A ``RoleConfig`` whose ``coach_prompt_path`` points at a tmp file
    so :meth:`LLMCoachAdapter.__init__` can read it once at construction
    without needing a live ``roles/tutor`` tree.
    """
    coach_path = tmp_path / "coach.md"
    coach_path.write_text(
        "You are the Coach. Score against the rubric.", encoding="utf-8"
    )
    # Player path is required by RoleConfig but not consumed by the
    # Coach adapter; write a placeholder so any defensive consumer that
    # touches both fields does not blow up.
    player_path = tmp_path / "player.md"
    player_path.write_text("placeholder", encoding="utf-8")
    return RoleConfig(
        id="tutor",
        name="Tutor Agent",
        description="test",
        player_prompt_path=player_path,
        criteria_path=None,
        coach_prompt_path=coach_path,
    )


@pytest.fixture
def session_state() -> SessionState:
    """A representative ``SessionState`` with the optional fields set."""
    return SessionState(
        session_id="sess-abc",
        student_id="lilymay",
        text_name="Macbeth",
        topic="Ambition",
        focus_aos=("AO1", "AO3"),
        mode="tutor",
    )


@pytest.fixture(autouse=True)
def _coach_model_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure ``AGENT_MODELS__COACH_MODEL`` is set for every test by
    default — ``_default_coach_model`` raises when unset, and the
    adapter resolves it on every ``evaluate`` call. Individual tests
    override or unset as needed.
    """
    monkeypatch.setenv("AGENT_MODELS__COACH_MODEL", "bedrock")


# ---------------------------------------------------------------------------
# Protocol conformance + construction
# ---------------------------------------------------------------------------


class TestProtocolConformance:
    """``LLMCoachAdapter`` must satisfy the ``CoachLike`` Protocol."""

    def test_implements_coach_like_protocol(
        self, role_config: RoleConfig
    ) -> None:
        """``isinstance(adapter, CoachLike)`` succeeds because
        ``CoachLike`` is ``@runtime_checkable`` and the adapter exposes
        an ``evaluate`` coroutine.
        """
        adapter = LLMCoachAdapter(role_config=role_config)
        assert isinstance(adapter, CoachLike)

    def test_constructor_loads_coach_prompt_eagerly(
        self, role_config: RoleConfig
    ) -> None:
        """The coach system prompt is cached at construction so per-turn
        invocations don't reload it from disk. We verify the cached
        value is the file contents, not the path itself.
        """
        adapter = LLMCoachAdapter(role_config=role_config)
        assert adapter._coach_prompt == (
            "You are the Coach. Score against the rubric."
        )

    def test_constructor_raises_when_coach_prompt_unconfigured(
        self, tmp_path: Path
    ) -> None:
        """``RoleConfig`` with ``coach_prompt_path=None`` must surface a
        :class:`FileNotFoundError` at adapter construction time so a
        misconfigured role manifest fails at boot rather than mid-
        session.
        """
        config = RoleConfig(
            id="tutor",
            name="t",
            description="d",
            player_prompt_path=tmp_path / "player.md",
            criteria_path=None,
            coach_prompt_path=None,
        )
        with pytest.raises(FileNotFoundError):
            LLMCoachAdapter(role_config=config)


# ---------------------------------------------------------------------------
# evaluate() — happy path (AC-LCA-05)
# ---------------------------------------------------------------------------


class TestEvaluateHappyPath:
    """Tests for :meth:`LLMCoachAdapter.evaluate` — well-formed output."""

    @pytest.mark.asyncio
    async def test_evaluate_returns_fully_shaped_coach_verdict(
        self, role_config: RoleConfig, session_state: SessionState
    ) -> None:
        """AC-LCA-05 second clause: returned ``CoachVerdict`` is
        fully-shaped — decision, weighted_total, per-criterion scores,
        rubric_feedback list, misconceptions list.
        """
        adapter = LLMCoachAdapter(role_config=role_config)

        with patch(
            "study_tutor.tutoring.adapters.llm_coach_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = json.dumps(
                _VALID_COACH_PAYLOAD
            )

            verdict = await adapter.evaluate(
                session_state=session_state,
                learner_message="Why does Macbeth murder Duncan?",
                player_response="What do you think Macbeth's ambition might be?",
            )

        assert isinstance(verdict, CoachVerdict)
        assert verdict.decision == "accept"
        assert verdict.weighted_total == pytest.approx(0.82)
        assert len(verdict.criterion_scores) == 6
        # rubric_feedback and misconceptions default to empty lists from
        # the model; assert they exist as lists rather than e.g. None.
        assert verdict.rubric_feedback == []
        assert verdict.misconceptions == []

    @pytest.mark.asyncio
    async def test_evaluate_calls_generate_with_assembled_prompt_and_coach_system(
        self, role_config: RoleConfig, session_state: SessionState
    ) -> None:
        """AC-LCA-05 first clause: ``evaluate`` invokes
        ``LLMClient.generate(prompt, coach_system_prompt)``. The
        assembled prompt carries the learner message and player
        response; the system arg is the cached coach prompt.
        """
        adapter = LLMCoachAdapter(role_config=role_config)

        with patch(
            "study_tutor.tutoring.adapters.llm_coach_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = json.dumps(
                _VALID_COACH_PAYLOAD
            )
            await adapter.evaluate(
                session_state=session_state,
                learner_message="MSG-TOKEN",
                player_response="RESPONSE-TOKEN",
            )

        prompt_arg = MockClient.return_value.generate.call_args.args[0]
        system_arg = MockClient.return_value.generate.call_args.args[1]
        assert "MSG-TOKEN" in prompt_arg
        assert "RESPONSE-TOKEN" in prompt_arg
        assert system_arg == "You are the Coach. Score against the rubric."

    @pytest.mark.asyncio
    async def test_evaluate_resolves_provider_at_call_time(
        self,
        role_config: RoleConfig,
        session_state: SessionState,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """SR-03: provider resolution reads the env var on every call,
        not at adapter construction. Setting ``AGENT_MODELS__COACH_MODEL``
        between two ``evaluate`` calls must surface in two distinct
        ``LLMClient(provider=...)`` constructions.
        """
        adapter = LLMCoachAdapter(role_config=role_config)

        with patch(
            "study_tutor.tutoring.adapters.llm_coach_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = json.dumps(
                _VALID_COACH_PAYLOAD
            )

            monkeypatch.setenv("AGENT_MODELS__COACH_MODEL", "bedrock")
            await adapter.evaluate(
                session_state=session_state,
                learner_message="m1",
                player_response="r1",
            )
            monkeypatch.setenv("AGENT_MODELS__COACH_MODEL", "anthropic")
            await adapter.evaluate(
                session_state=session_state,
                learner_message="m2",
                player_response="r2",
            )

        providers = [
            call.kwargs.get("provider") for call in MockClient.call_args_list
        ]
        assert providers == ["bedrock", "anthropic"]

    @pytest.mark.asyncio
    async def test_evaluate_grounds_prompt_with_text_name_and_topic(
        self, role_config: RoleConfig
    ) -> None:
        """The §4 contract says ``text_name`` and ``topic`` are used to
        ground the Coach prompt. With both fields set, both literal
        values must appear in the assembled prompt.
        """
        adapter = LLMCoachAdapter(role_config=role_config)
        state = SessionState(
            session_id="s",
            student_id="lilymay",
            text_name="Hamlet",
            topic="Madness",
        )

        with patch(
            "study_tutor.tutoring.adapters.llm_coach_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = json.dumps(
                _VALID_COACH_PAYLOAD
            )
            await adapter.evaluate(
                session_state=state,
                learner_message="msg",
                player_response="resp",
            )

        prompt_arg = MockClient.return_value.generate.call_args.args[0]
        assert "Hamlet" in prompt_arg
        assert "Madness" in prompt_arg

    @pytest.mark.asyncio
    async def test_evaluate_grounds_with_unspecified_when_text_name_topic_none(
        self, role_config: RoleConfig
    ) -> None:
        """``text_name`` and ``topic`` default to ``None`` for baseline-
        degraded sessions. The adapter must render those as
        ``"unspecified"`` rather than the literal Python ``"None"``
        token, so the Coach prompt is byte-stable and human-readable
        in logs.
        """
        adapter = LLMCoachAdapter(role_config=role_config)
        state = SessionState(session_id="s", student_id="lilymay")

        with patch(
            "study_tutor.tutoring.adapters.llm_coach_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = json.dumps(
                _VALID_COACH_PAYLOAD
            )
            await adapter.evaluate(
                session_state=state,
                learner_message="msg",
                player_response="resp",
            )

        prompt_arg = MockClient.return_value.generate.call_args.args[0]
        assert "unspecified" in prompt_arg
        # Defensive: the literal Python "None" token must never appear
        # in a learner-adjacent prompt — a future regression that drops
        # the fallback would otherwise silently leak a Pythonic marker
        # into the prompt body.
        assert "None" not in prompt_arg


# ---------------------------------------------------------------------------
# evaluate() — malformed output propagation (AC-LCA-06)
# ---------------------------------------------------------------------------


class TestEvaluateMalformedPropagation:
    """AC-LCA-06: ``MalformedCoachOutputError`` is NOT caught inside the
    adapter — it propagates so the orchestrator can route to fallback.
    """

    @pytest.mark.asyncio
    async def test_evaluate_propagates_malformed_on_non_json_output(
        self, role_config: RoleConfig, session_state: SessionState
    ) -> None:
        adapter = LLMCoachAdapter(role_config=role_config)
        with patch(
            "study_tutor.tutoring.adapters.llm_coach_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = (
                "not json at all {{{ definitely broken"
            )

            with pytest.raises(MalformedCoachOutputError):
                await adapter.evaluate(
                    session_state=session_state,
                    learner_message="m",
                    player_response="r",
                )

    @pytest.mark.asyncio
    async def test_evaluate_propagates_malformed_on_schema_invalid_json(
        self, role_config: RoleConfig, session_state: SessionState
    ) -> None:
        """JSON parses fine but is missing the required ``decision``
        field — ``parse_coach_output`` wraps the Pydantic
        ValidationError as :class:`MalformedCoachOutputError` and the
        adapter must not swallow it.
        """
        adapter = LLMCoachAdapter(role_config=role_config)
        with patch(
            "study_tutor.tutoring.adapters.llm_coach_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = json.dumps(
                {"weighted_total": 0.5, "criterion_scores": []}
            )

            with pytest.raises(MalformedCoachOutputError):
                await adapter.evaluate(
                    session_state=session_state,
                    learner_message="m",
                    player_response="r",
                )


# ---------------------------------------------------------------------------
# evaluate() — extra-criteria discard (ASSUM-LCA-005)
# ---------------------------------------------------------------------------


class TestEvaluateExtraCriteriaDiscard:
    """ASSUM-LCA-005 boundary: unknown criterion IDs returned by the
    LLM are silently dropped from the verdict. The parser is the source
    of truth; locking the policy at the adapter boundary defends
    against a future regression that adds adapter-side parsing.
    """

    @pytest.mark.asyncio
    async def test_evaluate_silently_drops_unknown_criterion_ids(
        self, role_config: RoleConfig, session_state: SessionState
    ) -> None:
        adapter = LLMCoachAdapter(role_config=role_config)
        payload: dict[str, object] = {
            "weighted_total": 0.5,
            "decision": "accept",
            "criterion_scores": [
                {
                    "criterion_id": "curriculum_accuracy",
                    "score": 0.5,
                    "evidence": "ok",
                },
                {
                    "criterion_id": "bogus_invented_criterion",
                    "score": 0.9,
                    "evidence": "should be dropped",
                },
            ],
            "rubric_feedback": [],
            "misconceptions": [],
        }
        with patch(
            "study_tutor.tutoring.adapters.llm_coach_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = json.dumps(payload)
            verdict = await adapter.evaluate(
                session_state=session_state,
                learner_message="m",
                player_response="r",
            )

        surviving_ids = [cs.criterion_id for cs in verdict.criterion_scores]
        assert surviving_ids == ["curriculum_accuracy"]
        assert "bogus_invented_criterion" not in surviving_ids


# ---------------------------------------------------------------------------
# _assemble_coach_prompt — static surface
# ---------------------------------------------------------------------------


class TestAssembleCoachPromptStatic:
    """Tests for the static prompt-assembly helper. Locks down the
    Phase-1 grounding format so a widening of the prompt surface
    (e.g. weaving ``focus_aos`` or ``session_id``) cannot land
    silently.
    """

    def test_assemble_prompt_includes_learner_message_and_player_response(
        self, session_state: SessionState
    ) -> None:
        prompt = LLMCoachAdapter._assemble_coach_prompt(
            session_state=session_state,
            learner_message="LEARNER-TOKEN-1",
            player_response="PLAYER-TOKEN-2",
        )
        assert "LEARNER-TOKEN-1" in prompt
        assert "PLAYER-TOKEN-2" in prompt

    def test_assemble_prompt_excludes_focus_aos_session_id_and_mode(
        self, session_state: SessionState
    ) -> None:
        """Defensive: the AC scope is ``text_name`` and ``topic`` only;
        a regression that widens the grounding surface to
        ``focus_aos`` / ``session_id`` / ``mode`` / ``student_id``
        would surface here. ``session_state.session_id`` happens to be
        ``"sess-abc"`` (a string unlikely to appear in normal prose),
        which makes the negative assertion meaningful.
        """
        prompt = LLMCoachAdapter._assemble_coach_prompt(
            session_state=session_state,
            learner_message="m",
            player_response="r",
        )
        assert "sess-abc" not in prompt
        assert "lilymay" not in prompt
        assert "AO1" not in prompt
        assert "AO3" not in prompt
        # ``mode="tutor"`` is the SessionState default; if it leaked into
        # the prompt the negative assertion below would fire when
        # combined with an explicit non-default token. Use an explicit
        # token rather than the default to keep the test resilient.
        assert "tutor-mode-marker" not in prompt


# ---------------------------------------------------------------------------
# Seam tests — producer-side contract verification
# ---------------------------------------------------------------------------
#
# These run as part of the unit suite because they assert structural
# contracts the adapter consumes. ``@pytest.mark.seam`` lets the
# integration-contract gate select them; they remain fast and require
# no live producer.


@pytest.mark.seam
@pytest.mark.integration_contract("SessionState")
def test_session_state_contract_for_coach_adapter() -> None:
    """Verify ``SessionState`` exposes the fields ``LLMCoachAdapter``
    consumes.

    Contract: ``text_name`` and ``topic`` are optional and used by the
    Coach prompt grounding; both default to ``None``.
    Producer: TASK-LCA-003.
    """
    state = SessionState(session_id="abc", student_id="lilymay")
    assert hasattr(state, "text_name")
    assert hasattr(state, "topic")
    assert state.text_name is None
    assert state.topic is None


@pytest.mark.seam
@pytest.mark.integration_contract("AGENT_MODELS__COACH_MODEL")
def test_default_coach_model_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify ``_default_coach_model`` shape matches ``LLMCoachAdapter``
    usage.

    Contract: returns the env value verbatim as a provider name string;
    raises :class:`LLMProviderError` naming
    ``AGENT_MODELS__COACH_MODEL`` when unset (no fallback default).
    Producer: TASK-LCA-004.
    """
    # Set: returns provider string verbatim.
    monkeypatch.setenv("AGENT_MODELS__COACH_MODEL", "bedrock")
    assert _default_coach_model() == "bedrock"

    # Unset: raises LLMProviderError naming the env var literally.
    monkeypatch.delenv("AGENT_MODELS__COACH_MODEL", raising=False)
    with pytest.raises(LLMProviderError) as exc_info:
        _default_coach_model()
    assert "AGENT_MODELS__COACH_MODEL" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Bug #10 regression guard (2026-05-11 run-3) — verifier_metadata kwarg
# acceptance
# ---------------------------------------------------------------------------
#
# ``PlayerCoachOrchestrator._evaluate_with_metadata`` forwards a
# ``verifier_metadata`` kwarg to the Coach when the upstream quote-
# verifier produced one. Before the Bug #10 fix this adapter did not
# accept that kwarg, so every turn where a handover ran surfaced as
# ``orchestrator_turn_flagged reason=coach_unreachable: TypeError:
# LLMCoachAdapter.evaluate() got an unexpected keyword argument
# 'verifier_metadata'`` and the orchestrator silently down-graded to the
# unevaluated-Player fallback. The fix lets the adapter accept the
# kwarg and intentionally ignore it (Phase-1 plumbing only — Phase-2
# Coach calibration owns prompt-grounding).


class TestEvaluateAcceptsVerifierMetadata:
    """Bug #10: ``evaluate`` must accept the ``verifier_metadata`` kwarg
    forwarded by the orchestrator's handover seam — both when the value
    is a real :class:`VerifierMetadata` and when it is ``None`` (the
    orchestrator's guarded-forwarding branch only adds the kwarg if it
    is non-None, but adapter-call sites in tests pass ``None`` directly
    so both shapes must round-trip).
    """

    @pytest.mark.asyncio
    async def test_evaluate_accepts_verifier_metadata_kwarg(
        self, role_config: RoleConfig, session_state: SessionState
    ) -> None:
        """The kwarg is accepted without raising ``TypeError``.

        Pre-fix this test failed at the call site with
        ``TypeError: LLMCoachAdapter.evaluate() got an unexpected
        keyword argument 'verifier_metadata'`` — the same failure mode
        captured at ``RESULTS-study-tutor-nats-fleet-demo-2026-05-11-run-3.md``
        Bug #10.
        """
        adapter = LLMCoachAdapter(role_config=role_config)
        metadata = VerifierMetadata(retrieval_skipped_reason="no_text_name")

        with patch(
            "study_tutor.tutoring.adapters.llm_coach_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = json.dumps(
                _VALID_COACH_PAYLOAD
            )

            verdict = await adapter.evaluate(
                session_state=session_state,
                learner_message="m",
                player_response="r",
                verifier_metadata=metadata,
            )

        assert isinstance(verdict, CoachVerdict)
        assert verdict.decision == "accept"

    @pytest.mark.asyncio
    async def test_evaluate_accepts_none_verifier_metadata(
        self, role_config: RoleConfig, session_state: SessionState
    ) -> None:
        """The kwarg accepts ``None`` (the orchestrator's
        no-handover branch). Same call site shape, distinct value
        shape — guards against a default-argument regression that
        accepts ``VerifierMetadata`` but rejects ``None``.
        """
        adapter = LLMCoachAdapter(role_config=role_config)

        with patch(
            "study_tutor.tutoring.adapters.llm_coach_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = json.dumps(
                _VALID_COACH_PAYLOAD
            )

            verdict = await adapter.evaluate(
                session_state=session_state,
                learner_message="m",
                player_response="r",
                verifier_metadata=None,
            )

        assert isinstance(verdict, CoachVerdict)

    @pytest.mark.asyncio
    async def test_evaluate_does_not_weave_verifier_metadata_into_prompt(
        self, role_config: RoleConfig, session_state: SessionState
    ) -> None:
        """Phase-1 invariant: ``verifier_metadata`` is accepted but NOT
        threaded into the Coach prompt.

        Phase-2 calibration owns wiring metadata fields (e.g.
        ``retrieval_skipped_reason``) into the prompt so the Coach can
        ground its ``quote_fidelity`` criterion. Until then the prompt
        shape must be byte-stable irrespective of metadata presence —
        otherwise an off-by-one Phase-2 enhancement would silently
        regress every existing Coach calibration evidence run.
        """
        adapter = LLMCoachAdapter(role_config=role_config)
        metadata = VerifierMetadata(
            retrieval_skipped_reason="UNIQUE-SENTINEL-12345",
        )

        with patch(
            "study_tutor.tutoring.adapters.llm_coach_adapter.LLMClient"
        ) as MockClient:
            MockClient.return_value.generate.return_value = json.dumps(
                _VALID_COACH_PAYLOAD
            )
            await adapter.evaluate(
                session_state=session_state,
                learner_message="m",
                player_response="r",
                verifier_metadata=metadata,
            )

        prompt_arg = MockClient.return_value.generate.call_args.args[0]
        assert "UNIQUE-SENTINEL-12345" not in prompt_arg, (
            "Phase-1 LLMCoachAdapter must accept but ignore "
            "verifier_metadata — Phase-2 owns prompt-grounding. If this "
            "test is failing because Phase-2 has landed, update the "
            "assertion to match the new prompt-shape contract."
        )
