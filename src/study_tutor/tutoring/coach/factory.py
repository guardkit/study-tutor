"""Coach factory + structural invariants + canonical Pydantic models (TASK-DTL-001).

This module is the **single** Coach construction surface for FEAT-PH1-003. It owns:

1. The canonical Pydantic v2 models that shape the Coach output schema:
   :class:`CriterionScore`, :class:`RubricFeedback`,
   :class:`MisconceptionObservation`, :class:`CoachVerdict`.
2. The :func:`validate_coach_config` helper that consolidates the four
   construction-time invariants in one grep-checkable place (per Finding F2
   of TASK-REV-DTL3).
3. The :class:`Coach` AsyncSubAgent-shaped wrapper that holds Coach-side
   state and dispatches F1 misconception writes via the injected shared
   write helper (per ADR-ARCH-012 + DDR-002).
4. The :func:`create_coach` factory function that wires everything together.

**Load-bearing structural invariants** — enforced at construction, never via
prompt instruction:

D1. **No tools (D5)**: the Coach is evaluation-only. The factory hard-codes
    ``tools=[]`` on every constructed Coach and refuses any caller-supplied
    non-empty tools list at the call site.

D2. **Non-empty system_prompt (ASSUM-005 boundary)**: an empty/whitespace
    system prompt is refused before any agent is built — no evaluator can be
    silently spun up with no instructions.

D3. **Two-provider rule (ASSUM-009)**: ``Coach.provider`` must differ from
    ``Player.provider`` so a single-provider outage cannot silently take
    both sides of the loop down at once.

D4. **No filesystem backend (D5)**: :func:`create_coach` exposes no
    fs_backend / filesystem_backend parameter at all. This is asserted
    structurally via :func:`inspect.signature` so a regression that adds
    such a parameter surfaces in the validator at runtime in addition to
    the unit-test suite.

The :class:`Coach` itself is a thin AsyncSubAgent-shaped class. It will
become a true subclass of ``deepagents.AsyncSubAgent`` once that dependency
lands; the public surface (``tools``, ``provider``, ``system_prompt``,
``write_helper``) is already shape-compatible per ADR-ARCH-012.

Cross-references:
    - ADR-ARCH-012 (deepagents 0.5.3 AsyncSubAgent for Coach)
    - DDR-002 (Coach AsyncSubAgent owns misconception writes)
    - TASK-REV-DTL3 review report finding F2 (single co-located validator)
    - ASSUM-005 (Coach refuses empty system prompt)
    - ASSUM-006 (long Coach reasoning flagged, never inlined into Player)
    - ASSUM-008 (no free-text dump field on revision feedback)
    - ASSUM-009 (two-provider rule)
"""
from __future__ import annotations

import asyncio
import inspect
import logging
from dataclasses import dataclass
from typing import Any, Literal, Protocol, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, model_validator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

#: Word-count threshold above which :attr:`CoachVerdict.reasoning_long`
#: flips True. Long reasoning is routed to observability ONLY; per ASSUM-006
#: it is never pasted back into the Player's revision prompt regardless of
#: this flag's value (the flag is a signal, not a gate).
REASONING_LONG_WORD_THRESHOLD: int = 200


#: Forbidden parameter names on the :func:`create_coach` signature. Checked
#: structurally by :func:`_assert_no_fs_backend_in_signature` so a future
#: "helpful" addition surfaces immediately rather than silently widening the
#: factory's capability surface (D4 / D5 invariant).
_FORBIDDEN_FACTORY_PARAMS: frozenset[str] = frozenset(
    {"fs_backend", "filesystem_backend", "filesystem", "fs"}
)


# ---------------------------------------------------------------------------
# Provider configs
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlayerConfig:
    """Subset of the Player agent's config the Coach factory consults.

    Only ``provider`` is consumed at construction time; it is the field
    checked by the two-provider invariant (D3). Frozen so a caller cannot
    mutate the value out from under the validator after the check.
    """

    provider: str


@dataclass(frozen=True)
class CoachConfig:
    """Subset of the Coach agent's config the factory consults.

    Only ``provider`` is consumed at construction time; it is the field
    checked by the two-provider invariant (D3). Frozen for the same reason
    as :class:`PlayerConfig`.
    """

    provider: str


