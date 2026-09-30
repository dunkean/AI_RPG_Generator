"""Validator for external influences step."""

from __future__ import annotations

import shortuuid


def validate_external_influences(response: dict) -> dict:
    """Create UUID-keyed groups from external influences response."""
    for k, v in response.items():
        v["name"] = k

    return {
        "details": {
            "external_influences": {
                "groups": {shortuuid.uuid(): v for v in response.values()}
            }
        }
    }
