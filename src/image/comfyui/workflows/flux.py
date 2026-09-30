"""Flux.1 / Flux.2 workflow builder for ComfyUI."""

from __future__ import annotations

from .base import GenerationParams, WorkflowBuilder


class FluxWorkflow(WorkflowBuilder):
    """Workflow for Flux.1-dev and Flux.2 models.

    Uses UNETLoader + DualCLIPLoader + VAELoader → CLIPTextEncode →
    BasicGuider + BasicScheduler + KSamplerSelect + RandomNoise →
    SamplerCustomAdvanced → VAEDecode → SaveImage.
    """

    def __init__(
        self,
        unet: str = "flux1-dev.safetensors",
        clip1: str = "t5xxl_fp16.safetensors",
        clip2: str = "clip_l.safetensors",
        vae: str = "ae.safetensors",
        weight_dtype: str = "fp8_e4m3fn",
        sampler: str = "euler",
        scheduler: str = "simple",
        steps: int = 20,
    ):
        self.unet = unet
        self.clip1 = clip1
        self.clip2 = clip2
        self.vae = vae
        self.weight_dtype = weight_dtype
        self.sampler = sampler
        self.scheduler = scheduler
        self.steps = steps

    @property
    def name(self) -> str:
        return "flux"

    @property
    def supports_negative_prompt(self) -> bool:
        return False

    @property
    def model_node_id(self) -> str:
        return "1"

    def build(self, params: GenerationParams) -> dict:
        seed = params.seed if params.seed >= 0 else 42
        return {
            "prompt": {
                # --- Model loaders ---
                "1": {
                    "class_type": "UNETLoader",
                    "inputs": {
                        "unet_name": self.unet,
                        "weight_dtype": self.weight_dtype,
                    },
                },
                "2": {
                    "class_type": "DualCLIPLoader",
                    "inputs": {
                        "clip_name1": self.clip1,
                        "clip_name2": self.clip2,
                        "type": "flux",
                    },
                },
                "3": {
                    "class_type": "VAELoader",
                    "inputs": {
                        "vae_name": self.vae,
                    },
                },
                # --- Prompt encoding (positive only, Flux ignores negative) ---
                "4": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {
                        "text": params.prompt,
                        "clip": ["2", 0],
                    },
                },
                # --- Latent ---
                "5": {
                    "class_type": "EmptySD3LatentImage",
                    "inputs": {
                        "width": params.width,
                        "height": params.height,
                        "batch_size": 1,
                    },
                },
                # --- Sampling components ---
                "6": {
                    "class_type": "BasicGuider",
                    "inputs": {
                        "model": ["1", 0],
                        "conditioning": ["4", 0],
                    },
                },
                "7": {
                    "class_type": "KSamplerSelect",
                    "inputs": {
                        "sampler_name": self.sampler,
                    },
                },
                "8": {
                    "class_type": "BasicScheduler",
                    "inputs": {
                        "model": ["1", 0],
                        "scheduler": self.scheduler,
                        "steps": self.steps,
                        "denoise": 1.0,
                    },
                },
                "9": {
                    "class_type": "RandomNoise",
                    "inputs": {
                        "noise_seed": seed,
                    },
                },
                # --- Advanced sampler ---
                "10": {
                    "class_type": "SamplerCustomAdvanced",
                    "inputs": {
                        "noise": ["9", 0],
                        "guider": ["6", 0],
                        "sampler": ["7", 0],
                        "sigmas": ["8", 0],
                        "latent_image": ["5", 0],
                    },
                },
                # --- Decode + save ---
                "11": {
                    "class_type": "VAEDecode",
                    "inputs": {
                        "samples": ["10", 0],
                        "vae": ["3", 0],
                    },
                },
                "12": {
                    "class_type": "SaveImage",
                    "inputs": {
                        "images": ["11", 0],
                        "filename_prefix": "ttrpg",
                    },
                },
            }
        }
