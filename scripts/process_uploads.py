#!/usr/bin/env python3
"""The upload worker — staged scans in, ingested subjects out (Lane 3 step 4).

This is the third piece of the upload surface (build spec
``docs/design/upload-surface-build-spec-2026-08-14.md``). It runs **on the
host**, never in the serving image, and it is the only piece that touches
docling or chromadb::

    data/uploads/<subject>/jobs/*.json   status=queued
        -> converting   (converter port: passthrough for .txt/.md, docling for scans)
        -> staged       (markdown written into sources/<source_type>/)
        -> ingested     (scripts/ingest_corpus.py run against sources/)
        or failed       (with the reason on the job record, which the page shows)

Three properties the spec asks for, and where they live here:

* **one job at a time** — :meth:`UploadWorker.run_once` walks the queue
  sequentially; there is no pool, no thread, no async. Ingest is the expensive
  step and it wants the machine to itself;
* **idempotent on restart** — :meth:`UploadWorker.requeue_stranded` moves any
  ``converting`` job (a crash caught it mid-conversion) back to ``queued`` at
  startup. ``staged`` jobs are resumed at the ingest step rather than re-queued,
  because their markdown is already on disk and re-ingest is an upsert;
* **embedding config comes from the environment** — never from a constant here.
  The code default in ``ingest_corpus.py`` (``nomic-embed``) is *not* what the
  deployment serves (``LLM_EMBEDDINGS_MODEL=embed``, 1024-dim), so the worker
  passes its environment through to the ingest child untouched and says at
  startup which model that resolves to. Guessing here would write a subject's
  vectors in a different embedding space from every other subject's — garbage
  retrieval, silently.

The collection name is passed **explicitly** (``--collection-name
gcse-<subject>-v1``) rather than left to the child's env resolution: a
``CHROMA_COLLECTION`` in the operator's shell would otherwise redirect every
subject's chunks into whichever collection that variable names.

Usage::

    uv run python scripts/process_uploads.py --once
    uv run python scripts/process_uploads.py            # loop, polling
"""

from __future__ import annotations

import argparse
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping, Sequence

# Allow direct invocation (``python scripts/process_uploads.py``) without an
# editable install — the same bootstrap ``scripts/ingest_corpus.py`` uses.
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_PATH = str(_REPO_ROOT / "src")
if _SRC_PATH not in sys.path:
    sys.path.insert(0, _SRC_PATH)

from study_tutor.cli.rag_wiring import subject_collection_name  # noqa: E402
from study_tutor.ingest.config import DEFAULT_STAGING_ROOT  # noqa: E402
from study_tutor.ingest.converter import (  # noqa: E402
    ConversionError,
    Converter,
    PassthroughConverter,
)
from study_tutor.ingest.converter_docling import DoclingConverter  # noqa: E402
from study_tutor.ingest.jobs import JobRecord, JobStatus  # noqa: E402
from study_tutor.ingest.staging import StagingTree  # noqa: E402

logger = logging.getLogger("study_tutor.process_uploads")

#: The ingest script this worker drives. Not imported: run as a child process
#: so its chromadb/openai import cost, and any crash inside it, stay out of the
#: long-running worker.
INGEST_SCRIPT: Path = _REPO_ROOT / "scripts" / "ingest_corpus.py"

#: Where the ingest child writes its ChromaDB store, when the environment says
#: nothing. Same default as ``ingest_corpus.py`` and ``rag_wiring``.
DEFAULT_PERSIST_DIR: Path = Path("data/chroma")

#: Env var naming the persist directory (fleet-shared, DECISION-RAG-001 §3.1).
PERSIST_DIR_ENV: str = "CHROMA_PERSIST_DIR"

#: Embedding configuration read from the environment and handed to the ingest
#: child. The worker never supplies a value for any of these — it only reports
#: what it found, so a missing override is visible rather than invented.
EMBEDDING_ENV_NAMES: tuple[str, ...] = (
    "LLM_EMBEDDINGS_BASE_URL",
    "LLM_EMBEDDINGS_API_KEY",
    "LLM_EMBEDDINGS_MODEL",
)

#: Seconds between queue polls in the default (looping) mode.
DEFAULT_POLL_SECONDS: float = 5.0


class IngestFailed(RuntimeError):
    """The ingest child exited non-zero."""


@dataclass(frozen=True)
class IngestInvocation:
    """Exactly what the worker would run to ingest one subject.

    Kept as a value rather than a call so the worker's decisions (which
    subject, which collection, which corpus root, which environment) are
    assertable without running anything.

    Attributes:
        subject: The subject being ingested.
        argv: Full command line, ``argv[0]`` being the interpreter.
        env: Environment for the child process.
    """

    subject: str
    argv: tuple[str, ...]
    env: Mapping[str, str]


