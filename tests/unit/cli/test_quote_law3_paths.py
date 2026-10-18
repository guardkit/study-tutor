"""Mission law 3 through BOTH production paths (cli/main.py wiring).

docs/design/quote-law3-no-unverified-quote-2026-10-18.md — Q1 (strict
verification: unmatched / short / unterminated quotes redacted, verifier
exceptions fail closed) and Q2 (no set text ⇒ verify against all of the
subject's primary texts; the session's subject reaches the verifier).

Every test drives the REAL production seams:

* ``handover`` — :func:`_build_coach_handover` wired into
  :meth:`PlayerCoachOrchestrator.run_turn` (the non-streaming path);
* ``stream`` — :func:`_build_turn_verifier_factory` wired into
  :meth:`PlayerCoachOrchestrator.run_turn_stream_verified` (the WS/voice
  path),

against an in-memory chroma-shaped collection, and asserts every emitted
delta AND the text handed to the Coach (which must equal what the learner
received).
"""

from __future__ import annotations

import asyncio
import logging
import re
import time
from typing import Any, AsyncIterator
from unittest.mock import AsyncMock, MagicMock

import pytest

from study_tutor.cli.main import _build_coach_handover, _build_turn_verifier_factory
from study_tutor.knowledge.corpus_models import (
    CorpusChunk,
    NovelCitationAnchor,
    PlayCitationAnchor,
    SourceType,
)
from study_tutor.knowledge.quote_verifier import UNVERIFIED_QUOTE_TEXT
from study_tutor.knowledge.retrieval import (
    CHUNK_PAYLOAD_KEY,
    clear_primary_text_index,
    register_primary_text,
    reset_collection_provider,
    reset_embedder_probe,
    reset_reranker_factory,
    set_collection_provider,
    set_reranker_factory,
)
from study_tutor.session.service import SessionService
from study_tutor.tutoring.adapters.session_state import SessionState
from study_tutor.tutoring.coach import CoachVerdict, CriterionScore, RubricFeedback
from study_tutor.tutoring.orchestrator import (
    FINAL_VERIFICATION_FALLBACK,
    PlayerCoachOrchestrator,
)
from tests.unit.knowledge.store.fakes import FakeStudentStore

N = UNVERIFIED_QUOTE_TEXT
PATHS = ("handover", "stream")

#: The fabricated "quotation" delivered on 18 Oct 2026 (robot session, no set
#: text): the Player's span as the verifier received it.
INCIDENT_SPAN = (
    "I have no spur / To prick the sides of my intent, but only / Remorse, "
    "that when this deed is done, / Makes ne'er so much the trống than makes "
    "me thus a backwardly"
)
INCIDENT_REPLY = (
    "Macbeth knows the murder is wrong. In his soliloquy he says "
    f'"{INCIDENT_SPAN}". What does that tell you about his ambition?'
)
INCIDENT_FRAGMENTS = ("Remorse", "trống", "backwardly", "no spur", "perhaps")

REAL_MACBETH = "Vaulting ambition, which o'erleaps itself"


# ---------------------------------------------------------------------------
# Corpus + collection fakes
# ---------------------------------------------------------------------------


def _chunk(
    text: str,
    text_name: str,
    anchor: Any,
    index: int,
    source_type: SourceType = SourceType.PRIMARY_TEXT,
) -> CorpusChunk:
    return CorpusChunk(
        text=text,
        source_type=source_type,
        source_path=f"/corpus/{text_name}/{index}.txt",
        text_name=text_name,
        citation_anchor=anchor,
        chunk_index=index,
    )


ENGLISH_CHUNKS = [
    _chunk(
        "I have no spur\nTo prick the sides of my intent, but only\n"
        "Vaulting ambition, which o'erleaps itself\nAnd falls on th' other.",
        "macbeth",
        PlayCitationAnchor(act=1, scene=7, line=25),
        7,
    ),
    _chunk(
        "We don't live alone. We are members of one body.",
        "an-inspector-calls",
        PlayCitationAnchor(act=3, scene=1, line=210),
        3,
    ),
]
FRENCH_CHUNKS = [
    _chunk(
        "Cela est bien dit, répondit Candide, mais il faut cultiver notre jardin.",
        "candide",
        NovelCitationAnchor(chapter=30, paragraph=12),
        30,
    ),
]


