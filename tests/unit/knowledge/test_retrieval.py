"""Unit + seam tests for the retrieval module (decision + retrieve).

Covers the acceptance criteria of TASK-PRV-003 (R2 + R3):

  * AC-001..AC-004: the four decision branches.
  * AC-005: AO3-only with empty ``context_historical`` still bypasses.
  * AC-006: embedder timeout override → ``REASON_EMBEDDER_TIMEOUT``.
  * AC-007: reason values are module-level constants (identity check).

And the acceptance criteria of TASK-PRV-004 (source-filtered retrieval):

  * Primary-first ordering at equal score.
  * Top-K boundary (0 / 3 / 6 / 7 available → 0 / 3 / 6 / 6 returned).
  * Empty corpus for a ``text_name`` returns ``[]``.
  * Reranker import-failure path returns chunks without rerank, sets
    ``mode="no_rerank"``.
  * AQA-pattern filename in metadata is filtered out at retrieval-time
    even if it slipped past ingestion.
  * ``CONTEXT_HISTORICAL`` is excluded by the where-filter for non-AO3
    turns.

Plus the seam test from the task spec, which validates the
``RetrievalDecision`` contract consumed by TASK-PRV-004 (skips retrieval
if ``retrieve=False``) and TASK-PRV-006 (forwards reason into
``VerifierMetadata``), and the seam test for TASK-PRV-004's
``SourceTypedCorpus`` contract.

Tests use the public registration / probe helpers
(``register_primary_text``, ``clear_primary_text_index``,
``set_embedder_probe``, ``reset_embedder_probe``,
``set_collection_provider``, ``set_reranker_factory``) rather than poking
at the underscore-prefixed module state directly. A ``conftest``-style
autouse fixture isolates each test from the others.
"""

from __future__ import annotations

import time
from typing import Any, Callable

import pytest

from study_tutor.knowledge.corpus_models import (
    CorpusChunk,
    PlayCitationAnchor,
    SourceType,
)
from study_tutor.knowledge.retrieval import (
    CHUNK_PAYLOAD_KEY,
    DEFAULT_TOP_K,
    EMBEDDER_TIMEOUT_SECONDS,
    MODE_NO_RERANK,
    MODE_RERANK,
    NON_AO3_SOURCE_TYPES,
    REASON_AO3_ONLY,
    REASON_EMBEDDER_TIMEOUT,
    REASON_NO_PRIMARY,
    REASON_RETRIEVE_MIXED,
    REASON_RETRIEVE_PRIMARY,
    RERANKER_MODEL,
    RetrievalDecision,
    clear_primary_text_index,
    decide_retrieval,
    embedder_available_within,
    get_last_retrieval_mode,
    has_primary_text,
    register_primary_text,
    reset_collection_provider,
    reset_embedder_probe,
    reset_reranker_factory,
    retrieve,
    set_collection_provider,
    set_embedder_probe,
    set_reranker_factory,
    should_retrieve,
)


# ---------------------------------------------------------------------------
# Fixtures: isolate module-level mutable state between cases
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_retrieval_module_state() -> None:
    """Reset all retrieval-module mutable state before AND after each test.

    The retrieval module keeps four pieces of mutable state — the
    primary-text index, the embedder probe, the collection provider, and
    the reranker factory. All are explicitly designed for test injection,
    but only if tests reset them — so we do that automatically.
    """
    clear_primary_text_index()
    reset_embedder_probe()
    reset_collection_provider()
    reset_reranker_factory()
    yield
    clear_primary_text_index()
    reset_embedder_probe()
    reset_collection_provider()
    reset_reranker_factory()


def _install_fast_probe() -> None:
    """Install a no-op probe so embedder checks never trigger fallback."""
    set_embedder_probe(lambda: None)


def _install_slow_probe(sleep_s: float) -> None:
    """Install a probe that sleeps ``sleep_s`` seconds (timeout simulation)."""

    def slow() -> None:
        time.sleep(sleep_s)

    set_embedder_probe(slow)


def _install_raising_probe(exc: Exception) -> None:
    """Install a probe that raises (embedder is down, not just slow)."""

    def boom() -> None:
        raise exc

    set_embedder_probe(boom)


