# Runbook: Base vs Fine-Tuned Tutor — Evaluation

**Status:** Executed 2026-05-18 — base model preferred **15/16** single-turn and **2/3 (1 tie)** multi-turn; the fine-tune leads only on Socratic stance (multi-turn) and reasoning visibility. Full write-up in [`RESULTS-base-vs-finetune-tutor-eval-2026-05-18.md`](RESULTS-base-vs-finetune-tutor-eval-2026-05-18.md). Authored for the Gemma 4 Good Hackathon submission (Evaluation section).
**Purpose:** Produce a defensible, reproducible side-by-side evaluation showing what fine-tuning bought the GCSE study tutor — base **Gemma 4 26B-A4B** vs the fine-tuned **`gemma4-tutor`** — and emit a results table that drops straight into [`technical-writeup.md`](../submission/technical-writeup.md) §11.
**Machine:** Dell DGX Spark GB10 (`promaxgb10-41b1`), 128 GB unified memory — the box already serving the tutor.
**Execution model:** This runbook is designed to be executed *by a Claude Code session* (the house pattern for runbooks here). The Phase 5 judge step is performed by that session directly — no external API key is required.
**Predecessors:**
- [`agentic-dataset-factory/domains/architect-agent/RUNBOOK-architect-fine-tune.md`](../../../agentic-dataset-factory/domains/architect-agent/RUNBOOK-architect-fine-tune.md) — produced the fine-tune; its Phase 6 ("What's next") explicitly names *build a golden set* and *run the eval harness* as the open items this runbook closes.
- [`RUNBOOK-open-webui-tutor-access.md`](../research/ideas/RUNBOOK-open-webui-tutor-access.md) — established that `gemma4-tutor` is served by llama-swap at `http://localhost:9000/v1` and recovered the canonical system prompt to `/opt/llama-swap/models/gemma4-tutor/system-prompt.txt`.
**Harness:** [`scripts/eval/`](../../scripts/eval/) — `golden_set.jsonl`, `multiturn_scenarios.jsonl` + the single-turn and multi-turn eval scripts, committed alongside this runbook (and suitable for the public submission repo as evaluation evidence).
**Expected duration:** ~60–90 min. Lean path (16-prompt golden set, single judge pass) is the quick-reference at the bottom.

---