# ---------------------------------------------------------------------------
# Write-helper protocol (consumed surface — see TASK-GSM-004)
# ---------------------------------------------------------------------------


@runtime_checkable
class WriteHelperLike(Protocol):
    """Structural protocol for the shared misconception write helper.

    The Coach calls ``write_misconception(student_id, observation)`` via
    ``asyncio.create_task(...)`` — fire-and-forget — per CC-13 + DDR-002.
    The actual helper is implemented in TASK-GSM-004; this Protocol is the
    consumer-side shape so the Coach module remains testable with
    :class:`unittest.mock.AsyncMock` and does not couple to any concrete backend.
    """

    async def write_misconception(
        self,
        student_id: str,
        observation: Any,
    ) -> None:  # pragma: no cover - protocol declaration only
        ...


# ---------------------------------------------------------------------------
# Canonical Pydantic v2 output models
# ---------------------------------------------------------------------------


class CriterionScore(BaseModel):
    """Per-criterion rubric score on a 0.0–1.0 scale with brief evidence.

    ``extra="forbid"`` keeps the contract tight: typos in caller code or
    LLM output surface as validation errors rather than silently dropped
    fields. Per-criterion data is part of the public Coach output schema,
    so strictness here is desirable.
    """

    model_config = ConfigDict(extra="forbid")

    criterion_id: str = Field(min_length=1)
    score: float = Field(ge=0.0, le=1.0)
    evidence: str = Field(min_length=1)


class RubricFeedback(BaseModel):
    """Structured "what to improve" payload — one entry per below-threshold criterion.

    Per ASSUM-008 + the @security @revision-loop scenario in the
    feature spec, **this model deliberately has no free-text dump field**.
    Adding any of ``raw`` / ``reasoning_passthrough`` / ``notes`` /
    ``free_text`` / ``coach_text`` would re-enable the prose-injection
    channel that TASK-DTL-001 is specifically designed to close. The
    accompanying test suite (``test_factory.py::test_rubric_feedback_has_no_free_text_dump_field``)
    asserts the absence of these fields as a property test.

    ``extra="forbid"`` is the active enforcement: any caller (or LLM
    structured-output coercion) that tries to attach prose to feedback
    will fail validation rather than silently smuggle text downstream.
    """

    model_config = ConfigDict(extra="forbid")

    criterion_id: str = Field(min_length=1)
    suggested_focus: str = Field(
        min_length=1,
        description=(
            "Short structured pointer (e.g. a topic slug or AO id) at what "
            "the Player should focus on. NOT free-text — keep this to a "
            "fixed-vocabulary string."
        ),
    )
    target_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Score the Player should aim to reach on this criterion.",
    )


class MisconceptionObservation(BaseModel):
    """Canonical misconception payload that flows to ``write_misconception(...)``.

    Field set is sourced from TASK-GSM-002's
    :class:`study_tutor.knowledge.episodes.MisconceptionObservedEpisode` and
    matches the temporary surface declared by TASK-DTL-004's dispatcher
    (now re-exported from this module per the consolidation plan in
    ``study_tutor.tutoring.coach.sanitise``'s docstring).

    ``extra="allow"`` is intentional here — and DIFFERENT from the strict
    ``extra="forbid"`` on :class:`RubricFeedback`. RubricFeedback is the
    revision-loop channel where prose injection is the threat we are
    closing. MisconceptionObservation, by contrast, is a payload-pass-through
    that may be enriched downstream (e.g. the dispatcher will add
    ``observed_at``, the helper may attach trace ids); ``extra="allow"`` keeps
    that forward-compat without requiring synchronised model bumps across
    every consumer.
    """

    model_config = ConfigDict(extra="allow")

    topic_name: str = Field(
        ...,
        min_length=1,
        description="Topic the misconception pertains to.",
    )
    misconception_text: str = Field(
        ...,
        min_length=1,
        description=(
            "Free-text description of the misconception. The shared write "
            "helper sanitises and length-caps this before it reaches the store."
        ),
    )
    confidence_band_at_observation: str = Field(
        default="unknown",
        description=(
            "Student's confidence band on the topic at observation time. "
            "Defaults to 'unknown' for boundary cases where the planner has "
            "not yet recorded a confidence value for this topic."
        ),
    )
    triggering_session_id: str = Field(
        default="",
        description="Session id this observation was made within.",
    )