# ---------------------------------------------------------------------------
# AC-001..AC-004 + AC-006: parametrised five-case decision matrix
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id,setup,text_name,focus_aos,expected",
    [
        # Branch 1: AO3-only → bypass (regardless of corpus contents).
        (
            "ao3_only_bypass",
            lambda: (register_primary_text("Macbeth"), _install_fast_probe()),
            "Macbeth",
            {"AO3"},
            RetrievalDecision(False, REASON_AO3_ONLY, "ao3_bypass"),
        ),
        # Branch 2: no primary text in corpus → analysis-mode.
        (
            "no_primary_text",
            lambda: (_install_fast_probe(),),
            "UnknownWork",
            {"AO1", "AO2"},
            RetrievalDecision(False, REASON_NO_PRIMARY, "analysis_mode"),
        ),
        # Branch 3: mixed AO3 + AO1/AO2 → retrieve, mode="mixed".
        (
            "mixed_ao3",
            lambda: (
                register_primary_text("Macbeth"),
                _install_fast_probe(),
            ),
            "Macbeth",
            {"AO1", "AO2", "AO3"},
            RetrievalDecision(True, REASON_RETRIEVE_MIXED, "mixed"),
        ),
        # Branch 4: primary present, non-AO3-only → retrieve primary.
        (
            "primary_present",
            lambda: (
                register_primary_text("Macbeth"),
                _install_fast_probe(),
            ),
            "Macbeth",
            {"AO1", "AO2"},
            RetrievalDecision(True, REASON_RETRIEVE_PRIMARY, "retrieve"),
        ),
        # AC-006: embedder timeout overrides any four-branch outcome.
        (
            "embedder_timeout_override",
            lambda: (
                register_primary_text("Macbeth"),
                # Probe sleeps just past the budget — guaranteed timeout.
                _install_slow_probe(EMBEDDER_TIMEOUT_SECONDS + 0.05),
            ),
            "Macbeth",
            {"AO1", "AO2"},
            RetrievalDecision(False, REASON_EMBEDDER_TIMEOUT, "analysis_mode"),
        ),
    ],
)
def test_decide_retrieval_decision_matrix(
    case_id: str,
    setup: Callable[[], object],
    text_name: str,
    focus_aos: set[str],
    expected: RetrievalDecision,
) -> None:
    """All five decision cases route as specified by R2 + R3."""
    setup()
    assert decide_retrieval(text_name, focus_aos) == expected, case_id


# ---------------------------------------------------------------------------
# AC-005: AO3-only with empty context_historical/ still bypasses
# ---------------------------------------------------------------------------


def test_ao3_only_bypasses_even_when_primary_indexed() -> None:
    """The AO3-only short-circuit comes BEFORE the primary-text check.

    The @edge-case scenario for "empty context-historical" reduces to
    this: regardless of what the corpus contains, ``focus_aos == {"AO3"}``
    must yield bypass. Asserting against an indexed primary covers the
    scenario directly — the empty-context-historical folder is just a
    different shape of "corpus contents that should not influence the
    AO3-only branch".
    """
    register_primary_text("Macbeth")

    decision = should_retrieve("Macbeth", {"AO3"})

    assert decision.retrieve is False
    assert decision.mode == "ao3_bypass"
    assert decision.reason is REASON_AO3_ONLY


def test_ao3_only_bypasses_with_empty_corpus() -> None:
    """And of course it bypasses when nothing is indexed at all."""
    decision = should_retrieve("AnythingAtAll", {"AO3"})

    assert decision == RetrievalDecision(False, REASON_AO3_ONLY, "ao3_bypass")


# ---------------------------------------------------------------------------
# AC-006 (direct): embedder probe with sleep > 5s triggers analysis-mode
# ---------------------------------------------------------------------------


def test_embedder_probe_sleep_over_budget_triggers_override() -> None:
    """When the probe sleeps past EMBEDDER_TIMEOUT_SECONDS, decide_retrieval
    returns the timeout decision regardless of the four-branch outcome."""
    register_primary_text("Macbeth")
    # Use a tight budget so the test stays fast — the override logic is
    # independent of the absolute timeout value.
    _install_slow_probe(0.10)

    decision = decide_retrieval("Macbeth", {"AO1", "AO2"}, timeout_s=0.01)

    assert decision.retrieve is False
    assert decision.reason is REASON_EMBEDDER_TIMEOUT
    assert decision.mode == "analysis_mode"


