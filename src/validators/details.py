"""Validators for detail and description steps."""

from __future__ import annotations


def validate_detail(response: dict) -> dict:
    """Wrap detail response in ``{"descriptions": ...}`` format under ``details``."""
    validated: dict = {}
    for k, v in response.items():
        validated[k] = {"descriptions": v}

    return {"details": validated}


def validate_descriptions(response: dict) -> dict:
    """Add ordering to long descriptions and wrap under ``details``."""
    descriptions = response.get("descriptions", response)
    if "long" in descriptions:
        descriptions["order"] = list(descriptions["long"].keys())
    return {"details": {"descriptions": descriptions}}
