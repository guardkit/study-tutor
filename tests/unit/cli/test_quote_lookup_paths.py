"""Quote-anchored lookup through BOTH production paths (cli/main.py wiring).

docs/design/quote-lookup-by-span-2026-10-18.md — in strict mode a span the
session's retrieved chunks leave unmatched is looked up by its own words
(same subject, text scope and source filter as the session's retrieval) and
re-matched by the same matcher against the session's chunks plus that span's
own lookup chunks; still unmatched ⇒ redacted. One memoised, budgeted
lookup per reply (R1); the incident fixture (R2); off the event loop (R3).

Drives the REAL seams (``handover`` = :func:`_build_coach_handover` in
``run_turn``; ``stream`` = :func:`_build_turn_verifier_factory` in
``run_turn_stream_verified``) against an in-memory chroma-shaped collection
whose results depend on the query, and asserts every emitted delta and the
text handed to the Coach.
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable

import pytest

import study_tutor.cli.main as cli_main
from study_tutor.knowledge.corpus_models import (
    CorpusChunk,
    NovelCitationAnchor,
    PlayCitationAnchor,
)
from study_tutor.knowledge.quote_verifier import MAX_QUOTE_LOOKUPS_PER_REPLY
from study_tutor.knowledge.retrieval import register_primary_text, set_collection_provider
from tests.unit.cli.test_quote_law3_paths import (  # noqa: F401 — fixtures
    INCIDENT_FRAGMENTS,
    INCIDENT_REPLY,
    INCIDENT_SPAN,
    N,
    PATHS,
    _assert_coach_saw_what_learner_got,
    _assert_no_fragment,
    _chunk,
    _FilteringCollection,
    _matches,
    _retrieval_state,
    _run,
    _run_handover,
    _run_stream,
    _state,
    _state_from_row,
)

#: The learner message every driver sends — the session's retrieval query.
SESSION_QUERY = "ambition"

NO_SPUR = _chunk(
    "He's here in double trust. I have no spur To prick the sides of my "
    "intent, but only Vaulting ambition, which o'erleaps itself And falls on "
    "the other.",
    "macbeth",
    PlayCitationAnchor(act=1, scene=7, line=25),
    7,
)
DAGGER = _chunk(
    "Is this a dagger which I see before me, The handle toward my hand? "
    "Come, let me clutch thee.",
    "macbeth",
    PlayCitationAnchor(act=2, scene=1, line=33),
    21,
)
SPOT = _chunk(
    "Out, damned spot! out, I say! One: two: why, then, 'tis time to do't.",
    "macbeth",
    PlayCitationAnchor(act=5, scene=1, line=35),
    51,
)
INSPECTOR = _chunk(
    "We don't live alone. We are members of one body.",
    "an-inspector-calls",
    PlayCitationAnchor(act=3, scene=1, line=210),
    3,
)
#: The session's retrieved chunks: Macbeth, but NOT the "no spur" chunk
#: (the 18 Oct incident — the learner's message ranked other chunks).
SESSION_CHUNKS = [DAGGER, SPOT, INSPECTOR]

#: The literal Player output from the Dell (design § What the live deploy
#: showed, Codex R2): line breaks, no slashes.
INCIDENT_LITERAL = (
    'In Act 1 Scene 7, Macbeth says:\n\n"I have no spur\nTo prick the sides '
    "of my intent, but only\nVaulting ambition, which o'erleaps itself\nAnd "
    'falls on the other."'
)
#: Control: the same span with one invented line substituted.
INCIDENT_LITERAL_INVENTED = (
    'In Act 1 Scene 7, Macbeth says:\n\n"I have no spur\nTo prick the sides '
    "of my intent, but only\nRemorse, that when this deed is done,\nAnd "
    'falls on the other."'
)

SPUR_SPAN = "I have no spur To prick the sides of my intent"
DAGGER_SPAN = "Is this a dagger which I see before me"
FABRICATED_SPANS = (
    "Fate itself bows to the bold",
    "The crown sits heavy upon the guilty",
    "Blood will wash away no stain",
    "My conscience is a sleeping dog",
)


class _RoutingCollection(_FilteringCollection):
    """Results depend on the query: the session query gets ``session``;
    a span query gets the first ``routes`` entry whose needle it contains
    (else ``default``). Records the calling thread of every query."""

    def __init__(
        self,
        session: list[CorpusChunk],
        routes: dict[str, list[CorpusChunk]],
        default: list[CorpusChunk] | None = None,
    ) -> None:
        super().__init__([])
        self._session = session
        self._routes = routes
        self._default = default if default is not None else [SPOT]
        self.threads: list[int] = []

    def query(
        self, *, query_texts: list[str], n_results: int, where: dict[str, Any]
    ) -> dict[str, Any]:
        self.threads.append(threading.get_ident())
        query = query_texts[0]
        if query == SESSION_QUERY:
            self._chunks = self._session
        else:
            self._chunks = next(
                (c for needle, c in self._routes.items() if needle in query),
                self._default,
            )
        return super().query(query_texts=query_texts, n_results=n_results, where=where)

    @property
    def lookups(self) -> list[str]:
        return [q for q in self.queries if q != SESSION_QUERY]


def _wire(
    session: list[CorpusChunk] | None = None,
    routes: dict[str, list[CorpusChunk]] | None = None,
) -> _RoutingCollection:
    collection = _RoutingCollection(
        SESSION_CHUNKS if session is None else session,
        {"no spur": [NO_SPUR, SPOT]} if routes is None else routes,
    )
    set_collection_provider(lambda: collection)
    register_primary_text("macbeth")
    register_primary_text("an-inspector-calls")
    return collection


class _VerifySpy:
    """Wraps the production ``apply_quote_verification``: records each call's
    thread, ``lookup`` and returned text."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.threads: list[int] = []
        self.lookups: list[Any] = []
        self.outputs: list[str] = []
        real: Callable[..., Any] = cli_main.apply_quote_verification

        def spy(*args: Any, **kwargs: Any) -> Any:
            self.threads.append(threading.get_ident())
            self.lookups.append(kwargs.get("lookup"))
            result = real(*args, **kwargs)
            self.outputs.append(result[0])
            return result

        monkeypatch.setattr(cli_main, "apply_quote_verification", spy)


