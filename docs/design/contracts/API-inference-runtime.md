# API Contract — Inference Runtime

**Bounded context:** Inference Runtime (anti-corruption layer)
**Phase:** P0 (live for `local`; stubbed for `bedrock`)
**Status:** Accepted — design captures live behaviour in `src/study_tutor/llm/client.py`
**Generated:** 2026-04-26 by `/system-design` (bias-to-defaults, Phase 0 scope)
**Refreshed:** 2026-04-27 (PM late) by `/system-design --focus="Inference Runtime"` to absorb [ADR-ARCH-018](../../architecture/decisions/ADR-ARCH-018-extend-cross-cutting-concerns-sr08-sr09.md) (CC-14 — runtime LLM parameters explicit; SR-09 origin in [openwebui-rag-empirical-findings-2026-04-23.md §2 Finding 4](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md)). DDR-004 captured. Closes the last outstanding stale-reference item from the 2026-04-27 AM/PM Tutoring + MCP refreshes.

---

## 1. Consumer model

Inference Runtime exposes **no external protocol surface**. By design (`domain-model.md §6.3`) all provider-specific knowledge stays inside this context, and upstream contexts speak only the `LLMClient.invoke(...)` Python interface.

| Consumer | Surface | Phase |
|---|---|---|
| Tutoring (`MCPAdapter._warm_up`, `tutor_turn`) | `LLMClient` Python class | P0 |
| Coach (P1) — possibly different provider than Player | `LLMClient` Python class | P1 |
| Tests | `LLMClient` Python class | P0 |

**Not consumers of this context:**
- Open WebUI / LiteLLM / OpenAI proxies — they speak directly to Ollama/Bedrock; they do not pass through `LLMClient`.
- Graphiti's entity-extraction LLM (vLLM on GB10 per the live `.guardkit/graphiti.yaml`, formerly Gemini per ADR-ARCH-007) — managed by Graphiti, not by `LLMClient`. Two separate provider abstractions exist by design.

## 2. Public Python interface

```python
class LLMClient:
    """Provider-agnostic LLM client. Sync, string-in / string-out.

    Construct per call site:
        client = LLMClient(provider=_default_player_model())
    Never store at module level (SR-03).
    """

    def __init__(self, provider: str) -> None: ...

    def generate(self, prompt: str, system: str | None = None) -> str: ...
```

**Helper:**

```python
def _default_player_model() -> str:
    """Return the provider from AGENT_MODELS__REASONING_MODEL (default: 'local').
    Read at call time (SR-03 invariant)."""
```

**Error class:**

```python
class LLMProviderError(RuntimeError):
    """Raised when the configured provider is misconfigured or unreachable."""
```

The contract is the **call signature + error class + provider matrix below**. P1 may grow `generate` to a `messages: list[ChatMessage]` shape if the Coach needs multi-turn context; `generate(prompt, system)` is the P0 commitment.

## 3. Provider matrix

Authoritative table — every provider listed here:
- has its label routed in `LLMClient.generate`,
- appears in `pyproject.toml [providers]` extra (CC-04 / SR-04), and
- is documented in the README quick-start.

