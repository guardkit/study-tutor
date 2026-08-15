"""Unit tests for the upload surface's HTTP routes (Lane 3 step 4, B-stage).

Follows ``test_student_model.py``'s harness — ``create_app`` with a real
``HTTPAuthConfig``, the fake ``StudentStore``, and Starlette's ``TestClient``
— so the auth guard, the ingest guards, and the staging write are exercised
together rather than mocked past.

The staging tree always points at ``tmp_path``: nothing here writes to
``data/uploads``. Hermetic throughout — no network, no docling, no broker, no
docker.

Covered:

* the four routes do not exist when no ``UploadService`` is wired (404, the
  voice/dev_reset existence gate — never 403);
* the page is served unauthenticated and is genuinely self-contained;
* every API route is bearer-authed (401 without, 401 on a rejected bearer);
* guard failures surface as 400 / 413 / 422 with a plain ``{"error": ...}``
  body and no ``error_type`` (binding §4.2);
* the happy path writes real bytes plus a ``queued`` job record, and both job
  reads see it;
* the boot gate: ``_build_upload_service`` builds a service only when
  ``STUDY_TUTOR_UPLOAD_ENABLED`` is truthy.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from unittest.mock import AsyncMock

import pytest
from starlette.testclient import TestClient

from study_tutor.http.app import UploadService, create_app
from study_tutor.http.auth import HTTPAuthConfig
from study_tutor.ingest.config import UploadConfig
from tests.unit.knowledge.store.fakes import FakeStudentStore

BEARER = {"Authorization": "Bearer test-token-student-a"}


# -- Harness -----------------------------------------------------------------


@pytest.fixture
def auth_config() -> HTTPAuthConfig:
    from study_tutor.http.auth import TableTokenResolver

    token_to_student = {"test-token-student-a": "lilymay"}
    return HTTPAuthConfig(
        token_to_student=token_to_student,
        dev_reset=False,
        resolver=TableTokenResolver(token_to_student=token_to_student),
    )


@pytest.fixture
def store() -> FakeStudentStore:
    s = FakeStudentStore()
    s.add_student("lilymay", name="Lily May", year_group=10, target_grade="7")
    return s


@pytest.fixture
def staging_root(tmp_path: Path) -> Path:
    return tmp_path / "uploads"


@pytest.fixture
def upload_config(staging_root: Path) -> UploadConfig:
    return UploadConfig(
        enabled=True,
        max_file_bytes=4096,
        subject_quota_bytes=16384,
        staging_root=staging_root,
    )


@pytest.fixture
def upload_service(upload_config: UploadConfig) -> UploadService:
    return UploadService.from_config(upload_config)


def _client(
    auth_config: HTTPAuthConfig,
    store: FakeStudentStore,
    upload_service: UploadService | None,
) -> TestClient:
    app = create_app(
        service=AsyncMock(),
        reply_fn=AsyncMock(),
        auth_config=auth_config,
        student_store=store,
        upload_service=upload_service,
    )
    return TestClient(app)


@pytest.fixture
def client(
    auth_config: HTTPAuthConfig,
    store: FakeStudentStore,
    upload_service: UploadService,
) -> TestClient:
    return _client(auth_config, store, upload_service)


@pytest.fixture
def client_without_upload(
    auth_config: HTTPAuthConfig, store: FakeStudentStore
) -> TestClient:
    return _client(auth_config, store, None)


def _post(
    client: TestClient,
    *,
    filename: str = "notes.md",
    content: bytes = b"# Macbeth notes\n\nAmbition and guilt.\n",
    subject: str = "english",
    source_type: str = "primary_text",
    headers: dict[str, str] | None = None,
):
    return client.post(
        "/api/corpus/upload",
        files={"file": (filename, content, "application/octet-stream")},
        data={"subject": subject, "source_type": source_type},
        headers=BEARER if headers is None else headers,
    )


# -- Existence gate ----------------------------------------------------------


@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/upload"),
        ("post", "/api/corpus/upload"),
        ("get", "/api/corpus/jobs"),
        ("get", "/api/corpus/jobs/1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed"),
    ],
)
def test_routes_absent_without_an_upload_service(
    client_without_upload: TestClient, method: str, path: str
) -> None:
    """No service ⇒ the paths are unknown paths. 404, never 403."""
    resp = getattr(client_without_upload, method)(path, headers=BEARER)
    assert resp.status_code == 404


def test_existing_routes_are_untouched_by_the_gate(
    client_without_upload: TestClient, client: TestClient
) -> None:
    """Mounting the surface changes nothing about the frozen routes."""
    for c in (client_without_upload, client):
        assert c.get("/healthz").status_code == 200
        assert c.get("/api/version", headers=BEARER).status_code == 200


# -- The page ----------------------------------------------------------------


def test_page_is_served_unauthenticated(client: TestClient) -> None:
    resp = client.get("/upload")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "Upload study material" in resp.text


def test_page_offers_every_control_the_operator_needs(client: TestClient) -> None:
    from study_tutor.ingest.guards import SOURCE_TYPE_NAMES

    body = client.get("/upload").text
    assert 'type="file"' in body
    assert 'id="subject"' in body
    for name in SOURCE_TYPE_NAMES:
        assert f'value="{name}"' in body
    assert "/api/corpus/upload" in body
    assert "/api/corpus/jobs" in body


def test_page_is_self_contained_and_stores_no_token(client: TestClient) -> None:
    """No CDN, no framework, and the bearer never leaves JS memory.

    Asserted against the page with its comments stripped — the comments
    describe what the page deliberately does NOT do, and would otherwise match
    the very names they promise are absent.
    """
    body = re.sub(r"<!--.*?-->", "", client.get("/upload").text, flags=re.DOTALL)
    body = re.sub(r"^\s*//.*$", "", body, flags=re.MULTILINE)
    assert "src=" not in body  # no external (or any) script/image src
    assert "http://" not in body
    assert "https://" not in body
    assert "localStorage" not in body
    assert "sessionStorage" not in body
    assert "document.cookie" not in body


# -- Auth --------------------------------------------------------------------


def test_upload_without_bearer_is_401(client: TestClient) -> None:
    resp = _post(client, headers={})
    assert resp.status_code == 401
    assert resp.json()["error_type"] == "Unauthenticated"


def test_upload_with_rejected_bearer_is_401(client: TestClient) -> None:
    resp = _post(client, headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
    assert resp.json()["error_type"] == "Unauthenticated"


def test_job_list_without_bearer_is_401(client: TestClient) -> None:
    resp = client.get("/api/corpus/jobs")
    assert resp.status_code == 401
    assert resp.json()["error_type"] == "Unauthenticated"


def test_single_job_without_bearer_is_401(client: TestClient) -> None:
    resp = client.get("/api/corpus/jobs/1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed")
    assert resp.status_code == 401
    assert resp.json()["error_type"] == "Unauthenticated"


def test_unauthenticated_upload_writes_nothing(
    client: TestClient, staging_root: Path
) -> None:
    _post(client, headers={})
    assert not staging_root.exists()


def test_any_seeded_learner_may_upload_there_is_no_operator_role(
    client: TestClient,
) -> None:
    """Posture pin: these routes are **authed, not authorised**.

    ``_resolve_student_id`` — which the spec ordered these routes use, exactly
    like every other route — accepts any bearer in the token table that has a
    ``StudentStore`` row. ``test-token-student-a`` here is the *learner's* own
    token (``lilymay``, the child), not a privileged operator credential; there
    is no operator role, group or scope in the token table to check, and adding
    one was outside the build spec (no auth changes).

    So the learner's token can write to the corpus staging tree whenever the
    flag is on. That is harmless while the flag is set nowhere and the surface
    is tailnet-only, and it is stated in RUNBOOK-upload-surface.md §3 and §9 —
    pinned here so nobody reads "bearer-authed" as "operator-only".
    """
    assert _post(client).status_code == 202
    assert client.get("/api/corpus/jobs", headers=BEARER).status_code == 200

    job_id = _post(client, filename="second.md").json()["job_id"]
    resp = client.get(f"/api/corpus/jobs/{job_id}", headers=BEARER)
    assert resp.status_code == 200


def test_runbook_does_not_promise_an_operator_credential() -> None:
    """The runbook must not imply a privileged bearer that does not exist."""
    runbook = (
        Path(__file__).resolve().parents[3]
        / "docs"
        / "runbooks"
        / "RUNBOOK-upload-surface.md"
    ).read_text(encoding="utf-8")

    assert "Paste the operator bearer" not in runbook
    assert "There is no operator role." in runbook


def test_wrong_method_is_405(client: TestClient) -> None:
    assert client.get("/api/corpus/upload", headers=BEARER).status_code == 405
    assert client.post("/api/corpus/jobs", headers=BEARER).status_code == 405


# -- Happy path --------------------------------------------------------------


def test_upload_returns_202_with_a_queued_job(client: TestClient) -> None:
    resp = _post(client)
    assert resp.status_code == 202
    body = resp.json()
    assert body["status"] == "queued"
    assert body["job_id"]


def test_upload_writes_the_bytes_and_the_job_record(
    client: TestClient, staging_root: Path
) -> None:
    content = b"# Macbeth notes\n\nAmbition and guilt.\n"
    job_id = _post(client, content=content).json()["job_id"]

    stored = staging_root / "english" / "incoming" / job_id / "notes.md"
    assert stored.read_bytes() == content

    record = json.loads(
        (staging_root / "english" / "jobs" / f"{job_id}.json").read_text()
    )
    assert record["job_id"] == job_id
    assert record["subject"] == "english"
    assert record["source_type"] == "primary_text"
    assert record["original_filename"] == "notes.md"
    assert record["status"] == "queued"
    assert record["size_bytes"] == len(content)
    assert record["error"] is None


def test_upload_creates_the_four_folder_sources_tree(
    client: TestClient, staging_root: Path
) -> None:
    """The worker points the existing ingest script at sources/ — all four
    folders must exist even when only one has content."""
    from study_tutor.ingest.guards import SOURCE_TYPE_NAMES

    _post(client)
    sources = staging_root / "english" / "sources"
    for name in SOURCE_TYPE_NAMES:
        assert (sources / name).is_dir()


def test_filename_is_reduced_to_a_basename(
    client: TestClient, staging_root: Path
) -> None:
    job_id = _post(client, filename="../../etc/notes.md").json()["job_id"]
    stored = staging_root / "english" / "incoming" / job_id
    assert [p.name for p in stored.iterdir()] == ["notes.md"]


def test_job_list_returns_the_upload(client: TestClient) -> None:
    job_id = _post(client).json()["job_id"]
    resp = client.get("/api/corpus/jobs?subject=english", headers=BEARER)
    assert resp.status_code == 200
    jobs = resp.json()
    assert [j["job_id"] for j in jobs] == [job_id]
    assert jobs[0]["status"] == "queued"


def test_job_list_without_subject_spans_every_subject(client: TestClient) -> None:
    english = _post(client, subject="english").json()["job_id"]
    history = _post(client, subject="demo_history").json()["job_id"]
    jobs = client.get("/api/corpus/jobs", headers=BEARER).json()
    assert {j["job_id"] for j in jobs} == {english, history}


def test_job_list_is_empty_before_any_upload(client: TestClient) -> None:
    assert client.get("/api/corpus/jobs", headers=BEARER).json() == []


def test_single_job_read(client: TestClient) -> None:
    job_id = _post(client).json()["job_id"]
    resp = client.get(f"/api/corpus/jobs/{job_id}", headers=BEARER)
    assert resp.status_code == 200
    assert resp.json()["job_id"] == job_id
    assert resp.json()["original_filename"] == "notes.md"


def test_single_job_read_scoped_by_subject(client: TestClient) -> None:
    job_id = _post(client, subject="english").json()["job_id"]
    found = client.get(f"/api/corpus/jobs/{job_id}?subject=english", headers=BEARER)
    missing = client.get(
        f"/api/corpus/jobs/{job_id}?subject=demo_history", headers=BEARER
    )
    assert found.status_code == 200
    assert missing.status_code == 404


def test_unknown_job_is_404(client: TestClient) -> None:
    resp = client.get(
        "/api/corpus/jobs/1b9d6bcd-bbfd-4b2d-9b5d-ab8dfbbd4bed", headers=BEARER
    )
    assert resp.status_code == 404
    assert "error_type" not in resp.json()


def test_non_uuid_job_id_is_404_not_500(client: TestClient) -> None:
    """An id that cannot exist and one that does not are the same answer."""
    _post(client)  # so a subject dir exists to be searched
    resp = client.get("/api/corpus/jobs/not-a-uuid", headers=BEARER)
    assert resp.status_code == 404


# -- Guards ------------------------------------------------------------------


def test_bad_subject_is_400(client: TestClient, staging_root: Path) -> None:
    resp = _post(client, subject="../escape")
    assert resp.status_code == 400
    assert "error_type" not in resp.json()
    assert not staging_root.exists()


def test_empty_subject_is_400(client: TestClient) -> None:
    assert _post(client, subject="").status_code == 400


def test_bad_source_type_is_400(client: TestClient) -> None:
    resp = _post(client, source_type="primary-text")
    assert resp.status_code == 400
    body = resp.json()
    assert "error_type" not in body
    assert "primary_text" in body["error"]  # names the four folders


def test_missing_source_type_is_400(client: TestClient) -> None:
    resp = client.post(
        "/api/corpus/upload",
        files={"file": ("notes.md", b"hello", "application/octet-stream")},
        data={"subject": "english"},
        headers=BEARER,
    )
    assert resp.status_code == 400


def test_missing_file_part_is_400(client: TestClient) -> None:
    resp = client.post(
        "/api/corpus/upload",
        data={"subject": "english", "source_type": "primary_text"},
        headers=BEARER,
    )
    assert resp.status_code == 400
    assert "error_type" not in resp.json()


def test_unsupported_extension_is_400(client: TestClient) -> None:
    resp = _post(client, filename="revision.docx")
    assert resp.status_code == 400
    assert ".pdf" in resp.json()["error"]


def test_empty_file_is_400(client: TestClient) -> None:
    resp = _post(client, content=b"")
    assert resp.status_code == 400


def test_assessment_material_is_422(client: TestClient, staging_root: Path) -> None:
    """AQA prohibits redistribution — refused at the door, never stored."""
    resp = _post(client, filename="aqa-mark-scheme.pdf")
    assert resp.status_code == 422
    assert "error_type" not in resp.json()
    assert "AQA" in resp.json()["error"]
    assert not staging_root.exists()


@pytest.mark.parametrize(
    "filename", ["past-paper-2023.pdf", "mark_scheme.pdf", "examiner-report.pdf"]
)
def test_every_refused_assessment_shape_is_422(
    client: TestClient, filename: str
) -> None:
    assert _post(client, filename=filename).status_code == 422


def test_oversized_file_is_413(client: TestClient) -> None:
    """Over the per-file cap (4096 bytes here) — the guard on the real bytes."""
    resp = _post(client, content=b"x" * 5000)
    assert resp.status_code == 413
    assert "error_type" not in resp.json()


def test_grossly_oversized_body_is_413_before_it_is_parsed(
    client: TestClient,
) -> None:
    """Past the Content-Length pre-check's slack, the body is refused up front."""
    resp = _post(client, content=b"x" * (4096 + 64 * 1024 + 1))
    assert resp.status_code == 413


