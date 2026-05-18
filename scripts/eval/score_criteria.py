#!/usr/bin/env python3
"""Criterion-referenced scoring — length-neutral.

The pairwise LLM-as-judge eval (judge_pairwise / the session judge) rewards
longer, more 'thorough-looking' responses — a well-documented bias. This
scorer removes that: each response is scored ONLY against its own item's
``expected_behaviours`` (met = 1.0 / partial = 0.5 / not = 0.0) and
``red_flags`` (tripped = 1). There is no comparison between the two models,
so a concise response that satisfies every expected behaviour scores 100%
regardless of length.

Input : criteria_judgements.jsonl — one object per golden-set item:
  {"id": str, "category": str,
   "base":     {"behaviours": [1|0.5|0, ...], "red_flags": [1|0, ...]},
   "finetune": {"behaviours": [...],          "red_flags": [...]}}
  The lists align positionally with golden_set.jsonl's expected_behaviours
  and red_flags for that item.
Output: criteria_results-table.md
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def aggregate(rows: list[dict], model: str) -> dict:
    beh_sum = beh_tot = rf_trip = rf_tot = 0.0
    clean = 0
    per = []
    for r in rows:
        m = r[model]
        b, rf = m["behaviours"], m["red_flags"]
        beh_sum += sum(b)
        beh_tot += len(b)
        rf_trip += sum(rf)
        rf_tot += len(rf)
        item_clean = sum(b) == len(b) and sum(rf) == 0
        clean += int(item_clean)
        per.append({"id": r["id"], "category": r["category"],
                    "behaviour_frac": round(sum(b) / max(len(b), 1), 2),
                    "red_flags": int(sum(rf))})
    return {
        "n": len(rows),
        "behaviour_pct": round(100 * beh_sum / max(beh_tot, 1), 1),
        "red_flags_tripped": int(rf_trip),
        "red_flag_total": int(rf_tot),
        "clean_items": clean,
        "per": per,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    base = "docs/runbooks/evidence/base-vs-finetune-eval"
    ap.add_argument("--judgements", default=f"{base}/criteria_judgements.jsonl")
    ap.add_argument("--out", default=f"{base}/criteria_results-table.md")
    args = ap.parse_args()

    rows = [
        json.loads(line)
        for line in Path(args.judgements).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    b = aggregate(rows, "base")
    f = aggregate(rows, "finetune")

    out = []
    out.append("# Base vs Fine-Tuned — Criterion-Referenced Results")
    out.append("")
    out.append(f"_{b['n']} golden-set prompts. Each response scored only against "
               "its own `expected_behaviours` and `red_flags` — length-neutral, "
               "no model-vs-model comparison, so verbosity cannot inflate a score._")
    out.append("")
    out.append("| Metric | Base | Fine-tuned |")
    out.append("|---|---|---|")
    out.append(f"| Expected behaviours met (%) | {b['behaviour_pct']} | {f['behaviour_pct']} |")
    out.append(f"| Red flags tripped | {b['red_flags_tripped']} / {b['red_flag_total']} "
               f"| {f['red_flags_tripped']} / {f['red_flag_total']} |")
    out.append(f"| Clean items (all behaviours, no red flag) | {b['clean_items']} / {b['n']} "
               f"| {f['clean_items']} / {f['n']} |")
    out.append("")
    out.append("## Per-item behaviour fraction (red flags in brackets)")
    out.append("")
    out.append("| Item | Base | Fine-tuned |")
    out.append("|---|---|---|")
    fmap = {p["id"]: p for p in f["per"]}
    for pb in b["per"]:
        pf = fmap[pb["id"]]
        bcell = f"{pb['behaviour_frac']:.2f}" + (f" ⚑{pb['red_flags']}" if pb["red_flags"] else "")
        fcell = f"{pf['behaviour_frac']:.2f}" + (f" ⚑{pf['red_flags']}" if pf["red_flags"] else "")
        out.append(f"| {pb['id']} | {bcell} | {fcell} |")
    out.append("")

    text = "\n".join(out) + "\n"
    Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
