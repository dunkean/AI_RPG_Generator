"""ComfyUI image provider — composes client + workflow builder + LoRA injection."""

from __future__ import annotations

import logging

from ..base import ImageProvider
from .client import ComfyUIClient
from .workflows.base import GenerationParams, WorkflowBuilder
from .workflows.lora import LoRAEntry, inject_loras

logger = logging.getLogger(__name__)


class ComfyUIProvider(ImageProvider):
    """Generate images via a local ComfyUI server using any supported model."""

    def __init__(
        self,
        client: ComfyUIClient,
        workflow: WorkflowBuilder,
        loras: list[LoRAEntry] | None = None,
    ):
        self.client = client
        self.workflow = workflow
        self.loras = loras or []

    async def generate(
        self,
        prompt: str,
        negative: str = "",
        width: int = 512,
        height: int = 512,
        seed: int = -1,
    ) -> bytes:
        params = GenerationParams(
            prompt=prompt,
            width=width,
            height=height,
            seed=seed,
            negative=negative,
        )
        payload = self.workflow.build(params)

        if self.loras:
            inject_loras(
                payload,
                self.loras,
                model_node_id=self.workflow.model_node_id,
                clip_node_id=self.workflow.clip_node_id,
            )

        logger.info(
            "ComfyUI [%s] generating: %.80s...",
            self.workflow.name,
            prompt,
        )
        return await self.client.execute_workflow(payload)
