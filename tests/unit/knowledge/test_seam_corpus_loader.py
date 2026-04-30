"""Seam test: verify the corpus loader emits CorpusChunk records carrying a
correctly-typed CitationAnchor union member per the SourceTypedCorpus contract.

Producer: TASK-PRV-002 (``load_corpus`` in ``corpus.py``)
Consumer: TASK-PRV-005 (the verifier consumes ``chunk.citation_anchor``
via ``isinstance`` checks against the union members)

Backfilled by TASK-FIX-AB7A-002. The original PRV-002 task stubbed this
test in its spec but the Player did not implement it, and the
``parallel_contention + all_gates_passed`` conditional approval rule
masked the gap. This file is the explicit gate that closes that hole:
if it fails locally, the conditionally-approved PRV-002 implementation
has a real contract bug and a code fix is required before the autobuild
can resume on FEAT-70A4 wave 3.

The fixture is hermetic: it writes a small Standard-Ebooks-style play
text under ``tmp_path / "primary_text" / "macbeth.txt"`` and asserts on
the loader's in-memory output. No real corpus, no network, no env-
dependent paths.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from study_tutor.knowledge.corpus import load_corpus
from study_tutor.knowledge.corpus_models import (
    CorpusChunk,
    NovelCitationAnchor,
    PlayCitationAnchor,
    SourceType,
)


# Standard-Ebooks-style play text. The leading ``ACT I`` / ``SCENE 1``
# markers are what the loader's anchor inferer keys off; the rest is
# enough body to give the chunker something to emit.
_MACBETH_FIXTURE = """\
ACT I

SCENE 1

A desert place. Thunder and lightning.

Enter three Witches.

First Witch
When shall we three meet again
In thunder, lightning, or in rain?

Second Witch
When the hurlyburly's done,
When the battle's lost and won.

Third Witch
That will be ere the set of sun.

First Witch
Where the place?

Second Witch
Upon the heath.

Third Witch
There to meet with Macbeth.
"""


@pytest.mark.seam
@pytest.mark.integration_contract("SourceTypedCorpus")
def test_corpus_chunk_carries_typed_citation_anchor(tmp_path: Path) -> None:
    """Loader emits primary-text play chunks with PlayCitationAnchor.

    Contract under test:
      * ``load_corpus`` returns at least one ``CorpusChunk`` for the play.
      * Every ``PRIMARY_TEXT`` chunk drawn from the play file has a
        non-None ``citation_anchor``.
      * That anchor is the discriminated-union member ``PlayCitationAnchor``
        — not a plain dict, not ``NovelCitationAnchor``.

    Why this matters: the verifier (TASK-PRV-005) downstream relies on
    ``isinstance(anchor, PlayCitationAnchor)`` rather than field-presence
    checks. If the loader is silently emitting plain dicts (or the wrong
    union member) this test fails — and that downstream pattern would be
    silently broken in production.
    """
    primary_dir = tmp_path / "primary_text"
    primary_dir.mkdir()
    (primary_dir / "macbeth.txt").write_text(_MACBETH_FIXTURE, encoding="utf-8")

    result = load_corpus(tmp_path)

    primary_play_chunks = [
        chunk
        for chunk in result.chunks
        if chunk.source_type is SourceType.PRIMARY_TEXT
        and chunk.text_name == "macbeth"
    ]

    assert primary_play_chunks, (
        "expected at least one primary-text chunk for the macbeth fixture; "
        f"got {len(result.chunks)} total chunks, "
        f"{len(result.skips)} skips, {len(result.refusals)} refusals"
    )
    for chunk in primary_play_chunks:
        assert isinstance(chunk, CorpusChunk)
        assert chunk.citation_anchor is not None, (
            f"primary-text play chunk {chunk.chunk_index} at "
            f"{chunk.source_path} has no citation_anchor; "
            "the loader must infer act/scene/line for play fixtures."
        )
        assert isinstance(chunk.citation_anchor, PlayCitationAnchor), (
            "primary-text play chunk citation_anchor must be a "
            f"PlayCitationAnchor (got "
            f"{type(chunk.citation_anchor).__name__})."
        )
        # Negative-discriminator assertion: the union's other member must
        # not match. This guards against a future regression where the
        # discriminator on the model is loosened or both branches are
        # accidentally accepted by the loader.
        assert not isinstance(chunk.citation_anchor, NovelCitationAnchor)
        # The fixture leads with ACT I / SCENE 1, so the anchor values
        # should reflect that. ``line`` depends on which content line of
        # the scene the chunk's start offset lands in, so we only assert
        # it is a positive int rather than pinning an exact value.
        assert chunk.citation_anchor.act == 1
        assert chunk.citation_anchor.scene == 1
        assert chunk.citation_anchor.line >= 1
