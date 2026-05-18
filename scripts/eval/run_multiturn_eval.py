#!/usr/bin/env python3
"""Multi-turn A/B harness: walk each scripted tutoring scenario through both
models and capture the full session transcript per model.

Why multi-turn matters here: the fine-tune was trained on multi-turn
Player-Coach dialogue, so it takes short conversational turns by design. A
single-turn eval (run_ab_eval.py) judges one reply as a whole lesson and
structurally favours a verbose single-shot model. This harness gives each
model the SAME fixed sequence of student messages and lets it build its own
side of the conversation — the setting the fine-tune was actually built for.

Parity: identical system prompt, identical greedy decoding, identical student
script. Each model accumulates its own assistant turns (the VISIBLE answer,
<think> stripped — chat history does not normally carry the thinking).

Input : multiturn_scenarios.jsonl
Output: multiturn_transcripts.jsonl
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

import httpx

_THINK = re.compile(r"<think>.*?</think>", re.S)


def strip_think(text: str) -> str:
    return _THINK.sub("", text).strip()


def generate(endpoint, model, messages, *, temperature, max_tokens, timeout, retries=3):
    payload = {"model": model, "temperature": temperature,
               "max_tokens": max_tokens, "messages": messages}
    for attempt in range(1, retries + 1):
        try:
            resp = httpx.post(f"{endpoint.rstrip('/')}/chat/completions",
                              json=payload, timeout=timeout)
            resp.raise_for_status()
            break
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            if attempt == retries:
                raise
            wait = 5 * attempt
            print(f"      transient error ({exc!r}) — retry in {wait}s")
            time.sleep(wait)
    m = resp.json()["choices"][0]["message"]
    content = m.get("content") or ""
    return {"content": content, "visible": strip_think(content),
            "reasoning_content": m.get("reasoning_content") or ""}


def run_scenario(endpoint, model, system_prompt, student_turns, **kw) -> list[dict]:
    """Walk one scenario; return a list of {student, tutor_visible, ...} turns."""
    messages = [{"role": "system", "content": system_prompt}]
    transcript = []
    for student in student_turns:
        messages.append({"role": "user", "content": student})
        t0 = time.time()
        r = generate(endpoint, model, messages, **kw)
        # Feed the VISIBLE answer back as history (thinking is not retained).
        messages.append({"role": "assistant", "content": r["visible"]})
        transcript.append({
            "student": student,
            "tutor_visible": r["visible"],
            "tutor_reasoning": r["reasoning_content"]
                               or (_THINK.search(r["content"]).group(0)
                                   if "<think>" in r["content"] else ""),
            "latency_s": round(time.time() - t0, 2),
        })
    return transcript


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenarios", default="scripts/eval/multiturn_scenarios.jsonl")
    ap.add_argument("--system-prompt", required=True)
    ap.add_argument("--base-endpoint", default="http://localhost:9000/v1")
    ap.add_argument("--base-model", default="gemma4-base")
    ap.add_argument("--finetune-endpoint", default="http://localhost:9000/v1")
    ap.add_argument("--finetune-model", default="gemma4-tutor")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=2048)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--out",
                    default="docs/runbooks/evidence/base-vs-finetune-eval/multiturn_transcripts.jsonl")
    args = ap.parse_args()

    system_prompt = Path(args.system_prompt).read_text(encoding="utf-8").strip()
    scenarios = [json.loads(l) for l in Path(args.scenarios).read_text().splitlines() if l.strip()]
    kw = dict(temperature=args.temperature, max_tokens=args.max_tokens, timeout=args.timeout)

    print(f"Scenarios: {len(scenarios)}  |  system prompt: {len(system_prompt)} bytes\n")

    def run_pass(label, endpoint, model):
        print(f"--- {label} pass: {model} ---")
        out = {}
        for sc in scenarios:
            try:
                tr = run_scenario(endpoint, model, system_prompt, sc["student_turns"], **kw)
            except Exception as exc:  # noqa: BLE001
                print(f"  ERROR on {sc['id']}: {exc}", file=sys.stderr)
                sys.exit(1)
            out[sc["id"]] = tr
            print(f"  {sc['id']:<26} {len(tr)} turns "
                  f"({sum(t['latency_s'] for t in tr):.0f}s total)")
        return out

    base = run_pass("BASE", args.base_endpoint, args.base_model)
    ft = run_pass("FINE-TUNE", args.finetune_endpoint, args.finetune_model)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for sc in scenarios:
            f.write(json.dumps({
                "id": sc["id"], "text": sc["text"], "summary": sc["summary"],
                "student_turns": sc["student_turns"],
                "base_transcript": base[sc["id"]],
                "finetune_transcript": ft[sc["id"]],
            }) + "\n")
    print(f"\nWrote {len(scenarios)} scenario transcripts -> {out_path}")


if __name__ == "__main__":
    main()