#: What a worker calls to ingest a staged subject. The default runs the real
#: script; tests pass a recorder.
IngestRunner = Callable[[IngestInvocation], None]


def build_invocation(
    *,
    subject: str,
    domain_root: Path,
    persist_dir: Path,
    env: Mapping[str, str],
    ingest_script: Path = INGEST_SCRIPT,
    python_executable: str | None = None,
) -> IngestInvocation:
    """Build the ingest command for one subject's staging tree.

    Args:
        subject: Subject slug (already validated by the staging tree).
        domain_root: The subject's ``sources/`` four-folder root.
        persist_dir: ChromaDB persist directory.
        env: Environment to pass through — embedding configuration included,
            unchanged.
        ingest_script: Path to ``ingest_corpus.py``.
        python_executable: Interpreter to run it with; defaults to this one.

    Returns:
        The :class:`IngestInvocation`.
    """
    argv = (
        python_executable or sys.executable,
        str(ingest_script),
        "--subject",
        subject,
        "--domain-root",
        str(domain_root),
        # Explicit, so a CHROMA_COLLECTION in the environment cannot redirect
        # this subject's chunks into another subject's collection.
        "--collection-name",
        subject_collection_name(subject),
        "--persist-dir",
        str(persist_dir),
    )
    return IngestInvocation(subject=subject, argv=argv, env=dict(env))


def run_ingest_subprocess(invocation: IngestInvocation) -> None:
    """Run the ingest child and raise if it fails.

    Args:
        invocation: What to run.

    Raises:
        IngestFailed: If the child exits non-zero; the message carries the exit
            code and the tail of its stderr, which is what the operator needs
            to see on the job record.
    """
    completed = subprocess.run(  # noqa: S603 — argv built here, never from input
        list(invocation.argv),
        env=dict(invocation.env),
        capture_output=True,
        text=True,
        check=False,
    )
    if completed.stdout:
        sys.stdout.write(completed.stdout)
        sys.stdout.flush()
    if completed.returncode != 0:
        tail = "\n".join((completed.stderr or "").strip().splitlines()[-8:])
        raise IngestFailed(
            f"ingest_corpus exited {completed.returncode} for "
            f"{invocation.subject!r}. Last output:\n{tail}"
        )


def select_converter(src: Path) -> Converter:
    """Return the converter for ``src``'s extension.

    Args:
        src: The uploaded file.

    Returns:
        :class:`~study_tutor.ingest.converter.PassthroughConverter` for text,
        :class:`~study_tutor.ingest.converter_docling.DoclingConverter` for
        scans and PDFs. Constructing the docling one imports nothing.

    Raises:
        ConversionError: If no converter handles the extension. The upload
            guards allow only extensions one of these two covers, so this means
            the allowlist and the converters have drifted apart.
    """
    passthrough = PassthroughConverter()
    if passthrough.supports(src):
        return passthrough
    docling = DoclingConverter()
    if docling.supports(src):
        return docling
    raise ConversionError(
        f"No converter handles {src.name!r} — the upload allowlist and the "
        "worker's converters disagree."
    )