class _FilteringCollection:
    """Chroma-shaped collection: applies ``where`` in memory, records it."""

    def __init__(self, chunks: list[CorpusChunk]) -> None:
        self._chunks = chunks
        self.wheres: list[dict[str, Any]] = []
        self.queries: list[str] = []

    def query(
        self, *, query_texts: list[str], n_results: int, where: dict[str, Any]
    ) -> dict[str, Any]:
        self.wheres.append(where)
        self.queries.extend(query_texts)
        hits = [c for c in self._chunks if _matches(c, where)][:n_results]
        return {
            "documents": [[c.text for c in hits]],
            "metadatas": [[{CHUNK_PAYLOAD_KEY: c.model_dump_json()} for c in hits]],
            "distances": [[float(i) for i, _ in enumerate(hits)]],
        }


def _matches(chunk: CorpusChunk, where: dict[str, Any]) -> bool:
    if "$and" in where:
        return all(_matches(chunk, clause) for clause in where["$and"])
    for field, condition in where.items():
        value = chunk.source_type.value if field == "source_type" else getattr(
            chunk, field
        )
        if isinstance(condition, dict):
            if value not in condition["$in"]:
                return False
        elif value != condition:
            return False
    return True


@pytest.fixture(autouse=True)
def _retrieval_state() -> Any:
    clear_primary_text_index()
    reset_embedder_probe()
    reset_collection_provider()

    def _no_reranker() -> Any:
        raise ImportError("sentence_transformers not installed")

    set_reranker_factory(_no_reranker)
    yield
    clear_primary_text_index()
    reset_embedder_probe()
    reset_collection_provider()
    reset_reranker_factory()


@pytest.fixture
def english() -> _FilteringCollection:
    collection = _FilteringCollection(ENGLISH_CHUNKS)
    set_collection_provider(lambda: collection)
    register_primary_text("macbeth")
    register_primary_text("an-inspector-calls")
    return collection


def _state(text_name: str | None = None, subject: str = "english") -> SessionState:
    return SessionState(
        session_id="s-1",
        student_id="suite-runner",
        text_name=text_name,
        focus_aos=("AO1", "AO2"),
        subject=subject,
    )


# ---------------------------------------------------------------------------
# Path drivers — return (emitted deltas, texts handed to the Coach)
# ---------------------------------------------------------------------------


def _verdict(decision: str, total: float) -> CoachVerdict:
    return CoachVerdict(
        weighted_total=total,
        decision=decision,  # type: ignore[arg-type]
        criterion_scores=[CriterionScore(criterion_id="c1", score=total, evidence="e")],
        rubric_feedback=(
            [RubricFeedback(criterion_id="c1", suggested_focus="x", target_score=0.8)]
            if decision == "revise"
            else []
        ),
        misconceptions=[],
        reasoning="",
    )


async def _run_handover(
    state: Any, reply: str, revision: str | None = None
) -> tuple[list[str], list[str]]:
    """run_turn with the production handover closure.

    With ``revision`` the Coach runs synchronously (the pre-send gate) and
    asks for one revision, so both the first attempt and the revision are
    verified; otherwise production's async-Coach configuration is used.
    """
    player = MagicMock()
    player.respond = AsyncMock(return_value=reply)
    player.revise = AsyncMock(return_value=revision)
    coach = MagicMock()
    coach.evaluate = AsyncMock(
        side_effect=[_verdict("revise", 0.2), _verdict("accept", 0.9)]
    )
    orch = PlayerCoachOrchestrator(
        player=player,
        coach=coach,
        coach_handover=_build_coach_handover(),
        coach_evaluation="sync" if revision is not None else "async",
    )
    dispatched = MagicMock()
    orch._dispatch_async_coach = dispatched  # type: ignore[method-assign]

    result = await orch.run_turn(session_state=state, learner_message="ambition")

    coach_inputs = [c.kwargs["player_response"] for c in coach.evaluate.call_args_list]
    coach_inputs += [c.kwargs["player_response"] for c in dispatched.call_args_list]
    return [result.response], coach_inputs


