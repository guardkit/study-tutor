"""The upload surface — how scans become subjects.

Three pieces, one contract between them (build spec
``docs/design/upload-surface-build-spec-2026-08-14.md``):

1. **the serving process** takes an uploaded file, runs every guard, writes the
   raw bytes plus a ``queued`` job record into the staging tree — and does
   nothing else. It never converts and never imports a converter;
2. **the staging tree** (:mod:`study_tutor.ingest.staging`) is the contract:
   ``data/uploads/<subject>/`` with ``incoming/``, ``jobs/`` and a ``sources/``
   tree in the exact four-folder shape the existing corpus loader walks;
3. **the host-side worker** picks up queued jobs, converts them to markdown
   through the :mod:`study_tutor.ingest.converter` port, drops the markdown in
   the right corpus folder, and runs the existing ``scripts/ingest_corpus.py``
   against ``sources/`` — moving the job to ``ingested`` or ``failed``.

Because the contract is files, both sides are testable without each other: no
HTTP, no docling, no broker, no network anywhere in this package.
"""

from __future__ import annotations

from study_tutor.ingest.config import (
    DEFAULT_MAX_FILE_MB,
    DEFAULT_STAGING_ROOT,
    DEFAULT_SUBJECT_QUOTA_MB,
    UploadConfig,
)
from study_tutor.ingest.converter import (
    ConversionError,
    ConversionNote,
    ConversionResult,
    Converter,
    PassthroughConverter,
)
from study_tutor.ingest.errors import (
    FileTooLarge,
    InvalidFilename,
    InvalidJobRecord,
    InvalidSourceType,
    InvalidStatusTransition,
    InvalidSubject,
    JobNotFound,
    RefusedMaterial,
    SubjectQuotaExceeded,
    UnsupportedFileType,
    UploadError,
)
from study_tutor.ingest.guards import (
    ALLOWED_EXTENSIONS,
    SOURCE_TYPE_NAMES,
    CheckedUpload,
    check_upload_request,
)
from study_tutor.ingest.jobs import JobRecord, JobStatus, utc_now_iso
from study_tutor.ingest.staging import StagingTree

__all__ = [
    "ALLOWED_EXTENSIONS",
    "CheckedUpload",
    "ConversionError",
    "ConversionNote",
    "ConversionResult",
    "Converter",
    "DEFAULT_MAX_FILE_MB",
    "DEFAULT_STAGING_ROOT",
    "DEFAULT_SUBJECT_QUOTA_MB",
    "FileTooLarge",
    "InvalidFilename",
    "InvalidJobRecord",
    "InvalidSourceType",
    "InvalidStatusTransition",
    "InvalidSubject",
    "JobNotFound",
    "JobRecord",
    "JobStatus",
    "PassthroughConverter",
    "RefusedMaterial",
    "SOURCE_TYPE_NAMES",
    "StagingTree",
    "SubjectQuotaExceeded",
    "UnsupportedFileType",
    "UploadConfig",
    "UploadError",
    "check_upload_request",
    "utc_now_iso",
]
