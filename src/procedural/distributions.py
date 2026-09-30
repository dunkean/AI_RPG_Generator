"""Statistical data and weight tables for procedural generation."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Age weights per situation/position  [old, mid, young]
# ---------------------------------------------------------------------------

AGE_WEIGHTS_PER_SITUATION: dict[str, list[float]] = {
    "old member": [0.4, 0.55, 0.05],
    "recent member": [0.05, 0.55, 0.4],
    "chief": [0.6, 0.3, 0.1],
    "vice-chief": [0.1, 0.6, 0.3],
    "underling": [0.05, 0.55, 0.4],
    "newbie": [0.05, 0.35, 0.6],
    "follower": [0.05, 0.55, 0.4],
    "old follower": [0.4, 0.55, 0.05],
    "grandparent": [0.6, 0.3, 0.1],
    "grandmother": [0.6, 0.3, 0.1],
    "grandfather": [0.6, 0.3, 0.1],
    "parent": [0.3, 0.6, 0.1],
    "mother": [0.3, 0.6, 0.1],
    "father": [0.3, 0.6, 0.1],
    "child": [0.05, 0.4, 0.55],
    "son": [0.05, 0.4, 0.55],
    "daughter": [0.05, 0.4, 0.55],
    "grandchild": [0.05, 0.25, 0.7],
    "grandson": [0.05, 0.25, 0.7],
    "granddaughter": [0.05, 0.25, 0.7],
    "cousin": [0.05, 0.55, 0.4],
    "pibling": [0.4, 0.5, 0.1],
    "uncle": [0.5, 0.5, 0.1],
    "aunt": [0.5, 0.5, 0.1],
    "boss": [0.6, 0.3, 0.1],
    "adventurer": [0.2, 0.6, 0.2],
    "on the run": [0.2, 0.6, 0.2],
    "traveler": [0.2, 0.6, 0.2],
    "wanderer": [0.3, 0.5, 0.2],
    "assignment": [0.2, 0.6, 0.2],
    "quest": [0.2, 0.6, 0.2],
    "eldest child": [0.05, 0.55, 0.4],
    "youngest child": [0.05, 0.35, 0.6],
    "eldest son": [0.05, 0.55, 0.4],
    "youngest son": [0.05, 0.35, 0.6],
    "eldest daughter": [0.05, 0.55, 0.4],
    "youngest daughter": [0.05, 0.35, 0.6],
    "prominent member": [0.3, 0.5, 0.2],
    "member": [0.2, 0.5, 0.3],
    "external employee": [0.1, 0.6, 0.3],
}


# ---------------------------------------------------------------------------
# Age weight dict — maps LLM age-range strings to generation weights
# ---------------------------------------------------------------------------

AGE_WEIGHT_DICT: dict[str, dict[str, float]] = {
    "old": {"old": 1, "mid": 0.1, "young": 0.02},
    "olds": {"old": 1, "mid": 0.1, "young": 0.02},
    "olds and mid": {"old": 1, "mid": 1, "young": 0.1},
    "old and mid": {"old": 1, "mid": 1, "young": 0.1},
    "mid": {"old": 0.1, "mid": 1, "young": 0.1},
    "young": {"old": 0.02, "mid": 0.1, "young": 1},
    "young and mid": {"old": 0.1, "mid": 1, "young": 1},
    "youngs": {"old": 0.02, "mid": 0.1, "young": 1},
    "old_mix": {"old": 0.5, "mid": 0.25, "young": 0.02},
    "old mix": {"old": 0.5, "mid": 0.25, "young": 0.02},
    "olds mix": {"old": 0.5, "mid": 0.25, "young": 0.02},
    "mid_mix": {"old": 0.25, "mid": 0.5, "young": 0.25},
    "mid mix": {"old": 0.25, "mid": 0.5, "young": 0.25},
    "young_mix": {"old": 0.02, "mid": 0.25, "young": 0.5},
    "young mix": {"old": 0.02, "mid": 0.25, "young": 0.5},
    "young and mix": {"old": 0.02, "mid": 0.25, "young": 0.5},
    "mix": {"old": 0.3, "mid": 0.4, "young": 0.3},
    "all": {"old": 0.3, "mid": 0.4, "young": 0.3},
}


def age_weight(ages: str, generation: str) -> float:
    """Look up the weight for a given age range and generation category."""
    ages_key = ages.lower().replace("_", " ")
    if ages_key not in AGE_WEIGHT_DICT:
        ages_key = "mix"  # safe fallback
    return AGE_WEIGHT_DICT[ages_key].get(generation.lower(), 0.3)


# ---------------------------------------------------------------------------
# Position pools — family and non-family groups
# ---------------------------------------------------------------------------

FAMILY_POSITIONS: dict[str, dict[str, dict[str, float]]] = {
    "male": {
        "default": {"son": 0.6, "cousin": 0.1, "uncle": 0.1, "grandson": 0.1},
        "pool": {
            "father": 1.0,
            "grandfather": 0.2,
            "eldest son": 0.4,
            "son": 0.2,
            "grandson": 0.2,
            "youngest son": 0.2,
            "cousin": 0.2,
            "uncle": 0.1,
        },
    },
    "female": {
        "default": {"daughter": 0.6, "cousin": 0.1, "aunt": 0.1, "granddaughter": 0.1},
        "pool": {
            "mother": 1.0,
            "grandmother": 0.2,
            "eldest daughter": 0.4,
            "daughter": 0.2,
            "granddaughter": 0.2,
            "youngest daughter": 0.2,
            "cousin": 0.2,
            "aunt": 0.1,
        },
    },
}

OUTSIDER_POSITIONS: dict[str, dict[str, dict[str, float]]] = {
    "friends": {
        "default": {"old member": 0.7, "recent member": 0.3},
        "pool": {},
    },
    "colleagues": {
        "default": {"vice-chief": 0.1, "underling": 0.85, "newbie": 0.05},
        "pool": {"chief": 1.0, "vice-chief": 0.5, "underling": 0.5, "newbie": 0.4},
    },
    "allies": {
        "default": {"prominent member": 0.2, "member": 0.8},
        "pool": {},
    },
    "common goal": {
        "default": {"prominent member": 0.2, "member": 0.8},
        "pool": {},
    },
    "common status": {
        "default": {"prominent member": 0.2, "member": 0.8},
        "pool": {},
    },
    "strangers": {
        "default": {"adventurer": 0.3, "on the run": 0.2, "wanderer": 0.2,
                     "traveler": 0.2, "external employee": 0.1},
        "pool": {},
    },
    "solo": {
        "default": {"adventurer": 0.3, "on the run": 0.2, "wanderer": 0.2,
                     "traveler": 0.2, "external employee": 0.1},
        "pool": {},
    },
}


# ---------------------------------------------------------------------------
# Workplace assignment filters
# ---------------------------------------------------------------------------

GROUP_FILTERS: dict[str, dict[str, tuple[dict, dict]]] = {
    "family": {
        "natives": ({"outsiders": 0.001}, {"family_type": 10}),
        "mix": ({"outsiders": 0.2}, {"family_type": 10}),
        "outsiders": ({"natives": 0.001}, {"family_type": 10}),
    },
    "cooperative": {
        "natives": ({"outsiders": 0.001}, {"family_type": 10}),
        "mix": ({"outsiders": 0.2}, {"family_type": 10}),
        "outsiders": ({"natives": 0.001}, {"family_type": 10}),
    },
    "guild": {
        "natives": ({"outsiders": 0.2}, {"hierarchy_type": 5, "cult_type": 2}),
        "mix": ({}, {"hierarchy_type": 5, "cult_type": 2}),
        "outsiders": ({"natives": 0.2}, {"hierarchy_type": 5, "cult_type": 2}),
    },
    "crew": {
        "natives": ({"outsiders": 0.05}, {"hierarchy_type": 2, "team_type": 5, "cult_type": 5}),
        "mix": ({}, {"hierarchy_type": 2, "team_type": 5, "cult_type": 5}),
        "outsiders": ({"natives": 0.05}, {"hierarchy_type": 2, "team_type": 5, "cult_type": 5}),
    },
    "illegal": {
        "natives": ({"outsiders": 0.2}, {"hierarchy_type": 10, "team_type": 0.2, "family_type": 2, "cult_type": 3}),
        "mix": ({}, {"hierarchy_type": 10, "team_type": 0.2, "family_type": 2, "cult_type": 3}),
        "outsiders": ({"natives": 0.4}, {"hierarchy_type": 10, "team_type": 0.2, "family_type": 2, "cult_type": 3}),
    },
    "company": {
        "natives": ({"outsiders": 0.2}, {"hierarchy_type": 10, "team_type": 0.2, "family_type": 2, "cult_type": 3}),
        "mix": ({}, {"hierarchy_type": 10, "team_type": 0.2, "family_type": 2, "cult_type": 3}),
        "outsiders": ({"natives": 0.4}, {"hierarchy_type": 10, "team_type": 0.2, "family_type": 2, "cult_type": 3}),
    },
    "council": {
        "natives": ({"outsiders": 0.001}, {}),
        "mix": ({"outsiders": 0.5}, {}),
        "outsiders": ({"natives": 0.05}, {}),
    },
    "team": {
        "natives": ({"outsiders": 0.1}, {"hierarchy_type": 0.5, "team_type": 10, "family_type": 2, "cult_type": 0.2}),
        "mix": ({}, {"hierarchy_type": 0.5, "team_type": 10, "family_type": 2, "cult_type": 0.2}),
        "outsiders": ({"natives": 0.2}, {"hierarchy_type": 0.5, "team_type": 10, "family_type": 2, "cult_type": 0.2}),
    },
}

# Individual selection weights by workplace type and composition
GROUP_WEIGHTS_IND: dict[str, dict[str, float]] = {
    "family": {"natives": 0.1, "mix": 0.2, "outsiders": 0.1},
    "cooperative": {"natives": 0.1, "mix": 0.2, "outsiders": 0.1},
    "guild": {"natives": 0.3, "mix": 0.5, "outsiders": 0.2},
    "crew": {"natives": 0.05, "mix": 0.05, "outsiders": 0.1},
    "company": {"natives": 0.4, "mix": 0.5, "outsiders": 0.4},
    "council": {"natives": 0.4, "mix": 0.05, "outsiders": 0.05},
    "team": {"natives": 0.1, "mix": 0.3, "outsiders": 0.2},
    "illegal": {"natives": 0.1, "mix": 0.3, "outsiders": 0.7},
}


# ---------------------------------------------------------------------------
# LLM string normalization
# ---------------------------------------------------------------------------

TRANSLATION_DICT: dict[str, str] = {
    "mixture": "mix",
    "band": "crew",
    "coven": "guild",
    "corporation": "company",
    "business": "company",
    # LLM structure types -> assignment system types
    "collaborative": "cooperative",
    "hierarchy": "guild",
    "decentralized": "team",
    "despotism": "company",
    "anarchy": "crew",
    "democracy": "council",
    # Common LLM variations
    "hierarchical": "guild",
    "service group": "team",
    "resource group": "team",
    "crafting group": "cooperative",
    "fighting group": "crew",
    "criminal group": "illegal",
    "faction": "guild",
}


def translate(word: str) -> str:
    """Normalize LLM-generated type/composition strings."""
    return TRANSLATION_DICT.get(word.lower(), word.lower())
