#!/usr/bin/env python3
"""Aggregate golden-quote fabrication results into a markdown table.

Input: the per-item results JSONL written by ``run_fabrication_eval.py``.
Output: a markdown report (stdout or ``--out``) with per-text and overall
rates against the FROZEN bars (pre-registered in
``docs/runbooks/RUNBOOK-golden-quote-fabrication-eval.md``):

* **Fabrication rate < 5% (Phase A) / < 1% (Phase B)** — quoted strings
  with no >= 95% windowed fuzzy match / total quoted strings.
* **Citation coverage** — verified matches (primary + fuzzy) carrying a
  citation anchor / all verified matches (from the additive
  ``anchorless_*`` VerifierMetadata counters). Against the shipped
  581/581-anchorless store this is honestly 0% until Track B lands.
* **False-correction flags** — verifier rewrites whose original had a
  >= 95% corpus match (scaffold; counted, not yet a bar).
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

PHASE_A_BAR = 0.05
PHASE_B_BAR = 0.01


@dataclass
class Bucket:
    """Aggregated counts for one text_name (or the overall roll-up)."""

    items: int = 0
    quotes: int = 0
    fabricated: int = 0
    verified_matches: int = 0
    anchorless_matches: int = 0
    strips: int = 0
    verifier_exceptions: int = 0
    false_correction_flags: int = 0
    fabricated_ids: list[str] = field(default_factory=list)

    def add(self, record: dict[str, Any]) -> None:
        self.items += 1
        for quote in record.get("quotes", []):
            self.quotes += 1
            if quote.get("fabricated"):
                self.fabricated += 1
                if record["item_id"] not in self.fabricated_ids:
                    self.fabricated_ids.append(record["item_id"])
        verifier = record.get("verifier", {})
        verified = verifier.get("primary_matches", 0) + verifier.get(
            "fuzzy_corrections", 0
        )
        anchorless = verifier.get("anchorless_primary_matches", 0) + verifier.get(
            "anchorless_fuzzy_corrections", 0
        )
        self.verified_matches += verified
        self.anchorless_matches += anchorless
        self.strips += verifier.get("no_match_strips", 0)
        self.verifier_exceptions += bool(verifier.get("verifier_exception"))
        self.false_correction_flags += len(
            record.get("false_correction_flags", [])
        )

    @property
    def fabrication_rate(self) -> float | None:
        return None if self.quotes == 0 else self.fabricated / self.quotes

    @property
    def citation_coverage(self) -> float | None:
        if self.verified_matches == 0:
            return None
        return (
            self.verified_matches - self.anchorless_matches
        ) / self.verified_matches


def _pct(value: float | None) -> str:
    return "n/a" if value is None else f"{value * 100:.1f}%"


def _bar_verdict(rate: float | None) -> str:
    if rate is None:
        return "no quotes"
    if rate < PHASE_B_BAR:
        return "PASS (Phase B)"
    if rate < PHASE_A_BAR:
        return "PASS (Phase A)"
    return "FAIL"


def aggregate(records: list[dict[str, Any]]) -> dict[str, Bucket]:
    """Bucket records per text_name plus an ``overall`` roll-up."""
    buckets: dict[str, Bucket] = {"overall": Bucket()}
    for record in records:
        buckets.setdefault(record["text_name"], Bucket()).add(record)
        buckets["overall"].add(record)
    return buckets


def render_markdown(buckets: dict[str, Bucket], source: str) -> str:
    """Render the per-text + overall markdown results table."""
    lines = [
        "# Golden-quote fabrication eval — results",
        "",
        f"Input: `{source}`",
        "",
        "**Frozen bar (pre-registered):** fabrication rate "
        f"< {PHASE_A_BAR:.0%} (Phase A) / < {PHASE_B_BAR:.0%} (Phase B). "
        "Re-run on every Player-model change and every corpus ingest.",
        "",
        "| text | items | quotes | fabricated | fabrication rate | "
        "citation coverage | strips | false-corr flags | verifier exc | "
        "verdict |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    ordered = sorted(k for k in buckets if k != "overall") + ["overall"]
    for name in ordered:
        bucket = buckets[name]
        label = f"**{name}**" if name == "overall" else name
        lines.append(
            f"| {label} | {bucket.items} | {bucket.quotes} | "
            f"{bucket.fabricated} | {_pct(bucket.fabrication_rate)} | "
            f"{_pct(bucket.citation_coverage)} | {bucket.strips} | "
            f"{bucket.false_correction_flags} | "
            f"{bucket.verifier_exceptions} | "
            f"{_bar_verdict(bucket.fabrication_rate)} |"
        )
    overall = buckets["overall"]
    if overall.fabricated_ids:
        lines += [
            "",
            "Fabrication-flagged items: "
            + ", ".join(f"`{i}`" for i in overall.fabricated_ids),
        ]
    if overall.citation_coverage == 0.0:
        lines += [
            "",
            "_Citation coverage 0% is the shipped store's honest state: "
            "581/581 chunks are anchorless (2026-05-10 docling ingest); "
            "verified quotes render uncited until Track B restores anchors._",
        ]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("results", type=Path, help="results JSONL from run_fabrication_eval.py")
    ap.add_argument("--out", type=Path, default=None, help="write markdown here (default stdout)")
    args = ap.parse_args(argv)

    records = [
        json.loads(line)
        for line in args.results.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    report = render_markdown(aggregate(records), str(args.results))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report, encoding="utf-8")
        print(f"wrote {args.out}")
    else:
        print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
