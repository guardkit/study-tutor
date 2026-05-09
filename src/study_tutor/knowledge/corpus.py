"""Source-typed corpus loader with copyright refusal (TASK-PRV-002).

This module is the on-disk ingestion surface for the primary-text-RAG-and-quote
verifier pipeline (FEAT-PRV4 / FEAT-PH1-004). It walks a four-folder corpus
tree, infers ``SourceType`` from the parent directory name, refuses copyrighted
material at the loader (so no ChromaDB write ever sees it), chunks each text
file with a citation-anchor metadata, and returns a typed
:class:`IngestResult`.

Folder layout (one canonical root per corpus):

    <root>/
      primary_text/            -> SourceType.PRIMARY_TEXT
      secondary_study_guide/   -> SourceType.SECONDARY_STUDY_GUIDE
      secondary_critical/      -> SourceType.SECONDARY_CRITICAL
      context_historical/      -> SourceType.CONTEXT_HISTORICAL

Anything outside those four folders is skipped with a structured log line —
the loader is intentionally strict about what counts as a recognised corpus
folder so that a typo (``primary-text`` vs ``primary_text``) is loud, not
silent.

Refusal vs. skip vs. error
--------------------------
* **Refusal** — material we *could* read but legally must not ingest in bulk
  (AQA assessment material, files outside the corpus root via
  path-traversal symlinks). Refusals are logged with the reason and
  reference the publisher prohibition so future engineers understand *why*
  a perfectly readable file was dropped.
* **Skip** — a file we tried to read but couldn't usefully consume
  (whitespace-only, binary/corrupted, unknown folder). Skips are logged so
  the corpus owner can audit what didn't make it in. The rest of the corpus
  still loads.
* **Error** — only raised for missing corpus root. Anything per-file is a
  refusal or skip; one bad file must not blow up ingestion of the others.

Why no ChromaDB call here
-------------------------
``load_corpus`` returns chunks; persistence is a separate concern. The
verifier (TASK-PRV-005) will read chunks back from ChromaDB without ever
re-parsing source text, so the loader's job ends at producing well-typed
:class:`CorpusChunk` records. Wiring them into ``chroma/gcse-english/`` is
deferred to a thin caller that imports ``chromadb`` lazily — keeping the
loader testable without an optional binary dependency on the dev path.

Citation-anchor inference is best-effort
----------------------------------------
Standard Ebooks markup is regular but not perfectly machine-readable. When
inference can't determine a full anchor (act+scene+line for plays, or
chapter+paragraph for novels) we set ``citation_anchor=None`` and emit a
structured warning. The verifier treats ``None`` as "no anchor available"
rather than blocking ingestion on perfect parsing.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Iterator

from study_tutor.knowledge.corpus_models import (
    CitationAnchor,
    CorpusChunk,
    NovelCitationAnchor,
    PlayCitationAnchor,
    SourceType,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Constants — folder layout, refusal patterns, chunker tuning
# ---------------------------------------------------------------------------

# Each canonical leaf folder maps to exactly one ``SourceType``. The loader
# infers source-type from the immediate parent directory name; a typo or
# unexpected folder is skipped with a warning rather than silently classified.
SOURCE_TYPE_FOLDERS: dict[str, SourceType] = {
    "primary_text": SourceType.PRIMARY_TEXT,
    "secondary_study_guide": SourceType.SECONDARY_STUDY_GUIDE,
    "secondary_critical": SourceType.SECONDARY_CRITICAL,
    "context_historical": SourceType.CONTEXT_HISTORICAL,
}

# AQA assessment-material refusal regex per task spec. Matches filenames
# (case-insensitive) that look like past papers, mark schemes, or examiner
# reports — AQA prohibits redistribution of these materials, so the loader
# refuses them at the folder boundary regardless of their parent source-type.
AQA_REFUSAL_PATTERN: re.Pattern[str] = re.compile(
    r"(?i)(past[_-]?paper|mark[_-]?scheme|examiner[_-]?report)"
)

# Chunker tuning: 23-Apr empirical findings §3d.
CHUNK_SIZE: int = 512
CHUNK_OVERLAP: int = 100


class RefusalReason(str, Enum):
    """Why a candidate corpus file was *refused* (legal/policy gate)."""

    AQA_ASSESSMENT_MATERIAL = "AQA_ASSESSMENT_MATERIAL"
    PATH_TRAVERSAL = "PATH_TRAVERSAL"


class SkipReason(str, Enum):
    """Why a candidate corpus file was *skipped* (couldn't usefully ingest)."""

    UNKNOWN_FOLDER = "UNKNOWN_FOLDER"
    WHITESPACE_ONLY = "WHITESPACE_ONLY"
    CORRUPTED_FILE = "CORRUPTED_FILE"
    EMPTY_FILE = "EMPTY_FILE"


@dataclass(frozen=True)
class RefusalRecord:
    """Structured record of a refused file. Mirrors the structured log line."""

    path: str
    reason: RefusalReason
    detail: str


@dataclass(frozen=True)
class SkipRecord:
    """Structured record of a skipped file. Mirrors the structured log line."""

    path: str
    reason: SkipReason
    detail: str


@dataclass
class IngestResult:
    """Outcome of a corpus walk: chunks produced + refusals + skips.

    ``chunks_created`` is exposed as a property so callers (and tests) can
    assert on the count directly, matching the AC vocabulary.
    """

    chunks: list[CorpusChunk] = field(default_factory=list)
    refusals: list[RefusalRecord] = field(default_factory=list)
    skips: list[SkipRecord] = field(default_factory=list)

    @property
    def chunks_created(self) -> int:
        return len(self.chunks)


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def load_corpus(root: Path) -> IngestResult:
    """Walk a four-folder source tree and return an :class:`IngestResult`.

    Each top-level subfolder of ``root`` is matched against
    :data:`SOURCE_TYPE_FOLDERS`; unrecognised folders are skipped with a
    structured warning. Each file inside a recognised folder is run through
    the refusal gates (path-traversal, AQA) before being chunked into
    :class:`CorpusChunk` records.

    The loader is robust to corrupted files: a per-file failure is logged
    and skipped, but the rest of the corpus still loads. The only error
    that aborts the whole walk is a missing / non-directory ``root``.
    """
    resolved_root = Path(root).resolve()
    if not resolved_root.is_dir():
        raise FileNotFoundError(
            f"Corpus root not found or not a directory: {resolved_root}"
        )

    result = IngestResult()
    for child in sorted(resolved_root.iterdir()):
        if not child.is_dir():
            # Stray top-level files (READMEs, etc.) are not part of the
            # source-typed corpus; they're ignored without ceremony.
            continue
        source_type = SOURCE_TYPE_FOLDERS.get(child.name)
        if source_type is None:
            record = SkipRecord(
                path=str(child),
                reason=SkipReason.UNKNOWN_FOLDER,
                detail=(
                    f"Folder {child.name!r} is not one of the four canonical "
                    "source-type folders; skipped."
                ),
            )
            result.skips.append(record)
            logger.warning(
                "corpus.skip.unknown_folder",
                extra={"path": record.path, "detail": record.detail},
            )
            continue
        for file_path in sorted(_iter_files(child)):
            _process_file(file_path, resolved_root, source_type, result)
    return result


# ---------------------------------------------------------------------------
# Per-file processing
# ---------------------------------------------------------------------------


def _iter_files(folder: Path) -> Iterator[Path]:
    """Yield every regular file under ``folder`` recursively."""
    for entry in folder.rglob("*"):
        if entry.is_file():
            yield entry


def _process_file(
    file_path: Path,
    root: Path,
    source_type: SourceType,
    result: IngestResult,
) -> None:
    """Run one file through the refusal/skip gates and chunker."""
    # Path-traversal guard: a symlink (or any other indirection) whose
    # resolved target escapes the corpus root is refused. Resolving with
    # ``strict=True`` collapses ``..`` segments and follows symlinks, which
    # is the form of path-traversal we care about in a curated corpus.
    try:
        resolved_path = file_path.resolve(strict=True)
    except OSError as exc:
        record = SkipRecord(
            path=str(file_path),
            reason=SkipReason.CORRUPTED_FILE,
            detail=f"Failed to resolve path: {exc}",
        )
        result.skips.append(record)
        logger.warning(
            "corpus.skip.resolve_failed",
            extra={"path": record.path, "detail": record.detail},
        )
        return

    try:
        resolved_path.relative_to(root)
    except ValueError:
        record = RefusalRecord(
            path=str(file_path),
            reason=RefusalReason.PATH_TRAVERSAL,
            detail=(
                f"Path-traversal attempt: {file_path!s} resolves to "
                f"{resolved_path!s}, which is outside the corpus root {root!s}."
            ),
        )
        result.refusals.append(record)
        logger.warning(
            "corpus.refusal.path_traversal",
            extra={"path": record.path, "detail": record.detail},
        )
        return

    name = file_path.name

    # AQA refusal — filename pattern-match. Applied across all source-type
    # folders because misfiled material must never leak into the index.
    if AQA_REFUSAL_PATTERN.search(name):
        record = RefusalRecord(
            path=str(file_path),
            reason=RefusalReason.AQA_ASSESSMENT_MATERIAL,
            detail=(
                "AQA assessment material (past paper / mark scheme / examiner "
                "report) refused per AQA publisher prohibition on redistribution."
            ),
        )
        result.refusals.append(record)
        logger.warning(
            "corpus.refusal.aqa_assessment_material",
            extra={"path": record.path, "detail": record.detail},
        )
        return

    try:
        text = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as exc:
        record = SkipRecord(
            path=str(file_path),
            reason=SkipReason.CORRUPTED_FILE,
            detail=f"Failed to read as UTF-8 text: {type(exc).__name__}: {exc}",
        )
        result.skips.append(record)
        logger.warning(
            "corpus.skip.corrupted_file",
            extra={"path": record.path, "detail": record.detail},
        )
        return

    if not text:
        record = SkipRecord(
            path=str(file_path),
            reason=SkipReason.EMPTY_FILE,
            detail="File is zero bytes.",
        )
        result.skips.append(record)
        logger.info("corpus.skip.empty_file", extra={"path": record.path})
        return

    if not text.strip():
        record = SkipRecord(
            path=str(file_path),
            reason=SkipReason.WHITESPACE_ONLY,
            detail="File contains only whitespace.",
        )
        result.skips.append(record)
        logger.warning(
            "corpus.skip.whitespace_only",
            extra={"path": record.path, "detail": record.detail},
        )
        return

    text_name = _derive_text_name(file_path)
    chunks = _chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
    for idx, (chunk_text, start_offset) in enumerate(chunks):
        anchor: CitationAnchor | None = None
        if source_type is SourceType.PRIMARY_TEXT:
            anchor = _infer_citation_anchor(text, start_offset)
            if anchor is None:
                logger.warning(
                    "corpus.citation_anchor.inference_failed",
                    extra={
                        "path": str(file_path),
                        "chunk_index": idx,
                        "char_offset": start_offset,
                    },
                )
        result.chunks.append(
            CorpusChunk(
                text=chunk_text,
                source_type=source_type,
                source_path=str(file_path),
                text_name=text_name,
                citation_anchor=anchor,
                chunk_index=idx,
            )
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _derive_text_name(path: Path) -> str:
    """Derive the human-facing ``text_name`` from a file path.

    Uses the file's stem; pre-normalises common punctuation back to single
    words (``inspector-calls`` -> ``inspector_calls``) so that downstream
    grouping by ``text_name`` is stable across filename variants.
    """
    stem = path.stem.strip()
    if not stem:
        return "unknown"
    return re.sub(r"[-\s.]+", "_", stem.lower())


def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[tuple[str, int]]:
    """Slice ``text`` into overlapping chunks, returning (chunk, start_offset).

    Adapted from agentic-dataset-factory's ``ingestion/chunker.py`` (a
    ``RecursiveCharacterTextSplitter`` wrapper). We don't import the full
    LangChain splitter because the cross-repo coupling cost dwarfs the
    30-line splitter we actually need (see Implementation Notes in the
    task spec). The 512/100 settings come from the 23-Apr empirical finding.
    """
    if not text:
        return []
    step = max(1, chunk_size - overlap)
    chunks: list[tuple[str, int]] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + chunk_size, n)
        # Prefer a paragraph or line boundary near the right edge so a
        # chunk doesn't end mid-word when there's a clean break available.
        if end < n:
            for separator in ("\n\n", "\n", ". ", " "):
                boundary = text.rfind(separator, start, end)
                if boundary != -1 and boundary > start + chunk_size // 2:
                    end = boundary + len(separator)
                    break
        piece = text[start:end].strip()
        if piece:
            chunks.append((piece, start))
        if end >= n:
            break
        start = max(start + step, end - overlap)
    return chunks


# ---------------------------------------------------------------------------
# Citation-anchor inference
# ---------------------------------------------------------------------------

_ROMAN_TO_INT: dict[str, int] = {
    "i": 1,
    "ii": 2,
    "iii": 3,
    "iv": 4,
    "v": 5,
    "vi": 6,
    "vii": 7,
    "viii": 8,
    "ix": 9,
    "x": 10,
}

_ACT_PATTERN = re.compile(r"^\s*act\s+([ivxlcdm]+|\d+)\b", re.IGNORECASE)
_SCENE_PATTERN = re.compile(r"^\s*scene\s+([ivxlcdm]+|\d+)\b", re.IGNORECASE)
_CHAPTER_PATTERN = re.compile(r"^\s*chapter\s+([ivxlcdm]+|\d+)\b", re.IGNORECASE)


def _parse_roman_or_int(token: str) -> int | None:
    """Parse ``"3"`` or ``"III"`` into an int. Returns ``None`` on failure."""
    cleaned = token.strip().lower()
    if cleaned.isdigit():
        return int(cleaned)
    return _ROMAN_TO_INT.get(cleaned)


def _infer_citation_anchor(file_text: str, char_offset: int) -> CitationAnchor | None:
    """Pick the right anchor inferer based on the file's structural markers."""
    if _ACT_PATTERN.search(file_text):
        return _infer_play_anchor(file_text, char_offset)
    if _CHAPTER_PATTERN.search(file_text):
        return _infer_novel_anchor(file_text, char_offset)
    return None


def _infer_play_anchor(file_text: str, char_offset: int) -> PlayCitationAnchor | None:
    """Walk ``file_text`` and return the play anchor at/after ``char_offset``.

    The state machine tracks ``act`` and ``scene`` from heading lines and
    counts non-heading non-empty lines within the current scene. The first
    content line at or past ``char_offset`` is taken as the chunk's anchor
    line. If the file lacks a complete act/scene/line state at that point
    (e.g., the chunk is in the front-matter before the first ACT marker),
    the inferer returns ``None`` and the caller emits a structured warning.
    """
    act: int | None = None
    scene: int | None = None
    line_count = 0
    captured_line: int | None = None
    pos = 0
    for raw_line in file_text.splitlines(keepends=True):
        stripped = raw_line.strip()
        act_match = _ACT_PATTERN.match(stripped)
        scene_match = _SCENE_PATTERN.match(stripped)
        if act_match:
            parsed = _parse_roman_or_int(act_match.group(1))
            if parsed is not None:
                act = parsed
                scene = None
                line_count = 0
        elif scene_match:
            parsed = _parse_roman_or_int(scene_match.group(1))
            if parsed is not None:
                scene = parsed
                line_count = 0
        elif stripped:
            line_count += 1
            if captured_line is None and pos >= char_offset:
                captured_line = line_count
                break
        pos += len(raw_line)
    if act is None or scene is None or captured_line is None:
        return None
    return PlayCitationAnchor(act=act, scene=scene, line=captured_line)


def _infer_novel_anchor(file_text: str, char_offset: int) -> NovelCitationAnchor | None:
    """Walk ``file_text`` and return the novel anchor at/after ``char_offset``.

    Tracks ``chapter`` from heading lines and counts paragraphs within the
    chapter. A paragraph is a run of one or more non-empty lines separated
    by blank lines. The first paragraph that begins at or past
    ``char_offset`` is the chunk's anchor; if no chapter has been seen by
    then, returns ``None``.
    """
    chapter: int | None = None
    paragraph_count = 0
    in_paragraph = False
    captured_paragraph: int | None = None
    pos = 0
    for raw_line in file_text.splitlines(keepends=True):
        stripped = raw_line.strip()
        chapter_match = _CHAPTER_PATTERN.match(stripped)
        if chapter_match:
            parsed = _parse_roman_or_int(chapter_match.group(1))
            if parsed is not None:
                chapter = parsed
                paragraph_count = 0
                in_paragraph = False
        elif stripped:
            if not in_paragraph:
                paragraph_count += 1
                in_paragraph = True
            if captured_paragraph is None and pos >= char_offset:
                captured_paragraph = paragraph_count
                break
        else:
            in_paragraph = False
        pos += len(raw_line)
    if chapter is None or captured_paragraph is None:
        return None
    return NovelCitationAnchor(chapter=chapter, paragraph=captured_paragraph)


__all__ = [
    "AQA_REFUSAL_PATTERN",
    "CHUNK_OVERLAP",
    "CHUNK_SIZE",
    "IngestResult",
    "RefusalReason",
    "RefusalRecord",
    "SOURCE_TYPE_FOLDERS",
    "SkipReason",
    "SkipRecord",
    "load_corpus",
]
