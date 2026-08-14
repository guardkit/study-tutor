"""Upload-time guards (Lane 3 step 4, A-core).

Every guard runs at *upload* time, not at ingest time: a scan that cannot
become corpus must be refused while the operator is still looking at the page,
not silently dropped by the loader hours later on the worker.

The guards, in the order :func:`check_upload_request` applies them:

1. subject slug validates against the subject-registry pattern
   (``rag_wiring.SUBJECT_COLLECTION_PATTERN`` — checked by round-tripping the
   slug through :func:`rag_wiring.subject_collection_name`, so the two can
   never drift);
2. ``source_type`` is one of the four canonical corpus folders
   (``corpus.SOURCE_TYPE_FOLDERS`` — imported, never re-listed);
3. filename sanitises to a bare basename (no traversal, no null bytes, no
   control characters);
4. extension is on the upload allowlist;
5. filename does not look like AQA assessment material
   (``corpus.AQA_REFUSAL_PATTERN`` — imported, never duplicated);
6. the file is within the per-file size cap;
7. the subject's staging area has room for it.

Subject first is load-bearing: nothing may touch a filesystem path derived
from a caller-supplied subject before that subject has been proven to be a
plain registry slug.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Callable

from study_tutor.cli.rag_wiring import (
    SUBJECT_COLLECTION_PATTERN,
    subject_collection_name,
)
from study_tutor.ingest.config import UploadConfig
from study_tutor.ingest.errors import (
    FileTooLarge,
    InvalidFilename,
    InvalidSourceType,
    InvalidSubject,
    RefusedMaterial,
    SubjectQuotaExceeded,
    UnsupportedFileType,
)
from study_tutor.knowledge.corpus import AQA_REFUSAL_PATTERN, SOURCE_TYPE_FOLDERS

#: The four canonical corpus folder names, straight from the loader's map.
#: ``source_type`` on an upload must be one of these verbatim — it *is* the
#: folder the converted markdown lands in.
SOURCE_TYPE_NAMES: tuple[str, ...] = tuple(sorted(SOURCE_TYPE_FOLDERS))

#: Extensions the upload surface accepts: scans (image/PDF) and already-typed
#: notes. Anything else has no converter behind it, so accepting it would only
#: defer the failure to the worker.
ALLOWED_EXTENSIONS: tuple[str, ...] = (
    ".jpeg",
    ".jpg",
    ".md",
    ".pdf",
    ".png",
    ".tif",
    ".tiff",
    ".txt",
)

#: Longest filename we will store. Comfortably under the 255-byte limit
#: common filesystems impose once a uuid4 job directory is in the path.
MAX_FILENAME_LENGTH: int = 200

#: Path separators to strip when reducing an uploaded name to a basename.
#: Both flavours: a browser on Windows can send a backslash-separated path.
_SEPARATORS = re.compile(r"[\\/]")


@dataclass(frozen=True)
class CheckedUpload:
    """An upload request that passed every guard.

    Attributes:
        subject: The validated subject slug.
        source_type: The validated corpus folder name.
        filename: The sanitised basename the bytes will be stored under.
        size_bytes: Size of the uploaded bytes.
    """

    subject: str
    source_type: str
    filename: str
    size_bytes: int


def validate_subject(subject: str) -> str:
    """Return ``subject`` if it is a valid registry subject slug.

    Validation is by construction rather than by a copied pattern: the slug is
    formatted into a collection name and matched against
    ``SUBJECT_COLLECTION_PATTERN``, so a change to the registry's scheme
    changes what the upload surface accepts, automatically.

    Args:
        subject: Candidate subject slug (e.g. ``english``, ``demo_history``).

    Returns:
        The same slug, unchanged.

    Raises:
        InvalidSubject: If the slug would not produce a discoverable
            collection name.
    """
    if not isinstance(subject, str) or not subject:
        raise InvalidSubject(subject)
    candidate = subject_collection_name(subject)
    if SUBJECT_COLLECTION_PATTERN.fullmatch(candidate) is None:
        raise InvalidSubject(subject)
    return subject


def validate_source_type(source_type: str) -> str:
    """Return ``source_type`` if it names one of the four corpus folders.

    Args:
        source_type: Candidate folder name.

    Returns:
        The same value, unchanged.

    Raises:
        InvalidSourceType: If it is not one of the four names verbatim.
    """
    if source_type not in SOURCE_TYPE_FOLDERS:
        raise InvalidSourceType(str(source_type), SOURCE_TYPE_NAMES)
    return source_type


def sanitise_filename(filename: str) -> str:
    """Reduce an uploaded filename to a safe basename.

    The stored path is always ``<job dir>/<basename>`` with a server-generated
    uuid4 job directory, so the caller never chooses where bytes land; this
    guard makes the *name* safe too.

    Args:
        filename: The name as the client sent it.

    Returns:
        The bare basename, whitespace-trimmed.

    Raises:
        InvalidFilename: Empty, null-byte-bearing, control-character-bearing,
            a bare ``.``/``..``, dot-leading, or over
            :data:`MAX_FILENAME_LENGTH` characters.
    """
    if not isinstance(filename, str) or not filename.strip():
        raise InvalidFilename(str(filename), "it is empty")
    if "\x00" in filename:
        raise InvalidFilename(filename, "it contains a null byte")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in filename):
        raise InvalidFilename(filename, "it contains control characters")

    basename = _SEPARATORS.split(filename)[-1].strip()
    if basename in ("", ".", ".."):
        raise InvalidFilename(filename, "it has no filename part")
    if basename.startswith("."):
        raise InvalidFilename(filename, "it starts with a dot")
    if len(basename) > MAX_FILENAME_LENGTH:
        raise InvalidFilename(
            filename, f"it is longer than {MAX_FILENAME_LENGTH} characters"
        )
    # Belt and braces: whatever the separator dance produced must be a single
    # path segment with no parent reference left in it.
    if PurePosixPath(basename).name != basename:
        raise InvalidFilename(filename, "it is not a plain filename")
    return basename


def validate_extension(filename: str) -> str:
    """Return the file's lower-cased extension if it is on the allowlist.

    Args:
        filename: A sanitised basename.

    Returns:
        The extension, lower-cased, including the leading dot.

    Raises:
        UnsupportedFileType: If the extension is missing or not allowed.
    """
    suffix = PurePosixPath(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileType(suffix, ALLOWED_EXTENSIONS)
    return suffix


def refuse_assessment_material(filename: str) -> None:
    """Refuse filenames that look like AQA assessment material.

    Uses the corpus loader's refusal regex directly (seam 1) so the upload
    surface and the loader can never disagree about what is refused.

    Args:
        filename: A sanitised basename.

    Raises:
        RefusedMaterial: If the name matches the AQA refusal pattern.
    """
    if AQA_REFUSAL_PATTERN.search(filename):
        raise RefusedMaterial(filename)


def validate_file_size(size_bytes: int, config: UploadConfig) -> int:
    """Return ``size_bytes`` if the file is non-empty and within the cap.

    Args:
        size_bytes: Size of the uploaded bytes.
        config: Resolved upload limits.

    Returns:
        The same size.

    Raises:
        FileTooLarge: If the file exceeds ``config.max_file_bytes``.
        ValueError: If ``size_bytes`` is negative or zero (an empty upload is
            a client bug, not a policy refusal).
    """
    if size_bytes <= 0:
        raise ValueError("Upload is empty — there are no bytes to stage.")
    if size_bytes > config.max_file_bytes:
        raise FileTooLarge(size_bytes, config.max_file_bytes)
    return size_bytes


def validate_subject_quota(
    subject: str, used_bytes: int, size_bytes: int, config: UploadConfig
) -> None:
    """Check the subject's staging area has room for ``size_bytes`` more.

    Args:
        subject: The validated subject slug.
        used_bytes: Bytes already staged under that subject.
        size_bytes: Size of the incoming file.
        config: Resolved upload limits.

    Raises:
        SubjectQuotaExceeded: If the total would exceed the per-subject quota.
    """
    if used_bytes + size_bytes > config.subject_quota_bytes:
        raise SubjectQuotaExceeded(
            subject, used_bytes, size_bytes, config.subject_quota_bytes
        )


def check_upload_request(
    *,
    subject: str,
    source_type: str,
    filename: str,
    size_bytes: int,
    config: UploadConfig,
    staged_bytes: Callable[[str], int],
) -> CheckedUpload:
    """Run every upload guard, in order, and return the checked request.

    Args:
        subject: Candidate subject slug.
        source_type: Candidate corpus folder name.
        filename: Filename as the client sent it.
        size_bytes: Size of the uploaded bytes.
        config: Resolved upload limits.
        staged_bytes: Callable returning the bytes already staged for a
            subject. Called only *after* the subject validates, so no
            filesystem path is ever built from an unvalidated slug.

    Returns:
        A :class:`CheckedUpload` carrying the validated, sanitised values.

    Raises:
        UploadError: The first guard that fails raises its own subclass; the
            order is the one documented at module level.
        ValueError: If the upload is empty.
    """
    checked_subject = validate_subject(subject)
    checked_source_type = validate_source_type(source_type)
    checked_filename = sanitise_filename(filename)
    validate_extension(checked_filename)
    refuse_assessment_material(checked_filename)
    validate_file_size(size_bytes, config)
    validate_subject_quota(
        checked_subject, staged_bytes(checked_subject), size_bytes, config
    )
    return CheckedUpload(
        subject=checked_subject,
        source_type=checked_source_type,
        filename=checked_filename,
        size_bytes=size_bytes,
    )
