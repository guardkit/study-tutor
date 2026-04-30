"""Unit + seam tests for the source-typed corpus loader (TASK-PRV-002).

Each test covers an explicit acceptance criterion on the task spec; comments
note the AC ID for traceability. The seam test at the bottom validates the
integration contract with TASK-PRV-001's ``CorpusChunk`` / ``CitationAnchor``
discriminated union and is the consumer-side test for the SourceTypedCorpus
contract.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from study_tutor.knowledge.corpus import (
    AQA_REFUSAL_PATTERN,
    INCOPYRIGHT_TITLES,
    SOURCE_TYPE_FOLDERS,
    IngestResult,
    RefusalReason,
    SkipReason,
    load_corpus,
)
from study_tutor.knowledge.corpus_models import (
    CorpusChunk,
    NovelCitationAnchor,
    PlayCitationAnchor,
    SourceType,
)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _make_corpus_skeleton(root: Path) -> None:
    """Create the four canonical source-type folders under ``root``."""
    for folder in SOURCE_TYPE_FOLDERS:
        (root / folder).mkdir(parents=True, exist_ok=True)


# A minimal but realistic Macbeth fixture in a Standard-Ebooks-ish shape:
# ACT / Scene markers on their own lines, with line-numbered dialogue
# following. Long enough to produce at least one chunk.
MACBETH_FIXTURE = """\
ACT I
Scene 1
A desert place. Thunder and lightning.
Enter three Witches.
First Witch
When shall we three meet again
In thunder, lightning, or in rain?
Second Witch
When the hurlyburly's done,
When the battle's lost and won.
Third Witch
That will be ere the set of sun.
First Witch
Where the place?
Second Witch
Upon the heath.
Third Witch
There to meet with Macbeth.
"""

# A Christmas Carol-style fixture: CHAPTER heading, then paragraphs separated
# by blank lines.
CHRISTMAS_CAROL_FIXTURE = """\
CHAPTER 1

Marley was dead, to begin with. There is no doubt whatever about that.

The register of his burial was signed by the clergyman, the clerk, the undertaker, and the chief mourner.

Scrooge signed it. And Scrooge's name was good upon 'Change for anything he chose to put his hand to.