def _assert_prefix_stable(outputs: list[str], deltas: list[str]) -> None:
    """Every streaming pass's output is the complete release so far: each is
    a cumulative join of the deltas (or nothing new), and the last is all."""
    cumulative = {"".join(deltas[:k]) for k in range(len(deltas) + 1)}
    for output in outputs:
        assert output in cumulative, (output, deltas)
    assert outputs[-1] == "".join(deltas)


# ---------------------------------------------------------------------------
# R2 — the incident fixture: the literal Player output survives, with 1.7
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("text_name", [None, "macbeth"])
@pytest.mark.parametrize("path", PATHS)
async def test_incident_literal_output_survives_with_its_citation(
    path: str, text_name: str | None
) -> None:
    collection = _wire()

    emitted, coach = await _run(path, _state(text_name=text_name), INCIDENT_LITERAL)

    assert "".join(emitted) == INCIDENT_LITERAL + " (1.7.25)"
    assert N not in "".join(emitted)
    _assert_coach_saw_what_learner_got(emitted, coach)
    # The session query missed it; the span's own lookup found it — once.
    assert collection.queries[0] == SESSION_QUERY
    assert len(collection.lookups) == 1
    assert "I have no spur" in collection.lookups[0]


@pytest.mark.parametrize("path", PATHS)
async def test_incident_control_one_invented_line_is_redacted(path: str) -> None:
    collection = _wire()

    emitted, coach = await _run(path, _state(), INCIDENT_LITERAL_INVENTED)

    # The lookup DID return the real "no spur" chunk; the span still fails.
    assert len(collection.lookups) == 1
    assert "".join(emitted) == f"In Act 1 Scene 7, Macbeth says:\n\n{N}"
    _assert_no_fragment(emitted, coach, ("Remorse", "no spur", "falls on"))
    _assert_coach_saw_what_learner_got(emitted, coach)


