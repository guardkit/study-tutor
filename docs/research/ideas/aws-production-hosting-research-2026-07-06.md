# AWS Production Hosting for the Fine-Tuned Tutor — Research Findings

**Status:** Research complete 2026-07-06. All load-bearing claims verified against live official
AWS/HF docs on 2026-07-06 (multi-agent research with independent adversarial verification; every
verdict below was CONFIRMED unless marked otherwise).
**Supersedes-in-part:** DEC-07 (decisions-log-2026-04-17) and [ADR-ARCH-006](../../architecture/decisions/ADR-ARCH-006-dual-inference-path-ollama-bedrock.md)
Bedrock Custom Model Import assumptions — see §2. ASSUM-007 (phase-0-validation: "Bedrock CMI
supports Gemma 4 natively in eu-west-2") is now **resolved NEGATIVE**.
**Consumed by:** a future ADR-ARCH-006 revision, an AWS-hosting scope/design doc, and an
executable deployment runbook (§7–8).

---

## 1. What we would be hosting (verified artifact facts)

| Fact | Value | Source |
|---|---|---|
| Base model | `unsloth/gemma-4-26B-A4B-it` — Gemma 4 MoE, ~27B total / ~4B active. ("31B Dense" in DEC-07/ADR-006/licensing.md is stale and wrong) | eval runbook "Model identities" + adapter_config.json |
| Fine-tune | LoRA r16 (Unsloth + TRL SFT), checkpoint 2026-04-18 | agentic-dataset-factory HF-upload runbook |
| Cloud-ready artifact | `merged-16bit/` — 49 GB HF safetensors, 2 shards, "vLLM-ready" | HF-upload runbook (executed, verified) |
| GGUF | Q4_K_M 16.8 GB complete + proven under llama.cpp; **BF16 GGUF is unusable** (shard 1 missing) | HF-upload runbook |
| HF repos | `RichWoollcott/gcse-tutor-gemma4-26b-moe` (+`-GGUF`) — but eval runbook says `studytutor-gcse-26b-moe`. **Repo-id discrepancy: verify on the Hub before pinning** | upload runbook vs eval runbook |
| Chat template | Stock Gemma 4 GGUF template leaks `<|channel>` tokens (caused HTTP 500s in eval). Production uses custom `gemma4-tutor.jinja`. **Any cloud host must carry the fix** | RESULTS-base-vs-finetune-2026-05-18 |
| License | **Unresolved conflict**: writeup says Apache 2.0; licensing.md says Gemma Terms of Use and claims weights are *not* distributed (contradicted by the executed HF upload). Resolve before any hosting/distribution decision | licensing.md vs technical-writeup §3/§11 |
| Serving today | llama-swap `:9000`, model `gemma4-tutor`, Q4_K_M, ctx 32768, ttl 1800, ~17 GB resident | dgx-spark live config 2026-07-05 |

## 2. Bedrock Custom Model Import — NOT VIABLE (verdict confirmed ×3)

Three independent, individually-fatal reasons (official docs, fetched 2026-07-06):

1. **Architecture:** CMI's supported list is Mistral, Mixtral, Flan(T5), Llama 2–3.3+Mllama,
   GPTBigCode, Qwen2/2.5/3 (incl. Qwen3MoeForCausalLM), GPT-OSS. **No Gemma of any generation.**
   Import auto-detects architecture from `config.json` and rejects unsupported ones. Additionally
   CMI caps max positional embeddings at 128K; Gemma 4 26B-A4B is a 256K-context model.
   <https://docs.aws.amazon.com/bedrock/latest/userguide/model-customization-import-model.html>
2. **Region:** CMI exists only in us-east-1/2, us-west-2, eu-central-1 (Frankfurt). **No eu-west-2.**
3. **No roadmap signal:** 2025–26 CMI additions were Qwen and GPT-OSS; no Gemma announcement.

Adjacent fact: **stock** Gemma 4 26B-A4B has been natively on Bedrock since 2026-06-10
(serverless `bedrock-mantle` OpenAI-compatible endpoint, $0.13/$0.40 per 1M tokens US,
$0.16/$0.48 Frankfurt, not in London) — **inference of Google's weights only, no custom-weight
path**. Relevant to §6b below.

CMI's economics were exactly what we wanted (scale-to-zero after 5 idle minutes, per-minute CMU
billing) — the only route to them would be re-fine-tuning onto a supported base
(Qwen3-30B-A3B MoE is the closest analogue), and even then Frankfurt, not London.

