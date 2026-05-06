"""pytest-bdd glue module for ``mcp-llm-player-coach-adapters.feature``.

Companion glue for the BDD oracle. The conftest at ``features/conftest.py``
redirects ``.feature`` argv to this sibling module so
:func:`pytest_bdd.scenarios` can bind the scenarios. Without this glue
``bdd_runner`` exits 4 ("not found") and the Coach gate reports a BDD
oracle failure — which is exactly the failure surfaced on Turn 1 of
TASK-LCA-003.

Step-definition discipline (mirrors the pattern set by
``features/deepagents-tutoring-loop/test_deepagents_tutoring_loop.py``):

* Background steps are implemented unconditionally — they run for every
  scenario in the file regardless of which ``@task:TASK-LCA-XXX`` tag
  the scenario carries.

* Scenario steps for ``@task:TASK-LCA-003`` (the two SessionState
  scenarios at .feature lines 165–169 and 300–305) are fully
  implemented here — they are this module's primary deliverable.

* Steps unique to sibling tasks (``@task:TASK-LCA-001`` /
  ``@task:TASK-LCA-002`` / ``@task:TASK-LCA-004`` / ``@task:TASK-LCA-005``)
  are intentionally NOT bound here. The bdd_runner invocation for
  TASK-LCA-003 uses ``-m task_TASK_LCA_003`` which deselects every
  other scenario at collection time, so unbound steps for those
  scenarios are never resolved at test-run time and the BDD oracle
  passes (``scenarios_failed == 0``).

The scenarios verify two contracts the unit suite cannot exercise
directly:

1. **Boundary**: a :class:`SessionState` constructed with only the
   two required fields (``session_id``, ``student_id``) reaches both
   the Player adapter's ``respond`` surface and the Coach adapter's
   ``evaluate`` surface without raising. ASSUM-LCA-007 says the
   optional fields default to ``None`` / ``()`` / ``"tutor"`` so the
   minimum-state path is the operational contract for baseline-
   degraded plans (no ``text_name`` / no ``focus_aos``).

2. **Security**: adversarial values placed in :class:`SessionState`
   fields (``text_name="../../../etc/passwd"``, control chars in
   ``topic``) are passed through unchanged to the Player and Coach
   adapters and are never used to drive filesystem access. The
   adapters treat these fields as opaque strings — the @security
   invariant the @edge-case @security scenario locks down.
"""
from __future__ import annotations

import builtins
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, scenarios, then, when

from study_tutor.tutoring.adapters.session_state import SessionState
from study_tutor.tutoring.coach import (
    CoachVerdict,
    CriterionScore,
)
from study_tutor.tutoring.orchestrator import (
    CoachLike,
    PlayerCoachOrchestrator,
    PlayerLike,
    TurnResult,
)


# Bind every scenario in the sibling .feature file. The bdd_runner's
# ``-m task_TASK_LCA_003`` filter selects only the per-task subset; un-bound
# steps in unrelated scenarios surface as deselected (never executed).
scenarios(str(Path(__file__).with_name("mcp-llm-player-coach-adapters.feature")))


# ---------------------------------------------------------------------------
# Per-scenario shared state
# ---------------------------------------------------------------------------


class _RecordingPlayer:
    """Minimal :class:`PlayerLike`-shaped stub.

    Records every ``session_state`` it sees so Then-steps can assert that
    the orchestrator forwarded the SessionState unchanged. Returns a
    fixed canned response so the orchestrator's accept/revise branch is
    deterministic.
    """

    def __init__(self) -> None:
        self.respond_calls: list[dict[str, Any]] = []
        self.revise_calls: list[dict[str, Any]] = []
        self.respond_raised: BaseException | None = None
        self.revise_raised: BaseException | None = None

    async def respond(
        self, *, session_state: Any, learner_message: str
    ) -> str:
        try:
            self.respond_calls.append(
                {
                    "session_state": session_state,
                    "learner_message": learner_message,
                }
            )
            return "stub-player-response"
        except BaseException as exc:  # pragma: no cover - defensive only
            self.respond_raised = exc
            raise

    async def revise(
        self,
        *,
        session_state: Any,
        learner_message: str,
        previous_response: str,
        rubric_feedback: list[Any],
    ) -> str:
        # Not exercised by the LCA-003 scenarios (verdict.decision="accept"
        # short-circuits the loop), but implementing it satisfies the
        # PlayerLike Protocol so the orchestrator's runtime_checkable
        # isinstance guard passes if/when Phase-2 wiring exercises revise.
        self.revise_calls.append(
            {
                "session_state": session_state,
                "learner_message": learner_message,
                "previous_response": previous_response,
                "rubric_feedback": list(rubric_feedback),
            }
        )
        return "stub-player-revision"


