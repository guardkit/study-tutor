"""pytest-bdd glue module for ``primary-text-rag-and-quote-verifier.feature``.

This module exists for three reasons (mirroring the pattern set by
``features/deepagents-tutoring-loop/test_deepagents_tutoring_loop.py``):

1. **Collection bridge**: GuardKit's ``bdd_runner`` invokes ``pytest`` with
   a ``.feature`` path. Pytest-bdd v8 has no built-in ``.feature`` collector;
   the bridge in ``features/conftest.py`` redirects that argv to this
   sibling ``test_<slug>.py`` module so :func:`pytest_bdd.scenarios` can
   actually bind the scenarios. Without it the runner exits 4 ("not found"),
   which is exactly the BDD-oracle failure surfaced by the Coach gate on
   the previous turn (TASK-PRV-003 turn 1).

2. **Step definitions for @task:TASK-PRV-002**: the 7 corpus-loader
   scenarios tagged ``@task:TASK-PRV-002`` have step definitions in this
   module — ingestion source-type inference, AQA refusal, in-copyright
   refusal, empty folder, whitespace-only file, corrupted file resilience,
   and path-traversal rejection. Steps drive the real
   :func:`study_tutor.knowledge.corpus.load_corpus` so the BDD oracle
   exercises the production loader, not a stub.

3. **Step definitions for @task:TASK-PRV-003**: the 5 scenarios tagged
   ``@task:TASK-PRV-003`` in this feature file have step definitions in
   this module:

   * ``@key-example @smoke @retrieval @analysis-mode`` — no primary text
     in corpus → ``REASON_NO_PRIMARY``.
   * ``@key-example @smoke @retrieval @ao3-bypass`` — AO3-only focus →
     ``REASON_AO3_ONLY``.
   * ``@edge-case @retrieval @ao3`` (mixed) — AO3 + AO1/AO2 → mixed-mode
     retrieval (``REASON_RETRIEVE_MIXED``, ``mode="mixed"``).
   * ``@edge-case @retrieval @resilience`` — embedder unavailable →
     ``REASON_EMBEDDER_TIMEOUT``.
   * ``@edge-case @retrieval @ao3`` (empty historical-context) — AO3-only
     short-circuit fires regardless of corpus folder contents.

   Steps unique to other tasks (TASK-PRV-004 / -005 / -006) remain
   intentionally unbound — they appear as ``scenarios_pending`` and are
   tolerated by the Coach gate (``scenarios_failed == 0``).

Step-definition discipline:

* Background steps are bound as no-ops because TASK-PRV-003's scope is
  purely the decision function — the corpus loader (TASK-PRV-002) and
  quote verifier (TASK-PRV-005) own the loader / verifier preconditions.
  Binding them here lets the ``@task:TASK-PRV-003`` scenarios resolve
  without dragging in unimplemented infrastructure.

* The decision-related steps call into the real
  :func:`study_tutor.knowledge.retrieval.should_retrieve` /
  :func:`decide_retrieval` so the BDD oracle exercises the production
  code path, not a stub. Reason values are asserted by **identity**
  against the module-level constants (``decision.reason is REASON_X``),
  matching the @key-example assumption (ASSUM-006) recorded in the
  feature file.

* Embedder unavailability is simulated by installing a slow probe
  (``set_embedder_probe``); we deliberately use a tight test-budget
  (``timeout_s=0.01``) and a probe that sleeps just past it so the BDD
  scenario completes in milliseconds rather than the 5-second
  production budget.
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest
from pytest_bdd import given, scenarios, then, when

from study_tutor.knowledge.retrieval import (
    REASON_AO3_ONLY,
    REASON_EMBEDDER_TIMEOUT,
    REASON_NO_PRIMARY,
    REASON_RETRIEVE_MIXED,
    REASON_RETRIEVE_PRIMARY,
    RetrievalDecision,
    clear_primary_text_index,
    decide_retrieval,
    register_primary_text,
    reset_embedder_probe,
    set_embedder_probe,
    should_retrieve,
)


# Bind every scenario in the sibling .feature file. The BDD runner's
# ``-m task_TASK_PRV_003`` filter selects the per-task subset; un-bound
# steps in unrelated scenarios surface as ``scenarios_pending`` (tolerated
# by the Coach gate — see module docstring).
scenarios(
    str(
        Path(__file__).with_name(
            "primary-text-rag-and-quote-verifier.feature"
        )
    )
)


# ---------------------------------------------------------------------------
# Per-scenario shared state
# ---------------------------------------------------------------------------


# Default text name used by scenarios that don't otherwise pin one. Every
# @task:TASK-PRV-003 scenario either registers this name explicitly via the
# "primary text whose canonical edition is in the corpus" Given, or uses a
# distinct name for the "in-copyright modern text whose primary edition is
# not in the corpus" Given — so collisions are impossible.
_PRIMARY_TEXT_NAME = "Macbeth"
_IN_COPYRIGHT_TEXT_NAME = "An Inspector Calls"


class BddContext:
    """Mutable container threaded through Given/When/Then via fixture.

    Holds the scenario inputs (text name, focus AOs, embedder timeout),
    the decision returned by the System-Under-Test, and a bag of
    metadata flags that the Then-steps inspect. Recreated per scenario
    by the :func:`bdd_context` fixture so state never leaks between
    scenarios.
    """

    def __init__(self) -> None:
        # Inputs to should_retrieve / decide_retrieval.
        self.text_name: str = _PRIMARY_TEXT_NAME
        self.focus_aos: set[str] = {"AO1", "AO2"}
        self.timeout_s: float = 5.0  # production default
        # Outputs.
        self.decision: RetrievalDecision | None = None
        # Metadata-style flags inspected by Then-steps. The decision
        # function does not write these directly — it returns a
        # RetrievalDecision and the orchestrator records it as turn
        # metadata. The BDD steps assert on the decision tuple itself
        # to verify "metadata would record X" claims.
        self.embedder_unavailable: bool = False


@pytest.fixture
def bdd_context() -> BddContext:
    """Fresh context per scenario; teardown resets module-level state.

    The retrieval module keeps mutable state (primary-text registry +
    embedder probe). The fixture clears both at scenario boundaries so
    one scenario's setup cannot leak into the next.
    """
    clear_primary_text_index()
    reset_embedder_probe()
    ctx = BddContext()
    yield ctx
    clear_primary_text_index()
    reset_embedder_probe()


# ---------------------------------------------------------------------------
# Background — bound as no-ops (TASK-PRV-002 / -005 own these surfaces)
# ---------------------------------------------------------------------------


@given("a source-typed corpus is configured under the GCSE English domain")
def _bg_corpus_configured() -> None:
    """No-op: corpus configuration is TASK-PRV-002's surface."""


