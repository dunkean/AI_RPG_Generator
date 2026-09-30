"""Workflow builder registry — maps type names to builder classes."""

from __future__ import annotations

from typing import Any

from .base import WorkflowBuilder
from .cogview import CogViewWorkflow
from .flux import FluxWorkflow
from .qwen import QwenImageWorkflow
from .sdxl_turbo import SDXLTurboWorkflow

_REGISTRY: dict[str, type[WorkflowBuilder]] = {
    "flux": FluxWorkflow,
    "sdxl_turbo": SDXLTurboWorkflow,
    "cogview": CogViewWorkflow,
    "qwen": QwenImageWorkflow,
}


def get_workflow_builder(
    workflow_type: str, params: dict[str, Any] | None = None
) -> WorkflowBuilder:
    """Look up and instantiate a workflow builder by type name.

    *params* are passed as keyword arguments to the builder constructor.
    """
    cls = _REGISTRY.get(workflow_type)
    if cls is None:
        available = ", ".join(sorted(_REGISTRY))
        raise ValueError(
            f"Unknown workflow type {workflow_type!r}. "
            f"Available: {available}"
        )
    return cls(**(params or {}))


def list_workflow_types() -> list[str]:
    """Return sorted list of registered workflow type names."""
    return sorted(_REGISTRY)
