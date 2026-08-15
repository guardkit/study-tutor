"""The upload worker — queued job in, ingested subject out.

Hermetic throughout: the converter and the ingest are both seams the worker
takes as arguments, so no test here converts a real scan, runs a subprocess, or
reaches a network. The one test that does run the real
``scripts/ingest_corpus.py`` runs it *in-process* against a temporary ChromaDB
directory with a stub embedding function — that is the test the build spec asks
for by name ("VERIFY … where ingest_corpus.py writes the per-subject sidecar
and that rag_wiring subject discovery would find the resulting collection").
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Sequence

import pytest

from scripts import process_uploads
from scripts.process_uploads import (
    IngestFailed,
    IngestInvocation,
    UploadWorker,
    build_invocation,
    run_ingest_subprocess,
    select_converter,
)
from study_tutor.cli.rag_wiring import subject_collection_name
from study_tutor.ingest.config import UploadConfig
from study_tutor.ingest.converter import (
    ConversionError,
    ConversionResult,
    PassthroughConverter,
)
from study_tutor.ingest.converter_docling import DoclingConverter
from study_tutor.ingest.jobs import JobRecord, JobStatus
from study_tutor.ingest.staging import StagingTree

SUBJECT = "demo_history"

#: Enough prose for the real chunker to make several chunks in the seam test.
FIXTURE_PARAGRAPHS = "\n\n".join(
    f"Paragraph {n}. The tutor's staging tree carries this text from an "
    "upload through conversion into the four-folder corpus the ingest script "
    "already knows how to walk, which is the whole point of the surface."
    for n in range(1, 21)
)


# ---------------------------------------------------------------------------
# Fixtures and fakes
# ---------------------------------------------------------------------------


@pytest.fixture
def staging_root(tmp_path: Path) -> Path:
    return tmp_path / "uploads"


@pytest.fixture
def tree(staging_root: Path) -> StagingTree:
    return StagingTree(root=staging_root)


@pytest.fixture
def config(staging_root: Path) -> UploadConfig:
    return UploadConfig(enabled=True, staging_root=staging_root)


def queue_upload(
    tree: StagingTree,
    config: UploadConfig,
    *,
    filename: str = "notes.md",
    data: bytes = b"typed notes\n",
    source_type: str = "primary_text",
    subject: str = SUBJECT,
    now: str | None = None,
) -> JobRecord:
    """Put one ``queued`` job in the tree, the way the HTTP surface would."""
    return tree.accept_upload(
        subject=subject,
        source_type=source_type,
        filename=filename,
        data=data,
        config=config,
        now=now,
    )


class RecordingConverter:
    """A converter that writes a fixed markdown file and remembers its calls."""

    def __init__(self, *, markdown: str = "converted\n", error: Exception | None = None):
        self.markdown = markdown
        self.error = error
        self.calls: list[tuple[Path, Path]] = []

    def convert(self, src: Path, dst_dir: Path) -> ConversionResult:
        self.calls.append((src, dst_dir))
        if self.error is not None:
            raise self.error
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / (src.stem + ".md")
        dst.write_text(self.markdown, encoding="utf-8")
        return ConversionResult(produced_paths=(dst,))


class RecordingIngest:
    """The ingest seam: records invocations, optionally fails."""

    def __init__(self, *, error: Exception | None = None):
        self.error = error
        self.calls: list[IngestInvocation] = []

    def __call__(self, invocation: IngestInvocation) -> None:
        self.calls.append(invocation)
        if self.error is not None:
            raise self.error


def build_worker(
    tree: StagingTree,
    *,
    converter: Any,
    ingest: Any,
    persist_dir: Path,
    env: dict[str, str] | None = None,
) -> UploadWorker:
    return UploadWorker(
        tree,
        persist_dir=persist_dir,
        env=env if env is not None else {},
        run_ingest=ingest,
        choose_converter=lambda src: converter,
    )


def flag_value(argv: Sequence[str], flag: str) -> str:
    """Return the value following ``flag`` in ``argv``."""
    return argv[list(argv).index(flag) + 1]


# ---------------------------------------------------------------------------
# The happy path
# ---------------------------------------------------------------------------


def test_a_queued_job_is_converted_staged_and_ingested(
    tree: StagingTree, config: UploadConfig, tmp_path: Path
) -> None:
    record = queue_upload(tree, config, filename="chapter-one.md")
    converter = RecordingConverter(markdown="# Chapter one\n")
    ingest = RecordingIngest()
    worker = build_worker(
        tree,
        converter=converter,
        ingest=ingest,
        persist_dir=tmp_path / "chroma",
        env={"LLM_EMBEDDINGS_MODEL": "embed"},
    )

    worked = worker.run_once()

    assert [r.job_id for r in worked] == [record.job_id]
    assert worked[0].status is JobStatus.INGESTED
    assert worked[0].error is None
    # The record on disk agrees with the record returned.
    assert tree.read_job(SUBJECT, record.job_id).status is JobStatus.INGESTED

    # The markdown landed in the corpus folder the upload named.
    staged_file = tree.source_type_dir(SUBJECT, "primary_text") / "chapter-one.md"
    assert staged_file.read_text(encoding="utf-8") == "# Chapter one\n"
    assert converter.calls == [
        (tree.stored_file(record), tree.source_type_dir(SUBJECT, "primary_text"))
    ]


def test_the_ingest_is_told_the_subject_its_sources_and_its_collection(
    tree: StagingTree, config: UploadConfig, tmp_path: Path
) -> None:
    queue_upload(tree, config)
    ingest = RecordingIngest()
    persist_dir = tmp_path / "chroma"
    worker = build_worker(
        tree,
        converter=RecordingConverter(),
        ingest=ingest,
        persist_dir=persist_dir,
        env={"LLM_EMBEDDINGS_MODEL": "embed", "LLM_EMBEDDINGS_BASE_URL": "http://x/v1"},
    )

    worker.run_once()

    assert len(ingest.calls) == 1
    argv = ingest.calls[0].argv
    assert flag_value(argv, "--subject") == SUBJECT
    assert Path(flag_value(argv, "--domain-root")) == tree.sources_dir(SUBJECT)
    assert flag_value(argv, "--collection-name") == subject_collection_name(SUBJECT)
    assert Path(flag_value(argv, "--persist-dir")) == persist_dir
    assert str(argv[1]).endswith("ingest_corpus.py")


def test_the_embedding_configuration_reaches_the_ingest_from_the_environment(
    tree: StagingTree, config: UploadConfig, tmp_path: Path
) -> None:
    """The deployment serves ``embed``; the ingest's own default is not that.

    So the worker must carry whatever the environment says through to the
    child untouched — and must never substitute a model name of its own.
    """
    queue_upload(tree, config)
    ingest = RecordingIngest()
    worker = build_worker(
        tree,
        converter=RecordingConverter(),
        ingest=ingest,
        persist_dir=tmp_path / "chroma",
        env={
            "LLM_EMBEDDINGS_MODEL": "embed",
            "LLM_EMBEDDINGS_BASE_URL": "http://localhost:9000/v1",
            "LLM_EMBEDDINGS_API_KEY": "not-needed",
        },
    )

    worker.run_once()

    env = ingest.calls[0].env
    assert env["LLM_EMBEDDINGS_MODEL"] == "embed"
    assert env["LLM_EMBEDDINGS_BASE_URL"] == "http://localhost:9000/v1"
    assert env["LLM_EMBEDDINGS_API_KEY"] == "not-needed"
    assert "nomic-embed" not in " ".join(ingest.calls[0].argv)


def test_an_environment_collection_cannot_redirect_a_subjects_chunks(
    tmp_path: Path,
) -> None:
    """``CHROMA_COLLECTION`` in the operator's shell must not win.

    The ingest resolves its collection from that variable when no flag is
    given, which would put every subject's chunks in one collection. The
    worker passes the flag, so the subject decides.
    """
    invocation = build_invocation(
        subject="french",
        domain_root=tmp_path / "uploads" / "french" / "sources",
        persist_dir=tmp_path / "chroma",
        env={"CHROMA_COLLECTION": "gcse-english-v1"},
    )

    assert flag_value(invocation.argv, "--collection-name") == "gcse-french-v1"
    assert invocation.env["CHROMA_COLLECTION"] == "gcse-english-v1"


# ---------------------------------------------------------------------------
# Failure paths
# ---------------------------------------------------------------------------


def test_a_conversion_failure_lands_on_the_job_and_never_reaches_ingest(
    tree: StagingTree, config: UploadConfig, tmp_path: Path
) -> None:
    record = queue_upload(tree, config, filename="blank.md")
    ingest = RecordingIngest()
    worker = build_worker(
        tree,
        converter=RecordingConverter(error=ConversionError("no text in 'blank.md'")),
        ingest=ingest,
        persist_dir=tmp_path / "chroma",
    )

    worked = worker.run_once()

    assert worked[0].status is JobStatus.FAILED
    assert "no text in 'blank.md'" in (worked[0].error or "")
    assert ingest.calls == []
    assert tree.read_job(SUBJECT, record.job_id).status is JobStatus.FAILED


def test_an_ingest_failure_lands_on_the_job_with_the_reason(
    tree: StagingTree, config: UploadConfig, tmp_path: Path
) -> None:
    record = queue_upload(tree, config)
    worker = build_worker(
        tree,
        converter=RecordingConverter(),
        ingest=RecordingIngest(error=IngestFailed("ingest_corpus exited 2")),
        persist_dir=tmp_path / "chroma",
    )

    worked = worker.run_once()

    assert worked[0].status is JobStatus.FAILED
    assert "ingest_corpus exited 2" in (worked[0].error or "")
    assert tree.read_job(SUBJECT, record.job_id).error == worked[0].error


def test_one_bad_scan_does_not_stop_the_rest_of_the_pile(
    tree: StagingTree, config: UploadConfig, tmp_path: Path
) -> None:
    first = queue_upload(tree, config, filename="bad.md", now="2026-08-14T10:00:00+00:00")
    second = queue_upload(
        tree, config, filename="good.md", now="2026-08-14T11:00:00+00:00"
    )

    class FailsTheFirstFile(RecordingConverter):
        def convert(self, src: Path, dst_dir: Path) -> ConversionResult:
            if src.name == "bad.md":
                self.calls.append((src, dst_dir))
                raise ConversionError("unreadable")
            return super().convert(src, dst_dir)

    worker = build_worker(
        tree,
        converter=FailsTheFirstFile(),
        ingest=RecordingIngest(),
        persist_dir=tmp_path / "chroma",
    )

    worked = worker.run_once()

    by_id = {r.job_id: r for r in worked}
    assert by_id[first.job_id].status is JobStatus.FAILED
    assert by_id[second.job_id].status is JobStatus.INGESTED


# ---------------------------------------------------------------------------
# Restart behaviour
# ---------------------------------------------------------------------------


def test_a_job_stranded_mid_conversion_is_requeued_on_startup(
    tree: StagingTree, config: UploadConfig, tmp_path: Path
) -> None:
    record = queue_upload(tree, config)
    stranded = tree.transition(record, JobStatus.CONVERTING)
    assert stranded.status is JobStatus.CONVERTING

    worker = build_worker(
        tree,
        converter=RecordingConverter(),
        ingest=RecordingIngest(),
        persist_dir=tmp_path / "chroma",
    )
    requeued = worker.requeue_stranded()

    assert [r.job_id for r in requeued] == [record.job_id]
    assert tree.read_job(SUBJECT, record.job_id).status is JobStatus.QUEUED

    # …and the re-queued job then runs through normally.
    worked = worker.run_once()
    assert worked[0].status is JobStatus.INGESTED


def test_requeueing_is_safe_to_repeat_and_leaves_other_states_alone(
    tree: StagingTree, config: UploadConfig, tmp_path: Path
) -> None:
    queued = queue_upload(tree, config, filename="a.md")
    done = queue_upload(tree, config, filename="b.md")
    tree.transition(tree.transition(tree.transition(done, JobStatus.CONVERTING), JobStatus.STAGED), JobStatus.INGESTED)

    worker = build_worker(
        tree,
        converter=RecordingConverter(),
        ingest=RecordingIngest(),
        persist_dir=tmp_path / "chroma",
    )

    assert worker.requeue_stranded() == []
    assert worker.requeue_stranded() == []
    assert tree.read_job(SUBJECT, queued.job_id).status is JobStatus.QUEUED
    assert tree.read_job(SUBJECT, done.job_id).status is JobStatus.INGESTED


def test_a_staged_job_resumes_at_ingest_without_converting_again(
    tree: StagingTree, config: UploadConfig, tmp_path: Path
) -> None:
    """A crash between staging and ingest must not re-run the converter.

    The markdown is already on disk; converting again would write a second
    copy of it beside the first and double the subject's chunks.
    """
    record = queue_upload(tree, config)
    tree.transition(tree.transition(record, JobStatus.CONVERTING), JobStatus.STAGED)

    converter = RecordingConverter()
    ingest = RecordingIngest()
    worker = build_worker(
        tree,
        converter=converter,
        ingest=ingest,
        persist_dir=tmp_path / "chroma",
    )

    worked = worker.run_once()

    assert worked[0].status is JobStatus.INGESTED
    assert converter.calls == []
    assert len(ingest.calls) == 1


def test_run_once_returns_when_the_queue_is_empty(
    tree: StagingTree, tmp_path: Path
) -> None:
    worker = build_worker(
        tree,
        converter=RecordingConverter(),
        ingest=RecordingIngest(),
        persist_dir=tmp_path / "chroma",
    )
    assert worker.run_once() == []
    assert worker.requeue_stranded() == []


def test_the_loop_sleeps_between_passes(
    tree: StagingTree, config: UploadConfig, tmp_path: Path
) -> None:
    queue_upload(tree, config)
    slept: list[float] = []
    worker = build_worker(
        tree,
        converter=RecordingConverter(),
        ingest=RecordingIngest(),
        persist_dir=tmp_path / "chroma",
    )

    worked = worker.run_forever(
        poll_seconds=0.25, sleep=slept.append, max_passes=3
    )

    assert worked == 1  # the job is worked once; later passes find nothing
    assert slept == [0.25, 0.25]


# ---------------------------------------------------------------------------
# Converter selection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", ["notes.md", "notes.txt", "NOTES.TXT"])
def test_text_uploads_go_to_the_passthrough_converter(name: str) -> None:
    assert isinstance(select_converter(Path(name)), PassthroughConverter)


@pytest.mark.parametrize("name", ["scan.pdf", "scan.PNG", "page.jpeg", "page.tiff"])
def test_scans_go_to_the_docling_converter(name: str) -> None:
    assert isinstance(select_converter(Path(name)), DoclingConverter)


def test_an_extension_no_converter_handles_is_a_loud_failure() -> None:
    with pytest.raises(ConversionError, match="No converter handles"):
        select_converter(Path("archive.zip"))


# ---------------------------------------------------------------------------
# The ingest child, and the command line
# ---------------------------------------------------------------------------


def test_a_failing_ingest_child_raises_with_its_exit_code_and_output() -> None:
    """The operator reads this text off the job record, so it must say enough."""
    invocation = IngestInvocation(
        subject=SUBJECT,
        argv=(
            sys.executable,
            "-c",
            "import sys; sys.stderr.write('corpus root missing\\n'); sys.exit(2)",
        ),
        env={},
    )

    with pytest.raises(IngestFailed) as excinfo:
        run_ingest_subprocess(invocation)

    assert "exited 2" in str(excinfo.value)
    assert "corpus root missing" in str(excinfo.value)


def test_a_successful_ingest_child_forwards_its_ndjson(
    capsys: pytest.CaptureFixture[str],
) -> None:
    invocation = IngestInvocation(
        subject=SUBJECT,
        argv=(sys.executable, "-c", "print('{\"event\": \"ingest_summary\"}')"),
        env={},
    )

    run_ingest_subprocess(invocation)

    assert "ingest_summary" in capsys.readouterr().out


def test_main_works_the_queue_once_and_exits(
    tree: StagingTree, config: UploadConfig, staging_root: Path, tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    record = queue_upload(tree, config)
    calls: list[IngestInvocation] = []
    monkeypatch.setattr(process_uploads, "run_ingest_subprocess", calls.append)
    monkeypatch.setattr(
        process_uploads, "select_converter", lambda src: RecordingConverter()
    )

    exit_code = process_uploads.main(
        [
            "--once",
            "--staging-root",
            str(staging_root),
            "--persist-dir",
            str(tmp_path / "chroma"),
        ]
    )

    assert exit_code == 0
    assert len(calls) == 1
    assert tree.read_job(SUBJECT, record.job_id).status is JobStatus.INGESTED


def test_main_on_an_empty_tree_does_nothing_and_succeeds(
    staging_root: Path, tmp_path: Path
) -> None:
    assert (
        process_uploads.main(
            [
                "--once",
                "--staging-root",
                str(staging_root),
                "--persist-dir",
                str(tmp_path / "chroma"),
            ]
        )
        == 0
    )
    assert not staging_root.exists()


# ---------------------------------------------------------------------------
# The seam the spec asks to verify, not assume
# ---------------------------------------------------------------------------


class _StubEmbeddingFunction:
    """A deterministic, offline stand-in for the OpenAI embedding function."""

    def __init__(self) -> None:
        pass

    def __call__(self, input: Sequence[str]) -> list[list[float]]:  # noqa: A002
        return [[float(len(text) % 11), 1.0, 2.0] for text in input]

    @staticmethod
    def name() -> str:
        return "stub-upload-worker"

    def get_config(self) -> dict[str, Any]:
        return {}

    @staticmethod
    def build_from_config(config: dict[str, Any]) -> "_StubEmbeddingFunction":
        return _StubEmbeddingFunction()


def test_the_workers_ingest_command_lands_a_subject_where_the_runtime_reads_it(
    tree: StagingTree,
    config: UploadConfig,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The C-stage verification: sidecar location and subject discovery.

    Runs the REAL ``scripts/ingest_corpus.py`` — with a stub embedding
    function and a temporary persist directory, so nothing touches the network
    or the repo's baked ``data/chroma`` — using exactly the command line the
    worker builds, and then checks the two things the build spec says to verify
    rather than assume:

    1. the per-subject sidecar is written where ``rag_wiring`` reads it;
    2. the resulting collection is one ``rag_wiring``'s subject discovery finds.
    """
    chromadb = pytest.importorskip("chromadb")
    from scripts import ingest_corpus
    from study_tutor.cli import rag_wiring
    from study_tutor.knowledge.retrieval import (
        clear_primary_text_index,
        has_primary_text,
    )

    monkeypatch.setattr(
        ingest_corpus, "_make_embedding_function", lambda: _StubEmbeddingFunction()
    )
    persist_dir = tmp_path / "chroma"

    def run_ingest_in_process(invocation: IngestInvocation) -> None:
        assert ingest_corpus.main(list(invocation.argv[2:])) == 0

    queue_upload(
        tree,
        config,
        filename="tudor_rebellions.md",
        data=FIXTURE_PARAGRAPHS.encode("utf-8"),
    )
    worker = UploadWorker(
        tree,
        persist_dir=persist_dir,
        env={},
        run_ingest=run_ingest_in_process,
        choose_converter=select_converter,
    )

    clear_primary_text_index()
    try:
        worked = worker.run_once()
        assert worked[0].status is JobStatus.INGESTED, worked[0].error

        # 1. The sidecar: written by the script, read by the wiring.
        sidecar = persist_dir / rag_wiring.subject_sidecar_filename(SUBJECT)
        assert sidecar.is_file(), sorted(p.name for p in persist_dir.iterdir())
        assert sidecar.read_text(encoding="utf-8").split() == ["tudor_rebellions"]

        clear_primary_text_index()
        replayed = rag_wiring._replay_primary_text_index(persist_dir, SUBJECT)
        assert replayed == 1
        assert has_primary_text("tudor_rebellions", SUBJECT)

        # 2. The collection: named the way subject discovery parses.
        client = chromadb.PersistentClient(path=str(persist_dir))
        names = [str(getattr(c, "name", c)) for c in client.list_collections()]
        expected = subject_collection_name(SUBJECT)
        assert expected in names
        match = rag_wiring.SUBJECT_COLLECTION_PATTERN.match(expected)
        assert match is not None and match.group("subject") == SUBJECT

        collection = client.get_or_create_collection(
            name=expected, embedding_function=_StubEmbeddingFunction()
        )
        assert collection.count() > 0
    finally:
        clear_primary_text_index()
