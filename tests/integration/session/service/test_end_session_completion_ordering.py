"""S-R1 — composed-service-path proof that ``end_session`` lands its completion.

Drives the *composed service path* — ``SessionService.start_session`` → ``turn``
→ ``end_session(completion=…)`` — against a self-provisioned throwaway Postgres,
asserting the ``topic_confidence`` and ``misconception`` children the completion
carries actually land.

This is the regression pin for the W0 ordering bug: before the fix,
``SessionService.end_session`` called ``store.end_session`` (status→'ended', its
own committed transaction) *before* ``store.record_session_completion``, whose
idempotency gate is ``ON CONFLICT … WHERE status != 'ended'``. With the row
already 'ended', the gate never fired and the confidence/misconception children
were silently dropped. The fix reorders the completion write ahead of the status
transition, so this test lands the children.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from sqlalchemy import text

from study_tutor.knowledge.store.entities import ConfidenceUpdate
from study_tutor.knowledge.student_model import Misconception
from study_tutor.session.service import SessionCompletion, SessionService, TutorReply


async def _echo_reply(user_message: str) -> TutorReply:
    """A trivial injected tutor loop for driving ``SessionService.turn``."""
    return TutorReply(response=f"tutor: {user_message}")


class TestEndSessionCompletionOrdering:
    """The completion write must survive the status transition (spec §1)."""

    async def test_composed_service_path_lands_confidence_and_misconceptions(
        self, pg_store, pg_engine, student_id: str
    ) -> None:
        """start_session → turn → end_session(completion) persists children."""
        service = SessionService(store=pg_store)

        start = await service.start_session(
            student_id=student_id,
            subject="mathematics",
            topic="Quadratic Equations",
        )
        session_id = start.session_id

        await service.turn(
            student_id=student_id,
            session_id=session_id,
            user_message="How do I factorise x^2 + 5x + 6?",
            reply_fn=_echo_reply,
        )

        completion = SessionCompletion(
            topic="Quadratic Equations",
            aos_scaffolded=["AO1", "AO3"],
            xp_awarded=120,
            confidence_updates=[
                ConfidenceUpdate(topic_name="Quadratic Equations", percentage=72)
            ],
            misconceptions=[
                Misconception(
                    topic_ref="Quadratic Equations",
                    text="Thinks the discriminant is always positive",
                    observed_at=datetime.now(timezone.utc),
                    confidence_band_at_observation="secure",
                )
            ],
        )

        end = await service.end_session(
            student_id=student_id,
            session_id=session_id,
            completion=completion,
        )
        assert end.status == "ended"

        # The session row transitioned to 'ended' and banked the completion facts.
        async with pg_engine.connect() as conn:
            session_row = (
                await conn.execute(
                    text(
                        "SELECT status, topic, xp_awarded "
                        "FROM session WHERE session_id = :sid"
                    ),
                    {"sid": session_id},
                )
            ).fetchone()
        assert session_row is not None
        assert session_row[0] == "ended"
        assert session_row[1] == "Quadratic Equations"
        # Spec §4.2: XP is engine-derived from engagement duration now, NOT the
        # explicit completion's xp_awarded. The two turns are stamped in the same
        # instant (engagement ≈ 0 s < 120 s), so this settles at 0 XP. The point
        # of this pin is that the confidence/misconception children still land in
        # the single finalize_session transaction (asserted below).
        assert session_row[2] == 0

        # The confidence child actually landed (this is what the bug dropped).
        async with pg_engine.connect() as conn:
            conf_row = (
                await conn.execute(
                    text(
                        "SELECT percentage, band FROM topic_confidence "
                        "WHERE student_id = :sid AND topic_name = :topic"
                    ),
                    {"sid": student_id, "topic": "Quadratic Equations"},
                )
            ).fetchone()
        assert conf_row is not None, (
            "topic_confidence row was dropped — the completion write lost the "
            "ON CONFLICT gate because the session was already 'ended'"
        )
        assert conf_row[0] == 72
        assert conf_row[1] == "secure"

        # The misconception child actually landed too.
        async with pg_engine.connect() as conn:
            misc_rows = (
                await conn.execute(
                    text(
                        "SELECT topic_name, text FROM misconception "
                        "WHERE student_id = :sid"
                    ),
                    {"sid": student_id},
                )
            ).fetchall()
        assert len(misc_rows) == 1, "misconception row was dropped"
        assert misc_rows[0][0] == "Quadratic Equations"
        assert misc_rows[0][1] == "Thinks the discriminant is always positive"

    async def test_replayed_end_session_is_idempotent(
        self, pg_store, pg_engine, student_id: str
    ) -> None:
        """A second end_session on the same session does not double-write children."""
        service = SessionService(store=pg_store)

        start = await service.start_session(
            student_id=student_id,
            subject="mathematics",
            topic="Trigonometry",
        )
        session_id = start.session_id
        await service.turn(
            student_id=student_id,
            session_id=session_id,
            user_message="Explain sine rule",
            reply_fn=_echo_reply,
        )

        completion = SessionCompletion(
            topic="Trigonometry",
            aos_scaffolded=["AO2"],
            xp_awarded=60,
            confidence_updates=[
                ConfidenceUpdate(topic_name="Trigonometry", percentage=55)
            ],
            misconceptions=[
                Misconception(
                    topic_ref="Trigonometry",
                    text="Confuses sine and cosine",
                    observed_at=datetime.now(timezone.utc),
                    confidence_band_at_observation="developing",
                )
            ],
        )

        await service.end_session(
            student_id=student_id, session_id=session_id, completion=completion
        )

        # Replaying the completion write against the already-ended session must
        # be a no-op on the children (idempotency gate on status='ended').
        await pg_store.record_session_completion(
            student_id=student_id,
            session_id=session_id,
            topic="Trigonometry",
            aos_scaffolded=["AO2"],
            xp_awarded=60,
            confidence_updates=[
                ConfidenceUpdate(topic_name="Trigonometry", percentage=99)
            ],
            misconceptions=[
                Misconception(
                    topic_ref="Trigonometry",
                    text="Confuses sine and cosine",
                    observed_at=datetime.now(timezone.utc),
                    confidence_band_at_observation="developing",
                )
            ],
        )

        async with pg_engine.connect() as conn:
            misc_count = (
                await conn.execute(
                    text(
                        "SELECT count(*) FROM misconception WHERE student_id = :sid"
                    ),
                    {"sid": student_id},
                )
            ).scalar()
            conf_pct = (
                await conn.execute(
                    text(
                        "SELECT percentage FROM topic_confidence "
                        "WHERE student_id = :sid AND topic_name = :topic"
                    ),
                    {"sid": student_id, "topic": "Trigonometry"},
                )
            ).scalar()

        assert misc_count == 1, "replay double-wrote the misconception child"
        assert conf_pct == 55, "replay overwrote the banked confidence value"
