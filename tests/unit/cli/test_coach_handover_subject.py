"""The coach-handover closure's subject threading + coverage check (ADR-ARCH-032 D3).

Drives the real ``_build_coach_handover`` closure with stub session
states and asserts the retrieval-skip envelope: a subject with no wired
collection skips with ``REASON_NO_SUBJECT_CORPUS`` (never falling back
to another subject's corpus), an absent/empty subject resolves to the
shared default, and a covered subject proceeds into the normal
decision/retrieve path keyed by that subject.
"""

from types import SimpleNamespace
from typing import Any

import pytest

from study_tutor.cli.main import _build_coach_handover
from study_tutor.knowledge.retrieval import (
    REASON_NO_PRIMARY,
    REASON_NO_SUBJECT_CORPUS,
    clear_primary_text_index,
    register_primary_text,
    reset_collection_provider,
    reset_embedder_probe,
    reset_reranker_factory,
    set_collection_provider,
)


@pytest.fixture(autouse=True)
def _reset_retrieval_module_state() -> None:
    clear_primary_text_index()
    reset_embedder_probe()
    reset_collection_provider()
    reset_reranker_factory()
    yield
    clear_primary_text_index()
    reset_embedder_probe()
    reset_collection_provider()
    reset_reranker_factory()


class _RecordingCollection:
    def __init__(self) -> None:
        self.query_calls: list[dict[str, Any]] = []

    def query(self, **kwargs: Any) -> dict[str, Any]:
        self.query_calls.append(kwargs)
        return {"metadatas": [[]], "documents": [[]], "distances": [[]]}


def _state(**kwargs: Any) -> SimpleNamespace:
    defaults: dict[str, Any] = {
        "text_name": "macbeth",
        "focus_aos": ("AO1",),
    }
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_uncovered_subject_skips_with_no_subject_corpus_reason() -> None:
    set_collection_provider(lambda: _RecordingCollection())  # english only
    register_primary_text("macbeth")  # english's registry

    handover = _build_coach_handover()
    _, metadata = handover("the response", "a question", _state(subject="french"))

    assert metadata.retrieval_skipped_reason == REASON_NO_SUBJECT_CORPUS


def test_uncovered_subject_never_queries_another_subjects_collection() -> None:
    english = _RecordingCollection()
    set_collection_provider(lambda: english)
    register_primary_text("macbeth")

    handover = _build_coach_handover()
    handover("the response", "a question", _state(subject="french"))

    assert english.query_calls == []


def test_missing_subject_attr_falls_back_to_default_subject() -> None:
    """A session state minted before subject threading resolves to english.

    The english provider IS wired here, so the coverage check passes and
    the closure reaches the four-branch decision — which skips with
    ``no_primary_text`` for an unregistered text. Reaching THAT reason
    (not ``no_corpus_for_subject``) proves the default-subject fallback.
    """
    set_collection_provider(lambda: _RecordingCollection())

    handover = _build_coach_handover()
    _, metadata = handover(
        "the response", "a question", _state(text_name="unregistered-text")
    )

    assert metadata.retrieval_skipped_reason == REASON_NO_PRIMARY


def test_empty_subject_falls_back_to_default_subject() -> None:
    set_collection_provider(lambda: _RecordingCollection())

    handover = _build_coach_handover()
    _, metadata = handover(
        "the response",
        "a question",
        _state(text_name="unregistered-text", subject=""),
    )

    assert metadata.retrieval_skipped_reason == REASON_NO_PRIMARY


def test_covered_subject_retrieves_from_its_own_collection() -> None:
    english = _RecordingCollection()
    french = _RecordingCollection()
    set_collection_provider(lambda: english)
    set_collection_provider(lambda: french, subject="french")
    register_primary_text("candide", "french")

    handover = _build_coach_handover()
    _, metadata = handover(
        "the response",
        "a question",
        _state(text_name="candide", subject="french"),
    )

    # Retrieval RAN (no skip reason) against french's collection only.
    assert metadata.retrieval_skipped_reason is None
    assert len(french.query_calls) == 1
    assert english.query_calls == []
