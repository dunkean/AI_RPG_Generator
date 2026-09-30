"""Validator for activity groups / workplaces step."""

from __future__ import annotations

import shortuuid


def validate_activity_groups(content: dict, response: dict | list) -> dict:
    """Normalize population and create UUID-keyed workplace groups.

    - If response is a dict with a "groups" key, extract the list.
    - Filter out groups with population <= 3.
    - Normalize total population to match the target.
    """
    # Handle both list (from table parser) and dict (from JSON)
    if isinstance(response, dict):
        groups = response.get("groups", list(response.values()))
        if isinstance(groups, dict):
            groups = list(groups.values())
    else:
        groups = response

    # Filter out tiny groups
    valid_groups = [g for g in groups if g.get("population", 0) > 3]
    if not valid_groups:
        valid_groups = groups  # keep all if filtering removes everything

    # Normalize population to match target
    target_pop = content["details"]["population"]
    total_pop = sum(g.get("population", 0) for g in valid_groups)
    if total_pop > 0:
        factor = target_pop / total_pop
        for g in valid_groups:
            g["population"] = max(1, int(g.get("population", 0) * factor))

    return {
        "groups": {
            "activity": {shortuuid.uuid(): g for g in valid_groups}
        }
    }
