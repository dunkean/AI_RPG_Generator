"""Abstract base class for LLM providers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from pydantic import BaseModel


class LLMProvider(ABC):
    """LLM-agnostic provider interface."""

    @abstractmethod
    async def query(
        self,
        system: str,
        prompt: str,
        *,
        temperature: float = 0.9,
    ) -> str:
        """Send a prompt and return raw text response."""

    @abstractmethod
    async def query_structured(
        self,
        system: str,
        prompt: str,
        response_model: type[BaseModel],
        *,
        temperature: float = 0.9,
    ) -> BaseModel:
        """Send a prompt and return a validated Pydantic model."""