@pytest.mark.parametrize("path", PATHS)
async def test_incident_control_fabricated_remorse_line_is_redacted(path: str) -> None:
    collection = _wire()

    emitted, coach = await _run(path, _state(), INCIDENT_REPLY)

    assert collection.lookups == [INCIDENT_SPAN]
    assert "".join(emitted) == (
        "Macbeth knows the murder is wrong. In his soliloquy he says "
        f"{N}. What does that tell you about his ambition?"
    )
    _assert_no_fragment(emitted, coach, INCIDENT_FRAGMENTS)
    _assert_coach_saw_what_learner_got(emitted, coach)


# ---------------------------------------------------------------------------
# Acceptance — fabricated / raising / cap / scope
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("path", PATHS)
async def test_fabricated_quote_with_unrelated_lookup_is_redacted(path: str) -> None:
    collection = _wire()
    span = FABRICATED_SPANS[1]

    emitted, coach = await _run(path, _state(), f'He says "{span}" here.')

    assert collection.lookups == [span]
    assert "".join(emitted) == f"He says {N} here."
    _assert_no_fragment(emitted, coach, ("crown",))
    _assert_coach_saw_what_learner_got(emitted, coach)


@pytest.mark.parametrize("path", PATHS)
async def test_lookup_that_raises_fails_closed(
    path: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    _wire()
    real_retrieve = cli_main.retrieve
    lookups: list[str] = []

    def retrieve(**kwargs: Any) -> Any:
        if kwargs["query"] != SESSION_QUERY:
            lookups.append(kwargs["query"])
            raise RuntimeError("embedding dimension mismatch")
        return real_retrieve(**kwargs)

    monkeypatch.setattr(cli_main, "retrieve", retrieve)
    caplog.set_level(logging.WARNING, logger="study_tutor.knowledge.quote_verifier")

    emitted, coach = await _run(path, _state(), f'He admits "{SPUR_SPAN}". Why?')

    # A genuine line, but its lookup failed: redacted, never released.
    assert lookups == [SPUR_SPAN]
    assert "".join(emitted) == f"He admits {N}. Why?"
    _assert_no_fragment(emitted, coach, ("no spur",))
    _assert_coach_saw_what_learner_got(emitted, coach)
    assert any(r.getMessage() == "quote_lookup.failed" for r in caplog.records)


@pytest.mark.parametrize("path", PATHS)
async def test_per_reply_cap_redacts_the_fifth_span_without_a_lookup(
    path: str, caplog: pytest.LogCaptureFixture
) -> None:
    # Five unmatched spans, each its own sentence (several stream passes).
    # The fifth is GENUINE — its lookup would find it — but the budget is
    # spent, so it is redacted without a lookup, on every pass.
    collection = _wire()
    spans = [*FABRICATED_SPANS, SPUR_SPAN]
    reply = "".join(f'Line {i} reads "{span}" here. ' for i, span in enumerate(spans))

    emitted, coach = await _run(path, _state(), reply)

    assert MAX_QUOTE_LOOKUPS_PER_REPLY == 4
    assert collection.lookups == list(FABRICATED_SPANS)
    assert "".join(emitted) == "".join(f"Line {i} reads {N} here. " for i in range(5))
    _assert_no_fragment(emitted, coach, ("no spur", "crown", "Fate"))
    _assert_coach_saw_what_learner_got(emitted, coach)


@pytest.mark.parametrize("text_name", [None, "macbeth"])
@pytest.mark.parametrize("path", PATHS)
async def test_lookup_uses_the_sessions_subject_and_text_scope(
    path: str, text_name: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    collection = _wire()
    real_retrieve = cli_main.retrieve
    calls: list[dict[str, Any]] = []

    def retrieve(**kwargs: Any) -> Any:
        calls.append(kwargs)
        return real_retrieve(**kwargs)

    monkeypatch.setattr(cli_main, "retrieve", retrieve)

    emitted, coach = await _run(
        path, _state(text_name=text_name), f'He admits "{SPUR_SPAN}" plainly.'
    )

    assert "".join(emitted) == f'He admits "{SPUR_SPAN}" (1.7.25) plainly.'
    _assert_coach_saw_what_learner_got(emitted, coach)
    session_call, lookup_call = calls
    assert session_call["query"] == SESSION_QUERY
    assert lookup_call == {
        "query": SPUR_SPAN,
        "text_name": text_name,
        "focus_aos": set(),
        "subject": "english",
    }
    assert session_call["text_name"] == text_name
    assert session_call["subject"] == "english"
    # Same where-filter (text scope + source filter) as the session query.
    assert collection.wheres[1] == collection.wheres[0]
    assert ("text_name" in repr(collection.wheres[1])) == (text_name is not None)


@pytest.mark.parametrize("path", PATHS)
async def test_lookup_stays_in_the_sessions_subject(path: str) -> None:
    english = _wire()
    jardin = _chunk(
        "Cela est bien dit, répondit Candide, mais il faut cultiver notre jardin.",
        "candide",
        NovelCitationAnchor(chapter=30, paragraph=12),
        30,
    )
    other = _chunk(
        "Tout est pour le mieux dans le meilleur des mondes possibles.",
        "candide",
        NovelCitationAnchor(chapter=1, paragraph=4),
        1,
    )
    french = _RoutingCollection([other], {"jardin": [jardin]})
    set_collection_provider(lambda: french, subject="french")
    register_primary_text("candide", "french")
    state = await _state_from_row("french")

    emitted, coach = await _run(
        path, state, 'Voltaire ends with "il faut cultiver notre jardin" as advice.'
    )

    assert english.queries == []
    assert french.lookups == ["il faut cultiver notre jardin"]
    assert "".join(emitted) == (
        'Voltaire ends with "il faut cultiver notre jardin" '
        "(Chapter 30, Paragraph 12) as advice."
    )
    _assert_coach_saw_what_learner_got(emitted, coach)


@pytest.mark.parametrize("path", PATHS)
async def test_no_lookup_when_the_subject_has_no_corpus(
    path: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    english = _wire()
    spy = _VerifySpy(monkeypatch)
    state = await _state_from_row("history")

    emitted, coach = await _run(path, state, f'The source says "{SPUR_SPAN}" here.')

    assert english.queries == []
    assert spy.lookups and all(lookup is None for lookup in spy.lookups)
    assert "".join(emitted) == f"The source says {N} here."
    _assert_coach_saw_what_learner_got(emitted, coach)


# ---------------------------------------------------------------------------
# R1 — stability across streaming passes
# ---------------------------------------------------------------------------


R1_REPLY = (
    "Macbeth hallucinates. "
    f'He asks "{DAGGER_SPAN}" in Act 2. '
    "That is fear. "
    f'Earlier he admits "{SPUR_SPAN}" plainly. '
    "Think about both."
)
R1_EXPECTED = (
    "Macbeth hallucinates. "
    f"He asks {N} in Act 2. "
    "That is fear. "
    f'Earlier he admits "{SPUR_SPAN}" (1.7.25) plainly. '
    "Think about both."
)


@pytest.mark.parametrize("path", PATHS)
async def test_two_quotes_each_decided_once_and_never_reclassified(
    path: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    # The dagger line is genuine, but neither the session chunks nor ITS OWN
    # lookup hold it, so it is redacted. The later spur span's lookup returns
    # the dagger chunk too — that must never reclassify the earlier,
    # already-released span (per-span chunk sets).
    collection = _wire(
        session=[SPOT, INSPECTOR],
        routes={"dagger": [SPOT], "no spur": [NO_SPUR, DAGGER]},
    )
    spy = _VerifySpy(monkeypatch)
    caplog.set_level(logging.ERROR, logger="study_tutor.tutoring.orchestrator")

    emitted, coach = await _run(path, _state(), R1_REPLY)

    assert "".join(emitted) == R1_EXPECTED
    _assert_no_fragment(emitted, coach, ("dagger",))
    _assert_coach_saw_what_learner_got(emitted, coach)
    # One lookup per distinct unmatched span, however many passes ran.
    assert collection.lookups == [DAGGER_SPAN, SPUR_SPAN]
    assert len({id(lookup) for lookup in spy.lookups}) == 1
    if path == "stream":
        assert len(emitted) >= 4
        assert len(spy.outputs) >= 5
        # The dagger decision, once made, is the same on every later pass.
        for output in spy.outputs:
            if "He asks" in output:
                assert f"He asks {N} in Act 2." in output
        _assert_prefix_stable(spy.outputs, emitted)
        assert not any("rewritten" in r.getMessage() for r in caplog.records)


@pytest.mark.parametrize("path", PATHS)
async def test_budget_exhaustion_is_stable_across_passes(
    path: str, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    collection = _wire()
    spy = _VerifySpy(monkeypatch)
    caplog.set_level(logging.ERROR, logger="study_tutor.tutoring.orchestrator")
    spans = [*FABRICATED_SPANS, SPUR_SPAN, SPUR_SPAN]
    reply = "".join(f'Line {i} reads "{span}" here. ' for i, span in enumerate(spans))

    emitted, coach = await _run(path, _state(), reply)

    assert collection.lookups == list(FABRICATED_SPANS)
    assert "".join(emitted) == "".join(
        f"Line {i} reads {N} here. " for i in range(len(spans))
    )
    _assert_coach_saw_what_learner_got(emitted, coach)
    if path == "stream":
        assert len(spy.outputs) >= len(spans)
        _assert_prefix_stable(spy.outputs, emitted)
        assert not any("rewritten" in r.getMessage() for r in caplog.records)


# ---------------------------------------------------------------------------
# R3 — off the event loop, both paths
# ---------------------------------------------------------------------------


async def test_handover_runs_off_the_event_loop_first_attempt_and_revision(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collection = _wire()
    spy = _VerifySpy(monkeypatch)
    loop_thread = threading.get_ident()

    emitted, coach = await _run_handover(
        _state(),
        f'He says "{FABRICATED_SPANS[0]}" here.',
        revision=INCIDENT_LITERAL,
    )

    assert coach == [f"He says {N} here.", INCIDENT_LITERAL + " (1.7.25)"]
    assert emitted == [coach[-1]]
    # One handover per Player attempt, each on a worker thread, each with
    # its own reply-scoped lookup; retrieval and lookups off the loop too.
    assert len(spy.threads) == 2
    assert all(thread != loop_thread for thread in spy.threads)
    assert spy.lookups[0] is not spy.lookups[1]
    assert len(collection.threads) == 4  # 2 session queries + 2 lookups
    assert all(thread != loop_thread for thread in collection.threads)


async def test_stream_every_verify_call_runs_off_the_event_loop(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collection = _wire()
    spy = _VerifySpy(monkeypatch)
    loop_thread = threading.get_ident()

    deltas, coach = await _run_stream(_state(), R1_REPLY)

    assert len(spy.threads) >= 5  # every boundary pass + the final pass
    assert all(thread != loop_thread for thread in spy.threads)
    assert collection.lookups  # a lookup was wired and used
    assert all(thread != loop_thread for thread in collection.threads)
    _assert_coach_saw_what_learner_got(deltas, coach)