| Provider label | Endpoint resolver | Default model | Status (P0) | ADR |
|---|---|---|---|---|
| `local` | `OLLAMA_BASE_URL` env (default `http://localhost:11434`) | `OLLAMA_MODEL` env (default `gcse-tutor-gemma4-moe:latest`) | **live, primary** | ADR-ARCH-006 |
| `bedrock` | AWS Bedrock Custom Model Import | `BEDROCK_MODEL_ARN` env | **stub — `NotImplementedError`** until FEAT-PO-004 | ADR-ARCH-006 |
| `openai` | OpenAI API | TBD | declared (extra installed); not wired | — |
| `anthropic` | Anthropic API | TBD | declared (extra installed); not wired | — |
| `gemini` | Google Gemini API | TBD | declared (extra installed); not wired (Graphiti's Gemini path is independent) | — |

**Adding a provider** is a contract change requiring `/design-refine` and a new entry in the `[providers]` extra.

## 4. Configuration surface

Inference Runtime configuration lives in **two distinct loci** with different ownership:

### 4.1 Client-resident (env vars, read at call time)

These are the runtime parameters that `LLMClient` reads and applies per request. Read **at call time** (never at module import — SR-03 invariant).

| Variable | Consumer | Default | Notes |
|---|---|---|---|
| `AGENT_MODELS__REASONING_MODEL` | `_default_player_model()` | `local` | Provider label; routed through `LLMClient.generate` |
| `OLLAMA_BASE_URL` | `_generate_ollama` | `http://localhost:11434` | Tailscale GB10 endpoint in deployed config |
| `OLLAMA_MODEL` | `_generate_ollama` | `gcse-tutor-gemma4-moe:latest` | Fine-tuned tutor model |
| `OLLAMA_NUM_PREDICT` | `_resolve_num_predict()` | `2048` | **Per-request** token ceiling, sent in `options.num_predict`; tuned in TASK-PO02F-002. Operator override; not the CC-14 floor (see §5 / DDR-004). |
| `BEDROCK_MODEL_ARN` | (P1) `_generate_bedrock` | placeholder | Set by FEAT-PO-004 |

**Hygiene:** no real-looking provider keys in `.env.example` — `<placeholder>` literals only (SR-06 / CC-06).

### 4.2 Modelfile-resident (CC-14 — Ollama only)

Per CC-14 / SR-09 (origin: [openwebui-rag-empirical-findings-2026-04-23.md §2 Finding 4](../../research/ideas/openwebui-rag-empirical-findings-2026-04-23.md)), the runtime context window and the Modelfile-default generation budget are owned by the Ollama Modelfile, **not** by `LLMClient`. The client honours these by trusting the loaded model — it does not set `options.num_ctx` per request, and does not override the Modelfile-default `num_predict` except via `OLLAMA_NUM_PREDICT` for tuning.

| Modelfile parameter | Required (CC-14) | Reference value | Why Modelfile-resident (not client) |
|---|---|---|---|
| `num_ctx` | **≥ 16384** for RAG-enabled personas | `PARAMETER num_ctx 16384` | Set when the model is loaded into memory; not a per-request tuning knob. Persona-specific (RAG vs no-RAG). See DDR-004. |
| `num_predict` | **≥ 1500** for tutoring responses | `PARAMETER num_predict 1500` | Sets a minimum **default** generation budget at load time; per-request override is the client's `OLLAMA_NUM_PREDICT` ceiling (default 2048, also ≥ 1500). |

**Conformance gate:** smoke test (see §7) asserts both via `ollama show <model> --modelfile | grep PARAMETER` *and* via runner-log inspection of the line `llama_new_context_with_model: n_ctx = N` from a real inference call. Regression trips the test.

**Out of CC-14 today:** non-Ollama providers (`bedrock`, `openai`, `anthropic`, `gemini`) — context-size semantics are managed by their respective deployment surfaces (model ID, request parameters, model-import config). Per-provider CC-14 conformance is an open question (§9).

## 5. Invariants

1. **Provider resolved at the factory, not at the handler.** Every call-site reads `params.get("player_model") or _default_player_model()`. (CC-03 / SR-03 / `domain-model.md §6.2`.)
2. **Every named provider is in `[providers]` extra.** A missing extra is a build failure, not a runtime failure. (CC-04 / SR-04.)
3. **`LLMClient.generate(...)` is the sole public interface.** Upstream code never constructs `ChatOllama`, `ChatBedrock`, or `httpx.Client` directly.
4. **Provider-specific knowledge stays inside this context.** ARNs, URLs, retry semantics, and model IDs do not leak into Tutoring or MCP Transport.
5. **Errors normalise to `LLMProviderError`.** Provider-specific exceptions (`httpx.HTTPError`, `boto3` ClientError, etc.) are caught and re-raised as `LLMProviderError` so upstream contexts handle one error type.
6. **Modelfile owns `num_ctx`; CC-14 is enforced by smoke test (DDR-004).** `LLMClient` does not set `options.num_ctx` per request. The Ollama Modelfile is the single source of truth for the runtime context window (`PARAMETER num_ctx ≥ 16384` for RAG-enabled personas) and for the Modelfile-default generation budget (`PARAMETER num_predict ≥ 1500`). Conformance is asserted via `ollama show <model> --modelfile | grep PARAMETER` and runner-log inspection of `llama_new_context_with_model: n_ctx = N` (see §7). This invariant is the **source of truth** for the cross-context pointer in [`DM-tutoring.md §6`](../models/DM-tutoring.md) — Tutoring inherits CC-14 through the `LLMClient` boundary; no Tutoring-side equivalent.
7. **`options.num_predict` is set explicitly on every Ollama request.** `_generate_ollama` always populates the request payload's `options.num_predict` from `_resolve_num_predict()` (`client.py:83, 89`); it never relies on the Modelfile default at the request layer. `OLLAMA_NUM_PREDICT` is an operator-tunable per-request **ceiling** (default 2048; ≥ 1500 today). It is *not* the CC-14 floor — the Modelfile default is. Operators tuning `OLLAMA_NUM_PREDICT` below 1500 explicitly accept the truncation risk that CC-14 was introduced to prevent.

## 6. Sync vs async

`LLMClient.generate` is **synchronous**. Callers (e.g. `MCPAdapter.tutor_turn`) wrap the call in `asyncio.to_thread(...)` so the async MCP framework isn't blocked by httpx. Phase 1 may introduce an async-native variant once deepagents 0.5.3+ AsyncSubAgent is in play (CC-12), but the sync interface remains the contract.

## 7. Conformance tests

### 7.1 In place / today

| Test | Surface | Location |
|---|---|---|
| `test_provider_resolution.py` | SR-03 — env-var resolution at call time, never at import | `tests/unit/llm/test_provider_resolution.py` |

### 7.2 Recommended additions

| Test | Surface | Notes |
|---|---|---|
| Provider-extra import smoke | SR-04 / CC-04 — every label in `[providers]` extra is importable | Recommended addition; trips when a label is added to the matrix without an extra entry. |
| **CC-14 Modelfile-parameter smoke** | I-IR6 / CC-14 — `num_ctx ≥ 16384`, `num_predict ≥ 1500` | Two-part assertion per ADR-ARCH-018: (a) `ollama show $OLLAMA_MODEL --modelfile \| grep PARAMETER` returns lines for both params at or above the thresholds; (b) on a real inference call, the Ollama runner log contains `llama_new_context_with_model: n_ctx = N` with `N >= 16384`. Run on every Modelfile change (per CC-14: cheap relative to the silent-truncation regression class it prevents). The runner-log half closes the loophole where `ollama show` reports a value the runner did not actually load. |
| **CC-14 client-payload smoke** | I-IR7 — `options.num_predict` is always present in the Ollama request payload | Patches `httpx.post` and asserts the captured payload has a positive integer `options.num_predict` from `_resolve_num_predict()`. Trips if a refactor drops the explicit per-request override. |

## 8. Out of scope

- **Streaming responses.** P0 is non-streaming (`stream: false`); streaming deferred to P1+.
- **Token-level cost accounting.** Deferred — single-user posture (ADR-ARCH-014).
- **Prompt caching.** Deferred (ADR-ARCH-011); irrelevant for Ollama, considered for Bedrock in P1+ if cost matters.
- **Retries / circuit breakers.** Deferred; failure surfaces as `LLMProviderError` to the caller.
- **Per-request `num_ctx` from the client.** Explicitly out of scope per **DDR-004**. The Modelfile is the source of truth for `num_ctx`; `LLMClient` does not set it on the request payload. Re-evaluate only if a use case emerges for per-request context-window resizing that the Modelfile cannot serve.
- **CC-14 conformance for non-Ollama providers.** CC-14 is Ollama-specific today (ADR-ARCH-018 cites Ollama Modelfile parameters). Bedrock / OpenAI / Anthropic / Gemini context-size semantics differ; per-provider extension is captured in §9.

## 9. Open questions for downstream phases

1. **P1 — message-shape API.** When the Coach lands, `generate(prompt, system)` may not be enough; a `messages: list[ChatMessage]` overload may be required. Consider via `/design-refine` once Coach criteria scoring is wired.
2. **P1 — Bedrock latency profile.** FEAT-PO-004's smoke test should record observed Bedrock latency vs Ollama. If Bedrock p95 > 30s, `tutor_turn` needs reclassification (currently sync).
3. **P1+ — Gemini consolidation.** Graphiti's vLLM/Gemini path is a separate provider abstraction. If a use case emerges for the Player/Coach to use the same vLLM endpoint Graphiti uses, evaluate consolidating both behind `LLMClient`.
4. **CC-14 extension to non-Ollama providers.** Bedrock Custom Model Import has its own context-size posture (set at import time); OpenAI / Anthropic / Gemini expose context windows as model-ID metadata, not Modelfile params. When a non-`local` provider goes live, decide whether to:
    - extend CC-14 with provider-specific conformance gates (e.g. assert `BEDROCK_MODEL_ARN` points at an import with the expected context size), or
    - keep CC-14 narrowly Ollama-scoped and document the per-provider posture separately.
   Prefer the former if a single provider matrix can carry the rule; the latter if provider semantics diverge too much.