def test_embedder_probe_raising_treated_as_unavailable() -> None:
    """A probe that raises is unavailable (down, not slow) — same fallback."""
    register_primary_text("Macbeth")
    _install_raising_probe(ConnectionError("embedder unreachable"))

    decision = decide_retrieval("Macbeth", {"AO1", "AO2"})

    assert decision.reason is REASON_EMBEDDER_TIMEOUT
    assert decision.retrieve is False


def test_embedder_available_within_returns_false_on_slow_probe() -> None:
    """The probe wrapper itself reports availability honestly."""
    _install_slow_probe(0.10)
    assert embedder_available_within(0.01) is False


def test_embedder_available_within_returns_true_on_fast_probe() -> None:
    """A fast probe is reported available (the no-op default behaves so)."""
    _install_fast_probe()
    assert embedder_available_within(EMBEDDER_TIMEOUT_SECONDS) is True


def test_embedder_available_within_rejects_non_positive_timeout() -> None:
    """Bad input raises ValueError — non-positive timeouts are config bugs."""
    with pytest.raises(ValueError):
        embedder_available_within(0)
    with pytest.raises(ValueError):
        embedder_available_within(-1.0)


# ---------------------------------------------------------------------------
# Empty focus_aos: defaults to retrieve when primary present
# ---------------------------------------------------------------------------


def test_empty_focus_aos_defaults_to_retrieve_when_primary_present() -> None:
    """Empty focus_aos is non-AO3-only AND not mixed → branch 4."""
    register_primary_text("Macbeth")

    decision = should_retrieve("Macbeth", set())

    assert decision == RetrievalDecision(
        True, REASON_RETRIEVE_PRIMARY, "retrieve"
    )


def test_empty_focus_aos_with_no_primary_falls_through_to_analysis_mode() -> None:
    """Empty focus_aos + no primary text → branch 2 (no_primary)."""
    decision = should_retrieve("UnknownWork", set())

    assert decision.reason is REASON_NO_PRIMARY


# ---------------------------------------------------------------------------
# AC-007: reason strings are module-level constants (identity check)
# ---------------------------------------------------------------------------


def test_reason_strings_are_module_level_constants() -> None:
    """``decision.reason is REASON_X`` must hold (identity, not equality).

    If a future refactor accidentally inlines the reason literal at the
    return site, equality would still pass but identity would fail —
    that's the regression this test guards against.
    """
    register_primary_text("Macbeth")

    branch1 = should_retrieve("Macbeth", {"AO3"})
    branch2 = should_retrieve("UnknownWork", {"AO1"})
    branch3 = should_retrieve("Macbeth", {"AO1", "AO3"})
    branch4 = should_retrieve("Macbeth", {"AO1"})

    assert branch1.reason is REASON_AO3_ONLY
    assert branch2.reason is REASON_NO_PRIMARY
    assert branch3.reason is REASON_RETRIEVE_MIXED
    assert branch4.reason is REASON_RETRIEVE_PRIMARY


# ---------------------------------------------------------------------------
# has_primary_text + corpus index registration
# ---------------------------------------------------------------------------


def test_has_primary_text_reflects_registry_state() -> None:
    """``has_primary_text`` is a pure lookup against the registered set."""
    assert has_primary_text("Macbeth") is False
    register_primary_text("Macbeth")
    assert has_primary_text("Macbeth") is True
    clear_primary_text_index()
    assert has_primary_text("Macbeth") is False


def test_register_primary_text_rejects_empty_string() -> None:
    """Empty ``text_name`` violates the corpus contract — refuse it."""
    with pytest.raises(ValueError):
        register_primary_text("")


# ---------------------------------------------------------------------------
# Defensive coercion: non-set focus_aos still routes correctly
# ---------------------------------------------------------------------------