@given(
    "the corpus is partitioned into four source-type folders: "
    "primary text, secondary study guide, secondary critical, "
    "and historical context"
)
def _bg_corpus_partitioned() -> None:
    """No-op: folder partitioning is TASK-PRV-002's surface."""


@given(
    "every chunk in the corpus carries a source-type label "
    "inferred from its parent folder"
)
def _bg_chunks_labelled() -> None:
    """No-op: source-type labelling is TASK-PRV-001/-002's surface."""


@given(
    "the corpus excludes AQA assessment materials in line with "
    "the publisher's stated prohibition"
)
def _bg_aqa_excluded() -> None:
    """No-op: AQA exclusion is TASK-PRV-002's surface."""


@given(
    "public-domain primary texts are sourced from a canonical "
    "edition with stable citation anchors"
)
def _bg_canonical_editions() -> None:
    """No-op: canonical-edition sourcing is TASK-PRV-002's surface."""


@given(
    "the tutoring loop consults the retrieval-decision function "
    "before every Player turn"
)
def _bg_tutoring_loop_consults() -> None:
    """No-op: orchestrator wiring is TASK-PRV-006's surface.

    What we DO need is for our decision function to exist and behave —
    that's covered by the When/Then steps below.
    """


@given(
    "the quote verifier inspects every Player response before the "
    "Coach evaluates it"
)
def _bg_verifier_inspects() -> None:
    """No-op: verifier-Coach handover is TASK-PRV-005/-006's surface."""