async def _run_stream(state: Any, reply: str) -> tuple[list[str], list[str]]:
    """run_turn_stream_verified with the production per-turn verifier factory."""
    tokens = re.findall(r"\S+\s*", reply)
    player = MagicMock()

    async def respond_stream(
        *, session_state: Any, learner_message: str
    ) -> AsyncIterator[str]:
        for token in tokens:
            yield token

    player.respond_stream = respond_stream
    orch = PlayerCoachOrchestrator(
        player=player,
        coach=MagicMock(),
        turn_verifier_factory=_build_turn_verifier_factory(),
        coach_evaluation="async",
    )
    dispatched = MagicMock()
    orch._dispatch_async_coach = dispatched  # type: ignore[method-assign]

    deltas = [
        delta
        async for delta in orch.run_turn_stream_verified(
            session_state=state, learner_message="ambition"
        )
    ]
    await asyncio.sleep(0)
    return deltas, [c.kwargs["player_response"] for c in dispatched.call_args_list]


async def _run(path: str, state: Any, reply: str) -> tuple[list[str], list[str]]:
    if path == "handover":
        return await _run_handover(state, reply)
    return await _run_stream(state, reply)


def _assert_coach_saw_what_learner_got(emitted: list[str], coach: list[str]) -> None:
    assert coach == ["".join(emitted)]


def _assert_no_fragment(emitted: list[str], coach: list[str], fragments: Any) -> None:
    for text in [*emitted, *coach]:
        for fragment in fragments:
            assert fragment not in text, (fragment, text)


