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
DEFAULT_OLLAMA_BASE_URL = "http://gb10.tailnet:11434"
DEFAULT_OLLAMA_MODEL = "gcse-tutor-gemma4-31b:Q4_K_M"
DEFAULT_OLLAMA_TIMEOUT_SECONDS = 120.0


class LLMProviderError(RuntimeError):
    """Raised when the configured provider is misconfigured or unreachable."""


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

        payload: dict[str, object] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
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