def test_focus_aos_accepts_frozenset_for_ao3_only_branch() -> None:
    """Callers passing ``frozenset`` are not silently mis-routed."""
    decision = should_retrieve("Macbeth", frozenset({"AO3"}))
    assert decision.reason is REASON_AO3_ONLY


# ---------------------------------------------------------------------------
# Seam test (from task spec): RetrievalDecision contract for
# TASK-PRV-004 (skips retrieval if retrieve=False) and TASK-PRV-006
# (forwards reason into VerifierMetadata).
# ---------------------------------------------------------------------------


@pytest.mark.seam
@pytest.mark.integration_contract("RetrievalDecision")
def test_should_retrieve_returns_named_tuple_contract() -> None:
    """Verify the four-branch decision tree returns the RetrievalDecision
    named tuple with module-level reason constants.

    Contract: ``should_retrieve(text_name, focus_aos) → (retrieve,
    reason, mode)``; reason values are module-level constants.
    Consumers: TASK-PRV-004 (skips retrieval if retrieve=False),
    TASK-PRV-006 (forwards reason into VerifierMetadata).
    """
    decision = should_retrieve("nonexistent_text", {"AO1", "AO2"})
    assert isinstance(decision, RetrievalDecision)
    assert decision.reason is REASON_NO_PRIMARY  # identity, not equality


# ---------------------------------------------------------------------------
# TASK-PRV-004: source-filtered retrieval test infrastructure
# ---------------------------------------------------------------------------
#
# A FakeCollection emulates the slice of the chromadb API ``retrieve``
# touches — ``query(query_texts=, n_results=, where=)`` returning a dict
# with keys ``ids`` / ``documents`` / ``metadatas`` / ``distances`` (each
# a list-of-lists keyed by query). It applies ``where`` filters in-memory
# so we can exercise the source_type / text_name filter without standing
# up a real chromadb instance.


def _make_chunk(
    *,
    text: str,
    source_type: SourceType,
    source_path: str = "/corpus/primary_text/macbeth.txt",
    text_name: str = "macbeth",
    chunk_index: int = 0,
    citation: PlayCitationAnchor | None = None,
) -> CorpusChunk:
    """Construct a CorpusChunk with sensible defaults for retrieval tests."""
    if citation is None and source_type is SourceType.PRIMARY_TEXT:
        citation = PlayCitationAnchor(act=1, scene=1, line=chunk_index + 1)
    return CorpusChunk(
        text=text,
        source_type=source_type,
        source_path=source_path,
        text_name=text_name,
        citation_anchor=citation,
        chunk_index=chunk_index,
    )


def _chunk_to_metadata(chunk: CorpusChunk) -> dict[str, Any]:
    """Encode a CorpusChunk for storage in the FakeCollection metadata.

    Mirrors the expected production wiring: chromadb's metadata stores a
    JSON-serialised payload under :data:`CHUNK_PAYLOAD_KEY` so that the
    discriminated ``citation_anchor`` union round-trips correctly.
    """
    return {
        CHUNK_PAYLOAD_KEY: chunk.model_dump_json(),
        # Duplicate scalar fields so the where-filter works at the fake-
        # collection layer the same way it does in real chromadb.
        "text_name": chunk.text_name,
        "source_type": chunk.source_type.value,
    }


class _FakeCollection:
    """Minimal in-memory stand-in for a chromadb collection.

    Stores ``(chunk, distance)`` pairs and applies the where-filter the
    same way real chromadb does: an ``$and`` clause is treated as the
    intersection of its members; ``{"field": {"$in": [...]}}`` matches
    when the chunk's ``field`` is in the list; bare ``{"field": value}``
    matches on equality. The ``query`` method returns at most
    ``n_results`` records, lowest-distance first.
    """

    def __init__(self, entries: list[tuple[CorpusChunk, float]]) -> None:
        self._entries = entries

    def query(
        self,
        *,
        query_texts: list[str],
        n_results: int,
        where: dict[str, Any] | None = None,
    ) -> dict[str, list[list[Any]]]:
        del query_texts  # FakeCollection ignores query semantics
        filtered = [
            (chunk, distance)
            for chunk, distance in self._entries
            if _matches_where(chunk, where or {})
        ]
        filtered.sort(key=lambda pair: pair[1])
        filtered = filtered[:n_results]
        return {
            "ids": [[f"id-{i}" for i, _ in enumerate(filtered)]],
            "documents": [[chunk.text for chunk, _ in filtered]],
            "metadatas": [[_chunk_to_metadata(chunk) for chunk, _ in filtered]],
            "distances": [[distance for _, distance in filtered]],
        }


