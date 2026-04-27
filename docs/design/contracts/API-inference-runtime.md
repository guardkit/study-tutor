# API Contract — Inference Runtime

**Bounded context:** Inference Runtime (anti-corruption layer)
**Phase:** P0 (live for `local`; stubbed for `bedrock`)
**Status:** Accepted — design captures live behaviour in `src/study_tutor/llm/client.py`
**Generated:** 2026-04-26 by `/system-design` (bias-to-defaults, Phase 0 scope)

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

## 4. Configuration surface (env vars)

The Inference Runtime is configured exclusively via environment variables, read **at call time** (never at module import — SR-03 invariant).

| Variable | Consumer | Default | Notes |
|---|---|---|---|
| `AGENT_MODELS__REASONING_MODEL` | `_default_player_model()` | `local` | Provider label; routed through `LLMClient.generate` |
| `OLLAMA_BASE_URL` | `_generate_ollama` | `http://localhost:11434` | Tailscale GB10 endpoint in deployed config |
| `OLLAMA_MODEL` | `_generate_ollama` | `gcse-tutor-gemma4-moe:latest` | Fine-tuned tutor model |
| `OLLAMA_NUM_PREDICT` | `_resolve_num_predict()` | `2048` | Token ceiling per generation; tuned in TASK-PO02F-002 |
| `BEDROCK_MODEL_ARN` | (P1) `_generate_bedrock` | placeholder | Set by FEAT-PO-004 |

**Hygiene:** no real-looking provider keys in `.env.example` — `<placeholder>` literals only (SR-06 / CC-06).

## 5. Invariants

1. **Provider resolved at the factory, not at the handler.** Every call-site reads `params.get("player_model") or _default_player_model()`. (CC-03 / SR-03 / `domain-model.md §6.2`.)
2. **Every named provider is in `[providers]` extra.** A missing extra is a build failure, not a runtime failure. (CC-04 / SR-04.)
3. **`LLMClient.generate(...)` is the sole public interface.** Upstream code never constructs `ChatOllama`, `ChatBedrock`, or `httpx.Client` directly.
4. **Provider-specific knowledge stays inside this context.** ARNs, URLs, retry semantics, and model IDs do not leak into Tutoring or MCP Transport.
5. **Errors normalise to `LLMProviderError`.** Provider-specific exceptions (`httpx.HTTPError`, `boto3` ClientError, etc.) are caught and re-raised as `LLMProviderError` so upstream contexts handle one error type.

## 6. Sync vs async

`LLMClient.generate` is **synchronous**. Callers (e.g. `MCPAdapter.tutor_turn`) wrap the call in `asyncio.to_thread(...)` so the async MCP framework isn't blocked by httpx. Phase 1 may introduce an async-native variant once deepagents 0.5.3+ AsyncSubAgent is in play (CC-12), but the sync interface remains the contract.

## 7. Conformance tests

| Test | Location |
|---|---|
| `test_provider_resolution.py` (SR-03 — env-var resolution at call time, never at import) | `tests/unit/llm/test_provider_resolution.py` |
| Provider-extra import smoke (SR-04 — every label in extra is importable) | recommended addition |

## 8. Out of scope

- **Streaming responses.** P0 is non-streaming (`stream: false`); streaming deferred to P1+.
- **Token-level cost accounting.** Deferred — single-user posture (ADR-ARCH-014).
- **Prompt caching.** Deferred (ADR-ARCH-011); irrelevant for Ollama, considered for Bedrock in P1+ if cost matters.
- **Retries / circuit breakers.** Deferred; failure surfaces as `LLMProviderError` to the caller.

## 9. Open questions for downstream phases

1. **P1 — message-shape API.** When the Coach lands, `generate(prompt, system)` may not be enough; a `messages: list[ChatMessage]` overload may be required. Consider via `/design-refine` once Coach criteria scoring is wired.
2. **P1 — Bedrock latency profile.** FEAT-PO-004's smoke test should record observed Bedrock latency vs Ollama. If Bedrock p95 > 30s, `tutor_turn` needs reclassification (currently sync).
3. **P1+ — Gemini consolidation.** Graphiti's vLLM/Gemini path is a separate provider abstraction. If a use case emerges for the Player/Coach to use the same vLLM endpoint Graphiti uses, evaluate consolidating both behind `LLMClient`.
