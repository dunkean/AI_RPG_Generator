"""Native Qwen-Image text-to-image workflow for ComfyUI split models."""

from __future__ import annotations

from secrets import randbits

from .base import GenerationParams, WorkflowBuilder


class QwenImageWorkflow(WorkflowBuilder):
    """Load diffusion model, Qwen text encoder and VAE separately."""

    def __init__(
        self,
        unet: str = "qwen_image_fp8_e4m3fn.safetensors",
        clip: str = "qwen_2.5_vl_7b_fp8_scaled.safetensors",
        vae: str = "qwen_image_vae.safetensors",
        weight_dtype: str = "default",
        sampler: str = "euler",
        scheduler: str = "simple",
        steps: int = 20,
        cfg_scale: float = 4.0,
        shift: float = 3.1,
    ):
        self.unet = unet
        self.clip = clip
        self.vae = vae
        self.weight_dtype = weight_dtype
        self.sampler = sampler
        self.scheduler = scheduler
        self.steps = steps
        self.cfg_scale = cfg_scale
        self.shift = shift

    @property
    def name(self) -> str:
        return "qwen"

    @property
    def supports_negative_prompt(self) -> bool:
        return True

    # Qwen LoRAs modify only the diffusion model; text encoder stays independent.
    # Inherited model_node_id="1", clip_node_id=None wires LoRAs before sampling shift.

    def build(self, params: GenerationParams) -> dict:
        seed = params.seed if params.seed >= 0 else randbits(63)
        return {
            "prompt": {
                "1": {
                    "class_type": "UNETLoader",
                    "inputs": {"unet_name": self.unet, "weight_dtype": self.weight_dtype},
                },
                "2": {
                    "class_type": "CLIPLoader",
                    "inputs": {"clip_name": self.clip, "type": "qwen_image", "device": "default"},
                },
                "3": {
                    "class_type": "VAELoader",
                    "inputs": {"vae_name": self.vae},
                },
                "4": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"text": params.prompt, "clip": ["2", 0]},
                },
                "5": {
                    "class_type": "CLIPTextEncode",
                    "inputs": {"text": params.negative, "clip": ["2", 0]},
                },
                "6": {
                    "class_type": "EmptySD3LatentImage",
                    "inputs": {"width": params.width, "height": params.height, "batch_size": 1},
                },
                "7": {
                    "class_type": "ModelSamplingAuraFlow",
                    "inputs": {"model": ["1", 0], "shift": self.shift},
                },
                "8": {
                    "class_type": "KSampler",
                    "inputs": {
                        "model": ["7", 0],
                        "positive": ["4", 0],
                        "negative": ["5", 0],
                        "latent_image": ["6", 0],
                        "seed": seed,
                        "steps": self.steps,
                        "cfg": self.cfg_scale,
                        "sampler_name": self.sampler,
                        "scheduler": self.scheduler,
                        "denoise": 1.0,
                    },
                },
                "9": {
                    "class_type": "VAEDecode",
                    "inputs": {"samples": ["8", 0], "vae": ["3", 0]},
                },
                "10": {
                    "class_type": "SaveImage",
                    "inputs": {"images": ["9", 0], "filename_prefix": "ttrpg"},
                },
            }
        }
