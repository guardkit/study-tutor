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
import logging
import re
from typing import AsyncIterator, Iterable

from study_tutor.llm.client import LLMClient, _default_player_model
from study_tutor.roles.loader import RoleConfig
from study_tutor.tutoring.adapters.session_state import SessionState
from study_tutor.tutoring.coach import RubricFeedback

logger = logging.getLogger(__name__)


_REVISE_PROMPT_HEADER = (
    "Your previous tutoring response did not meet the rubric on every "
    "criterion. Revise the response so each listed criterion reaches at "
    "least its target score. Do not invent new content; refine what is "
    "below."
)


# ---------------------------------------------------------------------------
# Session-context block + in-session-memory window (spec §2.5 / §2.6 / R13)
# ---------------------------------------------------------------------------

#: §2.6 in-session-memory window: the maximum number of prior transcript
#: turns folded into the Player generation prompt. Oldest turns are dropped
#: first (both when the window exceeds this count and when the token cap
#: below is exceeded).
_TRANSCRIPT_WINDOW_TURNS: int = 12

#: §2.6 token budget for the transcript window. We cannot tokenise cheaply on
#: the hot path, so we approximate one token ≈ 4 characters (the usual English
#: heuristic) and cap the summed content length. Oldest turns are dropped
#: first until the window fits. The cap lives here, beside the prompt
#: assembly, per R13.
_TRANSCRIPT_WINDOW_TOKEN_CAP: int = 1500
_APPROX_CHARS_PER_TOKEN: int = 4

#: design.md §6.1 Reachy phrasing for each confidence band. Keyed by the
#: ``ConfidenceBand`` literal carried on ``SessionState.topic_confidence_band``.
_BAND_PHRASING: dict[str, str] = {
    "struggling": "needs more work",
    "developing": "coming along",
    "secure": "feeling confident",
    "mastered": "really strong",
}

#: GOAL.md §7 grade-target register: a one-line calibration cue per grade band
#: so the Player pitches its scaffolding depth and expected output to the
#: learner's target. Grades outside the table fall back to the Grade-6 cue
#: (GOAL.md §7 default midpoint).
_GRADE_REGISTER: dict[str, str] = {
    "1": "comprehension and basic answer structure; one technique at a time",
    "2": "comprehension and basic answer structure; one technique at a time",
    "3": "comprehension and basic answer structure; one technique at a time",
    "4": "comprehension and basic answer structure; one technique at a time",
    "5": "comprehension and basic answer structure; one technique at a time",
    "6": "the what-how-why chain; expect embedded quotation and effect",
    "7": "the what-how-why chain; expect embedded quotation and effect",
    "8": "conceptual thinking across the whole text; layered interpretation",
    "9": "conceptual thinking across the whole text; layered interpretation",
}
_DEFAULT_GRADE_REGISTER: str = _GRADE_REGISTER["6"]


def _assemble_session_context_block(session_state: SessionState) -> str:
    """Build the compact ``Session context`` block from typed fields only.

    Spec §2.5: weave topic, text, confidence-band phrasing (design §6.1),
    misconceptions-to-revisit and the grade-target register (GOAL.md §7)
    into a ≤ ~120-word block. Assembled **exclusively** from the typed
    :class:`SessionState` fields the service populated — never free-form
    store text — so the prose-injection boundary stays closed.

    Returns ``""`` when no context fields are set (e.g. a bare
    ``SessionState``), so the caller can preserve the exact single-message
    prompt for context-free turns.
    """
    lines: list[str] = []

    topic = session_state.topic
    text_name = session_state.text_name
    if topic and text_name:
        lines.append(f"- Topic: {topic} (text: {text_name})")
    elif topic:
        lines.append(f"- Topic: {topic}")
    elif text_name:
        lines.append(f"- Text: {text_name}")

    band = session_state.topic_confidence_band
    if band:
        phrasing = _BAND_PHRASING.get(band, band)
        lines.append(f"- Confidence on this topic: {phrasing}")

    if session_state.weakest_topics:
        lines.append(
            "- Weak spots to strengthen: "
            + ", ".join(session_state.weakest_topics)
        )

    if session_state.recent_misconceptions:
        lines.append(
            "- Misconceptions to revisit: "
            + "; ".join(session_state.recent_misconceptions)
        )

    grade = session_state.grade_target
    if grade:
        register = _GRADE_REGISTER.get(grade, _DEFAULT_GRADE_REGISTER)
        lines.append(f"- Grade {grade} target: {register}")

    if not lines:
        return ""
    return "Session context:\n" + "\n".join(lines)


