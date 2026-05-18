# `scripts/eval/` — Base vs Fine-Tune Evaluation Harness

A small, reproducible A/B harness that quantifies what fine-tuning bought the
GCSE study tutor, by comparing the **base Gemma 4** model against the
**fine-tuned `gemma4-tutor`** on a fixed set of GCSE English tutoring prompts.

It is driven end-to-end by
[`docs/runbooks/RUNBOOK-base-vs-finetune-tutor-eval.md`](../../docs/runbooks/RUNBOOK-base-vs-finetune-tutor-eval.md)
— **run the runbook, not the scripts ad hoc.** The runbook covers serving the
base model, parity guarantees, and how to read the results.

## Files

| File | Role |
|---|---|
| `golden_set.jsonl` | 16 fixed GCSE English tutoring prompts across 8 behaviour categories, each with `expected_behaviours` / `red_flags`. Extend it freely — one JSON object per line. |
| `run_ab_eval.py` | Sends every golden prompt to both models under identical conditions; writes paired responses. |
| `score_deterministic.py` | No-LLM scoring: template-token leaks, `<think>` coverage, length, question-presence. |
| `judge_prepare.py` | Blinding step — turns paired responses into anonymised A/B pairs + a held-back key. |
| `judge_resolve.py` | Resolution step — applies the key to raw A/B verdicts, producing `judgements.jsonl`. |
| `judge_pairwise.py` | Optional API-driven judge (prepare→judge→resolve in one shot); for reproducing the eval without a Claude Code session. Needs `ANTHROPIC_API_KEY`. |
| `aggregate.py` | Combines the above into `results-table.md`, drop-in for the submission write-up §11. |
| `multiturn_scenarios.jsonl` | 3 scripted multi-turn tutoring sessions (5 student turns each). |
| `run_multiturn_eval.py` | Walks each scenario through both models; each builds its own side of the conversation. → `multiturn_transcripts.jsonl` |
| `multiturn_prepare.py` / `multiturn_resolve.py` | Blind-prepare and resolve+aggregate for holistic multi-turn session judging. |

## Two ways to judge

- **Claude Code session (default here):** `judge_prepare.py` → the session reads `blind_pairs.jsonl` and writes `raw_judgements.jsonl` → `judge_resolve.py`. No API key.
- **Automated / reproducible:** `judge_pairwise.py` alone, via the Anthropic API — so anyone cloning the repo can re-run it.

## Methodology — the parity rule

The comparison is only honest if the **only variable is the model weights**.
Both models therefore receive the *same* system prompt, the *same* greedy
decoding (`temperature 0`), the *same* prompts, and are served at the *same*
quantisation (Q4_K_M) on the *same* runtime family (llama.cpp). Giving the base
model no system prompt would measure "prompting + fine-tuning", not fine-tuning.

## Quick run

```bash
# 1. generate paired responses (both models via llama-swap)
uv run python scripts/eval/run_ab_eval.py \
  --system-prompt /opt/llama-swap/models/gemma4-tutor/system-prompt.txt \
  --base-endpoint http://localhost:9000/v1 --base-model gemma4-base \
  --finetune-endpoint http://localhost:9000/v1 --finetune-model gemma4-tutor

# 2. deterministic scoring
uv run python scripts/eval/score_deterministic.py

# 3. blind judging
uv run python scripts/eval/judge_prepare.py     # -> blind_pairs.jsonl + blind_key.json
#    ...judge each pair -> raw_judgements.jsonl...
uv run python scripts/eval/judge_resolve.py     # -> judgements.jsonl

# 4. aggregate into a submission-ready table
uv run python scripts/eval/aggregate.py
```

Artefacts land in `docs/runbooks/evidence/base-vs-finetune-eval/`.