# ---------------------------------------------------------------------------
# Scenario-specific Given steps
# ---------------------------------------------------------------------------


@given(
    "the session is on an in-copyright modern text whose "
    "primary edition is not in the corpus"
)
def _given_in_copyright_no_primary(bdd_context: BddContext) -> None:
    """The text exists in the world but has no chunks indexed.

    We deliberately do NOT register this text — leaving it absent from
    the corpus index drives ``has_primary_text`` to False, which is
    exactly the Branch-2 trigger the analysis-mode scenario needs.
    """
    bdd_context.text_name = _IN_COPYRIGHT_TEXT_NAME
    # Default focus_aos ({"AO1", "AO2"}) is non-AO3-only so Branch 1
    # cannot pre-empt Branch 2.


@given(
    "the session is on a primary text whose canonical edition "
    "is in the corpus"
)
def _given_primary_text_in_corpus(bdd_context: BddContext) -> None:
    """Register a primary text in the corpus index for this scenario."""
    bdd_context.text_name = _PRIMARY_TEXT_NAME
    register_primary_text(_PRIMARY_TEXT_NAME)


@given("the focus assessment objectives are limited to AO3 alone")
def _given_focus_ao3_only(bdd_context: BddContext) -> None:
    """Set focus_aos to the AO3-only short-circuit input."""
    bdd_context.focus_aos = {"AO3"}


@given("the focus assessment objectives include AO1, AO2, and AO3")
def _given_focus_mixed(bdd_context: BddContext) -> None:
    """Set focus_aos to the mixed-mode trigger input."""
    bdd_context.focus_aos = {"AO1", "AO2", "AO3"}


@given("the embedding service is unavailable")
def _given_embedder_unavailable(bdd_context: BddContext) -> None:
    """Install a slow probe so ``embedder_available_within`` reports False.

    We use a tight test budget (``timeout_s=0.01``) and a probe that
    sleeps just past it so the BDD scenario completes in milliseconds
    rather than the 5-second production budget. The override behaviour
    being verified is independent of the absolute timeout value.
    """
    bdd_context.embedder_unavailable = True
    bdd_context.timeout_s = 0.01

    def _slow_probe() -> None:
        time.sleep(0.05)

    set_embedder_probe(_slow_probe)


@given("the historical-context folder exists and is empty")
def _given_empty_historical_context(bdd_context: BddContext) -> None:
    """No-op for the decision function: corpus folder contents are
    irrelevant when the AO3-only short-circuit fires (Branch 1).

    Co-located with the AO3-only Given because that's the actual driver
    of the bypass — the empty-folder precondition is a context the
    scenario describes but the decision function never inspects.
    """


# ---------------------------------------------------------------------------
# When steps — invoke the real System-Under-Test
# ---------------------------------------------------------------------------


@when(
    "the retrieval-decision function is asked whether to retrieve "
    "for this turn"
)
def _when_decision_asked(bdd_context: BddContext) -> None:
    """Call the production decision function with the scenario inputs.

    For scenarios that did NOT install an embedder-unavailable probe,
    we use the pure ``should_retrieve`` (no probe involved). For the
    embedder-resilience scenario, the dedicated ``runs_for_the_turn``
    step is used instead — see below.
    """
    bdd_context.decision = should_retrieve(
        bdd_context.text_name, bdd_context.focus_aos
    )


@when("the retrieval-decision function runs for the turn")
def _when_decision_runs(bdd_context: BddContext) -> None:
    """Call ``decide_retrieval`` so the embedder-timeout override fires.

    The resilience scenario uses this When variant (the others use the
    "asked whether to retrieve" variant above). ``decide_retrieval``
    composes ``embedder_available_within`` with ``should_retrieve``,
    which is exactly the integration point the resilience scenario
    is documenting.
    """
    bdd_context.decision = decide_retrieval(
        bdd_context.text_name,
        bdd_context.focus_aos,
        timeout_s=bdd_context.timeout_s,
    )


# ---------------------------------------------------------------------------
# Then steps
# ---------------------------------------------------------------------------


