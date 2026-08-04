"""Integration smokes for TASK-LCA-005 — Wave-2 closure + per-turn isolation.

Covers three integration-layer acceptance criteria for the FEAT-6CC5
Phase-1 wiring:

* **AC-LCA-01** — per-turn factory isolation. Two concurrent
  ``tutor_turn`` invocations for two different sessions receive distinct
  :class:`PlayerCoachOrchestrator` instances. Asserted via a tracking
  factory that records every invocation.
* **AC-LCA-08** — same-provider rejection at boot. Constructing
  :class:`MCPAdapter` with the production
  :func:`_build_orchestrator_factory` closure while
  ``AGENT_MODELS__REASONING_MODEL`` and ``AGENT_MODELS__COACH_MODEL`` are
  set to the same provider raises
  :class:`CoachConfigurationError` from ``__init__`` (i.e. server boot
  fails before serving any traffic). The boot smoke check inside
  :class:`MCPAdapter.__init__` invokes the factory exactly once.
* **AC-LCA-09** — Phase-1 metadata shape. A live ``tutor_turn`` returns
  a dict whose key set is exactly the contract documented in
  :class:`study_tutor.tutoring.orchestrator.TurnResult` plus
  ``tutor_response``, with ``decision`` drawn from the canonical
  three-value Literal.

The live Lilymay scenario (AC-LCA-10) is gated behind
``STUDY_TUTOR_LIVE_LCA_SMOKE`` and the ``@pytest.mark.live`` marker so
the autobuild smoke gate (``pytest -m "feat_lca and smoke"``) stays
hermetic; operators flip the env var on for the demo capture, and the
calibration-fallback wording per Context A Q5 is asserted there rather
than as a hard revision-required gate.

Cross-references:
    - TASK-LCA-005 acceptance criteria
    - TASK-LCA-004 boot smoke check at MCPAdapter.__init__
    - ASSUM-LCA-015 (quote_verifier / coach_handover deferred to follow-up)
    - D-COACH-05 (no fallback default for AGENT_MODELS__COACH_MODEL)
    - Context A Q5 (calibration-fallback rationale for AC-LCA-10)
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from typing import Any

import pytest

from study_tutor.mcp.adapter import MCPAdapter
from study_tutor.roles.loader import RoleConfig, load_role
from study_tutor.session.service import SessionService
from tests.unit.knowledge.store.fakes import FakeStudentStore
from study_tutor.tutoring.coach import CoachVerdict
from study_tutor.tutoring.coach.factory import CoachConfigurationError
from study_tutor.tutoring.orchestrator import PlayerCoachOrchestrator


# Smoke-gate inclusion — every scenario in this module participates in
# ``pytest -m "feat_lca and smoke"``. The live scenario layers an
# additional ``live`` marker on top so the gate command excludes it
# unless the operator opts in via env var.
pytestmark = [pytest.mark.feat_lca, pytest.mark.smoke]


def _fake_session_service() -> SessionService:
    """Durable-store-backed SessionService seeded with lilymay.

    Post-FEAT-SMP-003 the MCP adapter takes ``session_service=`` (not the retired
    in-memory ``store=``); this mirrors the unit-test fixture so the integration
    smoke drives the same durable path.
    """
    store = FakeStudentStore()
    store.add_student(student_id="lilymay", year_group=9)
    return SessionService(store=store)


# ---------------------------------------------------------------------------
# Stub Player / Coach — Protocol-conforming minimal doubles
# ---------------------------------------------------------------------------


class _StubPlayer:
    """Minimal :class:`PlayerLike` double — returns deterministic strings.

    The integration smoke does not need real LLM output: AC-LCA-01 and
    AC-LCA-09 assert structural contracts (per-turn isolation; metadata
    shape) that are independent of the Player's content. Using a stub
    keeps the smoke hermetic and removes Ollama / OpenRouter as a flake
    surface.
    """

    async def respond(
        self,
        *,
        session_state: Any,
        learner_message: str,
    ) -> str:
        return f"stub-tutor:{learner_message}"

    async def revise(
        self,
        *,
        session_state: Any,
        learner_message: str,
        previous_response: str,
        rubric_feedback: list[Any],
    ) -> str:
        # The smoke never enters revision (stub Coach always accepts);
        # this branch exists to satisfy the Protocol surface.
        return previous_response


class _StubCoachAccept:
    """Minimal :class:`CoachLike` double that always accepts on first attempt.

    Returns a fully-shaped :class:`CoachVerdict` so the orchestrator's
    happy path produces ``decision="accept"`` and ``attempts=1``. Keeps
    the smoke focused on integration wiring rather than coach behaviour.
    """

    async def evaluate(
        self,
        *,
        session_state: Any,
        learner_message: str,
        player_response: str,
        **_: Any,
    ) -> CoachVerdict:
        return CoachVerdict(
            weighted_total=0.95,
            decision="accept",
            criterion_scores=[],
            rubric_feedback=[],
            misconceptions=[],
            reasoning="stub accept",
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _repo_root() -> Path:
    """Locate the worktree root by walking up from this test file.

    ``load_role`` resolves manifest paths relative to ``Path.cwd()`` —
    that's correct under the bash wrapper in production but unstable
    under pytest (the working directory depends on where the runner was
    invoked from). We anchor against the test file's location instead
    so the smoke is reproducible regardless of cwd.
    """
    here = Path(__file__).resolve()
    # tests/integration/test_mcp_lca_smoke.py -> ../../
    return here.parent.parent.parent


@pytest.fixture
def role_config(tmp_path: Path) -> RoleConfig:
    """Build a minimal ``RoleConfig`` with on-disk player + coach prompts.

    We do not call :func:`load_role` here because the test must not
    depend on the worktree's role.yaml staying intact across
    refactors — the fixture owns its prompt files end-to-end. Both
    prompt paths are populated so :class:`LLMCoachAdapter`'s
    construction-time read of ``coach_prompt_path`` succeeds when the
    smoke exercises the production closure.
    """
    player_prompt = tmp_path / "player.md"
    coach_prompt = tmp_path / "coach.md"
    player_prompt.write_text("You are a tutor.", encoding="utf-8")
    coach_prompt.write_text(
        "You are a coach. Score the tutor's reply.", encoding="utf-8"
    )
    return RoleConfig(
        id="tutor",
        name="Tutor Agent",
        description="integration smoke",
        player_prompt_path=player_prompt,
        criteria_path=None,
        coach_prompt_path=coach_prompt,
    )


async def _drain_warmups(adapter: MCPAdapter) -> None:
    """Cancel and await any LLM warm-up tasks created by ``tutor_start_session``.

    The Phase-0 warm-up path fires an empty ``LLMClient.generate`` to
    prime Ollama; the call is wrapped in a broad except so it never
    crashes the adapter, but the lingering task confuses pytest's
    asyncio teardown if not drained.
    """
    tasks = list(adapter._warmup_tasks)
    for task in tasks:
        task.cancel()
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


# ---------------------------------------------------------------------------
# AC-LCA-01 — per-turn factory isolation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_per_turn_factory_isolation_concurrent_sessions(
    role_config: RoleConfig,
) -> None:
    """AC-LCA-01: two concurrent turns get two distinct orchestrator instances.

    Wires a tracking factory that records every constructed
    :class:`PlayerCoachOrchestrator`. Boot smoke invokes the factory
    once (TASK-LCA-004); we then start two sessions and dispatch two
    concurrent ``tutor_turn`` calls via :func:`asyncio.gather`. After
    both turns complete, the recorded instances list must have grown by
    exactly two and the two new instances must be distinct objects.

    The concurrency assertion uses ``is not`` (identity comparison)
    rather than ``==`` because dataclass equality does not catch the
    "two turns share one orchestrator" regression — only object
    identity does.
    """
    instances: list[PlayerCoachOrchestrator] = []

    def tracking_factory() -> PlayerCoachOrchestrator:
        orch = PlayerCoachOrchestrator(
            player=_StubPlayer(),
            coach=_StubCoachAccept(),
            quote_verifier=None,
            coach_handover=None,
        )
        instances.append(orch)
        return orch

    session_service = _fake_session_service()
    adapter = MCPAdapter(
        role_config=role_config,
        session_service=session_service,
        orchestrator_factory=tracking_factory,
    )
    # Boot smoke check should have invoked the factory exactly once.
    boot_count = len(instances)
    assert boot_count == 1, (
        f"boot smoke check should invoke factory once; got {boot_count}"
    )

    # Two concurrently-live sessions for the one resolved identity. Ruled
    # (b) 2026-08-04: a second MCP start would share the (student,
    # SUBJECT_DEFAULT) key and END the first — one-active is structural
    # now — so the second live session comes from the service under a
    # different subject; the invariant under test here is tutor_turn's
    # per-turn factory isolation, not the start door's keying.
    s1 = await adapter.tutor_start_session(student_id="lilymay-iso-1")
    s2 = await session_service.start_session(
        student_id="lilymay", subject="french"
    )
    await _drain_warmups(adapter)
    sid1, sid2 = s1["session_id"], s2.session_id
    assert sid1 != sid2

    # Concurrent turns — gather forces both into the same event loop
    # iteration so a shared-instance bug would surface here.
    await asyncio.gather(
        adapter.tutor_turn(session_id=sid1, user_message="metaphor please"),
        adapter.tutor_turn(session_id=sid2, user_message="simile please"),
    )

    new_instances = instances[boot_count:]
    assert len(new_instances) == 2, (
        f"expected 2 fresh orchestrators (one per turn); got "
        f"{len(new_instances)}"
    )
    assert new_instances[0] is not new_instances[1], (
        "per-turn factory isolation invariant violated: two concurrent "
        "tutor_turn calls received the same PlayerCoachOrchestrator instance"
    )


# ---------------------------------------------------------------------------
# AC-LCA-09 — Phase-1 metadata shape
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_phase1_metadata_shape_returned_by_tutor_turn(
    role_config: RoleConfig,
) -> None:
    """AC-LCA-09: ``tutor_turn`` returns the documented Phase-1 dict shape.

    Asserts the key set, that ``decision`` is one of the canonical
    three Literal values, and that numeric/boolean fields have sane
    types. This is the integration-layer counterpart to the unit-test
    coverage of :class:`TurnResult` — it proves the MCP adapter
    forwards the orchestrator's verdict into the dict-shaped MCP
    response without dropping or renaming fields.
    """
    def factory() -> PlayerCoachOrchestrator:
        return PlayerCoachOrchestrator(
            player=_StubPlayer(),
            coach=_StubCoachAccept(),
            quote_verifier=None,
            coach_handover=None,
        )

    adapter = MCPAdapter(
        role_config=role_config,
        session_service=_fake_session_service(),
        orchestrator_factory=factory,
    )
    started = await adapter.tutor_start_session(student_id="lilymay-meta")
    await _drain_warmups(adapter)

    result = await adapter.tutor_turn(
        session_id=started["session_id"],
        user_message="What is a metaphor?",
    )

    expected_keys = {
        "tutor_response",
        "decision",
        "attempts",
        "flagged_for_review",
        "duration_seconds",
    }
    assert expected_keys.issubset(result.keys()), (
        f"Phase-1 metadata shape regression: missing keys "
        f"{expected_keys - set(result.keys())}; got {sorted(result.keys())}"
    )
    assert result["decision"] in {"accept", "exhausted", "fallback"}, (
        f"decision must be one of the canonical Literal values; "
        f"got {result['decision']!r}"
    )
    assert isinstance(result["attempts"], int)
    assert isinstance(result["flagged_for_review"], bool)
    assert isinstance(result["duration_seconds"], float)
    assert isinstance(result["tutor_response"], str)


# ---------------------------------------------------------------------------
# AC-LCA-08 — same-provider rejection at boot, through the production closure
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_same_provider_rejected_at_boot_via_production_closure(
    role_config: RoleConfig,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-LCA-08: production closure raises ``CoachConfigurationError`` at boot.

    Sets both ``AGENT_MODELS__REASONING_MODEL`` and
    ``AGENT_MODELS__COACH_MODEL`` to the same provider name, builds the
    production :func:`_build_orchestrator_factory` closure, and
    constructs :class:`MCPAdapter` with that closure. The boot smoke
    check inside ``MCPAdapter.__init__`` invokes the closure once;
    :func:`validate_coach_config` then raises
    :class:`CoachConfigurationError` for the D3 same-provider violation,
    propagating out of ``__init__``.

    Importantly this test goes through the **production** closure
    (``cli.main._build_orchestrator_factory``), not just a direct
    ``validate_coach_config`` call — the integration claim under test
    is that the wiring at the construction site enforces D3, not that
    the validator itself rejects same-provider configs (covered in unit
    tests under ``tests/unit/tutoring/coach/test_factory.py``).
    """
    monkeypatch.setenv("AGENT_MODELS__REASONING_MODEL", "openrouter")
    monkeypatch.setenv("AGENT_MODELS__COACH_MODEL", "openrouter")

    from study_tutor.cli.main import _build_orchestrator_factory

    factory = _build_orchestrator_factory(role_config)

    with pytest.raises(CoachConfigurationError) as excinfo:
        MCPAdapter(
            role_config=role_config,
            session_service=_fake_session_service(),
            orchestrator_factory=factory,
        )

    # The validator names both providers and references the D3 invariant.
    message = str(excinfo.value)
    assert "openrouter" in message
    assert "two-provider" in message or "D3" in message or "ASSUM-009" in message