def _matches_where(chunk: CorpusChunk, where: dict[str, Any]) -> bool:
    """Apply a where-filter to a chunk, supporting ``$and`` and ``$in``."""
    if not where:
        return True
    if "$and" in where:
        return all(_matches_where(chunk, clause) for clause in where["$and"])
    for field, condition in where.items():
        chunk_value: Any
        if field == "text_name":
            chunk_value = chunk.text_name
        elif field == "source_type":
            chunk_value = chunk.source_type.value
        else:
            chunk_value = getattr(chunk, field, None)
        if isinstance(condition, dict) and "$in" in condition:
            if chunk_value not in condition["$in"]:
                return False
        elif chunk_value != condition:
            return False
    return True


def _install_collection(entries: list[tuple[CorpusChunk, float]]) -> None:
    """Install a FakeCollection containing ``entries`` as the active provider."""
    collection = _FakeCollection(entries)
    set_collection_provider(lambda: collection)


def _install_identity_reranker() -> None:
    """Install a reranker that preserves the input order.

    The cross-encoder returns one score per pair; we return scores in
    descending input order so the rerank sort is a stable identity. This
    lets retrieve tests exercise the reranker code path without the test
    depending on a particular relevance signal.
    """

    class _IdentityReranker:
        def predict(self, pairs: list[list[str]]) -> list[float]:
            # Higher score → earlier in output. Preserve input ordering by
            # making the first pair's score the highest.
            return [float(len(pairs) - i) for i in range(len(pairs))]

    set_reranker_factory(lambda: _IdentityReranker())


def _install_failing_reranker() -> None:
    """Install a reranker factory that raises ImportError.

    Simulates the production "sentence_transformers not installed" path
    that triggers the graceful-degradation fallback.
    """

    def factory() -> Any:
        raise ImportError("sentence_transformers not installed")

    set_reranker_factory(factory)


# ---------------------------------------------------------------------------
# AC: primary-first ordering at equal score
# ---------------------------------------------------------------------------


def test_retrieve_primary_first_at_equal_score() -> None:
    """All PRIMARY_TEXT chunks come before any SECONDARY_* chunks.

    Fixture: 3 primary + 3 secondary chunks at the same distance. The
    where-filter doesn't disambiguate them — only the primary-first
    partition step in ``retrieve`` does. With identity rerank the input
    order survives, so any leading secondary in the result list would
    fail the assertion.
    """
    _install_identity_reranker()
    primaries = [
        _make_chunk(
            text=f"primary-{i}",
            source_type=SourceType.PRIMARY_TEXT,
            chunk_index=i,
        )
        for i in range(3)
    ]
    secondaries = [
        _make_chunk(
            text=f"secondary-{i}",
            source_type=SourceType.SECONDARY_STUDY_GUIDE,
            source_path=f"/corpus/secondary_study_guide/notes-{i}.txt",
            chunk_index=i,
            citation=None,
        )
        for i in range(3)
    ]
    # Interleave so the where-filter doesn't accidentally produce
    # primary-first by storage order — primary-first must come from the
    # partition step.
    entries = []
    for primary, secondary in zip(primaries, secondaries, strict=True):
        entries.append((primary, 0.5))
        entries.append((secondary, 0.5))

    _install_collection(entries)

    result = retrieve("witches", "macbeth", focus_aos={"AO1", "AO2"}, top_k=6)

    assert len(result) == 6
    types = [chunk.source_type for chunk in result]
    # All primary indices come strictly before all secondary indices.
    primary_indices = [
        i for i, st in enumerate(types) if st is SourceType.PRIMARY_TEXT
    ]
    secondary_indices = [
        i for i, st in enumerate(types) if st is not SourceType.PRIMARY_TEXT
    ]
    assert primary_indices == [0, 1, 2]
    assert secondary_indices == [3, 4, 5]