def _decision(bdd_context: BddContext) -> RetrievalDecision:
    """Helper: assert decision was produced and return it."""
    assert bdd_context.decision is not None, (
        "no decision recorded — When step did not run"
    )
    return bdd_context.decision


@then("the decision should be to skip retrieval")
def _then_skip_retrieval(bdd_context: BddContext) -> None:
    """``retrieve`` is the boolean decision; skip == False."""
    assert _decision(bdd_context).retrieve is False


@then("the decision should be to retrieve for the AO1 and AO2 evidence")
def _then_retrieve_for_ao12(bdd_context: BddContext) -> None:
    """Mixed-mode scenario: retrieve=True with mode="mixed".

    The "for the AO1 and AO2 evidence" wording is satisfied by the
    mixed-mode tag — the orchestrator (TASK-PRV-006) consumes mode and
    drives source-filtered retrieval (TASK-PRV-004) only against the
    AO1/AO2 portions, matching the spec.
    """
    decision = _decision(bdd_context)
    assert decision.retrieve is True
    assert decision.mode == "mixed"
    assert decision.reason is REASON_RETRIEVE_MIXED


@then(
    "the AO3 contextual material should be expected from the model's "
    "training"
)
def _then_ao3_from_training(bdd_context: BddContext) -> None:
    """The mixed-mode tag IS the contract the Coach reads to know it
    should not score AO3 portions on quote fidelity (TASK-PRV-006
    consumes ``mode="mixed"`` to apply that posture).
    """
    assert _decision(bdd_context).mode == "mixed"


@then("the turn metadata should record this as a mixed-mode turn")
def _then_metadata_mixed_mode(bdd_context: BddContext) -> None:
    """Mode field IS the metadata the orchestrator records."""
    assert _decision(bdd_context).mode == "mixed"


@then(
    "the turn metadata should record that retrieval was skipped "
    "with a reason"
)
def _then_metadata_records_skip_reason(bdd_context: BddContext) -> None:
    """Reason is one of the analysis-mode constants (no-primary or
    embedder-timeout). Identity check, not equality, per ASSUM-006.
    """
    decision = _decision(bdd_context)
    assert decision.reason is REASON_NO_PRIMARY or (
        decision.reason is REASON_EMBEDDER_TIMEOUT
    )
    assert decision.mode == "analysis_mode"


@then(
    "the Coach should not down-rank the response on quote fidelity "
    "for this turn"
)
def _then_coach_does_not_downrank(bdd_context: BddContext) -> None:
    """The "do not down-rank" contract is encoded as ``mode != \"retrieve\""
    — the Coach (TASK-PRV-006) consults mode to decide scoring posture,
    and analysis-mode / ao3_bypass / mixed are all "do not down-rank
    primary-text fidelity" modes.
    """
    decision = _decision(bdd_context)
    assert decision.mode in {"analysis_mode", "ao3_bypass", "mixed"}


@then(
    "the turn metadata should record that retrieval was bypassed "
    "for AO3 context"
)
def _then_metadata_ao3_bypass(bdd_context: BddContext) -> None:
    """AO3-only bypass is encoded as REASON_AO3_ONLY + mode="ao3_bypass"."""
    decision = _decision(bdd_context)
    assert decision.reason is REASON_AO3_ONLY
    assert decision.mode == "ao3_bypass"


@then(
    "the turn metadata should record an Analysis-Mode reason citing "
    "service unavailability"
)
def _then_metadata_embedder_unavailable(bdd_context: BddContext) -> None:
    """Embedder timeout override is encoded as REASON_EMBEDDER_TIMEOUT."""
    decision = _decision(bdd_context)
    assert decision.reason is REASON_EMBEDDER_TIMEOUT
    assert decision.mode == "analysis_mode"
    assert decision.retrieve is False


# ===========================================================================
# TASK-PRV-002 — Source-typed corpus loader scenarios
# ===========================================================================
#
# Step definitions for the 7 scenarios tagged ``@task:TASK-PRV-002``. Each
# scenario builds a small corpus tree under ``tmp_path`` and drives the real
# :func:`study_tutor.knowledge.corpus.load_corpus`, then asserts on the
# returned :class:`IngestResult` (chunks / refusals / skips). State is held
# on a dedicated :class:`CorpusBddContext` so the corpus scenarios don't
# collide with the retrieval-decision context above.
# ---------------------------------------------------------------------------

