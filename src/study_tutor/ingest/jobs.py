"""Upload job records — the contract between the server and the worker.

The serving process never converts and the worker never serves HTTP; the only
thing they share is the staging tree and these job files. So the record schema
is the contract, and it is pinned here (build spec, "Staging layout"):

``job_id`` (uuid4) · ``subject`` · ``source_type`` (one of the four folder
names) · ``original_filename`` (sanitised basename) · ``stored_path`` ·
``sha256`` · ``size_bytes`` · ``status`` · ``error`` (nullable) ·
``created_at`` / ``updated_at`` (UTC ISO).

``stored_path`` is stored **relative to the staging root**, POSIX-style. That
keeps the tree self-describing (it can be moved or mounted elsewhere without
rewriting every job file) and keeps absolute host paths out of the job list the
upload page renders.

Status transitions are append-style rewrites of the whole file. The writer is
whoever owns the transition: the server writes ``queued`` and nothing else; the
worker owns everything after.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

from study_tutor.ingest.errors import InvalidJobRecord, InvalidStatusTransition


class JobStatus(str, Enum):
    """Lifecycle of one uploaded file."""

    QUEUED = "queued"
    CONVERTING = "converting"
    STAGED = "staged"
    INGESTED = "ingested"
    FAILED = "failed"


#: What each status may become. ``converting -> queued`` is the worker's
#: restart path: a job caught mid-conversion by a crash is re-queued rather
#: than left stranded, which is what makes the worker idempotent on restart.
#: ``ingested`` and ``failed`` are terminal — a re-run is a new upload, so the
#: record of what happened to these bytes stays honest.
ALLOWED_TRANSITIONS: dict[JobStatus, frozenset[JobStatus]] = {
    JobStatus.QUEUED: frozenset({JobStatus.CONVERTING, JobStatus.FAILED}),
    JobStatus.CONVERTING: frozenset(
        {JobStatus.STAGED, JobStatus.QUEUED, JobStatus.FAILED}
    ),
    JobStatus.STAGED: frozenset({JobStatus.INGESTED, JobStatus.FAILED}),
    JobStatus.INGESTED: frozenset(),
    JobStatus.FAILED: frozenset(),
}

#: Field names every job file must carry.
REQUIRED_FIELDS: tuple[str, ...] = (
    "job_id",
    "subject",
    "source_type",
    "original_filename",
    "stored_path",
    "sha256",
    "size_bytes",
    "status",
    "error",
    "created_at",
    "updated_at",
)


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string with offset."""
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class JobRecord:
    """One uploaded file's staging record.

    Attributes:
        job_id: uuid4, generated server-side; also the incoming directory name.
        subject: Validated subject slug.
        source_type: One of the four corpus folder names.
        original_filename: Sanitised basename of the uploaded file.
        stored_path: Path to the raw bytes, relative to the staging root.
        sha256: Hex digest of the uploaded bytes.
        size_bytes: Size of the uploaded bytes.
        status: Where the job is in its lifecycle.
        error: Failure message, or ``None``.
        created_at: UTC ISO timestamp of the upload.
        updated_at: UTC ISO timestamp of the last status write.
    """

    job_id: str
    subject: str
    source_type: str
    original_filename: str
    stored_path: str
    sha256: str
    size_bytes: int
    status: JobStatus
    error: str | None
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serialisable form of this record."""
        return {
            "job_id": self.job_id,
            "subject": self.subject,
            "source_type": self.source_type,
            "original_filename": self.original_filename,
            "stored_path": self.stored_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
            "status": self.status.value,
            "error": self.error,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_json(self) -> str:
        """Return this record as pretty-printed JSON with a trailing newline."""
        return json.dumps(self.to_dict(), indent=2) + "\n"

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> JobRecord:
        """Rebuild a record from its JSON form.

        Args:
            data: Decoded job-file contents.

        Returns:
            The parsed :class:`JobRecord`.

        Raises:
            InvalidJobRecord: On a missing field, an unknown status, or a
                non-integer size.
        """
        missing = [name for name in REQUIRED_FIELDS if name not in data]
        if missing:
            raise InvalidJobRecord(f"missing field(s) {', '.join(sorted(missing))}")

        raw_status = data["status"]
        try:
            status = JobStatus(raw_status)
        except ValueError as exc:
            raise InvalidJobRecord(f"unknown status {raw_status!r}") from exc

        size = data["size_bytes"]
        if not isinstance(size, int) or isinstance(size, bool):
            raise InvalidJobRecord(f"size_bytes {size!r} is not a whole number")

        error = data["error"]
        if error is not None and not isinstance(error, str):
            raise InvalidJobRecord(f"error {error!r} is neither text nor null")

        return cls(
            job_id=str(data["job_id"]),
            subject=str(data["subject"]),
            source_type=str(data["source_type"]),
            original_filename=str(data["original_filename"]),
            stored_path=str(data["stored_path"]),
            sha256=str(data["sha256"]),
            size_bytes=size,
            status=status,
            error=error,
            created_at=str(data["created_at"]),
            updated_at=str(data["updated_at"]),
        )

    @classmethod
    def from_json(cls, text: str) -> JobRecord:
        """Parse a job file's contents.

        Args:
            text: The file's text.

        Returns:
            The parsed :class:`JobRecord`.

        Raises:
            InvalidJobRecord: If the text is not JSON, is not an object, or
                fails :meth:`from_dict` validation.
        """
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise InvalidJobRecord(f"file is not valid JSON ({exc})") from exc
        if not isinstance(data, dict):
            raise InvalidJobRecord("file does not hold a JSON object")
        return cls.from_dict(data)

    def with_status(
        self,
        status: JobStatus,
        *,
        error: str | None = None,
        now: str | None = None,
    ) -> JobRecord:
        """Return a copy of this record in ``status``.

        Args:
            status: The status to move to.
            error: Failure message. Required when moving to
                :attr:`JobStatus.FAILED`; cleared otherwise.
            now: UTC ISO timestamp to stamp ``updated_at`` with. Defaults to
                the current time.

        Returns:
            A new :class:`JobRecord`; this one is unchanged.

        Raises:
            InvalidStatusTransition: If the lifecycle does not allow the move.
            ValueError: If moving to ``failed`` without an error message.
        """
        if status not in ALLOWED_TRANSITIONS[self.status]:
            raise InvalidStatusTransition(self.status.value, status.value)
        if status is JobStatus.FAILED and not error:
            raise ValueError("A failed job must carry an error message.")
        return replace(
            self,
            status=status,
            error=error if status is JobStatus.FAILED else None,
            updated_at=now or utc_now_iso(),
        )
