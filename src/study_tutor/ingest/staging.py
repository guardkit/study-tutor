"""The staging tree — the A-stage contract everything else depends on.

Layout, per subject (build spec, "Staging layout")::

    <root>/<subject>/
      incoming/<job_id>/<original_filename>     # raw uploaded bytes
      jobs/<job_id>.json                        # job record
      sources/                                  # the four-folder tree ingest consumes
        primary_text/  secondary_study_guide/  secondary_critical/  context_historical/

``sources/`` is deliberately the *exact* shape ``load_corpus`` walks, so the
worker's job is to put converted markdown in the right folder and then point
the existing ingest script at ``<root>/<subject>/sources``. No new corpus
contract is invented anywhere in this pipeline.

Everything here is filesystem-only: no HTTP, no docling, no broker, no network.
That is what lets both sides of the contract — the serving process that writes
``queued`` and the host-side worker that writes everything after — be tested
hermetically against the same tree.
"""

from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from study_tutor.ingest.config import UploadConfig
from study_tutor.ingest.errors import JobNotFound
from study_tutor.ingest.guards import (
    SOURCE_TYPE_NAMES,
    CheckedUpload,
    check_upload_request,
    validate_source_type,
    validate_subject,
)
from study_tutor.ingest.jobs import JobRecord, JobStatus, utc_now_iso

#: Sub-directory names inside one subject's staging area.
INCOMING_DIRNAME: str = "incoming"
JOBS_DIRNAME: str = "jobs"
SOURCES_DIRNAME: str = "sources"

#: Suffix for the job file of a given job id.
JOB_FILE_SUFFIX: str = ".json"


