"""Subject-keyed retrieval seams (ADR-ARCH-032).

Pins the D1/D2 contract on the retrieval module: the primary-text
registry and collection providers are keyed by subject with ``english``
as the default everywhere (pre-multi-subject callers unchanged), and
``retrieve`` routes to exactly the requested subject's collection —
never another subject's (the no-cross-subject-fallback invariant).
"""

from typing import Any

import pytest

from study_tutor.knowledge.retrieval import (
    DEFAULT_SUBJECT,
    REASON_NO_PRIMARY,
    REASON_RETRIEVE_PRIMARY,
    clear_primary_text_index,
    get_collection_provider,
    has_corpus,
    has_primary_text,
    register_primary_text,
    reset_collection_provider,
    reset_embedder_probe,
    reset_reranker_factory,
    retrieve,
    set_collection_provider,
    should_retrieve,
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
    """Duck-typed chroma collection that records query calls, returns empty."""

    def __init__(self) -> None:
        self.query_calls: list[dict[str, Any]] = []

    def query(self, **kwargs: Any) -> dict[str, Any]:
        self.query_calls.append(kwargs)
        return {"metadatas": [[]], "documents": [[]], "distances": [[]]}


def test_default_subject_is_the_contract_value() -> None:
    """The knowledge layer's default matches the SUBJECT_DEFAULT contract."""
    assert DEFAULT_SUBJECT == "english"


def test_registry_is_subject_keyed_with_english_default() -> None:
    register_primary_text("macbeth")  # default → english
    register_primary_text("candide", "french")

    assert has_primary_text("macbeth")
    assert has_primary_text("macbeth", "english")
    assert not has_primary_text("macbeth", "french")
    assert has_primary_text("candide", "french")
    assert not has_primary_text("candide")  # english index has no candide


def test_register_primary_text_rejects_empty_subject() -> None:
    with pytest.raises(ValueError):
        register_primary_text("macbeth", "")


def test_clear_primary_text_index_clears_all_subjects() -> None:
    register_primary_text("macbeth")
    register_primary_text("candide", "french")
    clear_primary_text_index()
    assert not has_primary_text("macbeth")
    assert not has_primary_text("candide", "french")


def test_collection_providers_are_subject_keyed() -> None:
    english = _RecordingCollection()
    french = _RecordingCollection()
    set_collection_provider(lambda: english)  # default → english
    set_collection_provider(lambda: french, subject="french")

    assert get_collection_provider()() is english
    assert get_collection_provider("french")() is french
    assert get_collection_provider("chemistry") is None
    assert has_corpus("english")
    assert has_corpus("french")
    assert not has_corpus("chemistry")

    reset_collection_provider()
    assert not has_corpus("english")
    assert not has_corpus("french")


def test_set_collection_provider_rejects_empty_subject() -> None:
    with pytest.raises(ValueError):
        set_collection_provider(lambda: None, subject="")


def test_retrieve_routes_to_the_requested_subjects_collection() -> None:
    english = _RecordingCollection()
    french = _RecordingCollection()
    set_collection_provider(lambda: english)
    set_collection_provider(lambda: french, subject="french")

    retrieve("ou est le poignard", "candide", set(), subject="french")

    assert len(french.query_calls) == 1
    assert english.query_calls == []  # never the other subject's corpus


def test_retrieve_returns_empty_for_unwired_subject() -> None:
    english = _RecordingCollection()
    set_collection_provider(lambda: english)

    chunks = retrieve("query", "candide", set(), subject="french")

    assert chunks == []
    assert english.query_calls == []  # no cross-subject fallback


def test_should_retrieve_consults_the_subjects_registry() -> None:
    register_primary_text("candide", "french")

    default_decision = should_retrieve("candide", {"AO1"})
    french_decision = should_retrieve("candide", {"AO1"}, "french")

    assert default_decision.reason is REASON_NO_PRIMARY
    assert french_decision.reason is REASON_RETRIEVE_PRIMARY
    assert french_decision.retrieve