import os  # noqa: E402  -- kept here to localise corpus-section imports

from study_tutor.knowledge.corpus import (  # noqa: E402
    IngestResult,
    RefusalReason,
    SkipReason,
    SOURCE_TYPE_FOLDERS,
    load_corpus,
)
from study_tutor.knowledge.corpus_models import SourceType  # noqa: E402


class CorpusBddContext:
    """Per-scenario state for TASK-PRV-002 corpus-loader scenarios.

    Holds the corpus root, a registry of files placed (so Then-steps can
    name them), and the :class:`IngestResult` returned by ``load_corpus``.
    Recreated per scenario by the :func:`corpus_context` fixture so one
    scenario's filesystem state never leaks into the next.
    """

    def __init__(self, root: Path) -> None:
        self.root: Path = root
        # Map of logical role → on-disk path so Then-steps can refer to
        # "the first file" / "the corrupted file" / etc. by intent.
        self.files: dict[str, Path] = {}
        # Outputs.
        self.result: IngestResult | None = None

    def make_skeleton(self) -> None:
        """Create the four canonical source-type folders under root."""
        for folder in SOURCE_TYPE_FOLDERS:
            (self.root / folder).mkdir(parents=True, exist_ok=True)


@pytest.fixture
def corpus_context(tmp_path: Path) -> CorpusBddContext:
    """Fresh corpus context per scenario.

    ``tmp_path`` gives us a unique directory per scenario; we don't need
    explicit teardown because pytest cleans the ``tmp_path`` tree itself.
    """
    ctx = CorpusBddContext(tmp_path)
    ctx.make_skeleton()
    return ctx


def _result(corpus_context: CorpusBddContext) -> IngestResult:
    """Helper: assert load_corpus has been invoked and return the result."""
    assert corpus_context.result is not None, (
        "load_corpus has not been called — When step did not run"
    )
    return corpus_context.result


# ---------------------------------------------------------------------------
# Given steps
# ---------------------------------------------------------------------------


# A small but realistic Standard-Ebooks-shaped Macbeth fixture used by
# multiple corpus scenarios. Long enough to produce at least one chunk.
_MACBETH_TEXT = (
    "ACT I\n"
    "Scene 1\n"
    "A desert place. Thunder and lightning.\n"
    "First Witch\n"
    "When shall we three meet again\n"
    "In thunder, lightning, or in rain?\n"
    "Second Witch\n"
    "When the hurlyburly's done,\n"
    "When the battle's lost and won.\n"
)
_STUDY_GUIDE_TEXT = (
    "York Notes on Macbeth: ambition is the central theme that drives "
    "the protagonist toward his destruction.\n"
)


@given("a source file is placed under the primary text folder")
def _given_primary_file(corpus_context: CorpusBddContext) -> None:
    """Place a Macbeth play fixture under primary_text/."""
    path = corpus_context.root / "primary_text" / "macbeth.txt"
    path.write_text(_MACBETH_TEXT, encoding="utf-8")
    corpus_context.files["primary"] = path


@given("another source file is placed under the secondary study guide folder")
def _given_secondary_study_guide_file(corpus_context: CorpusBddContext) -> None:
    """Place a study-guide fixture under secondary_study_guide/."""
    path = corpus_context.root / "secondary_study_guide" / "york_notes.txt"
    path.write_text(_STUDY_GUIDE_TEXT, encoding="utf-8")
    corpus_context.files["secondary_study_guide"] = path


@given("the primary-text folder exists and is empty")
def _given_empty_primary_text_folder(corpus_context: CorpusBddContext) -> None:
    """The four-folder skeleton already exists; primary_text/ is empty."""
    primary = corpus_context.root / "primary_text"
    assert primary.is_dir()
    # Sanity: no files inside (the corpus_context fixture creates only the
    # four empty folders, so this is already true — but explicit is better).
    assert not any(primary.iterdir()), (
        "primary_text/ should start empty for this scenario"
    )