def _build_transcript_history(
    session_state: SessionState,
) -> list[dict[str, str]]:
    """Build the messages-list history window for ``LLMClient.generate``.

    Spec §2.6 / R13: take the last :data:`_TRANSCRIPT_WINDOW_TURNS` prior
    turns, then enforce :data:`_TRANSCRIPT_WINDOW_TOKEN_CAP` by dropping the
    **oldest** turns first until the window fits. Store roles map to the
    chat vocabulary (``tutor`` → ``assistant``). Returns ``[]`` when the
    session carries no prior transcript.
    """
    turns = list(session_state.transcript)
    if not turns:
        return []

    # Keep only the most recent window of turns (oldest dropped first).
    windowed = turns[-_TRANSCRIPT_WINDOW_TURNS:]

    # Enforce the token cap by dropping oldest turns until the approximate
    # token budget is satisfied. A single over-budget final turn is kept
    # (truncating it would corrupt the most recent context).
    char_cap = _TRANSCRIPT_WINDOW_TOKEN_CAP * _APPROX_CHARS_PER_TOKEN
    total = sum(len(turn.content) for turn in windowed)
    while len(windowed) > 1 and total > char_cap:
        dropped = windowed.pop(0)
        total -= len(dropped.content)

    history: list[dict[str, str]] = []
    for turn in windowed:
        role = "assistant" if turn.role == "tutor" else "user"
        history.append({"role": role, "content": turn.content})
    return history


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


# An in-flight ``<think`` opener (possibly still missing its ``>``): from
# here on, everything is potential reasoning — hold it back.
_THINK_OPENER_ANYWHERE_RE = re.compile(r"<think\b", re.IGNORECASE)

#: Proper prefixes of ``<think`` — a raw-stream tail matching one of these
#: might be a marker split across model tokens ("<th" + "ink>"), so it is
#: withheld until the next token disambiguates.
_THINK_MARKER_PREFIXES = ("<", "<t", "<th", "<thi", "<thin")


