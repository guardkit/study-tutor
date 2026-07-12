"""Unit tests for session completion producer (TASK-SMP3-05).

Tests the pure producer that turns a completed session into a SessionCompletion
by reading current confidence from the store and applying Phase1MinimalDeltaPolicy.
"""

from __future__ import annotations

import pytest

from study_tutor.knowledge.store.entities import ConfidenceUpdate
from study_tutor.knowledge.student_model import TopicConfidence
from study_tutor.session.completion import (
    Phase1MinimalDeltaPolicy,
    build_session_completion,
)
from study_tutor.session.service import SessionCompletion
from tests.unit.knowledge.store.fakes import FakeStudentStore


class TestPhase1MinimalDeltaPolicy:
    """Test the pure delta policy heuristic."""

    def test_no_misconceptions_five_turns_gives_plus_one(self) -> None:
        """With ≥5 turns and no misconceptions, delta is +1 (engagement bonus)."""
        policy = Phase1MinimalDeltaPolicy()
        delta = policy.compute(
            student_id="S1",
            topic_ref="algebra",
            session_summary={
                "student_turn_count": 5,
                "misconceptions_per_topic": {"algebra": 0},
            },
        )
        assert delta == 1

    def test_no_misconceptions_four_turns_gives_zero(self) -> None:
        """With <5 turns and no misconceptions, delta is 0 (no change)."""
        policy = Phase1MinimalDeltaPolicy()
        delta = policy.compute(
            student_id="S1",
            topic_ref="algebra",
            session_summary={
                "student_turn_count": 4,
                "misconceptions_per_topic": {"algebra": 0},
            },
        )
        assert delta == 0

    def test_one_misconception_gives_minus_three(self) -> None:
        """One misconception → delta -3."""
        policy = Phase1MinimalDeltaPolicy()
        delta = policy.compute(
            student_id="S1",
            topic_ref="algebra",
            session_summary={
                "student_turn_count": 5,
                "misconceptions_per_topic": {"algebra": 1},
            },
        )
        assert delta == -3

    def test_multiple_misconceptions_accumulate_penalty(self) -> None:
        """Multiple misconceptions accumulate: 2 misc → -6."""
        policy = Phase1MinimalDeltaPolicy()
        delta = policy.compute(
            student_id="S1",
            topic_ref="algebra",
            session_summary={
                "student_turn_count": 5,
                "misconceptions_per_topic": {"algebra": 2},
            },
        )
        assert delta == -6

    def test_clamp_lower_bound(self) -> None:
        """Delta is clamped to [-10, 10]: 4+ misc → -10."""
        policy = Phase1MinimalDeltaPolicy()
        delta = policy.compute(
            student_id="S1",
            topic_ref="algebra",
            session_summary={
                "student_turn_count": 5,
                "misconceptions_per_topic": {"algebra": 5},
            },
        )
        assert delta == -10

    def test_clamp_upper_bound(self) -> None:
        """Delta is clamped to [-10, 10]: upper clamp is defensive."""
        policy = Phase1MinimalDeltaPolicy()
        # Current heuristic can't produce > +1, but clamp is defensive
        delta = policy.compute(
            student_id="S1",
            topic_ref="algebra",
            session_summary={
                "student_turn_count": 10,
                "misconceptions_per_topic": {"algebra": 0},
            },
        )
        assert delta == 1  # +1 engagement bonus, no way to exceed +10 currently

    def test_missing_topic_in_misconceptions_map_defaults_to_zero(self) -> None:
        """If topic not in misconceptions map, defaults to 0 misconceptions."""
        policy = Phase1MinimalDeltaPolicy()
        delta = policy.compute(
            student_id="S1",
            topic_ref="geometry",
            session_summary={
                "student_turn_count": 5,
                "misconceptions_per_topic": {},  # Empty map
            },
        )
        assert delta == 1  # 5+ turns, 0 misc → +1

    def test_policy_name_is_phase1_minimal_policy(self) -> None:
        """Policy name matches documented contract."""
        policy = Phase1MinimalDeltaPolicy()
        assert policy.name == "phase1_minimal_policy"