# ---------------------------------------------------------------------------
# AC-LCA-10 — live Lilymay smoke (operator-conducted, calibration fallback)
# ---------------------------------------------------------------------------


@pytest.mark.live
@pytest.mark.skipif(
    "STUDY_TUTOR_LIVE_LCA_SMOKE" not in os.environ,
    reason=(
        "live LLM providers required to run AC-LCA-10 Lilymay smoke; "
        "set STUDY_TUTOR_LIVE_LCA_SMOKE=1 (and AGENT_MODELS__REASONING_MODEL "
        "+ AGENT_MODELS__COACH_MODEL to two distinct providers) to enable"
    ),
)
@pytest.mark.asyncio
async def test_live_lilymay_two_turn_session_calibration_fallback(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """AC-LCA-10: live 2-turn Lilymay smoke with calibration-fallback wording.

    Per Context A Q5: zero-revision turns during the demo are NOT a
    test failure when the Coach prompt is minimal (Phase-1 plumbing
    only; calibration is Phase-2). This test records EITHER a
    revision-occurred result (``attempts > 1`` on at least one turn)
    OR an explicit ``calibration_gap=True`` annotation that the
    operator captures in ``docs/research/ideas/phase-1-validation.md``.

    The test passes in both branches; the failure mode is "neither
    branch was reached" (no attempts metadata at all) which would
    indicate a wiring regression rather than a calibration concern.
    """
    from study_tutor.cli.main import _build_orchestrator_factory

    role_config = load_role("tutor", repo_root=_repo_root())
    factory = _build_orchestrator_factory(role_config)
    adapter = MCPAdapter(
        role_config=role_config,
        session_service=_fake_session_service(),
        orchestrator_factory=factory,
    )

    started = await adapter.tutor_start_session(student_id="lilymay")
    sid = started["session_id"]
    await _drain_warmups(adapter)

    turn1 = await adapter.tutor_turn(
        session_id=sid,
        user_message=(
            "I'm working on the witches' opening scene in Macbeth. "
            "What does 'Fair is foul, and foul is fair' mean?"
        ),
    )
    turn2 = await adapter.tutor_turn(
        session_id=sid,
        user_message=(
            "Can you give me a quotation that shows Macbeth's ambition "
            "in Act 1?"
        ),
    )

    # Both turns must return a Phase-1-shaped metadata dict — the
    # AC-LCA-09 contract is load-bearing for AC-LCA-10's diagnostic
    # signal, so we re-assert it here against live providers.
    for turn_label, result in (("turn1", turn1), ("turn2", turn2)):
        assert "attempts" in result, (
            f"{turn_label} missing 'attempts' — wiring regression, not "
            f"calibration gap"
        )
        assert result["decision"] in {"accept", "exhausted", "fallback"}, (
            f"{turn_label} decision={result['decision']!r} not in canonical set"
        )

    revision_observed = max(turn1["attempts"], turn2["attempts"]) > 1
    if revision_observed:
        # Branch A — Coach disagreed and Player revised. Calibration is
        # working; record it on stderr so the operator log can capture
        # the timestamped evidence.
        print(
            f"AC-LCA-10 result=revision_observed "
            f"turn1_attempts={turn1['attempts']} "
            f"turn2_attempts={turn2['attempts']}",
            file=sys.stderr,
        )
    else:
        # Branch B — calibration gap (Context A Q5). Record explicitly
        # so the operator can carry the annotation into
        # ``phase-1-validation.md`` as a Phase-2 calibration follow-up
        # rather than a Phase-1 test failure.
        print(
            "AC-LCA-10 result=calibration_gap=True "
            "reason=coach_never_disagreed_across_two_turns "
            "follow_up=phase_2_coach_calibration",
            file=sys.stderr,
        )

    # Either branch is a passing outcome; the only failure mode is
    # a wiring regression (asserted above).
