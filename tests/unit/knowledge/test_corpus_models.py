"""Unit tests for source-typed corpus chunk models.

Covers AC-001..AC-005 of TASK-PRV-001:
  * AC-001: ``SourceType`` enum exposes all four values.
  * AC-002: ``CitationAnchor`` discriminated union dispatches on ``kind``.
  * AC-003: ``CorpusChunk`` accepts ``citation_anchor=None`` and rejects
    unknown ``source_type`` values.
  * AC-004: ``text_name`` is a non-empty string.
  * AC-005: Module imports cleanly with no Graphiti / ChromaDB / file-I/O
    dependencies.
"""

from __future__ import annotations

import ast
import inspect

import pytest
from pydantic import TypeAdapter, ValidationError

from study_tutor.knowledge import corpus_models as corpus_models_module
from study_tutor.knowledge.corpus_models import (
    CitationAnchor,
    CorpusChunk,
    NovelCitationAnchor,
    PlayCitationAnchor,
    SourceType,
)


# ---------------------------------------------------------------------------
# AC-001: SourceType enum membership
# ---------------------------------------------------------------------------


def test_source_type_exposes_all_four_values() -> None:
    """All four filesystem-aligned source types must be enum members."""
    assert {s.value for s in SourceType} == {
        "PRIMARY_TEXT",
        "SECONDARY_STUDY_GUIDE",
        "SECONDARY_CRITICAL",
        "CONTEXT_HISTORICAL",
    }


def test_source_type_is_str_enum() -> None:
    """``SourceType`` is a ``str``-subclass enum so JSON serialisation is trivial."""
    assert issubclass(SourceType, str)
    assert SourceType.PRIMARY_TEXT == "PRIMARY_TEXT"


# ---------------------------------------------------------------------------
# AC-002: CitationAnchor discriminated union dispatch
# ---------------------------------------------------------------------------


@pytest.fixture()
def anchor_adapter() -> TypeAdapter[CitationAnchor]:
    """A ``TypeAdapter`` is the canonical way to validate a non-class type alias."""
    return TypeAdapter(CitationAnchor)


def test_play_citation_anchor_round_trips() -> None:
    payload = {"kind": "play", "act": 5, "scene": 1, "line": 35}
    anchor = PlayCitationAnchor.model_validate(payload)
    assert anchor.act == 5
    assert anchor.scene == 1
    assert anchor.line == 35
    assert anchor.model_dump() == payload


def test_novel_citation_anchor_round_trips() -> None:
    payload = {"kind": "novel", "chapter": 3, "paragraph": 7}
    anchor = NovelCitationAnchor.model_validate(payload)
    assert anchor.chapter == 3
    assert anchor.paragraph == 7
    assert anchor.model_dump() == payload


def test_citation_anchor_dispatches_play(
    anchor_adapter: TypeAdapter[CitationAnchor],
) -> None:
    parsed = anchor_adapter.validate_python(
        {"kind": "play", "act": 5, "scene": 1, "line": 35},
    )
    assert isinstance(parsed, PlayCitationAnchor)


def test_citation_anchor_dispatches_novel(
    anchor_adapter: TypeAdapter[CitationAnchor],
) -> None:
    parsed = anchor_adapter.validate_python(
        {"kind": "novel", "chapter": 3, "paragraph": 7},
    )
    assert isinstance(parsed, NovelCitationAnchor)


def test_citation_anchor_rejects_unknown_kind(
    anchor_adapter: TypeAdapter[CitationAnchor],
) -> None:
    with pytest.raises(ValidationError):
        anchor_adapter.validate_python(
            {"kind": "poetry", "stanza": 1, "line": 1},
        )


def test_citation_anchor_rejects_missing_kind(
    anchor_adapter: TypeAdapter[CitationAnchor],
) -> None:
    with pytest.raises(ValidationError):
        anchor_adapter.validate_python({"act": 1, "scene": 1, "line": 1})


