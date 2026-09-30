"""HuggingFace Inference API backend for Flux.1 image generation."""

from __future__ import annotations

import logging

import httpx

from .base import ImageProvider

logger = logging.getLogger(__name__)

HF_INFERENCE_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"


class FluxHuggingFace(ImageProvider):
    """Generate images via the HuggingFace Inference API (Flux.1-dev)."""

    def __init__(self, hf_token: str):
        self.hf_token = hf_token
        self.headers = {"Authorization": f"Bearer {hf_token}"}

    async def generate(
        self,
        prompt: str,
        negative: str = "",
        width: int = 512,
        height: int = 512,
        seed: int = -1,
    ) -> bytes:
        payload = {
            "inputs": prompt,
            "parameters": {
                "width": width,
                "height": height,
                "num_inference_steps": 30,
                "guidance_scale": 3.5,
            },
        }
        if negative:
            payload["parameters"]["negative_prompt"] = negative
        if seed >= 0:
            payload["parameters"]["seed"] = seed

        logger.info("Generating image via HuggingFace: %.80s...", prompt)

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                HF_INFERENCE_URL,
                json=payload,
                headers=self.headers,
            )
            response.raise_for_status()
            return response.content
