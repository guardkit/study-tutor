"""The docling adapter — tested with a mocked docling module.

``docling`` ships in the optional ``[ingest]`` extra and is deliberately absent
from the dev/serving path, so these tests never depend on it being installed:
the import seam is a fake module in :data:`sys.modules`, and the
not-installed path is pinned just as hard as the happy one.
"""

from __future__ import annotations

import ast
import sys
import types
from pathlib import Path

import pytest

from study_tutor.ingest.converter import ConversionError
from study_tutor.ingest.converter_docling import (
    DOCLING_MISSING_MESSAGE,
    DoclingConverter,
)


class _FakeDocument:
    def __init__(self, markdown: str) -> None:
        self._markdown = markdown

    def export_to_markdown(self) -> str:
        return self._markdown


class _FakeConversion:
    def __init__(self, markdown: str) -> None:
        self.document = _FakeDocument(markdown)


def _install_fake_docling(
    monkeypatch: pytest.MonkeyPatch,
    *,
    markdown: str = "# Scanned page\n\nSome recognised text.\n",
    raises: Exception | None = None,
) -> list[str]:
    """Put a fake ``docling.document_converter`` in ``sys.modules``.

    Args:
        monkeypatch: Pytest's patcher (undoes the module insertion after).
        markdown: What the fake converter's document exports.
        raises: Exception the fake ``convert`` raises instead of returning.

    Returns:
        A list that records every source path handed to ``convert``.
    """
    seen: list[Path] = []

    class DocumentConverter:
        def convert(self, source: Path):  # noqa: ANN202 — fake of a third-party API
            seen.append(source)
            if raises is not None:
                raise raises
            return _FakeConversion(markdown)

    docling = types.ModuleType("docling")
    document_converter = types.ModuleType("docling.document_converter")
    document_converter.DocumentConverter = DocumentConverter  # type: ignore[attr-defined]
    docling.document_converter = document_converter  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "docling", docling)
    monkeypatch.setitem(sys.modules, "docling.document_converter", document_converter)
    return seen


def _uninstall_docling(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``import docling.document_converter`` raise, installed or not."""
    monkeypatch.setitem(sys.modules, "docling", None)
    monkeypatch.setitem(sys.modules, "docling.document_converter", None)


def test_convert_writes_docling_markdown_into_the_destination(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen = _install_fake_docling(monkeypatch, markdown="# Act 1\n\nEnter Macbeth.\n")
    src = tmp_path / "scan.pdf"
    src.write_bytes(b"%PDF-1.7 not really a pdf")
    dst_dir = tmp_path / "primary_text"

    result = DoclingConverter().convert(src, dst_dir)

    # A path, never a string: docling's convert() would fetch a URL-shaped one.
    assert seen == [src]
    assert result.produced_paths == (dst_dir / "scan.md",)
    assert (dst_dir / "scan.md").read_text(encoding="utf-8") == (
        "# Act 1\n\nEnter Macbeth.\n"
    )
    assert result.notes == ()


def test_convert_without_docling_says_which_command_installs_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _uninstall_docling(monkeypatch)
    src = tmp_path / "scan.pdf"
    src.write_bytes(b"%PDF-1.7")

    with pytest.raises(ConversionError) as excinfo:
        DoclingConverter().convert(src, tmp_path / "out")

    message = str(excinfo.value)
    assert message == DOCLING_MISSING_MESSAGE
    assert "uv sync --extra ingest" in message
    assert not (tmp_path / "out").exists()


def test_a_second_scan_of_the_same_name_does_not_overwrite_the_first(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_docling(monkeypatch, markdown="page two\n")
    dst_dir = tmp_path / "primary_text"
    dst_dir.mkdir()
    (dst_dir / "scan.md").write_text("page one\n", encoding="utf-8")
    src = tmp_path / "scan.png"
    src.write_bytes(b"\x89PNG")

    result = DoclingConverter().convert(src, dst_dir)

    assert result.produced_paths == (dst_dir / "scan-2.md",)
    assert (dst_dir / "scan.md").read_text(encoding="utf-8") == "page one\n"
    assert len(result.notes) == 1
    assert "scan-2.md" in result.notes[0].note


def test_convert_refuses_a_file_type_it_does_not_handle(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # docling is not even importable here: an unsupported extension must be
    # refused before the import is reached.
    _uninstall_docling(monkeypatch)
    src = tmp_path / "notes.txt"
    src.write_text("typed notes\n", encoding="utf-8")

    with pytest.raises(ConversionError, match="not a scan or PDF"):
        DoclingConverter().convert(src, tmp_path / "out")


def test_convert_refuses_a_missing_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_docling(monkeypatch)

    with pytest.raises(ConversionError, match="No file to convert"):
        DoclingConverter().convert(tmp_path / "gone.pdf", tmp_path / "out")


def test_docling_failure_becomes_a_conversion_error_naming_the_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_docling(monkeypatch, raises=RuntimeError("model weights missing"))
    src = tmp_path / "chapter.pdf"
    src.write_bytes(b"%PDF-1.7")

    with pytest.raises(ConversionError) as excinfo:
        DoclingConverter().convert(src, tmp_path / "out")

    assert "chapter.pdf" in str(excinfo.value)
    assert "model weights missing" in str(excinfo.value)


def test_a_scan_with_no_recognised_text_fails_rather_than_staging_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _install_fake_docling(monkeypatch, markdown="   \n\n")
    src = tmp_path / "blank.jpg"
    src.write_bytes(b"\xff\xd8\xff")

    with pytest.raises(ConversionError, match="no text"):
        DoclingConverter().convert(src, tmp_path / "out")

    assert not (tmp_path / "out").exists()


def test_supports_covers_the_scan_half_of_the_upload_allowlist() -> None:
    """Every accepted extension is handled by exactly one of the two converters."""
    from study_tutor.ingest.converter import PASSTHROUGH_SUFFIXES
    from study_tutor.ingest.guards import ALLOWED_EXTENSIONS

    converter = DoclingConverter()
    for suffix in ALLOWED_EXTENSIONS:
        handled_by_passthrough = suffix in PASSTHROUGH_SUFFIXES
        assert converter.supports(Path("f" + suffix)) == (not handled_by_passthrough), (
            f"{suffix} must be handled by exactly one of the two converters"
        )


def test_the_module_imports_docling_only_inside_a_function() -> None:
    """The fence: no module-level docling import, anywhere in this adapter.

    A top-level import would put docling on the import path of anything that
    imports the ingest package — including, one refactor later, the serving
    image the spec keeps it out of.
    """
    import study_tutor.ingest.converter_docling as module

    tree = ast.parse(Path(module.__file__).read_text(encoding="utf-8"))
    top_level_imports: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.Import):
            top_level_imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            top_level_imports.append(node.module or "")

    assert not [name for name in top_level_imports if name.startswith("docling")], (
        f"docling must not be imported at module level; found {top_level_imports}"
    )