@dataclass(frozen=True)
class StagingTree:
    """Reader/writer for one staging root.

    Attributes:
        root: Root of the staging tree (``data/uploads`` in the deployment,
            a ``tmp_path`` in tests).
    """

    root: Path

    @classmethod
    def from_config(cls, config: UploadConfig) -> StagingTree:
        """Build a tree rooted at ``config.staging_root``."""
        return cls(root=Path(config.staging_root))

    # -- paths -------------------------------------------------------------

    def subject_dir(self, subject: str) -> Path:
        """Return the staging directory for ``subject`` (validated slug)."""
        return self.root / validate_subject(subject)

    def incoming_dir(self, subject: str) -> Path:
        """Return the raw-bytes directory for ``subject``."""
        return self.subject_dir(subject) / INCOMING_DIRNAME

    def job_dir(self, subject: str, job_id: str) -> Path:
        """Return the directory holding one job's raw bytes."""
        return self.incoming_dir(subject) / _validate_job_id(job_id)

    def jobs_dir(self, subject: str) -> Path:
        """Return the job-record directory for ``subject``."""
        return self.subject_dir(subject) / JOBS_DIRNAME

    def job_path(self, subject: str, job_id: str) -> Path:
        """Return the job-record path for one job."""
        return self.jobs_dir(subject) / (_validate_job_id(job_id) + JOB_FILE_SUFFIX)

    def sources_dir(self, subject: str) -> Path:
        """Return the four-folder corpus root the ingest script consumes."""
        return self.subject_dir(subject) / SOURCES_DIRNAME

    def source_type_dir(self, subject: str, source_type: str) -> Path:
        """Return the corpus folder converted markdown for ``source_type`` goes in."""
        return self.sources_dir(subject) / validate_source_type(source_type)

    def stored_file(self, record: JobRecord) -> Path:
        """Return the absolute-in-this-tree path of a record's raw bytes.

        ``stored_path`` is relative to the staging root, so resolving it is the
        tree's job, not the caller's.

        Args:
            record: The job record.

        Returns:
            ``root / record.stored_path``.
        """
        return self.root / Path(record.stored_path)

    # -- structure ---------------------------------------------------------

    def ensure_subject(self, subject: str) -> Path:
        """Create (idempotently) the whole staging tree for ``subject``.

        Includes all four corpus folders, so the worker can point the ingest
        script at ``sources/`` even when only one folder has content in it.

        Args:
            subject: Subject slug.

        Returns:
            The subject directory.

        Raises:
            InvalidSubject: If the slug is not a registry subject.
        """
        subject_dir = self.subject_dir(subject)
        self.incoming_dir(subject).mkdir(parents=True, exist_ok=True)
        self.jobs_dir(subject).mkdir(parents=True, exist_ok=True)
        for folder in SOURCE_TYPE_NAMES:
            (self.sources_dir(subject) / folder).mkdir(parents=True, exist_ok=True)
        return subject_dir

    def subjects(self) -> list[str]:
        """Return the subject slugs that have a staging area, sorted."""
        if not self.root.is_dir():
            return []
        found: list[str] = []
        for child in sorted(self.root.iterdir()):
            if not child.is_dir():
                continue
            try:
                found.append(validate_subject(child.name))
            except Exception:  # noqa: BLE001 — a stray dir is not a subject
                continue
        return found

    def subject_usage_bytes(self, subject: str) -> int:
        """Return the total bytes staged under ``subject``.

        Counts everything in the subject's tree — raw uploads, job records and
        converted sources — because all of it is disk the operator's quota is
        meant to bound.

        Args:
            subject: Subject slug.

        Returns:
            Total size in bytes; ``0`` when the subject has no staging area.
        """
        subject_dir = self.subject_dir(subject)
        if not subject_dir.is_dir():
            return 0
        total = 0
        for entry in subject_dir.rglob("*"):
            if entry.is_file() and not entry.is_symlink():
                total += entry.stat().st_size
        return total

    # -- writes ------------------------------------------------------------

    def accept_upload(
        self,
        *,
        subject: str,
        source_type: str,
        filename: str,
        data: bytes,
        config: UploadConfig,
        now: str | None = None,
    ) -> JobRecord:
        """Run the guards, store the bytes, and write a ``queued`` job record.

        This is the only write the serving process ever makes to the staging
        tree; every later status belongs to the worker.

        Args:
            subject: Subject slug as the caller supplied it.
            source_type: Corpus folder name as the caller supplied it.
            filename: Filename as the client sent it.
            data: The uploaded bytes.
            config: Resolved upload limits.
            now: UTC ISO timestamp for ``created_at``/``updated_at``. Defaults
                to the current time.

        Returns:
            The written :class:`JobRecord`, status ``queued``.

        Raises:
            UploadError: If any guard refuses the upload — nothing is written.
            ValueError: If ``data`` is empty.
        """
        checked: CheckedUpload = check_upload_request(
            subject=subject,
            source_type=source_type,
            filename=filename,
            size_bytes=len(data),
            config=config,
            staged_bytes=self.subject_usage_bytes,
        )

        self.ensure_subject(checked.subject)
        job_id = str(uuid.uuid4())
        job_dir = self.job_dir(checked.subject, job_id)
        job_dir.mkdir(parents=True, exist_ok=False)

        stored = job_dir / checked.filename
        # The filename is already a sanitised basename, but the invariant that
        # bytes never land outside their own job directory is worth asserting
        # rather than assuming.
        if stored.parent.resolve() != job_dir.resolve():
            raise AssertionError(
                f"Refusing to store {checked.filename!r} outside its job directory."
            )
        _atomic_write_bytes(stored, data)

        timestamp = now or utc_now_iso()
        record = JobRecord(
            job_id=job_id,
            subject=checked.subject,
            source_type=checked.source_type,
            original_filename=checked.filename,
            stored_path=self.relative_path(stored),
            sha256=hashlib.sha256(data).hexdigest(),
            size_bytes=checked.size_bytes,
            status=JobStatus.QUEUED,
            error=None,
            created_at=timestamp,
            updated_at=timestamp,
        )
        self.save_job(record)
        return record

    def save_job(self, record: JobRecord) -> Path:
        """Write ``record`` to its job file, replacing any earlier version.

        The write is atomic (temporary file plus ``os.replace``): the worker
        polls these files while the server writes them, so a reader must never
        see a half-written record.

        Args:
            record: The record to persist.

        Returns:
            The job file's path.
        """
        path = self.job_path(record.subject, record.job_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_text(path, record.to_json())
        return path

    def transition(
        self,
        record: JobRecord,
        status: JobStatus,
        *,
        error: str | None = None,
        now: str | None = None,
    ) -> JobRecord:
        """Move ``record`` to ``status`` and persist it.

        Args:
            record: The record to move.
            status: The status to move to.
            error: Failure message; required for :attr:`JobStatus.FAILED`.
            now: UTC ISO timestamp for ``updated_at``.

        Returns:
            The persisted, updated record.

        Raises:
            InvalidStatusTransition: If the lifecycle disallows the move.
            ValueError: If moving to ``failed`` without an error message.
        """
        updated = record.with_status(status, error=error, now=now)
        self.save_job(updated)
        return updated

    # -- reads -------------------------------------------------------------

    def read_job(self, subject: str, job_id: str) -> JobRecord:
        """Return one job record.

        Args:
            subject: Subject slug.
            job_id: The job's id.

        Returns:
            The parsed record.

        Raises:
            JobNotFound: If no job file exists.
            InvalidJobRecord: If the file is malformed.
        """
        path = self.job_path(subject, job_id)
        if not path.is_file():
            raise JobNotFound(job_id)
        return JobRecord.from_json(path.read_text(encoding="utf-8"))

    def list_jobs(self, subject: str) -> list[JobRecord]:
        """Return every job record for ``subject``, newest first.

        Args:
            subject: Subject slug.

        Returns:
            Records sorted by ``created_at`` descending, then ``job_id`` — an
            empty list when the subject has no staging area.

        Raises:
            InvalidJobRecord: If any job file is malformed.
        """
        jobs_dir = self.jobs_dir(subject)
        if not jobs_dir.is_dir():
            return []
        records = [
            JobRecord.from_json(path.read_text(encoding="utf-8"))
            for path in sorted(jobs_dir.glob(f"*{JOB_FILE_SUFFIX}"))
            if path.is_file()
        ]
        records.sort(key=lambda r: (r.created_at, r.job_id), reverse=True)
        return records

    def jobs_with_status(self, subject: str, status: JobStatus) -> list[JobRecord]:
        """Return ``subject``'s jobs in ``status``, oldest first.

        Oldest first because this is the worker's queue view: uploads are
        processed in the order the operator made them.

        Args:
            subject: Subject slug.
            status: The status to filter on.

        Returns:
            Matching records, ``created_at`` ascending.
        """
        return sorted(
            (r for r in self.list_jobs(subject) if r.status is status),
            key=lambda r: (r.created_at, r.job_id),
        )

    def relative_path(self, path: Path) -> str:
        """Return ``path`` relative to the staging root, POSIX-style.

        Args:
            path: A path inside the tree.

        Returns:
            The relative path as a string, e.g.
            ``english/incoming/<job_id>/scan.pdf``.

        Raises:
            ValueError: If ``path`` is not inside the staging root.
        """
        return PurePosixPath(path.relative_to(self.root).as_posix()).as_posix()


def _validate_job_id(job_id: str) -> str:
    """Return ``job_id`` if it is a canonical uuid string.

    Job ids come off the wire on the ``GET /api/corpus/jobs/{job_id}`` route
    and are used as path segments, so they are parsed as uuids rather than
    string-matched.

    Args:
        job_id: Candidate id.

    Returns:
        The id, unchanged.

    Raises:
        JobNotFound: If it is not a uuid — an id that cannot exist is
            indistinguishable, to a caller, from one that does not.
    """
    try:
        parsed = uuid.UUID(str(job_id))
    except (ValueError, AttributeError, TypeError) as exc:
        raise JobNotFound(str(job_id)) from exc
    if str(parsed) != str(job_id):
        raise JobNotFound(str(job_id))
    return job_id


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write ``data`` to ``path`` via a temporary file and ``os.replace``."""
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    tmp.write_bytes(data)
    os.replace(tmp, path)


def _atomic_write_text(path: Path, text: str) -> None:
    """Write ``text`` (UTF-8) to ``path`` via a temporary file and ``os.replace``."""
    tmp = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)
