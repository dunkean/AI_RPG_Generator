"""Factory for creating image providers from configuration."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from .base import ImageProvider

if TYPE_CHECKING:
    from ..config import ImageConfig

logger = logging.getLogger(__name__)


def create_image_provider(
    image_config: ImageConfig,
    hf_token: str = "",
) -> ImageProvider | None:
    """Create an image provider from the given config.

    Returns None if the provider can't be initialized (e.g. missing token).
    """
    provider_type = image_config.provider

    if provider_type == "flux_hf":
        if not hf_token:
            logger.warning("HF_TOKEN not set, cannot create HuggingFace provider")
            return None
        from .flux_hf import FluxHuggingFace
        return FluxHuggingFace(hf_token=hf_token)

    if provider_type == "comfyui":
        from .comfyui.client import ComfyUIClient
        from .comfyui.provider import ComfyUIProvider
        from .comfyui.workflows.lora import LoRAEntry
        from .comfyui.workflows.registry import get_workflow_builder

        # Look up the selected model profile
        model_name = image_config.model
        model_profiles = image_config.models
        if model_name not in model_profiles:
            available = ", ".join(sorted(model_profiles))
            raise ValueError(
                f"Unknown image model {model_name!r}. "
                f"Available: {available}"
            )

        profile = model_profiles[model_name]
        workflow = get_workflow_builder(profile.type, profile.params)

        client = ComfyUIClient(
            base_url=image_config.comfyui_url,
            timeout=image_config.comfyui_timeout,
        )

        loras = [
            LoRAEntry(
                name=l.name,
                strength_model=l.strength_model,
                strength_clip=l.strength_clip,
            )
            for l in profile.loras
        ]

        return ComfyUIProvider(client=client, workflow=workflow, loras=loras)

    logger.warning("Unknown image provider: %s", provider_type)
    return None
