"""``LLMProviderError.status_code`` from both OpenAI-compat client paths.

Design ``docs/design/tutor-busy-and-history-repair-2026-10-18.md`` F2.1: the
upstream HTTP status (llama-swap's 429 busy / 502 refused-load) rides the
error so the session service can classify it as ``TutorBusy``; connection
errors carry ``None``. Message text is unchanged.
"""
from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from study_tutor.llm.client import LLMClient, LLMProviderError
from tests.unit.llm.test_streaming import StreamingMockTransport


@pytest.fixture(autouse=True)
def _local_provider_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_MODELS__REASONING_MODEL", "local")
    monkeypatch.setenv("LOCAL_BASE_URL", "http://test:11434")
    monkeypatch.setenv("LOCAL_MODEL", "test-model")


def test_default_status_code_is_none() -> None:
    assert LLMProviderError("boom").status_code is None


@pytest.mark.parametrize("status", [429, 502])
def test_sync_path_carries_upstream_status(status: int) -> None:
    request = httpx.Request("POST", "http://test:11434/v1/chat/completions")
    response = httpx.Response(status, request=request)

    with patch("httpx.post", return_value=response):
        client = LLMClient(provider="local")
        with pytest.raises(LLMProviderError, match="OpenAI-compat request") as exc_info:
            client.generate("hi")

    assert exc_info.value.status_code == status
    assert isinstance(exc_info.value.__cause__, httpx.HTTPStatusError)


def test_sync_path_connection_error_has_no_status() -> None:
    with patch("httpx.post", side_effect=httpx.ConnectError("refused")):
        client = LLMClient(provider="local")
        with pytest.raises(LLMProviderError) as exc_info:
            client.generate("hi")

    assert exc_info.value.status_code is None


@pytest.mark.parametrize("status", [429, 502])
async def test_stream_path_carries_upstream_status(status: int) -> None:
    client = LLMClient(provider="local")
    client._async_client = httpx.AsyncClient(
        transport=StreamingMockTransport([], status_code=status)
    )

    with pytest.raises(
        LLMProviderError, match="OpenAI-compat streaming request"
    ) as exc_info:
        async for _ in client.generate_stream("hi"):
            pass

    assert exc_info.value.status_code == status
