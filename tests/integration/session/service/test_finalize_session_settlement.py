"""Real-Postgres proofs for ``finalize_session`` + the sweep (spec §4.2 / §4.3).

Drives the settlement transaction against a self-provisioned throwaway Postgres
(the session-service conftest; never the env DSN, never a non-loopback host):
the single-transaction bank (XP + achievement + settled_at + confidence history),
the savepoint fault path (D4), exactly-once double-end replay (D6), the zero-turn
settle, and the sweep CLI end-to-end.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from click.testing import CliRunner
from sqlalchemy import text

from study_tutor.knowledge.store.entities import ConfidenceUpdate
from study_tutor.knowledge.student_model import Misconception

UTC = timezone.utc


async def _active_session_with_turns(
    pg_store, pg_engine, student_id: str, *, engagement_seconds: int,
    started_at: datetime,
) -> str:
    """Create an active session, then stamp two turns ``engagement_seconds`` apart."""
    record, _ = await pg_store.create_session(
        student_id=student_id, subject="english", topic="Macbeth"
    )
    sid = record.session_id
    last = started_at + timedelta(seconds=engagement_seconds)
    async with pg_engine.begin() as conn:
        await conn.execute(
            text("UPDATE session SET started_at = :ts WHERE session_id = :sid"),
            {"ts": started_at, "sid": sid},
        )
        for idx, (role, ts) in enumerate(
            [("user", started_at), ("tutor", last)]
        ):
            await conn.execute(
                text(
                    "INSERT INTO session_turn "
                    "(session_id, turn_index, role, content, ts) "
                    "VALUES (:sid, :idx, :role, 'x', :ts)"
                ),
                {"sid": sid, "idx": idx, "role": role, "ts": ts},
            )
        await conn.execute(
            text("UPDATE session SET turn_count = 2 WHERE session_id = :sid"),
            {"sid": sid},
        )
    return sid


async def _fetch_session(pg_engine, sid: str):
    async with pg_engine.connect() as conn:
        return (
            await conn.execute(
                text(
                    "SELECT status, xp_awarded, settled_at FROM session "
                    "WHERE session_id = :sid"
                ),
                {"sid": sid},
            )
        ).fetchone()


class TestFinalizeSession:
    async def test_winner_banks_xp_achievement_and_history(
        self, pg_store, pg_engine, student_id
    ) -> None:
        sid = await _active_session_with_turns(
            pg_store, pg_engine, student_id,
            engagement_seconds=300, started_at=datetime(2026, 7, 12, 9, 0, tzinfo=UTC),
        )
        now = datetime(2026, 7, 12, 10, 0, tzinfo=UTC)
        result = await pg_store.finalize_session(
            student_id=student_id, session_id=sid, now=now,
            confidence_updates=[ConfidenceUpdate(topic_name="Macbeth", percentage=55)],
            misconceptions=[], aos_scaffolded=["AO1"], topic="Macbeth",
        )

        assert result.settled is True and result.replayed is False
        assert result.decision is not None
        assert result.decision.xp_awarded == 60  # 300 s → +60 band

        row = await _fetch_session(pg_engine, sid)
        assert row[0] == "ended"
        assert row[1] == 60
        assert row[2] == now  # settled_at stamped

        async with pg_engine.connect() as conn:
            ach = (
                await conn.execute(
                    text(
                        "SELECT achievement_id, xp_awarded, session_id "
                        "FROM achievement WHERE student_id = :sid "
                        "ORDER BY achievement_id"
                    ),
                    {"sid": student_id},
                )
            ).fetchall()
            history = (
                await conn.execute(
                    text(
                        "SELECT topic_name, percentage, session_id, source "
                        "FROM topic_confidence_history WHERE student_id = :sid"
                    ),
                    {"sid": student_id},
                )
            ).fetchall()

        # First Steps + the First-Century cascade, each linked to the session.
        assert {a[0] for a in ach} == {"first_steps", "first_century"}
        assert all(a[2] == sid for a in ach)
        assert history == [("Macbeth", 55, sid, "session")]

    async def test_double_end_replays_identical_decision(
        self, pg_store, pg_engine, student_id
    ) -> None:
        sid = await _active_session_with_turns(
            pg_store, pg_engine, student_id,
            engagement_seconds=1600, started_at=datetime(2026, 7, 12, 9, 0, tzinfo=UTC),
        )
        first = await pg_store.finalize_session(
            student_id=student_id, session_id=sid,
            now=datetime(2026, 7, 12, 10, 0, tzinfo=UTC),
            confidence_updates=[], misconceptions=[], aos_scaffolded=[], topic="Macbeth",
        )
        second = await pg_store.finalize_session(
            student_id=student_id, session_id=sid,
            now=datetime(2026, 7, 12, 11, 0, tzinfo=UTC),
            confidence_updates=[], misconceptions=[], aos_scaffolded=[], topic="Macbeth",
        )

        assert first.replayed is False and second.replayed is True
        assert first.decision == second.decision  # exactly-once + identical replay

        # Achievements banked exactly once despite the second call.
        async with pg_engine.connect() as conn:
            count = (
                await conn.execute(
                    text("SELECT count(*) FROM achievement WHERE student_id = :sid"),
                    {"sid": student_id},
                )
            ).scalar()
        assert count == len(first.decision.unlocked)

    async def test_settlement_fault_ends_session_leaves_marker_null(
        self, pg_store, pg_engine, student_id
    ) -> None:
        sid = await _active_session_with_turns(
            pg_store, pg_engine, student_id,
            engagement_seconds=300, started_at=datetime(2026, 7, 12, 9, 0, tzinfo=UTC),
        )
        poison = Misconception(
            text="   ",  # blank after sanitisation → raises in the savepoint
            topic_ref="Macbeth", observed_at=datetime.now(UTC),
            confidence_band_at_observation="developing",
        )
        result = await pg_store.finalize_session(
            student_id=student_id, session_id=sid,
            now=datetime(2026, 7, 12, 10, 0, tzinfo=UTC),
            confidence_updates=[ConfidenceUpdate(topic_name="Macbeth", percentage=55)],
            misconceptions=[poison], aos_scaffolded=[], topic="Macbeth",
        )

        assert result.settled is False and result.decision is None
        row = await _fetch_session(pg_engine, sid)
        assert row[0] == "ended"  # the session still ends
        assert row[2] is None  # settled_at NULL for the sweep (D4)

        # No partial writes rolled forward from the savepoint.
        async with pg_engine.connect() as conn:
            ach = (
                await conn.execute(
                    text("SELECT count(*) FROM achievement WHERE student_id = :sid"),
                    {"sid": student_id},
                )
            ).scalar()
            conf = (
                await conn.execute(
                    text(
                        "SELECT count(*) FROM topic_confidence "
                        "WHERE student_id = :sid"
                    ),
                    {"sid": student_id},
                )
            ).scalar()
        assert ach == 0 and conf == 0

    async def test_zero_turn_settles_at_zero_xp(
        self, pg_store, pg_engine, student_id
    ) -> None:
        record, _ = await pg_store.create_session(
            student_id=student_id, subject="english", topic="Macbeth"
        )
        now = datetime(2026, 7, 12, 10, 0, tzinfo=UTC)
        result = await pg_store.finalize_session(
            student_id=student_id, session_id=record.session_id, now=now,
            confidence_updates=[], misconceptions=[], aos_scaffolded=[], topic="Macbeth",
        )
        assert result.had_turns is False
        assert result.decision is not None and result.decision.xp_awarded == 0
        row = await _fetch_session(pg_engine, record.session_id)
        assert row[0] == "ended" and row[1] == 0 and row[2] == now


class TestSweep:
    async def test_sweep_settles_unsettled_then_idempotent(
        self, pg_store, pg_engine, student_id
    ) -> None:
        sid = await _active_session_with_turns(
            pg_store, pg_engine, student_id,
            engagement_seconds=300, started_at=datetime(2026, 7, 12, 9, 0, tzinfo=UTC),
        )
        # Simulate a session that ended WITHOUT settling (settled_at NULL).
        async with pg_engine.begin() as conn:
            await conn.execute(
                text("UPDATE session SET status = 'ended' WHERE session_id = :sid"),
                {"sid": sid},
            )

        assert await pg_store.list_unsettled_ended_sessions() == [sid]

        now = datetime(2026, 7, 12, 10, 0, tzinfo=UTC)
        first = await pg_store.sweep_settle_session(session_id=sid, now=now)
        assert first is not None and first.settled is True
        assert first.decision is not None and first.decision.xp_awarded == 60

        assert await pg_store.list_unsettled_ended_sessions() == []
        second = await pg_store.sweep_settle_session(
            session_id=sid, now=now + timedelta(hours=1)
        )
        assert second is None  # idempotent

    async def test_settle_sessions_cli(
        self, pg_store, pg_engine, student_id, session_service_pg_container, monkeypatch
    ) -> None:
        """The ``settle-sessions`` click subcommand settles unsettled rows."""
        from study_tutor.cli.main import cli
        from study_tutor.knowledge.store import provider as store_provider

        sid = await _active_session_with_turns(
            pg_store, pg_engine, student_id,
            engagement_seconds=1600, started_at=datetime(2026, 7, 12, 9, 0, tzinfo=UTC),
        )
        async with pg_engine.begin() as conn:
            await conn.execute(
                text("UPDATE session SET status = 'ended' WHERE session_id = :sid"),
                {"sid": sid},
            )

        monkeypatch.setenv("STUDY_TUTOR_PG_DSN", session_service_pg_container)
        try:
            # CliRunner.invoke runs the command's own asyncio.run(); run it off
            # the test's event loop so the two loops don't collide.
            import asyncio

            result = await asyncio.to_thread(
                lambda: CliRunner().invoke(
                    cli, ["settle-sessions", "--log-level", "ERROR"]
                )
            )
            assert result.exit_code == 0, result.output
            assert "Settled 1 sessions" in result.output
        finally:
            store_provider.set_student_store(None)

        row = await _fetch_session(pg_engine, sid)
        assert row[2] is not None  # settled_at stamped by the CLI sweep
        assert row[1] == 180  # 1600 s → +180 band


class TestW2CaptureSettlement:
    """S-E4: the W2 capture-wave tranche fires through the REAL Postgres
    settlement — proving the ``_read_w2_facts`` SQL assembly (correlated
    text-association subquery, cumulative counters) produces the signals."""

    async def _macbeth_session(
        self, pg_store, pg_engine, student_id, *, started_at, quotes=0
    ) -> str:
        record, _ = await pg_store.create_session(
            student_id=student_id, subject="english", topic="Macbeth",
            text_name="macbeth",
        )
        sid = record.session_id
        last = started_at + timedelta(seconds=300)
        async with pg_engine.begin() as conn:
            await conn.execute(
                text("UPDATE session SET started_at = :ts WHERE session_id = :sid"),
                {"ts": started_at, "sid": sid},
            )
            for idx, (role, ts) in enumerate([("user", started_at), ("tutor", last)]):
                await conn.execute(
                    text(
                        "INSERT INTO session_turn "
                        "(session_id, turn_index, role, content, ts) "
                        "VALUES (:sid, :idx, :role, 'x', :ts)"
                    ),
                    {"sid": sid, "idx": idx, "role": role, "ts": ts},
                )
            await conn.execute(
                text(
                    "UPDATE session SET turn_count = 2, quotes_embedded = :q "
                    "WHERE session_id = :sid"
                ),
                {"sid": sid, "q": quotes},
            )
        return sid

    async def test_macbeth_master_banks_via_real_settlement(
        self, pg_store, pg_engine, student_id
    ) -> None:
        sid = await self._macbeth_session(
            pg_store, pg_engine, student_id,
            started_at=datetime(2026, 7, 12, 9, 0, tzinfo=UTC),
        )
        now = datetime(2026, 7, 12, 10, 0, tzinfo=UTC)
        result = await pg_store.finalize_session(
            student_id=student_id, session_id=sid, now=now,
            confidence_updates=[
                ConfidenceUpdate(topic_name="ambition", percentage=85),
                ConfidenceUpdate(topic_name="guilt", percentage=82),
                ConfidenceUpdate(topic_name="kingship", percentage=80),
            ],
            misconceptions=[], aos_scaffolded=["AO2"], topic="ambition",
        )
        assert "macbeth_master" in {a.id for a in result.decision.unlocked}

        async with pg_engine.connect() as conn:
            banked = (
                await conn.execute(
                    text(
                        "SELECT xp_awarded, session_id FROM achievement "
                        "WHERE student_id = :sid AND achievement_id = 'macbeth_master'"
                    ),
                    {"sid": student_id},
                )
            ).fetchone()
        assert banked is not None
        assert banked[0] == 500  # design §5 verbatim
        assert banked[1] == sid  # carries the settling session (replay support)

    async def test_quote_champion_banks_on_ten_embedded_quotes(
        self, pg_store, pg_engine, student_id
    ) -> None:
        sid = await self._macbeth_session(
            pg_store, pg_engine, student_id,
            started_at=datetime(2026, 7, 12, 9, 0, tzinfo=UTC), quotes=10,
        )
        now = datetime(2026, 7, 12, 10, 0, tzinfo=UTC)
        result = await pg_store.finalize_session(
            student_id=student_id, session_id=sid, now=now,
            confidence_updates=[], misconceptions=[], aos_scaffolded=[], topic="Macbeth",
        )
        assert "quote_champion" in {a.id for a in result.decision.unlocked}

    async def test_plain_settlement_banks_no_w2(
        self, pg_store, pg_engine, student_id
    ) -> None:
        sid = await self._macbeth_session(
            pg_store, pg_engine, student_id,
            started_at=datetime(2026, 7, 12, 9, 0, tzinfo=UTC),
        )
        now = datetime(2026, 7, 12, 10, 0, tzinfo=UTC)
        result = await pg_store.finalize_session(
            student_id=student_id, session_id=sid, now=now,
            confidence_updates=[ConfidenceUpdate(topic_name="ambition", percentage=55)],
            misconceptions=[], aos_scaffolded=[], topic="ambition",
        )
        w2_ids = {
            "macbeth_master", "quote_champion", "quote_master", "set_text_explorer",
            "six_ao_sampler", "climbing", "breakthrough", "no_weak_spots",
        }
        assert {a.id for a in result.decision.unlocked} & w2_ids == set()