def test_subject_quota_is_413(client: TestClient) -> None:
    """The quota bounds the whole staging area, not just the uploaded bytes.

    16KB quota, ~4KB files: three go in, and the fourth is refused — the job
    records staged alongside the bytes count too, which is the point of a
    disk quota.
    """
    chunk = b"y" * 4000
    for index in range(3):
        accepted = _post(client, filename=f"part{index}.md", content=chunk)
        assert accepted.status_code == 202
    resp = _post(client, filename="part3.md", content=chunk)
    assert resp.status_code == 413
    assert "per-subject limit" in resp.json()["error"]


def test_a_refusal_leaves_the_earlier_jobs_alone(client: TestClient) -> None:
    good = _post(client, filename="good.md").json()["job_id"]
    assert _post(client, filename="mark-scheme.pdf").status_code == 422
    jobs = client.get("/api/corpus/jobs?subject=english", headers=BEARER).json()
    assert [j["job_id"] for j in jobs] == [good]


def test_job_list_with_a_bad_subject_is_400(client: TestClient) -> None:
    resp = client.get("/api/corpus/jobs?subject=../escape", headers=BEARER)
    assert resp.status_code == 400
    assert "error_type" not in resp.json()


# -- Boot gate ---------------------------------------------------------------


def test_build_upload_service_returns_none_when_flag_unset() -> None:
    from study_tutor.cli.main import _build_upload_service

    assert _build_upload_service({}) is None