class _RecordingCoach:
    """Minimal :class:`CoachLike`-shaped stub.

    Records every ``session_state`` and returns an ``accept`` verdict so
    the orchestrator exits the loop on the first attempt — the LCA-003
    scenarios assert call-shape, not revision-loop behaviour.
    """

    def __init__(self) -> None:
        self.evaluate_calls: list[dict[str, Any]] = []
        self.evaluate_raised: BaseException | None = None

    async def evaluate(
        self, *, session_state: Any, learner_message: str, player_response: str
    ) -> CoachVerdict:
        try:
            self.evaluate_calls.append(
                {
                    "session_state": session_state,
                    "learner_message": learner_message,
                    "player_response": player_response,
                }
            )
            # Single-criterion accept verdict — the smallest valid shape that
            # satisfies CoachVerdict's pydantic constraints (weighted_total in
            # [0,1], decision in {accept, revise}). decision="accept" guarantees
            # the orchestrator returns after one attempt with no revise() call.
            return CoachVerdict(
                weighted_total=0.95,
                decision="accept",
                criterion_scores=[
                    CriterionScore(
                        criterion_id="bdd_stub", score=0.95, evidence="stub"
                    )
                ],
                rubric_feedback=[],
                misconceptions=[],
                reasoning="bdd-stub coach verdict",
            )
        except BaseException as exc:  # pragma: no cover - defensive only
            self.evaluate_raised = exc
            raise


class BddContext:
    """Mutable container threaded through Given/When/Then via fixture."""

    def __init__(self) -> None:
        self.session_state: SessionState | None = None
        self.player: _RecordingPlayer | None = None
        self.coach: _RecordingCoach | None = None
        self.orchestrator: PlayerCoachOrchestrator | None = None
        self.turn_result: TurnResult | None = None
        self.player_respond_raised: BaseException | None = None
        self.coach_evaluate_raised: BaseException | None = None
        # Adversarial-scenario observability hooks.
        self.open_calls: list[tuple[Any, ...]] = []
        self.original_open: Any = None


@pytest.fixture
def context() -> BddContext:
    return BddContext()


def _build_orchestrator(ctx: BddContext) -> None:
    """Assemble the orchestrator + recording adapters lazily.

    Lazy assembly keeps Given-step ordering flexible: scenarios may
    populate ``ctx.session_state`` either before or after the
    "orchestrator runs a turn" When-step is reached.
    """
    if ctx.player is None:
        ctx.player = _RecordingPlayer()
    if ctx.coach is None:
        ctx.coach = _RecordingCoach()
    if ctx.orchestrator is None:
        # Confirm the structural protocols are satisfied — runtime_checkable
        # isinstance probes the method shape, which is the structural
        # invariant the orchestrator depends on.
        assert isinstance(ctx.player, PlayerLike)
        assert isinstance(ctx.coach, CoachLike)
        ctx.orchestrator = PlayerCoachOrchestrator(
            player=ctx.player,
            coach=ctx.coach,
        )


# ===========================================================================
# Background steps (apply to every scenario)
# ===========================================================================


@given(
    "the tutoring orchestrator surfaces (PlayerLike, CoachLike, "
    "PlayerCoachOrchestrator, validate_coach_config, parse_coach_output) "
    "are unchanged from Phase-0"
)
def _bg_orchestrator_surfaces_unchanged() -> None:
    """Phase-0 surface contract — verified by import.

    Importing these names succeeds iff the modules expose them; an
    accidental rename would surface here as ImportError before any
    scenario runs. The Phase-0 path (no ``orchestrator_factory`` wired)
    is the live runtime today, and these surfaces remain stable for
    Phase-1 (TASK-LCA-001/002/003) consumption.
    """
    from study_tutor.tutoring.coach import parse_coach_output, validate_coach_config

    # Reference-evaluate so static analysers don't strip the import.
    assert callable(parse_coach_output)
    assert callable(validate_coach_config)
    assert PlayerLike is not None
    assert CoachLike is not None
    assert PlayerCoachOrchestrator is not None


@given(
    "the AGENT_MODELS__REASONING_MODEL env var configures the Player provider"
)
def _bg_reasoning_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set a deterministic Player provider env value for the duration of
    the scenario. The LCA-003 scenarios don't exercise an LLM call —
    the recording stubs short-circuit before any provider lookup — so
    a non-empty placeholder is sufficient to satisfy the Background
    contract."""
    monkeypatch.setenv("AGENT_MODELS__REASONING_MODEL", "openai:gpt-4-bdd-stub")


@given(
    "the AGENT_MODELS__COACH_MODEL env var configures the Coach provider"
)
def _bg_coach_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set a deterministic Coach provider env value distinct from the
    Player provider. The two-provider invariant (D3) is asserted by
    TASK-LCA-004's scenarios; this Background step only ensures the
    env shape is present so the scenario set-up assumption holds."""
    monkeypatch.setenv("AGENT_MODELS__COACH_MODEL", "anthropic:claude-bdd-stub")