class TestBuildSessionCompletion:
    """Test the store-backed completion producer."""

    @pytest.mark.asyncio
    async def test_reads_current_confidence_and_applies_delta(self) -> None:
        """Producer reads current confidence, applies delta, emits resolved value."""
        store = FakeStudentStore()
        store.add_student(student_id="S1", year_group=10)

        # Set initial confidence: algebra at 50%
        await store.record_session_completion(
            session_id="sess1",
            student_id="S1",
            topic="algebra",
            aos_scaffolded=[],
            xp_awarded=0,
            confidence_updates=[ConfidenceUpdate(topic_name="algebra", percentage=50)],
            misconceptions=[],
        )

        # Build completion with +1 delta (5 turns, no misconceptions)
        completion = await build_session_completion(
            store=store,
            student_id="S1",
            topic="algebra",
            student_turn_count=5,
            aos_scaffolded=["AO1"],
            misconceptions_per_topic={},
        )

        assert completion.topic == "algebra"
        assert completion.aos_scaffolded == ["AO1"]
        assert completion.xp_awarded == 0
        assert completion.misconceptions == []
        assert len(completion.confidence_updates) == 1
        assert completion.confidence_updates[0].topic_name == "algebra"
        assert completion.confidence_updates[0].percentage == 51  # 50 + 1

    @pytest.mark.asyncio
    async def test_clamps_to_zero_one_hundred(self) -> None:
        """Resolved confidence is clamped to [0, 100]."""
        store = FakeStudentStore()
        store.add_student(student_id="S1", year_group=10)

        # Set initial confidence: algebra at 5%
        await store.record_session_completion(
            session_id="sess1",
            student_id="S1",
            topic="algebra",
            aos_scaffolded=[],
            xp_awarded=0,
            confidence_updates=[ConfidenceUpdate(topic_name="algebra", percentage=5)],
            misconceptions=[],
        )

        # Apply -10 delta (should clamp to 0, not -5)
        completion = await build_session_completion(
            store=store,
            student_id="S1",
            topic="algebra",
            student_turn_count=5,
            aos_scaffolded=[],
            misconceptions_per_topic={"algebra": 5},  # -10 delta
        )

        assert completion.confidence_updates[0].percentage == 0  # Clamped to 0

    @pytest.mark.asyncio
    async def test_upper_clamp_to_one_hundred(self) -> None:
        """Resolved confidence clamped to 100 max."""
        store = FakeStudentStore()
        store.add_student(student_id="S1", year_group=10)

        # Set initial confidence: algebra at 99%
        await store.record_session_completion(
            session_id="sess1",
            student_id="S1",
            topic="algebra",
            aos_scaffolded=[],
            xp_awarded=0,
            confidence_updates=[ConfidenceUpdate(topic_name="algebra", percentage=99)],
            misconceptions=[],
        )

        # Apply +1 delta (should clamp to 100, not 100)
        completion = await build_session_completion(
            store=store,
            student_id="S1",
            topic="algebra",
            student_turn_count=5,
            aos_scaffolded=[],
            misconceptions_per_topic={},
        )

        assert completion.confidence_updates[0].percentage == 100  # Clamped to 100

    @pytest.mark.asyncio
    async def test_first_seen_topic_bootstraps_at_baseline_50(self) -> None:
        """S-R3 §2.3 / R12: a first-seen topic (no row yet) is created at the
        mid-Developing baseline (50) BEFORE the session delta is applied.

        This replaces the old skip-unknown-topic behaviour: the guard is
        dropped so ``topic_confidence`` rows are actually *created*, not only
        updated. With 5 turns + no misconceptions the policy delta is +1, so a
        brand-new topic resolves to 51.
        """
        from study_tutor.gamification.constants import (
            CONFIDENCE_BASELINE_PERCENTAGE,
        )

        assert CONFIDENCE_BASELINE_PERCENTAGE == 50

        store = FakeStudentStore()
        store.add_student(student_id="S1", year_group=10)

        # No confidence row for "geometry" → bootstrap at 50, then +1 delta.
        completion = await build_session_completion(
            store=store,
            student_id="S1",
            topic="geometry",
            student_turn_count=5,
            aos_scaffolded=[],
            misconceptions_per_topic={},
        )

        assert completion.topic == "geometry"
        assert len(completion.confidence_updates) == 1
        assert completion.confidence_updates[0].topic_name == "geometry"
        assert completion.confidence_updates[0].percentage == 51  # 50 + 1

    @pytest.mark.asyncio
    async def test_first_seen_topic_with_misconceptions_bootstraps_below_50(
        self,
    ) -> None:
        """Bootstrap-then-delta: a first-seen topic with 2 misconceptions
        resolves to 50 − 6 = 44 (the delta is applied to the baseline, not
        skipped)."""
        store = FakeStudentStore()
        store.add_student(student_id="S1", year_group=10)

        completion = await build_session_completion(
            store=store,
            student_id="S1",
            topic="geometry",
            student_turn_count=5,
            aos_scaffolded=[],
            misconceptions_per_topic={"geometry": 2},  # -6 delta
        )

        assert len(completion.confidence_updates) == 1
        assert completion.confidence_updates[0].percentage == 44  # 50 - 6

    @pytest.mark.asyncio
    async def test_zero_delta_omits_update(self) -> None:
        """If delta is 0 and value unchanged, no update is emitted (acceptable)."""
        store = FakeStudentStore()
        store.add_student(student_id="S1", year_group=10)

        # Set initial confidence: algebra at 50%
        await store.record_session_completion(
            session_id="sess1",
            student_id="S1",
            topic="algebra",
            aos_scaffolded=[],
            xp_awarded=0,
            confidence_updates=[ConfidenceUpdate(topic_name="algebra", percentage=50)],
            misconceptions=[],
        )

        # Apply 0 delta (4 turns, no misconceptions)
        completion = await build_session_completion(
            store=store,
            student_id="S1",
            topic="algebra",
            student_turn_count=4,
            aos_scaffolded=[],
            misconceptions_per_topic={},
        )

        # AC: "no update emitted for an unchanged value is acceptable"
        # So we can emit it or skip it; this test documents the implementation choice
        assert completion.topic == "algebra"
        # Implementation may choose to emit percentage=50 or skip; both are valid

    @pytest.mark.asyncio
    async def test_xp_awarded_is_zero_placeholder(self) -> None:
        """xp_awarded is 0 (ASSUM-006 placeholder)."""
        store = FakeStudentStore()
        store.add_student(student_id="S1", year_group=10)

        completion = await build_session_completion(
            store=store,
            student_id="S1",
            topic="algebra",
            student_turn_count=5,
            aos_scaffolded=[],
            misconceptions_per_topic={},
        )

        assert completion.xp_awarded == 0

    @pytest.mark.asyncio
    async def test_misconceptions_is_empty_placeholder(self) -> None:
        """misconceptions is [] (ASSUM-007 placeholder)."""
        store = FakeStudentStore()
        store.add_student(student_id="S1", year_group=10)

        completion = await build_session_completion(
            store=store,
            student_id="S1",
            topic="algebra",
            student_turn_count=5,
            aos_scaffolded=[],
            misconceptions_per_topic={"algebra": 2},  # Ignored this wave
        )

        assert completion.misconceptions == []

    @pytest.mark.asyncio
    async def test_topic_and_aos_scaffolded_pass_through(self) -> None:
        """topic and aos_scaffolded are carried through unchanged."""
        store = FakeStudentStore()
        store.add_student(student_id="S1", year_group=10)

        completion = await build_session_completion(
            store=store,
            student_id="S1",
            topic="trigonometry",
            student_turn_count=5,
            aos_scaffolded=["AO1", "AO3"],
            misconceptions_per_topic={},
        )

        assert completion.topic == "trigonometry"
        assert completion.aos_scaffolded == ["AO1", "AO3"]
