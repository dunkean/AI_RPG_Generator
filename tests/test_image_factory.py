"""Tests for the image provider factory."""

import pytest

from src.config import ImageConfig, ComfyUIModelConfig, LoRAConfig
from src.image.factory import create_image_provider
from src.image.flux_hf import FluxHuggingFace
from src.image.comfyui.provider import ComfyUIProvider


class TestCreateImageProvider:
    def test_flux_hf_with_token(self):
        config = ImageConfig(provider="flux_hf")
        provider = create_image_provider(config, hf_token="hf_test123")
        assert isinstance(provider, FluxHuggingFace)

    def test_flux_hf_without_token(self):
        config = ImageConfig(provider="flux_hf")
        provider = create_image_provider(config, hf_token="")
        assert provider is None

    def test_comfyui_default_flux(self):
        config = ImageConfig(provider="comfyui", model="flux")
        provider = create_image_provider(config)
        assert isinstance(provider, ComfyUIProvider)
        assert provider.workflow.name == "flux"

    def test_comfyui_sdxl_turbo(self):
        config = ImageConfig(
            provider="comfyui",
            model="sdxl_turbo",
            models={
                "sdxl_turbo": ComfyUIModelConfig(
                    type="sdxl_turbo",
                    params={"checkpoint": "turbo.safetensors"},
                ),
            },
        )
        provider = create_image_provider(config)
        assert isinstance(provider, ComfyUIProvider)
        assert provider.workflow.name == "sdxl_turbo"

    def test_comfyui_with_loras(self):
        config = ImageConfig(
            provider="comfyui",
            model="flux",
            models={
                "flux": ComfyUIModelConfig(
                    type="flux",
                    params={"unet": "test.safetensors"},
                    loras=[LoRAConfig(name="art.safetensors", strength_model=0.8)],
                ),
            },
        )
        provider = create_image_provider(config)
        assert isinstance(provider, ComfyUIProvider)
        assert len(provider.loras) == 1
        assert provider.loras[0].name == "art.safetensors"

    def test_unknown_model_raises(self):
        config = ImageConfig(provider="comfyui", model="nonexistent")
        with pytest.raises(ValueError, match="Unknown image model"):
            create_image_provider(config)

    def test_unknown_provider(self):
        config = ImageConfig(provider="unknown_provider")
        provider = create_image_provider(config)
        assert provider is None
