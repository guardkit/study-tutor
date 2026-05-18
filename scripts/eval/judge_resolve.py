#!/usr/bin/env python3
"""Resolve step: apply the blind key to raw A/B judgements, producing the
final ``judgements.jsonl`` that ``aggregate.py`` consumes.

``raw_judgements.jsonl`` is the judge's committed output — one object per
line, written against the *blind* A/B labels:

  {"id": str,
   "winner": "A" | "B" | "tie",
   "A": {socratic_stance, aqa_alignment, scaffolding,
         subject_accuracy, tone, reasoning_visibility},   # ints 1-5
   "B": {... same six keys ...},
   "rationale": str}

This script reads the key written by ``judge_prepare.py`` and maps A/B back
to base/fine-tune. Run it only AFTER ``raw_judgements.jsonl`` is finalised.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

DIMS = [
    "socratic_stance", "aqa_alignment", "scaffolding",
    "subject_accuracy", "tone", "reasoning_visibility",
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    base = "docs/runbooks/evidence/base-vs-finetune-eval"
    ap.add_argument("--raw", default=f"{base}/raw_judgements.jsonl")
    ap.add_argument("--key", default=f"{base}/blind_key.json")
    ap.add_argument("--pairs", default=f"{base}/blind_pairs.jsonl")
    ap.add_argument("--out", default=f"{base}/judgements.jsonl")
    args = ap.parse_args()

    key = json.loads(Path(args.key).read_text(encoding="utf-8"))["base_position"]
    categories = {
        json.loads(line)["id"]: json.loads(line)["category"]
        for line in Path(args.pairs).read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    raw = [
        json.loads(line)
        for line in Path(args.raw).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    tally = {"base": 0, "finetune": 0, "tie": 0}
    with Path(args.out).open("w", encoding="utf-8") as f:
        for j in raw:
            if j["id"] not in key:
                raise SystemExit(f"{j['id']}: not present in blind key")
            for pos in ("A", "B"):
                missing = [d for d in DIMS if d not in j.get(pos, {})]
                if missing:
                    raise SystemExit(f"{j['id']}: response {pos} missing {missing}")

            base_pos = key[j["id"]]                       # "A" or "B"
            ft_pos = "B" if base_pos == "A" else "A"
            w = j["winner"]
            if w == "tie":
                winner = "tie"
            elif w == base_pos:
                winner = "base"
            else:
                winner = "finetune"
            tally[winner] += 1

            f.write(json.dumps({
                "id": j["id"],
                "category": categories.get(j["id"], "?"),
                "base_position": base_pos,
                "winner": winner,
                "base_scores": j[base_pos],
                "finetune_scores": j[ft_pos],
                "rationale": j.get("rationale", ""),
            }) + "\n")

    print(f"Resolved {len(raw)} judgements -> {args.out}")
    print(f"Tally  fine-tune={tally['finetune']}  base={tally['base']}  tie={tally['tie']}")


if __name__ == "__main__":
    main()
