# DDR-004 — `num_ctx` is owned by the Modelfile, not by `LLMClient`; CC-14 conformance is a smoke test

## Status

Accepted

**Date:** 2026-04-27
**Phase:** Phase 0 (rule); Phase 1 (operative as RAG-enabled personas + smoke test land)
**Bounded context:** Inference Runtime
**Related:** [ADR-ARCH-018](../../architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) (CC-14 — runtime LLM parameters explicit; SR-09 origin), [openwebui-rag-empirical-findings-2026-04-23.md §2 Finding 4 + §3a](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md), [API-inference-runtime.md §4 / §5 / §7](../contracts/API-inference-runtime.md), [DM-inference-runtime.md §4 / §5 (I-IR7, I-IR8)](../models/DM-inference-runtime.md), [DM-tutoring.md §6 cross-context pointer](../models/DM-tutoring.md).

## Context

[ADR-ARCH-018](../../architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) promoted SR-09 to **CC-14**: every Ollama Modelfile used by the tutor must set explicit `num_ctx` (≥ 16384 for RAG-enabled personas) and `num_predict` (≥ 1500 for tutoring responses), with smoke-test assertions via `ollama show <model> --modelfile | grep PARAMETER` and via the runner-log line `llama_new_context_with_model: n_ctx = N`.

The empirical anchor is the 23 April 2026 OpenWebUI RAG session ([openwebui-rag-empirical-findings-2026-04-23.md §2 Finding 4](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md)): Ollama's default `num_ctx = 2048` silently truncated tutoring responses mid-sentence whenever RAG was active (system prompt ~600 tokens + RAG template ~100 tokens + 6 retrieved chunks at 512 tokens ≈ 3000 tokens — generation budget exhausted before completion, with no error). The fix landed in the deployed Modelfile as `PARAMETER num_ctx 16384` + `PARAMETER num_predict 1500`.

ADR-ARCH-018 settles **what** must hold (≥ 16384 / ≥ 1500, asserted) but does not settle **where** the rule lives in the codebase. The Inference Runtime contract has to choose between two designs:

1. **Client-resident:** push `num_ctx` into the request payload from `LLMClient._generate_ollama`, mirroring the existing per-request `options.num_predict` pathway (`client.py:89`). The client becomes the enforcer; the smoke test is auxiliary.
2. **Modelfile-resident:** leave `num_ctx` to the Modelfile, with the smoke test as the **primary** conformance gate. The client trusts the loaded model and continues to set only `options.num_predict` per request.

Today's `client.py` is shape (2) — `options.num_ctx` is not in the payload, only `options.num_predict` is. CC-14 forces the choice to be explicit rather than incidental.

## Decision

**`LLMClient` does not set `options.num_ctx` per request. The Ollama Modelfile is the single source of truth for the runtime context window. CC-14 conformance is enforced by a smoke test, not by per-request enforcement in the client.**

Concretely:

- `_generate_ollama` (`client.py:78–107`) continues to omit `num_ctx` from the request payload's `options` block. Only `num_predict` is set per request.
- The Modelfile (`PARAMETER num_ctx N`, `PARAMETER num_predict N`) is the canonical locus for both parameters.
- The CC-14 smoke test runs against the loaded model — both halves are required:
  - **`ollama show <model> --modelfile | grep PARAMETER`** confirms the Modelfile literal at the threshold.
  - **Runner-log inspection** of `llama_new_context_with_model: n_ctx = N` from a real inference call confirms the runner actually loaded that value.
- `OLLAMA_NUM_PREDICT` (env var, default 2048) remains the per-request operator override for `num_predict`. It is not the CC-14 floor — the Modelfile default is. Operators tuning below 1500 explicitly accept the truncation risk that CC-14 was introduced to prevent.
- Codified as **I-IR7** and **I-IR8** in [`DM-inference-runtime.md §5`](../models/DM-inference-runtime.md); the smoke test is recorded in [`API-inference-runtime.md §7.2`](../contracts/API-inference-runtime.md).