# ---------------------------------------------------------------------------
# (6) No set text: all primary texts, real quote survives, invented one goes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", PATHS)
async def test_no_text_name_retrieves_all_texts_and_redacts_invented_line(
    path: str, english: _FilteringCollection, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.INFO, logger="study_tutor.cli.main")
    reply = (
        f'Macbeth admits "{REAL_MACBETH}". Earlier he says "{INCIDENT_SPAN}". '
        "Think about it."
    )

    emitted, coach = await _run(path, _state(text_name=None), reply)

    # The session's query once; then (quote-lookup design) the unmatched
    # span's own lookup once, in the same scope — no text-name filter
    # (source-type filter only).
    assert english.queries == ["ambition", INCIDENT_SPAN]
    assert english.wheres[1] == english.wheres[0]
    assert "text_name" not in repr(english.wheres[0])
    assert "source_type" in english.wheres[0]
    assert "".join(emitted) == (
        f'Macbeth admits "{REAL_MACBETH}" (1.7.25). Earlier he says {N}. '
        "Think about it."
    )
    _assert_no_fragment(emitted, coach, INCIDENT_FRAGMENTS)
    _assert_coach_saw_what_learner_got(emitted, coach)
    assert any(
        "scope=all_primary_texts" in r.getMessage()
        and "reason=no_text_name" in r.getMessage()
        for r in caplog.records
    )
    assert not any("retrieval_mode=skipped" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("path", PATHS)
async def test_no_text_name_quote_from_another_set_text_is_primary(
    path: str, english: _FilteringCollection
) -> None:
    reply = 'Priestley warns "We are members of one body" at the end.'

    emitted, coach = await _run(path, _state(text_name=None), reply)

    assert "".join(emitted) == (
        'Priestley warns "We are members of one body" (3.1.210) at the end.'
    )
    _assert_coach_saw_what_learner_got(emitted, coach)


# ---------------------------------------------------------------------------
# (7) The streamed no-text session never releases the invented line
# ---------------------------------------------------------------------------


async def test_stream_no_text_session_never_releases_fabricated_line(
    english: _FilteringCollection,
) -> None:
    deltas, coach = await _run_stream(_state(text_name=None), INCIDENT_REPLY)

    # Released at sentence boundaries — the safe first sentence went first.
    assert deltas[0] == "Macbeth knows the murder is wrong. "
    assert len(deltas) >= 2
    _assert_no_fragment(deltas, coach, INCIDENT_FRAGMENTS)
    _assert_coach_saw_what_learner_got(deltas, coach)


# ---------------------------------------------------------------------------
# (8) Incident regression, both paths
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", PATHS)
async def test_incident_reply_regression(
    path: str, english: _FilteringCollection
) -> None:
    emitted, coach = await _run(path, _state(text_name=None), INCIDENT_REPLY)

    assert "".join(emitted) == (
        "Macbeth knows the murder is wrong. In his soliloquy he says "
        f"{N}. What does that tell you about his ambition?"
    )
    _assert_no_fragment(emitted, coach, INCIDENT_FRAGMENTS)
    _assert_coach_saw_what_learner_got(emitted, coach)


@pytest.mark.parametrize("path", PATHS)
async def test_set_text_session_also_redacts_the_invented_line(
    path: str, english: _FilteringCollection
) -> None:
    """Law 3 makes no exception for sessions that have a set text."""
    emitted, coach = await _run(path, _state(text_name="macbeth"), INCIDENT_REPLY)

    assert {"text_name": "macbeth"} in english.wheres[0]["$and"]
    _assert_no_fragment(emitted, coach, INCIDENT_FRAGMENTS)
    assert N in "".join(emitted)
    _assert_coach_saw_what_learner_got(emitted, coach)


# ---------------------------------------------------------------------------
# R1 — short (1-3 word) spans: exact match survives, anything else redacted
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text_name", [None, "macbeth"])
@pytest.mark.parametrize("path", PATHS)
async def test_short_spans_exact_survives_unmatched_redacted(
    path: str, text_name: str | None, english: _FilteringCollection
) -> None:
    reply = 'He fears "Vaulting ambition" most. He is called "bloody tyrant" too.'

    emitted, coach = await _run(path, _state(text_name=text_name), reply)

    assert "".join(emitted) == (
        f'He fears "Vaulting ambition" (1.7.25) most. He is called {N} too.'
    )
    _assert_no_fragment(emitted, coach, ("bloody tyrant",))
    _assert_coach_saw_what_learner_got(emitted, coach)


# ---------------------------------------------------------------------------
# R2 — an unterminated quote at the end, after an already-released sentence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("opening", ['"', "“"])
@pytest.mark.parametrize("path", PATHS)
async def test_unterminated_quote_at_end_is_redacted(
    path: str, opening: str, english: _FilteringCollection
) -> None:
    reply = (
        "A metaphor compares directly. "
        f"Then he says {opening}I have no spur. To prick the sides of my"
    )

    emitted, coach = await _run(path, _state(text_name=None), reply)

    assert "".join(emitted) == f"A metaphor compares directly. Then he says {N}"
    if path == "stream":
        # The safe sentence was released before the open quote arrived and
        # is never retracted; the open quote was held, then redacted.
        assert emitted[0] == "A metaphor compares directly. "
    _assert_no_fragment(emitted, coach, ("no spur", "prick", opening))
    _assert_coach_saw_what_learner_got(emitted, coach)


class _SlowCollection(_FilteringCollection):
    """Retrieval that is still pending when the Player's stream ends."""

    def query(self, **kwargs: Any) -> dict[str, Any]:
        time.sleep(0.3)
        return super().query(**kwargs)


@pytest.mark.parametrize("opening", ['"', "“"])
async def test_stream_unterminated_quote_with_retrieval_still_pending(
    opening: str,
) -> None:
    # Codex implementation review R1: no releasable boundary before the open
    # quote, and generation finishes while the verifier is still being built
    # (retrieval pending). The final pass must still verify and redact.
    collection = _SlowCollection(ENGLISH_CHUNKS)
    set_collection_provider(lambda: collection)
    register_primary_text("macbeth")
    reply = f"Then he says {opening}I have no spur to prick the sides of my"

    emitted, coach = await _run_stream(_state(text_name=None), reply)

    assert "".join(emitted) == f"Then he says {N}"
    _assert_no_fragment(emitted, coach, ("no spur", "prick", opening))
    _assert_coach_saw_what_learner_got(emitted, coach)


# ---------------------------------------------------------------------------
# R3 — a verifier exception releases no quoted text (first attempt + revision)
# ---------------------------------------------------------------------------


def _verifier_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    def _boom(*args: Any, **kwargs: Any) -> Any:
        raise RuntimeError("simulated verifier failure")

    monkeypatch.setattr("study_tutor.knowledge.coach_handover.verify_quotes", _boom)


async def test_handover_verifier_exception_first_attempt_and_revision(
    monkeypatch: pytest.MonkeyPatch, english: _FilteringCollection
) -> None:
    _verifier_raises(monkeypatch)
    first = f'He says "{INCIDENT_SPAN}" here.'
    revision = f'Revised: he says “{REAL_MACBETH}” and then "an open one'

    emitted, coach = await _run_handover(
        _state(text_name=None), first, revision=revision
    )

    # Both attempts reached the Coach fully redacted; the released reply is
    # the accepted revision, identical to what the Coach evaluated.
    assert coach == [f"He says {N} here.", f"Revised: he says {N} and then {N}"]
    assert emitted == [coach[-1]]
    _assert_no_fragment(
        emitted, coach, (*INCIDENT_FRAGMENTS, "Vaulting", "open one", '"', "“")
    )


async def test_handover_verifier_exception_async_production_config(
    monkeypatch: pytest.MonkeyPatch, english: _FilteringCollection
) -> None:
    _verifier_raises(monkeypatch)

    emitted, coach = await _run_handover(_state(text_name=None), INCIDENT_REPLY)

    assert emitted == [
        "Macbeth knows the murder is wrong. In his soliloquy he says "
        f"{N}. What does that tell you about his ambition?"
    ]
    _assert_coach_saw_what_learner_got(emitted, coach)


async def test_stream_verifier_exception_releases_no_quoted_text(
    monkeypatch: pytest.MonkeyPatch, english: _FilteringCollection
) -> None:
    _verifier_raises(monkeypatch)

    deltas, coach = await _run_stream(_state(text_name=None), INCIDENT_REPLY)

    assert deltas == [FINAL_VERIFICATION_FALLBACK]
    _assert_no_fragment(deltas, coach, INCIDENT_FRAGMENTS)
    _assert_coach_saw_what_learner_got(deltas, coach)


# ---------------------------------------------------------------------------
# R4 — the session's subject reaches the verifier (real build_turn_session_state)
# ---------------------------------------------------------------------------


async def _state_from_row(subject: str) -> SessionState:
    store = FakeStudentStore()
    store._students["suite-runner"] = {
        "name": "Suite Runner",
        "year_group": 10,
        "target_grade": None,
    }
    record, _ = await store.create_session(student_id="suite-runner", subject=subject)
    return await SessionService(store=store).build_turn_session_state(
        student_id="suite-runner", session_id=record.session_id
    )


@pytest.mark.parametrize("path", PATHS)
async def test_wired_non_english_subject_queries_only_its_own_collection(
    path: str, english: _FilteringCollection
) -> None:
    french = _FilteringCollection(FRENCH_CHUNKS)
    set_collection_provider(lambda: french, subject="french")
    register_primary_text("candide", "french")
    state = await _state_from_row("french")
    assert state.subject == "french" and state.text_name is None

    reply = 'Voltaire ends with "il faut cultiver notre jardin" as advice.'
    emitted, coach = await _run(path, state, reply)

    assert len(french.wheres) == 1
    assert "text_name" not in repr(french.wheres[0])
    assert english.wheres == []
    assert "".join(emitted) == (
        'Voltaire ends with "il faut cultiver notre jardin" '
        "(Chapter 30, Paragraph 12) as advice."
    )
    _assert_coach_saw_what_learner_got(emitted, coach)


@pytest.mark.parametrize("path", PATHS)
async def test_unwired_subject_never_queries_english(
    path: str, english: _FilteringCollection
) -> None:
    state = await _state_from_row("history")
    assert state.subject == "history"

    # A genuine English line, but this is a history session with no corpus:
    # it cannot be verified here, so it is redacted — never checked against
    # another subject's collection.
    reply = f'The source says "{REAL_MACBETH}" here.'
    emitted, coach = await _run(path, state, reply)

    assert english.wheres == []
    assert "".join(emitted) == f"The source says {N} here."
    _assert_coach_saw_what_learner_got(emitted, coach)
