#!/usr/bin/env python3
"""Resolve + aggregate the multi-turn judgements.

multiturn_raw_judgements.jsonl is the judge's committed output — one object
per scenario, against the blind A/B labels:

  {"id": str, "winner": "A"|"B"|"tie",
   "A": {socratic_stance, aqa_alignment, scaffolding,
         subject_accuracy, tone, reasoning_visibility},   # ints 1-5
   "B": {... same six keys ...},
   "rationale": str}

Run only AFTER multiturn_raw_judgements.jsonl is finalised.
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
    ap.add_argument("--raw", default=f"{base}/multiturn_raw_judgements.jsonl")
    ap.add_argument("--key", default=f"{base}/multiturn_key.json")
    ap.add_argument("--out", default=f"{base}/multiturn_judgements.jsonl")
    ap.add_argument("--table", default=f"{base}/multiturn_results-table.md")
    args = ap.parse_args()

    key = json.loads(Path(args.key).read_text(encoding="utf-8"))["base_position"]
    raw = [
        json.loads(line)
        for line in Path(args.raw).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    n = max(len(raw), 1)

    tally = {"base": 0, "finetune": 0, "tie": 0}
    resolved = []
    for j in raw:
        for pos in ("A", "B"):
            missing = [d for d in DIMS if d not in j.get(pos, {})]
            if missing:
                raise SystemExit(f"{j['id']}: response {pos} missing {missing}")
        base_pos = key[j["id"]]
        ft_pos = "B" if base_pos == "A" else "A"
        w = j["winner"]
        winner = "tie" if w == "tie" else ("base" if w == base_pos else "finetune")
        tally[winner] += 1
        resolved.append({
            "id": j["id"], "winner": winner,
            "base_scores": j[base_pos], "finetune_scores": j[ft_pos],
            "rationale": j.get("rationale", ""),
        })

    Path(args.out).write_text(
        "\n".join(json.dumps(r) for r in resolved) + "\n", encoding="utf-8"
    )

    dm = {"base": {}, "finetune": {}}
    for d in DIMS:
        dm["base"][d] = sum(r["base_scores"][d] for r in resolved) / n
        dm["finetune"][d] = sum(r["finetune_scores"][d] for r in resolved) / n

    out = []
    out.append("# Base vs Fine-Tuned — Multi-Turn Evaluation Results")
    out.append("")
    out.append(f"_{len(raw)} scripted multi-turn tutoring scenarios, blind "
               "position-randomised holistic judging. Identical system prompt, "
               "greedy decoding and student script; each model built its own side "
               "of the conversation._")
    out.append("")
    out.append("## Head-to-head — judge preference (whole session)")
    out.append("")
    out.append("| Outcome | Count |")
    out.append("|---|---|")
    for k, lab in [("finetune", "Fine-tune preferred"),
                   ("base", "Base preferred"), ("tie", "Tie")]:
        out.append(f"| {lab} | {tally[k]} |")
    out.append("")
    out.append("## Mean dimension scores (1–5)")
    out.append("")
    out.append("| Dimension | Base | Fine-tuned | Δ |")
    out.append("|---|---|---|---|")
    for d in DIMS:
        b, f = dm["base"][d], dm["finetune"][d]
        out.append(f"| {d.replace('_', ' ').title()} | {b:.2f} | {f:.2f} | {f - b:+.2f} |")
    out.append("")
    out.append("## Per-scenario verdicts")
    out.append("")
    out.append("| Scenario | Winner | Rationale |")
    out.append("|---|---|---|")
    for r in resolved:
        out.append(f"| {r['id']} | {r['winner']} | {r['rationale']} |")
    out.append("")

    text = "\n".join(out) + "\n"
    Path(args.table).write_text(text, encoding="utf-8")
    print(text)
    print(f"Tally  fine-tune={tally['finetune']}  base={tally['base']}  tie={tally['tie']}")
    print(f"Wrote {args.out} and {args.table}")


if __name__ == "__main__":
    main()
