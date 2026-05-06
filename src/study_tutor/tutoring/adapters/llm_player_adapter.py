"""Production ``PlayerLike`` adapter backed by ``LLMClient`` (TASK-LCA-001).

Wraps the shared ``LLMClient`` to satisfy the
:class:`~study_tutor.tutoring.orchestrator.PlayerLike` Protocol surface
consumed by :class:`PlayerCoachOrchestrator`. The adapter exposes the
two coroutines the orchestrator drives directly:

* :meth:`LLMPlayerAdapter.respond` — first-attempt Player generation,
  parameterised solely by the learner message and the static player
  system prompt loaded once at construction.
* :meth:`LLMPlayerAdapter.revise` — subsequent-attempt generation driven
  by structured :class:`RubricFeedback` from the Coach.

Load-bearing safety invariant (ASSUM-008 / ASSUM-LCA-006): the prompt
assembled by :meth:`_assemble_revise_prompt` carries **only** structured
criterion pointers — ``criterion_id`` and ``target_score`` — and never
free-text reasoning, evidence strings, or ``RubricFeedback.suggested_focus``.
The latter exists in the schema as a fixed-vocabulary slug for future
use, but feeding it into the Player prompt re-opens the prose-injection
channel TASK-DTL-001 specifically closed and would let Coach-side text
leak across the security boundary in spite of the shape constraints
enforced one layer up. Coach evidence and reasoning live on
:class:`~study_tutor.tutoring.coach.CoachVerdict`/
:class:`~study_tutor.tutoring.coach.CriterionScore` and never reach this
module — they cannot leak through ``revise`` because the orchestrator
hands us only ``rubric_feedback`` from the verdict.

Provider resolution follows the SR-03 call-time pattern from
:func:`study_tutor.llm.client._default_player_model`: ``LLMClient`` is
constructed per-call (not at adapter construction) so an env-var
rotation between turns is observed without restarting the server.

The Protocol declares ``respond`` / ``revise`` as ``async`` while
:meth:`LLMClient.generate` is synchronous and uses ``httpx`` under the
hood; we bridge with :func:`asyncio.to_thread` to avoid pinning the
event loop on the network call (matching the existing MCP-adapter
pattern at ``study_tutor.mcp.adapter.MCPAdapter.tutor_turn``).
"""
from __future__ import annotations

import asyncio
import re
from typing import Iterable

from study_tutor.llm.client import LLMClient, _default_player_model
from study_tutor.roles.loader import RoleConfig
from study_tutor.tutoring.adapters.session_state import SessionState
from study_tutor.tutoring.coach import RubricFeedback


_REVISE_PROMPT_HEADER = (
    "Your previous tutoring response did not meet the rubric on every "
    "criterion. Revise the response so each listed criterion reaches at "
    "least its target score. Do not invent new content; refine what is "
    "below."
)


# Matches well-formed ``<think>...</think>`` blocks. ``re.DOTALL`` so the
# inner ``.`` matches newlines (the model emits multi-line reasoning);
# ``re.IGNORECASE`` is cheap insurance against capitalisation drift
# (``<Think>`` / ``<THINK>``) — not observed in production output but
# trivially defended.
_THINK_BLOCK_RE = re.compile(
    r"<think\b[^>]*>.*?</think>", re.DOTALL | re.IGNORECASE
)
# Unclosed-tag prefix: the fine-tuned Gemma 4 model sometimes truncates
# ``</think>``, leaving a dangling opener. We strip from that opener up
# to the first blank-line boundary the model uses to separate reasoning
# from response. The pattern is anchored at start-of-string after a
# leading-whitespace skip so a stray ``<think>`` mid-response does not
# eat the rest of the turn.
_UNCLOSED_THINK_PREFIX_RE = re.compile(
    r"\A\s*<think\b[^>]*>.*?\n\n", re.DOTALL | re.IGNORECASE
)
# Fallback when a dangling ``<think>`` opener has no following blank
# line: drop only the marker tag itself, preserving any content the
# model produced after it. Leaking the marker without reasoning is less
# harmful than blanking the entire ``tutor_response``.
_UNCLOSED_THINK_TAG_ONLY_RE = re.compile(
    r"\A\s*<think\b[^>]*>", re.IGNORECASE
)


def _strip_think_tokens(raw: str) -> str:
    """Remove model reasoning preambles before they reach the orchestrator.

    The fine-tuned Gemma 4 26B-A4B MoE Player model emits
    ``<think>...</think>`` reasoning blocks ahead of its student-facing
    response. Sanitisation lives in the Player adapter (not in
    :class:`~study_tutor.llm.client.LLMClient`) because other consumers
    of ``LLMClient`` — notably the Coach adapter — may need access to
    raw output for parsing or diagnostics.

    Handles three cases observed in session ``c78a49a0`` (2026-05-06):

    1. Well-formed pairs: any number of ``<think>...</think>`` blocks
       are removed wholesale.
    2. Unclosed prefix with blank-line delimiter: a leading ``<think>``
       with no closing tag is stripped up to and including the first
       ``\\n\\n`` boundary the model uses between reasoning and
       response.
    3. Unclosed prefix with no blank line: only the dangling ``<think>``
       opener tag is removed, preserving any content the model produced
       after it (Hippocratic choice — leaking a marker is less harmful
       than emptying the turn).

    Trailing leading-whitespace artefacts are trimmed via ``lstrip``.
    """
    cleaned = _THINK_BLOCK_RE.sub("", raw)
    if _UNCLOSED_THINK_PREFIX_RE.match(cleaned):
        cleaned = _UNCLOSED_THINK_PREFIX_RE.sub("", cleaned, count=1)
    elif _UNCLOSED_THINK_TAG_ONLY_RE.match(cleaned):
        cleaned = _UNCLOSED_THINK_TAG_ONLY_RE.sub("", cleaned, count=1)
    return cleaned.lstrip()


