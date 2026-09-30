"""LoRA injection utility for ComfyUI workflows."""

from __future__ import annotations

import copy
from dataclasses import dataclass, field


@dataclass
class LoRAEntry:
    """A single LoRA to apply to a workflow."""

    name: str
    strength_model: float = 1.0
    strength_clip: float = 1.0


def _next_node_id(workflow_prompt: dict) -> str:
    """Return the next available integer node ID as a string."""
    max_id = max(int(k) for k in workflow_prompt)
    return str(max_id + 1)


def _rewire_references(
    workflow_prompt: dict,
    old_ref: tuple[str, int],
    new_ref: tuple[str, int],
    skip_node: str | None = None,
) -> None:
    """Replace all [old_node, old_slot] references with [new_node, new_slot].

    Skips the node *skip_node* itself to avoid self-references.
    """
    for node_id, node in workflow_prompt.items():
        if node_id == skip_node:
            continue
        for input_name, input_val in node.get("inputs", {}).items():
            if (
                isinstance(input_val, list)
                and len(input_val) == 2
                and input_val[0] == old_ref[0]
                and input_val[1] == old_ref[1]
            ):
                node["inputs"][input_name] = [new_ref[0], new_ref[1]]


def inject_loras(
    workflow: dict,
    loras: list[LoRAEntry],
    model_node_id: str = "1",
    clip_node_id: str | None = None,
) -> None:
    """Inject LoRA loader nodes into a ComfyUI workflow dict (in-place).

    For Flux-style workflows (no clip_node_id): uses ``LoraLoaderModelOnly``,
    chaining model output only.

    For checkpoint-style workflows (clip_node_id set): uses ``LoraLoader``,
    chaining both model and clip outputs.

    Multiple LoRAs are chained in sequence. Downstream nodes that referenced
    the original model/clip outputs are rewired to the last LoRA node.
    """
    if not loras:
        return

    prompt = workflow["prompt"]
    has_clip = clip_node_id is not None

    # Track current model/clip source as we chain LoRAs
    current_model_ref = (model_node_id, 0)
    current_clip_ref = (clip_node_id, 1) if has_clip else None

    # Collect original references before we start rewiring
    # We need to rewire everything that points to the original model/clip
    # after all LoRAs are inserted.
    original_model_ref = current_model_ref
    original_clip_ref = current_clip_ref

    lora_node_ids = []

    for lora in loras:
        node_id = _next_node_id(prompt)

        if has_clip:
            prompt[node_id] = {
                "class_type": "LoraLoader",
                "inputs": {
                    "lora_name": lora.name,
                    "strength_model": lora.strength_model,
                    "strength_clip": lora.strength_clip,
                    "model": [current_model_ref[0], current_model_ref[1]],
                    "clip": [current_clip_ref[0], current_clip_ref[1]],
                },
            }
            current_model_ref = (node_id, 0)
            current_clip_ref = (node_id, 1)
        else:
            prompt[node_id] = {
                "class_type": "LoraLoaderModelOnly",
                "inputs": {
                    "lora_name": lora.name,
                    "strength_model": lora.strength_model,
                    "model": [current_model_ref[0], current_model_ref[1]],
                },
            }
            current_model_ref = (node_id, 0)

        lora_node_ids.append(node_id)

    # Rewire: everything that referenced the original model/clip
    # (except the LoRA chain itself) should now reference the last LoRA output
    last_lora_id = lora_node_ids[-1]

    if current_model_ref != original_model_ref:
        _rewire_model_refs(
            prompt, original_model_ref, current_model_ref, lora_node_ids
        )

    if has_clip and current_clip_ref != original_clip_ref:
        _rewire_clip_refs(
            prompt, original_clip_ref, current_clip_ref, lora_node_ids
        )


def _rewire_model_refs(
    prompt: dict,
    original: tuple[str, int],
    new: tuple[str, int],
    skip_nodes: list[str],
) -> None:
    """Rewire model references from original to new, skipping LoRA chain nodes."""
    for node_id, node in prompt.items():
        if node_id in skip_nodes:
            continue
        for input_name, input_val in node.get("inputs", {}).items():
            if (
                isinstance(input_val, list)
                and len(input_val) == 2
                and input_val[0] == original[0]
                and input_val[1] == original[1]
                and input_name in ("model",)
            ):
                node["inputs"][input_name] = [new[0], new[1]]


def _rewire_clip_refs(
    prompt: dict,
    original: tuple[str, int],
    new: tuple[str, int],
    skip_nodes: list[str],
) -> None:
    """Rewire clip references from original to new, skipping LoRA chain nodes."""
    for node_id, node in prompt.items():
        if node_id in skip_nodes:
            continue
        for input_name, input_val in node.get("inputs", {}).items():
            if (
                isinstance(input_val, list)
                and len(input_val) == 2
                and input_val[0] == original[0]
                and input_val[1] == original[1]
                and input_name in ("clip",)
            ):
                node["inputs"][input_name] = [new[0], new[1]]
