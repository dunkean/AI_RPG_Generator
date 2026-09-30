"""Tests for LoRA injection into ComfyUI workflows."""

import copy

from src.image.comfyui.workflows.base import GenerationParams
from src.image.comfyui.workflows.flux import FluxWorkflow
from src.image.comfyui.workflows.sdxl_turbo import SDXLTurboWorkflow
from src.image.comfyui.workflows.qwen import QwenImageWorkflow
from src.image.comfyui.workflows.lora import LoRAEntry, inject_loras


PARAMS = GenerationParams(
    prompt="test", width=512, height=512, seed=42, negative=""
)


class TestLoRAInjectionFlux:
    """Flux uses LoraLoaderModelOnly (no clip routing)."""

    def test_single_lora(self):
        w = FluxWorkflow()
        payload = w.build(PARAMS)
        loras = [LoRAEntry(name="style.safetensors", strength_model=0.8)]
        inject_loras(payload, loras, model_node_id="1", clip_node_id=None)

        prompt = payload["prompt"]
        # A LoRA node was added
        lora_node = prompt["13"]  # next after 12
        assert lora_node["class_type"] == "LoraLoaderModelOnly"
        assert lora_node["inputs"]["lora_name"] == "style.safetensors"
        assert lora_node["inputs"]["strength_model"] == 0.8
        assert lora_node["inputs"]["model"] == ["1", 0]

        # Downstream model references now point to LoRA output
        assert prompt["6"]["inputs"]["model"] == ["13", 0]   # BasicGuider
        assert prompt["8"]["inputs"]["model"] == ["13", 0]   # BasicScheduler

    def test_multiple_loras_chain(self):
        w = FluxWorkflow()
        payload = w.build(PARAMS)
        loras = [
            LoRAEntry(name="lora1.safetensors", strength_model=0.7),
            LoRAEntry(name="lora2.safetensors", strength_model=0.5),
        ]
        inject_loras(payload, loras, model_node_id="1", clip_node_id=None)

        prompt = payload["prompt"]
        # First LoRA takes from model node 1
        assert prompt["13"]["inputs"]["model"] == ["1", 0]
        # Second LoRA chains from first
        assert prompt["14"]["inputs"]["model"] == ["13", 0]
        # Downstream references the last LoRA
        assert prompt["6"]["inputs"]["model"] == ["14", 0]

    def test_empty_loras_noop(self):
        w = FluxWorkflow()
        payload = w.build(PARAMS)
        original = copy.deepcopy(payload)
        inject_loras(payload, [], model_node_id="1", clip_node_id=None)
        assert payload == original


class TestLoRAInjectionCheckpoint:
    """Checkpoint-based models use LoraLoader (model + clip)."""

    def test_single_lora_with_clip(self):
        w = SDXLTurboWorkflow()
        payload = w.build(PARAMS)
        loras = [LoRAEntry(name="detail.safetensors", strength_model=0.9, strength_clip=0.6)]
        inject_loras(payload, loras, model_node_id="1", clip_node_id="1")

        prompt = payload["prompt"]
        lora_node = prompt["8"]  # next after 7
        assert lora_node["class_type"] == "LoraLoader"
        assert lora_node["inputs"]["lora_name"] == "detail.safetensors"
        assert lora_node["inputs"]["strength_model"] == 0.9
        assert lora_node["inputs"]["strength_clip"] == 0.6
        assert lora_node["inputs"]["model"] == ["1", 0]
        assert lora_node["inputs"]["clip"] == ["1", 1]

        # Downstream model refs rewired
        assert prompt["5"]["inputs"]["model"] == ["8", 0]
        # Downstream clip refs rewired
        assert prompt["2"]["inputs"]["clip"] == ["8", 1]
        assert prompt["3"]["inputs"]["clip"] == ["8", 1]

    def test_multiple_loras_checkpoint(self):
        w = SDXLTurboWorkflow()
        payload = w.build(PARAMS)
        loras = [
            LoRAEntry(name="a.safetensors"),
            LoRAEntry(name="b.safetensors"),
        ]
        inject_loras(payload, loras, model_node_id="1", clip_node_id="1")

        prompt = payload["prompt"]
        # First LoRA from checkpoint
        assert prompt["8"]["inputs"]["model"] == ["1", 0]
        assert prompt["8"]["inputs"]["clip"] == ["1", 1]
        # Second LoRA chains from first
        assert prompt["9"]["inputs"]["model"] == ["8", 0]
        assert prompt["9"]["inputs"]["clip"] == ["8", 1]
        # Downstream gets last LoRA
        assert prompt["5"]["inputs"]["model"] == ["9", 0]
        assert prompt["2"]["inputs"]["clip"] == ["9", 1]


def test_qwen_lora_preserves_text_encoder_and_sampling_shift():
    workflow = QwenImageWorkflow()
    payload = workflow.build(PARAMS)
    inject_loras(
        payload, [LoRAEntry(name="qwen_style.safetensors")],
        model_node_id=workflow.model_node_id, clip_node_id=workflow.clip_node_id,
    )
    graph = payload["prompt"]
    assert graph["11"]["class_type"] == "LoraLoaderModelOnly"
    assert graph["11"]["inputs"]["model"] == ["1", 0]
    assert graph["7"]["inputs"]["model"] == ["11", 0]
    assert graph["8"]["inputs"]["model"] == ["7", 0]
    assert graph["4"]["inputs"]["clip"] == ["2", 0]
    assert graph["5"]["inputs"]["clip"] == ["2", 0]
