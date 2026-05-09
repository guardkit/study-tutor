#!/usr/bin/env python3
"""One-shot bridge: reconstruct study-tutor secondary_study_guide .md files
from agentic-dataset-factory's chroma_data_backup.

Throwaway script for smoke-testing TASK-RAG-CC1 against real Mr Bruff content
without re-running docling on the GB10. The 7 source PDFs were processed by
docling on the GB10; their extracted text lives in
``agentic-dataset-factory/chroma_data_backup/chroma.sqlite3`` as already-chunked
records (3,850 chunks across 6 ingestible PDFs + 1 practice-paper PDF skipped).

Reconstruction:
    1. For each source PDF, gather chunks (page_number, chunk_index, document text)
    2. Sort by (page_number, chunk_index)
    3. Concatenate with double-newline separators
    4. Write to domains/gcse-english/sources/secondary_study_guide/<slug>.md

Re-embedding is automatic when ``scripts/ingest_corpus.py`` runs: it embeds via
``nomic-embed-text`` (768 dim) over llama-swap per DECISION-RAG-001, regardless
of whatever model ADF originally used.

Why this is a deviation from the canonical review:
The canonical review (REVIEW-RAG-COURSE-CORRECT-docling-integration.md) preferred
re-running docling on the source PDFs on the GB10. That assumed GB10 access at
smoke time. This script lets us smoke from the Mac using content already
on-disk. Resulting .md files will be plain-text-ish (chunk-per-paragraph
concatenation) rather than docling's structured markdown — but the loader's
chunker is plain-text-oriented anyway, so retrieval signals are unaffected.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ADF_CHROMA_DB = Path(
    "/Users/richardwoollcott/Projects/appmilla_github/"
    "agentic-dataset-factory/chroma_data_backup/chroma.sqlite3"
)

REPO_ROOT = Path(__file__).resolve().parent.parent
TARGET_DIR = REPO_ROOT / "domains/gcse-english/sources/secondary_study_guide"

# Per the canonical review's task-sequencing table. All 6 ingestible files
# go to secondary_study_guide/. Practice-paper PDF is skipped (AQA-adjacent).
SOURCE_TO_SLUG: dict[str, str] = {
    "Lang-Guide-4th-edition-Sept-2025-5fgv5j.pdf": "lang-guide.md",
    "Literature-Guide-June-21st-2025-ebook-9dkdzh.pdf": "literature-guide.md",
    "Macbeth203rd20edition-hvhcex.pdf": "mr-bruff-macbeth.md",
    "Mr-Bruffs-Guide-to-An-Inspector-Calls-2nd-edition.pdf": "mr-bruff-inspector-calls.md",
    "Mr-Bruffs-Guide-to-Christmas-Carol-Feb2022-xx7wta.pdf": "mr-bruff-christmas-carol.md",
    "Power-and-Conflict-Guide-2nd--wsazur.pdf": "mr-bruff-power-and-conflict.md",
}

# Pulls every metadata field for a single source_file in one query, so we
# don't round-trip the database 600+ times per file.
_QUERY = """
SELECT em_page.int_value AS page,
       em_chunk.int_value AS chunk_idx,
       em_doc.string_value AS document
FROM embedding_metadata em_src
JOIN embedding_metadata em_page  ON em_src.id = em_page.id  AND em_page.key  = 'page_number'
JOIN embedding_metadata em_chunk ON em_src.id = em_chunk.id AND em_chunk.key = 'chunk_index'
JOIN embedding_metadata em_doc   ON em_src.id = em_doc.id   AND em_doc.key   = 'chroma:document'
WHERE em_src.key = 'source_file' AND em_src.string_value = ?
ORDER BY em_page.int_value, em_chunk.int_value
"""


def reconstruct_one(cur: sqlite3.Cursor, source_pdf: str, target_path: Path) -> int:
    """Pull all chunks for ``source_pdf``, write them as a single .md.

    Returns the number of chunks written.
    """
    cur.execute(_QUERY, (source_pdf,))
    rows = cur.fetchall()
    if not rows:
        raise RuntimeError(f"No chunks found in chroma_data_backup for {source_pdf!r}")

    # Double-newline between chunks gives the loader's chunker meaningful
    # paragraph boundaries — its rfind('\n\n') step prefers paragraph
    # breaks for chunk edges.
    body = "\n\n".join(row[2] for row in rows if row[2])
    target_path.write_text(body, encoding="utf-8")
    return len(rows)


def main() -> int:
    if not ADF_CHROMA_DB.is_file():
        print(f"error: ADF chroma DB not found at {ADF_CHROMA_DB}", file=sys.stderr)
        return 1
    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(f"file:{ADF_CHROMA_DB}?mode=ro", uri=True)
    try:
        cur = conn.cursor()
        total_chunks = 0
        for source_pdf, slug in SOURCE_TO_SLUG.items():
            target = TARGET_DIR / slug
            count = reconstruct_one(cur, source_pdf, target)
            total_chunks += count
            print(f"  {source_pdf} -> {target.relative_to(REPO_ROOT)} ({count} chunks)")
        print(f"\nWrote {len(SOURCE_TO_SLUG)} files, {total_chunks} chunks total to "
              f"{TARGET_DIR.relative_to(REPO_ROOT)}/")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