> ### Model identities (confirmed 2026-05-18)
> | Role | Identity |
> |---|---|
> | **Base** | [`unsloth/gemma-4-26B-A4B-it`](https://huggingface.co/unsloth/gemma-4-26B-A4B-it) — Gemma 4 26B-A4B, Mixture-of-Experts, 27B total params. GGUF: `unsloth/gemma-4-26B-A4B-it-GGUF` (`UD-Q4_K_M`). |
> | **Fine-tune (merged 16-bit)** | [`RichWoollcott/studytutor-gcse-26b-moe`](https://huggingface.co/RichWoollcott/studytutor-gcse-26b-moe) — LoRA rank 16, Unsloth + TRL SFT |
> | **Fine-tune (GGUF)** | [`RichWoollcott/gcse-tutor-gemma4-26b-moe-GGUF`](https://huggingface.co/RichWoollcott/gcse-tutor-gemma4-26b-moe-GGUF) — Q4_K_M; this is what llama-swap serves as `gemma4-tutor`. |
>
> The submission plan originally said "Gemma 4 31B Dense" — wrong on both count and architecture, now corrected in `gemma4-hackathon-submission-plan.md` and `technical-writeup.md`. It is **26B-A4B MoE**. Older ADRs and `docs/history/` files still carry the stale name; they are historical records, left as-is.

---

## What this runbook produces

Artefacts under `docs/runbooks/evidence/base-vs-finetune-eval/`:

| Artefact | What it is |
|---|---|
| `responses.jsonl` | Every golden prompt answered by *both* models under identical conditions. The raw evidence. |
| `deterministic.json` | No-LLM metrics: template-token leaks, `<think>` coverage, length, question-presence. |
| `blind_pairs.jsonl` / `blind_key.json` | Anonymised A/B pairs for judging + the held-back base/fine-tune mapping. |
| `raw_judgements.jsonl` | The judge's per-pair verdicts, written against the *blind* A/B labels. |
| `judgements.jsonl` | The resolved verdicts (A/B mapped back to base/fine-tune) with 6-dimension scores. |
| `results-table.md` | The aggregated, submission-ready markdown table. |

Plus a `RESULTS-…` companion file (Phase 7) recording the run, per the template in [`templates/RESULTS-template.md`](templates/RESULTS-template.md).

---

## Methodology: the parity rule (read this first — it is load-bearing)

The comparison is only honest if **the only variable is the model weights.**
Everything else is held identical between the two models:

| Held identical | Value | Why it matters |
|---|---|---|
| System prompt | The recovered `gemma4-tutor` system prompt, byte-for-byte | Giving the base model *no* prompt would measure "prompting + fine-tuning". Giving it the *same* prompt isolates fine-tuning. The honest question is: *with the same instructions, how much better are the trained weights?* |
| Decoding | `temperature 0` (greedy), `max_tokens 1024` | Greedy decoding makes every response reproducible — re-running the harness yields the same text, so the eval is auditable. |
| Runtime | The **same** `llama-server` binary | Both models are registered in llama-swap and served by the identical `llama.cpp` `llama-server` build — same kernel, same sampler, same host. |
| Quantisation | ~4-bit K-M GGUF | Fine-tune: standard `Q4_K_M`. Base: Unsloth-Dynamic `UD-Q4_K_M`. Both are 4-bit K-M; UD is a per-layer-optimised variant. Close, not identical — recorded as an honest parity caveat in RESULTS. |
| Prompts | `scripts/eval/golden_set.jsonl`, fixed | A frozen golden set means the result is stable and the eval can be re-run after any future re-train. |

The **chat template is deliberately *not* forced to match.** The fine-tune uses its custom `gemma4-tutor.jinja` (the leak-fix template); the base uses its own stock Gemma 4 template (the GGUF's embedded one). That is correct — each model is evaluated as it would actually be served. We *measure* template-token leaks (Phase 4) rather than papering over them.

Single-turn by design: each golden prompt is a realistic mid-conversation student message (a wrong answer, a weak paragraph, a plea for the answer). One tutor reply per prompt reveals the tutoring behaviour without the divergence problems of scripted multi-turn A/B. Multi-turn is a documented stretch (Phase 8).

---

## Phase 0: Pre-flight

### 0.1 Confirm llama-swap is serving the fine-tuned tutor

```bash
curl -s --max-time 30 http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma4-tutor","max_tokens":32,
       "messages":[{"role":"user","content":"Hello"}]}' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('routed model:', d.get('model'))
print('PASS' if d.get('model') == 'gemma4-tutor' else 'FAIL: wrong model / routing broken')
"
```

Expected: `routed model: gemma4-tutor`. If it fails, see [`RUNBOOK-open-webui-tutor-access.md`](../research/ideas/RUNBOOK-open-webui-tutor-access.md) Phase 0.1.

### 0.2 Confirm the shared system prompt exists

Both models will be fed this file. If missing, recover it as the Open WebUI tutor runbook Phase 0.2 does (dominant system prompt from the training data).

```bash
SYS=/opt/llama-swap/models/gemma4-tutor/system-prompt.txt
[ -f "$SYS" ] && echo "PASS: system prompt present ($(wc -c < "$SYS") bytes)" \
              || echo "FAIL: recover it — see RUNBOOK-open-webui-tutor-access.md Phase 0.2"
```

Expected: ~811 bytes.

### 0.3 Confirm the llama-swap config is writable and the service is user-mode

The base model is registered as a second llama-swap model. That needs a writable config and a service this session can restart without `sudo`.

```bash
test -w /opt/llama-swap/config/config.yaml && echo "PASS: config writable" || echo "FAIL: config not writable"
test -w /opt/llama-swap/models && echo "PASS: models dir writable" || echo "FAIL: models dir not writable"
systemctl --user is-active llama-swap.service && echo "PASS: llama-swap is a user service" \
  || echo "FAIL: not a user service — restart will need sudo"
df -h /opt | tail -1   # need ~20 GB free for the base GGUF
```

### 0.4 Pre-flight gate

| Check | Expected |
|---|---|
| 0.1 llama-swap serves `gemma4-tutor` | PASS |
| 0.2 shared system prompt present | PASS (~811 bytes) |
| 0.3 config + models dir writable, user-mode service, ≥20 GB free | PASS |

All PASS → Phase 1. The judge (Phase 5) is performed by the Claude Code session executing this runbook, so no API-key check is needed.

---

## Phase 1: Register the base model in llama-swap

The base is served by the **same `llama-server` binary** as the fine-tune — the tightest possible runtime parity. This costs one config block and one service restart.

### 1.1 Confirm the base against the fine-tune's adapter config

The base is `unsloth/gemma-4-26B-A4B-it`. Sanity-check it against what the fine-tune recorded so RESULTS cites first-party evidence:

```bash
FT_OUT=$(ls -d ~/fine-tuning/output/gcse-tutor-gemma4-26b-moe* 2>/dev/null | head -1)
python3 -c "
import json, glob
cfg = glob.glob('$FT_OUT/**/adapter_config.json', recursive=True)
print('base_model_name_or_path:', json.load(open(cfg[0])).get('base_model_name_or_path')) if cfg \
  else print('adapter_config.json not local — HF card RichWoollcott/studytutor-gcse-26b-moe is the source of truth')
"
```

Expected: `unsloth/gemma-4-26B-A4B-it` (or a local path resolving to it).

### 1.2 Download the base GGUF

```bash
mkdir -p /opt/llama-swap/models/gemma4-base
hf download unsloth/gemma-4-26B-A4B-it-GGUF \
  gemma-4-26B-A4B-it-UD-Q4_K_M.gguf \
  --local-dir /opt/llama-swap/models/gemma4-base
ls -lh /opt/llama-swap/models/gemma4-base/*.gguf
```

Expected: a ~15–16 GB `.gguf` file. (`hf` is the Hugging Face CLI at `~/.local/bin/hf`.)

### 1.3 Add the `gemma4-base` block to the llama-swap config

Append a model block mirroring `gemma4-tutor` — **with two deliberate differences**: it points at the base GGUF, and it carries **no `--chat-template-file`** so the base uses its own stock Gemma 4 template (see the parity rule). Insert under the `models:` map in `/opt/llama-swap/config/config.yaml`:

```yaml
  "gemma4-base":
    cmd: >
      /home/richardwoollcott/llama.cpp/build/bin/llama-server
      --port ${PORT}
      --host 0.0.0.0
      --model /opt/llama-swap/models/gemma4-base/gemma-4-26B-A4B-it-UD-Q4_K_M.gguf
      --alias gemma4-base
      --ctx-size 32768
      --batch-size 2048
      --ubatch-size 2048
      --threads 16
      -ngl 999
      --no-mmap
      --flash-attn on
      --jinja
      --temp 0.7
      --top-p 0.9
      -np 1
    checkEndpoint: /health
    ttl: 3600
    concurrencyLimit: 2
```

`ttl: 3600` lets the base worker unload an hour after the eval rather than squatting GPU memory permanently. Do **not** add it to the `groups`/`preload` sets — it is served on demand only.

### 1.4 Restart llama-swap and verify both models

```bash
systemctl --user restart llama-swap.service
sleep 5
curl -s --max-time 10 http://localhost:9000/v1/models \
  | python3 -c "import sys,json; ids=[m['id'] for m in json.load(sys.stdin)['data']]; \
print('models:', ids); print('PASS' if {'gemma4-tutor','gemma4-base'} <= set(ids) else 'FAIL')"
```

> **EXEC NOTE — brief tutor interruption.** The restart bounces every llama-swap worker for a few seconds; workers reload on demand. Harmless between demos, but do not run Phase 1.4 *during* a live tutor session.

### 1.5 Base smoke test + GPU headroom

```bash
curl -s --max-time 180 http://localhost:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gemma4-base","max_tokens":64,
       "messages":[{"role":"user","content":"Hello"}]}' \
  | python3 -c "import sys,json; d=json.load(sys.stdin); print('routed:', d.get('model')); \
print('PASS' if d['choices'][0]['message']['content'] else 'FAIL')"

nvidia-smi --query-gpu=memory.used,memory.total --format=csv
```

Expected: a brief reply, `routed: gemma4-base`, and combined GPU memory comfortably under ~100 GB. The harness calls one model then the other per item, so only one of the two 26B workers needs to be hot at a time — but llama-swap's `concurrencyLimit` and TTL may keep both resident; if memory climbs past ~100 GB, stop non-essential workers (graphiti, workhorse) per the fine-tune runbook Phase 0.5.

---

## Phase 2: Review the golden set

The harness ships a 16-prompt golden set at [`scripts/eval/golden_set.jsonl`](../../scripts/eval/golden_set.jsonl) — 8 behaviour categories × 2 prompts. Each line carries `expected_behaviours` and `red_flags`.

| Category | What it probes |
|---|---|
| `socratic` | Does the tutor guide, or just hand over the answer? |
| `essay_feedback` | AO-aligned critique of a weak student paragraph, without rewriting it |
| `quote_analysis` | Drawing analysis out of the student; authentic quotations |
| `misconception` | Correcting a wrong belief gently and pedagogically |
| `exam_technique` | AQA mark-scheme / assessment-objective fluency |
| `scaffolding` | Grade-7-targeted, age-appropriate explanation |
| `boundary` | Staying in role; refusing to do the work for the student |
| `tone` | Warmth and encouragement with a discouraged student |

```bash
wc -l scripts/eval/golden_set.jsonl        # expect 16
```

24–32 prompts gives the judge-preference percentages more weight (Phase 8); 16 is the deadline-day floor.

---

## Phase 3: Generate the paired responses

One call to each model per golden prompt — identical system prompt, identical greedy decoding. Both endpoints are llama-swap (`:9000`).

```bash
uv run python scripts/eval/run_ab_eval.py \
  --system-prompt /opt/llama-swap/models/gemma4-tutor/system-prompt.txt \
  --base-endpoint     http://localhost:9000/v1 --base-model     gemma4-base \
  --finetune-endpoint http://localhost:9000/v1 --finetune-model gemma4-tutor \
  --temperature 0.0 --max-tokens 1024
```

Output: `responses.jsonl` — 16 lines, each with `base` and `finetune` blocks. The script exits non-zero on the first transport error; a clean `Wrote 16 paired responses` is the gate. Eyeball lengths to confirm neither model returned empty:

```bash
python3 -c "
import json
for l in open('docs/runbooks/evidence/base-vs-finetune-eval/responses.jsonl'):
    r = json.loads(l)
    print(r['id'], '| base', len(r['base']['content']), 'ch | ft', len(r['finetune']['content']), 'ch')
"
```

---

## Phase 4: Deterministic scoring (no LLM)

```bash
uv run python scripts/eval/score_deterministic.py
```

| Metric | Expectation |
|---|---|
| `leak_total` (fine-tune) | **0.** Non-zero means the `gemma4-tutor.jinja` leak fix regressed — investigate before trusting the rest. |
| `think_block_pct` | Fine-tune **high** (a trained behaviour), base **low**. A large gap is one of the cleanest fine-tuning signals. |
| `asks_question_pct` | Fine-tune expected higher (Socratic stance) — a *crude proxy*; the judge does the real assessment. |
| `mean_words` | Informational — flags if one model is systematically terse or rambling. |

Output: `deterministic.json`.

---

## Phase 5: Blind pairwise judging (performed by the Claude Code session)

The judge here is the **Claude Code session executing this runbook**. Judging is split into three steps so it stays honest: blinding, judging, then resolution.

### 5.1 Prepare blind pairs

```bash
uv run python scripts/eval/judge_prepare.py
```

Writes `blind_pairs.jsonl` (anonymised "Response A" / "Response B" pairs) and `blind_key.json` (the base/fine-tune position, held back).

### 5.2 Judge every pair

The executing session reads **`blind_pairs.jsonl`** and, for each pair, scores Response A and Response B and picks a winner — then appends one JSON object per pair to **`raw_judgements.jsonl`**:

```json
{"id": "socratic-01", "winner": "A",
 "A": {"socratic_stance": 4, "aqa_alignment": 3, "scaffolding": 4,
       "subject_accuracy": 5, "tone": 4, "reasoning_visibility": 2},
 "B": {"socratic_stance": 2, "aqa_alignment": 2, "scaffolding": 3,
       "subject_accuracy": 4, "tone": 3, "reasoning_visibility": 1},
 "rationale": "<= 2 sentences"}
```

**Rubric** — you are an experienced AQA GCSE English examiner. Score each response 1 (poor) – 5 (excellent) on every dimension:

- **`socratic_stance`** — guides with questions; never simply hands over the finished answer
- **`aqa_alignment`** — uses AQA assessment-objective framing (AO1/AO2/AO3) and exam-board vocabulary
- **`scaffolding`** — builds on the student's attempt; pitched for a 15-year-old targeting grade 7
- **`subject_accuracy`** — correct about the set texts (Macbeth, An Inspector Calls, Power & Conflict anthology); quotations authentic
- **`tone`** — warm and encouraging, especially with a discouraged student
- **`reasoning_visibility`** — makes its pedagogical reasoning visible

Pick `winner` = `"A"`, `"B"`, or `"tie"`. **Integrity rules:** judge every pair before running 5.3; do not open `blind_key.json` until `raw_judgements.jsonl` is complete; if you re-judge, re-judge the whole set and replace the file wholesale.

### 5.3 Resolve

```bash
uv run python scripts/eval/judge_resolve.py
```

Applies `blind_key.json`, writes `judgements.jsonl`, prints the `fine-tune / base / tie` tally.

> **Reproducible alternative.** `scripts/eval/judge_pairwise.py` does prepare→judge→resolve in one shot via the Anthropic API (`ANTHROPIC_API_KEY` required). It exists so anyone cloning the public repo can re-run the eval without a Claude Code session — it is *not* needed for this run.

---

## Phase 6: Aggregate into the submission table

```bash
uv run python scripts/eval/aggregate.py
```

Output: `results-table.md` — head-to-head win rate, mean dimension scores with deltas, per-category win counts, deterministic checks.

**Human spot-check (required — do not skip).** Read 3–4 full pairs in `responses.jsonl`, ideally including one scored as a base win or tie. Confirm the fine-tune's wins are *real tutoring quality*, not length or formatting artefacts.

---

## Phase 7: Decision gate and write-up

### 7.1 Record the run

Copy [`templates/RESULTS-template.md`](templates/RESULTS-template.md) to `RESULTS-base-vs-finetune-tutor-eval-2026-05-18.md` and fill in: base identity (Phase 1.1), the base GGUF + quant, golden-set size, that the judge was the Claude Code session, and the aggregated numbers.

### 7.2 Decision matrix

| Outcome | Reading | Action |
|---|---|---|
| Fine-tune wins a clear majority; positive deltas on `socratic_stance` / `aqa_alignment` / `reasoning_visibility` | The expected, defensible result — fine-tuning taught tutoring *behaviour* | Put `results-table.md` into write-up §11; lead with the `<think>` coverage gap. |
| Fine-tune wins but margins thin | Real but modest effect | Report honestly; consider expanding the golden set (Phase 8). |
| Base wins, or parity | Either base+prompt is already strong, or a parity flaw | **Stop.** Re-check parity: same system prompt? Inspect `responses.jsonl` for degenerate base output inflating the win for the wrong reason. |
| `leak_total` (fine-tune) > 0 | Template-leak regression | Flag it; the leak fix needs re-checking before the demo. Add to `known-issues.md`. |

### 7.3 What to claim in the submission

**Accurate, defensible framing:**

> "On a fixed 16-prompt GCSE English golden set, with both models given an
> identical system prompt and greedy decoding and served by the same
> `llama-server` binary at ~4-bit K-M quantisation, a blind
> position-randomised pairwise judge preferred the fine-tuned tutor in N of
> 16 head-to-heads. The largest gains were in Socratic stance and AQA
> assessment-objective alignment; the fine-tune emitted structured `<think>`
> reasoning on X% of prompts versus Y% for the base."

**Do not claim** a statistically significant result from 16 prompts — call it a *directional* evaluation. **Do not** drop the parity caveats (including the `Q4_K_M` vs `UD-Q4_K_M` note); they are what make the number trustworthy.

---

## Phase 8: Multi-turn evaluation (executed 2026-05-18)

The fine-tune is trained on multi-turn dialogue, so a single-turn eval
under-represents it. A multi-turn harness was added and run:

- `scripts/eval/multiturn_scenarios.jsonl` — 3 scripted tutoring sessions (5 student turns each).
- `run_multiturn_eval.py` — walks each scenario through both models; each builds its own side of the conversation from a fixed student script. → `multiturn_transcripts.jsonl`
- `multiturn_prepare.py` → blind A/B pairs; the session judges whole sessions holistically into `multiturn_raw_judgements.jsonl`; `multiturn_resolve.py` → `multiturn_results-table.md`.

Outcome: base preferred 2/3, 1 tie, fine-tune 0 — but the fine-tune wins
Socratic stance (+1.00) and reasoning visibility (+2.00). The gap narrowed
versus single-turn but did not reverse. See the RESULTS file.

### Further stretch (not executed)

| Stretch | Effort | Value |
|---|---|---|
| Expand the golden set to 24–32 prompts | ~20 min | Firmer win-rate percentages |
| Quote-fidelity check against `data/chroma` | ~30 min | Verifies `subject_accuracy` quotes are authentic primary text |
| Re-judge with a second seed | ~10 min | Confirms the result is not seed-sensitive |

---

## Quick-reference (lean path, ~60 min)

```bash
# --- Phase 0-1: register the base in llama-swap ---
hf download unsloth/gemma-4-26B-A4B-it-GGUF gemma-4-26B-A4B-it-UD-Q4_K_M.gguf \
  --local-dir /opt/llama-swap/models/gemma4-base
#   ...add the gemma4-base block to /opt/llama-swap/config/config.yaml (Phase 1.3)...
systemctl --user restart llama-swap.service && sleep 5

# --- Phase 3-4: generate + deterministic score ---
uv run python scripts/eval/run_ab_eval.py \
  --system-prompt /opt/llama-swap/models/gemma4-tutor/system-prompt.txt \
  --base-endpoint http://localhost:9000/v1 --base-model gemma4-base \
  --finetune-endpoint http://localhost:9000/v1 --finetune-model gemma4-tutor \
  --temperature 0.0
uv run python scripts/eval/score_deterministic.py

# --- Phase 5: blind judge (the session does the judging in 5.2) ---
uv run python scripts/eval/judge_prepare.py
#   ...session reads blind_pairs.jsonl, writes raw_judgements.jsonl...
uv run python scripts/eval/judge_resolve.py

# --- Phase 6: aggregate ---
uv run python scripts/eval/aggregate.py
cat docs/runbooks/evidence/base-vs-finetune-eval/results-table.md
```

---

## Appendix A: Why llama-swap for the base, not Ollama or vLLM

Serving the base through llama-swap means it runs on the **identical `llama-server` binary** as the fine-tune — strictly tighter parity than Ollama (a different llama.cpp build/runtime) or vLLM (bf16, a quantisation mismatch against the Q4 fine-tune). Ollama remains a valid alternative if editing the llama-swap config is undesirable: `ollama pull hf.co/unsloth/gemma-4-26B-A4B-it-GGUF:Q4_K_M`, then point `run_ab_eval.py --base-endpoint http://localhost:11434/v1`.

## Appendix B: Fallback — GGUF-convert the cached base checkpoint

If the Unsloth base GGUF were ever unavailable, the fine-tune's own base download is cached under `~/.cache/huggingface/hub/` in HF format. Convert + quantise with `llama.cpp` (`convert_hf_to_gguf.py` → `llama-quantize` to `Q4_K_M`), then register it exactly as Phase 1.3. ~30 min; see the fine-tune runbook Phase 5.3 and guardkit's `RUNBOOK-INFRA-ORCHESTRATION.md` §8.

## Cross-references

- Fine-tune runbook (produced the model; Phase 6 names this eval as the open item): [`agentic-dataset-factory/domains/architect-agent/RUNBOOK-architect-fine-tune.md`](../../../agentic-dataset-factory/domains/architect-agent/RUNBOOK-architect-fine-tune.md)
- Tutor serving + system-prompt recovery: [`RUNBOOK-open-webui-tutor-access.md`](../research/ideas/RUNBOOK-open-webui-tutor-access.md)
- Submission write-up (§11 Evaluation is the target): [`docs/submission/technical-writeup.md`](../submission/technical-writeup.md)
- Harness: [`scripts/eval/`](../../scripts/eval/)

*Prepared: 2026-05-18 — for the Gemma 4 Good Hackathon submission (deadline 2026-05-18 23:59 UTC).*
