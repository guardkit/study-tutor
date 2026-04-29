"""Unit tests for the Lilymay baseline seeding script (TASK-GSM-006).

Each acceptance criterion in
``tasks/backlog/graphiti-student-model/TASK-GSM-006-seeding-script.md`` is
covered by at least one test below.

The tests deliberately avoid hitting a real FalkorDB:

- ``get_client`` is monkeypatched to return a fake :class:`GraphitiClient`
  wrapper (or ``None`` for the store-unreachable path).
- ``get_student_state`` is monkeypatched per-scenario to drive the
  pre-flight idempotency branch and the post-seed verification gate.
- The :class:`GraphitiWriteHelper` is replaced by a fake that records every
  ``schedule_write`` call without ever spawning a task.

This keeps the suite hermetic while still exercising the real script
orchestration code (``main`` / ``seed_lilymay``).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

import scripts.seed_student_model as seed_module
from scripts.seed_student_model import (
    AOS,
    DEFAULT_CONFIG,
    EXIT_CLIENT_UNAVAILABLE,
    EXIT_OK,
    EXIT_PENDING_WRITES_ABANDONED,
    STUDENT_ID,
    SUBJECTS,
    TEXTS,
    TOPICS,
    _is_already_seeded,
    load_config,
    main,
    require_client_or_exit,
    seed_lilymay,
)
from study_tutor.knowledge.episodes import (
    SeedBaselineEpisode,
    TopicConfidenceUpdatedEpisode,
)
from study_tutor.knowledge.queries import StudentState, TopicConfidenceSnapshot
from study_tutor.knowledge.student_model import (
    FLEET_GROUP_ID,
    STUDENT_GROUP_PREFIX,
    SUBJECT_GROUP_PREFIX,
    confidence_band_for,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeHelper:
    """Records every schedule_write call; drain reports configured tallies."""

    def __init__(
        self, *, drain_succeeded: int = 0, drain_abandoned: int = 0
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self._drain_succeeded = drain_succeeded
        self._drain_abandoned = drain_abandoned
        self.drain_call_count = 0

    def schedule_write(
        self,
        *,
        group_ids: list[str],
        episode: Any,
        flush_id: str,
    ) -> None:
        self.calls.append(
            {
                "group_ids": list(group_ids),
                "episode": episode,
                "flush_id": flush_id,
            }
        )
        return None

    async def drain(self, timeout_sec: int | None = None) -> tuple[int, int]:
        self.drain_call_count += 1
        # Use the recorded calls as the implicit "succeeded" budget when
        # not explicitly overridden so the post-drain summary log matches
        # what a real helper would report.
        succeeded = (
            self._drain_succeeded
            if self._drain_succeeded
            else max(0, len(self.calls) - self._drain_abandoned)
        )
        return (succeeded, self._drain_abandoned)


class _FakeWrapper:
    """Stand-in for :class:`GraphitiClient` exposing the surface the script needs."""

    def __init__(self) -> None:
        self.client_or_none = object()  # opaque "inner client"
        self.close_call_count = 0

    async def close(self) -> None:
        self.close_call_count += 1


# ---------------------------------------------------------------------------
# require_client_or_exit (AC-004)
# ---------------------------------------------------------------------------


def test_require_client_or_exit_raises_systemexit_2_on_none(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC-004 contract: client=None ⇒ SystemExit(2) + structured log."""
    with caplog.at_level(logging.ERROR, logger="study_tutor.seed"):
        with pytest.raises(SystemExit) as excinfo:
            require_client_or_exit(None)

    assert excinfo.value.code == EXIT_CLIENT_UNAVAILABLE == 2
    record = next(
        (r for r in caplog.records if getattr(r, "event", "") == "seeding_failed"),
        None,
    )
    assert record is not None, "expected event=seeding_failed log line"
    assert record.reason == "client_unavailable"


def test_require_client_or_exit_returns_client_when_present() -> None:
    """A non-None client passes through unchanged (no SystemExit)."""
    fake = _FakeWrapper()
    assert require_client_or_exit(fake) is fake


# ---------------------------------------------------------------------------
# Idempotency pre-flight (AC-003)
# ---------------------------------------------------------------------------


def test_is_already_seeded_recognises_subjects() -> None:
    state = StudentState(
        empty=False,
        student_id=STUDENT_ID,
        subjects=["English Literature"],
    )
    assert _is_already_seeded(state) is True


def test_is_already_seeded_recognises_year_group() -> None:
    state = StudentState(empty=False, student_id=STUDENT_ID, year_group=10)
    assert _is_already_seeded(state) is True


