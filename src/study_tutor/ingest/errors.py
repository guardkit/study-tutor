"""Upload-surface error hierarchy (Lane 3 step 4, A-core).

Plain Python exceptions — they do NOT inherit from any HTTP exception type.
Each carries an ``http_status`` class attribute so the B-stage routes can map
a guard failure to a status code without re-deriving the policy, and a
plain-language message the operator can act on (the upload page shows it
verbatim).

Deliberately NO ``error_type`` wire field: the frozen binding's §4 convention
for validation failures is a plain ``{"error": "..."}`` body, and the upload
surface copies its neighbours rather than inventing a shape.
"""

from __future__ import annotations


class UploadError(Exception):
    """Base for every upload-time guard failure.

    Attributes:
        http_status: Status code the B-stage route should return.
    """

    http_status: int = 400


class EmptyUpload(UploadError):
    """The uploaded file has no bytes.

    A refusal, not a server fault: a failed scan or a wrong drag produces an
    empty file often enough that the operator must see a 400 with a reason,
    never a 500 (2026-08-15 coach finding — this used to escape the hierarchy
    as a bare ``ValueError``).
    """

    http_status = 400

    def __init__(self) -> None:
        super().__init__(
            "The file is empty — there is nothing to upload. Re-scan the "
            "page or pick the right file."
        )


class InvalidSubject(UploadError):
    """Subject slug does not match the registry's subject pattern.

    Args:
        subject: The rejected slug (echoed back so the operator sees the typo).
        reason: Optional replacement message when the generic
            shape-explanation would mislead (e.g. a too-long slug is shaped
            fine — its problem is length).
    """

    http_status = 400

    def __init__(self, subject: str, reason: str | None = None):
        self.subject = subject
        super().__init__(
            reason
            or f"Subject {subject!r} is not a valid subject name. Use lower-case "
            "letters, digits, hyphens or underscores, starting with a letter "
            "(for example: english, demo_history)."
        )


class InvalidSourceType(UploadError):
    """``source_type`` is not one of the four canonical corpus folders.

    Args:
        source_type: The rejected value.
        allowed: The four accepted folder names, sorted.
    """

    http_status = 400

    def __init__(self, source_type: str, allowed: tuple[str, ...]):
        self.source_type = source_type
        self.allowed = allowed
        super().__init__(
            f"Source type {source_type!r} is not one of the four corpus "
            f"folders: {', '.join(allowed)}."
        )


class InvalidFilename(UploadError):
    """Filename is empty, a traversal attempt, or contains unsafe bytes.

    Args:
        filename: The rejected filename.
        detail: Why it was rejected.
    """

    http_status = 400

    def __init__(self, filename: str, detail: str):
        self.filename = filename
        self.detail = detail
        super().__init__(f"Filename {filename!r} cannot be accepted: {detail}")


class UnsupportedFileType(UploadError):
    """File extension is outside the upload allowlist.

    Args:
        suffix: The rejected extension (lower-cased, with dot; may be empty).
        allowed: The allowed extensions, sorted.
    """

    http_status = 400

    def __init__(self, suffix: str, allowed: tuple[str, ...]):
        self.suffix = suffix
        self.allowed = allowed
        shown = suffix or "(no extension)"
        super().__init__(
            f"Files of type {shown} are not accepted. Upload one of: "
            f"{', '.join(allowed)}."
        )


class RefusedMaterial(UploadError):
    """Filename looks like AQA assessment material — refused, not stored.

    The refusal regex is the corpus loader's (imported, never duplicated):
    AQA prohibits redistribution of past papers, mark schemes and examiner
    reports, so the upload surface refuses them at the door rather than
    letting the loader drop them after they are on disk.

    Args:
        filename: The refused filename.
    """

    http_status = 422

    def __init__(self, filename: str):
        self.filename = filename
        super().__init__(
            f"{filename!r} looks like AQA assessment material (past paper, "
            "mark scheme or examiner report). AQA prohibits redistribution of "
            "these, so the tutor will not ingest them."
        )


class FileTooLarge(UploadError):
    """Single file exceeds the per-file cap.

    Args:
        size_bytes: Size of the rejected upload.
        max_bytes: The configured per-file cap.
    """

    http_status = 413

    def __init__(self, size_bytes: int, max_bytes: int):
        self.size_bytes = size_bytes
        self.max_bytes = max_bytes
        super().__init__(
            f"File is {size_bytes / (1024 * 1024):.1f}MB, over the "
            f"{max_bytes / (1024 * 1024):.0f}MB per-file limit. Split the scan "
            "or raise STUDY_TUTOR_UPLOAD_MAX_FILE_MB."
        )


class SubjectQuotaExceeded(UploadError):
    """Accepting this file would push the subject over its staging quota.

    Args:
        subject: The subject whose staging area is full.
        used_bytes: Bytes already staged for the subject.
        size_bytes: Size of the upload that would not fit.
        quota_bytes: The configured per-subject quota.
    """

    http_status = 413

    def __init__(
        self, subject: str, used_bytes: int, size_bytes: int, quota_bytes: int
    ):
        self.subject = subject
        self.used_bytes = used_bytes
        self.size_bytes = size_bytes
        self.quota_bytes = quota_bytes
        mb = 1024 * 1024
        super().__init__(
            f"Subject {subject!r} has {used_bytes / mb:.1f}MB staged and this "
            f"file adds {size_bytes / mb:.1f}MB, over the "
            f"{quota_bytes / mb:.0f}MB per-subject limit. Ingest and clear the "
            "staged files, or raise STUDY_TUTOR_UPLOAD_SUBJECT_QUOTA_MB."
        )


class JobNotFound(UploadError):
    """No job record exists for the requested id.

    Args:
        job_id: The id that was looked up.
    """

    http_status = 404

    def __init__(self, job_id: str):
        self.job_id = job_id
        super().__init__(f"No upload job {job_id!r}.")


class InvalidJobRecord(UploadError):
    """A job file on disk is missing fields or holds an unknown status.

    Args:
        detail: What is wrong with the record.
    """

    http_status = 500

    def __init__(self, detail: str):
        self.detail = detail
        super().__init__(f"Malformed upload job record: {detail}")


class InvalidStatusTransition(UploadError):
    """A status change the job lifecycle does not allow.

    Args:
        current: The job's current status value.
        requested: The status that was asked for.
    """

    http_status = 500

    def __init__(self, current: str, requested: str):
        self.current = current
        self.requested = requested
        super().__init__(
            f"Upload job cannot move from {current!r} to {requested!r}."
        )
