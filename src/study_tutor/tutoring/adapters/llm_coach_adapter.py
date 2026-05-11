"""Production ``CoachLike`` adapter backed by ``LLMClient`` (TASK-LCA-002).

Wraps the shared :class:`~study_tutor.llm.client.LLMClient` to satisfy the
:class:`~study_tutor.tutoring.orchestrator.CoachLike` Protocol surface
consumed by :class:`PlayerCoachOrchestrator`.

Path C (hybrid) per the FEAT-6CC5 brief: the LLM emits per-criterion JSON;
deterministic post-processing via
:func:`study_tutor.tutoring.coach.rubric.parse_coach_output` assembles the
:class:`CoachVerdict`. Coach prompt assembly mirrors the sister
:class:`~study_tutor.tutoring.adapters.llm_player_adapter.LLMPlayerAdapter`
in shape: a static system prompt cached at construction, a freshly-built
user prompt per call, no per-session state.

Provider resolution follows the SR-03 call-time pattern (see
:func:`study_tutor.llm.client._default_coach_model`): ``LLMClient`` is
constructed per-call (not at adapter construction) so an env-var rotation
between turns is observed without restarting the server. Unlike the
Player-side helper, ``_default_coach_model`` raises
:class:`LLMProviderError` when ``AGENT_MODELS__COACH_MODEL`` is unset
rather than falling back to a default — propagating that exception is
intentional and lets the orchestrator surface a clear configuration
error rather than silently defaulting onto the Player's provider and
violating the D3 two-provider invariant (ASSUM-LCA-009).

The Protocol declares ``evaluate`` as ``async`` while
:meth:`LLMClient.generate` is synchronous and uses ``httpx`` under the
hood; we bridge with :func:`asyncio.to_thread` to avoid pinning the
event loop on the network call (matching the existing MCP-adapter
pattern at ``study_tutor.mcp.adapter.MCPAdapter.tutor_turn`` and
the sister Player adapter).

:class:`MalformedCoachOutputError` from :func:`parse_coach_output` is
deliberately NOT caught here — per AC-LCA-06 it propagates so the
orchestrator's bounded-revision loop can route the turn to
``decision=fallback`` (the unevaluated-turn fallback policy from
ASSUM-007).
"""
from __future__ import annotations

import asyncio

from study_tutor.knowledge.quote_verifier import VerifierMetadata
from study_tutor.llm.client import LLMClient, _default_coach_model
from study_tutor.roles.loader import RoleConfig
from study_tutor.tutoring.adapters.session_state import SessionState
from study_tutor.tutoring.coach import CoachVerdict, parse_coach_output


_COACH_PROMPT_HEADER = (
    "Evaluate the tutor response below against the six rubric criteria. "
    "Return JSON conforming to the CoachVerdict schema. Use only the "
    "structured rubric_feedback shape — do not add free-text feedback fields."
)