@given("a primary-text file exists but contains only whitespace")
def _given_whitespace_only_file(corpus_context: CorpusBddContext) -> None:
    """Place a whitespace-only file under primary_text/."""
    path = corpus_context.root / "primary_text" / "blank.txt"
    path.write_text("   \n\t\n  \n", encoding="utf-8")
    corpus_context.files["whitespace"] = path


@given(
    "a file whose name matches an AQA past-paper, mark-scheme, "
    "or examiner-report pattern is placed in the corpus"
)
def _given_aqa_file(corpus_context: CorpusBddContext) -> None:
    """Place an AQA-pattern-named file under secondary_study_guide/."""
    # Filename pattern is the refusal trigger; folder choice is incidental.
    path = corpus_context.root / "secondary_study_guide" / "past_paper_2023.pdf"
    path.write_text("AQA past paper content", encoding="utf-8")
    corpus_context.files["aqa"] = path


@given(
    "an in-copyright modern set text is placed under the primary-text folder"
)
def _given_in_copyright_set_text(corpus_context: CorpusBddContext) -> None:
    """Place an in-copyright-titled file under primary_text/."""
    path = corpus_context.root / "primary_text" / "inspector_calls.txt"
    path.write_text(
        "An Inspector Calls full text — this must never be ingested in bulk.",
        encoding="utf-8",
    )
    corpus_context.files["in_copyright"] = path


@given("the primary-text folder contains one valid file and one corrupted file")
def _given_valid_and_corrupted_files(corpus_context: CorpusBddContext) -> None:
    """Place a valid Macbeth file alongside a non-UTF-8 corrupted file."""
    valid = corpus_context.root / "primary_text" / "macbeth.txt"
    valid.write_text(_MACBETH_TEXT, encoding="utf-8")
    corpus_context.files["valid"] = valid
    corrupted = corpus_context.root / "primary_text" / "corrupted.txt"
    # Bytes that can't be decoded as UTF-8 → loader skips with
    # SkipReason.CORRUPTED_FILE rather than crashing the walk.
    corrupted.write_bytes(b"\xff\xfe\xfd\xfc \x80\x81\x82 invalid utf-8")
    corpus_context.files["corrupted"] = corrupted


@given(
    "a source file whose resolved path lies outside the corpus root "
    "is placed in the corpus"
)
def _given_path_traversal_file(corpus_context: CorpusBddContext) -> None:
    """Install a symlink in primary_text/ that resolves outside the root.

    A literal ``../etc/passwd`` filename is rejected by most filesystems,
    so a symlink in the corpus pointing outside the root is the realistic
    proxy for a path-traversal attempt. The loader's
    ``Path.resolve(strict=True)`` + ``relative_to(root)`` chain catches it.
    """
    outside = corpus_context.root.parent / "outside_secret_for_bdd.txt"
    outside.write_text("secret outside corpus root", encoding="utf-8")
    link = corpus_context.root / "primary_text" / "passwd"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")
    corpus_context.files["traversal_link"] = link
    corpus_context.files["traversal_target"] = outside


# ---------------------------------------------------------------------------
# When step — invoke the production corpus loader
# ---------------------------------------------------------------------------


@when("the corpus is loaded")
def _when_corpus_loaded(corpus_context: CorpusBddContext) -> None:
    """Drive the real :func:`load_corpus` against the scenario's root."""
    corpus_context.result = load_corpus(corpus_context.root)


# ---------------------------------------------------------------------------
# Then steps — assert on the IngestResult
# ---------------------------------------------------------------------------


@then("chunks from the first file should carry the primary-text source type")
def _then_first_file_primary_source_type(
    corpus_context: CorpusBddContext,
) -> None:
    """The Macbeth file → at least one chunk with SourceType.PRIMARY_TEXT."""
    primary_path = corpus_context.files["primary"]
    chunks = [
        c for c in _result(corpus_context).chunks
        if c.source_path == str(primary_path)
    ]
    assert chunks, "expected chunks from the primary-text file"
    assert all(c.source_type is SourceType.PRIMARY_TEXT for c in chunks)