class CoachVerdict(BaseModel):
    """Top-level Coach output — weighted total, decision, scores, feedback.

    Per ASSUM-006: ``reasoning`` accepts arbitrary length text; the
    ``reasoning_long`` flag is set in post-validation to ``True`` iff
    ``len(reasoning.split()) > REASONING_LONG_WORD_THRESHOLD`` (200 words).
    Long reasoning is routed to observability sinks; it is NEVER inlined
    into the Player's revision prompt — that channel uses :class:`RubricFeedback`
    only.

    ``extra="forbid"`` keeps the verdict shape strict so future "helpful"
    field additions (e.g. a stray free-text ``summary``) surface in code
    review rather than as a silent prompt-injection vector.
    """

    model_config = ConfigDict(extra="forbid")

    weighted_total: float = Field(
        ge=0.0,
        le=1.0,
        description="Aggregate score across all criterion scores after weighting.",
    )
    decision: Literal["accept", "revise"] = Field(
        ...,
        description=(
            "Binary decision on whether the Player turn is accepted or "
            "must be revised. Drives the revision loop in TASK-DTL-003."
        ),
    )
    criterion_scores: list[CriterionScore] = Field(default_factory=list)
    rubric_feedback: list[RubricFeedback] = Field(default_factory=list)
    misconceptions: list[MisconceptionObservation] = Field(default_factory=list)
    reasoning: str = Field(
        default="",
        description=(
            "Free-text justification for the verdict. Accepts arbitrary "
            "length; long reasoning is flagged via ``reasoning_long`` and "
            "never inlined into the Player's revision prompt (ASSUM-006)."
        ),
    )
    reasoning_long: bool = Field(
        default=False,
        description=(
            "True iff len(reasoning.split()) > REASONING_LONG_WORD_THRESHOLD. "
            "Computed in post-validation; do not set this directly."
        ),
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_misconception_strings(cls, data: Any) -> Any:
        """Coerce bare-string ``misconceptions`` entries to objects (TASK-LCA-006).

        Belt-and-braces guard against coach LLM prompt drift: if the LLM
        emits ``misconceptions: ["The tutor treats the top..."]`` instead
        of the canonical ``[{"topic_name": ..., "misconception_text": ...}]``
        shape, each string is wrapped into a
        :class:`MisconceptionObservation` with
        ``topic_name="unspecified"`` and ``misconception_text=<string>``.

        Why ``mode="before"``: a ``field_validator`` cannot rewrite a
        bare ``str`` into a nested-model dict — by the time per-field
        validation runs, pydantic has already classified the input as
        ``type=model_type`` mismatch and raised. We must rewrite the
        ``data`` dict before per-field validation begins.

        Why this does NOT loosen ``extra="forbid"`` (AC-LCA-06-03):
        we only rewrite items that are *bare strings*. Items that are
        dicts but malformed (e.g. ``{"foo": "bar"}``) pass through
        untouched and still hit the canonical per-field validator,
        which rejects them — the safety semantics for genuinely
        malformed coach output remain intact.

        A structured ``coach_misconception_coerced`` warning is emitted
        per coercion so prompt drift surfaces in telemetry rather than
        silently turning every turn into a ``coach_unreachable``
        fallback (the regression captured in the 2026-05-12 logs).
        """
        if not isinstance(data, dict):
            # Already-built model instances, opaque mapping types, etc.
            # pass through; the canonical per-field validation path
            # handles them unchanged.
            return data

        misconceptions = data.get("misconceptions")
        if not isinstance(misconceptions, list):
            return data

        coerced: list[Any] = []
        any_coerced = False
        for item in misconceptions:
            if isinstance(item, str):
                # Truncate the logged value so a pathologically long
                # observation can't blow up structured-log sinks.
                logger.warning(
                    "event=coach_misconception_coerced "
                    "reason=string_to_observation "
                    "text=%r",
                    item[:120],
                )
                coerced.append(
                    {
                        "topic_name": "unspecified",
                        "misconception_text": item,
                    }
                )
                any_coerced = True
            else:
                coerced.append(item)

        if not any_coerced:
            return data

        # Shallow-copy the input so callers' dicts are not mutated under
        # them; pydantic ``mode="before"`` validators may receive a
        # caller-owned dict and an in-place mutation would surprise.
        rewritten = dict(data)
        rewritten["misconceptions"] = coerced
        return rewritten

    @model_validator(mode="after")
    def _set_reasoning_long(self) -> "CoachVerdict":
        """Compute the ``reasoning_long`` flag from the validated ``reasoning`` text.

        The flag is derived state — anything a caller sets explicitly is
        overridden. This guarantees the invariant
        ``reasoning_long iff len(reasoning.split()) > THRESHOLD`` cannot be
        spoofed by a constructor caller.
        """
        word_count = len(self.reasoning.split())
        # Pydantic v2 supports direct attribute assignment in
        # ``mode="after"`` validators; using object.__setattr__ keeps this
        # explicit (and works regardless of any future model_config that
        # might enable frozen instances).
        object.__setattr__(
            self,
            "reasoning_long",
            word_count > REASONING_LONG_WORD_THRESHOLD,
        )
        return self


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class CoachConfigurationError(ValueError):
    """Raised when a structural invariant is violated at Coach construction.

    Subclasses :class:`ValueError` so existing ``except ValueError`` callers
    catch it without code changes, while still allowing precise targeting
    via ``except CoachConfigurationError`` for tests and audit tooling.
    """


# ---------------------------------------------------------------------------
# Validator (single co-located surface — Finding F2 of TASK-REV-DTL3)
# ---------------------------------------------------------------------------


def validate_coach_config(
    *,
    player_config: PlayerConfig,
    coach_config: CoachConfig,
    system_prompt: str,
    tools: list[Any] | None,
) -> None:
    """Enforce the four construction-time Coach invariants in one place.

    Co-locating these checks matches Finding F2 of the TASK-REV-DTL3 review:
    a single validator is grep-checkable and prevents drift if a future
    invariant lands (e.g. a per-criterion weight sanity check). The four
    invariants checked here are D1 (no tools), D2 (non-empty system_prompt),
    D3 (two-provider rule); D4 (no fs_backend) is enforced structurally by
    :func:`create_coach`'s signature and asserted defensively here via
    :func:`_assert_no_fs_backend_in_signature`.

    Args:
        player_config: The Player agent's runtime config — provider field
            consulted for D3.
        coach_config: The Coach agent's runtime config — provider field
            consulted for D3.
        system_prompt: The Coach system prompt; must be a non-empty string
            with non-whitespace content (D2 / ASSUM-005).
        tools: Optional list of caller-supplied tools. ``None`` and ``[]``
            are accepted (the factory always hard-codes the actual Coach
            ``tools`` to ``[]``); any non-empty list is rejected (D1 / D5).

    Raises:
        CoachConfigurationError: If any invariant is violated. Each branch
            uses a distinct error message so the failing invariant is
            unambiguously identifiable from the exception text alone.
    """
    # D2: non-empty system prompt. Check before D1 so an "empty + tools"
    # caller error gets the most actionable message first (the prompt being
    # empty is the more fundamental misconfiguration).
    if not isinstance(system_prompt, str) or not system_prompt.strip():
        raise CoachConfigurationError(
            "Coach refused: system_prompt must be a non-empty string with "
            "non-whitespace content (per ASSUM-005). An empty system prompt "
            "would silently spin up an evaluator agent with no instructions."
        )

    # D1: no tools. ``None`` and ``[]`` are accepted; any other truthy value
    # (non-empty list/tuple/etc.) is rejected. We accept tuple/list etc. as
    # the input shape since callers might forward a normalised collection.
    if tools is not None and len(tools) > 0:
        raise CoachConfigurationError(
            f"Coach refused: tools list must be empty — the Coach is an "
            f"evaluation-only AsyncSubAgent (per D5). Got "
            f"{len(tools)} tool(s); the Coach factory does not allow "
            f"caller-supplied tools."
        )

    # D3: two-provider rule. Compare provider strings exactly; we don't try
    # to canonicalise (e.g. "openai" vs "OpenAI") — the caller is expected
    # to pass a normalised provider id and the strict comparison surfaces
    # accidental mismatches as visible D3 violations rather than silent
    # equivalences.
    if coach_config.provider == player_config.provider:
        raise CoachConfigurationError(
            f"Coach refused: Coach.provider ({coach_config.provider!r}) "
            f"must differ from Player.provider ({player_config.provider!r}) "
            f"— per the two-provider invariant (ASSUM-009), a single-"
            f"provider outage must not silently take both agents down."
        )

    # D4: defence-in-depth assertion that the factory signature has not
    # acquired a filesystem-backend parameter through a regression. The
    # primary enforcement is structural (the parameter does not exist in
    # ``create_coach``'s definition); this runtime check is the second line.
    _assert_no_fs_backend_in_signature()


def _assert_no_fs_backend_in_signature() -> None:
    """Defensive runtime check: :func:`create_coach` must expose no fs_backend.

    Inspects the public factory's signature against
    :data:`_FORBIDDEN_FACTORY_PARAMS`. A regression that adds ``fs_backend``
    (or any near-name variant) surfaces here on the first
    ``validate_coach_config`` call, in addition to being caught by the unit
    test in ``tests/unit/tutoring/coach/test_factory.py``.
    """
    # ``create_coach`` is bound by the time any validator call occurs at
    # runtime (module-level definitions complete before user code runs),
    # so this lookup is safe despite the forward textual ordering.
    sig = inspect.signature(create_coach)
    overlap = _FORBIDDEN_FACTORY_PARAMS.intersection(sig.parameters)
    if overlap:
        raise CoachConfigurationError(
            f"Coach refused: create_coach signature must not expose "
            f"filesystem-backend parameters (per D5 invariant). Found: "
            f"{sorted(overlap)}."
        )


# ---------------------------------------------------------------------------
# Coach AsyncSubAgent (thin wrapper)
# ---------------------------------------------------------------------------


class Coach:
    """Thin AsyncSubAgent-shaped Coach wrapper (per ADR-ARCH-012).

    Public surface (``tools``, ``provider``, ``system_prompt``,
    ``schedule_misconception_write``) is shape-compatible with the eventual
    ``deepagents.AsyncSubAgent`` subclass once that dependency lands in a
    downstream wave. Constructing the AsyncSubAgent boundary on day 1 avoids
    a Phase 2 migration tax (DDR-002 §Decision).

    The misconception-write site lives in :meth:`schedule_misconception_write`
    and is the **only** place this class calls into the injected write
    helper. Per CC-13 + DDR-002 the dispatch is fire-and-forget via
    ``asyncio.create_task(...)`` — no ``await`` on the helper coroutine
    inside the Coach's task surface.
    """

    def __init__(
        self,
        *,
        provider: str,
        system_prompt: str,
        write_helper: WriteHelperLike,
    ) -> None:
        """Construct a Coach with hard-coded empty tools and an injected helper.

        Args:
            provider: The Coach's LLM provider id (e.g. ``"anthropic"``).
                Stored on the instance for downstream provider-aware code
                (e.g. quota tracking, fallback routing).
            system_prompt: The Coach system prompt. Already validated by
                :func:`create_coach`/:func:`validate_coach_config` to be
                non-empty.
            write_helper: The shared misconception write helper, passed in via
                constructor injection per the TASK-DTL-001 consumer_context
                ("do not import the helper module-globally").
        """
        # D1 hard-code: tools is ALWAYS an empty list. Stored as a fresh
        # instance so external mutations (e.g. ``coach.tools.append(...)``
        # in misbehaving caller code) do not leak across Coach instances.
        # The class deliberately does not accept a ``tools`` constructor
        # parameter — there is no path for a caller to populate it.
        self.tools: list[Any] = []
        self.provider: str = provider
        self.system_prompt: str = system_prompt
        self._write_helper: WriteHelperLike = write_helper

    @property
    def write_helper(self) -> WriteHelperLike:
        """Read-only view of the injected helper (for tests and observability).

        Exposed as a property rather than a public attribute so subclasses
        and downstream tests cannot accidentally rebind the helper after
        construction. The ``_write_helper`` attribute itself remains the
        canonical storage and is what the misconception-write site reads.
        """
        return self._write_helper

    def schedule_misconception_write(
        self,
        student_id: str,
        misconception_payload: MisconceptionObservation,
    ) -> asyncio.Task[None]:
        """Dispatch an F1 misconception write fire-and-forget (CC-13 / DDR-002).

        The call uses ``asyncio.create_task(...)``; this method NEVER
        ``await``\\ s the underlying write. The Coach's evaluator budget
        is therefore independent of FalkorDB latency.

        Args:
            student_id: The student the observation was made for.
            misconception_payload: Structured observation produced by the
                Coach evaluator.

        Returns:
            The :class:`asyncio.Task` wrapping the in-flight helper call.
            Tests can ``await`` this task to assert the helper was reached;
            production code MUST NOT (the call is fire-and-forget by design).

        Raises:
            RuntimeError: If invoked outside a running event loop. The
                Coach is constructed inside the orchestrator's loop so
                this is a programmer-error condition, not a runtime
                failure mode.
        """
        # The single CC-13 / DDR-002 dispatch site. Source-grep-checked by
        # the test suite to confirm we use ``asyncio.create_task`` and not
        # a direct ``await``.
        return asyncio.create_task(
            self._write_helper.write_misconception(
                student_id, misconception_payload
            )
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_coach(
    *,
    player_config: PlayerConfig,
    coach_config: CoachConfig,
    system_prompt: str,
    write_helper: WriteHelperLike,
    tools: list[Any] | None = None,
) -> Coach:
    """Construct an evaluation-only :class:`Coach` with all D-invariants enforced.

    See module docstring for the full invariant set. This function
    deliberately DOES NOT accept any filesystem-backend / fs_backend
    parameter — that absence IS the D4/D5 invariant, asserted structurally
    via :func:`_assert_no_fs_backend_in_signature` at every validator call.

    All parameters are keyword-only so the call site reads as a
    self-documenting structural-invariant configuration. Positional
    arguments would let a caller accidentally pass a ``tools`` list into
    the ``system_prompt`` slot (etc.), which is exactly the kind of
    invariant-bypass bug this factory exists to prevent.

    Args:
        player_config: The Player agent's runtime config (provider field
            consulted for D3).
        coach_config: The Coach agent's runtime config (provider field
            consulted for D3).
        system_prompt: The Coach's system prompt. Must be non-empty
            non-whitespace text (D2 / ASSUM-005).
        write_helper: Shared misconception write helper, injected per the
            TASK-DTL-001 consumer_context. Constructor injection (rather
            than module-global import) keeps the Coach testable and
            preserves DDR-002 single-call-site isolation.
        tools: Optional caller-supplied tools list. ``None`` and ``[]``
            are accepted; any non-empty list is rejected at the call site
            (D1 / D5). Note that the constructed :class:`Coach` always
            has ``coach.tools == []`` — the parameter exists only for
            defensive validation, not for population.

    Returns:
        A fresh :class:`Coach` instance with ``tools == []``,
        ``provider == coach_config.provider``, the validated system prompt,
        and the injected write helper.

    Raises:
        CoachConfigurationError: If any of the four construction-time
            invariants (D1, D2, D3, D4) is violated.
    """
    # Validation is co-located in ``validate_coach_config`` so the four
    # checks live in exactly one place (Finding F2 of TASK-REV-DTL3).
    validate_coach_config(
        player_config=player_config,
        coach_config=coach_config,
        system_prompt=system_prompt,
        tools=tools,
    )

    # Defence in depth: the validator already raises on truthy ``tools``,
    # but the Coach constructor ALSO hard-codes ``tools=[]`` and exposes
    # no ``tools`` parameter — so a future regression that bypasses the
    # validator still cannot smuggle a tool list onto a Coach instance.
    return Coach(
        provider=coach_config.provider,
        system_prompt=system_prompt,
        write_helper=write_helper,
    )


__all__ = [
    "REASONING_LONG_WORD_THRESHOLD",
    "Coach",
    "CoachConfig",
    "CoachConfigurationError",
    "CoachVerdict",
    "CriterionScore",
    "MisconceptionObservation",
    "PlayerConfig",
    "RubricFeedback",
    "WriteHelperLike",
    "create_coach",
    "validate_coach_config",
]
