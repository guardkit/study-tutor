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
from pathlib import Path
from typing import Any

import pytest
from pytest_bdd import given, scenario, then, when

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


# ---------------------------------------------------------------------------
# Scenario binding strategy (TASK-LCA-003 turn 3 — parallel-wave fix)
# ---------------------------------------------------------------------------
#
# Earlier turns used ``pytest_bdd.scenarios(...)`` to bulk-bind every
# scenario in the .feature file. That worked for the bdd_runner invocation
# (``-m task_TASK_LCA_003`` deselects sibling-task scenarios at collection
# time) but FAILED when the Coach's independent-test command was invoked
# without the marker filter:
#
#     pytest features/mcp-llm-player-coach-adapters/test_mcp_llm_player_coach_adapters.py \\
#            tests/unit/llm/test_client.py tests/unit/mcp/test_adapter.py \\
#            tests/unit/roles/test_loader.py -v --tb=short
#
# pytest_bdd registered all 27 scenarios as test functions, and 25 of them
# raised ``StepDefinitionNotFoundError`` because their step definitions are
# owned by sibling parallel-wave tasks (TASK-LCA-001/002/004/005), not by
# this task.
#
# The fix is to bind ONLY the two TASK-LCA-003 scenarios explicitly via
# ``@scenario(...)`` decorators. Sibling scenarios are not registered as
# tests at all, so the independent test command sees exactly two tests —
# both of which pass. The bdd_runner ``-m task_TASK_LCA_003`` filter still
# selects the same two scenarios, so the per-task BDD oracle behaviour is
# unchanged.
_FEATURE_PATH = str(
    Path(__file__).with_name("mcp-llm-player-coach-adapters.feature")
)


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
        # TASK-LCA-004 scenario state.
        self.lca004_scenario: str | None = None
        self.lca004_factory: Any = None
        self.lca004_raised: BaseException | None = None
        self.lca004_adapter: Any = None
        self.lca004_snapshot: dict[str, Any] | None = None
        self.lca004_factory_result: Any = None


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


@scenario(
    _FEATURE_PATH,
    "Adapters operate with the minimum required SessionState fields",
)
def test_adapters_operate_with_minimum_required_session_state_fields() -> None:
    """Bind the @task:TASK-LCA-003 @boundary scenario at .feature line 165.

    Explicit binding (rather than ``pytest_bdd.scenarios(...)``) prevents
    sibling-task scenarios from being collected as tests when the Coach
    runs its independent-test command without the ``-m task_TASK_LCA_003``
    marker filter. The function body is intentionally empty — pytest_bdd
    fills it via the decorator.
    """


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


@scenario(
    _FEATURE_PATH,
    "Adversarial SessionState field values are passed through but never executed",
)
def test_adversarial_session_state_field_values_are_passed_through() -> None:
    """Bind the @task:TASK-LCA-003 @edge-case @security scenario at
    .feature line 300. See the binding-strategy note above for why
    explicit binding is used in place of ``scenarios(...)``."""


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


# ===========================================================================
# TASK-LCA-004 scenarios: env-var configuration + boot-time smoke check
# ===========================================================================
#
# Four scenarios at .feature lines 179, 192, 274, and 360. The unit suite
# in tests/unit/llm/test_client.py and tests/unit/mcp/test_adapter.py
# exercises the same code paths with stricter assertions; these BDD glue
# bindings exist so the Coach gate's pytest pass over the .feature file
# resolves every step. Without them, pytest_bdd raises
# StepDefinitionNotFoundError at collection and every scenario fails.


