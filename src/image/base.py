"""Abstract base class for image generation providers."""

from __future__ import annotations

from abc import ABC, abstractmethod


class ImageProvider(ABC):
    """Image generation provider interface."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        negative: str = "",
        width: int = 512,
        height: int = 512,
        seed: int = -1,
    ) -> bytes:
        """Generate an image and return raw bytes (PNG)."""
