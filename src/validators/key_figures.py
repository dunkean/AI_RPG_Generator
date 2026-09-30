"""Validator for key figures (Step 11)."""

from __future__ import annotations


def validate_key_figure(response: dict) -> dict:
    """Merge detailed NPC bio into the npcs dict."""
    full_name = response.get("full_name", "")
    if full_name:
        return {"npcs": {full_name: response}}
    return {}
