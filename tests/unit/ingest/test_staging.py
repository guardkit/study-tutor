"""The staging tree: layout, the queued write, quota accounting, reads.

Every test writes under ``tmp_path``. Nothing here touches ``data/uploads``,
the repo's ``data/chroma``, a network, or a broker.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from study_tutor.ingest.config import BYTES_PER_MB, UploadConfig
from study_tutor.ingest.errors import (
    FileTooLarge,
    InvalidFilename,
    InvalidSourceType,
    InvalidSubject,
    JobNotFound,
    RefusedMaterial,
    SubjectQuotaExceeded,
    UnsupportedFileType,
)
from study_tutor.ingest.guards import SOURCE_TYPE_NAMES
from study_tutor.ingest.jobs import JobRecord, JobStatus
from study_tutor.ingest.staging import StagingTree


@pytest.fixture()
def tree(tmp_path: Path) -> StagingTree:
    return StagingTree(root=tmp_path / "uploads")


@pytest.fixture()
def config(tmp_path: Path) -> UploadConfig:
    return UploadConfig.from_env({}, staging_root=tmp_path / "uploads")


def upload(tree: StagingTree, config: UploadConfig, **overrides: object) -> JobRecord:
    kwargs: dict[str, object] = {
        "subject": "english",
        "source_type": "secondary_study_guide",
        "filename": "macbeth-notes.txt",
        "data": b"Macbeth is a play about ambition.\n",
        "config": config,
    }
    kwargs.update(overrides)
    return tree.accept_upload(**kwargs)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Layout
# ---------------------------------------------------------------------------


def test_from_config_roots_the_tree_at_the_configured_path(
    tmp_path: Path, config: UploadConfig
) -> None:
    assert StagingTree.from_config(config).root == tmp_path / "uploads"


def test_ensure_subject_builds_the_whole_layout(tree: StagingTree) -> None:
    subject_dir = tree.ensure_subject("english")

    assert subject_dir == tree.root / "english"
    assert (subject_dir / "incoming").is_dir()
    assert (subject_dir / "jobs").is_dir()
    assert (subject_dir / "sources").is_dir()
    for folder in SOURCE_TYPE_NAMES:
        assert (subject_dir / "sources" / folder).is_dir()


def test_sources_is_the_four_folder_corpus_shape(tree: StagingTree) -> None:
    """The worker points the existing ingest script straight at sources/."""
    tree.ensure_subject("demo_history")

    found = {p.name for p in tree.sources_dir("demo_history").iterdir() if p.is_dir()}
    assert found == set(SOURCE_TYPE_NAMES)


def test_ensure_subject_is_idempotent(tree: StagingTree) -> None:
    tree.ensure_subject("english")
    (tree.sources_dir("english") / "primary_text" / "keep.md").write_text("hi")

    tree.ensure_subject("english")

    assert (tree.sources_dir("english") / "primary_text" / "keep.md").is_file()


def test_paths_refuse_an_unvalidated_subject(tree: StagingTree) -> None:
    for call in (
        tree.subject_dir,
        tree.incoming_dir,
        tree.jobs_dir,
        tree.sources_dir,
        tree.ensure_subject,
        tree.subject_usage_bytes,
        tree.list_jobs,
    ):
        with pytest.raises(InvalidSubject):
            call("../../etc")


def test_source_type_dir_refuses_an_unknown_folder(tree: StagingTree) -> None:
    with pytest.raises(InvalidSourceType):
        tree.source_type_dir("english", "primary-text")


def test_subjects_lists_only_valid_subject_directories(tree: StagingTree) -> None:
    tree.ensure_subject("english")
    tree.ensure_subject("demo_history")
    (tree.root / "NotASubject").mkdir()
    (tree.root / "stray-file.txt").write_text("x")

    assert tree.subjects() == ["demo_history", "english"]


def test_subjects_is_empty_before_anything_is_uploaded(tree: StagingTree) -> None:
    assert tree.subjects() == []


# ---------------------------------------------------------------------------
# accept_upload — the one write the serving process makes
# ---------------------------------------------------------------------------


def test_accept_upload_stores_bytes_and_a_queued_record(
    tree: StagingTree, config: UploadConfig
) -> None:
    data = b"Macbeth is a play about ambition.\n"
    record = upload(tree, config, data=data)

    assert record.status is JobStatus.QUEUED
    assert record.error is None
    assert record.subject == "english"
    assert record.source_type == "secondary_study_guide"
    assert record.original_filename == "macbeth-notes.txt"
    assert record.size_bytes == len(data)
    assert record.sha256 == hashlib.sha256(data).hexdigest()
    assert record.created_at == record.updated_at

    stored = tree.stored_file(record)
    assert stored.read_bytes() == data
    assert stored == tree.root / "english" / "incoming" / record.job_id / "macbeth-notes.txt"


def test_stored_path_is_relative_to_the_root_not_absolute(
    tree: StagingTree, config: UploadConfig
) -> None:
    record = upload(tree, config)

    assert not Path(record.stored_path).is_absolute()
    assert record.stored_path == (
        f"english/incoming/{record.job_id}/macbeth-notes.txt"
    )


def test_job_ids_are_uuid4_and_unique(tree: StagingTree, config: UploadConfig) -> None:
    import uuid

    first = upload(tree, config)
    second = upload(tree, config)

    assert first.job_id != second.job_id
    assert uuid.UUID(first.job_id).version == 4


def test_the_job_file_lands_where_the_worker_looks(
    tree: StagingTree, config: UploadConfig
) -> None:
    record = upload(tree, config)

    path = tree.root / "english" / "jobs" / f"{record.job_id}.json"
    assert path.is_file()
    assert json.loads(path.read_text())["status"] == "queued"


def test_two_uploads_of_the_same_filename_do_not_collide(
    tree: StagingTree, config: UploadConfig
) -> None:
    first = upload(tree, config, data=b"first version\n")
    second = upload(tree, config, data=b"second version\n")

    assert tree.stored_file(first).read_bytes() == b"first version\n"
    assert tree.stored_file(second).read_bytes() == b"second version\n"


def test_a_traversing_filename_lands_inside_its_own_job_directory(
    tree: StagingTree, config: UploadConfig
) -> None:
    record = upload(tree, config, filename="../../../../etc/notes.txt")

    stored = tree.stored_file(record)
    assert record.original_filename == "notes.txt"
    assert stored.parent == tree.root / "english" / "incoming" / record.job_id
    assert stored.is_file()
    assert not (tree.root.parent / "notes.txt").exists()


# ---------------------------------------------------------------------------
# Guards, at the staging boundary — a refused upload writes nothing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("overrides", "expected"),
    [
        ({"subject": "English"}, InvalidSubject),
        ({"source_type": "notes"}, InvalidSourceType),
        ({"filename": "notes.exe"}, UnsupportedFileType),
        ({"filename": "past-paper.pdf"}, RefusedMaterial),
        ({"filename": "  "}, InvalidFilename),
    ],
)
def test_refused_upload_writes_nothing(
    tree: StagingTree,
    config: UploadConfig,
    overrides: dict[str, object],
    expected: type[Exception],
) -> None:
    with pytest.raises(expected):
        upload(tree, config, **overrides)

    # Not even the subject's directory tree gets created for a refused upload.
    assert list(tree.root.rglob("*.json")) == []


def test_oversized_upload_refused_and_not_written(tmp_path: Path) -> None:
    config = UploadConfig.from_env(
        {"STUDY_TUTOR_UPLOAD_MAX_FILE_MB": "1"}, staging_root=tmp_path / "uploads"
    )
    tree = StagingTree.from_config(config)

    with pytest.raises(FileTooLarge):
        upload(tree, config, data=b"x" * (BYTES_PER_MB + 1))

    assert tree.list_jobs("english") == []


def test_empty_upload_refused(tree: StagingTree, config: UploadConfig) -> None:
    with pytest.raises(ValueError):
        upload(tree, config, data=b"")


# ---------------------------------------------------------------------------
# Quota accounting
# ---------------------------------------------------------------------------


def test_usage_is_zero_for_an_untouched_subject(tree: StagingTree) -> None:
    assert tree.subject_usage_bytes("english") == 0


def test_usage_counts_the_stored_bytes(
    tree: StagingTree, config: UploadConfig
) -> None:
    record = upload(tree, config, data=b"x" * 500)

    usage = tree.subject_usage_bytes("english")
    assert usage >= 500
    assert usage >= record.size_bytes


def test_usage_is_per_subject(tree: StagingTree, config: UploadConfig) -> None:
    upload(tree, config, subject="english", data=b"x" * 500)

    assert tree.subject_usage_bytes("demo_history") == 0


def test_quota_stops_the_upload_that_would_overflow(tmp_path: Path) -> None:
    config = UploadConfig.from_env(
        {"STUDY_TUTOR_UPLOAD_SUBJECT_QUOTA_MB": "1"},
        staging_root=tmp_path / "uploads",
    )
    tree = StagingTree.from_config(config)

    upload(tree, config, filename="first.txt", data=b"x" * (BYTES_PER_MB // 2))

    with pytest.raises(SubjectQuotaExceeded):
        upload(tree, config, filename="second.txt", data=b"x" * BYTES_PER_MB)

    assert len(tree.list_jobs("english")) == 1


# ---------------------------------------------------------------------------
# Reads and transitions — the worker's side of the contract
# ---------------------------------------------------------------------------


def test_read_job_returns_what_was_written(
    tree: StagingTree, config: UploadConfig
) -> None:
    record = upload(tree, config)

    assert tree.read_job("english", record.job_id) == record


def test_read_job_missing_id(tree: StagingTree, config: UploadConfig) -> None:
    upload(tree, config)

    with pytest.raises(JobNotFound):
        tree.read_job("english", "0f8fad5b-d9cb-469f-a165-70867728950e")


@pytest.mark.parametrize("job_id", ["../../etc/passwd", "not-a-uuid", ""])
def test_a_job_id_that_is_not_a_uuid_is_simply_not_found(
    tree: StagingTree, job_id: str
) -> None:
    with pytest.raises(JobNotFound):
        tree.read_job("english", job_id)


def test_list_jobs_is_newest_first(tree: StagingTree, config: UploadConfig) -> None:
    older = upload(tree, config, filename="a.txt", now="2026-08-14T20:00:00+00:00")
    newer = upload(tree, config, filename="b.txt", now="2026-08-14T21:00:00+00:00")

    assert [r.job_id for r in tree.list_jobs("english")] == [
        newer.job_id,
        older.job_id,
    ]


def test_list_jobs_is_empty_for_an_unknown_subject(tree: StagingTree) -> None:
    assert tree.list_jobs("demo_history") == []


def test_jobs_with_status_is_the_workers_queue_oldest_first(
    tree: StagingTree, config: UploadConfig
) -> None:
    older = upload(tree, config, filename="a.txt", now="2026-08-14T20:00:00+00:00")
    newer = upload(tree, config, filename="b.txt", now="2026-08-14T21:00:00+00:00")
    tree.transition(newer, JobStatus.CONVERTING, now="2026-08-14T21:05:00+00:00")

    queued = tree.jobs_with_status("english", JobStatus.QUEUED)
    converting = tree.jobs_with_status("english", JobStatus.CONVERTING)

    assert [r.job_id for r in queued] == [older.job_id]
    assert [r.job_id for r in converting] == [newer.job_id]


def test_transition_rewrites_the_same_job_file(
    tree: StagingTree, config: UploadConfig
) -> None:
    record = upload(tree, config)

    moved = tree.transition(record, JobStatus.CONVERTING, now="2026-08-14T20:05:00+00:00")

    assert tree.read_job("english", record.job_id) == moved
    assert moved.updated_at == "2026-08-14T20:05:00+00:00"
    assert moved.created_at == record.created_at
    assert len(list(tree.jobs_dir("english").glob("*.json"))) == 1


def test_failure_is_persisted_with_its_reason(
    tree: StagingTree, config: UploadConfig
) -> None:
    record = upload(tree, config)
    converting = tree.transition(record, JobStatus.CONVERTING)

    failed = tree.transition(
        converting, JobStatus.FAILED, error="docling is not installed"
    )

    reread = tree.read_job("english", record.job_id)
    assert reread.status is JobStatus.FAILED
    assert reread.error == "docling is not installed"
    assert failed == reread


def test_the_full_walk_survives_a_round_trip_through_disk(
    tree: StagingTree, config: UploadConfig
) -> None:
    record = upload(tree, config)

    for status in (JobStatus.CONVERTING, JobStatus.STAGED, JobStatus.INGESTED):
        record = tree.transition(tree.read_job("english", record.job_id), status)

    assert tree.read_job("english", record.job_id).status is JobStatus.INGESTED


def test_no_temporary_files_are_left_behind(
    tree: StagingTree, config: UploadConfig
) -> None:
    record = upload(tree, config)
    tree.transition(record, JobStatus.CONVERTING)

    assert list(tree.root.rglob("*.tmp")) == []


def test_relative_path_refuses_a_path_outside_the_tree(tree: StagingTree) -> None:
    with pytest.raises(ValueError):
        tree.relative_path(Path("/etc/passwd"))


def test_a_malformed_job_file_is_reported_not_swallowed(
    tree: StagingTree, config: UploadConfig
) -> None:
    record = upload(tree, config)
    tree.job_path("english", record.job_id).write_text("{oh no")

    from study_tutor.ingest.errors import InvalidJobRecord

    with pytest.raises(InvalidJobRecord):
        tree.read_job("english", record.job_id)


def test_job_record_type_is_what_reads_return(
    tree: StagingTree, config: UploadConfig
) -> None:
    record = upload(tree, config)

    assert isinstance(tree.read_job("english", record.job_id), JobRecord)
