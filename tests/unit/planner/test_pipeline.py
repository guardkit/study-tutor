"""Unit tests for :mod:`study_tutor.planner.pipeline`.

Covers the TASK-DSP-005 acceptance criteria for the rule-pipeline
dispatcher and the rule-6 / baseline fallback chain. Each test maps
back to a single AC in the task file so a coverage audit can trace
test → criterion in one hop.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Mapping

import pytest

from study_tutor.knowledge.queries import StudentState, TopicConfidenceSnapshot
from study_tutor.knowledge.student_model import (
    Misconception,
    TopicConfidence,
)
from study_tutor.planner.pipeline import (
    _build_planner_context,
    _build_opening_prompt,
    plan_session,
    run_rule_pipeline,
)
from study_tutor.planner.protocols import PlannerContext
from study_tutor.planner.types import SessionPlan


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


_FROZEN_NOW = datetime(2026, 4, 29, 12, 0, 0, tzinfo=timezone.utc)


def _frozen_clock(when: datetime = _FROZEN_NOW):
    """Return a zero-arg callable that always reports ``when``."""

    def _clock() -> datetime:
        return when

    return _clock


def _topic(
    name: str,
    *,
    percentage: int = 50,
    band: str = "developing",
    last_revised_at: datetime | None = None,
) -> TopicConfidence:
    return TopicConfidence(
        student_ref="student-1",
        topic_ref=name,
        percentage=percentage,
        band=band,  # type: ignore[arg-type]
        last_revised_at=last_revised_at
        or _FROZEN_NOW - timedelta(hours=72),
    )


def _misc(topic: str, *, observed_at: datetime | None = None) -> Misconception:
    return Misconception(
        text="confused two terms",
        topic_ref=topic,
        observed_at=observed_at or _FROZEN_NOW - timedelta(days=2),
        confidence_band_at_observation="developing",
    )


def _build_context(
    *,
    topic_confidences: list[TopicConfidence] | None = None,
    misconceptions: list[Misconception] | None = None,
    ao_mapping: Mapping[str, list[str]] | None = None,
    topic_override: str | None = None,
    rng: random.Random | None = None,
    clock_at: datetime | None = None,
) -> PlannerContext:
    return PlannerContext.create(
        student_id="student-1",
        topic_confidences=topic_confidences or [],
        misconceptions=misconceptions or [],
        ao_mapping=ao_mapping or {},
        topic_override=topic_override,
        clock=_frozen_clock(clock_at or _FROZEN_NOW),
        rng=rng or random.Random(42),
    )


# ---------------------------------------------------------------------------
# AC-001 — non-empty override → rule-1
# ---------------------------------------------------------------------------


class TestRule1Selection:
    """`@key-example @rule-1` — override short-circuits ranking."""

    def test_non_empty_override_selects_rule_1(self) -> None:
        ctx = _build_context(
            topic_override="Macbeth's ambition",
            topic_confidences=[
                _topic("metaphor", percentage=20, band="struggling"),
            ],
        )

        plan = run_rule_pipeline(ctx)

        assert plan.rule_selected == "rule-1"
        assert plan.fallback_used is None
        assert plan.topic_name == "Macbeth's ambition"


# ---------------------------------------------------------------------------
# AC-002 — struggling stale topic → rule-3
# ---------------------------------------------------------------------------


class TestRule3Selection:
    """`@key-example @rule-3` — weakest stale topic with no override."""

    def test_struggling_stale_topic_selects_rule_3(self) -> None:
        # Two struggling-band topics, both well outside cooldown. Rule 3
        # should pick the weaker one ('weak-stale') because percentage
        # ranks ascending.
        ctx = _build_context(
            topic_confidences=[
                _topic(
                    "weak-stale",
                    percentage=15,
                    band="struggling",
                    last_revised_at=_FROZEN_NOW - timedelta(days=10),
                ),
                _topic(
                    "less-weak-stale",
                    percentage=30,
                    band="struggling",
                    last_revised_at=_FROZEN_NOW - timedelta(days=10),
                ),
            ],
        )

        plan = run_rule_pipeline(ctx)

        assert plan.rule_selected == "rule-3"
        assert plan.fallback_used is None
        assert plan.topic_name == "weak-stale"


# ---------------------------------------------------------------------------
# AC-003 — equally-weak topics with one unrevisited misconception → rule-4
# ---------------------------------------------------------------------------


class TestRule4Selection:
    """`@key-example @rule-4` — unrevisited misconception preferred."""

    def test_unrevisited_misconception_selects_rule_4(self) -> None:
        # Two equally-weak topics. Both eligible for rule 3 (stale), but
        # 'topic-A' has an unrevisited misconception so rule 4 fires
        # first because it precedes rule 3 only in the priority list...
        #
        # Wait — the actual priority order is rule-1, rule-2, rule-3,
        # rule-4. So rule-3 fires before rule-4. To prove rule-4 is
        # selected we need rule-3 to return None, which requires the
        # stale topics to be inside the cooldown window. Set
        # last_revised_at to 1h ago (inside the 48h cooldown). Then
        # rule-3 returns None and rule-4 picks the topic with the
        # unrevisited misconception.
        ctx = _build_context(
            topic_confidences=[
                _topic(
                    "topic-A",
                    percentage=45,
                    band="developing",
                    last_revised_at=_FROZEN_NOW - timedelta(hours=1),
                ),
                _topic(
                    "topic-B",
                    percentage=45,
                    band="developing",
                    last_revised_at=_FROZEN_NOW - timedelta(hours=1),
                ),
            ],
            misconceptions=[
                _misc("topic-A"),
            ],
        )

        plan = run_rule_pipeline(ctx)

        assert plan.rule_selected == "rule-4"
        assert plan.fallback_used is None
        assert plan.topic_name == "topic-A"
        assert len(plan.related_misconceptions) == 1


# ---------------------------------------------------------------------------
# AC-004 — rules 1/3/4 None + non-empty developing band → rule-6
# ---------------------------------------------------------------------------


class TestRule6Fallback:
    """`@boundary @rule-6 @fallback` — random pick from developing."""

    def test_rule_6_fires_when_primaries_return_none(self) -> None:
        # Developing-band topics, both within cooldown (rule-3 None),
        # no misconceptions (rule-4 None), no override (rule-1 None).
        ctx = _build_context(
            topic_confidences=[
                _topic(
                    "alpha",
                    percentage=50,
                    band="developing",
                    last_revised_at=_FROZEN_NOW - timedelta(hours=1),
                ),
                _topic(
                    "beta",
                    percentage=50,
                    band="developing",
                    last_revised_at=_FROZEN_NOW - timedelta(hours=1),
                ),
            ],
            rng=random.Random(42),
        )

        plan = run_rule_pipeline(ctx)

        assert plan.rule_selected == "rule-6"
        assert plan.fallback_used == "rule-6"
        assert plan.topic_name in {"alpha", "beta"}


# ---------------------------------------------------------------------------
# AC-005 — gap test: rules 1/3/4 None AND developing band empty → baseline
# ---------------------------------------------------------------------------


class TestBaselineFallback:
    """TASK-REV-DA72 §5 Gap 1 — pipeline never raises on empty bands."""

    def test_baseline_when_developing_band_empty(self) -> None:
        # Only struggling/secure topics, all within cooldown (rule-3
        # None), no misconceptions (rule-4 None), no override (rule-1
        # None), no developing-band topics (rule-6 None).
        ctx = _build_context(
            topic_confidences=[
                _topic(
                    "secured",
                    percentage=85,
                    band="secure",
                    last_revised_at=_FROZEN_NOW - timedelta(hours=1),
                ),
            ],
        )

        plan = run_rule_pipeline(ctx)

        assert plan.rule_selected == "baseline"
        assert plan.fallback_used == "baseline"
        # baseline_plan(learner_state_available=True) reads YAML:
        assert plan.learner_state_available is True
        assert plan.topic_name  # non-empty


# ---------------------------------------------------------------------------
# AC-006 — rule-6 with seeded rng is reproducible
# ---------------------------------------------------------------------------


class TestRule6Reproducibility:
    """`@determinism` — seeded rng produces deterministic rule-6 output."""

    def _developing_only_context(self, rng: random.Random) -> PlannerContext:
        return _build_context(
            topic_confidences=[
                _topic(
                    "alpha",
                    percentage=50,
                    band="developing",
                    last_revised_at=_FROZEN_NOW - timedelta(hours=1),
                ),
                _topic(
                    "beta",
                    percentage=50,
                    band="developing",
                    last_revised_at=_FROZEN_NOW - timedelta(hours=1),
                ),
                _topic(
                    "gamma",
                    percentage=50,
                    band="developing",
                    last_revised_at=_FROZEN_NOW - timedelta(hours=1),
                ),
            ],
            rng=rng,
        )

    def test_seeded_rng_reproduces_same_topic(self) -> None:
        first = run_rule_pipeline(
            self._developing_only_context(random.Random(42))
        )
        second = run_rule_pipeline(
            self._developing_only_context(random.Random(42))
        )
        assert first.topic_name == second.topic_name
        assert first.rule_selected == "rule-6"


# ---------------------------------------------------------------------------
# AC-007 — rule-6 sorts candidates by topic_name before sampling
# ---------------------------------------------------------------------------


class TestRule6SortsBeforeSampling:
    """`@determinism` — alphabetical sort precedes rng.choice."""

    def test_choice_is_independent_of_input_order(self) -> None:
        # Same three topics in two different input orders. If rule-6
        # didn't sort first, rng.choice(same seed) would pick different
        # indices and the topic_name would diverge.
        in_order = [
            _topic(
                "alpha",
                percentage=50,
                band="developing",
                last_revised_at=_FROZEN_NOW - timedelta(hours=1),
            ),
            _topic(
                "beta",
                percentage=50,
                band="developing",
                last_revised_at=_FROZEN_NOW - timedelta(hours=1),
            ),
            _topic(
                "gamma",
                percentage=50,
                band="developing",
                last_revised_at=_FROZEN_NOW - timedelta(hours=1),
            ),
        ]
        reversed_order = list(reversed(in_order))

        plan_a = run_rule_pipeline(
            _build_context(
                topic_confidences=in_order, rng=random.Random(42)
            )
        )
        plan_b = run_rule_pipeline(
            _build_context(
                topic_confidences=reversed_order, rng=random.Random(42)
            )
        )

        assert plan_a.topic_name == plan_b.topic_name


# ---------------------------------------------------------------------------
# AC-008 — opening prompt references the topic exactly once
# ---------------------------------------------------------------------------


class TestOpeningPromptShape:
    """`@edge-case` — opening prompt is fresh and topic-specific."""

    def test_prompt_references_topic_exactly_once(self) -> None:
        # Use a distinctive topic name that wouldn't appear elsewhere
        # in the canned phrasing.
        prompt = _build_opening_prompt("XYZ_Quokka_Topic_42")
        assert prompt.count("XYZ_Quokka_Topic_42") == 1

    def test_two_different_topics_yield_different_prompts(self) -> None:
        prompt_a = _build_opening_prompt("topic-A")
        prompt_b = _build_opening_prompt("topic-B")
        assert prompt_a != prompt_b

    def test_pipeline_prompt_mentions_chosen_topic(self) -> None:
        ctx = _build_context(topic_override="My Override Topic")
        plan = run_rule_pipeline(ctx)
        assert plan.topic_name == "My Override Topic"
        assert plan.opening_prompt.count("My Override Topic") == 1


# ---------------------------------------------------------------------------
# AC-009 — topic with no AO mapping → focus_aos=[], ao_mapping_found=False
# ---------------------------------------------------------------------------


class TestAOMapping:
    """`@edge-case @integration-boundary` — AO-mapping scenario."""

    def test_unmapped_topic_yields_empty_focus_aos(self) -> None:
        ctx = _build_context(
            topic_override="Some Off-Curriculum Topic",
            ao_mapping={"other-topic": ["AO1", "AO2"]},  # type: ignore[dict-item]
        )

        plan = run_rule_pipeline(ctx)

        assert plan.focus_aos == []
        assert plan.ao_mapping_found is False

    def test_mapped_topic_populates_focus_aos(self) -> None:
        ctx = _build_context(
            topic_override="metaphor",
            ao_mapping={"metaphor": ["AO2"]},  # type: ignore[dict-item]
        )

        plan = run_rule_pipeline(ctx)

        assert plan.focus_aos == ["AO2"]
        assert plan.ao_mapping_found is True


# ---------------------------------------------------------------------------
# AC-010 — byte-identical output for identical inputs and seeded rng
# ---------------------------------------------------------------------------


class TestDeterminism:
    """`@edge-case @determinism` — two calls produce byte-identical plans."""

    def test_consecutive_calls_byte_identical(self) -> None:
        def _make_ctx() -> PlannerContext:
            return _build_context(
                topic_confidences=[
                    _topic(
                        "alpha",
                        percentage=50,
                        band="developing",
                        last_revised_at=_FROZEN_NOW - timedelta(hours=1),
                    ),
                    _topic(
                        "beta",
                        percentage=50,
                        band="developing",
                        last_revised_at=_FROZEN_NOW - timedelta(hours=1),
                    ),
                ],
                rng=random.Random(42),
            )

        first = run_rule_pipeline(_make_ctx())
        second = run_rule_pipeline(_make_ctx())

        # Byte-identical comparison via Pydantic JSON serialisation.
        assert first.model_dump_json() == second.model_dump_json()


# ---------------------------------------------------------------------------
# Async wrapper coverage — plan_session() builds context and dispatches
# ---------------------------------------------------------------------------


class _FakeClient:
    """Minimal duck-typed wrapper exposing ``client_or_none``.

    The real :class:`GraphitiClient` exposes a ``client_or_none``
    property. For ``get_student_state`` the wrapper is fine returning
    ``None`` for the inner — the helper short-circuits to
    ``StudentState(empty=True)``. We use this fake to drive the
    no-state branch of ``_build_planner_context`` end-to-end.
    """

    def __init__(self, inner: object | None = None) -> None:
        self._inner = inner

    @property
    def client_or_none(self) -> object | None:
        return self._inner


async def test_plan_session_with_no_client_yields_baseline_plan() -> None:
    """End-to-end: ``client=None`` produces the baseline-degraded plan.

    Exercises the async wrapper, the read boundary
    (:func:`get_student_state` returns an empty StudentState with no
    client), and the final fallback (developing band empty →
    :func:`_baseline_plan`).
    """
    plan = await plan_session(
        "lilymay",
        topic_override=None,
        clock=_frozen_clock(),
        rng=random.Random(42),
        client=None,
    )
    assert isinstance(plan, SessionPlan)
    assert plan.rule_selected == "baseline"
    assert plan.fallback_used == "baseline"


async def test_plan_session_with_override_selects_rule_1() -> None:
    """End-to-end: override flows through async wrapper into rule-1."""
    plan = await plan_session(
        "lilymay",
        topic_override="dramatic irony",
        clock=_frozen_clock(),
        rng=random.Random(42),
        client=None,
        ao_mapping={"dramatic irony": ["AO1", "AO2"]},  # type: ignore[arg-type]
    )
    assert plan.rule_selected == "rule-1"
    assert plan.fallback_used is None
    assert plan.topic_name == "dramatic irony"
    assert plan.focus_aos == ["AO1", "AO2"]
    assert plan.ao_mapping_found is True


async def test_build_planner_context_projects_snapshots() -> None:
    """`_build_planner_context` projects StudentState into rule entities.

    Uses a stub client+inner that returns a populated
    :class:`StudentState`, then asserts the resulting
    :class:`PlannerContext` carries rule-layer
    :class:`TopicConfidence` entities.
    """

    class _StubInner:
        async def search_nodes(self, group_ids: list[str], query: str) -> list:
            return [
                {
                    "entity_type": "topicconfidence",
                    "attributes": {
                        "topic_ref": "metaphor",
                        "band": "developing",
                        "percentage": 55,
                        "last_revised_at": (
                            _FROZEN_NOW - timedelta(hours=2)
                        ).isoformat(),
                    },
                }
            ]

        async def search_memory_facts(
            self, group_ids: list[str], query: str
        ) -> list:
            return []

    client = _FakeClient(inner=_StubInner())

    ctx = await _build_planner_context(
        "lilymay",
        clock=_frozen_clock(),
        rng=random.Random(42),
        topic_override=None,
        client=client,
    )

    assert ctx.student_id == "lilymay"
    assert len(ctx.topic_confidences) == 1
    assert ctx.topic_confidences[0].topic_ref == "metaphor"
    assert ctx.topic_confidences[0].band == "developing"
