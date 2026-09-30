"""OpenAI Responses contract tests; no network or credentials required."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import httpx
import pytest
from openai import BadRequestError
from pydantic import BaseModel

from src.providers.openai_provider import OpenAIProvider


@pytest.fixture
def provider():
    with patch("src.providers.openai_provider.AsyncOpenAI") as client:
        client.return_value.responses.create = AsyncMock()
        client.return_value.responses.parse = AsyncMock()
        yield OpenAIProvider("test-key", max_tokens=8192, reasoning_effort="low")


def completed(**overrides):
    return SimpleNamespace(
        **{"status": "completed", "output": [], "usage": None, **overrides}
    )


async def test_luna_request_contract(provider):
    provider.client.responses.create.return_value = completed(output_text='{"name":"Enclave"}')
    assert await provider.query("system", "prompt", temperature=0.7) == '{"name":"Enclave"}'
    provider.client.responses.create.assert_awaited_once_with(
        model="gpt-6-luna", instructions="system", input="prompt",
        reasoning={"effort": "low"}, max_output_tokens=8192, store=False,
    )


async def test_sampling_controls_only_without_reasoning(provider):
    provider.reasoning_effort = "none"
    provider.client.responses.create.return_value = completed(output_text="ok")
    await provider.query("system", "prompt", temperature=0.7)
    assert provider.client.responses.create.call_args.kwargs["temperature"] == 0.7


async def test_structured_response(provider):
    class NPC(BaseModel):
        name: str

    npc = NPC(name="Alma")
    provider.client.responses.parse.return_value = completed(output_parsed=npc)
    assert await provider.query_structured("system", "prompt", NPC) == npc
    assert provider.client.responses.parse.call_args.kwargs["text_format"] is NPC


async def test_incomplete_response_is_not_merged(provider):
    provider.client.responses.create.return_value = SimpleNamespace(
        status="incomplete", incomplete_details={"reason": "max_output_tokens"},
    )
    with pytest.raises(RuntimeError, match="output budget"):
        await provider.query("system", "prompt")


async def test_refusal_is_explicit(provider):
    refusal = SimpleNamespace(type="refusal", refusal="Cannot comply")
    provider.client.responses.create.return_value = completed(
        output_text="", output=[SimpleNamespace(content=[refusal])],
    )
    with pytest.raises(RuntimeError, match="refused"):
        await provider.query("system", "prompt")


async def test_bad_request_is_not_retried(provider):
    response = httpx.Response(400, request=httpx.Request("POST", "https://api.openai.com"))
    provider.client.responses.create.side_effect = BadRequestError(
        "unsupported parameter", response=response, body=None,
    )
    with pytest.raises(BadRequestError):
        await provider.query("system", "prompt")
    assert provider.client.responses.create.await_count == 1