class _IncrementalThinkFilter:
    """Streaming ``<think>`` suppression with token-split safety.

    Feeds raw model tokens; returns only the deltas that are provably
    OUTSIDE reasoning blocks, releasing them as they arrive (true
    streaming). Closed blocks are removed with the same regexes the
    batch path uses; an open ``<think`` holds everything after it; a
    buffer tail that could be the start of a split marker is withheld
    until disambiguated. ``flush()`` applies the canonical
    :func:`_strip_think_tokens` to the full raw text so end-of-stream
    semantics (dangling-opener rules, lstrip) match the batch path
    exactly.
    """

    def __init__(self) -> None:
        self._raw = ""
        #: Chars of the visible prefix already consumed (including any
        #: head whitespace swallowed by the lstrip mirror) — position
        #: bookkeeping stays on the visible-prefix plane.
        self._consumed = 0
        #: The text actually emitted (post-lstrip) — flush() compares
        #: against the canonical strip with this.
        self._emitted = ""

    def _visible_prefix(self) -> str:
        visible = _THINK_BLOCK_RE.sub("", self._raw)
        opener = _THINK_OPENER_ANYWHERE_RE.search(visible)
        if opener is not None:
            # Everything from an unclosed opener onward is reasoning
            # until its ``</think>`` arrives (at which point the block
            # regex removes the whole span).
            visible = visible[: opener.start()]
        else:
            lowered = visible.lower()
            for prefix in _THINK_MARKER_PREFIXES:
                if lowered.endswith(prefix):
                    visible = visible[: len(visible) - len(prefix)]
                    break
        return visible

    def feed(self, token: str) -> str:
        self._raw += token
        visible = self._visible_prefix()
        chunk = visible[self._consumed :]
        if not chunk:
            return ""
        self._consumed = len(visible)
        if not self._emitted:
            # Mirror the batch path's lstrip of the response head; the
            # swallowed whitespace still counts as consumed.
            chunk = chunk.lstrip()
            if not chunk:
                return ""
        self._emitted += chunk
        return chunk

    def flush(self) -> str:
        final = _strip_think_tokens(self._raw)
        if not final.startswith(self._emitted):
            # Defensive: the incremental prefix should always be a prefix
            # of the canonical strip; if not, never re-emit or contradict
            # what was already shown.
            logger.error(
                "incremental think filter diverged from canonical strip",
                extra={"emitted_chars": len(self._emitted)},
            )
            return ""
        tail = final[len(self._emitted) :]
        # Stricter than the batch function in one pathological case: a
        # MID-response dangling ``<think`` (no close, not at the head)
        # survives the canonical strip's head-anchored rules — never
        # release it here; reasoning must not reach the learner.
        opener = _THINK_OPENER_ANYWHERE_RE.search(tail)
        if opener is not None:
            tail = tail[: opener.start()]
        return tail


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

        Spec §2.5/§2.6: the typed ``session_state`` context the service
        populated is woven into the generation here — a compact
        ``Session context`` block prefixes the current turn, and the
        prior-transcript window rides as the ``LLMClient.generate``
        messages-list history. Both are assembled from typed fields only
        (:func:`_assemble_session_context_block` /
        :func:`_build_transcript_history`); when the session carries no
        context (a bare ``SessionState``), the prompt is the raw learner
        message and no history is sent — byte-identical to the prior
        single-message call.
        """
        prompt = self._weave_context_prompt(session_state, learner_message)
        history = _build_transcript_history(session_state)
        provider = _default_player_model()
        client = LLMClient(provider=provider)
        if history:
            raw = await asyncio.to_thread(
                client.generate, prompt, self._player_prompt, history
            )
        else:
            raw = await asyncio.to_thread(
                client.generate, prompt, self._player_prompt
            )
        return _strip_think_tokens(raw)

    @staticmethod
    def _weave_context_prompt(
        session_state: SessionState, learner_message: str
    ) -> str:
        """Prefix the ``Session context`` block onto the learner message.

        The reserved §2.5 seam: returns ``learner_message`` unchanged when
        no context block is produced, otherwise ``"<block>\\n\\n<message>"``.
        """
        block = _assemble_session_context_block(session_state)
        if not block:
            return learner_message
        return f"{block}\n\n{learner_message}"

    async def respond_stream(
        self,
        *,
        session_state: SessionState,
        learner_message: str,
    ) -> AsyncIterator[str]:
        """Stream a first-attempt Player response for ``learner_message``.

        Yields tokens as they arrive from the LLM. Prompt assembly matches
        ``respond()`` — the §2.5 ``Session context`` block prefixes the
        current turn and the §2.6 transcript window rides as generate-stream
        history (both from typed ``session_state`` fields only).

        This is natively async (no ``asyncio.to_thread`` bridge) because
        ``LLMClient.generate_stream`` is already async. Used by
        TASK-VS2-003 run_turn_stream.

        Note: <think> block stripping is applied by buffering the complete
        response and then yielding the cleaned tokens. This maintains
        correctness at the cost of delaying the first token until we can
        determine if it's part of a think block. For truly unbuffered
        streaming, consumers should handle think blocks themselves.

        Args:
            session_state: Session context (consumed for Protocol parity)
            learner_message: Learner's question or message

        Yields:
            Token strings with <think> blocks stripped
        """
        prompt = self._weave_context_prompt(session_state, learner_message)
        history = _build_transcript_history(session_state)
        provider = _default_player_model()
        client = LLMClient(provider=provider)

        # True incremental streaming with correct think suppression
        # (2026-08-03): the previous implementation buffered the COMPLETE
        # generation (fake streaming) and then re-yielded RAW tokens
        # through a per-token marker check — but model tokens split
        # "<think>" across pieces, so the markers slipped through and the
        # reasoning content (which contains no markers) streamed straight
        # to the learner. Receipt: session b1eec0dc turn 11 persisted a
        # raw think block. The filter holds back only what could still be
        # reasoning and releases everything else as it arrives.
        think_filter = _IncrementalThinkFilter()
        async for token in client.generate_stream(
            prompt, self._player_prompt, history
        ):
            delta = think_filter.feed(token)
            if delta:
                yield delta
        tail = think_filter.flush()
        if tail:
            yield tail

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
