# ADR-ARCH-006 — Dual inference path: Ollama (primary) + Bedrock (validation)

## Status

Accepted

**Date:** 2026-04-18
**Phase:** Phase 0
**Related:** ADR-ARCH-004, DEC-07, CC-03

## Context

GB10 (the on-premise Jetson running Ollama) is the only machine
capable of serving the fine-tuned Gemma 4 31B model locally. DEC-07
specifies that GB10 must also run three sequential training workloads
in Phases 1–2:

1. Study-tutor training-dataset expansion (additional subjects).
2. Study-tutor re-fine-tune.
3. Architect-agent training + fine-tune for DDD Southwest (16 May).

Training and inference at 31B scale cannot run concurrently on GB10.
The fine-tuned tutor must remain available to Lilymay daily, and must
be demonstrably working during demo week (12–16 May). Without an
alternative inference path, demo week collides with training.

AWS Bedrock Custom Model Import supports Gemma 4 31B natively,
scale-to-zero, with a cold start of 30–60s. Memory flagged Bedrock
as a Phase 2 deliverable; DEC-07 moves it earlier.

Per CC-03 / SR-03, provider selection must be env-var driven at the
`LLMClient` factory, not hard-coded in handlers.

## Decision

Study Tutor supports two primary inference paths through a single
`LLMClient` (anti-corruption layer in the Inference Runtime context):

1. **`local` (Phase 0 default):** Ollama on GB10 via Tailscale.
   Existing, low-latency (~5–8s per 200 tokens).
2. **`bedrock` (Phase 0 validation; Phase 1+ demo-week primary):**
   AWS Bedrock Custom Model Import. Scale-to-zero; 30–60s cold start;
   per-call latency within 5× of Ollama.

Selection is via `AGENT_MODELS__REASONING_MODEL={local|bedrock|...}`.
No handler hard-codes a provider (CC-03 / SR-03 — LES1 PMEV/CRMV
evidence).

Additional providers (`openai`, `anthropic`, `gemini`) are declared
in `[providers]` (CC-04 / SR-04) but are not on the P0 critical path;
they are reserved for Coach / fallback.

Phase 0 validation test (FEAT-PO-004, Tuesday 22 April):
`tutor_turn` returns a coherent response via `bedrock` within 5× the
Ollama latency.

## Alternatives considered

- **Ollama-only; pause training during demo week.** Rejected.
  Fragile; architect-agent training schedule conflicts with demo
  timing; no fallback if GB10 has a hardware issue during week 3.
- **Bedrock-only.** Rejected. Lilymay's daily use has been on Ollama
  for months; zero-cost baseline; don't introduce unnecessary cost
  and dependency.
- **vLLM / SGLang on a separate GPU.** Rejected. No separate GPU
  available. Would add hardware procurement to the critical path.
- **Two fine-tuned models (one for GB10, one for Bedrock) with quality
  variance accepted.** Rejected. Bedrock imports the existing
  merged-16bit weights directly; one model, two hosts.

## Consequences

**Positive:**
- Decouples demo week from GB10 training schedule.
- Validates a scale-to-zero path that's cheap for Lilymay's
  post-hackathon use (~$1.50–3/session).
- CC-03/SR-03 compliance exercised early by having two real providers.

**Negative:**
- Two inference paths = two failure modes during the Phase 0
  clean-machine walkthrough. Accepted — Bedrock is marked "validation"
  in Phase 0; Ollama is primary.
- AWS account + IAM setup required as a prerequisite. Documented in
  Phase 0 build-plan §Prerequisites.
- Bedrock cold-start (30–60s) is visible on the first call of a demo
  session. Mitigated by warming Bedrock ~2 min before each demo
  recording.

## References

- DEC-07 in `docs/research/ideas/decisions-log-2026-04-17.md`
- Phase 0 scope FEAT-PO-004.
