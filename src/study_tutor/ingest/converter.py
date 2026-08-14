"""The converter port: uploaded file in, markdown out.

One narrow seam between the staging tree and whatever turns a scan into text.
The serving process never calls a converter and never imports one; the
host-side worker picks an implementation per file:

* :class:`PassthroughConverter` — ``.txt`` / ``.md``, copied through with the
  encoding normalised to UTF-8. No dependency, no model, no network.
* ``DoclingConverter`` (C-stage, ``converter_docling.py``) — PDFs and images,
  importing ``docling`` lazily inside the method so the serving image never
  sees it.

Keeping the port here means the worker, its tests, and the docling adapter all
agree on one shape without any of them importing docling to find out what it is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol, runtime_checkable

#: Extensions :class:`PassthroughConverter` handles.
PASSTHROUGH_SUFFIXES: tuple[str, ...] = (".md", ".txt")

#: Extension every converter writes. The corpus loader reads whatever regular
#: files it finds, so this is a convention rather than a filter — but a
#: uniform one keeps the four-folder tree legible to a human.
MARKDOWN_SUFFIX: str = ".md"

#: Decodings tried, in order, when normalising a text file to UTF-8. The
#: fallbacks matter for scanned-and-typed notes that came off a Windows box;
#: ``latin-1`` never fails, so it is the floor rather than a real guess.
_DECODINGS: tuple[str, ...] = ("utf-8-sig", "utf-8", "cp1252", "latin-1")


class ConversionError(Exception):
    """A converter could not produce markdown from the given file."""


@dataclass(frozen=True)
class ConversionNote:
    """One thing worth telling the operator about a produced file.

    Attributes:
        path: The produced file the note is about.
        note: Plain-language detail (e.g. which encoding was assumed).
    """

    path: Path
    note: str


@dataclass(frozen=True)
class ConversionResult:
    """What a converter produced from one source file.

    Attributes:
        produced_paths: Markdown files written into the destination directory,
            in write order.
        notes: Per-file notes, in the order they were raised.
    """

    produced_paths: tuple[Path, ...]
    notes: tuple[ConversionNote, ...] = field(default=())


@runtime_checkable
class Converter(Protocol):
    """Turns one uploaded file into markdown in a destination directory."""

    def convert(self, src: Path, dst_dir: Path) -> ConversionResult:
        """Convert ``src`` into markdown written under ``dst_dir``.

        Args:
            src: The uploaded file.
            dst_dir: Directory to write markdown into; created if absent.

        Returns:
            The :class:`ConversionResult` describing what was written.

        Raises:
            ConversionError: If the file cannot be converted.
        """
        ...


class PassthroughConverter:
    """Copies ``.txt`` / ``.md`` through, normalising the encoding to UTF-8.

    Nothing is parsed or reflowed: text the operator already typed is already
    the thing we want in the corpus. The only change is the encoding (and CRLF
    line endings, so the chunker's paragraph splitting behaves the same
    whatever machine the file came from).
    """

    suffixes: tuple[str, ...] = PASSTHROUGH_SUFFIXES

    def supports(self, src: Path) -> bool:
        """Return whether this converter handles ``src``'s extension."""
        return src.suffix.lower() in self.suffixes

    def convert(self, src: Path, dst_dir: Path) -> ConversionResult:
        """Copy ``src`` into ``dst_dir`` as UTF-8 markdown.

        Args:
            src: A ``.txt`` or ``.md`` file.
            dst_dir: Destination directory; created if absent.

        Returns:
            A result with exactly one produced path, plus a note when the file
            was not already UTF-8 (so a mojibake report has an explanation).

        Raises:
            ConversionError: If the extension is unsupported, the file is
                missing, or it holds no text.
        """
        if not self.supports(src):
            raise ConversionError(
                f"{src.name!r} is not a text file this converter handles "
                f"(it takes {', '.join(self.suffixes)})."
            )
        if not src.is_file():
            raise ConversionError(f"No file to convert at {src}.")

        raw = src.read_bytes()
        text, encoding = _decode(raw, src)
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        if not text.strip():
            raise ConversionError(f"{src.name!r} holds no text to ingest.")

        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = _free_path(dst_dir, src.stem + MARKDOWN_SUFFIX)
        dst.write_text(text, encoding="utf-8")

        notes: list[ConversionNote] = []
        if encoding not in ("utf-8", "utf-8-sig"):
            notes.append(
                ConversionNote(
                    path=dst,
                    note=(
                        f"{src.name!r} was not UTF-8; read as {encoding}. Check "
                        "any accented characters came through."
                    ),
                )
            )
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


def _decode(raw: bytes, src: Path) -> tuple[str, str]:
    """Decode ``raw``, returning the text and the encoding that worked.

    Args:
        raw: The file's bytes.
        src: The source path, for the error message.

    Returns:
        ``(text, encoding_name)``.

    Raises:
        ConversionError: If no candidate decoding succeeds.
    """
    for encoding in _DECODINGS:
        try:
            return raw.decode(encoding), encoding
        except UnicodeDecodeError:
            continue
    raise ConversionError(
        f"{src.name!r} is not readable as text in any of: {', '.join(_DECODINGS)}."
    )


def _free_path(dst_dir: Path, name: str) -> Path:
    """Return ``dst_dir/name``, suffixed with ``-2``, ``-3``… if taken.

    Two uploads with the same filename must not silently overwrite one another
    — losing a scan quietly is worse than an awkward filename.

    Args:
        dst_dir: Destination directory.
        name: Preferred filename.

    Returns:
        A path that does not yet exist.
    """
    candidate = dst_dir / name
    if not candidate.exists():
        return candidate
    stem = Path(name).stem
    suffix = Path(name).suffix
    counter = 2
    while True:
        candidate = dst_dir / f"{stem}-{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1
