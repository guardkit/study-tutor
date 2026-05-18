#!/usr/bin/env python3
"""Claude-as-judge: blind pairwise comparison of base vs fine-tuned tutor
responses.

Two bias-control measures are built in:

* **Blind** — the judge is shown "Response A" / "Response B" and is never
  told which model produced which.
* **Position-randomised** — for each item the base/fine-tune assignment to
  A/B is randomised (deterministically, via ``--seed``) so any positional
  preference of the judge averages out across the set.

The rubric system block is sent with ``cache_control`` so it is written to
the Anthropic prompt cache once and re-read on every subsequent item.

Input : responses.jsonl  (from run_ab_eval.py)
Output: judgements.jsonl
Requires: ANTHROPIC_API_KEY in the environment, and the ``anthropic`` package
          (``uv pip install anthropic`` — pulled in transitively by
          langchain-anthropic, which is already a project dependency).
"""
from __future__ import annotations

import argparse
import json
import os
import random
import re
from pathlib import Path

import anthropic

DIMENSIONS = [
    "socratic_stance",       # guides instead of handing over the answer
    "aqa_alignment",         # assessment objectives + exam-board vocabulary
    "scaffolding",           # grade/age-appropriate, builds on the attempt
    "subject_accuracy",      # correct about the text/topic; quotes authentic
    "tone",                  # encouraging, right for a Year-10 student
    "reasoning_visibility",  # surfaces its pedagogical thinking
]

RUBRIC = """You are an experienced AQA GCSE English examiner and teacher-trainer.
You are judging two AI tutor responses to the same Year-10 student message.
The student is targeting grade 7 in AQA English Literature (8702) and English
Language (8700). A strong GCSE tutor response:

- guides with questions; it never simply hands over the finished answer
- uses AQA assessment-objective framing (AO1/AO2/AO3) and exam-board vocabulary
- builds on what the student already attempted and is pitched for a 15-year-old
- is accurate about the set texts (Macbeth, An Inspector Calls, the Power &
  Conflict anthology) and uses only authentic quotations
- is warm and encouraging, especially with a discouraged student
- makes its pedagogical reasoning visible

Score EACH response on EVERY dimension from 1 (poor) to 5 (excellent), then
pick the overall better tutor response. If they are genuinely indistinguishable
in quality, return "tie".

Return ONLY a fenced ```json block of exactly this shape:
{"winner": "A" | "B" | "tie",
 "A": {"socratic_stance": int, "aqa_alignment": int, "scaffolding": int,
       "subject_accuracy": int, "tone": int, "reasoning_visibility": int},
 "B": {"socratic_stance": int, "aqa_alignment": int, "scaffolding": int,
       "subject_accuracy": int, "tone": int, "reasoning_visibility": int},
 "rationale": "<= 2 sentences"}"""


def judge(client: anthropic.Anthropic, model: str, item: dict,
          resp_a: str, resp_b: str) -> dict:
    user = (
        f"STUDENT MESSAGE:\n{item['prompt']}\n\n"
        f"--- RESPONSE A ---\n{resp_a}\n\n"
        f"--- RESPONSE B ---\n{resp_b}\n"
    )
    msg = client.messages.create(
        model=model,
        max_tokens=700,
        temperature=0,
        system=[{"type": "text", "text": RUBRIC,
                 "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in msg.content if b.type == "text")
    match = re.search(r"```json\s*(.+?)```", text, re.S)
    return json.loads(match.group(1) if match else text)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    base = "docs/runbooks/evidence/base-vs-finetune-eval"
    ap.add_argument("--responses", default=f"{base}/responses.jsonl")
    ap.add_argument("--out", default=f"{base}/judgements.jsonl")
    ap.add_argument("--model", default="claude-opus-4-7",
                    help="Judge model. claude-sonnet-4-6 is fine for a dry run.")
    ap.add_argument("--seed", type=int, default=20260518,
                    help="Seeds the A/B position randomisation — keep it fixed "
                         "across re-runs for reproducibility.")
    args = ap.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY is not set.")

    random.seed(args.seed)
    client = anthropic.Anthropic()
    rows = [
        json.loads(line)
        for line in Path(args.responses).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]

    out_path = Path(args.out)
    tally = {"base": 0, "finetune": 0, "tie": 0}
    with out_path.open("w", encoding="utf-8") as f:
        for i, r in enumerate(rows, 1):
            base_is_a = random.random() < 0.5
            # Judge the VISIBLE answer (content with any <think> block
            # stripped) so neither model is flattered by where it reasons.
            resp_a = r["base"]["visible"] if base_is_a else r["finetune"]["visible"]
            resp_b = r["finetune"]["visible"] if base_is_a else r["base"]["visible"]

            verdict = judge(client, args.model, r, resp_a, resp_b)

            base_key, ft_key = ("A", "B") if base_is_a else ("B", "A")
            winner = verdict["winner"]
            if winner == "tie":
                winner_model = "tie"
            elif winner == base_key:
                winner_model = "base"
            else:
                winner_model = "finetune"
            tally[winner_model] += 1

            f.write(json.dumps({
                "id": r["id"],
                "category": r["category"],
                "base_position": base_key,
                "winner": winner_model,
                "base_scores": verdict[base_key],
                "finetune_scores": verdict[ft_key],
                "rationale": verdict.get("rationale", ""),
            }) + "\n")
            print(f"[{i}/{len(rows)}] {r['id']:<20} winner={winner_model}")

    print(f"\nTally  fine-tune={tally['finetune']}  base={tally['base']}  tie={tally['tie']}")
    print(f"Wrote {len(rows)} judgements -> {out_path}")


if __name__ == "__main__":
    main()