# ---------------------------------------------------------------------------
# AC: top-K boundary (0 / 3 / 6 / 7 available → 0 / 3 / 6 / 6 returned)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "available,expected_returned",
    [
        (0, 0),
        (3, 3),
        (6, 6),
        (7, 6),
    ],
)
def test_retrieve_top_k_boundary(available: int, expected_returned: int) -> None:
    """Top-K caps the result list; fewer-than-K returns all available."""
    _install_identity_reranker()
    entries = [
        (
            _make_chunk(
                text=f"chunk-{i}",
                source_type=SourceType.PRIMARY_TEXT,
                chunk_index=i,
            ),
            0.1 + 0.001 * i,
        )
        for i in range(available)
    ]
    _install_collection(entries)

    result = retrieve("query", "macbeth", focus_aos={"AO1"}, top_k=DEFAULT_TOP_K)

    assert len(result) == expected_returned


# ---------------------------------------------------------------------------
# AC: empty corpus for text_name returns []
# ---------------------------------------------------------------------------


def test_retrieve_empty_corpus_returns_empty_list() -> None:
    """A text_name with no chunks (e.g. Inspector Calls) → []."""
    _install_identity_reranker()
    # Collection has chunks but for a different text_name.
    other_chunk = _make_chunk(
        text="other text",
        source_type=SourceType.PRIMARY_TEXT,
        text_name="othello",
    )
    _install_collection([(other_chunk, 0.1)])

    result = retrieve("query", "inspector_calls", focus_aos={"AO1", "AO2"})

    assert result == []


def test_retrieve_returns_empty_when_no_collection_provider() -> None:
    """No provider wired → empty list (not an exception)."""
    # No _install_collection call; the autouse fixture has reset it.
    result = retrieve("query", "macbeth", focus_aos={"AO1"})

    assert result == []


# ---------------------------------------------------------------------------
# AC: reranker import-failure path returns chunks without rerank
# ---------------------------------------------------------------------------


def test_retrieve_falls_back_when_reranker_unavailable() -> None:
    """ImportError from the reranker → mode=no_rerank, chunks still returned.

    Verifies (a) results are still produced, (b) primary-first ordering
    holds even on the fallback path, and (c) ``get_last_retrieval_mode``
    reports ``MODE_NO_RERANK`` so the orchestrator can record it in turn
    metadata.
    """
    _install_failing_reranker()
    entries = [
        (
            _make_chunk(
                text="primary",
                source_type=SourceType.PRIMARY_TEXT,
                chunk_index=0,
            ),
            0.1,
        ),
        (
            _make_chunk(
                text="secondary",
                source_type=SourceType.SECONDARY_CRITICAL,
                source_path="/corpus/secondary_critical/essay.txt",
                chunk_index=0,
                citation=None,
            ),
            0.05,  # secondary scored *better* by base similarity
        ),
    ]
    _install_collection(entries)

    result = retrieve("query", "macbeth", focus_aos={"AO1"})

    assert len(result) == 2
    # Primary-first must still hold despite secondary's lower distance.
    assert result[0].source_type is SourceType.PRIMARY_TEXT
    assert result[1].source_type is SourceType.SECONDARY_CRITICAL
    assert get_last_retrieval_mode() == MODE_NO_RERANK


def test_retrieve_records_mode_rerank_on_success_path() -> None:
    """Successful reranker call → mode=rerank recorded for orchestrator."""
    _install_identity_reranker()
    _install_collection(
        [
            (
                _make_chunk(
                    text="primary",
                    source_type=SourceType.PRIMARY_TEXT,
                ),
                0.1,
            )
        ]
    )

    retrieve("query", "macbeth", focus_aos={"AO1"})

    assert get_last_retrieval_mode() == MODE_RERANK


# ---------------------------------------------------------------------------
# AC: AQA-pattern filename in metadata is excluded at retrieval-time
# ---------------------------------------------------------------------------


