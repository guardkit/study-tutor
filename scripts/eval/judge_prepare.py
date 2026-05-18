#!/usr/bin/env python3
"""Blind-prepare step: turn ``responses.jsonl`` into anonymised A/B pairs for
a judge that must not know which model produced which response.

Splitting *blinding* from *judging* keeps the eval judge-agnostic — the judge
may be a Claude Code session executing the runbook, a human, or the automated
API path in ``judge_pairwise.py``. Whoever judges sees only "Response A" /
"Response B"; the base/fine-tune mapping is held in a separate key file and
applied afterwards by ``judge_resolve.py``.

Writes:
  blind_pairs.jsonl  — {id, category, prompt, expected_behaviours,
                        red_flags, response_a, response_b}   (NO model labels)
  blind_key.json     — {seed, base_position: {id: "A"|"B"}}  base's position
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    base = "docs/runbooks/evidence/base-vs-finetune-eval"
    ap.add_argument("--responses", default=f"{base}/responses.jsonl")
    ap.add_argument("--pairs-out", default=f"{base}/blind_pairs.jsonl")
    ap.add_argument("--key-out", default=f"{base}/blind_key.json")
    ap.add_argument("--seed", type=int, default=20260518,
                    help="Seeds the A/B shuffle — keep fixed across re-runs.")
    args = ap.parse_args()

    random.seed(args.seed)
    rows = [
        json.loads(line)
        for line in Path(args.responses).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    def channels(side: dict) -> dict:
        """The judge sees the visible answer plus the model's reasoning —
        the reasoning may be inline ``<think>`` or the ``reasoning_content``
        channel, so prefer whichever is populated."""
        content = side.get("content", "")
        reasoning = side.get("reasoning_content", "").strip()
        if not reasoning and "<think>" in content:
            import re
            m = re.search(r"<think>(.*?)</think>", content, re.S)
            reasoning = m.group(1).strip() if m else ""
        return {"visible": side.get("visible", content), "reasoning": reasoning}

    base_position: dict[str, str] = {}
    with Path(args.pairs_out).open("w", encoding="utf-8") as f:
        for r in rows:
            base_is_a = random.random() < 0.5
            base_position[r["id"]] = "A" if base_is_a else "B"
            a = channels(r["base"]) if base_is_a else channels(r["finetune"])
            b = channels(r["finetune"]) if base_is_a else channels(r["base"])
            f.write(json.dumps({
                "id": r["id"],
                "category": r["category"],
                "prompt": r["prompt"],
                "expected_behaviours": r.get("expected_behaviours", []),
                "red_flags": r.get("red_flags", []),
                "response_a": a["visible"],
                "response_a_reasoning": a["reasoning"],
                "response_b": b["visible"],
                "response_b_reasoning": b["reasoning"],
            }) + "\n")

    Path(args.key_out).write_text(
        json.dumps({"seed": args.seed, "base_position": base_position}, indent=2),
        encoding="utf-8",
    )
    print(f"Wrote {len(rows)} blind pairs -> {args.pairs_out}")
    print(f"Wrote base-position key      -> {args.key_out}")
    print("The judge must commit raw_judgements.jsonl BEFORE the key is applied.")


if __name__ == "__main__":
    main()