@given("the LLMCoachAdapter parses LLM output via parse_coach_output")
def _bg_parse_coach_output_available() -> None:
    """parse_coach_output is the deterministic post-processor the
    LLMCoachAdapter (TASK-LCA-002) consumes. We verify the function is
    importable from the canonical site so the Background assumption
    holds; the LCA-003 scenarios use recording stubs and do not invoke
    parse_coach_output directly."""
    from study_tutor.tutoring.coach import parse_coach_output

    assert callable(parse_coach_output)


# ===========================================================================
# TASK-LCA-003 scenario: minimum-required SessionState fields (.feature 165)
# ===========================================================================


@given("a SessionState populated only with session_id and student_id")
def _given_minimal_session_state(context: BddContext) -> None:
    """Build the smallest valid SessionState (ASSUM-LCA-007).

    Constructing with only the two required fields exercises the
    optional-field defaults (``text_name=None``, ``topic=None``,
    ``focus_aos=()``, ``mode="tutor"``). If any field were not
    optional, this construction would raise TypeError — the boundary
    contract requires it not to.
    """
    context.session_state = SessionState(
        session_id="sess-bdd-lca003-min",
        student_id="lilymay",
    )
    # Defence-in-depth: assert the defaults the adapters rely on are
    # what the AC documents (ASSUM-LCA-007).
    assert context.session_state.text_name is None
    assert context.session_state.topic is None
    assert context.session_state.focus_aos == ()
    assert context.session_state.mode == "tutor"


@when("the orchestrator runs a turn against this SessionState")
def _when_orchestrator_runs_turn(context: BddContext) -> None:
    """Run a single Player→Coach round trip with the recording stubs.

    We record any exception raised by the Player or Coach surface
    without re-raising so the Then-steps can assert "without raising"
    against captured state rather than relying on pytest's exception
    bubbling (the second scenario uses the same When-step but checks
    different post-conditions on the recorded adapter calls).
    """
    _build_orchestrator(context)
    assert context.session_state is not None
    assert context.orchestrator is not None
    import asyncio

    try:
        context.turn_result = asyncio.run(
            context.orchestrator.run_turn(
                session_state=context.session_state,
                learner_message="Tell me about Act 1.",
            )
        )
    except BaseException as exc:  # noqa: BLE001 — capture for Then-step
        # The Then-step "without raising" reads from
        # ``player_respond_raised`` / ``coach_evaluate_raised`` rather
        # than letting the exception propagate, so capture the failure
        # mode here for the assertion to inspect.
        context.player_respond_raised = exc
        context.coach_evaluate_raised = exc


@then("the Player adapter should respond without raising")
def _then_player_responded_without_raising(context: BddContext) -> None:
    """Player.respond was invoked exactly once with the SessionState
    threaded through unchanged, and did not raise."""
    assert context.player is not None
    assert context.player_respond_raised is None, (
        f"Player.respond raised: {context.player_respond_raised!r}"
    )
    assert len(context.player.respond_calls) == 1
    forwarded_state = context.player.respond_calls[0]["session_state"]
    assert isinstance(forwarded_state, SessionState)
    assert forwarded_state is context.session_state


@then("the Coach adapter should evaluate without raising")
def _then_coach_evaluated_without_raising(context: BddContext) -> None:
    """Coach.evaluate was invoked exactly once with the SessionState
    threaded through unchanged, and did not raise."""
    assert context.coach is not None
    assert context.coach_evaluate_raised is None, (
        f"Coach.evaluate raised: {context.coach_evaluate_raised!r}"
    )
    assert len(context.coach.evaluate_calls) == 1
    forwarded_state = context.coach.evaluate_calls[0]["session_state"]
    assert isinstance(forwarded_state, SessionState)
    assert forwarded_state is context.session_state
    # The orchestrator should have terminated with an accept verdict.
    assert context.turn_result is not None
    assert context.turn_result.decision == "accept"


# ===========================================================================
# TASK-LCA-003 scenario: adversarial SessionState values (.feature 300)
# ===========================================================================


_ADVERSARIAL_TEXT_NAME = "../../../etc/passwd"
# Control characters: NUL, SOH, BEL, vertical tab, form feed.
_ADVERSARIAL_TOPIC = "topic\x00\x01\x07\x0b\x0c-with-control-chars"