# ---------------------------------------------------------------------------
# AC-003: CorpusChunk validation
# ---------------------------------------------------------------------------


def _primary_chunk_payload() -> dict:
    return dict(
        text="Is this a dagger which I see before me?",
        source_type=SourceType.PRIMARY_TEXT,
        source_path="/corpus/primary/macbeth/act-2.txt",
        text_name="Macbeth",
        citation_anchor=PlayCitationAnchor(act=2, scene=1, line=33),
        chunk_index=12,
    )


def _secondary_chunk_payload() -> dict:
    return dict(
        text="Macbeth's ambition is the engine of the tragedy.",
        source_type=SourceType.SECONDARY_STUDY_GUIDE,
        source_path="/corpus/secondary/study-guides/macbeth-themes.md",
        text_name="Macbeth Study Guide",
        citation_anchor=None,
        chunk_index=3,
    )


def test_corpus_chunk_accepts_primary_with_anchor() -> None:
    chunk = CorpusChunk(**_primary_chunk_payload())
    assert chunk.source_type is SourceType.PRIMARY_TEXT
    assert isinstance(chunk.citation_anchor, PlayCitationAnchor)
    assert chunk.citation_anchor.act == 2


def test_corpus_chunk_accepts_secondary_without_anchor() -> None:
    chunk = CorpusChunk(**_secondary_chunk_payload())
    assert chunk.source_type is SourceType.SECONDARY_STUDY_GUIDE
    assert chunk.citation_anchor is None


def test_corpus_chunk_citation_anchor_defaults_to_none() -> None:
    """Omitting ``citation_anchor`` entirely is permitted (defaults to ``None``)."""
    payload = _secondary_chunk_payload()
    payload.pop("citation_anchor")
    chunk = CorpusChunk(**payload)
    assert chunk.citation_anchor is None


def test_corpus_chunk_rejects_unknown_source_type() -> None:
    payload = _secondary_chunk_payload()
    payload["source_type"] = "OTHER_THING"
    with pytest.raises(ValidationError):
        CorpusChunk(**payload)


def test_corpus_chunk_round_trips_through_model_dump_and_validate() -> None:
    """A primary chunk must survive ``model_dump()`` → ``model_validate()``."""
    original = CorpusChunk(**_primary_chunk_payload())
    rehydrated = CorpusChunk.model_validate(original.model_dump())
    assert rehydrated == original
    assert isinstance(rehydrated.citation_anchor, PlayCitationAnchor)


# ---------------------------------------------------------------------------
# AC-004: text_name non-empty constraint
# ---------------------------------------------------------------------------


def test_corpus_chunk_rejects_empty_text_name() -> None:
    payload = _secondary_chunk_payload()
    payload["text_name"] = ""
    with pytest.raises(ValidationError):
        CorpusChunk(**payload)


# ---------------------------------------------------------------------------
# AC-005: stack-agnostic import surface
# ---------------------------------------------------------------------------


def _imported_module_roots(source: str) -> set[str]:
    """Return the top-level module names actually imported by ``source``.

    Walks the AST so we only inspect ``import`` / ``from ... import`` statements
    — words that appear in docstrings or comments are correctly ignored.
    """
    tree = ast.parse(source)
    roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None and node.level == 0:
                roots.add(node.module.split(".")[0])
    return roots


def test_corpus_models_module_does_not_import_graphiti_chromadb_or_io() -> None:
    """Source must not pull in graph / vector-store / file-I/O dependencies.

    Inspecting the AST rather than ``sys.modules`` avoids false positives
    from other test modules that legitimately import these libraries, and
    inspecting imports rather than the raw source text avoids matching
    docstring or comment mentions of the forbidden module names.
    """
    source = inspect.getsource(corpus_models_module)
    imports = _imported_module_roots(source)
    forbidden = {"graphiti_core", "graphiti", "chromadb", "os", "pathlib", "io"}
    leaked = imports & forbidden
    assert not leaked, f"corpus_models imports forbidden modules: {leaked}"
