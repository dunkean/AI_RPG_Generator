"""Abstract base class for ComfyUI workflow builders."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class GenerationParams:
    """Parameters passed to every workflow builder."""

    prompt: str
    width: int
    height: int
    seed: int
    negative: str = ""


class WorkflowBuilder(ABC):
    """Constructs a ComfyUI API-format workflow dict for a specific model type."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Short identifier for this workflow type (e.g. 'flux', 'sdxl_turbo')."""

    @property
    def supports_negative_prompt(self) -> bool:
        """Whether this model architecture uses a negative prompt."""
        return False

    @property
    def model_node_id(self) -> str:
        """Node ID that outputs the model — used by LoRA injection."""
        return "1"

    @property
    def clip_node_id(self) -> str | None:
        """Node ID that outputs the CLIP — used by LoRA injection.

        Return None for architectures that don't expose a separate CLIP node
        (e.g. Flux uses DualCLIPLoader which LoRA doesn't route through).
        """
        return None

    @abstractmethod
    def build(self, params: GenerationParams) -> dict:
        """Return a ComfyUI API payload ``{"prompt": {...}}``."""