def test_retrieve_filters_aqa_filename_defence_in_depth() -> None:
    """Even if a chunk's source_path matches the AQA regex, exclude it.

    Mirrors the loader's ingestion-time refusal but applied as a safety
    net at retrieval — if the loader regex was bypassed (typo, new
    filename pattern), the retrieval-time filter is the last line of
    defence before the chunk reaches the Player.
    """
    _install_identity_reranker()
    safe = _make_chunk(
        text="legitimate primary",
        source_type=SourceType.PRIMARY_TEXT,
        source_path="/corpus/primary_text/macbeth.txt",
        chunk_index=0,
    )
    leaked_aqa = _make_chunk(
        text="leaked aqa material",
        source_type=SourceType.PRIMARY_TEXT,
        # Typical filename that should have been refused at ingestion.
        source_path="/corpus/primary_text/macbeth_past_paper_2024.txt",
        chunk_index=1,
    )
    _install_collection([(safe, 0.1), (leaked_aqa, 0.2)])

    result = retrieve("query", "macbeth", focus_aos={"AO1"})

    assert len(result) == 1
    assert result[0].source_path == "/corpus/primary_text/macbeth.txt"
    # Verify other AQA filename variants too.
    for path in (
        "/corpus/primary_text/mark-scheme-2023.txt",
        "/corpus/primary_text/examiner_report.txt",
    ):
        leaked = _make_chunk(
            text="x",
            source_type=SourceType.PRIMARY_TEXT,
            source_path=path,
            chunk_index=2,
        )
        _install_collection([(safe, 0.1), (leaked, 0.2)])
        result = retrieve("query", "macbeth", focus_aos={"AO1"})
        assert len(result) == 1
        assert result[0].source_path == "/corpus/primary_text/macbeth.txt"


# ---------------------------------------------------------------------------
# AC: where-filter excludes CONTEXT_HISTORICAL for non-AO3 turns
# ---------------------------------------------------------------------------


def test_retrieve_excludes_context_historical_for_non_ao3_turns() -> None:
    """CONTEXT_HISTORICAL is reserved for AO3-context-historical retrievals.

    The where-filter constrains source_type to the non-AO3 set; a
    CONTEXT_HISTORICAL chunk in the same collection must not surface.
    """
    _install_identity_reranker()
    primary = _make_chunk(
        text="primary",
        source_type=SourceType.PRIMARY_TEXT,
    )
    historical = _make_chunk(
        text="historical context",
        source_type=SourceType.CONTEXT_HISTORICAL,
        source_path="/corpus/context_historical/jacobean.txt",
        chunk_index=0,
        citation=None,
    )
    _install_collection([(primary, 0.1), (historical, 0.05)])

    result = retrieve("query", "macbeth", focus_aos={"AO1", "AO2"})

    assert len(result) == 1
    assert result[0].source_type is SourceType.PRIMARY_TEXT
    # Defensive check: the CONTEXT_HISTORICAL value is not in the
    # constant we filter against, mirroring the four-folder invariant.
    assert SourceType.CONTEXT_HISTORICAL not in NON_AO3_SOURCE_TYPES


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def test_retrieve_rejects_empty_text_name() -> None:
    """Empty text_name is a config bug — refuse it loudly."""
    with pytest.raises(ValueError):
        retrieve("query", "", focus_aos={"AO1"})


def test_retrieve_rejects_non_positive_top_k() -> None:
    """Non-positive top_k is a config bug — refuse it loudly."""
    with pytest.raises(ValueError):
        retrieve("query", "macbeth", focus_aos={"AO1"}, top_k=0)
    with pytest.raises(ValueError):
        retrieve("query", "macbeth", focus_aos={"AO1"}, top_k=-1)


def test_reranker_model_constant_is_bge_v2_m3() -> None:
    """The module-level constant pins the production reranker identifier."""
    assert RERANKER_MODEL == "BAAI/bge-reranker-v2-m3"


def test_load_reranker_caches_production_instance(monkeypatch) -> None:
    """The production path constructs the CrossEncoder once per process.

    Constructing the reranker loads ~2.3GB of weights (~3.5s measured on
    the spark — Lane 2 1a receipt, 2026-08-01); an uncached production
    path pays that on every retrieval turn.
    """
    import sys
    import types

    from study_tutor.knowledge import retrieval as retrieval_module

    constructed: list[object] = []

    class _CountingCrossEncoder:
        def __init__(self, model_name: str, device: str | None = None) -> None:
            constructed.append(self)

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.CrossEncoder = _CountingCrossEncoder  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    first = retrieval_module._load_reranker()
    second = retrieval_module._load_reranker()

    assert first is second
    assert len(constructed) == 1


