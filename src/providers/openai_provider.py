"""Async OpenAI Responses provider for text and structured generation."""

from __future__ import annotations

import logging
from typing import Any

from openai import APIConnectionError, AsyncOpenAI, InternalServerError, RateLimitError
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .base import LLMProvider

logger = logging.getLogger(__name__)


def _transient_retry():
    """Retry transport, rate-limit and server errors, never invalid requests."""
    return retry(
        retry=retry_if_exception_type((APIConnectionError, RateLimitError, InternalServerError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        reraise=True,
    )


class OpenAIProvider(LLMProvider):
    """Use Responses with configurable reasoning and output-token budget."""

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-6-luna",
        *,
        max_tokens: int = 16384,
        reasoning_effort: str = "low",
    ):
        self.client = AsyncOpenAI(api_key=api_key, max_retries=0)
        self.model = model
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort

    def _request(self, system: str, prompt: str, temperature: float) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "instructions": system,
            "input": prompt,
            "max_output_tokens": self.max_tokens,
            "store": False,
        }
        if self.model.startswith(("gpt-5", "gpt-6", "o1", "o3", "o4")):
            kwargs["reasoning"] = {"effort": self.reasoning_effort}
            # GPT-6 sampling controls are supported only with reasoning disabled.
            if self.reasoning_effort == "none":
                kwargs["temperature"] = temperature
        else:
            kwargs["temperature"] = temperature
        return kwargs

    @staticmethod
    def _check_response(response: Any) -> None:
        if response.status != "completed":
            raise RuntimeError(
                f"OpenAI response {response.status}: {response.incomplete_details}. "
                "Check provider.max_tokens if the output budget was exhausted."
            )
        for item in response.output:
            for content in getattr(item, "content", ()):
                if content.type == "refusal":
                    raise RuntimeError(f"OpenAI refused generation: {content.refusal}")

    @_transient_retry()
    async def query(
        self,
        system: str,
        prompt: str,
        *,
        temperature: float = 0.9,
    ) -> str:
        response = await self.client.responses.create(**self._request(system, prompt, temperature))
        self._check_response(response)
        if not response.output_text.strip():
            raise RuntimeError("OpenAI returned no text for generation")
        logger.debug("OpenAI [%s] usage: %s", self.model, response.usage)
        return response.output_text

    @_transient_retry()
    async def query_structured(
        self,
        system: str,
        prompt: str,
        response_model: type[BaseModel],
        *,
        temperature: float = 0.9,
    ) -> BaseModel:
        response = await self.client.responses.parse(
            **self._request(system, prompt, temperature),
            text_format=response_model,
        )
        self._check_response(response)
        if response.output_parsed is None:
            raise RuntimeError("OpenAI returned no structured content")
        logger.debug("OpenAI [%s] usage: %s", self.model, response.usage)
        return response.output_parsed
