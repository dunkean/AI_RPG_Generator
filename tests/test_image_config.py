"""Tests for ImageConfig legacy migration and new structured config."""

from src.config import ImageConfig, ComfyUIModelConfig, LoRAConfig, load_config


class TestImageConfigNew:
    def test_default_provider(self):
        config = ImageConfig()
        assert config.provider == "comfyui"
        assert config.model == "qwen"
        assert config.models["qwen"].type == "qwen"

    def test_default_models_has_flux(self):
        config = ImageConfig()
        assert "flux" in config.models
        assert config.models["flux"].type == "flux"

    def test_custom_model_profile(self):
        config = ImageConfig(
            model="custom",
            models={
                "custom": ComfyUIModelConfig(
                    type="sdxl_turbo",
                    params={"checkpoint": "custom.safetensors", "steps": 2},
                ),
            },
        )
        assert config.models["custom"].type == "sdxl_turbo"
        assert config.models["custom"].params["steps"] == 2

    def test_lora_config(self):
        lora = LoRAConfig(name="test.safetensors", strength_model=0.7)
        assert lora.strength_clip == 1.0

    def test_comfyui_timeout(self):
        config = ImageConfig(comfyui_timeout=120.0)
        assert config.comfyui_timeout == 120.0


class TestLegacyMigration:
    def test_flux_comfyui_provider_migrated(self):
        """Old provider name 'flux_comfyui' should become 'comfyui'."""
        config = ImageConfig(**{"provider": "flux_comfyui"})
        assert config.provider == "comfyui"
        assert config.model == "flux"

    def test_flat_comfyui_fields_migrated(self):
        """Old flat comfyui_* fields should be migrated into models.flux.params."""
        config = ImageConfig(**{
            "provider": "flux_comfyui",
            "comfyui_unet": "my_unet.safetensors",
            "comfyui_clip1": "my_clip1.safetensors",
            "comfyui_clip2": "my_clip2.safetensors",
            "comfyui_vae": "my_vae.safetensors",
            "comfyui_weight_dtype": "fp8_e4m3fn",
        })
        assert config.provider == "comfyui"
        flux = config.models["flux"]
        assert flux.params["unet"] == "my_unet.safetensors"
        assert flux.params["clip1"] == "my_clip1.safetensors"
        assert flux.params["clip2"] == "my_clip2.safetensors"
        assert flux.params["vae"] == "my_vae.safetensors"
        assert flux.params["weight_dtype"] == "fp8_e4m3fn"

    def test_legacy_doesnt_overwrite_explicit_models(self):
        """If models section is already present, legacy params use setdefault."""
        config = ImageConfig(**{
            "comfyui_unet": "legacy.safetensors",
            "models": {
                "flux": {
                    "type": "flux",
                    "params": {"unet": "explicit.safetensors"},
                },
            },
        })
        # Explicit value wins
        assert config.models["flux"].params["unet"] == "explicit.safetensors"

    def test_load_config_with_new_yaml(self):
        """default.yaml now uses the new structured format — should load cleanly."""
        config = load_config("enclave")
        assert config.image.provider == "comfyui"
        assert "flux" in config.image.models
        assert config.image.models["flux"].type == "flux"
        assert config.image.models["flux"].params["unet"] == "flux1-dev-fp8-e4m3fn.safetensors"