class UploadWorker:
    """Drives queued upload jobs through conversion and ingest.

    Attributes:
        tree: The staging tree it reads and writes.
        persist_dir: ChromaDB persist directory handed to the ingest child.
        env: Environment passed through to the ingest child.
    """

    def __init__(
        self,
        tree: StagingTree,
        *,
        persist_dir: Path,
        env: Mapping[str, str] | None = None,
        run_ingest: IngestRunner = run_ingest_subprocess,
        choose_converter: Callable[[Path], Converter] = select_converter,
    ) -> None:
        """Build a worker.

        Args:
            tree: Staging tree to work.
            persist_dir: ChromaDB persist directory for the ingest child.
            env: Environment for the ingest child; defaults to this process's.
            run_ingest: The ingest seam — swapped in tests.
            choose_converter: The converter-selection seam — swapped in tests.
        """
        self.tree = tree
        self.persist_dir = persist_dir
        self.env: Mapping[str, str] = dict(os.environ if env is None else env)
        self._run_ingest = run_ingest
        self._choose_converter = choose_converter

    # -- startup -----------------------------------------------------------

    def requeue_stranded(self) -> list[JobRecord]:
        """Re-queue every ``converting`` job, and report them.

        A job in ``converting`` means a worker died holding it: nothing else
        can be mid-conversion, because only one job is worked at a time. Its
        conversion output (if any) is a markdown file in ``sources/`` that a
        re-run will simply write beside — losing a scan is the failure worth
        avoiding, a duplicate markdown file is not.

        Returns:
            The re-queued records, in the order they were found.
        """
        requeued: list[JobRecord] = []
        for subject in self.tree.subjects():
            for record in self.tree.jobs_with_status(subject, JobStatus.CONVERTING):
                requeued.append(self.tree.transition(record, JobStatus.QUEUED))
                logger.warning(
                    "event=upload_job_requeued job_id=%s subject=%s",
                    record.job_id,
                    record.subject,
                )
        return requeued

    # -- one pass ----------------------------------------------------------

    def pending(self) -> list[JobRecord]:
        """Return the work waiting, oldest first.

        ``staged`` jobs come first: their markdown is already written, so they
        are one ingest away from done, and finishing them keeps the corpus and
        the job list agreeing.

        Returns:
            Records in ``staged`` then ``queued``, oldest first within each.
        """
        staged: list[JobRecord] = []
        queued: list[JobRecord] = []
        for subject in self.tree.subjects():
            staged.extend(self.tree.jobs_with_status(subject, JobStatus.STAGED))
            queued.extend(self.tree.jobs_with_status(subject, JobStatus.QUEUED))
        staged.sort(key=lambda r: (r.created_at, r.job_id))
        queued.sort(key=lambda r: (r.created_at, r.job_id))
        return staged + queued

    def run_once(self) -> list[JobRecord]:
        """Work the queue until it is empty, one job at a time.

        Returns:
            The final record of every job this pass touched, in the order they
            were worked (each either ``ingested`` or ``failed``).
        """
        worked: list[JobRecord] = []
        seen: set[str] = set()
        while True:
            candidates = [r for r in self.pending() if r.job_id not in seen]
            if not candidates:
                return worked
            record = candidates[0]
            # Recorded before the work, not after: a job whose own failure
            # write throws must not be picked up again in the same pass.
            seen.add(record.job_id)
            worked.append(self.process(record))

    def run_forever(
        self,
        *,
        poll_seconds: float = DEFAULT_POLL_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
        max_passes: int | None = None,
    ) -> int:
        """Poll the queue until interrupted.

        Args:
            poll_seconds: Seconds to sleep between passes.
            sleep: Sleep function — replaced in tests.
            max_passes: Stop after this many passes; ``None`` means never
                (the operator stops it with Ctrl-C).

        Returns:
            The number of jobs worked across all passes.
        """
        worked = 0
        passes = 0
        while max_passes is None or passes < max_passes:
            worked += len(self.run_once())
            passes += 1
            if max_passes is not None and passes >= max_passes:
                break
            sleep(poll_seconds)
        return worked

    # -- one job -----------------------------------------------------------

    def process(self, record: JobRecord) -> JobRecord:
        """Take one job as far as it goes: convert, stage, ingest.

        Args:
            record: A ``queued`` or ``staged`` job.

        Returns:
            The job's final record — ``ingested``, or ``failed`` carrying the
            reason. Failures are recorded, never raised: one bad scan must not
            stop the worker from converting the rest of the pile.
        """
        current = record
        try:
            if current.status is JobStatus.QUEUED:
                current = self._convert(current)
            self._ingest(current)
            current = self.tree.transition(current, JobStatus.INGESTED)
            logger.info(
                "event=upload_job_ingested job_id=%s subject=%s",
                current.job_id,
                current.subject,
            )
            return current
        except Exception as exc:  # noqa: BLE001 — every failure lands on the record
            reason = f"{type(exc).__name__}: {exc}"
            logger.error(
                "event=upload_job_failed job_id=%s subject=%s detail=%s",
                current.job_id,
                current.subject,
                reason,
            )
            return self.tree.transition(current, JobStatus.FAILED, error=reason)

    def _convert(self, record: JobRecord) -> JobRecord:
        """Convert a queued job's file into its corpus folder.

        Args:
            record: The ``queued`` record.

        Returns:
            The record, now ``staged``.

        Raises:
            ConversionError: If the file cannot be converted.
        """
        current = self.tree.transition(record, JobStatus.CONVERTING)
        src = self.tree.stored_file(current)
        dst_dir = self.tree.source_type_dir(current.subject, current.source_type)
        converter = self._choose_converter(src)
        result = converter.convert(src, dst_dir)
        for note in result.notes:
            logger.info(
                "event=upload_conversion_note job_id=%s path=%s detail=%s",
                current.job_id,
                note.path,
                note.note,
            )
        logger.info(
            "event=upload_job_staged job_id=%s subject=%s files=%s",
            current.job_id,
            current.subject,
            ",".join(p.name for p in result.produced_paths),
        )
        return self.tree.transition(current, JobStatus.STAGED)

    def _ingest(self, record: JobRecord) -> None:
        """Run the ingest for the job's whole subject.

        The unit of ingest is the subject, not the file: ``ingest_corpus.py``
        walks the four-folder tree and upserts on deterministic chunk ids, so
        re-running it after each upload is idempotent and keeps the collection
        consistent with what is on disk.

        Args:
            record: The ``staged`` record.

        Raises:
            Exception: Whatever the ingest runner raises.
        """
        invocation = build_invocation(
            subject=record.subject,
            domain_root=self.tree.sources_dir(record.subject),
            persist_dir=self.persist_dir,
            env=self.env,
        )
        logger.info(
            "event=upload_ingest_start job_id=%s subject=%s collection=%s",
            record.job_id,
            record.subject,
            subject_collection_name(record.subject),
        )
        self._run_ingest(invocation)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="process_uploads",
        description=(
            "Convert queued uploads into the four-folder corpus tree and run "
            "the ingest for their subject. Runs on the host — never in the "
            "serving image, which has neither docling nor a converter."
        ),
        epilog=(
            "Embedding configuration is taken from the environment "
            "(LLM_EMBEDDINGS_BASE_URL / _API_KEY / _MODEL) and passed to the "
            "ingest unchanged. The deployment serves LLM_EMBEDDINGS_MODEL=embed; "
            "the ingest script's built-in default is a different model, so run "
            "this with the same environment the tutor runs with."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--staging-root",
        type=Path,
        default=DEFAULT_STAGING_ROOT,
        help=f"Root of the upload staging tree. Default: {DEFAULT_STAGING_ROOT}",
    )
    parser.add_argument(
        "--persist-dir",
        type=Path,
        default=None,
        help=(
            "ChromaDB persist directory handed to the ingest. Default: "
            f"${PERSIST_DIR_ENV} or {DEFAULT_PERSIST_DIR}"
        ),
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Work the queue once and exit (cron, tests). Default: loop.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_POLL_SECONDS,
        help=(
            "Seconds between queue polls when looping. Default: "
            f"{DEFAULT_POLL_SECONDS}"
        ),
    )
    return parser