## Rationale

- **`num_ctx` is a per-model, model-load-time concern; `num_predict` is a per-request tuning knob.** The two parameters are not symmetric. `num_ctx` allocates KV-cache memory at load time and is fixed for the lifetime of the running model; setting it per request is at best wasteful and at worst inconsistent with what the runner has actually allocated. `num_predict` is a generation-budget ceiling per call. Pushing both into the request payload conflates two different lifecycles.
- **Persona split lives in the Modelfile, not in the client.** The deployed configuration ([§3e of openwebui-rag-empirical-findings](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md)) splits "GCSE Shakespeare Tutor" (no RAG) from "GCSE Modern Texts Tutor" (RAG mandatory) and a general fallback. RAG-enabled personas need `num_ctx ≥ 16384`; the Shakespeare persona does not. The persona-to-`num_ctx` mapping is a **deployment** decision (which Modelfile to load), not a request-time decision. Putting `num_ctx` in the client would either (a) require the client to know which persona it is talking to, or (b) force a single value across personas — both worse than the Modelfile staying authoritative.
- **The empirical failure mode is silent truncation.** Finding 4 establishes that `num_ctx` regressions surface as mid-word truncation with no error. A smoke-test gate at Modelfile-build time is the right shape: once asserted, it stays asserted until the Modelfile changes; the test is cheap to re-run; and the runner-log half closes the loophole where a build artefact diverges from what the runner uses. A runtime check from the client cannot detect the same failure because the client sees a string truncated by the runner — there is no error to catch.
- **Symmetry with `num_predict` resolution is an illusion.** `_resolve_num_predict()` (`client.py:31–44`) reads an env var and applies it as a per-request ceiling — a *capping* operation against the Modelfile default. There is no analogous capping operation for `num_ctx`: the runner has already allocated whatever the Modelfile said. The shapes look similar but have different semantics.
- **Non-Ollama providers don't have Modelfiles.** Bedrock Custom Model Import sets context size at import time (a model-ARN attribute); OpenAI / Anthropic / Gemini expose context windows as model-ID metadata. Putting `num_ctx` into `LLMClient` would force a per-provider switch with five non-overlapping shapes. Keeping `num_ctx` out of the client preserves the option to add per-provider CC-14 conformance gates without committing to a particular runtime locus today (open question, [API-inference-runtime.md §9 item 4](../contracts/API-inference-runtime.md)).

## Alternatives considered

- **Push `num_ctx` into `LLMClient._generate_ollama`'s `options` payload.** Rejected.
  - Duplicates the Modelfile setting and risks drift (Modelfile says 16384, client says 8192 → which wins? The runner uses what was loaded at startup, so the client setting is effectively a no-op or worse, a misleading log artefact).
  - Couples per-persona context budgets to client code; the persona split documented in [§3e of openwebui-rag-empirical-findings](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) becomes harder to maintain.
  - Does not actually catch silent-truncation regressions — the runner has already loaded `num_ctx` by the time the client sends a request.

- **Add a unified `_resolve_inference_params()` that returns both `num_ctx` and `num_predict` from env vars.** Rejected. Same drift / coupling risk as above; treats the two parameters as if they had the same lifecycle when they do not.

- **Defer the rule and rely on per-PR review.** Rejected. The 78.98s `add_episode` median made CC-13 non-negotiable for analogous reasons; the silent-truncation failure mode for `num_ctx` is the same shape — a regression class that produces incorrect outputs without errors. A recorded rule + smoke test is cheaper than re-litigating per PR.

- **Bind the rule to ADR-ARCH-018 alone.** Rejected. ADR-ARCH-018 is an *architectural* commitment about *which parameters must be explicit*. The Modelfile-vs-client split is a *design-level* artefact about *where the explicitness lives in the codebase*. Conflating them obscures the chain of evidence and makes the design-level rule invisible to anyone reading only `docs/design/`.

