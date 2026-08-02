"""ADR-ARCH-032 D5 — the ingest script's --subject derivation.

Hermetic (no chromadb): ``scripts.ingest_corpus`` imports chroma lazily
inside ``main``, so the naming helpers are importable on the dev path.
"""

from pathlib import Path

from scripts import ingest_corpus
from study_tutor.cli.rag_wiring import (
    subject_collection_name,
    subject_sidecar_filename,
)
from study_tutor.knowledge.retrieval import (
    clear_primary_text_index,
    has_primary_text,
)


def test_sidecar_filename_matches_the_wiring_readers_expectation() -> None:
    """The script's writer and the wiring's reader must agree per subject."""
    for subject in ("english", "french", "chemistry"):
        assert ingest_corpus._sidecar_filename(subject) == subject_sidecar_filename(
            subject
        )
    # English keeps the legacy unsuffixed name (baked stores predate scoping).
    assert ingest_corpus._sidecar_filename("english") == ".primary_text_index"
    assert (
        ingest_corpus._sidecar_filename("french") == ".primary_text_index.french"
    )


def test_default_names_parse_under_the_discovery_scheme() -> None:
    """The grandfathered english defaults ARE the scheme's english values."""
    assert ingest_corpus.DEFAULT_COLLECTION_NAME == subject_collection_name("english")
    assert ingest_corpus.DEFAULT_DOMAIN_ROOT == Path("domains/gcse-english/sources")


def test_register_primary_texts_writes_subject_sidecar_and_registry(
    tmp_path: Path,
) -> None:
    clear_primary_text_index()
    try:
        sidecar = ingest_corpus._register_primary_texts(
            tmp_path, ["candide"], "french"
        )
        assert sidecar == tmp_path / ".primary_text_index.french"
        assert sidecar.read_text(encoding="utf-8") == "candide\n"
        assert has_primary_text("candide", "french")
        assert not has_primary_text("candide")  # not english's registry
    finally:
        clear_primary_text_index()


def test_register_primary_texts_default_subject_keeps_legacy_sidecar(
    tmp_path: Path,
) -> None:
    clear_primary_text_index()
    try:
        sidecar = ingest_corpus._register_primary_texts(tmp_path, ["macbeth"])
        assert sidecar == tmp_path / ".primary_text_index"
        assert has_primary_text("macbeth")
    finally:
        clear_primary_text_index()