class LLMPlayerAdapter:
    """Production :class:`PlayerLike` implementation backed by ``LLMClient``.

    Holds no per-session state — the player system prompt is static for
    the lifetime of the process and is loaded once at construction; every
    ``respond`` / ``revise`` call resolves the provider afresh and builds
    a new ``LLMClient``. Two concurrent sessions sharing one adapter
    therefore cannot leak observations through the adapter.
    """

    def __init__(self, role_config: RoleConfig) -> None:
        """Cache the player system prompt resolved from ``role_config``.

        Reading the prompt at construction time (not per-call) is
        deliberate: the prompt is a static role manifest artefact, and
        re-reading it on every turn would burn disk I/O on the hot path
        without changing behaviour. ``RoleConfig.load_player_prompt``
        raises :class:`FileNotFoundError` if the manifest path is
        missing — surfacing that here means a misconfigured role fails
        adapter construction at boot rather than mid-session.
        """
        self._player_prompt = role_config.load_player_prompt()

    async def respond(
        self,
        *,
        session_state: SessionState,
        learner_message: str,
    ) -> str:
        """Generate a first-attempt Player response for ``learner_message``.

        ``session_state`` is accepted for Protocol parity but its fields
        are not yet woven into the prompt — Phase-1 wiring keeps the
        prompt scope narrow (player system prompt + raw learner message)
        per the architecture in IMPLEMENTATION-GUIDE.md §2. The argument
        is read here purely so a future enhancement can route session
        context (text_name, focus_aos) without changing the call shape.
        """
        # Touch the typed session_state so the parameter is observably
        # consumed (mypy/pyright noise control); we deliberately do not
        # subscript it — attribute access is the §4 contract.
        _ = session_state.session_id
        provider = _default_player_model()
        client = LLMClient(provider=provider)
        raw = await asyncio.to_thread(
            client.generate, learner_message, self._player_prompt
        )
        return _strip_think_tokens(raw)

    async def revise(
        self,
        *,
        session_state: SessionState,
        learner_message: str,
        previous_response: str,
        rubric_feedback: list[RubricFeedback],
    ) -> str:
        """Regenerate the response using structured rubric pointers only.

        The assembled prompt carries the original learner message, the
        previous response, and one bullet per :class:`RubricFeedback`
        entry rendered as ``criterion_id: <id>; target_score: <score>``.
        Any free-text channel (``suggested_focus``, Coach reasoning,
        evidence) is excluded by construction — see
        :meth:`_assemble_revise_prompt`.
        """
        _ = session_state.session_id
        prompt = self._assemble_revise_prompt(
            learner_message=learner_message,
            previous_response=previous_response,
            rubric_feedback=rubric_feedback,
        )
        provider = _default_player_model()
        client = LLMClient(provider=provider)
        raw = await asyncio.to_thread(
            client.generate, prompt, self._player_prompt
        )
        return _strip_think_tokens(raw)

    @staticmethod
    def _assemble_revise_prompt(
        *,
        learner_message: str,
        previous_response: str,
        rubric_feedback: Iterable[RubricFeedback],
    ) -> str:
        """Build the deterministic revise prompt.

        Strictly emits ``criterion_id`` and ``target_score`` from each
        ``RubricFeedback``; ``suggested_focus`` is intentionally ignored.
        The unit-test suite asserts the absence of ``suggested_focus``
        text (and any other free-text from the Coach side) as a property
        test — adding a third field here without updating that test
        would re-open the prose-injection channel TASK-DTL-001 closed.
        """
        bullets: list[str] = []
        for entry in rubric_feedback:
            # ``target_score`` is a float in [0.0, 1.0]; format with a
            # short fixed precision so the prompt is byte-stable across
            # equivalent verdicts (helpful for snapshot-style tests and
            # for replaying a turn in diagnostics).
            bullets.append(
                f"- criterion_id: {entry.criterion_id}; "
                f"target_score: {entry.target_score:.2f}"
            )

        if bullets:
            criteria_block = "Criteria to improve:\n" + "\n".join(bullets)
        else:
            # Degenerate path: orchestrator should not normally reach
            # ``revise`` with an empty rubric (an empty feedback list
            # implies acceptance), but the Protocol does not forbid it
            # and the prompt must remain syntactically valid either way.
            criteria_block = "Criteria to improve:\n(no specific criteria provided)"

        return (
            f"{_REVISE_PROMPT_HEADER}\n\n"
            f"Original learner message:\n{learner_message}\n\n"
            f"Previous response:\n{previous_response}\n\n"
            f"{criteria_block}"
        )


__all__ = ["LLMPlayerAdapter"]
