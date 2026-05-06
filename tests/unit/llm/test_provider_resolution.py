"""Provider resolution tests for LLMClient (SR-03 parity surface).

Covers the integration contract with TASK-PO02-001
(``AGENT_MODELS__REASONING_MODEL``) plus the Bedrock-stub boundary and
the Ollama HTTP call-shape. TASK-PO02-006 covers the broader parity
matrix end-to-end.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.seam
@pytest.mark.integration_contract("AGENT_MODELS__REASONING_MODEL")
def test_agent_models_reasoning_model_format() -> None:
    """Verify AGENT_MODELS__REASONING_MODEL matches the expected format.

    Contract: string ∈ {'local', 'bedrock', 'openai', 'anthropic', 'gemini'};
              Phase 0 supports 'local' (default) and 'bedrock' (NotImplementedError).
    Producer: TASK-PO02-001 (.env.example)
    """
    from study_tutor.llm.client import _default_player_model

    # Factory must read env at call time, not import time (SR-03)
    with patch.dict(os.environ, {"AGENT_MODELS__REASONING_MODEL": "local"}, clear=False):
        assert _default_player_model() == "local"

    with patch.dict(os.environ, {"AGENT_MODELS__REASONING_MODEL": "bedrock"}, clear=False):
        assert _default_player_model() == "bedrock"

    # Fallback when unset
    env_without = {k: v for k, v in os.environ.items() if k != "AGENT_MODELS__REASONING_MODEL"}
    with patch.dict(os.environ, env_without, clear=True):
        assert _default_player_model() == "local"


@pytest.mark.seam
def test_bedrock_provider_raises_not_implemented() -> None:
    """Phase 0 Bedrock stub must raise NotImplementedError, not silently fail."""
    from study_tutor.llm.client import LLMClient

    client = LLMClient(provider="bedrock")
    with pytest.raises(NotImplementedError, match="FEAT-PO-004"):
        client.generate("test prompt")


def test_unsupported_provider_raises_llm_provider_error() -> None:
    """Unknown providers must fail explicitly; never silently route to a default."""
    from study_tutor.llm.client import LLMClient, LLMProviderError

    client = LLMClient(provider="openai")  # reserved for Phase 1+
    with pytest.raises(LLMProviderError, match="Unsupported provider"):
        client.generate("hello")


def test_local_provider_posts_openai_compat_with_system_prompt() -> None:
    """Local path should POST to {LOCAL_BASE_URL}/v1/chat/completions with messages."""
    from study_tutor.llm.client import LLMClient

    fake_response = MagicMock()
    fake_response.json.return_value = {
        "choices": [{"message": {"content": "Macbeth is a tragedy."}}]
    }
    fake_response.raise_for_status.return_value = None

    env = {
        "LOCAL_BASE_URL": "http://localhost:11434",
        "LOCAL_MODEL": "gcse-tutor-test",
    }
    with patch.dict(os.environ, env, clear=False):
        with patch("httpx.post", return_value=fake_response) as mock_post:
            client = LLMClient(provider="local")
            out = client.generate("Explain the dagger speech.", system="You are a tutor.")

    assert out == "Macbeth is a tragedy."
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "http://localhost:11434/v1/chat/completions"
    body = kwargs["json"]
    assert body["model"] == "gcse-tutor-test"
    assert body["messages"] == [
        {"role": "system", "content": "You are a tutor."},
        {"role": "user", "content": "Explain the dagger speech."},
    ]
    assert body["stream"] is False
    # Default num_predict ceiling (TASK-PO02F-002) keeps essay scaffolds
    # from truncating at Ollama's ~128-token default.
    assert body["max_tokens"] == 2048


def test_local_provider_omits_system_when_none() -> None:
    """When system is not provided, the messages list must contain only the user message."""
    from study_tutor.llm.client import LLMClient

    fake_response = MagicMock()
    fake_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}]
    }
    fake_response.raise_for_status.return_value = None

    with patch.dict(os.environ, {}, clear=False):
        with patch("httpx.post", return_value=fake_response) as mock_post:
            LLMClient(provider="local").generate("hi")

    body = mock_post.call_args.kwargs["json"]
    assert all(m.get("role") != "system" for m in body["messages"])
    assert body["messages"] == [{"role": "user", "content": "hi"}]


def test_local_provider_uses_env_num_predict_at_call_time() -> None:
    """LOCAL_NUM_PREDICT override must be read at call time (SR-03).

    TASK-PO02F-002: the Ollama-compatible default (~128 tokens) truncates
    GCSE essay scaffolds mid-body-paragraph. Default ceiling is 2048;
    overridable per-call via the env var.
    """
    from study_tutor.llm.client import LLMClient

    fake_response = MagicMock()
    fake_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}]
    }
    fake_response.raise_for_status.return_value = None

    with patch.dict(os.environ, {"LOCAL_NUM_PREDICT": "512"}, clear=False):
        with patch("httpx.post", return_value=fake_response) as mock_post:
            LLMClient(provider="local").generate("hi")

    body = mock_post.call_args.kwargs["json"]
    assert body["max_tokens"] == 512


def test_local_provider_falls_back_to_default_on_bad_num_predict() -> None:
    """Non-integer or non-positive LOCAL_NUM_PREDICT values must fall back
    to the default, not crash or pass through garbage to the local LLM."""
    from study_tutor.llm.client import LLMClient

    fake_response = MagicMock()
    fake_response.json.return_value = {
        "choices": [{"message": {"content": "ok"}}]
    }
    fake_response.raise_for_status.return_value = None

    for bad in ("not-a-number", "0", "-1", ""):
        with patch.dict(os.environ, {"LOCAL_NUM_PREDICT": bad}, clear=False):
            with patch("httpx.post", return_value=fake_response) as mock_post:
                LLMClient(provider="local").generate("hi")
        body = mock_post.call_args.kwargs["json"]
        assert body["max_tokens"] == 2048, (
            f"Expected fallback to 2048 for LOCAL_NUM_PREDICT={bad!r}"
        )


def test_local_provider_wraps_http_errors() -> None:
    """httpx errors should be re-raised as LLMProviderError with context."""
    import httpx

    from study_tutor.llm.client import LLMClient, LLMProviderError

    with patch("httpx.post", side_effect=httpx.ConnectError("refused")):
        client = LLMClient(provider="local")
        with pytest.raises(LLMProviderError, match="OpenAI-compat request"):
            client.generate("hi")


def test_no_module_level_client_instantiation() -> None:
    """SR-03: no top-level LLMClient() call in the module.

    Reads the source and asserts we never instantiate at import time,
    since such an instance would capture env vars prematurely.
    """
    import inspect

    from study_tutor.llm import client as client_mod

    source = inspect.getsource(client_mod)
    # Strip indented (function-body) lines to inspect module-level statements only.
    module_level = "\n".join(
        line for line in source.splitlines() if line and not line[0].isspace()
    )
    assert "LLMClient(" not in module_level


@pytest.mark.seam
@pytest.mark.integration_contract("SR-03-adapter-provider-neutrality")
def test_adapter_handlers_do_not_reference_provider_string_literals() -> None:
    """SR-03: MCP tool handlers must resolve the provider at call time,
    never hard-code one.

    Greps the adapter source for any of the reserved provider tokens
    ('local', 'bedrock', 'openai', 'anthropic', 'gemini') appearing as
    string literals. The only acceptable provider reference inside a
    handler is ``_default_player_model()``.
    """
    import inspect
    import re

    from study_tutor.mcp import adapter as adapter_mod

    source = inspect.getsource(adapter_mod)
    # Strip docstrings / comments: the contract is about executable code,
    # not prose. Module/function/class docstrings may legitimately name
    # providers while describing the SR-03 rule itself.
    code_only = re.sub(r'"""[\s\S]*?"""', "", source)
    code_only = re.sub(r"'''[\s\S]*?'''", "", code_only)
    code_only = re.sub(r"#.*", "", code_only)

    forbidden = ("local", "bedrock", "openai", "anthropic", "gemini")
    for token in forbidden:
        pattern = rf"""["']{re.escape(token)}["']"""
        hit = re.search(pattern, code_only)
        assert hit is None, (
            f"SR-03 violation: adapter.py contains string literal "
            f"{hit.group() if hit else token!r}. Handlers must resolve "
            f"the provider via _default_player_model() at call time."
        )