@given(
    'a SessionState whose text_name field contains "../../../etc/passwd" '
    "and whose topic field contains control characters"
)
def _given_adversarial_session_state(
    context: BddContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Construct a SessionState carrying values that would be malicious if
    interpreted as a path or unsanitised string. We also wrap
    :func:`builtins.open` so the scenario can prove the adapters never
    perform filesystem I/O during the turn (the @security invariant)."""
    context.session_state = SessionState(
        session_id="sess-bdd-lca003-adv",
        student_id="lilymay",
        text_name=_ADVERSARIAL_TEXT_NAME,
        topic=_ADVERSARIAL_TOPIC,
        focus_aos=("AO1",),
        mode="tutor",
    )

    # Spy on builtins.open. Calling-through preserves any legitimate
    # framework I/O (pytest-bdd's own bookkeeping); the Then-step asserts
    # that no recorded call carried the adversarial path.
    real_open = builtins.open

    def _spy_open(*args: Any, **kwargs: Any) -> Any:
        context.open_calls.append((args, kwargs))
        return real_open(*args, **kwargs)

    context.original_open = real_open
    monkeypatch.setattr(builtins, "open", _spy_open)


@then(
    "the Player and Coach adapters should receive the SessionState unchanged"
)
def _then_adapters_received_session_state_unchanged(
    context: BddContext,
) -> None:
    """Both adapters must see the same SessionState instance (or an
    equal one) with text_name and topic preserved verbatim — no
    sanitisation, no path-resolution, no transformation."""
    assert context.player is not None
    assert context.coach is not None
    assert len(context.player.respond_calls) == 1
    assert len(context.coach.evaluate_calls) == 1

    player_state = context.player.respond_calls[0]["session_state"]
    coach_state = context.coach.evaluate_calls[0]["session_state"]

    for name, state in (("player", player_state), ("coach", coach_state)):
        assert isinstance(state, SessionState), name
        assert state.text_name == _ADVERSARIAL_TEXT_NAME, name
        assert state.topic == _ADVERSARIAL_TOPIC, name
        assert state.session_id == "sess-bdd-lca003-adv", name
        assert state.student_id == "lilymay", name

    # SessionState is frozen; replacing fields produces a new instance.
    # Verify the orchestrator did not silently rebuild a sanitised copy
    # by comparing the player and coach states for structural equality.
    assert player_state == coach_state
    # And confirm equality with the originally-constructed state.
    assert player_state == context.session_state


@then("no filesystem access should be attempted from the adapters")
def _then_no_filesystem_access(context: BddContext) -> None:
    """Assert builtins.open was never called with the adversarial
    text_name. This is a defence-in-depth check — the recording stubs
    obviously don't open files, but the assertion locks down the
    invariant that future production adapters (TASK-LCA-001 /
    TASK-LCA-002) MUST NOT use SessionState fields as paths."""
    for args, _ in context.open_calls:
        path_arg = str(args[0]) if args else ""
        assert _ADVERSARIAL_TEXT_NAME not in path_arg, (
            f"adapter attempted filesystem access with adversarial "
            f"text_name; saw open({args!r})"
        )
        # Defence-in-depth: also ensure no /etc/passwd resolution leaked.
        assert "/etc/passwd" not in path_arg, (
            f"adapter resolved adversarial text_name to a real path: "
            f"open({args!r})"
        )


@then(
    "the LLM call assembly should treat these fields as opaque strings"
)
def _then_fields_are_opaque_strings(context: BddContext) -> None:
    """Verify the adversarial values are still raw strings on the
    forwarded SessionState — not Path objects, not split, not
    interpolated into any structured payload by the orchestrator."""
    assert context.player is not None
    assert context.coach is not None
    forwarded_state = context.player.respond_calls[0]["session_state"]
    # type() check rather than isinstance(...) so a Path subclass would
    # also fail (Path is not a str — but a defensive check belts and
    # braces against accidental coercion in future code).
    assert type(forwarded_state.text_name) is str  # noqa: E721
    assert type(forwarded_state.topic) is str  # noqa: E721
    # Length-preservation: control characters survived round-trip
    # without trimming/replacement.
    assert len(forwarded_state.text_name) == len(_ADVERSARIAL_TEXT_NAME)
    assert len(forwarded_state.topic) == len(_ADVERSARIAL_TOPIC)
    # No splitting on the path separator happened anywhere.
    assert "/" in forwarded_state.text_name


# ---------------------------------------------------------------------------
# Public re-export so tooling that introspects the module sees the helpers.
# ---------------------------------------------------------------------------


__all__ = [
    "BddContext",
    "context",
]
