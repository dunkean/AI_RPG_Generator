"""Validators for architecture steps (Step 10)."""

from __future__ import annotations


def validate_architecture(response: dict) -> dict:
    """Wrap global architecture data under the architecture key."""
    return {"architecture": response}


def validate_workplace_sites(response: dict) -> dict:
    """Merge per-workplace site architecture into sites data."""
    return {"_workplace_sites": response}