def _log_embedding_config(env: Mapping[str, str]) -> None:
    """Say which embedding configuration the ingest child will inherit.

    A worker run with the wrong (or no) ``LLM_EMBEDDINGS_MODEL`` writes a
    subject's vectors in a different embedding space from every other
    subject's, and nothing downstream complains — retrieval just returns
    nonsense. So the resolved values go in the log at startup, and an unset
    model is a warning rather than a silent default.

    Args:
        env: The environment the child will inherit.
    """
    for name in EMBEDDING_ENV_NAMES:
        value = env.get(name)
        if name.endswith("_API_KEY"):
            # Never log the value itself, whatever it is.
            logger.info("event=upload_worker_env name=%s set=%s", name, value is not None)
            continue
        logger.info("event=upload_worker_env name=%s value=%s", name, value or "(unset)")
    if not env.get("LLM_EMBEDDINGS_MODEL"):
        logger.warning(
            "event=upload_worker_embeddings_unset detail=%s",
            (
                "LLM_EMBEDDINGS_MODEL is not set, so the ingest will use its "
                "own built-in default — which is NOT the model the deployment "
                "serves. Run this worker with the tutor's environment."
            ),
        )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the worker. ``argv`` is exposed for programmatic / test use.

    Args:
        argv: Command-line arguments; ``None`` reads ``sys.argv``.

    Returns:
        Process exit code: 0 always on a clean pass or a clean interrupt —
        individual job failures live on the job records, not the exit code,
        because the operator reads them on the upload page.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
        stream=sys.stderr,
    )
    args = _build_parser().parse_args(argv)

    env: Mapping[str, str] = dict(os.environ)
    persist_dir: Path = args.persist_dir or Path(
        env.get(PERSIST_DIR_ENV, str(DEFAULT_PERSIST_DIR))
    )
    _log_embedding_config(env)
    logger.info(
        "event=upload_worker_start staging_root=%s persist_dir=%s once=%s",
        args.staging_root,
        persist_dir,
        args.once,
    )

    # The two seams are passed rather than defaulted so this entry point is
    # the single place that decides how a job gets converted and ingested.
    worker = UploadWorker(
        StagingTree(root=args.staging_root),
        persist_dir=persist_dir,
        env=env,
        run_ingest=run_ingest_subprocess,
        choose_converter=select_converter,
    )
    worker.requeue_stranded()

    if args.once:
        worked = worker.run_once()
        logger.info("event=upload_worker_done jobs=%d", len(worked))
        return 0

    try:
        worker.run_forever(poll_seconds=args.interval)
    except KeyboardInterrupt:  # pragma: no cover — operator's Ctrl-C
        logger.info("event=upload_worker_stopped")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