def test_build_upload_service_returns_none_when_flag_false() -> None:
    from study_tutor.cli.main import _build_upload_service

    assert _build_upload_service({"STUDY_TUTOR_UPLOAD_ENABLED": "false"}) is None


def test_build_upload_service_constructs_when_enabled() -> None:
    from study_tutor.cli.main import _build_upload_service
    from study_tutor.ingest.config import DEFAULT_STAGING_ROOT

    service = _build_upload_service({"STUDY_TUTOR_UPLOAD_ENABLED": "1"})
    assert isinstance(service, UploadService)
    assert service.config.enabled is True
    assert service.config.staging_root == DEFAULT_STAGING_ROOT


def test_build_upload_service_honours_the_size_overrides() -> None:
    from study_tutor.cli.main import _build_upload_service

    service = _build_upload_service(
        {
            "STUDY_TUTOR_UPLOAD_ENABLED": "1",
            "STUDY_TUTOR_UPLOAD_MAX_FILE_MB": "7",
            "STUDY_TUTOR_UPLOAD_SUBJECT_QUOTA_MB": "70",
        }
    )
    assert service.config.max_file_bytes == 7 * 1024 * 1024
    assert service.config.subject_quota_bytes == 70 * 1024 * 1024


def test_build_upload_service_refuses_a_malformed_flag() -> None:
    """A typo'd flag fails boot loudly rather than silently disabling."""
    from study_tutor.cli.main import _build_upload_service

    with pytest.raises(ValueError, match="STUDY_TUTOR_UPLOAD_ENABLED"):
        _build_upload_service({"STUDY_TUTOR_UPLOAD_ENABLED": "maybe"})


def test_building_a_service_creates_no_directories(tmp_path: Path) -> None:
    """Booting with the surface on must not pre-create subject folders."""
    root = tmp_path / "uploads"
    UploadService.from_config(UploadConfig(enabled=True, staging_root=root))
    assert not root.exists()
