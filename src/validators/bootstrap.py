"""Bootstrap validator — transforms LLM response into content patch."""

from __future__ import annotations

CATEGORY_KEYS = {
    "culture", "customs", "goals", "resources", "history",
    "external_influences", "timeline", "sites", "anecdotes",
}


def validate_bootstrap(response: dict) -> dict:
    """Transform bootstrap response into a patch for content dict.

    - Moves ``setting_setting`` into ``setting.keywords``
    - Wraps category lists in ``{"keywords": [...]}`` under ``details``
    - Everything else goes directly under ``details``
    """
    patch: dict = {
        "details": {},
        "setting": {},
    }

    # Handle setting keywords (was "setting_setting" or "world_setting")
    for key in ("setting_setting", "world_setting"):
        if key in response:
            patch["setting"]["keywords"] = response.pop(key)
            break

    for k, v in response.items():
        if k in CATEGORY_KEYS:
            patch["details"][k] = {"keywords": v}
        else:
            patch["details"][k] = v

    return patch
