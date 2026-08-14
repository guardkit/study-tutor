"""Job records: the schema, the timestamps, and the lifecycle.

These records are the whole contract between the serving process and the
host-side worker, so the schema is pinned field-by-field here.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from study_tutor.ingest.errors import InvalidJobRecord, InvalidStatusTransition
from study_tutor.ingest.jobs import (
    ALLOWED_TRANSITIONS,
    REQUIRED_FIELDS,
    JobRecord,
    JobStatus,
    utc_now_iso,
)


def make_record(**overrides: object) -> JobRecord:
    fields: dict[str, object] = {
        "job_id": "9f1d0a4c-6b6e-4c0e-9c4f-9d2f0e5a1b23",
        "subject": "english",
        "source_type": "secondary_study_guide",
        "original_filename": "macbeth-notes.pdf",
        "stored_path": "english/incoming/9f1d0a4c-6b6e-4c0e-9c4f-9d2f0e5a1b23/macbeth-notes.pdf",
        "sha256": "0" * 64,
        "size_bytes": 1234,
        "status": JobStatus.QUEUED,
        "error": None,
        "created_at": "2026-08-14T20:00:00+00:00",
        "updated_at": "2026-08-14T20:00:00+00:00",
    }
    fields.update(overrides)
    return JobRecord(**fields)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def test_schema_is_the_spec_field_list() -> None:
    assert REQUIRED_FIELDS == (
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
    assert set(make_record().to_dict()) == set(REQUIRED_FIELDS)


def test_statuses_are_the_five_spec_values() -> None:
    assert {s.value for s in JobStatus} == {
        "queued",
        "converting",
        "staged",
        "ingested",
        "failed",
    }


def test_status_serialises_as_its_string_value() -> None:
    payload = json.loads(make_record().to_json())

    assert payload["status"] == "queued"
    assert payload["error"] is None


def test_json_round_trip_is_lossless() -> None:
    record = make_record(status=JobStatus.FAILED, error="docling exploded")

    assert JobRecord.from_json(record.to_json()) == record


def test_json_ends_with_a_newline() -> None:
    assert make_record().to_json().endswith("}\n")


@pytest.mark.parametrize("missing", REQUIRED_FIELDS)
def test_missing_field_is_rejected_by_name(missing: str) -> None:
    payload = make_record().to_dict()
    del payload[missing]

    with pytest.raises(InvalidJobRecord) as exc:
        JobRecord.from_dict(payload)

    assert missing in str(exc.value)


def test_unknown_status_is_rejected() -> None:
    payload = make_record().to_dict()
    payload["status"] = "halfway"

    with pytest.raises(InvalidJobRecord) as exc:
        JobRecord.from_dict(payload)

    assert "halfway" in str(exc.value)


@pytest.mark.parametrize("size", ["1234", 12.5, None, True])
def test_non_integer_size_is_rejected(size: object) -> None:
    payload = make_record().to_dict()
    payload["size_bytes"] = size

    with pytest.raises(InvalidJobRecord):
        JobRecord.from_dict(payload)


def test_non_text_error_is_rejected() -> None:
    payload = make_record().to_dict()
    payload["error"] = {"why": "no"}

    with pytest.raises(InvalidJobRecord):
        JobRecord.from_dict(payload)


@pytest.mark.parametrize("text", ["not json at all", "[1, 2, 3]", ""])
def test_malformed_job_file_is_rejected(text: str) -> None:
    with pytest.raises(InvalidJobRecord):
        JobRecord.from_json(text)


# ---------------------------------------------------------------------------
# Timestamps
# ---------------------------------------------------------------------------


def test_timestamps_are_utc_iso() -> None:
    stamp = utc_now_iso()
    parsed = datetime.fromisoformat(stamp)

    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timezone.utc.utcoffset(None)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_the_happy_path_walk() -> None:
    record = make_record()

    record = record.with_status(JobStatus.CONVERTING, now="2026-08-14T20:01:00+00:00")
    record = record.with_status(JobStatus.STAGED, now="2026-08-14T20:02:00+00:00")
    record = record.with_status(JobStatus.INGESTED, now="2026-08-14T20:03:00+00:00")

    assert record.status is JobStatus.INGESTED
    assert record.error is None
    assert record.created_at == "2026-08-14T20:00:00+00:00"
    assert record.updated_at == "2026-08-14T20:03:00+00:00"


@pytest.mark.parametrize(
    "start", [JobStatus.QUEUED, JobStatus.CONVERTING, JobStatus.STAGED]
)
def test_any_live_status_can_fail(start: JobStatus) -> None:
    record = make_record(status=start)

    failed = record.with_status(JobStatus.FAILED, error="scanner produced 3 blank pages")

    assert failed.status is JobStatus.FAILED
    assert failed.error == "scanner produced 3 blank pages"


def test_converting_returns_to_queued_so_a_worker_restart_is_idempotent() -> None:
    record = make_record(status=JobStatus.CONVERTING)

    assert record.with_status(JobStatus.QUEUED).status is JobStatus.QUEUED


@pytest.mark.parametrize("terminal", [JobStatus.INGESTED, JobStatus.FAILED])
def test_terminal_statuses_do_not_move(terminal: JobStatus) -> None:
    record = make_record(status=terminal, error="x" if terminal is JobStatus.FAILED else None)

    assert ALLOWED_TRANSITIONS[terminal] == frozenset()
    for target in JobStatus:
        with pytest.raises(InvalidStatusTransition):
            record.with_status(target, error="anything")


@pytest.mark.parametrize(
    ("start", "target"),
    [
        (JobStatus.QUEUED, JobStatus.STAGED),
        (JobStatus.QUEUED, JobStatus.INGESTED),
        (JobStatus.CONVERTING, JobStatus.INGESTED),
        (JobStatus.STAGED, JobStatus.CONVERTING),
    ],
)
def test_skipping_a_step_is_refused(start: JobStatus, target: JobStatus) -> None:
    with pytest.raises(InvalidStatusTransition) as exc:
        make_record(status=start).with_status(target)

    assert start.value in str(exc.value)
    assert target.value in str(exc.value)


def test_failing_without_a_reason_is_refused() -> None:
    with pytest.raises(ValueError):
        make_record().with_status(JobStatus.FAILED)


def test_a_successful_transition_clears_a_stale_error() -> None:
    record = make_record(error="a note from an earlier life")

    assert record.with_status(JobStatus.CONVERTING).error is None


def test_records_are_immutable() -> None:
    record = make_record()
    moved = record.with_status(JobStatus.CONVERTING)

    assert record.status is JobStatus.QUEUED
    assert moved is not record
    with pytest.raises(Exception):
        record.status = JobStatus.FAILED  # type: ignore[misc]
