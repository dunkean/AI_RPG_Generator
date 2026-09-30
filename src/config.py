"""Configuration system: YAML loading + Pydantic validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, model_validator
from pydantic_settings import BaseSettings

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


# ---------------------------------------------------------------------------
# Pydantic models for config sections
# ---------------------------------------------------------------------------

class ProviderConfig(BaseModel):
    type: str = "openai"
    model: str = "gpt-6-luna"
    temperature: float = 0.9
    max_tokens: int = Field(default=16384, gt=0)
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = "low"


class LoRAConfig(BaseModel):
    """A LoRA to apply during image generation."""

    name: str
    strength_model: float = 1.0
    strength_clip: float = 1.0


class ComfyUIModelConfig(BaseModel):
    """Configuration for a single ComfyUI model profile."""

    type: str  # workflow builder name: "flux", "sdxl_turbo", "cogview", "qwen"
    params: dict[str, Any] = Field(default_factory=dict)
    loras: list[LoRAConfig] = Field(default_factory=list)


def _default_models() -> dict[str, ComfyUIModelConfig]:
    return {
        "flux": ComfyUIModelConfig(
            type="flux",
            params={
                "unet": "flux1-dev-fp8-e4m3fn.safetensors",
                "clip1": "t5xxl_fp16.safetensors",
                "clip2": "clip_l.safetensors",
                "vae": "ae.safetensors",
                "weight_dtype": "default",
                "sampler": "euler",
                "scheduler": "simple",
                "steps": 20,
            },
        ),
        "qwen": ComfyUIModelConfig(
            type="qwen",
            params={
                "unet": "qwen_image_fp8_e4m3fn.safetensors",
                "clip": "qwen_2.5_vl_7b_fp8_scaled.safetensors",
                "vae": "qwen_image_vae.safetensors",
                "steps": 20,
                "cfg_scale": 4.0,
            },
        ),
    }


class ImageConfig(BaseModel):
    provider: str = "comfyui"
    model: str = "qwen"
    portrait_width: int = 768
    portrait_height: int = 1024
    building_width: int = 1024
    building_height: int = 768
    comfyui_url: str = "http://127.0.0.1:8188"
    comfyui_timeout: float = 600.0
    models: dict[str, ComfyUIModelConfig] = Field(default_factory=_default_models)

    @model_validator(mode="before")
    @classmethod
    def _migrate_legacy_fields(cls, data: Any) -> Any:
        """Auto-migrate old flat comfyui_* config fields to the new structure."""
        if not isinstance(data, dict):
            return data

        # Migrate provider name: "flux_comfyui" -> "comfyui"
        if data.get("provider") == "flux_comfyui":
            data["provider"] = "comfyui"
            data.setdefault("model", "flux")

        # Migrate flat comfyui_* fields into models.flux.params
        legacy_keys = {
            "comfyui_unet": "unet",
            "comfyui_clip1": "clip1",
            "comfyui_clip2": "clip2",
            "comfyui_vae": "vae",
            "comfyui_weight_dtype": "weight_dtype",
        }
        legacy_params = {}
        for old_key, new_key in legacy_keys.items():
            if old_key in data:
                legacy_params[new_key] = data.pop(old_key)

        if legacy_params:
            models = data.setdefault("models", {})
            flux = models.setdefault("flux", {})
            if isinstance(flux, dict):
                flux.setdefault("type", "flux")
                params = flux.setdefault("params", {})
                for k, v in legacy_params.items():
                    params.setdefault(k, v)

        return data


class FolderConfig(BaseModel):
    output: str = "output"
    cache: str = "cache"
    log: str = "log"
    portraits: str = "portraits"
    buildings: str = "buildings"


class GenerationConfig(BaseModel):
    seed: int = 42
    mean_group_size: int = 7
    temperature: float = 0.9
    max_retries: int = 3
    max_concurrent_queries: int = 3


class SettingConfig(BaseModel):
    lore: str = ""
    type: str = "Medieval fantasy"


class CommunityConfig(BaseModel):
    description: str = ""
    type: str = "small community"
    scale: str = "local"
    population: int = 80
    race_ratio: dict[str, float] = Field(default_factory=lambda: {"human": 1.0})


class ProjectConfig(BaseModel):
    """Full merged configuration for a generation run."""

    project_id: str = "default"
    generation: GenerationConfig = Field(default_factory=GenerationConfig)
    provider: ProviderConfig = Field(default_factory=ProviderConfig)
    image: ImageConfig = Field(default_factory=ImageConfig)
    folders: FolderConfig = Field(default_factory=FolderConfig)
    setting: SettingConfig = Field(default_factory=SettingConfig)
    community: CommunityConfig = Field(default_factory=CommunityConfig)
    group_categories: list[str] = Field(default_factory=lambda: [
        "culture", "customs", "goals", "resources", "history",
        "external_influences", "timeline", "sites", "anecdotes",
    ])
    detail_categories: list[str] = Field(default_factory=lambda: [
        "customs", "resources", "history", "timeline", "sites", "anecdotes",
    ])


# ---------------------------------------------------------------------------
# Environment-based secrets
# ---------------------------------------------------------------------------

class EnvSettings(BaseSettings):
    openai_api_key: str = ""
    hf_token: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge *override* into *base*, returning the result."""
    merged = base.copy()
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def _load_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def load_config(project_name: str, config_dir: Path | None = None) -> ProjectConfig:
    """Load default.yaml, merge with project yaml, return validated config."""
    config_dir = config_dir or CONFIG_DIR

    default_data = _load_yaml(config_dir / "default.yaml")
    project_path = config_dir / "projects" / f"{project_name}.yaml"
    project_data = _load_yaml(project_path) if project_path.exists() else {}

    merged = _deep_merge(default_data, project_data)
    return ProjectConfig(**merged)