## Consequences

**Positive:**
- `LLMClient` stays simple — one provider matrix, one per-request tuning knob (`num_predict`), no client-side enforcement of model-load-time concerns.
- The Modelfile remains the single locus for persona-specific context-window decisions; persona split is a deployment-time choice, not a code-time choice.
- The CC-14 smoke test is the cheapest possible conformance gate — once green, it stays green until the Modelfile changes; the runner-log half makes it decisive (catches "Modelfile changed but runner did not reload" failures).
- Aligns with the Inference Runtime's anti-corruption-layer role (`ARCHITECTURE.md §3`): provider-specific knowledge (Modelfile vs request-payload semantics) stays inside the context.

**Negative:**
- A regressed Modelfile is silently catastrophic *unless* the smoke test runs. The CC-14 smoke test must run on every Modelfile change (CI or pre-commit hook); a stale or skipped test re-introduces the silent-truncation class. Mitigated by recording the test recommendation in [`API-inference-runtime.md §7.2`](../contracts/API-inference-runtime.md) and flagging it as outstanding in [§5 of `openwebui-rag-empirical-findings`](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) (*"Add smoke-test for `num_ctx` runtime value (guard against Modelfile regression)"*).
- Extending CC-14 to non-Ollama providers requires per-provider conformance work; there is no single implementation point in `LLMClient` to extend. Recorded as an open question in [API-inference-runtime.md §9 item 4](../contracts/API-inference-runtime.md).
- The client-payload shape (no `num_ctx`) and the Modelfile shape (canonical `num_ctx`) are easy to confuse on first read. Mitigated by I-IR7 / I-IR8 spelling out both halves and by the §4.1 / §4.2 split in the API contract and data model.

## Affected artefacts

- [`docs/design/contracts/API-inference-runtime.md §4 (split into 4.1 client-resident / 4.2 Modelfile-resident) + §5 (invariants 6, 7) + §7.2 (CC-14 smoke test row) + §8 (per-request `num_ctx` out of scope) + §9 (non-Ollama-provider extension)`](../contracts/API-inference-runtime.md) — references this DDR.
- [`docs/design/models/DM-inference-runtime.md §4 (4.1 / 4.2 split) + §5 (I-IR7, I-IR8) + §6 (Modelfile relationship row) + §8 (per-request `num_ctx` out of scope)`](../models/DM-inference-runtime.md) — encodes the rule and its enforcement; **source of truth** for the cross-context CC-14 pointer in [`DM-tutoring.md §6`](../models/DM-tutoring.md).
- [`src/study_tutor/llm/client.py` lines 78–107 (`_generate_ollama`)](../../../src/study_tutor/llm/client.py) — the request-payload shape that this DDR commits to (no `options.num_ctx`).
- The Modelfile of `gcse-tutor-gemma4-moe:latest` (and any future RAG-enabled persona Modelfile) — the canonical locus this DDR points at; not under version control in this repo today, but the deployed configuration is captured in [§3a of openwebui-rag-empirical-findings](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md).

## References

- [ADR-ARCH-018](../../architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) — CC-14 / SR-09 promotion to load-bearing cross-cutting concern.
- [openwebui-rag-empirical-findings-2026-04-23.md §2 Finding 4](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) — the silent-truncation failure mode CC-14 was introduced to prevent.
- [openwebui-rag-empirical-findings-2026-04-23.md §3a](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) — the deployed Modelfile (`PARAMETER num_ctx 16384`, `PARAMETER num_predict 1500`).
- [openwebui-rag-empirical-findings-2026-04-23.md §3e](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) — the persona split that depends on per-Modelfile `num_ctx`.
- [openwebui-rag-empirical-findings-2026-04-23.md §5 outstanding-this-week](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md) — "Add smoke-test for `num_ctx` runtime value" — this DDR is the design home for that test.
