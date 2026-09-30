"""CogView / GLM-Image workflow builder for ComfyUI."""

from __future__ import annotations

from .base import GenerationParams, WorkflowBuilder


class CogViewWorkflow(WorkflowBuilder):
    """Standard checkpoint-based workflow for CogView/GLM-Image models.

    Uses CheckpointLoaderSimple + pos/neg CLIPTextEncode +
    EmptyLatentImage + KSampler → VAEDecode → SaveImage.
    """

    def __init__(
        self,
        checkpoint: str = "cogview3-plus.safetensors",
        sampler: str = "euler",
        scheduler: str = "normal",
        steps: int = 30,
        cfg_scale: float = 7.5,
    ):
        self.checkpoint = checkpoint
        self.sampler = sampler
        self.scheduler = scheduler
        self.steps = steps
        self.cfg_scale = cfg_scale

    @property
    def name(self) -> str:
        return "cogview"

    @property
    def supports_negative_prompt(self) -> bool:
        return True

    @property
    def model_node_id(self) -> str:
        return "1"

    @property
    def clip_node_id(self) -> str | None:
        return "1"

    def build(self, params: GenerationParams) -> dict:
        seed = params.seed if params.seed >= 0 else 42
        return {
            "prompt": {
                "1": {
                    "class_type": "CheckpointLoaderSimple",
                    "inputs": {
                        "ckpt_name": self.checkpoint,
                    },
                },
                "2": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "text": params.prompt,
                        "clip": ["1", 1],
                    },
                },
                "3": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "text": params.negative,
                        "clip": ["1", 1],
                    },
                },
                "4": {
                    "class_type": "EmptyLatentImage",
                    "inputs": {
                        "width": params.width,
                        "height": params.height,
                        "batch_size": 1,
                    },
                },
                "5": {
                    "class_type": "KSampler",
                    "inputs": {
                        "model": ["1", 0],
                        "positive": ["2", 0],
                        "negative": ["3", 0],
                        "latent_image": ["4", 0],
                        "seed": seed,
                        "steps": self.steps,
                        "cfg": self.cfg_scale,
                        "sampler_name": self.sampler,
                        "scheduler": self.scheduler,
                        "denoise": 1.0,
                    },
                },
                "6": {
                    "class_type": "VAEDecode",
                    "inputs": {
                        "samples": ["5", 0],
                        "vae": ["1", 2],
                    },
                },
                "7": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "images": ["6", 0],
                        "filename_prefix": "ttrpg",
                    },
                },
            }
        }
