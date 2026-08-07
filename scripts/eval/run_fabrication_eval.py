#!/usr/bin/env python3
"""Golden-quote fabrication eval — the S2 measurement harness (Lane 2 step 3).

Measures the ADR-ARCH-022 D1 gate: **fabrication rate < 5% Phase A /
< 1% Phase B** on the golden-quote set (``scripts/eval/golden_quotes.jsonl``),
plus citation coverage and a false-correction scaffold. The bars are frozen
in ``docs/runbooks/RUNBOOK-golden-quote-fabrication-eval.md`` — pre-registered
BEFORE any measured run.

This harness exercises THIS repo's runtime closure (``_build_coach_handover``
→ retrieval → ``apply_quote_verification``) as a per-ingest / per-model
regression gate. It is deliberately NOT part of the fleet-evals judging
estate (model-vs-model) and NOT a qa/gates black-box probe.

Tiers
-----
* **T1 (hermetic, CI-safe)** — fake in-memory collection provider wired via
  ``retrieval.set_collection_provider`` + an ImportError reranker factory
  (the ``tests/integration/test_cli_rag_wiring.py`` pattern). The fake
  corpus is built from the golden set itself (one anchorless PRIMARY_TEXT
  chunk per item, mirroring the shipped 2026-05-10 store's 581/581
  anchorless reality). No network, no model server.
* **T2 (in-process vs the REAL baked store + REAL embedder)** — env pins
  ``LLM_EMBEDDINGS_MODEL=embed``, ``LLM_EMBEDDINGS_BASE_URL=http://localhost:9000/v1``,
  ``HF_HOME=/opt/study-tutor/hf-cache``, ``HF_HUB_OFFLINE=1``; wiring via
  ``build_rag_providers(load_role('tutor'))``; verification through the
  production closure. Store access is READ-ONLY in intent: only
  ``get_or_create_collection`` (existing name) + ``query`` are issued, and
  the fabrication-metric corpus is read via sqlite ``immutable=1``.

Modes
-----
Default is **verify-only**: Player responses are SUPPLIED via ``--responses``
(JSONL of ``{"id": ..., "response": ...}``), so the harness is usable
without any generation. ``--generate`` optionally produces responses by
POSTing ``:9000/v1/chat/completions`` (model ``gemma4-tutor``) with the
tutor system prompt (``roles/tutor/prompts/player.md`` minus its leading
HTML comment).

Metrics (per the pinned spec, rag-grounding-design.md §4)
---------------------------------------------------------
* **Fabrication rate** — extracted quoted strings with no >= 95% fuzzy
  match against the session text's corpus chunks / total extracted quoted
  strings. THE target metric.
* **Citation coverage** — post-verifier: verified matches
  (primary + fuzzy) carrying a citation anchor / all verified matches.
  Computed from the additive ``anchorless_*`` VerifierMetadata counters.
* **False-correction scaffold** — flags verifier rewrites (fuzzy
  corrections and no-match strips) whose ORIGINAL span had a >= 95% match
  somewhere in the corpus (any text). Honest limits: it can only see
  editions that are IN the corpus — a correct quote from an edition absent
  from the store (e.g. Folger wording lost by the 2026-05-10 docling-VLM
  ingest) is invisible to it and will be scored fabricated.

Fuzzy metric (documented precisely — rapidfuzz is NOT a project
dependency, so this is a stdlib implementation):
  For a normalised quote ``q`` of ``n`` words and a normalised chunk, the
  harness slides word windows of size ``n-2 .. n+2`` over the chunk and
  computes ``difflib.SequenceMatcher(None, q, window).ratio()`` — i.e.
  ``2*M / T`` where ``M`` is the number of matching characters and ``T``
  the total characters of both strings. A quote matches when its best
  ratio across all windows of all chunks is >= 0.95 (exact normalised
  substring short-circuits to 1.0). Normalisation: '/' (the verse
  linebreak convention) -> space, curly quotes -> straight, whitespace
  runs collapsed, surrounding punctuation stripped, lower-cased.

Quote extraction is INDEPENDENT of the runtime extractor (per the spec —
the runtime extractor handles only double quotes): double straight quotes,
double curly quotes, AND markdown block-quote lines (``> ...``), with the
'/' linebreak convention preserved inside spans.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT / "src") not in sys.path:  # script-mode imports
    sys.path.insert(0, str(REPO_ROOT / "src"))
    sys.path.insert(0, str(REPO_ROOT))

GOLDEN_PATH_DEFAULT = REPO_ROOT / "scripts" / "eval" / "golden_quotes.jsonl"
PLAYER_PROMPT_PATH = REPO_ROOT / "roles" / "tutor" / "prompts" / "player.md"

#: Frozen bars (pre-registered in the runbook BEFORE any measured run).
PHASE_A_BAR = 0.05
PHASE_B_BAR = 0.01

#: Fuzzy-match threshold (spec: rapidfuzz partial_ratio >= 95 — implemented
#: as windowed SequenceMatcher ratio >= 0.95, see module docstring).
MATCH_THRESHOLD = 0.95

#: Spans below this many words are not treated as quotes (mirrors the
#: runtime verifier's MIN_QUOTE_WORDS=4, defined independently here so the
#: harness never imports the runtime extractor).
EVAL_MIN_QUOTE_WORDS = 4

#: The three corpus text slugs the golden set may reference.
KNOWN_TEXT_NAMES = ("an_inspector_calls", "macbeth", "power_and_conflict_poems")

#: Golden-set schema: required fields, allowed categories.
REQUIRED_FIELDS = (
    "id",
    "text_name",
    "prompt",
    "expected_exact",
    "canonical_citation",
    "category",
    "source_check",
)
ALLOWED_CATEGORIES = (
    "recall",
    "control",
    "fabrication_bait",
    "store_gap",
    "edition_variant",
)

# T2 env pins (the pin file §5; outside docker-compose the embedding-function
# module defaults are WRONG for the 1024-dim baked store).
T2_ENV_PINS = {
    "LLM_EMBEDDINGS_MODEL": "embed",
    "LLM_EMBEDDINGS_BASE_URL": "http://localhost:9000/v1",
    "HF_HOME": "/opt/study-tutor/hf-cache",
    "HF_HUB_OFFLINE": "1",
}


# ---------------------------------------------------------------------------
# Golden-set loading + schema validation
# ---------------------------------------------------------------------------


def validate_golden_item(item: dict[str, Any]) -> list[str]:
    """Return a list of schema problems for one golden item (empty = valid)."""
    problems: list[str] = []
    for fld in REQUIRED_FIELDS:
        if not item.get(fld):
            problems.append(f"missing/empty field {fld!r}")
    if item.get("text_name") not in KNOWN_TEXT_NAMES:
        problems.append(
            f"text_name {item.get('text_name')!r} not a corpus slug "
            f"{KNOWN_TEXT_NAMES}"
        )
    if item.get("category") not in ALLOWED_CATEGORIES:
        problems.append(f"category {item.get('category')!r} not allowed")
    expected = item.get("expected_exact", "")
    if len(normalise_for_match(expected).split()) < EVAL_MIN_QUOTE_WORDS:
        problems.append(
            f"expected_exact below {EVAL_MIN_QUOTE_WORDS} words: {expected!r}"
        )
    kf = item.get("known_fabrications")
    if kf is not None and (
        not isinstance(kf, list) or not all(isinstance(s, str) for s in kf)
    ):
        problems.append("known_fabrications must be a list of strings")
    # Law 4 — never AQA assessment material in a golden set.
    haystack = " ".join(
        str(item.get(f, "")) for f in ("prompt", "expected_exact")
    ).lower()
    for banned in ("mark scheme", "past paper", "8700", "8702", "insert"):
        if banned in haystack:
            problems.append(f"AQA assessment-material marker {banned!r}")
    return problems


def load_golden(path: Path) -> list[dict[str, Any]]:
    """Load + validate the golden set; raise ValueError on any schema problem."""
    items: list[dict[str, Any]] = []
    problems: list[str] = []
    seen: set[str] = set()
    for lineno, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        line = line.strip()
        if not line:
            continue
        item = json.loads(line)
        for p in validate_golden_item(item):
            problems.append(f"line {lineno} ({item.get('id')}): {p}")
        if item.get("id") in seen:
            problems.append(f"line {lineno}: duplicate id {item.get('id')!r}")
        seen.add(item.get("id"))
        items.append(item)
    if problems:
        raise ValueError("golden set schema problems:\n" + "\n".join(problems))
    return items


# ---------------------------------------------------------------------------
# Independent quote extraction (spec: do NOT reuse the runtime extractor)
# ---------------------------------------------------------------------------

_DOUBLE_QUOTE = re.compile(r'"([^"\n]+)"|“([^”\n]+)”')
_BLOCK_QUOTE_LINE = re.compile(r"^\s{0,3}>\s?(.*)$")


def extract_quoted_spans(response_text: str) -> list[str]:
    """Extract quoted spans: straight/curly double quotes + markdown block quotes.

    * Double-quoted spans (straight ``"..."`` and curly ``“...”``).
    * Markdown block-quote runs — contiguous lines starting with ``>``
      joined with `` / `` (the verse linebreak convention), treated as one
      quoted span.
    * The ``/`` linebreak convention inside spans is preserved here and
      neutralised by :func:`normalise_for_match` at match time.

    Spans under :data:`EVAL_MIN_QUOTE_WORDS` words are dropped.
    """
    spans: list[str] = []
    for m in _DOUBLE_QUOTE.finditer(response_text):
        inner = m.group(1) if m.group(1) is not None else m.group(2)
        if inner:
            spans.append(inner.strip())

    block_run: list[str] = []
    for line in response_text.splitlines() + [""]:
        bm = _BLOCK_QUOTE_LINE.match(line)
        if bm and bm.group(1).strip():
            block_run.append(bm.group(1).strip())
        else:
            if block_run:
                spans.append(" / ".join(block_run))
                block_run = []

    return [
        s
        for s in spans
        if len(normalise_for_match(s).split()) >= EVAL_MIN_QUOTE_WORDS
    ]


# ---------------------------------------------------------------------------
# Normalisation + windowed fuzzy match (metric documented in module docstring)
# ---------------------------------------------------------------------------


def normalise_for_match(text: str) -> str:
    """Harness normalisation: '/' -> space, curly -> straight, collapse ws,
    strip surrounding punctuation, lower-case. Independent implementation
    (deliberately mirrors, but does not import, the verifier's)."""
    text = (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("/", " ")
    )
    text = re.sub(r"\s+", " ", text).strip()
    text = text.strip(".,;:!?\"' ")
    return text.lower()


def best_window_ratio(quote_norm: str, chunk_norm: str) -> float:
    """Best SequenceMatcher ratio of ``quote_norm`` vs word windows of the chunk.

    Exact normalised substring short-circuits to 1.0. Windows span
    ``n-2 .. n+2`` words (n = quote word count), bounded to the chunk.
    Uses ``quick_ratio`` upper bounds to prune full computations.
    """
    if not quote_norm or not chunk_norm:
        return 0.0
    if quote_norm in chunk_norm:
        return 1.0
    chunk_words = chunk_norm.split()
    n = len(quote_norm.split())
    best = 0.0
    matcher = SequenceMatcher(None, "", quote_norm)
    for size in range(max(1, n - 2), min(len(chunk_words), n + 2) + 1):
        for start in range(0, len(chunk_words) - size + 1):
            window = " ".join(chunk_words[start : start + size])
            matcher.set_seq1(window)
            if matcher.real_quick_ratio() <= best or matcher.quick_ratio() <= best:
                continue
            ratio = matcher.ratio()
            if ratio > best:
                best = ratio
                if best == 1.0:
                    return best
    return best


def best_corpus_match(
    quote: str, chunks: Sequence[dict[str, Any]]
) -> tuple[float, int | None]:
    """Best ratio for ``quote`` across ``chunks`` -> (ratio, chunk_index)."""
    qn = normalise_for_match(quote)
    best, best_idx = 0.0, None
    for chunk in chunks:
        ratio = best_window_ratio(qn, normalise_for_match(chunk["text"]))
        if ratio > best:
            best, best_idx = ratio, chunk.get("chunk_index")
            if best == 1.0:
                break
    return best, best_idx


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------


def load_corpus_from_sqlite(persist_dir: Path) -> dict[str, list[dict[str, Any]]]:
    """Read every chunk_json row from the store's sqlite, READ-ONLY.

    Opens ``chroma.sqlite3`` with ``immutable=1`` so no lock, journal or
    WAL write can touch the store — the sanctioned read path for the
    fabrication-metric corpus (whole-text matching, independent of what
    top-k retrieval hands the verifier).
    """
    db = persist_dir / "chroma.sqlite3"
    con = sqlite3.connect(f"file:{db}?immutable=1", uri=True)
    try:
        rows = [
            json.loads(r[0])
            for r in con.execute(
                "select string_value from embedding_metadata"
                " where key='chunk_json'"
            )
        ]
    finally:
        con.close()
    corpus: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        corpus.setdefault(row["text_name"], []).append(row)
    for chunks in corpus.values():
        chunks.sort(key=lambda c: c.get("chunk_index", 0))
    return corpus


def build_t1_corpus(
    items: Sequence[dict[str, Any]],
) -> tuple[dict[str, list[dict[str, Any]]], list[Any]]:
    """Fake corpus for T1: one anchorless PRIMARY_TEXT chunk per golden item.

    Mirrors the shipped store's 581/581-anchorless reality so T1 also
    exercises the anchorless-degradation path. Returns the metric corpus
    (plain dicts) and the CorpusChunk list for the fake collection.
    """
    from study_tutor.knowledge.corpus_models import CorpusChunk, SourceType

    metric_corpus: dict[str, list[dict[str, Any]]] = {}
    model_chunks: list[Any] = []
    for idx, item in enumerate(items):
        text = item["expected_exact"].replace(" / ", " ")
        chunk = CorpusChunk(
            text=f"Context before. {text} Context after.",
            source_type=SourceType.PRIMARY_TEXT,
            source_path=f"/fixture/primary_text/{item['text_name']}.md",
            text_name=item["text_name"],
            citation_anchor=None,
            chunk_index=idx,
        )
        model_chunks.append(chunk)
        metric_corpus.setdefault(item["text_name"], []).append(
            {"text": chunk.text, "text_name": chunk.text_name, "chunk_index": idx}
        )
    return metric_corpus, model_chunks


# ---------------------------------------------------------------------------
# Closure construction per tier
# ---------------------------------------------------------------------------


def build_t1_closure(items: Sequence[dict[str, Any]]) -> tuple[
    Callable[..., tuple[str, Any]], dict[str, list[dict[str, Any]]]
]:
    """Hermetic closure: fake collection provider + ImportError reranker."""
    from study_tutor.cli.main import _build_coach_handover
    from study_tutor.knowledge.retrieval import (
        register_primary_text,
        set_collection_provider,
        set_reranker_factory,
    )

    metric_corpus, model_chunks = build_t1_corpus(items)

    class _FakeCollection:
        """Minimal query surface (the test_cli_rag_wiring.py pattern)."""

        def __init__(self, chunks: list[Any]) -> None:
            self._chunks = chunks

        def count(self) -> int:
            return len(self._chunks)

        def query(
            self,
            *,
            query_texts: list[str],
            n_results: int,
            where: dict[str, Any],
        ) -> dict[str, Any]:
            text_name = None
            allowed: set[str] = set()
            for clause in where.get("$and", []):
                if "text_name" in clause:
                    text_name = clause["text_name"]
                if "source_type" in clause:
                    allowed = set(clause["source_type"]["$in"])
            matched = [
                c
                for c in self._chunks
                if (text_name is None or c.text_name == text_name)
                and c.source_type.value in allowed
            ][:n_results]
            return {
                "metadatas": [
                    [{"chunk_json": c.model_dump_json()} for c in matched]
                ],
                "documents": [[c.text for c in matched]],
                "distances": [[float(i) for i in range(len(matched))]],
            }

    def _import_error_reranker() -> Any:
        raise ImportError("reranker unavailable (T1 hermetic tier)")

    collection = _FakeCollection(model_chunks)
    set_collection_provider(lambda: collection)
    set_reranker_factory(_import_error_reranker)
    for name in sorted({i["text_name"] for i in items}):
        register_primary_text(name)
    return _build_coach_handover(), metric_corpus


def build_t2_closure(persist_dir: Path) -> tuple[
    Callable[..., tuple[str, Any]], dict[str, list[dict[str, Any]]]
]:
    """Production closure vs the REAL baked store + real embedder (:9000)."""
    for key, value in T2_ENV_PINS.items():
        os.environ.setdefault(key, value)
    os.environ["CHROMA_PERSIST_DIR"] = str(persist_dir)

    from study_tutor.cli.main import _build_coach_handover
    from study_tutor.cli.rag_wiring import build_rag_providers
    from study_tutor.roles.loader import load_role

    build_rag_providers(load_role("tutor"))
    metric_corpus = load_corpus_from_sqlite(persist_dir)
    return _build_coach_handover(), metric_corpus


# ---------------------------------------------------------------------------
# Optional generation (--generate)
# ---------------------------------------------------------------------------


def load_player_system_prompt(path: Path = PLAYER_PROMPT_PATH) -> str:
    """The tutor system prompt: player.md minus its leading HTML comment."""
    text = path.read_text(encoding="utf-8")
    return re.sub(r"\A\s*<!--.*?-->\s*", "", text, count=1, flags=re.S)


def _import_generate():
    """Import the A/B harness's ``generate`` under both invocation modes.

    Under pytest the repo root is on ``sys.path`` so the package import
    works; run as a plain script (``uv run python scripts/eval/…``, the
    runbook's own command) ``scripts`` is NOT importable — fall back to a
    same-directory import (2026-08-07 measured-run regression).
    """
    try:
        from scripts.eval.run_ab_eval import generate
    except ModuleNotFoundError:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from run_ab_eval import generate  # type: ignore[no-redef]
    return generate


def generate_response(
    prompt: str,
    *,
    endpoint: str,
    model: str,
    system_prompt: str,
    temperature: float,
    max_tokens: int,
    timeout: float,
) -> str:
    """One generation round-trip, reusing the A/B harness's client."""
    generate = _import_generate()

    result = generate(
        endpoint,
        model,
        system_prompt,
        prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    return result["visible"]


# ---------------------------------------------------------------------------
# Per-item evaluation
# ---------------------------------------------------------------------------


@dataclass
class QuoteVerdict:
    text: str
    best_ratio: float
    best_chunk_index: int | None
    fabricated: bool


@dataclass
class ItemResult:
    item_id: str
    text_name: str
    category: str
    response_source: str
    raw_response: str
    rewritten_response: str
    quotes: list[QuoteVerdict] = field(default_factory=list)
    expected_quoted: bool = False
    verifier: dict[str, Any] = field(default_factory=dict)
    false_correction_flags: list[dict[str, Any]] = field(default_factory=list)

    def to_json(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "text_name": self.text_name,
            "category": self.category,
            "response_source": self.response_source,
            "raw_response": self.raw_response,
            "rewritten_response": self.rewritten_response,
            "quotes": [
                {
                    "text": q.text,
                    "best_ratio": round(q.best_ratio, 4),
                    "best_chunk_index": q.best_chunk_index,
                    "fabricated": q.fabricated,
                }
                for q in self.quotes
            ],
            "expected_quoted": self.expected_quoted,
            "verifier": self.verifier,
            "false_correction_flags": self.false_correction_flags,
        }


def evaluate_item(
    item: dict[str, Any],
    response: str,
    response_source: str,
    closure: Callable[..., tuple[str, Any]],
    metric_corpus: dict[str, list[dict[str, Any]]],
) -> ItemResult:
    """Drive one golden item through the closure and score it."""
    session_state = SimpleNamespace(
        text_name=item["text_name"],
        focus_aos=("AO1", "AO2"),
        subject="english",
    )
    rewritten, metadata = closure(response, item["prompt"], session_state)

    result = ItemResult(
        item_id=item["id"],
        text_name=item["text_name"],
        category=item["category"],
        response_source=response_source,
        raw_response=response,
        rewritten_response=rewritten,
    )

    session_chunks = metric_corpus.get(item["text_name"], [])
    for quote in extract_quoted_spans(response):
        ratio, chunk_idx = best_corpus_match(quote, session_chunks)
        result.quotes.append(
            QuoteVerdict(
                text=quote,
                best_ratio=ratio,
                best_chunk_index=chunk_idx,
                fabricated=ratio < MATCH_THRESHOLD,
            )
        )
    expected_norm = normalise_for_match(item["expected_exact"])
    result.expected_quoted = any(
        expected_norm in normalise_for_match(q.text)
        or normalise_for_match(q.text) in expected_norm
        for q in result.quotes
    )

    primary = list(getattr(metadata, "primary_matches", []))
    fuzzy = list(getattr(metadata, "fuzzy_corrections", []))
    strips = list(getattr(metadata, "no_match_strips", []))
    result.verifier = {
        "primary_matches": len(primary),
        "secondary_rewrites": len(getattr(metadata, "secondary_rewrites", [])),
        "fuzzy_corrections": len(fuzzy),
        "no_match_strips": len(strips),
        "cross_text_events": len(getattr(metadata, "cross_text_events", [])),
        "anchorless_primary_matches": getattr(
            metadata, "anchorless_primary_matches", 0
        ),
        "anchorless_fuzzy_corrections": getattr(
            metadata, "anchorless_fuzzy_corrections", 0
        ),
        "retrieval_skipped_reason": getattr(
            metadata, "retrieval_skipped_reason", None
        ),
        "verifier_exception": getattr(metadata, "verifier_exception", False),
    }

    # False-correction scaffold: any rewrite whose ORIGINAL had a >= 95%
    # match anywhere in the corpus (any text). See module docstring for
    # its honest limits.
    all_chunks = [c for chunks in metric_corpus.values() for c in chunks]
    for event_kind, events in (("fuzzy_correction", fuzzy), ("no_match_strip", strips)):
        for event in events:
            original = getattr(event, "original_span", "")
            ratio, chunk_idx = best_corpus_match(original, all_chunks)
            if ratio >= MATCH_THRESHOLD:
                result.false_correction_flags.append(
                    {
                        "kind": event_kind,
                        "original_span": original,
                        "corpus_ratio": round(ratio, 4),
                        "corpus_chunk_index": chunk_idx,
                    }
                )
    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def load_responses(path: Path) -> dict[str, str]:
    responses: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        row = json.loads(line)
        responses[row["id"]] = row["response"]
    return responses


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--golden", type=Path, default=GOLDEN_PATH_DEFAULT)
    ap.add_argument(
        "--tier",
        choices=("t1", "t2"),
        required=True,
        help="t1 = hermetic fake collection; t2 = real baked store + embedder",
    )
    ap.add_argument(
        "--persist-dir",
        type=Path,
        default=None,
        help="T2 only: ChromaDB persist dir (sets CHROMA_PERSIST_DIR). "
        "Point READ-ONLY at the baked store — never at a store you may not "
        "modify without also accepting chroma's own bookkeeping writes; "
        "prefer a scratch copy for absolute isolation.",
    )
    ap.add_argument(
        "--responses",
        type=Path,
        default=None,
        help="Verify-only mode (default): JSONL of {id, response}.",
    )
    ap.add_argument(
        "--ids",
        default=None,
        help="Comma-separated golden ids to run (default: all).",
    )
    ap.add_argument(
        "--generate",
        action="store_true",
        help="Generate responses via chat/completions instead of --responses.",
    )
    ap.add_argument("--endpoint", default="http://localhost:9000/v1")
    ap.add_argument("--model", default="gemma4-tutor")
    ap.add_argument("--temperature", type=float, default=0.7)
    ap.add_argument("--max-tokens", type=int, default=1024)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument(
        "--out",
        type=Path,
        required=True,
        help="Results JSONL (feed to score_fabrication.py).",
    )
    args = ap.parse_args(argv)

    items = load_golden(args.golden)
    if args.ids:
        wanted = {i.strip() for i in args.ids.split(",") if i.strip()}
        missing = wanted - {i["id"] for i in items}
        if missing:
            ap.error(f"unknown golden ids: {sorted(missing)}")
        items = [i for i in items if i["id"] in wanted]

    if args.generate and args.responses:
        ap.error("--generate and --responses are mutually exclusive")
    if not args.generate and not args.responses:
        ap.error("default mode verifies SUPPLIED responses: pass --responses "
                 "(or opt in to generation with --generate)")

    if args.tier == "t1":
        closure, metric_corpus = build_t1_closure(items)
    else:
        persist_dir = args.persist_dir or Path(
            os.environ.get("CHROMA_PERSIST_DIR", "data/chroma")
        )
        if not persist_dir.exists():
            ap.error(f"persist dir not found: {persist_dir}")
        closure, metric_corpus = build_t2_closure(persist_dir)

    responses = load_responses(args.responses) if args.responses else {}
    system_prompt = load_player_system_prompt() if args.generate else ""

    results: list[ItemResult] = []
    for item in items:
        if args.generate:
            response = generate_response(
                item["prompt"],
                endpoint=args.endpoint,
                model=args.model,
                system_prompt=system_prompt,
                temperature=args.temperature,
                max_tokens=args.max_tokens,
                timeout=args.timeout,
            )
            source = f"generated:{args.model}"
        else:
            if item["id"] not in responses:
                print(f"  SKIP {item['id']} (no supplied response)")
                continue
            response = responses[item["id"]]
            source = "supplied"
        result = evaluate_item(item, response, source, closure, metric_corpus)
        results.append(result)
        fabricated = sum(q.fabricated for q in result.quotes)
        print(
            f"  {result.item_id}: quotes={len(result.quotes)} "
            f"fabricated={fabricated} "
            f"primary={result.verifier['primary_matches']} "
            f"(anchorless={result.verifier['anchorless_primary_matches']}) "
            f"strips={result.verifier['no_match_strips']} "
            f"exception={result.verifier['verifier_exception']}"
        )

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", encoding="utf-8") as fh:
        for result in results:
            fh.write(json.dumps(result.to_json(), ensure_ascii=False) + "\n")
    print(f"wrote {len(results)} item results -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
