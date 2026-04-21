"""LLM client with provider resolution (SR-03 locus).

Factory routes requests to the configured provider based on
``AGENT_MODELS__REASONING_MODEL``. Phase 0 wires the Ollama path
(GB10 over Tailscale) and stubs Bedrock.

Every MCP handler must resolve the provider at call time via
``_default_player_model()`` — never at module import. Hard-coding
``provider="local"`` or any other value anywhere in the code path
violates SR-03.
"""

from __future__ import annotations

import os

DEFAULT_PLAYER_MODEL = "local"
DEFAULT_OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_OLLAMA_MODEL = "gcse-tutor-gemma4-moe:latest"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 120.0
# Ollama's default num_predict is ~128 tokens — too small for GCSE essay
# scaffolds. Cap at 2048 to fit a full Intro/Body ×2/Conclusion plan;
# overridable via OLLAMA_NUM_PREDICT for tuning (see TASK-PO02F-002).
DEFAULT_OLLAMA_NUM_PREDICT = 2048


class LLMProviderError(RuntimeError):
    """Raised when the configured provider is misconfigured or unreachable."""


def _resolve_num_predict() -> int:
    """Return the Ollama ``num_predict`` ceiling.

    Reads ``OLLAMA_NUM_PREDICT`` at call time (SR-03). Falls back to
    ``DEFAULT_OLLAMA_NUM_PREDICT`` when unset or not a positive integer.
    """
    raw = os.environ.get("OLLAMA_NUM_PREDICT")
    if raw is None or raw == "":
        return DEFAULT_OLLAMA_NUM_PREDICT
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_OLLAMA_NUM_PREDICT
    return value if value > 0 else DEFAULT_OLLAMA_NUM_PREDICT


def _default_player_model() -> str:
    """Return the default player-model provider from the environment.

    Reads ``AGENT_MODELS__REASONING_MODEL`` at call time (SR-03).
    Falls back to ``"local"`` when unset.
    """
    return os.environ.get("AGENT_MODELS__REASONING_MODEL") or DEFAULT_PLAYER_MODEL


class LLMClient:
    """Provider-agnostic LLM client.

    Sync, string-in / string-out. Construct per call site
    (``LLMClient(provider=_default_player_model())``) — never module-level.
    """

    def __init__(self, provider: str) -> None:
        self.provider = provider

    def generate(self, prompt: str, system: str | None = None) -> str:
        if self.provider == "local":
            return self._generate_ollama(prompt, system)
        if self.provider == "bedrock":
            raise NotImplementedError(
                "Bedrock provider wired by FEAT-PO-004"
            )
        raise LLMProviderError(
            f"Unsupported provider: {self.provider!r}. "
            "Expected one of: 'local', 'bedrock' (Phase 0)."
        )

    def _generate_ollama(self, prompt: str, system: str | None) -> str:
        import httpx  # Lazy: keeps import graph minimal for non-local paths

        base_url = os.environ.get("OLLAMA_BASE_URL") or DEFAULT_OLLAMA_BASE_URL
        model = os.environ.get("OLLAMA_MODEL") or DEFAULT_OLLAMA_MODEL
        num_predict = _resolve_num_predict()

        payload: dict[str, object] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"num_predict": num_predict},
        }
        if system:
            payload["system"] = system

        try:
            response = httpx.post(
                f"{base_url.rstrip('/')}/api/generate",
                json=payload,
                timeout=DEFAULT_OLLAMA_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"Ollama request to {base_url} failed: {exc}"
            ) from exc

        data = response.json()
        return data.get("response", "")