def test_factory_path_stays_uncached_and_clears_production_cache(monkeypatch) -> None:
    """Installing a factory drops the cached instance; the factory path is uncached.

    A factory that raises ``ImportError`` per call must keep raising on
    every call (the degradation branch is exercised per retrieve), and
    reset must return the module to its import-time state so the next
    production load constructs fresh.
    """
    import sys
    import types

    from study_tutor.knowledge import retrieval as retrieval_module

    constructed: list[object] = []

    class _CountingCrossEncoder:
        def __init__(self, model_name: str, device: str | None = None) -> None:
            constructed.append(self)

    fake_module = types.ModuleType("sentence_transformers")
    fake_module.CrossEncoder = _CountingCrossEncoder  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    retrieval_module._load_reranker()  # warm the production cache
    assert len(constructed) == 1

    calls: list[int] = []

    def _raising_factory() -> Any:
        calls.append(1)
        raise ImportError("simulated: sentence_transformers not installed")

    set_reranker_factory(_raising_factory)
    with pytest.raises(ImportError):
        retrieval_module._load_reranker()
    with pytest.raises(ImportError):
        retrieval_module._load_reranker()
    assert len(calls) == 2  # factory consulted per call, never cached

    reset_reranker_factory()
    retrieval_module._load_reranker()
    assert len(constructed) == 2  # cache was dropped, fresh construction


# ---------------------------------------------------------------------------
# Seam test (from task spec): SourceTypedCorpus contract for retrieve()
# ---------------------------------------------------------------------------


@pytest.fixture
def small_corpus() -> None:
    """Install a small fixture corpus exercising primary + secondary chunks."""
    _install_identity_reranker()
    primary_chunks = [
        _make_chunk(
            text=f"primary witch passage {i}",
            source_type=SourceType.PRIMARY_TEXT,
            chunk_index=i,
            citation=PlayCitationAnchor(act=1, scene=1, line=i + 1),
        )
        for i in range(3)
    ]
    secondary_chunks = [
        _make_chunk(
            text=f"secondary commentary {i}",
            source_type=SourceType.SECONDARY_STUDY_GUIDE,
            source_path=f"/corpus/secondary_study_guide/notes-{i}.txt",
            chunk_index=i,
            citation=None,
        )
        for i in range(2)
    ]
    entries: list[tuple[CorpusChunk, float]] = []
    for i, chunk in enumerate(primary_chunks):
        entries.append((chunk, 0.1 + 0.001 * i))
    for i, chunk in enumerate(secondary_chunks):
        entries.append((chunk, 0.2 + 0.001 * i))
    _install_collection(entries)


@pytest.mark.seam
@pytest.mark.integration_contract("SourceTypedCorpus")
def test_retrieve_returns_primary_first_with_citation_anchors(
    small_corpus: None,
) -> None:
    """Verify retrieve() returns CorpusChunk objects with primary-text
    chunks ordered first, and that primary chunks carry citation_anchor.

    Contract: retrieve() consumes the SourceTypedCorpus contract
    and emits chunks downstream to TASK-PRV-005 (verifier reads
    citation_anchor directly).
    """
    chunks = retrieve(
        "witches in macbeth", "macbeth", focus_aos={"AO1", "AO2"}
    )

    primary = [
        c for c in chunks if c.source_type is SourceType.PRIMARY_TEXT
    ]
    secondary = [
        c for c in chunks if c.source_type is not SourceType.PRIMARY_TEXT
    ]

    # Primary-first ordering invariant
    if primary and secondary:
        primary_max_idx = max(chunks.index(c) for c in primary)
        secondary_min_idx = min(chunks.index(c) for c in secondary)
        assert primary_max_idx < secondary_min_idx, (
            "primary chunks must come before secondary chunks"
        )

    for chunk in primary:
        assert chunk.citation_anchor is not None, (
            "primary chunks must carry citation_anchor"
        )
