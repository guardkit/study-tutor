#!/usr/bin/env python3
"""Blind-prepare for the multi-turn eval — anonymise the per-scenario
transcripts into A/B pairs for holistic session judging.

Writes:
  multiturn_blind.jsonl — {id, text, summary, transcript_a, transcript_b}
  multiturn_key.json    — {seed, base_position: {id: "A"|"B"}}
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    base = "docs/runbooks/evidence/base-vs-finetune-eval"
    ap.add_argument("--transcripts", default=f"{base}/multiturn_transcripts.jsonl")
    ap.add_argument("--blind-out", default=f"{base}/multiturn_blind.jsonl")
    ap.add_argument("--key-out", default=f"{base}/multiturn_key.json")
    ap.add_argument("--seed", type=int, default=20260518)
    args = ap.parse_args()

    random.seed(args.seed)
    rows = [
        json.loads(line)
        for line in Path(args.transcripts).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    key: dict[str, str] = {}
    with Path(args.blind_out).open("w", encoding="utf-8") as f:
        for r in rows:
            base_is_a = random.random() < 0.5
            key[r["id"]] = "A" if base_is_a else "B"
            ta = r["base_transcript"] if base_is_a else r["finetune_transcript"]
            tb = r["finetune_transcript"] if base_is_a else r["base_transcript"]
            f.write(json.dumps({
                "id": r["id"], "text": r["text"], "summary": r["summary"],
                "transcript_a": ta, "transcript_b": tb,
            }) + "\n")

    Path(args.key_out).write_text(
        json.dumps({"seed": args.seed, "base_position": key}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} blind scenario pairs -> {args.blind_out}")
    print(f"Wrote base-position key            -> {args.key_out}")


if __name__ == "__main__":
    main()
