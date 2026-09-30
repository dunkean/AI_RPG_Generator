"""Validator for population details (Step 6)."""

from __future__ import annotations

# Visual fields that are now procedurally generated — strip if the LLM returns them
_VISUAL_FIELDS_TO_STRIP = {
    "clothes", "eyes", "hair", "skin", "height", "weight",
    "age_look", "physical_detail",
}


def validate_population_details(response: dict) -> dict:
    """Merge enriched NPC attributes into content npcs.

    Response has {"members": [{"full_name": ..., ...}]}
    Returns a patch that updates the NPCs dict.
    Strips old visual fields that are now generated procedurally.
    """
    members = response.get("members", [])
    if not members and isinstance(response, list):
        members = response

    patch: dict = {"npcs": {}}

    # We can't easily map back to NPC UUIDs here without the content dict,
    # so we store by full_name and let the pipeline do the mapping.
    for member in members:
        full_name = member.get("full_name", "")
        if full_name:
            # Strip visual fields the LLM may still return
            cleaned = {
                k: v for k, v in member.items()
                if k not in _VISUAL_FIELDS_TO_STRIP
            }
            patch["npcs"][full_name] = cleaned

    return patch