Old Marley was as dead as a door-nail.
"""


# ---------------------------------------------------------------------------
# AC: source-type inference per folder + no-default-source-type invariant
# ---------------------------------------------------------------------------


def test_loader_infers_source_type_from_each_of_four_folders(tmp_path: Path) -> None:
    """AC: chunks carry the correct ``source_type`` per parent folder.

    Covers AC "Loading a four-folder corpus produces CorpusChunks with
    correct source_type per folder".
    """
    _make_corpus_skeleton(tmp_path)
    (tmp_path / "primary_text" / "macbeth.txt").write_text(MACBETH_FIXTURE)
    (tmp_path / "secondary_study_guide" / "york_notes.txt").write_text(
        "Study guide notes about Macbeth's ambition theme..."
    )
    (tmp_path / "secondary_critical" / "bradley.txt").write_text(
        "Bradley on Shakespearean tragedy: the tragic hero..."
    )
    (tmp_path / "context_historical" / "jacobean.txt").write_text(
        "Jacobean society and the divine right of kings..."
    )

    result = load_corpus(tmp_path)

    types_seen = {chunk.source_type for chunk in result.chunks}
    assert types_seen == {
        SourceType.PRIMARY_TEXT,
        SourceType.SECONDARY_STUDY_GUIDE,
        SourceType.SECONDARY_CRITICAL,
        SourceType.CONTEXT_HISTORICAL,
    }

    # Spot-check that file→folder routing is correct.
    by_folder = {
        SourceType.PRIMARY_TEXT: "macbeth",
        SourceType.SECONDARY_STUDY_GUIDE: "york_notes",
        SourceType.SECONDARY_CRITICAL: "bradley",
        SourceType.CONTEXT_HISTORICAL: "jacobean",
    }
    for source_type, expected_text_name in by_folder.items():
        sample = next(c for c in result.chunks if c.source_type is source_type)
        assert sample.text_name == expected_text_name


def test_no_chunk_carries_default_or_unset_source_type(tmp_path: Path) -> None:
    """AC: every chunk has a real ``SourceType`` value, no defaults / unsets."""
    _make_corpus_skeleton(tmp_path)
    (tmp_path / "primary_text" / "macbeth.txt").write_text(MACBETH_FIXTURE)
    (tmp_path / "secondary_critical" / "essay.txt").write_text(
        "A critical essay about Macbeth's downfall..."
    )

    result = load_corpus(tmp_path)

    assert result.chunks, "fixture should produce at least one chunk"
    valid_values = {member.value for member in SourceType}
    for chunk in result.chunks:
        assert isinstance(chunk.source_type, SourceType), (
            f"source_type must be a SourceType enum, got {type(chunk.source_type)}"
        )
        assert chunk.source_type.value in valid_values


# ---------------------------------------------------------------------------
# AC: AQA assessment-material refusal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    [
        "past_paper.pdf",
        "Mark-Scheme.pdf",
        "examiner_report_2024.pdf",
        "PastPaper.txt",
        "mark_scheme.txt",
        "examiner-report.pdf",
    ],
)
def test_aqa_pattern_catches_assessment_material_filenames(filename: str) -> None:
    """AC: the AQA regex catches past papers, mark schemes, examiner reports."""
    assert AQA_REFUSAL_PATTERN.search(filename) is not None, (
        f"AQA_REFUSAL_PATTERN failed to match {filename!r}"
    )


def test_aqa_named_file_is_refused_with_publisher_log(tmp_path: Path) -> None:
    """AC: AQA file is refused; refusal log line references publisher prohibition.

    Covers "AQA past-paper-named file is refused; refusal log line references
    publisher prohibition".
    """
    _make_corpus_skeleton(tmp_path)
    (tmp_path / "secondary_study_guide" / "past_paper_2023.pdf").write_text(
        "AQA paper text"
    )

    result = load_corpus(tmp_path)

    aqa_refusals = [
        r for r in result.refusals
        if r.reason is RefusalReason.AQA_ASSESSMENT_MATERIAL
    ]
    assert aqa_refusals, "expected at least one AQA refusal"
    detail = aqa_refusals[0].detail
    assert "AQA" in detail, "refusal detail must mention the publisher"
    assert "publisher prohibition" in detail.lower(), (
        "refusal detail must reference the publisher prohibition"
    )


# ---------------------------------------------------------------------------
# AC: in-copyright deny-list refusal
# ---------------------------------------------------------------------------


def test_incopyright_titles_constant_lists_required_entries() -> None:
    """AC: the in-copyright deny-list contains the six modern set texts."""
    expected = {
        "inspector_calls",
        "blood_brothers",
        "dna",
        "lord_of_the_flies",
        "anita_and_me",
        "animal_farm",
    }
    assert expected <= INCOPYRIGHT_TITLES


@pytest.mark.parametrize("filename", ["inspector_calls.txt", "Inspector-Calls.txt"])
def test_incopyright_match_is_case_insensitive_with_punctuation(
    tmp_path: Path, filename: str
) -> None:
    """AC: deny-list catches both ``inspector_calls.txt`` and ``Inspector-Calls.txt``."""
    _make_corpus_skeleton(tmp_path)
    (tmp_path / "primary_text" / filename).write_text(
        "Some primary-text content that should never be ingested."
    )

    result = load_corpus(tmp_path)

    refusals = [
        r for r in result.refusals if r.reason is RefusalReason.IN_COPYRIGHT_TITLE
    ]
    assert refusals, f"expected refusal for {filename!r}"
    # AC: log advises per-student Phase 2 path.
    assert any("phase 2" in r.detail.lower() for r in refusals), (
        "refusal detail must reference the per-student Phase 2 path"
    )
    # The refused file must NOT have produced any chunks.
    assert all(
        Path(c.source_path).name != filename for c in result.chunks
    ), "refused file must not appear in chunks"


# ---------------------------------------------------------------------------
# AC: path-traversal safety
# ---------------------------------------------------------------------------


def test_symlink_escaping_corpus_root_is_refused(tmp_path: Path) -> None:
    """AC: a path-traversal file is rejected; refusal log names the attempt.

    We model path-traversal via a symlink in ``primary_text/`` that points to
    a file outside the corpus root — that's the realistic shape an attacker /
    misconfigured rsync would produce. A literal ``../etc/passwd`` filename
    can't be created on most filesystems, so symlink redirection is the
    practical proxy used here.
    """
    _make_corpus_skeleton(tmp_path)
    outside_target = tmp_path.parent / "outside_secret_for_corpus_test.txt"
    outside_target.write_text("secret content outside the corpus root")
    link = tmp_path / "primary_text" / "passwd"
    try:
        try:
            os.symlink(outside_target, link)
        except (OSError, NotImplementedError):
            pytest.skip("symlinks not supported on this platform")

        result = load_corpus(tmp_path)

        path_refusals = [
            r for r in result.refusals if r.reason is RefusalReason.PATH_TRAVERSAL
        ]
        assert path_refusals, "expected a path-traversal refusal for symlink"
        # AC: refusal log names the attempt.
        assert any(
            str(link) in r.path or "passwd" in r.path for r in path_refusals
        ), "refusal record must name the offending path"
        # The escaping file must NOT have produced any chunks.
        assert not any(
            "outside_secret" in c.source_path for c in result.chunks
        )
    finally:
        if outside_target.exists():
            outside_target.unlink()


# ---------------------------------------------------------------------------
# AC: corrupted-file resilience
# ---------------------------------------------------------------------------


def test_corrupted_file_is_skipped_and_valid_neighbour_still_loads(
    tmp_path: Path,
) -> None:
    """AC: a corrupted file in primary_text/ is skipped; a valid sibling still loads."""
    _make_corpus_skeleton(tmp_path)
    valid = tmp_path / "primary_text" / "macbeth.txt"
    valid.write_text(MACBETH_FIXTURE)
    bad = tmp_path / "primary_text" / "corrupted.txt"
    # Bytes that can't be decoded as UTF-8 — triggers UnicodeDecodeError on
    # ``read_text`` and routes to the corrupted-file skip branch.
    bad.write_bytes(b"\xff\xfe\xfd\xfc \x80\x81\x82 invalid utf-8")

    result = load_corpus(tmp_path)

    valid_chunks = [c for c in result.chunks if c.text_name == "macbeth"]
    assert valid_chunks, "valid neighbour must still produce chunks"

    corrupted_skips = [
        s for s in result.skips if s.reason is SkipReason.CORRUPTED_FILE
    ]
    assert corrupted_skips, "corrupted file must be recorded as a skip"
    assert any("corrupted" in s.path for s in corrupted_skips)


# ---------------------------------------------------------------------------
# AC: empty primary_text/ folder
# ---------------------------------------------------------------------------


def test_empty_primary_text_folder_produces_zero_chunks_no_error(
    tmp_path: Path,
) -> None:
    """AC: empty primary_text/ folder produces zero chunks and no error."""
    _make_corpus_skeleton(tmp_path)

    result = load_corpus(tmp_path)

    assert isinstance(result, IngestResult)
    assert result.chunks_created == 0
    assert result.chunks == []


# ---------------------------------------------------------------------------
# AC: whitespace-only file is skipped with structured log
# ---------------------------------------------------------------------------


def test_whitespace_only_file_is_skipped(tmp_path: Path) -> None:
    """AC: a whitespace-only file is skipped with a structured log entry."""
    _make_corpus_skeleton(tmp_path)
    (tmp_path / "primary_text" / "blank.txt").write_text("   \n\t\n  \n")

    result = load_corpus(tmp_path)

    assert not result.chunks
    whitespace_skips = [
        s for s in result.skips if s.reason is SkipReason.WHITESPACE_ONLY
    ]
    assert whitespace_skips, "whitespace-only file must be recorded as a skip"


# ---------------------------------------------------------------------------
# AC: citation-anchor inference (plays + novels)
# ---------------------------------------------------------------------------


def test_play_chunks_carry_play_citation_anchor(tmp_path: Path) -> None:
    """AC: plays produce chunks with PlayCitationAnchor (act/scene/line)."""
    _make_corpus_skeleton(tmp_path)
    (tmp_path / "primary_text" / "macbeth.txt").write_text(MACBETH_FIXTURE)

    result = load_corpus(tmp_path)

    primary_chunks = [
        c for c in result.chunks if c.source_type is SourceType.PRIMARY_TEXT
    ]
    assert primary_chunks, "expected primary-text chunks for play"

    anchored = [c for c in primary_chunks if c.citation_anchor is not None]
    assert anchored, "at least one play chunk must carry a citation anchor"
    for chunk in anchored:
        assert isinstance(chunk.citation_anchor, PlayCitationAnchor)
        assert chunk.citation_anchor.act == 1
        assert chunk.citation_anchor.scene == 1
        assert chunk.citation_anchor.line >= 1


def test_novel_chunks_carry_novel_citation_anchor(tmp_path: Path) -> None:
    """AC: novels produce chunks with NovelCitationAnchor (chapter/paragraph)."""
    _make_corpus_skeleton(tmp_path)
    (tmp_path / "primary_text" / "christmas_carol.txt").write_text(
        CHRISTMAS_CAROL_FIXTURE
    )

    result = load_corpus(tmp_path)

    primary_chunks = [
        c for c in result.chunks if c.source_type is SourceType.PRIMARY_TEXT
    ]
    assert primary_chunks, "expected primary-text chunks for novel"

    anchored = [c for c in primary_chunks if c.citation_anchor is not None]
    assert anchored, "at least one novel chunk must carry a citation anchor"
    for chunk in anchored:
        assert isinstance(chunk.citation_anchor, NovelCitationAnchor)
        assert chunk.citation_anchor.chapter == 1
        assert chunk.citation_anchor.paragraph >= 1


# ---------------------------------------------------------------------------
# Defensive: unknown folder is skipped, not silently classified
# ---------------------------------------------------------------------------


def test_unknown_folder_is_skipped_with_warning(tmp_path: Path) -> None:
    """A folder not in SOURCE_TYPE_FOLDERS is skipped — typos must be loud."""
    _make_corpus_skeleton(tmp_path)
    rogue = tmp_path / "primary-text"  # hyphen instead of underscore
    rogue.mkdir()
    (rogue / "stray.txt").write_text("This should not be ingested.")

    result = load_corpus(tmp_path)

    unknown_skips = [s for s in result.skips if s.reason is SkipReason.UNKNOWN_FOLDER]
    assert unknown_skips, "unknown-folder skip must be recorded"
    assert all(c.source_path != str(rogue / "stray.txt") for c in result.chunks)


# ---------------------------------------------------------------------------
# Seam test: integration contract with TASK-PRV-001 models
# ---------------------------------------------------------------------------


@pytest.mark.seam
@pytest.mark.integration_contract("SourceTypedCorpus")
def test_corpus_chunk_carries_typed_citation_anchor(tmp_path: Path) -> None:
    """Seam test: loader emits CorpusChunk with the discriminated union anchor.

    Producer: TASK-PRV-001 (models)
    Consumer: TASK-PRV-002 (this loader); TASK-PRV-005 (verifier reads
    ``citation_anchor`` directly from chunk metadata, never re-parses text).

    Contract: primary-text chunks carry a non-None ``citation_anchor`` of the
    correct kind for the text type, and the value is a real Pydantic model
    (not a plain dict).
    """
    _make_corpus_skeleton(tmp_path)
    (tmp_path / "primary_text" / "macbeth.txt").write_text(MACBETH_FIXTURE)

    result = load_corpus(tmp_path)
    chunks = result.chunks

    primary_play_chunks = [
        c
        for c in chunks
        if c.source_type is SourceType.PRIMARY_TEXT and c.text_name == "macbeth"
    ]

    assert primary_play_chunks, "expected primary-text chunks for play"
    anchored = [c for c in primary_play_chunks if c.citation_anchor is not None]
    assert anchored, "primary-text play chunks must carry citation_anchor"
    for chunk in anchored:
        assert isinstance(chunk, CorpusChunk)
        assert isinstance(chunk.citation_anchor, PlayCitationAnchor), (
            f"plays must carry PlayCitationAnchor, "
            f"got {type(chunk.citation_anchor)}"
        )