@then(
    "chunks from the second file should carry the secondary study-guide "
    "source type"
)
def _then_second_file_secondary_source_type(
    corpus_context: CorpusBddContext,
) -> None:
    """The York Notes file → at least one chunk with SECONDARY_STUDY_GUIDE."""
    secondary_path = corpus_context.files["secondary_study_guide"]
    chunks = [
        c for c in _result(corpus_context).chunks
        if c.source_path == str(secondary_path)
    ]
    assert chunks, "expected chunks from the secondary-study-guide file"
    assert all(
        c.source_type is SourceType.SECONDARY_STUDY_GUIDE for c in chunks
    )


@then("no chunk should carry an unset or default source-type label")
def _then_no_chunk_has_default_source_type(
    corpus_context: CorpusBddContext,
) -> None:
    """Every chunk's ``source_type`` is a real ``SourceType`` enum member."""
    valid_values = {member.value for member in SourceType}
    for chunk in _result(corpus_context).chunks:
        assert isinstance(chunk.source_type, SourceType)
        assert chunk.source_type.value in valid_values


@then("no chunks should be emitted from that folder")
def _then_no_chunks_from_folder(corpus_context: CorpusBddContext) -> None:
    """Empty primary_text/ → zero chunks under the primary_text folder."""
    primary_root = str(corpus_context.root / "primary_text")
    chunks = [
        c for c in _result(corpus_context).chunks
        if c.source_path.startswith(primary_root)
    ]
    assert not chunks


@then("the loader should report a successful ingestion summary")
def _then_successful_ingestion_summary(
    corpus_context: CorpusBddContext,
) -> None:
    """``load_corpus`` returned an IngestResult — no exception bubbled."""
    result = _result(corpus_context)
    assert isinstance(result, IngestResult)
    # ``chunks_created`` is the summary's load-bearing field.
    assert result.chunks_created >= 0


@then("no chunks should be emitted from that file")
def _then_no_chunks_from_whitespace_file(
    corpus_context: CorpusBddContext,
) -> None:
    """The whitespace-only file produced no chunks."""
    target = corpus_context.files["whitespace"]
    chunks = [
        c for c in _result(corpus_context).chunks
        if c.source_path == str(target)
    ]
    assert not chunks


@then("the loader should record a structured log entry naming the skipped file")
def _then_whitespace_skip_recorded(corpus_context: CorpusBddContext) -> None:
    """A WHITESPACE_ONLY skip record exists naming the file."""
    target = corpus_context.files["whitespace"]
    skips = [
        s for s in _result(corpus_context).skips
        if s.reason is SkipReason.WHITESPACE_ONLY and s.path == str(target)
    ]
    assert skips, "expected whitespace-only skip record naming the file"


@then("the file should not be ingested")
def _then_file_not_ingested(corpus_context: CorpusBddContext) -> None:
    """The candidate refused/rejected file is absent from chunks.

    Resolves the candidate by precedence: AQA → in-copyright → traversal
    link. Each scenario installs exactly one of these, so the lookup is
    unambiguous.
    """
    candidate = (
        corpus_context.files.get("aqa")
        or corpus_context.files.get("in_copyright")
        or corpus_context.files.get("traversal_link")
    )
    assert candidate is not None, "no refused-file candidate registered"
    chunks = [
        c for c in _result(corpus_context).chunks
        if c.source_path == str(candidate)
    ]
    assert not chunks


@then(
    "the loader should record a structured refusal entry naming the "
    "prohibited file"
)
def _then_aqa_refusal_recorded(corpus_context: CorpusBddContext) -> None:
    """An AQA refusal record exists naming the file."""
    target = corpus_context.files["aqa"]
    refusals = [
        r for r in _result(corpus_context).refusals
        if r.reason is RefusalReason.AQA_ASSESSMENT_MATERIAL
        and r.path == str(target)
    ]
    assert refusals, "expected AQA refusal naming the prohibited file"


