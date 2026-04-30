"""Seam test: verify the RetrievalDecision contract from TASK-PRV-003.

Backfills the contract test that was planned in
``tasks/backlog/primary-text-rag-and-quote-verifier/TASK-PRV-003-retrieval-decision-function.md:158-184``
but never implemented in its own file. TASK-PRV-003 was conditionally
approved under the same ``parallel_contention`` rule that masked
TASK-PRV-002's contract failure, so this test acts as a gate condition
before resuming the autobuild from wave 3.

Producer: TASK-PRV-003 (``should_retrieve`` four-branch decision tree).
Consumers: TASK-PRV-004 (skips retrieval if ``retrieve=False``) and
TASK-PRV-006 (forwards ``reason`` into ``VerifierMetadata``).

Why identity not equality
-------------------------
``decision.reason is REASON_X`` is asserted on every branch. The original
PRV-003 task spec required reason values to be module-level constants so
a future rename fails loudly: an ``==`` check would silently still match
a stale literal copy at the call site, while ``is`` catches the divergence.

Hermeticity
-----------
No embedder calls and no FalkorDB. ``has_primary_text`` is exercised
through its public registration helpers (``register_primary_text`` /
``clear_primary_text_index``) rather than mocked, because the helpers
are themselves part of the contract tested here.
"""

from __future__ import annotations

import pytest

from study_tutor.knowledge.retrieval import (
    REASON_AO3_ONLY,
    REASON_NO_PRIMARY,
    REASON_RETRIEVE_MIXED,
    REASON_RETRIEVE_PRIMARY,
    RetrievalDecision,
    clear_primary_text_index,
    register_primary_text,
    should_retrieve,
)


@pytest.fixture(autouse=True)
def _isolate_primary_text_index() -> None:
    """Clear the corpus index before AND after each case.

    ``_PRIMARY_TEXT_INDEX`` is module-level mutable state. Each branch
    here has different expectations about whether a text is registered,
    so we reset around every test rather than relying on ordering.
    """
    clear_primary_text_index()
    yield
    clear_primary_text_index()


@pytest.mark.seam
@pytest.mark.integration_contract("RetrievalDecision")
def test_should_retrieve_returns_named_tuple_contract() -> None:
    """Verify all four branches return a ``RetrievalDecision`` named
    tuple whose ``reason`` is the documented module-level constant.

    Branch matrix (from the PRV-003 task spec):

    | focus_aos                | text registered | reason                  | mode           |
    |--------------------------|-----------------|-------------------------|----------------|
    | {"AO3"}                  | irrelevant      | REASON_AO3_ONLY         | "ao3_bypass"   |
    | {"AO1","AO2"}            | no              | REASON_NO_PRIMARY       | "analysis_mode"|
    | {"AO1","AO2","AO3"}      | yes             | REASON_RETRIEVE_MIXED   | "mixed"        |
    | {"AO1","AO2"}            | yes             | REASON_RETRIEVE_PRIMARY | "retrieve"     |
    """
    # Branch 2 (anchor case from the original stub): no primary text →
    # analysis_mode. Run first because the autouse fixture has already
    # cleared the index, so no setup is needed.
    decision_no_primary = should_retrieve("nonexistent_text", {"AO1", "AO2"})
    assert isinstance(decision_no_primary, RetrievalDecision)
    assert decision_no_primary.reason is REASON_NO_PRIMARY  # identity, not equality
    assert decision_no_primary.retrieve is False
    assert decision_no_primary.mode == "analysis_mode"

    # Branch 1: AO3-only → bypass regardless of corpus contents.
    decision_ao3_only = should_retrieve("Macbeth", {"AO3"})
    assert isinstance(decision_ao3_only, RetrievalDecision)
    assert decision_ao3_only.reason is REASON_AO3_ONLY  # identity
    assert decision_ao3_only.retrieve is False
    assert decision_ao3_only.mode == "ao3_bypass"

    # Branch 3: mixed AO3 + non-AO3, primary present → retrieve, mode="mixed".
    register_primary_text("Macbeth")
    decision_mixed = should_retrieve("Macbeth", {"AO1", "AO2", "AO3"})
    assert isinstance(decision_mixed, RetrievalDecision)
    assert decision_mixed.reason is REASON_RETRIEVE_MIXED  # identity
    assert decision_mixed.retrieve is True
    assert decision_mixed.mode == "mixed"

    # Branch 4: primary present, non-AO3-only → standard retrieval.
    decision_primary = should_retrieve("Macbeth", {"AO1", "AO2"})
    assert isinstance(decision_primary, RetrievalDecision)
    assert decision_primary.reason is REASON_RETRIEVE_PRIMARY  # identity
    assert decision_primary.retrieve is True
    assert decision_primary.mode == "retrieve"
