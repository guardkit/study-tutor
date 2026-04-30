"""Unit + seam tests for the dynamic retrieval-decision function.

Covers the acceptance criteria of TASK-PRV-003 (R2 + R3):

  * AC-001..AC-004: the four decision branches.
  * AC-005: AO3-only with empty ``context_historical`` still bypasses.
  * AC-006: embedder timeout override → ``REASON_EMBEDDER_TIMEOUT``.
  * AC-007: reason values are module-level constants (identity check).

Plus the seam test from the task spec, which validates the
``RetrievalDecision`` contract consumed by TASK-PRV-004 (skips retrieval
if ``retrieve=False``) and TASK-PRV-006 (forwards reason into
``VerifierMetadata``).

Tests use the public registration / probe helpers
(``register_primary_text``, ``clear_primary_text_index``,
``set_embedder_probe``, ``reset_embedder_probe``) rather than poking at
the underscore-prefixed module state directly. A ``conftest``-style
autouse fixture isolates each test from the others.
"""

from __future__ import annotations

import time
from typing import Callable

import pytest

from study_tutor.knowledge.retrieval import (
    EMBEDDER_TIMEOUT_SECONDS,
    REASON_AO3_ONLY,
    REASON_EMBEDDER_TIMEOUT,
    REASON_NO_PRIMARY,
    REASON_RETRIEVE_MIXED,
    REASON_RETRIEVE_PRIMARY,
    RetrievalDecision,
    clear_primary_text_index,
    decide_retrieval,
    embedder_available_within,
    has_primary_text,
    register_primary_text,
    reset_embedder_probe,
    set_embedder_probe,
    should_retrieve,
)


# ---------------------------------------------------------------------------
# Fixtures: isolate module-level mutable state between cases
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_retrieval_module_state() -> None:
    """Reset corpus index + embedder probe before AND after each test.

    The retrieval module keeps two pieces of mutable state (the
    primary-text index and the embedder probe). Both are explicitly
    designed for test injection, but only if tests reset them — so we
    do that automatically.
    """
    clear_primary_text_index()
    reset_embedder_probe()
    yield
    clear_primary_text_index()
    reset_embedder_probe()


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