@then("the refusal should reference the publisher's prohibition")
def _then_refusal_references_publisher_prohibition(
    corpus_context: CorpusBddContext,
) -> None:
    """The AQA refusal detail string mentions the publisher's prohibition."""
    aqa_refusals = [
        r for r in _result(corpus_context).refusals
        if r.reason is RefusalReason.AQA_ASSESSMENT_MATERIAL
    ]
    assert aqa_refusals
    assert any(
        "publisher prohibition" in r.detail.lower() for r in aqa_refusals
    )


@then(
    "the loader should record a structured refusal naming the "
    "in-copyright text"
)
def _then_incopyright_refusal_recorded(
    corpus_context: CorpusBddContext,
) -> None:
    """An IN_COPYRIGHT_TITLE refusal record exists naming the file."""
    target = corpus_context.files["in_copyright"]
    refusals = [
        r for r in _result(corpus_context).refusals
        if r.reason is RefusalReason.IN_COPYRIGHT_TITLE
        and r.path == str(target)
    ]
    assert refusals, "expected in-copyright refusal naming the file"


@then(
    "the loader should advise that the only legitimate route is "
    "per-student licensed material in a future phase"
)
def _then_incopyright_advises_phase_2(
    corpus_context: CorpusBddContext,
) -> None:
    """The in-copyright refusal detail references the per-student Phase 2 path."""
    refusals = [
        r for r in _result(corpus_context).refusals
        if r.reason is RefusalReason.IN_COPYRIGHT_TITLE
    ]
    assert refusals
    assert any("phase 2" in r.detail.lower() for r in refusals), (
        "in-copyright refusal must advise the per-student Phase 2 path"
    )


@then("chunks from the valid file should be emitted")
def _then_valid_file_still_loads(corpus_context: CorpusBddContext) -> None:
    """The valid Macbeth neighbour produced chunks despite the corrupted sibling."""
    valid_path = corpus_context.files["valid"]
    chunks = [
        c for c in _result(corpus_context).chunks
        if c.source_path == str(valid_path)
    ]
    assert chunks, "valid neighbour must still produce chunks"


@then("the corrupted file should be skipped with a structured log entry")
def _then_corrupted_file_skip_recorded(
    corpus_context: CorpusBddContext,
) -> None:
    """A CORRUPTED_FILE skip record exists naming the bad file."""
    corrupted_path = corpus_context.files["corrupted"]
    skips = [
        s for s in _result(corpus_context).skips
        if s.reason is SkipReason.CORRUPTED_FILE
        and s.path == str(corrupted_path)
    ]
    assert skips, "expected corrupted-file skip naming the file"


@then(
    "the loader should report a successful ingestion summary that "
    "names the skipped file"
)
def _then_summary_names_skipped_file(
    corpus_context: CorpusBddContext,
) -> None:
    """The skipped file appears in the result's skips by path."""
    corrupted_path = corpus_context.files["corrupted"]
    result = _result(corpus_context)
    assert isinstance(result, IngestResult)
    assert any(s.path == str(corrupted_path) for s in result.skips)


@then("the file should be rejected")
def _then_traversal_file_rejected(corpus_context: CorpusBddContext) -> None:
    """A PATH_TRAVERSAL refusal record exists for the symlink."""
    link = corpus_context.files["traversal_link"]
    refusals = [
        r for r in _result(corpus_context).refusals
        if r.reason is RefusalReason.PATH_TRAVERSAL
        and r.path == str(link)
    ]
    assert refusals, "expected path-traversal refusal naming the symlink"


@then(
    "the loader should record a structured refusal naming the "
    "path-traversal attempt"
)
def _then_traversal_refusal_named(
    corpus_context: CorpusBddContext,
) -> None:
    """The path-traversal refusal record names the offending path."""
    link = corpus_context.files["traversal_link"]
    refusals = [
        r for r in _result(corpus_context).refusals
        if r.reason is RefusalReason.PATH_TRAVERSAL
    ]
    assert any(str(link) in r.path for r in refusals)


@then("no chunks from that file should be emitted")
def _then_no_chunks_from_traversal_file(
    corpus_context: CorpusBddContext,
) -> None:
    """The traversal-target content never reaches the chunk list."""
    target = corpus_context.files["traversal_target"]
    assert all(
        c.source_path != str(target) for c in _result(corpus_context).chunks
    )