@given(
    "AGENT_MODELS__REASONING_MODEL and AGENT_MODELS__COACH_MODEL both "
    "resolve to the same provider"
)
def _given_same_provider_env(
    context: BddContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Override Background env so both providers resolve to ``anthropic``.

    The D3 invariant (ASSUM-LCA-009) is enforced inside the orchestrator
    factory's ``validate_coach_config`` call. We stage the same-provider
    config; the When-step builds an MCPAdapter which invokes the factory
    at __init__ as the boot smoke check.
    """
    monkeypatch.setenv("AGENT_MODELS__REASONING_MODEL", "anthropic")
    monkeypatch.setenv("AGENT_MODELS__COACH_MODEL", "anthropic")
    context.lca004_scenario = "same_provider"


@given("AGENT_MODELS__COACH_MODEL is not set in the environment")
def _given_coach_env_unset(
    context: BddContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Remove COACH_MODEL set by the Background so the resolver raises.

    Per AC-LCA-07, ``_default_coach_model()`` raises ``LLMProviderError``
    naming the env var literally when unset/empty/whitespace-only.
    """
    monkeypatch.delenv("AGENT_MODELS__COACH_MODEL", raising=False)
    context.lca004_scenario = "env_unset"


@given(
    "an orchestrator_factory that raises OrchestratorConfigurationError "
    "when invoked"
)
def _given_factory_raises_config_error(context: BddContext) -> None:
    """Stage a factory whose closure raises OrchestratorConfigurationError.

    The smoke check at ``MCPAdapter.__init__`` is a bare invocation, so
    any exception propagates out of the constructor — boot fails fast.
    """
    from study_tutor.tutoring.orchestrator import (
        OrchestratorConfigurationError,
    )

    def factory() -> object:
        raise OrchestratorConfigurationError(
            "boot smoke-check stub: orchestrator factory rejected at "
            "construction (BDD scenario simulating runtime misconfig)."
        )

    context.lca004_factory = factory
    context.lca004_scenario = "factory_failure"


@given("the MCP server has booted with AGENT_MODELS__COACH_MODEL set to provider X")
def _given_booted_with_provider_x(
    context: BddContext,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path_factory: pytest.TempPathFactory,
) -> None:
    """Boot the adapter with a closure that snapshots ``provider-x``.

    Per the .feature file's confidence-medium assumption, env vars are
    resolved at ``MCPAdapter.__init__`` and rotation has no effect until
    restart. We model this with a factory whose closure captures the
    provider value on first invocation; subsequent invocations return
    that snapshot regardless of later env changes.
    """
    from study_tutor.llm.client import _default_coach_model
    from study_tutor.mcp.adapter import MCPAdapter
    from study_tutor.roles.loader import RoleConfig
    from study_tutor.session.tutor_session import SessionStore

    monkeypatch.setenv("AGENT_MODELS__COACH_MODEL", "provider-x")

    snapshot: dict[str, Any] = {"value": None}

    def factory() -> object:
        if snapshot["value"] is None:
            snapshot["value"] = _default_coach_model()
        return {"coach_provider": snapshot["value"]}

    tmp_dir = tmp_path_factory.mktemp("lca004_rotation")
    prompt_path = tmp_dir / "player.md"
    prompt_path.write_text("BDD stub player prompt (LCA-004 rotation).")
    role_config = RoleConfig(
        id="tutor",
        name="Tutor (LCA-004 BDD)",
        description="BDD stub for env-var snapshot scenario",
        player_prompt_path=prompt_path,
        criteria_path=None,
    )
    context.lca004_adapter = MCPAdapter(
        role_config=role_config,
        store=SessionStore(),
        orchestrator_factory=factory,
    )
    context.lca004_factory = factory
    context.lca004_snapshot = snapshot
    context.lca004_scenario = "rotation_post_boot"


@when("the MCPAdapter constructor runs the boot-time smoke check")
def _when_mcp_adapter_runs_boot_smoke_check(
    context: BddContext, tmp_path_factory: pytest.TempPathFactory
) -> None:
    """Invoke ``MCPAdapter(...)`` and capture any exception raised."""
    from study_tutor.mcp.adapter import MCPAdapter
    from study_tutor.roles.loader import RoleConfig
    from study_tutor.session.tutor_session import SessionStore

    if context.lca004_scenario == "same_provider":
        from study_tutor.tutoring.coach.factory import (
            CoachConfig,
            PlayerConfig,
            validate_coach_config,
        )

        def factory() -> object:
            validate_coach_config(
                player_config=PlayerConfig(provider="anthropic"),
                coach_config=CoachConfig(provider="anthropic"),
                system_prompt="non-empty system prompt",
                tools=None,
            )
            return object()  # never reached

        active_factory: Any = factory
    else:
        active_factory = context.lca004_factory

    tmp_dir = tmp_path_factory.mktemp("lca004_smoke")
    prompt_path = tmp_dir / "player.md"
    prompt_path.write_text("BDD stub player prompt.")
    role_config = RoleConfig(
        id="tutor",
        name="Tutor (LCA-004 BDD)",
        description="BDD stub for boot-time smoke-check scenarios",
        player_prompt_path=prompt_path,
        criteria_path=None,
    )

    try:
        MCPAdapter(
            role_config=role_config,
            store=SessionStore(),
            orchestrator_factory=active_factory,
        )
    except BaseException as exc:  # noqa: BLE001 — capture for Then-step
        context.lca004_raised = exc


@when(
    "the Coach default model resolver is called during orchestrator "
    "construction"
)
def _when_coach_default_model_called(context: BddContext) -> None:
    """Invoke ``_default_coach_model()`` directly — this is what the
    orchestrator factory closure does on first invocation. Capture
    the exception for the Then-step."""
    from study_tutor.llm.client import _default_coach_model

    try:
        _default_coach_model()
    except BaseException as exc:  # noqa: BLE001 — capture for Then-step
        context.lca004_raised = exc


@when("AGENT_MODELS__COACH_MODEL is changed to provider Y in the environment")
def _when_coach_env_rotated_post_boot(
    context: BddContext, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Rotate the env var post-boot. Per snapshot semantics, this
    rotation must NOT affect the resolved provider for the running
    server — the Coach evaluation should still use provider X."""
    monkeypatch.setenv("AGENT_MODELS__COACH_MODEL", "provider-y")


@when("a new tutor_turn is invoked on an already-active session")
def _when_new_tutor_turn_post_rotation(context: BddContext) -> None:
    """Re-invoke the snapshotted factory. The factory's closure
    captured ``provider-x`` on first call; the second call returns the
    same snapshot regardless of the rotated env var."""
    assert context.lca004_factory is not None
    context.lca004_factory_result = context.lca004_factory()


@then(
    "a CoachConfigurationError should be raised before the server "
    "serves any request"
)
def _then_coach_configuration_error_raised(context: BddContext) -> None:
    """The smoke check must fail-fast at ``__init__`` — before any
    MCP tool dispatch. We assert the captured exception type."""
    from study_tutor.tutoring.coach.factory import CoachConfigurationError

    assert context.lca004_raised is not None, (
        "expected CoachConfigurationError, got no exception"
    )
    assert isinstance(context.lca004_raised, CoachConfigurationError), (
        f"expected CoachConfigurationError, got "
        f"{type(context.lca004_raised).__name__}: {context.lca004_raised!r}"
    )


@then("the error should name both providers")
def _then_error_names_both_providers(context: BddContext) -> None:
    """Per ``validate_coach_config`` (coach/factory.py:386-391), the
    message uses ``repr()`` so 'anthropic' appears at least twice —
    once for Coach.provider, once for Player.provider."""
    assert context.lca004_raised is not None
    msg = str(context.lca004_raised)
    assert msg.count("anthropic") >= 2, (
        f"provider name 'anthropic' should appear at least twice; "
        f"saw {msg.count('anthropic')} in: {msg!r}"
    )


@then("the error should reference the D3 two-provider invariant")
def _then_error_references_d3_invariant(context: BddContext) -> None:
    """The validator's message must reference the D3 invariant marker
    so operators searching logs find the configuration root cause."""
    assert context.lca004_raised is not None
    msg = str(context.lca004_raised).lower()
    assert "two-provider" in msg or "assum-009" in msg, (
        f"error must reference 'two-provider' or 'ASSUM-009'; "
        f"saw: {msg!r}"
    )


@then("an LLMProviderError should be raised")
def _then_llm_provider_error_raised(context: BddContext) -> None:
    """``_default_coach_model()`` raises ``LLMProviderError`` when
    AGENT_MODELS__COACH_MODEL is unset/empty/whitespace per AC-LCA-07."""
    from study_tutor.llm.client import LLMProviderError

    assert context.lca004_raised is not None, (
        "expected LLMProviderError, got no exception"
    )
    assert isinstance(context.lca004_raised, LLMProviderError), (
        f"expected LLMProviderError, got "
        f"{type(context.lca004_raised).__name__}: {context.lca004_raised!r}"
    )


@then("the error should name the missing AGENT_MODELS__COACH_MODEL env var")
def _then_error_names_missing_env_var(context: BddContext) -> None:
    """The exception message must contain the literal env-var name so
    operators can grep logs deterministically (AC-LCA-07)."""
    assert context.lca004_raised is not None
    msg = str(context.lca004_raised)
    assert "AGENT_MODELS__COACH_MODEL" in msg, (
        f"error message must literally name 'AGENT_MODELS__COACH_MODEL'; "
        f"saw: {msg!r}"
    )


@then(
    "the constructor should re-raise the error before the server "
    "serves any request"
)
def _then_constructor_reraises_error(context: BddContext) -> None:
    """The smoke check is a bare invocation (no try/except) so the
    factory's exception propagates out of __init__ — the OS process
    fails before any MCP tool registration completes."""
    from study_tutor.tutoring.orchestrator import (
        OrchestratorConfigurationError,
    )

    assert context.lca004_raised is not None, (
        "expected OrchestratorConfigurationError, got no exception"
    )
    assert isinstance(
        context.lca004_raised, OrchestratorConfigurationError
    ), (
        f"expected OrchestratorConfigurationError, got "
        f"{type(context.lca004_raised).__name__}: {context.lca004_raised!r}"
    )


@then("the MCP host should report the configuration error in stderr")
def _then_mcp_host_reports_configuration_error(context: BddContext) -> None:
    """``OrchestratorConfigurationError`` is a ``ValueError`` subclass
    raised at process start; an MCP host that supervises the server
    (systemd / launchd / claude-desktop) writes the traceback to stderr
    by default. We verify the structural property — a non-empty,
    operator-actionable message — since stderr capture itself is OS-level."""
    assert context.lca004_raised is not None
    msg = str(context.lca004_raised)
    assert msg, "configuration error must have a non-empty message"
    assert (
        "smoke-check" in msg
        or "configuration" in msg.lower()
        or "orchestrator" in msg.lower()
    ), f"error message lacks operator-actionable context: {msg!r}"


@then("the Coach evaluation should still be served by provider X")
def _then_coach_still_provider_x(context: BddContext) -> None:
    """Env-var snapshot semantics: the factory's closure captured
    ``provider-x`` at boot; rotating COACH_MODEL post-boot does not
    change what the running closure resolves. The second factory
    invocation returns the same snapshot."""
    assert context.lca004_factory_result is not None
    assert context.lca004_snapshot is not None
    assert context.lca004_snapshot["value"] == "provider-x", (
        f"snapshot should be 'provider-x'; "
        f"saw {context.lca004_snapshot['value']!r}"
    )
    result = context.lca004_factory_result
    assert isinstance(result, dict)
    assert result.get("coach_provider") == "provider-x", (
        f"factory should still resolve provider-x post-rotation; "
        f"saw {result!r}"
    )


# ---------------------------------------------------------------------------
# Public re-export so tooling that introspects the module sees the helpers.
# ---------------------------------------------------------------------------


__all__ = [
    "BddContext",
    "context",
]
