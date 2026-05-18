#!/usr/bin/env python3
"""A/B generation harness: run the GCSE-tutor golden set against two model
endpoints (base Gemma 4 vs the fine-tuned tutor) under identical conditions.

Parity is the whole point of this harness — see
``docs/runbooks/RUNBOOK-base-vs-finetune-tutor-eval.md``. Both models receive
the SAME system prompt, the SAME decoding parameters and the SAME prompts.
The only variable is the model weights.

Reasoning-channel asymmetry (handled here): Gemma 4 is a thinking model.
  * the fine-tune emits reasoning INLINE in ``content`` as ``<think>...</think>``
  * the base routes reasoning to the separate ``reasoning_content`` field
So each response is captured as three things:
  * ``content``           — the raw assistant message content
  * ``reasoning_content`` — the model's reasoning channel (base path)
  * ``visible``           — what the student actually reads: ``content`` with
                            any ``<think>`` block stripped
Downstream scoring/judging compares ``visible`` so neither model is unfairly
credited or penalised for *where* it puts its reasoning.
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
    """Return the visible answer — ``content`` minus any ``<think>`` block."""
    return _THINK.sub("", text).strip()


def load_jsonl(path: str) -> list[dict]:
    items: list[dict] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            items.append(json.loads(line))
    return items


def generate(
    endpoint: str,
    model: str,
    system_prompt: str,
    user_message: str,
    *,
    temperature: float,
    max_tokens: int,
    timeout: float,
    retries: int = 3,
) -> dict:
    """One chat-completions round-trip against an OpenAI-compatible server.

    Retries transient failures (5xx, transport errors) with backoff — a
    cold model swap inside llama-swap can briefly 500.
    """
    payload = {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    }
    t0 = time.time()
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            resp = httpx.post(
                f"{endpoint.rstrip('/')}/chat/completions", json=payload, timeout=timeout
            )
            resp.raise_for_status()
            break
        except (httpx.HTTPStatusError, httpx.TransportError) as exc:
            last_exc = exc
            if attempt == retries:
                raise
            wait = 5 * attempt
            print(f"    transient error ({exc!r}) — retry {attempt}/{retries - 1} in {wait}s")
            time.sleep(wait)
    data = resp.json()
    choice = data["choices"][0]
    message = choice["message"]
    content = message.get("content") or ""
    reasoning = message.get("reasoning_content") or ""
    return {
        "content": content,
        "reasoning_content": reasoning,
        "visible": strip_think(content),
        "finish_reason": choice.get("finish_reason"),
        "routed_model": data.get("model"),
        "latency_s": round(time.time() - t0, 2),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--golden", default="scripts/eval/golden_set.jsonl")
    ap.add_argument(
        "--system-prompt",
        required=True,
        help="Path to the tutor system-prompt.txt — fed to BOTH models.",
    )
    ap.add_argument("--base-endpoint", default="http://localhost:9000/v1")
    ap.add_argument("--base-model", default="gemma4-base")
    ap.add_argument("--finetune-endpoint", default="http://localhost:9000/v1")
    ap.add_argument("--finetune-model", default="gemma4-tutor")
    ap.add_argument("--temperature", type=float, default=0.0)
    ap.add_argument("--max-tokens", type=int, default=2048,
                    help="Generous — reasoning + answer share this budget.")
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument(
        "--out",
        default="docs/runbooks/evidence/base-vs-finetune-eval/responses.jsonl",
    )
    args = ap.parse_args()

    system_prompt = Path(args.system_prompt).read_text(encoding="utf-8").strip()
    golden = load_jsonl(args.golden)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Golden items     : {len(golden)}")
    print(f"System prompt    : {len(system_prompt)} bytes (identical for both models)")
    print(f"Decoding         : temperature={args.temperature}, max_tokens={args.max_tokens}")
    print(f"BASE             : {args.base_model} @ {args.base_endpoint}")
    print(f"FINE-TUNE        : {args.finetune_model} @ {args.finetune_endpoint}\n")

    # Generate one model fully before the other. llama-swap keeps a single
    # 26B worker hot per pass, so the whole run costs ONE model swap instead
    # of one per item — far faster and avoids cold-swap 500s.
    def run_pass(label: str, endpoint: str, model: str) -> dict[str, dict]:
        print(f"--- {label} pass: {model} @ {endpoint} ---")
        out: dict[str, dict] = {}
        for i, item in enumerate(golden, 1):
            try:
                r = generate(
                    endpoint, model, system_prompt, item["prompt"],
                    temperature=args.temperature, max_tokens=args.max_tokens,
                    timeout=args.timeout,
                )
            except Exception as exc:  # noqa: BLE001 — fail fast; operator fixes infra
                print(f"  ERROR on {item['id']}: {exc}", file=sys.stderr)
                sys.exit(1)
            out[item["id"]] = r
            print(f"  [{i}/{len(golden)}] {item['id']:<20} {r['latency_s']}s "
                  f"({len(r['visible'])} ch visible)")
        return out

    base_results = run_pass("BASE", args.base_endpoint, args.base_model)
    ft_results = run_pass("FINE-TUNE", args.finetune_endpoint, args.finetune_model)

    with out_path.open("w", encoding="utf-8") as f:
        for item in golden:
            f.write(json.dumps({
                **item,
                "base": base_results[item["id"]],
                "finetune": ft_results[item["id"]],
            }) + "\n")

    print(f"\nWrote {len(golden)} paired responses -> {out_path}")


if __name__ == "__main__":
    main()
