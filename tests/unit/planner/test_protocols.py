"""Unit tests for the Rule protocol, PlannerContext, and Candidate types.

Covers TASK-DSP-002 acceptance criteria AC-001 through AC-007. AC-002
runs ``mypy --strict`` as a subprocess against an inline sample module;
the test is skipped if mypy is not on ``PATH`` so the suite stays green
in environments without the dev tools installed.
"""
from __future__ import annotations

import dataclasses
import random
import shutil
import subprocess
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol, get_type_hints

import pytest

from study_tutor.knowledge.student_model import (
    Misconception,
    TopicConfidence,
)
from study_tutor.planner import (
    AOCode,
    Candidate,
    PlannerContext,
    Rule,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _topic(
    name: str,
    band: str,
    *,
    percentage: int = 50,
    student_id: str = "student-1",
) -> TopicConfidence:
    """Build a TopicConfidence for use in tests."""
    return TopicConfidence(
        student_ref=student_id,
        topic_ref=name,
        percentage=percentage,
        band=band,  # type: ignore[arg-type]
        last_revised_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )


def _frozen_clock() -> datetime:
    return datetime(2026, 4, 29, 12, 0, 0, tzinfo=timezone.utc)


def _build_context(
    *,
    topic_override: str | None = None,
    topic_confidences: list[TopicConfidence] | None = None,
    misconceptions: list[Misconception] | None = None,
    clock: object = None,
) -> PlannerContext:
    """Build a PlannerContext with sensible defaults for protocol tests."""
    return PlannerContext.create(
        student_id="student-1",
        topic_confidences=topic_confidences or [],
        misconceptions=misconceptions or [],
        ao_mapping={},
        topic_override=topic_override,
        clock=clock,  # type: ignore[arg-type]
        rng=random.Random(42),
    )


# ---------------------------------------------------------------------------
# AC-001: Rule is a typing.Protocol (structural typing, no inheritance)
# ---------------------------------------------------------------------------


def test_rule_is_a_typing_protocol() -> None:
    """``Rule`` must be a ``typing.Protocol`` subclass, not a regular ABC."""
    # Both checks together prove "structural typing": Protocol is in the
    # MRO and the class carries the runtime Protocol marker.
    assert Protocol in Rule.__mro__
    assert getattr(Rule, "_is_protocol", False) is True


def test_class_with_call_signature_is_a_rule_without_subclassing() -> None:
    """A class with a conforming ``__call__`` is a Rule by structure alone."""

    class StructuralRule:
        def __call__(self, ctx: PlannerContext) -> Candidate | None:
            return None

    instance = StructuralRule()

    # Structural typing: no explicit subclassing required. The class
    # must not inherit from ``Rule`` explicitly — only via structure.
    assert Rule not in StructuralRule.__bases__
    assert Rule not in StructuralRule.__mro__
    # Runtime protocol check accepts the structurally-conforming class.
    assert isinstance(instance, Rule)


# ---------------------------------------------------------------------------
# AC-002: mypy --strict accepts a class with a conforming __call__
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    shutil.which("mypy") is None,
    reason="mypy not available on PATH",
)
def test_mypy_strict_accepts_structurally_conforming_rule(
    tmp_path: Path,
) -> None:
    """``mypy --strict`` accepts both a structurally-typed class and a
    plain lambda assigned to a ``Rule``-typed name. Covers AC-002 and the
    type-system half of AC-003 (covariant return type).
    """
    sample = tmp_path / "rule_sample.py"
    sample.write_text(
        textwrap.dedent(
            """
            from __future__ import annotations

            from study_tutor.planner import (
                Candidate,
                PlannerContext,
                Rule,
            )


            class StructuralRule:
                def __call__(self, ctx: PlannerContext) -> Candidate | None:
                    return None


            def take_rule(r: Rule) -> None:
                pass


            # Structural conformance — no explicit subclassing.
            take_rule(StructuralRule())

            # Lambda returning None must satisfy Candidate | None
            # (covariant return type).
            lambda_rule: Rule = lambda ctx: None
            take_rule(lambda_rule)
            """
        ),
        encoding="utf-8",
    )

    completed = subprocess.run(
        [
            "mypy",
            "--strict",
            "--no-incremental",
            # Resolve imports against the interpreter running the tests (the
            # project .venv, which carries the editable study_tutor install +
            # py.typed). The `mypy` on PATH may be a global install whose own
            # interpreter cannot see the src-layout editable package.
            "--python-executable",
            sys.executable,
            str(sample),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, (
        f"mypy --strict rejected sample:\n"
        f"stdout:\n{completed.stdout}\n"
        f"stderr:\n{completed.stderr}"
    )


# ---------------------------------------------------------------------------
# AC-003: Plain lambda satisfies the Rule protocol
# ---------------------------------------------------------------------------


def test_plain_lambda_satisfies_rule_protocol() -> None:
    """``lambda ctx: None`` must satisfy the Rule protocol at runtime."""
    rule: Rule = lambda ctx: None  # noqa: E731  (lambda is the test subject)

    # Runtime protocol membership.
    assert isinstance(rule, Rule)

    # Calling it with a real context returns None and never raises.
    ctx = _build_context()
    assert rule(ctx) is None


# ---------------------------------------------------------------------------
# AC-004: PlannerContext.topics_in_band
# ---------------------------------------------------------------------------


def test_topics_in_band_filters_by_band() -> None:
    struggling = _topic("metaphor", "struggling", percentage=20)
    developing = _topic("simile", "developing", percentage=55)
    secure = _topic("alliteration", "secure", percentage=80)
    ctx = _build_context(
        topic_confidences=[struggling, developing, secure],
    )

    assert ctx.topics_in_band("struggling") == [struggling]
    assert ctx.topics_in_band("developing") == [developing]
    assert ctx.topics_in_band("secure") == [secure]


def test_topics_in_band_returns_empty_list_when_no_match() -> None:
    ctx = _build_context(
        topic_confidences=[_topic("x", "secure")],
    )
    assert ctx.topics_in_band("struggling") == []


def test_topics_in_band_preserves_order() -> None:
    first = _topic("a", "developing", percentage=45)
    second = _topic("b", "developing", percentage=60)
    ctx = _build_context(topic_confidences=[first, second])
    assert ctx.topics_in_band("developing") == [first, second]


@pytest.mark.parametrize(
    "bad_band",
    ["mastered", "STRUGGLING", "", "weak", "unknown", "Developing"],
)
def test_topics_in_band_rejects_unknown_band(bad_band: str) -> None:
    ctx = _build_context()
    with pytest.raises(ValueError) as exc_info:
        ctx.topics_in_band(bad_band)  # type: ignore[arg-type]
    assert "unknown band" in str(exc_info.value)


# ---------------------------------------------------------------------------
# AC-005: Candidate is immutable
# ---------------------------------------------------------------------------


def _valid_candidate_kwargs() -> dict:
    return {
        "topic_name": "metaphor identification",
        "rule_source": "rule-1",
        "confidence_percentage": 35.0,
        "related_misconceptions": [],
        "rationale_fragment": "Lowest-confidence struggling topic.",
    }


def test_candidate_is_a_frozen_dataclass() -> None:
    assert dataclasses.is_dataclass(Candidate)
    # frozen=True surfaces on the dataclass params.
    params = getattr(Candidate, "__dataclass_params__", None)
    assert params is not None
    assert params.frozen is True


def test_candidate_instantiates_with_full_kwargs() -> None:
    candidate = Candidate(**_valid_candidate_kwargs())
    assert candidate.topic_name == "metaphor identification"
    assert candidate.rule_source == "rule-1"
    assert candidate.confidence_percentage == 35.0
    assert candidate.related_misconceptions == []
    assert candidate.rationale_fragment


def test_candidate_rejects_attribute_assignment() -> None:
    candidate = Candidate(**_valid_candidate_kwargs())
    with pytest.raises(dataclasses.FrozenInstanceError):
        candidate.topic_name = "rewritten"  # type: ignore[misc]


def test_candidate_accepts_none_confidence_for_off_curriculum() -> None:
    candidate = Candidate(
        **{**_valid_candidate_kwargs(), "confidence_percentage": None},
    )
    assert candidate.confidence_percentage is None


# ---------------------------------------------------------------------------
# AC-006: Empty-string override → None
# ---------------------------------------------------------------------------


def test_empty_string_override_is_normalised_to_none() -> None:
    ctx = PlannerContext.create(
        student_id="student-1",
        topic_confidences=[],
        misconceptions=[],
        ao_mapping={},
        topic_override="",
    )
    assert ctx.topic_override is None


def test_none_override_stays_none() -> None:
    ctx = PlannerContext.create(
        student_id="student-1",
        topic_confidences=[],
        misconceptions=[],
        ao_mapping={},
        topic_override=None,
    )
    assert ctx.topic_override is None


def test_non_empty_override_is_preserved_verbatim() -> None:
    ctx = PlannerContext.create(
        student_id="student-1",
        topic_confidences=[],
        misconceptions=[],
        ao_mapping={},
        topic_override="metaphor identification",
    )
    assert ctx.topic_override == "metaphor identification"


def test_whitespace_only_override_is_preserved() -> None:
    """Only the empty string normalises — whitespace stays as-is so the
    rule pipeline can decide how to react to a clearly malformed value
    rather than silently swallowing it."""
    ctx = PlannerContext.create(
        student_id="student-1",
        topic_confidences=[],
        misconceptions=[],
        ao_mapping={},
        topic_override="   ",
    )
    assert ctx.topic_override == "   "


# ---------------------------------------------------------------------------
# Default factories: clock and rng (supports AC-001 / AC-005 contract)
# ---------------------------------------------------------------------------


def test_create_defaults_supply_callable_clock_and_random() -> None:
    ctx = PlannerContext.create(
        student_id="student-1",
        topic_confidences=[],
        misconceptions=[],
        ao_mapping={},
    )
    assert callable(ctx.clock)
    now = ctx.clock()
    assert isinstance(now, datetime)
    assert isinstance(ctx.rng, random.Random)


def test_create_respects_injected_clock_and_rng() -> None:
    seeded = random.Random(99)
    ctx = PlannerContext.create(
        student_id="student-1",
        topic_confidences=[],
        misconceptions=[],
        ao_mapping={},
        clock=_frozen_clock,
        rng=seeded,
    )
    assert ctx.clock() == _frozen_clock()
    assert ctx.rng is seeded


# ---------------------------------------------------------------------------
# AC-007: lint/format — vacuously satisfied (no lint tooling is configured
# in pyproject.toml). py_compile sanity check covers basic well-formedness.
# ---------------------------------------------------------------------------


def test_protocols_module_compiles_cleanly() -> None:
    import py_compile

    from study_tutor.planner import protocols

    py_compile.compile(protocols.__file__, doraise=True)


def test_planner_init_re_exports_new_symbols() -> None:
    """The package-level imports added in TASK-DSP-002 must round-trip."""
    from study_tutor import planner

    for name in ("Rule", "Candidate", "PlannerContext", "AOCode", "PlannerBand"):
        assert name in planner.__all__
        assert hasattr(planner, name)


# ---------------------------------------------------------------------------
# Type-shape sanity (cheap structural checks against the spec)
# ---------------------------------------------------------------------------


def test_planner_context_has_expected_fields() -> None:
    field_names = {f.name for f in dataclasses.fields(PlannerContext)}
    assert field_names == {
        "student_id",
        "topic_confidences",
        "misconceptions",
        "ao_mapping",
        "topic_override",
        "clock",
        "rng",
        # TASK-DSP-006 — read-boundary signal carried alongside the
        # rule inputs so the pipeline can route to ``_baseline_plan(False)``
        # when the student-model read failed or the learner is unseeded.
        "learner_state_available",
        # S-R3 §6.3(c) R11 — persisted session plan facts feeding the 4-day
        # London anti-repetition window (see anti_repetition_blocked()).
        "recent_recommendations",
    }


def test_candidate_has_expected_fields() -> None:
    field_names = {f.name for f in dataclasses.fields(Candidate)}
    assert field_names == {
        "topic_name",
        "rule_source",
        "confidence_percentage",
        "related_misconceptions",
        "rationale_fragment",
    }


def test_rule_protocol_call_signature_uses_planner_context() -> None:
    """The Rule.__call__ annotation must reference PlannerContext."""
    hints = get_type_hints(Rule.__call__)
    assert hints["ctx"] is PlannerContext
    # Return is Candidate | None.
    assert "Candidate" in str(hints["return"])
    assert "None" in str(hints["return"]) or hints["return"].__class__.__name__ in {
        "_UnionGenericAlias",
        "UnionType",
    }


def test_aocode_alias_matches_planner_assessment_objective_code() -> None:
    from study_tutor.planner.types import AssessmentObjectiveCode

    assert AOCode is AssessmentObjectiveCode