class LLMCoachAdapter:
    """Production :class:`CoachLike` implementation backed by ``LLMClient``.

    Holds no per-session state — the coach system prompt is static for
    the lifetime of the process and is loaded once at construction;
    every ``evaluate`` call resolves the provider afresh and builds a
    new ``LLMClient``. Two concurrent sessions sharing one adapter
    therefore cannot leak observations through the adapter.
    """

    def __init__(self, role_config: RoleConfig) -> None:
        """Cache the coach system prompt resolved from ``role_config``.

        Reading the prompt at construction time (not per-call) is
        deliberate: the prompt is a static role manifest artefact, and
        re-reading it on every turn would burn disk I/O on the hot path
        without changing behaviour. ``RoleConfig.load_coach_prompt``
        raises :class:`FileNotFoundError` when the manifest omits
        ``coach.prompt_file`` or the resolved file is missing — both
        branches surface here at boot rather than mid-session.
        """
        self._coach_prompt = role_config.load_coach_prompt()

    async def evaluate(
        self,
        *,
        session_state: SessionState,
        learner_message: str,
        player_response: str,
        verifier_metadata: VerifierMetadata | None = None,
    ) -> CoachVerdict:
        """Score ``player_response`` against the rubric and return a verdict.

        Provider is resolved at call time (SR-03). ``LLMClient.generate``
        is sync (httpx under the hood) — bridged via
        :func:`asyncio.to_thread` so the orchestrator's event loop is
        not pinned during the network call.

        The ``verifier_metadata`` keyword is accepted (per
        ``PlayerCoachOrchestrator._evaluate_with_metadata``'s guarded-
        forwarding contract) but intentionally **not** woven into the
        Phase-1 Coach prompt. Bug #10 (2026-05-11 run-3): rejecting the
        kwarg here raised ``TypeError`` inside the orchestrator's
        forward call and surfaced as ``coach_unreachable: TypeError:
        LLMCoachAdapter.evaluate() got an unexpected keyword argument
        'verifier_metadata'`` whenever the upstream quote-verifier
        produced metadata. Phase-2 Coach calibration owns wiring
        ``VerifierMetadata`` (primary/secondary/fuzzy match lists,
        ``retrieval_skipped_reason``, ``verifier_exception``) into the
        evaluation prompt so the Coach can suppress quote_fidelity
        down-rank for legitimately-skipped retrievals. Touching the
        parameter below mirrors the ``session_state`` "consume but
        ignore" idiom on this adapter (and on the sister Player
        adapter) so a future Phase-2 enhancement is a one-site grep.

        Raises:
            MalformedCoachOutputError: When the LLM returns non-JSON or
                schema-invalid output. Propagated unchanged so the
                orchestrator can route ``decision=fallback`` (per
                AC-LCA-06 + ASSUM-007).
            LLMProviderError: When ``AGENT_MODELS__COACH_MODEL`` is
                unset at call time (per
                :func:`_default_coach_model`).
        """
        # Touch the typed session_state so the parameter is observably
        # consumed (mypy/pyright noise control); we deliberately do not
        # subscript it — attribute access is the §4 contract. Mirrors
        # the sister Player adapter.
        _ = session_state.session_id
        # Phase-1 Coach does not consume verifier_metadata yet — Phase-2
        # owns the prompt-grounding integration (see docstring above).
        _ = verifier_metadata
        prompt = self._assemble_coach_prompt(
            session_state=session_state,
            learner_message=learner_message,
            player_response=player_response,
        )
        provider = _default_coach_model()
        client = LLMClient(provider=provider)
        raw = await asyncio.to_thread(
            client.generate, prompt, self._coach_prompt
        )
        # Intentionally NOT wrapped in try/except — MalformedCoachOutputError
        # propagates to the orchestrator's bounded-revision loop per
        # AC-LCA-06.
        return parse_coach_output(raw)

    @staticmethod
    def _assemble_coach_prompt(
        *,
        session_state: SessionState,
        learner_message: str,
        player_response: str,
    ) -> str:
        """Build the deterministic Coach evaluation prompt.

        ``session_state.text_name`` and ``session_state.topic`` are
        woven in as labelled fields so the Coach can ground its
        criterion scoring (curriculum_accuracy, ao_alignment,
        quote_fidelity in particular) against the session metadata.
        Both fields are optional on :class:`SessionState`; when ``None``
        we render ``"unspecified"`` rather than the literal Python
        ``"None"`` token so the prompt remains byte-stable across
        baseline-degraded sessions and humans skimming logs are not
        confused into thinking the Coach received a nullish marker.

        Format is intentionally simple labelled fields rather than a
        templated ``coach.md`` placeholder substitution — Phase-1
        grounding is exploratory (per ASSUM-LCA-010) and a fixed inline
        format keeps the assembly site grep-checkable. Calibration of
        the grounding scheme is Phase-2 territory.

        ``focus_aos``, ``mode``, ``student_id`` and ``session_id`` are
        deliberately NOT woven into the prompt — the AC scope is
        ``text_name`` and ``topic`` only, and widening the surface
        without a matching test would silently expand the Coach's
        contextual inputs.
        """
        text_name = session_state.text_name or "unspecified"
        topic = session_state.topic or "unspecified"
        return (
            f"{_COACH_PROMPT_HEADER}\n\n"
            f"Text: {text_name}\n"
            f"Topic: {topic}\n\n"
            f"Learner message:\n{learner_message}\n\n"
            f"Tutor response to evaluate:\n{player_response}"
        )


__all__ = ["LLMCoachAdapter"]
