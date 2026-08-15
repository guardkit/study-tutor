"""The converter port and the passthrough implementation.

No docling anywhere in this module — that adapter is C-stage, and the point of
the port is that neither this test nor the worker's tests need it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from study_tutor.ingest.converter import (
    MARKDOWN_SUFFIX,
    PASSTHROUGH_SUFFIXES,
    ConversionError,
    ConversionNote,
    ConversionResult,
    Converter,
    PassthroughConverter,
)


@pytest.fixture()
def converter() -> PassthroughConverter:
    return PassthroughConverter()


@pytest.fixture()
def dst(tmp_path: Path) -> Path:
    return tmp_path / "sources" / "secondary_study_guide"


# ---------------------------------------------------------------------------
# The port
# ---------------------------------------------------------------------------


def test_passthrough_satisfies_the_converter_protocol(
    converter: PassthroughConverter,
) -> None:
    assert isinstance(converter, Converter)


def test_a_stub_converter_satisfies_the_protocol_too() -> None:
    """The port must be implementable without importing anything of ours."""

    class StubConverter:
        def convert(self, src: Path, dst_dir: Path) -> ConversionResult:
            return ConversionResult(produced_paths=(dst_dir / "stub.md",))

    assert isinstance(StubConverter(), Converter)


def test_conversion_result_defaults_to_no_notes(tmp_path: Path) -> None:
    result = ConversionResult(produced_paths=(tmp_path / "a.md",))

    assert result.notes == ()


def test_conversion_result_is_frozen(tmp_path: Path) -> None:
    result = ConversionResult(produced_paths=(tmp_path / "a.md",))

    with pytest.raises(Exception):
        result.produced_paths = ()  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PassthroughConverter
# ---------------------------------------------------------------------------


def test_it_handles_exactly_txt_and_md() -> None:
    assert set(PASSTHROUGH_SUFFIXES) == {".txt", ".md"}


@pytest.mark.parametrize("name", ["notes.txt", "notes.md", "notes.TXT", "notes.MD"])
def test_supports_is_case_insensitive(
    converter: PassthroughConverter, name: str
) -> None:
    assert converter.supports(Path(name))


@pytest.mark.parametrize("name", ["scan.pdf", "scan.png", "notes"])
def test_does_not_claim_files_it_cannot_convert(
    converter: PassthroughConverter, name: str
) -> None:
    assert not converter.supports(Path(name))


def test_markdown_copies_through_unchanged(
    converter: PassthroughConverter, tmp_path: Path, dst: Path
) -> None:
    src = tmp_path / "macbeth-notes.md"
    src.write_text("# Macbeth\n\nAmbition, and what it costs.\n", encoding="utf-8")

    result = converter.convert(src, dst)

    assert len(result.produced_paths) == 1
    produced = result.produced_paths[0]
    assert produced == dst / "macbeth-notes.md"
    assert produced.read_text(encoding="utf-8") == (
        "# Macbeth\n\nAmbition, and what it costs.\n"
    )
    assert result.notes == ()


def test_text_becomes_markdown(
    converter: PassthroughConverter, tmp_path: Path, dst: Path
) -> None:
    src = tmp_path / "context.txt"
    src.write_text("Jacobean England, briefly.\n", encoding="utf-8")

    produced = converter.convert(src, dst).produced_paths[0]

    assert produced.name == "context" + MARKDOWN_SUFFIX
    assert produced.read_text(encoding="utf-8") == "Jacobean England, briefly.\n"


def test_the_destination_directory_is_created(
    converter: PassthroughConverter, tmp_path: Path, dst: Path
) -> None:
    src = tmp_path / "notes.txt"
    src.write_text("hello\n", encoding="utf-8")
    assert not dst.exists()

    converter.convert(src, dst)

    assert dst.is_dir()


def test_a_utf8_bom_is_stripped(
    converter: PassthroughConverter, tmp_path: Path, dst: Path
) -> None:
    src = tmp_path / "bom.txt"
    src.write_bytes("﻿Lady Macbeth\n".encode("utf-8"))

    result = converter.convert(src, dst)

    assert result.produced_paths[0].read_text(encoding="utf-8") == "Lady Macbeth\n"
    assert result.notes == ()


def test_a_windows_encoded_file_is_normalised_and_noted(
    converter: PassthroughConverter, tmp_path: Path, dst: Path
) -> None:
    src = tmp_path / "curly.txt"
    src.write_bytes("The Inspector’s entrance\n".encode("cp1252"))

    result = converter.convert(src, dst)

    produced = result.produced_paths[0]
    assert produced.read_text(encoding="utf-8") == "The Inspector’s entrance\n"
    assert produced.read_bytes().decode("utf-8")  # it really is UTF-8 on disk
    assert len(result.notes) == 1
    assert isinstance(result.notes[0], ConversionNote)
    assert result.notes[0].path == produced
    assert "cp1252" in result.notes[0].note


def test_crlf_line_endings_are_normalised(
    converter: PassthroughConverter, tmp_path: Path, dst: Path
) -> None:
    src = tmp_path / "windows.txt"
    src.write_bytes(b"one\r\ntwo\r\n")

    produced = converter.convert(src, dst).produced_paths[0]

    assert produced.read_bytes() == b"one\ntwo\n"


def test_a_name_clash_does_not_overwrite_the_earlier_file(
    converter: PassthroughConverter, tmp_path: Path, dst: Path
) -> None:
    first = tmp_path / "a" / "notes.txt"
    second = tmp_path / "b" / "notes.txt"
    for path, text in ((first, "first scan\n"), (second, "second scan\n")):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    converter.convert(first, dst)
    result = converter.convert(second, dst)

    assert (dst / "notes.md").read_text(encoding="utf-8") == "first scan\n"
    assert result.produced_paths[0] == dst / "notes-2.md"
    assert result.produced_paths[0].read_text(encoding="utf-8") == "second scan\n"
    assert any("already existed" in note.note for note in result.notes)


def test_an_unsupported_extension_is_a_clear_error(
    converter: PassthroughConverter, tmp_path: Path, dst: Path
) -> None:
    src = tmp_path / "scan.pdf"
    src.write_bytes(b"%PDF-1.7\n")

    with pytest.raises(ConversionError) as exc:
        converter.convert(src, dst)

    assert ".txt" in str(exc.value)
    assert not dst.exists()


def test_a_missing_file_is_a_clear_error(
    converter: PassthroughConverter, tmp_path: Path, dst: Path
) -> None:
    with pytest.raises(ConversionError):
        converter.convert(tmp_path / "gone.txt", dst)


def test_an_empty_file_is_refused_rather_than_ingested_as_nothing(
    converter: PassthroughConverter, tmp_path: Path, dst: Path
) -> None:
    src = tmp_path / "blank.txt"
    src.write_text("   \n\n", encoding="utf-8")

    with pytest.raises(ConversionError):
        converter.convert(src, dst)

    assert not (dst / "blank.md").exists()