def test_is_already_seeded_recognises_confidences() -> None:
    state = StudentState(
        empty=False,
        student_id=STUDENT_ID,
        topic_confidences=[
            TopicConfidenceSnapshot(
                topic_name="Macbeth's witches",
                band="struggling",
                percentage=25,
            )
        ],
    )
    assert _is_already_seeded(state) is True


@pytest.mark.parametrize(
    "state",
    [
        None,
        StudentState(empty=True),
        StudentState(empty=False, student_id=STUDENT_ID),  # no subjects/conf
    ],
)
def test_is_already_seeded_returns_false_for_empty_states(
    state: StudentState | None,
) -> None:
    assert _is_already_seeded(state) is False


@pytest.mark.asyncio
async def test_seed_lilymay_skips_when_already_seeded(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC-003: pre-flight non-empty state ⇒ exit 0 + seeding_skipped log."""
    helper = _FakeHelper()
    wrapper = _FakeWrapper()

    async def fake_get_state(client: Any, student_id: str, **kwargs: Any) -> Any:
        return StudentState(
            empty=False,
            student_id=student_id,
            subjects=["English Literature"],
        )

    monkeypatch.setattr(seed_module, "get_student_state", fake_get_state)

    with caplog.at_level(logging.INFO, logger="study_tutor.seed"):
        rc = await seed_lilymay(wrapper, helper)

    assert rc == EXIT_OK
    assert helper.calls == [], "skipped path must not schedule any writes"
    skipped = next(
        (
            r
            for r in caplog.records
            if getattr(r, "event", "") == "seeding_skipped"
        ),
        None,
    )
    assert skipped is not None
    assert skipped.reason == "already_seeded"


# ---------------------------------------------------------------------------
# Fresh-seed happy path (AC-002, AC-006, AC-007, AC-008)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_lilymay_fresh_run_succeeds_and_uses_seed_flush_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    helper = _FakeHelper(drain_abandoned=0)
    wrapper = _FakeWrapper()

    states = iter(
        [
            StudentState(empty=True),  # pre-flight: no baseline yet
            # Post-drain verification: full baseline visible.
            StudentState(
                empty=False,
                student_id=STUDENT_ID,
                year_group=10,
                target_grade="7",
                subjects=["English Literature", "English Language"],
                topic_confidences=[
                    TopicConfidenceSnapshot(
                        topic_name=t["name"],
                        band=confidence_band_for(t["initial_percentage"]),
                        percentage=t["initial_percentage"],
                    )
                    for t in TOPICS
                ],
            ),
        ]
    )

    async def fake_get_state(client: Any, student_id: str, **kwargs: Any) -> Any:
        return next(states)

    monkeypatch.setattr(seed_module, "get_student_state", fake_get_state)

    rc = await seed_lilymay(wrapper, helper)

    assert rc == EXIT_OK
    assert helper.drain_call_count == 1
    assert helper.calls, "fresh seed must schedule writes"

    # AC-007: every schedule_write uses flush_id="SEED" — this is the
    # primary in-process check that complements the seam-test AST scan.
    assert all(
        c["flush_id"] == "SEED" for c in helper.calls
    ), f"non-SEED flush_id detected: {[c['flush_id'] for c in helper.calls]}"


@pytest.mark.asyncio
async def test_seed_lilymay_seeds_all_six_aos_with_descriptions(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-008: AO1–AO6 all present with AQA descriptions."""
    helper = _FakeHelper(drain_abandoned=0)
    wrapper = _FakeWrapper()

    states = iter(
        [
            StudentState(empty=True),
            StudentState(
                empty=False,
                student_id=STUDENT_ID,
                subjects=["English Literature"],
            ),
        ]
    )

    async def fake_get_state(client: Any, student_id: str, **kwargs: Any) -> Any:
        return next(states)

    monkeypatch.setattr(seed_module, "get_student_state", fake_get_state)

    await seed_lilymay(wrapper, helper)

    ao_episodes = [
        c["episode"]
        for c in helper.calls
        if isinstance(c["episode"], SeedBaselineEpisode)
        and c["episode"].entity_kind == "assessment_objective"
    ]
    seeded_codes = {e.entity_name for e in ao_episodes}
    assert seeded_codes == {"AO1", "AO2", "AO3", "AO4", "AO5", "AO6"}, (
        f"expected all six AOs, got {seeded_codes}"
    )

    # Each description must come from the AQA-canonical table and end up in
    # the projected episode body so the extraction LLM sees it.
    for ao_def in AOS:
        match = next((e for e in ao_episodes if e.entity_name == ao_def["code"]), None)
        assert match is not None
        body = match.to_graphiti_episode_body()
        # The first ~60 chars of the AQA description survive the projection.
        assert ao_def["description"][:40] in body
        assert "AQA" in match.description


@pytest.mark.asyncio
async def test_seed_lilymay_covers_all_three_planner_bands(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-006: at least one struggling / developing / secure topic."""
    helper = _FakeHelper(drain_abandoned=0)
    wrapper = _FakeWrapper()

    states = iter(
        [
            StudentState(empty=True),
            StudentState(empty=False, student_id=STUDENT_ID, subjects=["x"]),
        ]
    )

    async def fake_get_state(client: Any, student_id: str, **kwargs: Any) -> Any:
        return next(states)

    monkeypatch.setattr(seed_module, "get_student_state", fake_get_state)
    await seed_lilymay(wrapper, helper)

    confidence_episodes = [
        c["episode"]
        for c in helper.calls
        if isinstance(c["episode"], TopicConfidenceUpdatedEpisode)
    ]
    bands = {e.new_band for e in confidence_episodes}
    assert {"struggling", "developing", "secure"}.issubset(bands), (
        f"missing required bands; got {bands}"
    )


@pytest.mark.asyncio
async def test_seed_lilymay_topics_match_topic_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Every TOPICS row produces a Topic baseline + a confidence episode."""
    helper = _FakeHelper(drain_abandoned=0)
    wrapper = _FakeWrapper()

    states = iter([StudentState(empty=True), StudentState(empty=True)])

    async def fake_get_state(client: Any, student_id: str, **kwargs: Any) -> Any:
        return next(states)

    monkeypatch.setattr(seed_module, "get_student_state", fake_get_state)
    await seed_lilymay(wrapper, helper)

    topic_baseline_names = {
        c["episode"].entity_name
        for c in helper.calls
        if isinstance(c["episode"], SeedBaselineEpisode)
        and c["episode"].entity_kind == "topic"
    }
    confidence_topic_names = {
        c["episode"].topic_name
        for c in helper.calls
        if isinstance(c["episode"], TopicConfidenceUpdatedEpisode)
    }
    expected = {t["name"] for t in TOPICS}
    assert topic_baseline_names == expected
    assert confidence_topic_names == expected


@pytest.mark.asyncio
async def test_seed_lilymay_uses_correct_group_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Group-id discipline: student/subject/fleet — never bare literals."""
    helper = _FakeHelper(drain_abandoned=0)
    wrapper = _FakeWrapper()

    states = iter([StudentState(empty=True), StudentState(empty=True)])

    async def fake_get_state(client: Any, student_id: str, **kwargs: Any) -> Any:
        return next(states)

    monkeypatch.setattr(seed_module, "get_student_state", fake_get_state)
    await seed_lilymay(wrapper, helper)

    # Student write → student:lilymay
    student_calls = [
        c
        for c in helper.calls
        if isinstance(c["episode"], SeedBaselineEpisode)
        and c["episode"].entity_kind == "student"
    ]
    assert student_calls, "no Student write scheduled"
    assert student_calls[0]["group_ids"] == [f"{STUDENT_GROUP_PREFIX}lilymay"]

    # AO writes → fleet:appmilla
    ao_calls = [
        c
        for c in helper.calls
        if isinstance(c["episode"], SeedBaselineEpisode)
        and c["episode"].entity_kind == "assessment_objective"
    ]
    assert ao_calls, "no AO writes scheduled"
    for c in ao_calls:
        assert c["group_ids"] == [FLEET_GROUP_ID]

    # Subject writes → subject:<slug>
    subject_calls = [
        c
        for c in helper.calls
        if isinstance(c["episode"], SeedBaselineEpisode)
        and c["episode"].entity_kind == "subject"
    ]
    assert {c["group_ids"][0] for c in subject_calls} == {
        f"{SUBJECT_GROUP_PREFIX}{s['slug']}" for s in SUBJECTS
    }

    # Confidence writes → student:lilymay
    confidence_calls = [
        c
        for c in helper.calls
        if isinstance(c["episode"], TopicConfidenceUpdatedEpisode)
    ]
    for c in confidence_calls:
        assert c["group_ids"] == [f"{STUDENT_GROUP_PREFIX}lilymay"]


# ---------------------------------------------------------------------------
# Drain failure (AC-005)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_seed_lilymay_returns_exit_3_when_writes_abandoned(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC-005: any abandoned write ⇒ exit 3 + structured log w/ count."""
    helper = _FakeHelper(drain_abandoned=2)
    wrapper = _FakeWrapper()

    states = iter([StudentState(empty=True), StudentState(empty=True)])

    async def fake_get_state(client: Any, student_id: str, **kwargs: Any) -> Any:
        return next(states)

    monkeypatch.setattr(seed_module, "get_student_state", fake_get_state)

    with caplog.at_level(logging.ERROR, logger="study_tutor.seed"):
        rc = await seed_lilymay(wrapper, helper)

    assert rc == EXIT_PENDING_WRITES_ABANDONED == 3
    abandoned_log = next(
        (
            r
            for r in caplog.records
            if getattr(r, "event", "") == "seeding_pending_writes_abandoned"
        ),
        None,
    )
    assert abandoned_log is not None
    assert abandoned_log.abandoned == 2


# ---------------------------------------------------------------------------
# main() integration (AC-001, AC-002, AC-004)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_main_exits_2_when_get_client_returns_none(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """AC-004 end-to-end: main() exits 2 when the store is unreachable."""

    async def fake_get_client(config: Any) -> Any:
        return None

    monkeypatch.setattr(seed_module, "get_client", fake_get_client)

    with caplog.at_level(logging.ERROR, logger="study_tutor.seed"):
        with pytest.raises(SystemExit) as excinfo:
            await main([])

    assert excinfo.value.code == EXIT_CLIENT_UNAVAILABLE == 2


@pytest.mark.asyncio
async def test_main_returns_zero_on_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """AC-002 end-to-end: main() returns 0 on a clean fresh seed."""
    wrapper = _FakeWrapper()
    helper_holder: dict[str, _FakeHelper] = {}

    async def fake_get_client(config: Any) -> Any:
        return wrapper

    states = iter(
        [
            StudentState(empty=True),
            StudentState(
                empty=False,
                student_id=STUDENT_ID,
                subjects=["English Literature"],
            ),
        ]
    )

    async def fake_get_state(client: Any, student_id: str, **kwargs: Any) -> Any:
        return next(states)

    def fake_helper_ctor(client: Any, *args: Any, **kwargs: Any) -> _FakeHelper:
        helper = _FakeHelper(drain_abandoned=0)
        helper_holder["helper"] = helper
        return helper

    monkeypatch.setattr(seed_module, "get_client", fake_get_client)
    monkeypatch.setattr(seed_module, "get_student_state", fake_get_state)
    monkeypatch.setattr(seed_module, "GraphitiWriteHelper", fake_helper_ctor)

    rc = await main([])

    assert rc == EXIT_OK
    assert wrapper.close_call_count == 1, "main() must close the wrapper"
    assert helper_holder["helper"].drain_call_count >= 1


# ---------------------------------------------------------------------------
# CLI / config plumbing (AC-001)
# ---------------------------------------------------------------------------


def test_load_config_uses_defaults_when_path_omitted() -> None:
    cfg = load_config(None)
    assert cfg.falkor_host == DEFAULT_CONFIG["falkor_host"]
    assert cfg.falkor_port == DEFAULT_CONFIG["falkor_port"]
    assert cfg.timeout_seconds == DEFAULT_CONFIG["timeout_seconds"]


def test_load_config_overrides_via_yaml(tmp_path: Path) -> None:
    config_file = tmp_path / "seed-config.yaml"
    config_file.write_text(
        "falkor_host: example.invalid\n"
        "falkor_port: 12345\n"
        "database: alt-db\n"
        "embedder_url: http://example.invalid/v1\n"
        "timeout_seconds: 9.0\n"
    )

    cfg = load_config(config_file)

    assert cfg.falkor_host == "example.invalid"
    assert cfg.falkor_port == 12345
    assert cfg.database == "alt-db"
    assert cfg.timeout_seconds == 9.0
    # Non-overridden defaults are preserved.
    assert cfg.llm_provider == DEFAULT_CONFIG["llm_provider"]


def test_load_config_rejects_non_mapping_yaml(tmp_path: Path) -> None:
    bad = tmp_path / "bad.yaml"
    bad.write_text("- just\n- a\n- list\n")
    with pytest.raises(ValueError, match="must deserialise to a mapping"):
        load_config(bad)


def test_argparse_accepts_config_path_flag() -> None:
    """AC-001 contract: --config-path flag is wired through argparse."""
    ns = seed_module._parse_args(["--config-path", "/tmp/x.yaml"])
    assert ns.config_path == Path("/tmp/x.yaml")
    ns_default = seed_module._parse_args([])
    assert ns_default.config_path is None
