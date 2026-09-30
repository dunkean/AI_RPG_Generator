"""Prompt context builder — selects relevant prior data for each prompt category."""

from __future__ import annotations

import json
from typing import Any

# Maps each prompt category to which prior content sections are relevant.
# Keys are top-level content keys; values are sub-keys to include.
CATEGORIES_TO_KEEP: dict[str, dict[str, list[str]]] = {
    "description": {
        "details": ["culture", "customs", "goals", "resources", "history",
                     "external_influences", "timeline", "anecdotes"],
    },
    "culture": {
        "details": ["culture", "customs", "goals", "resources", "history",
                     "external_influences", "timeline", "anecdotes"],
    },
    "customs": {
        "details": ["customs", "goals", "resources", "history",
                     "external_influences", "timeline", "anecdotes"],
    },
    "goals": {
        "details": ["customs", "goals", "resources", "history",
                     "external_influences", "timeline", "anecdotes"],
    },
    "resources": {
        "details": ["customs", "goals", "resources", "history",
                     "external_influences", "timeline", "anecdotes"],
    },
    "history": {
        "details": ["customs", "goals", "resources", "history",
                     "external_influences", "timeline", "anecdotes"],
    },
    "external_influences": {
        "details": ["customs", "goals", "resources", "history",
                     "external_influences", "timeline", "anecdotes"],
    },
    "timeline": {
        "details": ["customs", "goals", "resources", "history",
                     "external_influences", "timeline", "anecdotes"],
    },
    "sites": {
        "details": ["customs", "goals", "resources", "history",
                     "external_influences", "timeline", "anecdotes"],
    },
    "anecdotes": {
        "details": ["customs", "goals", "resources", "history",
                     "external_influences", "timeline", "anecdotes"],
    },
    "activity_groups": {
        "details": ["customs", "goals", "resources"],
    },
    "workplaces": {
        "details": ["customs", "resources", "history", "goals",
                     "external_influences", "sites"],
    },
    "families": {
        "details": ["resources", "customs", "history", "timeline", "sites"],
    },
}


def context_json(content: dict, category: str | None = None) -> dict[str, Any]:
    """Build a selective context dict for prompt construction.

    Always includes: name, type, structure, keywords, setting, population, prosperity.
    If *category* is given, also includes the keyword lists from relevant prior sections.
    """
    details = content["details"]

    prompt_json: dict[str, Any] = {
        "name": details["name"],
        "type": details["type"],
        "structure": details["structure"],
        "keywords": details["keywords"],
        "setting": content["setting"]["keywords"],
        "population": details["population"],
        "prosperity": details["prosperity"],
    }

    if category and category in CATEGORIES_TO_KEEP:
        for top_key, sub_keys in CATEGORIES_TO_KEEP[category].items():
            for sub_key in sub_keys:
                section = content.get(top_key, {}).get(sub_key, {})
                if isinstance(section, dict) and "keywords" in section:
                    prompt_json[sub_key] = section["keywords"]

    return prompt_json
