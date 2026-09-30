"""Tests for ComfyUI workflow builders."""

import pytest

from src.image.comfyui.workflows.base import GenerationParams
from src.image.comfyui.workflows.flux import FluxWorkflow
from src.image.comfyui.workflows.sdxl_turbo import SDXLTurboWorkflow
from src.image.comfyui.workflows.cogview import CogViewWorkflow
from src.image.comfyui.workflows.qwen import QwenImageWorkflow
from src.image.comfyui.workflows.registry import get_workflow_builder, list_workflow_types


PARAMS = GenerationParams(
    prompt="a fantasy portrait",
    width=768,
    height=1024,
    seed=42,
    negative="blurry",
)


class TestFluxWorkflow:
    def test_name(self):
        w = FluxWorkflow()
        assert w.name == "flux"

    def test_no_negative_prompt(self):
        w = FluxWorkflow()
        assert w.supports_negative_prompt is False

    def test_build_has_all_nodes(self):
        w = FluxWorkflow(unet="test.safetensors", steps=15)
        payload = w.build(PARAMS)
        prompt = payload["prompt"]
        assert prompt["1"]["class_type"] == "UNETLoader"
        assert prompt["1"]["inputs"]["unet_name"] == "test.safetensors"
        assert prompt["2"]["class_type"] == "DualCLIPLoader"
        assert prompt["3"]["class_type"] == "VAELoader"
        assert prompt["4"]["class_type"] == "CLIPTextEncode"
        assert prompt["4"]["inputs"]["text"] == "a fantasy portrait"
        assert prompt["5"]["class_type"] == "EmptySD3LatentImage"
        assert prompt["5"]["inputs"]["width"] == 768
        assert prompt["5"]["inputs"]["height"] == 1024
        assert prompt["8"]["inputs"]["steps"] == 15
        assert prompt["9"]["inputs"]["noise_seed"] == 42
        assert prompt["10"]["class_type"] == "SamplerCustomAdvanced"
        assert prompt["12"]["class_type"] == "SaveImage"

    def test_negative_seed_defaults(self):
        w = FluxWorkflow()
        p = GenerationParams(prompt="test", width=512, height=512, seed=-1)
        payload = w.build(p)
        assert payload["prompt"]["9"]["inputs"]["noise_seed"] == 42

    def test_custom_sampler_scheduler(self):
        w = FluxWorkflow(sampler="dpmpp_2m", scheduler="karras")
        payload = w.build(PARAMS)
        assert payload["prompt"]["7"]["inputs"]["sampler_name"] == "dpmpp_2m"
        assert payload["prompt"]["8"]["inputs"]["scheduler"] == "karras"

    def test_model_node_id(self):
        w = FluxWorkflow()
        assert w.model_node_id == "1"
        assert w.clip_node_id is None


class TestSDXLTurboWorkflow:
    def test_name(self):
        w = SDXLTurboWorkflow()
        assert w.name == "sdxl_turbo"

    def test_supports_negative_prompt(self):
        w = SDXLTurboWorkflow()
        assert w.supports_negative_prompt is True

    def test_build_structure(self):
        w = SDXLTurboWorkflow(checkpoint="turbo.safetensors", steps=2, cfg_scale=1.2)
        payload = w.build(PARAMS)
        prompt = payload["prompt"]
        assert prompt["1"]["class_type"] == "CheckpointLoaderSimple"
        assert prompt["1"]["inputs"]["ckpt_name"] == "turbo.safetensors"
        # Positive prompt
        assert prompt["2"]["inputs"]["text"] == "a fantasy portrait"
        # Negative prompt
        assert prompt["3"]["inputs"]["text"] == "blurry"
        assert prompt["5"]["class_type"] == "KSampler"
        assert prompt["5"]["inputs"]["steps"] == 2
        assert prompt["5"]["inputs"]["cfg"] == 1.2
        assert prompt["7"]["class_type"] == "SaveImage"

    def test_clip_node_id(self):
        w = SDXLTurboWorkflow()
        assert w.clip_node_id == "1"


class TestCogViewWorkflow:
    def test_name(self):
        assert CogViewWorkflow().name == "cogview"

    def test_defaults(self):
        w = CogViewWorkflow()
        payload = w.build(PARAMS)
        assert payload["prompt"]["5"]["inputs"]["steps"] == 30
        assert payload["prompt"]["5"]["inputs"]["cfg"] == 7.5


class TestQwenImageWorkflow:
    def test_name(self):
        assert QwenImageWorkflow().name == "qwen"

    def test_defaults(self):
        w = QwenImageWorkflow()
        payload = w.build(PARAMS)
        graph = payload["prompt"]
        assert graph["8"]["inputs"]["steps"] == 20
        assert graph["8"]["inputs"]["cfg"] == 4.0
        assert graph["1"]["class_type"] == "UNETLoader"
        assert graph["2"]["inputs"]["type"] == "qwen_image"
        assert graph["3"]["class_type"] == "VAELoader"
        assert graph["6"]["class_type"] == "EmptySD3LatentImage"
        assert graph["6"]["inputs"]["width"] == PARAMS.width
        assert graph["7"]["inputs"]["shift"] == 3.1
        assert graph["8"]["inputs"]["model"] == ["7", 0]
        assert graph["8"]["inputs"]["seed"] == PARAMS.seed
        assert graph["9"]["inputs"]["vae"] == ["3", 0]
        assert graph["4"]["inputs"]["text"] == PARAMS.prompt
        assert graph["5"]["inputs"]["text"] == PARAMS.negative

    def test_negative_seed_is_random(self, monkeypatch):
        monkeypatch.setattr("src.image.comfyui.workflows.qwen.randbits", lambda bits: 123456)
        params = GenerationParams(prompt="test", width=512, height=512, seed=-1)
        assert QwenImageWorkflow().build(params)["prompt"]["8"]["inputs"]["seed"] == 123456


class TestRegistry:
    def test_list_types(self):
        types = list_workflow_types()
        assert "flux" in types
        assert "sdxl_turbo" in types
        assert "cogview" in types
        assert "qwen" in types

    def test_get_flux(self):
        w = get_workflow_builder("flux", {"unet": "my.safetensors"})
        assert isinstance(w, FluxWorkflow)
        assert w.unet == "my.safetensors"

    def test_get_sdxl_turbo(self):
        w = get_workflow_builder("sdxl_turbo")
        assert isinstance(w, SDXLTurboWorkflow)

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError, match="Unknown workflow type"):
            get_workflow_builder("nonexistent")
