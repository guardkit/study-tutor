"""Pydantic models describing source-typed corpus chunks and their citation anchors.

These models are the foundation for the primary-text-RAG-and-quote-verifier
pipeline (FEAT-PRV4 / FEAT-PH1-004): every other subtask in the wave consumes
``SourceType``, ``CitationAnchor`` (the discriminated union), and
``CorpusChunk`` from this module.

The module is intentionally stack-agnostic:
  * No imports from the Postgres ``StudentStore`` (the student-model backend).
  * No imports from ``chromadb`` (the vector store used for retrieval).
  * No file I/O — corpus loading is the responsibility of TASK-PRV-002.
  * No business logic — retrieval / filtering / ranking lives downstream.

Discriminated union vs. single Optional-fields model
----------------------------------------------------
``CitationAnchor`` is a Pydantic v2 discriminated union of
``PlayCitationAnchor`` and ``NovelCitationAnchor`` rather than a single class
with optional ``act``/``scene``/``line`` and ``chapter``/``paragraph`` fields.
That gives us static exhaustiveness: adding a new citation kind (poetry, etc.)
is a type-system change rather than a runtime guess about which fields apply.
The verifier (TASK-PRV-005) uses ``isinstance(anchor, PlayCitationAnchor)``
rather than ``anchor.act is not None``, which is much harder to misuse.

Module location rationale
-------------------------
These models live in ``corpus_models.py`` (not ``corpus.py``) so the verifier
in TASK-PRV-005 can consume them without transitively importing the loader's
ChromaDB dependency. Keeping the data contract in a dedicated module preserves
that separation.
"""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, ConfigDict, Field


class SourceType(str, Enum):
    """Classification of a corpus chunk by its provenance.

    Values intentionally mirror the on-disk folder layout the loader
    (TASK-PRV-002) walks: each leaf folder corresponds to exactly one
    ``SourceType`` value, so the loader can infer the type from the path.

    The four values:
      * ``PRIMARY_TEXT`` — the literary work itself (e.g. *Macbeth* play text,
        *An Inspector Calls* script). Only chunks of this type carry a
        :class:`CitationAnchor`; secondary / contextual sources do not.
      * ``SECONDARY_STUDY_GUIDE`` — study guides, revision notes, and other
        teaching material *about* the primary text.
      * ``SECONDARY_CRITICAL`` — critical / scholarly essays and analyses.
      * ``CONTEXT_HISTORICAL`` — historical / cultural background that
        contextualises the primary text but is not directly about it.
    """

    PRIMARY_TEXT = "PRIMARY_TEXT"
    SECONDARY_STUDY_GUIDE = "SECONDARY_STUDY_GUIDE"
    SECONDARY_CRITICAL = "SECONDARY_CRITICAL"
    CONTEXT_HISTORICAL = "CONTEXT_HISTORICAL"


class PlayCitationAnchor(BaseModel):
    """Citation anchor for a chunk drawn from a play (Act / Scene / Line).

    The ``kind`` literal is the discriminator used by :data:`CitationAnchor`.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["play"] = "play"
    act: int
    scene: int
    line: int


class NovelCitationAnchor(BaseModel):
    """Citation anchor for a chunk drawn from a novel (Chapter / Paragraph).

    The ``kind`` literal is the discriminator used by :data:`CitationAnchor`.
    """

    model_config = ConfigDict(extra="forbid")

    kind: Literal["novel"] = "novel"
    chapter: int
    paragraph: int


# Pydantic v2 discriminated union. The ``kind`` field on each member acts as
# the tag — ``{"kind": "play", ...}`` parses to ``PlayCitationAnchor`` and
# ``{"kind": "novel", ...}`` parses to ``NovelCitationAnchor``. Any other
# ``kind`` value (or a missing one) raises ``ValidationError`` at parse time.
CitationAnchor = Annotated[
    Union[PlayCitationAnchor, NovelCitationAnchor],
    Field(discriminator="kind"),
]


class CorpusChunk(BaseModel):
    """A single retrievable chunk of source material.

    A ``CorpusChunk`` is what the loader (TASK-PRV-002) emits and what the
    retrieval / verifier pipeline (TASK-PRV-003 .. TASK-PRV-005) consumes.

    Field semantics:
      * ``text``: the chunk's natural-language content (already segmented).
      * ``source_type``: provenance — see :class:`SourceType`.
      * ``source_path``: the on-disk path the chunk was loaded from. The
        loader writes this; downstream code uses it for citation display.
      * ``text_name``: human-readable name of the work the chunk belongs to
        (e.g. ``"Macbeth"``). Constrained to a non-empty string so retrieval
        always has something to render in citations.
      * ``citation_anchor``: structured location within the work. Only
        ``PRIMARY_TEXT`` chunks carry one; secondary / context chunks set this
        to ``None``. Defaulting to ``None`` keeps non-primary loaders simple.
      * ``chunk_index``: the chunk's position within its source file, used
        for stable ordering when the same source is re-emitted.
    """

    # ``extra="forbid"`` mirrors the strictness of the episode contract in
    # ``episodes.py``: the data shape is part of the public API of this module,
    # so silently dropping unknown fields is undesirable.
    model_config = ConfigDict(extra="forbid")

    text: str
    source_type: SourceType
    source_path: str
    text_name: str = Field(min_length=1)
    citation_anchor: CitationAnchor | None = None
    chunk_index: int


__all__ = [
    "SourceType",
    "PlayCitationAnchor",
    "NovelCitationAnchor",
    "CitationAnchor",
    "CorpusChunk",
]
