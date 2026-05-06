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
DEFAULT_LOCAL_BASE_URL = "http://localhost:11434"
DEFAULT_LOCAL_MODEL = "gcse-tutor-gemma4-moe:latest"
DEFAULT_LOCAL_TIMEOUT_SECONDS = 120.0
# The Ollama-compatible default num_predict is ~128 tokens — too small for
# GCSE essay scaffolds. Cap at 2048 to fit a full Intro/Body ×2/Conclusion
# plan; overridable via LOCAL_NUM_PREDICT for tuning (see TASK-PO02F-002).
DEFAULT_LOCAL_NUM_PREDICT = 2048


class LLMProviderError(RuntimeError):
    """Raised when the configured provider is misconfigured or unreachable."""


def _resolve_num_predict() -> int:
    """Return the local LLM ``num_predict`` ceiling.

    Reads ``LOCAL_NUM_PREDICT`` at call time (SR-03). Falls back to
    ``DEFAULT_LOCAL_NUM_PREDICT`` when unset or not a positive integer.
    """
    raw = os.environ.get("LOCAL_NUM_PREDICT")
    if raw is None or raw == "":
        return DEFAULT_LOCAL_NUM_PREDICT
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_LOCAL_NUM_PREDICT
    return value if value > 0 else DEFAULT_LOCAL_NUM_PREDICT


def _default_player_model() -> str:
    """Return the default player-model provider from the environment.

    Reads ``AGENT_MODELS__REASONING_MODEL`` at call time (SR-03).
    Falls back to ``"local"`` when unset.
    """
    return os.environ.get("AGENT_MODELS__REASONING_MODEL") or DEFAULT_PLAYER_MODEL


def _default_coach_model() -> str:
    """Resolve the Coach provider name at call time.

    Reads ``AGENT_MODELS__COACH_MODEL`` from the environment on every
    invocation (SR-03 parity with :func:`_default_player_model`). Unlike
    the player-side helper, there is **no fallback default** — per
    decision D-COACH-05 (FEAT-6CC5) the operator MUST configure the
    Coach provider explicitly so the D3 two-provider invariant
    (ASSUM-LCA-009) cannot be silently violated by accepting a default
    that happens to coincide with the Player's provider.

    Returns:
        The exact, untransformed value of
        ``AGENT_MODELS__COACH_MODEL`` from the environment. The value
        is returned verbatim — no canonicalisation, no case folding —
        so that downstream comparisons (e.g.
        ``Coach.provider == Player.provider`` in
        :func:`study_tutor.tutoring.coach.factory.validate_coach_config`)
        operate on exactly what the operator typed.

    Raises:
        LLMProviderError: When ``AGENT_MODELS__COACH_MODEL`` is unset
            or set to an empty/whitespace-only string. The exception
            message names the env var literally (``"AGENT_MODELS__COACH_MODEL"``)
            so that operators can search logs deterministically (per
            AC-LCA-07).
    """
    raw = os.environ.get("AGENT_MODELS__COACH_MODEL", "")
    if not raw or not raw.strip():
        raise LLMProviderError(
            "AGENT_MODELS__COACH_MODEL is not set. Phase-1 requires the "
            "Coach provider to be explicitly configured and to differ "
            "from AGENT_MODELS__REASONING_MODEL (the D3 two-provider "
            "invariant is enforced at orchestrator factory time via "
            "validate_coach_config; rotation requires server restart "
            "because the env var is snapshotted at boot)."
        )
    return raw


class LLMClient:
    """Provider-agnostic LLM client.

    Sync, string-in / string-out. Construct per call site
    (``LLMClient(provider=_default_player_model())``) — never module-level.
    """

    def __init__(self, provider: str) -> None:
        self.provider = provider

    def generate(self, prompt: str, system: str | None = None) -> str:
        if self.provider == "local":
            return self._generate_openai_compat(
                prompt,
                system,
                model_env="LOCAL_MODEL",
                base_url_env="LOCAL_BASE_URL",
            )
        if self.provider == "local-coach":
            # Coach routes through its own llama-swap endpoint
            # (LOCAL_COACH_BASE_URL) and selects LOCAL_COACH_MODEL.
            # When LOCAL_COACH_BASE_URL is unset the Coach falls back to
            # LOCAL_BASE_URL so single-host setups still work. D3
            # (Coach.provider != Player.provider) is satisfied at the
            # provider-name level so the boot smoke check in
            # MCPAdapter.__init__ accepts the configuration. Phase-1
            # plumbing only — Coach calibration is Phase-2 (per
            # ASSUM-LCA-010 and TASK-REV-GRD5 follow-up).
            #
            # Uses /v1/chat/completions (OpenAI-compatible) so the same code
            # path works against llama-swap (Phase-1 Coach host, which only
            # exposes the OpenAI-compat surface) and against Mac Ollama (which
            # supports both /v1/chat/completions and /api/generate). A
            # single-host configuration that points LOCAL_COACH_BASE_URL at
            # Mac Ollama therefore works without code changes.
            return self._generate_openai_compat(
                prompt,
                system,
                model_env="LOCAL_COACH_MODEL",
                base_url_env="LOCAL_COACH_BASE_URL",
            )
        if self.provider == "bedrock":
            raise NotImplementedError(
                "Bedrock provider wired by FEAT-PO-004"
            )
        raise LLMProviderError(
            f"Unsupported provider: {self.provider!r}. "
            "Expected one of: 'local', 'local-coach', 'bedrock' (Phase 0)."
        )

    def _generate_openai_compat(
        self,
        prompt: str,
        system: str | None,
        *,
        model_env: str,
        base_url_env: str,
    ) -> str:
        """Call an OpenAI-compatible /v1/chat/completions endpoint.

        Used by the ``local-coach`` provider for hosts (e.g. llama-swap)
        that don't expose Ollama's native /api/generate surface. Returns
        the assistant message content as a string, matching the
        Player-side return shape so callers can treat both code paths
        uniformly.

        Note: after TASK-LSP-002 both ``local`` and ``local-coach``
        providers reach this helper, so the ``LOCAL_BASE_URL`` fallback
        below is shared across providers.
        """
        import httpx  # Lazy: keeps import graph minimal for non-local paths

        base_url = (
            os.environ.get(base_url_env)
            or os.environ.get("LOCAL_BASE_URL")
            or DEFAULT_LOCAL_BASE_URL
        )
        model = os.environ.get(model_env) or DEFAULT_LOCAL_MODEL
        num_predict = _resolve_num_predict()

        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload: dict[str, object] = {
            "model": model,
            "messages": messages,
            "max_tokens": num_predict,
            "stream": False,
        }

        try:
            response = httpx.post(
                f"{base_url.rstrip('/')}/v1/chat/completions",
                json=payload,
                timeout=DEFAULT_LOCAL_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise LLMProviderError(
                f"OpenAI-compat request to {base_url} failed: {exc}"
            ) from exc

        data = response.json()
        choices = data.get("choices") or []
        if not choices:
            return ""
        message = choices[0].get("message") or {}
        return message.get("content", "")
