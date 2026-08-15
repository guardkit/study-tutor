"""The docling converter — scans and PDFs in, markdown out.

This is the ONLY module in the repo that may import ``docling``, and it does so
lazily, inside :meth:`DoclingConverter.convert`. Two reasons, both load-bearing:

* the serving image must never carry docling (or its model stack). Nothing
  under ``src/study_tutor/http/`` or ``src/study_tutor/voice/`` imports this
  module; only the host-side worker (``scripts/process_uploads.py``) does;
* the dev path must stay installable without it. ``docling`` ships in the
  optional ``[ingest]`` extra, so a repo without that extra can still import
  this module, construct the converter, and run its tests — the ImportError
  only happens if you actually ask it to convert something, and then it says
  which command to run.

The output contract is the shared one (:mod:`study_tutor.ingest.converter`):
markdown files written into a destination directory, described by a
:class:`~study_tutor.ingest.converter.ConversionResult`.
"""

from __future__ import annotations

from pathlib import Path

from study_tutor.ingest.converter import (
    MARKDOWN_SUFFIX,
    ConversionError,
    ConversionNote,
    ConversionResult,
    _free_path,
)

#: Extensions this converter handles — the upload allowlist minus the two
#: passthrough text types. Scans (images) and PDFs are exactly the things a
#: document-understanding model is needed for.
DOCLING_SUFFIXES: tuple[str, ...] = (
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
)

#: What the operator is told when the extra is not installed. It names the
#: command rather than the package: the pin lives in ``pyproject.toml`` and a
#: bare ``pip install docling`` would drift from it.
DOCLING_MISSING_MESSAGE: str = (
    "docling is not installed, so scans and PDFs cannot be converted. "
    "Install the ingest extra on the worker host: uv sync --extra ingest "
    "(the upload worker is the only thing that needs it — the serving image "
    "does not)."
)


class DoclingConverter:
    """Converts a scan or PDF to markdown with docling.

    Nothing is imported, downloaded, or loaded at construction time: building
    one of these is free, so the worker can hold an instance whether or not the
    ``[ingest]`` extra is installed and only pay for docling when a job
    actually needs it.
    """

    suffixes: tuple[str, ...] = DOCLING_SUFFIXES

    def supports(self, src: Path) -> bool:
        """Return whether this converter handles ``src``'s extension."""
        return src.suffix.lower() in self.suffixes

    def convert(self, src: Path, dst_dir: Path) -> ConversionResult:
        """Convert ``src`` into one markdown file under ``dst_dir``.

        Args:
            src: The uploaded scan or PDF.
            dst_dir: Destination directory; created if absent.

        Returns:
            A result with exactly one produced path, plus a note when the
            filename had to be de-collided.

        Raises:
            ConversionError: If docling is not installed (with the install
                command), the extension is unsupported, the file is missing, or
                docling produced no text.
        """
        if not self.supports(src):
            raise ConversionError(
                f"{src.name!r} is not a scan or PDF this converter handles "
                f"(it takes {', '.join(self.suffixes)})."
            )
        if not src.is_file():
            raise ConversionError(f"No file to convert at {src}.")

        document_converter = self._document_converter()
        try:
            # A ``Path``, not a string: docling's ``convert`` also accepts URLs
            # and fetches them, and a path is the only thing this converter
            # should ever be pointed at.
            converted = document_converter.convert(src)
            markdown = converted.document.export_to_markdown()
        except Exception as exc:  # noqa: BLE001 — docling raises its own zoo
            raise ConversionError(
                f"docling could not read {src.name!r}: {type(exc).__name__}: {exc}"
            ) from exc

        if not markdown or not markdown.strip():
            raise ConversionError(
                f"docling found no text in {src.name!r}. If it is a photo of a "
                "page, try a flatter, better-lit scan."
            )

        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = _free_path(dst_dir, src.stem + MARKDOWN_SUFFIX)
        dst.write_text(markdown, encoding="utf-8")

        notes: list[ConversionNote] = []
        if dst.name != src.stem + MARKDOWN_SUFFIX:
            notes.append(
                ConversionNote(
                    path=dst,
                    note=(
                        f"{src.stem + MARKDOWN_SUFFIX!r} already existed in "
                        f"{dst_dir.name}/, so this was written as {dst.name!r}."
                    ),
                )
            )
        return ConversionResult(produced_paths=(dst,), notes=tuple(notes))

    @staticmethod
    def _document_converter() -> object:
        """Import docling and return a fresh ``DocumentConverter``.

        The import is here — inside the method, not at module scope — so that
        importing this module costs nothing and an absent extra fails at the
        moment of use with an actionable message rather than at import time in
        some unrelated process.

        Returns:
            A ``docling.document_converter.DocumentConverter`` instance.

        Raises:
            ConversionError: If docling cannot be imported.
        """
        try:
            from docling.document_converter import (  # type: ignore[import-not-found]
                DocumentConverter,
            )
        except ImportError as exc:
            raise ConversionError(DOCLING_MISSING_MESSAGE) from exc
        return DocumentConverter()


__all__ = [
    "DOCLING_MISSING_MESSAGE",
    "DOCLING_SUFFIXES",
    "DoclingConverter",
]
