"""Upload-time guards: every refusal, and the order they are applied in.

The order matters as much as the rules: the subject is validated before
anything builds a filesystem path from it, and every content-shaped refusal
happens before a single byte is counted against a quota.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from study_tutor.cli.rag_wiring import (
    SUBJECT_COLLECTION_PATTERN,
    subject_collection_name,
)
from study_tutor.ingest.config import BYTES_PER_MB, UploadConfig
from study_tutor.ingest.errors import (
    FileTooLarge,
    InvalidFilename,
    InvalidSourceType,
    InvalidSubject,
    RefusedMaterial,
    SubjectQuotaExceeded,
    UnsupportedFileType,
)
from study_tutor.ingest.guards import (
    ALLOWED_EXTENSIONS,
    SOURCE_TYPE_NAMES,
    check_upload_request,
    refuse_assessment_material,
    sanitise_filename,
    validate_extension,
    validate_file_size,
    validate_source_type,
    validate_subject,
    validate_subject_quota,
)
from study_tutor.knowledge.corpus import AQA_REFUSAL_PATTERN, SOURCE_TYPE_FOLDERS


@pytest.fixture()
def config() -> UploadConfig:
    return UploadConfig.from_env({})


# ---------------------------------------------------------------------------
# Subject — validated against the registry pattern (seam 3)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("subject", ["english", "demo_history", "a", "b3-x_y"])
def test_valid_subject_slugs(subject: str) -> None:
    assert validate_subject(subject) == subject


@pytest.mark.parametrize(
    "subject",
    [
        "",
        "English",  # upper case
        "3history",  # must start with a letter
        "with space",
        "../escape",
        "history/",
        "history.v2",
        "history\n",
    ],
)
def test_invalid_subject_slugs(subject: str) -> None:
    with pytest.raises(InvalidSubject):
        validate_subject(subject)


def test_subject_validation_is_the_registry_pattern_not_a_copy() -> None:
    """An accepted slug must round-trip to a discoverable collection name."""
    accepted = validate_subject("demo_history")
    collection = subject_collection_name(accepted)

    match = SUBJECT_COLLECTION_PATTERN.fullmatch(collection)
    assert match is not None
    assert match.group("subject") == accepted


# ---------------------------------------------------------------------------
# source_type — the four folder names, imported from the loader (seam 1)
# ---------------------------------------------------------------------------


def test_source_type_names_come_from_the_corpus_loader() -> None:
    assert SOURCE_TYPE_NAMES == tuple(sorted(SOURCE_TYPE_FOLDERS))
    assert set(SOURCE_TYPE_NAMES) == {
        "primary_text",
        "secondary_study_guide",
        "secondary_critical",
        "context_historical",
    }


@pytest.mark.parametrize("source_type", sorted(SOURCE_TYPE_FOLDERS))
def test_each_corpus_folder_is_accepted(source_type: str) -> None:
    assert validate_source_type(source_type) == source_type


@pytest.mark.parametrize(
    "source_type", ["primary-text", "PRIMARY_TEXT", "notes", "", "primary_text/.."]
)
def test_unknown_source_type_refused(source_type: str) -> None:
    with pytest.raises(InvalidSourceType) as exc:
        validate_source_type(source_type)

    # The message names the four so the operator can fix it without the docs.
    for name in SOURCE_TYPE_NAMES:
        assert name in str(exc.value)


# ---------------------------------------------------------------------------
# Filename sanitisation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("scan.pdf", "scan.pdf"),
        ("  scan.pdf  ", "scan.pdf"),
        ("/etc/passwd.txt", "passwd.txt"),
        ("../../../etc/shadow.txt", "shadow.txt"),
        (r"C:\Users\rich\notes.md", "notes.md"),
        ("Macbeth notes (v2).md", "Macbeth notes (v2).md"),
    ],
)
def test_filename_reduced_to_basename(raw: str, expected: str) -> None:
    assert sanitise_filename(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "   ",
        "..",
        ".",
        "scan\x00.pdf",
        "scan\n.pdf",
        "scan\t.pdf",
        ".hidden.pdf",
        "/",
        "a" * 201 + ".pdf",
    ],
)
def test_unsafe_filenames_refused(raw: str) -> None:
    with pytest.raises(InvalidFilename):
        sanitise_filename(raw)


def test_traversal_never_survives_sanitisation() -> None:
    assert "/" not in sanitise_filename("../../evil.txt")
    assert ".." != sanitise_filename("../notes.txt")


# ---------------------------------------------------------------------------
# Extension allowlist
# ---------------------------------------------------------------------------


def test_allowlist_is_the_spec_set() -> None:
    assert set(ALLOWED_EXTENSIONS) == {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".tif",
        ".tiff",
        ".txt",
        ".md",
    }


@pytest.mark.parametrize("suffix", sorted(ALLOWED_EXTENSIONS))
def test_allowed_extensions_accepted_case_insensitively(suffix: str) -> None:
    assert validate_extension(f"scan{suffix}") == suffix
    assert validate_extension(f"scan{suffix.upper()}") == suffix


@pytest.mark.parametrize(
    "filename", ["scan.exe", "notes.docx", "archive.zip", "noextension", "scan.pdf.exe"]
)
def test_unsupported_extensions_refused(filename: str) -> None:
    with pytest.raises(UnsupportedFileType):
        validate_extension(filename)


# ---------------------------------------------------------------------------
# AQA refusal — the loader's regex, imported (seam 1)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename",
    [
        "aqa-past-paper-2019.pdf",
        "Past_Paper_June.pdf",
        "english-mark_scheme.pdf",
        "markscheme.pdf",
        "examiner-report-2021.pdf",
        "EXAMINERREPORT.txt",
    ],
)
def test_assessment_material_refused(filename: str) -> None:
    with pytest.raises(RefusedMaterial) as exc:
        refuse_assessment_material(filename)

    assert "AQA" in str(exc.value)


@pytest.mark.parametrize(
    "filename", ["english mark scheme.pdf", "EXAMINER REPORT.txt", "past paper.pdf"]
)
def test_space_separated_assessment_names_slip_through_today(filename: str) -> None:
    """Honest pin of a gap in the *loader's* regex, not a new rule here.

    ``AQA_REFUSAL_PATTERN`` allows ``_`` or ``-`` between the words but not a
    space, so ``mark scheme.pdf`` is not refused. The upload surface imports
    that regex rather than a widened copy (build spec seam 1: "REUSE it,
    never duplicate it"), so it inherits the gap. Widening is a change to the
    loader, owned by the corpus contract — recorded here so it cannot be
    mistaken for upload-surface behaviour.
    """
    assert AQA_REFUSAL_PATTERN.search(filename) is None
    refuse_assessment_material(filename)


@pytest.mark.parametrize(
    "filename",
    ["specimen-paper.pdf", "Specimen Paper 2024.pdf", "aqa_specimen_paper_1.pdf"],
)
def test_specimen_papers_slip_through_today(filename: str) -> None:
    """The second half of the same honest pin: no ``specimen`` term exists.

    Mission law 4 (``docs/study-tutor-mission-statement-2026-08-01.md``) names
    **four** categories — past papers, mark schemes, examiner reports and
    *specimen papers*. ``AQA_REFUSAL_PATTERN`` implements the first three. A
    specimen paper is therefore accepted by this surface, and the operator is
    the filter (RUNBOOK-upload-surface.md §7, second row).

    Widening the regex is a change to the corpus contract that owns it, not to
    the upload surface — recorded here so the gap cannot be discovered by a
    specimen paper landing in a collection.
    """
    assert AQA_REFUSAL_PATTERN.search(filename) is None
    refuse_assessment_material(filename)


@pytest.mark.parametrize(
    "filename", ["macbeth-notes.pdf", "inspector-calls-guide.md", "context.txt"]
)
def test_ordinary_study_material_not_refused(filename: str) -> None:
    refuse_assessment_material(filename)


# ---------------------------------------------------------------------------
# The runbook's guard table must describe THIS regex, not a wider imagined one
# ---------------------------------------------------------------------------
#
# The operator executes RUNBOOK-upload-surface.md by hand at the scanner. Its
# §7 table and §8 failure modes are the only place the AQA guard's real reach
# is stated, and an over-claim there ("renaming it does not make it
# acceptable") is worse than no claim: it invites the operator to trust a check
# that a single space defeats. These tests fail if the runbook drifts back.

_RUNBOOK = (
    Path(__file__).resolve().parents[3]
    / "docs"
    / "runbooks"
    / "RUNBOOK-upload-surface.md"
)


def _runbook_text() -> str:
    return _RUNBOOK.read_text(encoding="utf-8")


def test_runbook_aqa_row_lists_only_spellings_the_regex_actually_matches() -> None:
    rows = [
        line
        for line in _runbook_text().splitlines()
        if line.startswith("| **AQA assessment material**")
    ]
    assert len(rows) == 1, "§7's AQA row is missing or duplicated"

    spellings = re.findall(r"`([^`]+)`", rows[0])
    assert spellings, "the row must spell out what it matches"
    for spelling in spellings:
        assert AQA_REFUSAL_PATTERN.search(f"{spelling}.pdf"), (
            f"runbook claims {spelling!r} is refused; the regex does not match it"
        )


def test_runbook_states_the_gap_the_regex_leaves() -> None:
    text = _runbook_text()

    assert "What that guard does NOT catch" in text, (
        "§7 must carry the row naming what gets through"
    )
    # The two shapes that get through, each named by example in the runbook.
    assert "mark scheme.pdf" in text
    assert "specimen" in text.lower()

    # And it must not tell the operator that renaming cannot help — it can.
    assert "renaming it does not make it acceptable" not in text


def test_refusal_uses_the_loaders_regex_not_a_copy() -> None:
    """Reuse check: the guard must fire on exactly what the loader refuses."""
    probe = "some-mark_scheme.pdf"
    assert AQA_REFUSAL_PATTERN.search(probe)

    with pytest.raises(RefusedMaterial):
        refuse_assessment_material(probe)


# ---------------------------------------------------------------------------
# Size cap + subject quota
# ---------------------------------------------------------------------------


def test_size_within_cap_passes(config: UploadConfig) -> None:
    assert validate_file_size(1024, config) == 1024


def test_size_over_cap_refused(config: UploadConfig) -> None:
    with pytest.raises(FileTooLarge) as exc:
        validate_file_size(config.max_file_bytes + 1, config)

    assert "STUDY_TUTOR_UPLOAD_MAX_FILE_MB" in str(exc.value)


def test_empty_upload_is_a_client_bug_not_a_policy_refusal(
    config: UploadConfig,
) -> None:
    with pytest.raises(ValueError):
        validate_file_size(0, config)


def test_size_cap_follows_the_env_override() -> None:
    config = UploadConfig.from_env({"STUDY_TUTOR_UPLOAD_MAX_FILE_MB": "1"})

    validate_file_size(BYTES_PER_MB, config)
    with pytest.raises(FileTooLarge):
        validate_file_size(BYTES_PER_MB + 1, config)


def test_quota_allows_a_file_that_exactly_fills_it(config: UploadConfig) -> None:
    used = config.subject_quota_bytes - 10
    validate_subject_quota("english", used, 10, config)


def test_quota_refuses_the_byte_that_overflows(config: UploadConfig) -> None:
    used = config.subject_quota_bytes - 10

    with pytest.raises(SubjectQuotaExceeded) as exc:
        validate_subject_quota("english", used, 11, config)

    assert "english" in str(exc.value)
    assert "STUDY_TUTOR_UPLOAD_SUBJECT_QUOTA_MB" in str(exc.value)


def test_quota_follows_the_env_override() -> None:
    config = UploadConfig.from_env({"STUDY_TUTOR_UPLOAD_SUBJECT_QUOTA_MB": "1"})

    validate_subject_quota("english", 0, BYTES_PER_MB, config)
    with pytest.raises(SubjectQuotaExceeded):
        validate_subject_quota("english", 1, BYTES_PER_MB, config)


# ---------------------------------------------------------------------------
# The orchestrator — order is the contract
# ---------------------------------------------------------------------------


def _check(config: UploadConfig, **overrides: object):
    kwargs: dict[str, object] = {
        "subject": "english",
        "source_type": "secondary_study_guide",
        "filename": "macbeth-notes.pdf",
        "size_bytes": 1024,
        "config": config,
        "staged_bytes": lambda _subject: 0,
    }
    kwargs.update(overrides)
    return check_upload_request(**kwargs)  # type: ignore[arg-type]


def test_valid_request_returns_the_sanitised_values(config: UploadConfig) -> None:
    checked = _check(config, filename="/tmp/scans/macbeth-notes.pdf")

    assert checked.subject == "english"
    assert checked.source_type == "secondary_study_guide"
    assert checked.filename == "macbeth-notes.pdf"
    assert checked.size_bytes == 1024


def test_subject_is_checked_before_any_path_is_built(config: UploadConfig) -> None:
    """The usage reader must not be called with an unvalidated subject."""
    calls: list[str] = []

    with pytest.raises(InvalidSubject):
        _check(config, subject="../../etc", staged_bytes=lambda s: calls.append(s) or 0)

    assert calls == []


def test_quota_is_the_last_guard(config: UploadConfig) -> None:
    """A refused file must never be counted against the subject's quota."""
    calls: list[str] = []

    with pytest.raises(RefusedMaterial):
        _check(
            config,
            filename="past-paper.pdf",
            staged_bytes=lambda s: calls.append(s) or 0,
        )

    assert calls == []


def test_refusals_beat_size_checks(config: UploadConfig) -> None:
    """An oversized past paper is refused as a past paper, not as a big file."""
    with pytest.raises(RefusedMaterial):
        _check(
            config,
            filename="past-paper.pdf",
            size_bytes=config.max_file_bytes + 1,
        )


def test_extension_is_checked_before_the_refusal_regex(config: UploadConfig) -> None:
    """A .zip named 'mark_scheme' is refused for being a .zip — the earlier gate."""
    assert AQA_REFUSAL_PATTERN.search("mark_scheme.zip")

    with pytest.raises(UnsupportedFileType):
        _check(config, filename="mark_scheme.zip")


def test_orchestrator_applies_the_quota(config: UploadConfig) -> None:
    with pytest.raises(SubjectQuotaExceeded):
        _check(
            config,
            size_bytes=1024,
            staged_bytes=lambda _s: config.subject_quota_bytes,
        )