## 3. SageMaker — viable but the expensive managed path

- **Container:** classic LMI is too old (V20 bundles vLLM 0.15.1; Gemma 4 needs ≥0.19). Use AWS's
  **native vLLM DLC** `vllm:0.24.0-gpu-py312-cu130-ubuntu22.04-sagemaker` (July 2026).
  TensorRT-LLM lists Gemma 4 but has open bugs on L4 (#14942) — vLLM is the path.
- **Format:** HF safetensors from S3 (the 49 GB merged-16bit). GGUF on vLLM is "highly
  experimental" — not a production path. Keep GGUF for GB10/EC2-llama.cpp routes.
- **Instances:** eu-west-2 SageMaker has **no ml.g6e**. London cheapest fit: **ml.g6.12xlarge**
  (4×L4, 96 GB, BF16 TP=4) **$7.30/hr**. Frankfurt: **ml.g6e.2xlarge** (1×L40S 48 GB) **$3.50/hr**
  with an FP8 quant (~26 GB, e.g. llm-compressor). GPU endpoint quotas default to **0** — file the
  Service Quotas increase early.
- **Scale-to-zero:** works (inference components, MinInstanceCount=0) but requests **fail** during
  the ~6–12 min scale-up and scale-in takes ~25 min. For predictable evening use, the right
  pattern is **scheduled scaling** (Application Auto Scaling cron on DesiredCopyCount: 0→1 before
  study time, 1→0 at night) — zero perceived cold start, billed only for the window.

## 4. The sleeper options (cheaper than SageMaker)

- **EC2 g6.xlarge (London) + llama.cpp/llama-swap + EventBridge stop/start — recommended default.**
  $1.0216/hr on-demand (spot $0.34); the existing Q4_K_M GGUF + llama-swap config port
  **unchanged** (zero model-porting risk, and preserves quant parity with what Lilymay uses daily —
  the 2026-05-18 eval shows quantisation changes behaviour). Stopped instance costs only EBS.
  ~1–2 min wake. You own patching/TLS/auth. If a bigger quant is ever wanted, **G7e** (96 GB
  Blackwell) has been in London since May 2026 ($3.36/hr, spot ~$1.84).
- **HF Inference Endpoints — best managed scale-to-zero, two caveats.** AWS eu-west-1 (Ireland —
  EU, not UK) or us-east-1. L4 $0.80/hr, L40S $1.80/hr, per-minute billing, scale-to-zero after
  ~15 min idle. **llama.cpp GGUF engine out of the box** — our exact artifact deploys as-is.
  Caveats: cold starts return 502 (client needs retry/"warming up" UX; `X-Scale-Up-Timeout` header
  can hold requests), and weights live on the HF Hub, not in our AWS account.
- Also checked: Bedrock Marketplace BYO-endpoint (**ineligible** — "can't change the model
  artifacts from the base model"); JumpStart (has stock Gemma 4 26B-A4B since Apr 2026 — useful
  reference config, but BYO fine-tune collapses into the plain SageMaker path); ECS Managed
  Instances (lighter-ops middle ground, GPU list tops out at 24 GB in London); no GPU serverless
  exists on AWS (Lambda: no GPUs; SageMaker Serverless: no GPUs); G6f fractional (≤12 GB) too small.

## 5. Cost comparison (~2 h/day ≈ 61 h/mo, on-demand, ex-VAT)

| Path | Region | ~Monthly | Residency | Ops burden |
|---|---|---|---|---|
| EC2 g6.xlarge + llama.cpp (stop/start) | London | **$70–75** (spot ~$30) | UK | self-managed |
| HF Inference Endpoints L4 (GGUF) | Ireland | **~$49** | EU | managed |
| SageMaker ml.g6e.2xlarge FP8 (scheduled) | Frankfurt | ~$213 | EU | managed |
| SageMaker ml.g6.12xlarge BF16 (scheduled) | London | ~$445 | UK | managed |
| Bedrock serverless **stock** Gemma 4 (tokens) | Frankfurt | ~$1–5 | EU | none (no fine-tune) |
| Bedrock CMI | — | not viable | — | — |
| 24/7 anything GPU | — | $2.5k–6.6k | — | uneconomic |

## 6. Decision points the scope/design doc must resolve

a. **Residency ADR.** ADR-ARCH-015 is *UK on-device* residency. Any cloud host — even London —
   is a posture change needing a new ADR; Ireland/Frankfurt options need explicit sign-off that
   EU-adequate ≠ UK-resident is acceptable for a minor's tutoring transcripts.
b. **Fine-tune vs stock.** The 2026-05-18 eval preferred the *base* model 15/16 single-turn; the
   fine-tune wins Socratic stance + `<think>` visibility. Token-priced stock Gemma 4 on Bedrock
   (~$1–5/mo at our usage) vs $50–450/mo GPU hosting for the fine-tune is a real product decision,
   not an infra one. If the Socratic stance is the product, GPU hosting stands; if a strong system
   prompt on stock 26B-A4B closes the gap, the cheapest path wins. Worth a small eval before
   committing spend.
c. **License** (§1) — resolve Apache-2.0-vs-Gemma-ToU before hosting weights off-premises.
d. **HF repo-id** discrepancy (§1) — verify on the Hub before pinning in any runbook.
e. **Quant parity** — a cloud re-host at BF16/FP8 behaves differently from the Q4_K_M the student
   uses daily; pick one canonical serving quant or accept the drift knowingly.

## 7. Executable-runbook applicability — YES, with three extensions

The house pattern (dgx-spark/RUNBOOK-CONVENTIONS.md) transfers well: PINS → region/account/
image-digest/S3-URI/instance-type; inline gates → `aws … describe-* | jq` assertions; Phase 0
recon is *easier* on AWS (everything queryable); idempotent re-run works because gates read live
cloud state; base/overlay split maps to account-bootstrap → endpoint-standup → teardown. Needed
extensions, all consistent with house instincts (cf. the DF-005 anti-cloud-spend gate):

1. **Async waiter gates** — endpoint/import provisioning runs 10–60 min; the synchronous
   step→inline-check rhythm needs bounded poll/waiter gates + checkpoint-resume semantics.
2. **Cost-on-halt discipline** — "fail loudly and halt" strands billable resources on AWS. Add:
   billing-alarm pre-flight gate, per-phase billable-resource registry, halt-path teardown offer,
   and a gate-verified zero-orphan teardown phase.
3. **Operator predecessor runbook** — console-only steps (account/MFA/quota tickets) hoist out
   with paste-back evidence (precedent: W0-R operator runbook, http-dev-deploy attended Phase 6).

No prior AWS runbook exists in any repo — this would be greenfield for the pattern
(ADR-ARCH-006 is the only prior design intent, and its Bedrock branch is now dead per §2).

## 8. Suggested next steps

1. **ADR-ARCH-006 revision** (`/arch-refine`): record the Bedrock-CMI branch as infeasible
   (§2 evidence), replace with the §5 option set; keep the LLMClient env-var provider seam.
2. **Scope/design doc** for the chosen path once §6a–b are decided (owner decisions).
3. **Executable runbook skeleton**: `RUNBOOK-aws-account-bootstrap` (operator, paste-back) →
   `RUNBOOK-aws-tutor-hosting` (agent, overlay, with waiter-gates + cost discipline) →
   `RUNBOOK-aws-teardown` (gate-verified zero-orphan).
4. Cheapest de-risk spike: EC2 g6.xlarge, copy the GGUF + llama-swap config, EventBridge
   schedule — one evening, ~$5, proves the whole serving path before any bigger commitment.

---

*Generated 2026-07-06 from a multi-agent research pass (repo recon + live-web verification;
15 agents, all key claims independently adversarially verified against official sources).*
