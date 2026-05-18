#!/usr/bin/env python3
"""Aggregate the deterministic + judge results into a submission-ready
markdown table, drop-in for ``docs/submission/technical-writeup.md`` §11
(Evaluation).

Input : deterministic.json + judgements.jsonl
Output: results-table.md (and the same content printed to stdout)
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

DIMS = [
    "socratic_stance", "aqa_alignment", "scaffolding",
    "subject_accuracy", "tone", "reasoning_visibility",
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    base = "docs/runbooks/evidence/base-vs-finetune-eval"
    ap.add_argument("--deterministic", default=f"{base}/deterministic.json")
    ap.add_argument("--judgements", default=f"{base}/judgements.jsonl")
    ap.add_argument("--out", default=f"{base}/results-table.md")
    args = ap.parse_args()

    det = json.loads(Path(args.deterministic).read_text(encoding="utf-8"))["summary"]
    judg = [
        json.loads(line)
        for line in Path(args.judgements).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    n = max(len(judg), 1)

    wins = {"base": 0, "finetune": 0, "tie": 0}
    for j in judg:
        wins[j["winner"]] += 1

    dim_means = {"base": {}, "finetune": {}}
    for d in DIMS:
        dim_means["base"][d] = sum(j["base_scores"][d] for j in judg) / n
        dim_means["finetune"][d] = sum(j["finetune_scores"][d] for j in judg) / n

    # Per-category win counts.
    cats: dict[str, dict[str, int]] = {}
    for j in judg:
        c = cats.setdefault(j["category"], {"base": 0, "finetune": 0, "tie": 0})
        c[j["winner"]] += 1

    out: list[str] = []
    out.append("# Base vs Fine-Tuned — Evaluation Results")
    out.append("")
    out.append(
        f"_Generated {datetime.date.today()} — {len(judg)} golden-set prompts, "
        "blind position-randomised Claude-as-judge. Both models served at "
        "Q4_K_M via llama.cpp and given an identical system prompt and "
        "greedy decoding (temperature 0); the only variable is the weights._"
    )
    out.append("")
    out.append("## Head-to-head — judge preference")
    out.append("")
    out.append("| Outcome | Count | Share |")
    out.append("|---|---|---|")
    for k, label in [("finetune", "Fine-tune preferred"),
                     ("base", "Base preferred"),
                     ("tie", "Tie")]:
        out.append(f"| {label} | {wins[k]} | {100 * wins[k] / n:.0f}% |")
    out.append("")
    out.append("## Mean dimension scores (1–5)")
    out.append("")
    out.append("| Dimension | Base | Fine-tuned | Δ |")
    out.append("|---|---|---|---|")
    for d in DIMS:
        b, f = dim_means["base"][d], dim_means["finetune"][d]
        out.append(f"| {d.replace('_', ' ').title()} | {b:.2f} | {f:.2f} | {f - b:+.2f} |")
    out.append("")
    out.append("## Win rate by prompt category")
    out.append("")
    out.append("| Category | Fine-tune | Base | Tie |")
    out.append("|---|---|---|---|")
    for c in sorted(cats):
        v = cats[c]
        out.append(f"| {c} | {v['finetune']} | {v['base']} | {v['tie']} |")
    out.append("")
    out.append("## Deterministic checks")
    out.append("")
    out.append("| Metric | Base | Fine-tuned |")
    out.append("|---|---|---|")
    for k, label in [
        ("inline_think_pct", "Inline `<think>` block in output (%)"),
        ("reasoning_present_pct", "Reasoning present, either channel (%)"),
        ("leak_total", "Template-token leaks, visible stream (must be 0)"),
        ("asks_question_pct", "Visible answer contains a question (%)"),
        ("mean_visible_words", "Mean visible-answer length (words)"),
    ]:
        out.append(f"| {label} | {det['base'][k]} | {det['finetune'][k]} |")
    out.append("")

    text = "\n".join(out) + "\n"
    Path(args.out).write_text(text, encoding="utf-8")
    print(text)
    print(f"Wrote {args.out}")


if __name__ == "__main__":
    main()
