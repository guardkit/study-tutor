#!/usr/bin/env python3
"""Deterministic (no-LLM) scoring of the A/B responses.

Measures the things a judge is not needed for — and the things a judge
should never be trusted with because they must be exact:

* template-token leaks (``<|channel>`` / ``<|turn>`` etc.) in the visible
  stream — a fine-tune regression signal; must be zero
* where each model puts its reasoning — inline ``<think>`` (the fine-tune's
  trained format) vs the ``reasoning_content`` API channel (the base)
* visible-answer length and whether the reply asks the student a question
  (a crude Socratic-stance proxy; the judge does the real assessment)

Length and question-presence are measured on the VISIBLE answer (``<think>``
stripped) so the fine-tune is not flattered by its inline reasoning block.

Input : responses.jsonl  (from run_ab_eval.py)
Output: deterministic.json + a printed summary table
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

# Chat-template control tokens that must never appear in user-visible text.
LEAK_TOKENS = [
    "<|channel>", "<channel|>", "<|turn>", "<turn|>",
    "<|message>", "<end_of_turn>", "<start_of_turn>",
]


def score_one(resp: dict) -> dict:
    content = resp.get("content", "")
    visible = resp.get("visible", content)
    reasoning_channel = resp.get("reasoning_content", "")
    inline_think = "<think>" in content
    return {
        "visible_chars": len(visible),
        "visible_words": len(visible.split()),
        "inline_think": inline_think,
        "reasoning_present": inline_think or bool(reasoning_channel.strip()),
        "leak_tokens": sum(visible.count(t) for t in LEAK_TOKENS),
        "asks_a_question": "?" in visible,
        "finish_reason": resp.get("finish_reason"),
    }


def summarise(items: list[dict]) -> dict:
    n = max(len(items), 1)
    return {
        "n": len(items),
        "inline_think_pct": round(100 * sum(i["inline_think"] for i in items) / n, 1),
        "reasoning_present_pct": round(100 * sum(i["reasoning_present"] for i in items) / n, 1),
        "leak_total": sum(i["leak_tokens"] for i in items),
        "asks_question_pct": round(100 * sum(i["asks_a_question"] for i in items) / n, 1),
        "mean_visible_words": round(sum(i["visible_words"] for i in items) / n, 1),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    base = "docs/runbooks/evidence/base-vs-finetune-eval"
    ap.add_argument("--responses", default=f"{base}/responses.jsonl")
    ap.add_argument("--out", default=f"{base}/deterministic.json")
    args = ap.parse_args()

    rows = [
        json.loads(line)
        for line in Path(args.responses).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    base_scores, ft_scores, per_item = [], [], []
    for r in rows:
        b = score_one(r["base"])
        f = score_one(r["finetune"])
        base_scores.append(b)
        ft_scores.append(f)
        per_item.append({"id": r["id"], "category": r["category"], "base": b, "finetune": f})

    summary = {"base": summarise(base_scores), "finetune": summarise(ft_scores)}
    Path(args.out).write_text(
        json.dumps({"summary": summary, "per_item": per_item}, indent=2),
        encoding="utf-8",
    )

    print(f"{'metric':<26}{'base':>12}{'fine-tune':>12}")
    print("-" * 50)
    for k in ["n", "inline_think_pct", "reasoning_present_pct",
              "leak_total", "asks_question_pct", "mean_visible_words"]:
        print(f"{k:<26}{summary['base'][k]:>12}{summary['finetune'][k]:>12}")

    leaks = summary["finetune"]["leak_total"]
    print()
    if leaks:
        print(f"WARNING: {leaks} template-token leak(s) in the fine-tune's visible "
              "output — the gemma4-tutor.jinja leak fix may have regressed.")
    else:
        print("PASS: zero template-token leaks in the fine-tune's visible output.")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
