"""Procedural appearance generation with race-specific tables and family inheritance."""

from __future__ import annotations

import random
from typing import Any

# ---------------------------------------------------------------------------
# Helper: weighted pick from {value: weight} table
# ---------------------------------------------------------------------------

def _pick(table: dict[str, float], rng: random.Random) -> str:
    """Pick a value from a weight table using the provided RNG."""
    keys = list(table.keys())
    weights = list(table.values())
    return rng.choices(keys, weights=weights, k=1)[0]


def _pick_for_race(table: dict[str, dict[str, float]], race: str, rng: random.Random) -> str:
    """Pick from a race-keyed table, falling back to 'human'."""
    subtable = table.get(race, table.get("human", {}))
    return _pick(subtable, rng)


def _pick_for_race_gender(
    table: dict[str, dict[str, dict[str, float]]], race: str, gender: str, rng: random.Random,
) -> str:
    """Pick from a table keyed by race then gender, falling back."""
    race_table = table.get(race, table.get("human", {}))
    subtable = race_table.get(gender, race_table.get("male", {}))
    return _pick(subtable, rng)


# ===========================================================================
# RACE-SPECIFIC FEATURE TABLES
# ===========================================================================

HAIR_COLOR: dict[str, dict[str, float]] = {
    "human": {
        "dark brown": 25, "black": 22, "light brown": 15, "auburn": 10,
        "dirty blonde": 8, "golden blonde": 7, "red": 5, "copper": 4,
        "chestnut": 2, "sandy": 2,
    },
    "elf": {
        "silver white": 15, "platinum blonde": 12, "golden blonde": 12,
        "midnight black": 10, "copper": 10, "honey blonde": 8,
        "pale green": 6, "moonlight blue": 5, "auburn": 5,
        "ash blonde": 5, "raven black": 5, "strawberry blonde": 4, "tawny": 3,
    },
    "half-elf": {
        "dark brown": 18, "light brown": 15, "golden blonde": 12, "black": 10,
        "auburn": 10, "copper": 8, "silver-streaked brown": 6,
        "honey blonde": 6, "chestnut": 5, "dirty blonde": 5, "ash blonde": 5,
    },
    "dwarf": {
        "fiery red": 20, "dark brown": 18, "black": 15, "auburn": 12,
        "copper": 10, "rust": 8, "sandy brown": 7, "iron gray": 5,
        "golden": 3, "dark red": 2,
    },
    "halfling": {
        "chestnut brown": 22, "sandy brown": 18, "dark brown": 15,
        "curly red": 12, "honey blonde": 10, "light brown": 8,
        "auburn": 6, "golden brown": 5, "tawny": 2, "strawberry blonde": 2,
    },
    "gnome": {
        "bright red": 18, "white": 15, "carrot orange": 12, "electric blue": 8,
        "mossy green": 7, "violet": 6, "sandy brown": 8, "silver": 6,
        "golden": 5, "pink-tinged": 5, "copper": 5, "teal": 3, "lavender": 2,
    },
}

HAIR_LENGTH: dict[str, dict[str, dict[str, float]]] = {
    "human": {
        "male": {"short": 35, "medium": 30, "long": 15, "very short": 10, "shaved": 10},
        "female": {"long": 30, "medium": 25, "very long": 15, "short": 15, "shoulder-length": 15},
    },
    "elf": {
        "male": {"long": 35, "very long": 25, "medium": 20, "waist-length": 10, "shoulder-length": 10},
        "female": {"very long": 30, "long": 25, "waist-length": 20, "medium": 15, "hip-length": 10},
    },
    "half-elf": {
        "male": {"medium": 30, "long": 25, "short": 20, "shoulder-length": 15, "very short": 10},
        "female": {"long": 30, "medium": 25, "very long": 15, "shoulder-length": 20, "short": 10},
    },
    "dwarf": {
        "male": {"long": 30, "medium": 25, "very long": 20, "short": 15, "shoulder-length": 10},
        "female": {"long": 30, "very long": 25, "medium": 20, "shoulder-length": 15, "waist-length": 10},
    },
    "halfling": {
        "male": {"short": 30, "medium": 30, "very short": 15, "curly short": 15, "long": 10},
        "female": {"medium": 30, "short": 20, "shoulder-length": 20, "long": 15, "curly medium": 15},
    },
    "gnome": {
        "male": {"wild medium": 25, "short": 20, "spiky short": 20, "medium": 15, "long": 10, "very short": 10},
        "female": {"medium": 25, "short": 20, "long": 15, "wild short": 15, "pixie cut": 15, "shoulder-length": 10},
    },
}

HAIR_STYLE: dict[str, dict[str, dict[str, float]]] = {
    "human": {
        "male": {"straight": 25, "wavy": 20, "unkempt": 15, "slicked back": 10, "tied back": 10, "curly": 10, "cropped": 10},
        "female": {"wavy": 25, "straight": 20, "braided": 15, "curly": 12, "tied up": 10, "loose": 10, "pinned up": 8},
    },
    "elf": {
        "male": {"straight and flowing": 30, "sleek": 20, "braided at temples": 15, "loose": 15, "half-up": 10, "windswept": 10},
        "female": {"flowing": 25, "intricately braided": 20, "straight and silky": 15, "adorned with small flowers": 10, "loose waves": 15, "half-braided": 10, "cascading": 5},
    },
    "half-elf": {
        "male": {"wavy": 25, "straight": 20, "partially braided": 15, "loose": 15, "tied back": 15, "tousled": 10},
        "female": {"wavy": 25, "half-braided": 20, "loose": 15, "straight": 15, "flowing": 15, "adorned": 10},
    },
    "dwarf": {
        "male": {"thick and braided": 30, "wild and bushy": 18, "tightly braided": 15, "unkempt": 12, "elaborately braided": 10, "loose and thick": 8, "coiled": 7},
        "female": {"braided": 25, "thick and wavy": 20, "elaborately braided": 15, "adorned with beads": 12, "coiled up": 10, "loose and thick": 10, "pinned with clasps": 8},
    },
    "halfling": {
        "male": {"curly": 30, "tousled": 20, "wavy": 18, "messy": 12, "combed back": 10, "straight": 10},
        "female": {"curly": 25, "wavy": 20, "bouncy": 15, "braided": 12, "pinned back": 10, "tousled": 10, "ribbon-tied": 8},
    },
    "gnome": {
        "male": {"wild and spiky": 25, "unkempt": 20, "sticking up": 15, "braided": 12, "bushy": 10, "flyaway": 10, "tufted": 8},
        "female": {"wild curls": 22, "messy bun": 15, "pigtails": 12, "frizzy": 12, "adorned with trinkets": 10, "bouncy": 10, "braided with ribbons": 10, "unkempt": 9},
    },
}

EYE_COLOR: dict[str, dict[str, float]] = {
    "human": {
        "brown": 35, "dark brown": 15, "hazel": 12, "blue": 10,
        "green": 8, "gray": 7, "amber": 5, "light blue": 4,
        "dark gray": 2, "olive": 2,
    },
    "elf": {
        "emerald green": 18, "bright blue": 12, "violet": 10,
        "silver": 10, "golden amber": 8, "pale blue": 8,
        "deep green": 7, "sapphire blue": 7, "amethyst": 5,
        "starlight gray": 5, "turquoise": 5, "pale gold": 5,
    },
    "half-elf": {
        "green": 18, "hazel": 15, "blue": 12, "brown": 10,
        "gray-green": 10, "amber": 8, "violet-tinged": 6,
        "light brown": 6, "silver-gray": 5, "teal": 5, "pale green": 5,
    },
    "dwarf": {
        "dark brown": 22, "brown": 18, "steel gray": 12, "deep blue": 10,
        "amber": 10, "black": 8, "dark green": 6, "iron gray": 5,
        "coal": 5, "copper": 4,
    },
    "halfling": {
        "warm brown": 25, "hazel": 18, "bright green": 15, "golden brown": 10,
        "blue": 8, "amber": 8, "dark brown": 6, "chestnut": 5, "olive": 5,
    },
    "gnome": {
        "bright blue": 18, "emerald green": 15, "golden": 12,
        "violet": 10, "amber": 8, "turquoise": 8, "heterochromatic": 5,
        "deep brown": 5, "pale gray": 5, "sparkling hazel": 5,
        "copper": 5, "sky blue": 4,
    },
}

EYE_SHAPE: dict[str, dict[str, float]] = {
    "human": {"round": 25, "almond": 25, "narrow": 15, "wide": 15, "deep-set": 10, "hooded": 10},
    "elf": {"almond": 40, "upturned": 25, "narrow and elegant": 15, "large and luminous": 10, "elongated": 10},
    "half-elf": {"almond": 30, "slightly upturned": 25, "wide": 15, "round": 15, "hooded": 15},
    "dwarf": {"deep-set": 30, "small and keen": 25, "round": 18, "narrow": 15, "hooded": 12},
    "halfling": {"round and bright": 30, "wide": 25, "large": 20, "sparkling": 15, "almond": 10},
    "gnome": {"large and round": 30, "bright and wide": 25, "sparkling": 18, "curious": 15, "almond": 12},
}

SKIN_TONE: dict[str, dict[str, float]] = {
    "human": {
        "fair": 15, "olive": 15, "tan": 15, "light brown": 12,
        "dark brown": 10, "pale": 8, "bronze": 8, "warm brown": 7,
        "ruddy": 5, "sallow": 3, "golden": 2,
    },
    "elf": {
        "porcelain": 15, "pale ivory": 12, "golden": 10, "bronze": 10,
        "alabaster": 8, "warm copper": 8, "moonlit silver": 6,
        "dusk brown": 6, "fair": 6, "olive": 5, "deep bronze": 5,
        "sun-kissed": 5, "tawny": 4,
    },
    "half-elf": {
        "fair": 15, "olive": 12, "light bronze": 12, "tan": 10,
        "warm ivory": 10, "golden": 8, "pale": 8, "sun-kissed": 8,
        "light brown": 7, "copper-tinged": 5, "bronze": 5,
    },
    "dwarf": {
        "ruddy": 18, "weathered tan": 15, "pale": 12, "dark bronze": 10,
        "fair": 10, "granite gray": 8, "sun-darkened": 8,
        "warm brown": 7, "copper": 6, "earthy brown": 6,
    },
    "halfling": {
        "warm tan": 20, "rosy": 18, "fair": 15, "golden brown": 12,
        "light brown": 10, "peach": 8, "sun-kissed": 7,
        "freckled": 5, "olive": 3, "honey": 2,
    },
    "gnome": {
        "rosy pink": 15, "warm tan": 12, "pale": 12, "golden": 10,
        "ruddy": 10, "earthy brown": 8, "olive": 8,
        "copper-tinged": 7, "dusky": 6, "sun-darkened": 5,
        "freckled": 4, "blue-tinged": 3,
    },
}

FACE_SHAPE: dict[str, dict[str, float]] = {
    "human": {"oval": 25, "round": 20, "square": 15, "long": 12, "heart-shaped": 10, "diamond": 8, "rectangular": 5, "triangular": 5},
    "elf": {"narrow and angular": 25, "heart-shaped": 20, "oval": 18, "high-cheekboned": 15, "delicate": 12, "diamond": 10},
    "half-elf": {"oval": 25, "angular": 15, "heart-shaped": 15, "slightly angular": 15, "round": 12, "high-cheekboned": 10, "diamond": 8},
    "dwarf": {"broad and square": 28, "round and wide": 20, "blocky": 15, "rectangular": 12, "broad": 10, "heavy-jawed": 10, "barrel-shaped": 5},
    "halfling": {"round": 30, "cherubic": 18, "oval": 15, "heart-shaped": 12, "soft and plump": 10, "wide": 8, "button-like": 7},
    "gnome": {"round": 25, "wide": 18, "triangular": 15, "pointed": 12, "heart-shaped": 10, "angular": 10, "small and compact": 10},
}

NOSE_SHAPE: dict[str, dict[str, float]] = {
    "human": {"straight": 25, "broad": 15, "aquiline": 12, "button": 10, "narrow": 10, "hooked": 8, "flat": 8, "snub": 7, "prominent": 5},
    "elf": {"narrow and straight": 30, "small and pointed": 22, "delicate": 18, "aquiline": 12, "elegant": 10, "refined": 8},
    "half-elf": {"straight": 25, "slightly pointed": 18, "narrow": 15, "delicate": 12, "aquiline": 10, "button": 10, "snub": 10},
    "dwarf": {"broad and flat": 25, "bulbous": 20, "broken-looking": 12, "wide": 12, "blunt": 10, "crooked": 8, "thick": 8, "prominent": 5},
    "halfling": {"small and round": 25, "button": 22, "snub": 18, "upturned": 12, "slightly pointed": 10, "broad": 8, "flat": 5},
    "gnome": {"large and bulbous": 25, "pointed": 20, "upturned": 15, "small and sharp": 12, "round": 10, "button": 10, "wide": 8},
}

LIP_SHAPE: dict[str, dict[str, float]] = {
    "human": {"thin": 22, "full": 20, "medium": 18, "wide": 12, "narrow": 10, "bow-shaped": 8, "pursed": 5, "thick": 5},
    "elf": {"thin and elegant": 25, "bow-shaped": 22, "delicate": 18, "narrow": 12, "full": 10, "refined": 8, "pale and thin": 5},
    "half-elf": {"medium": 22, "slightly full": 18, "bow-shaped": 15, "thin": 12, "full": 12, "delicate": 10, "wide": 6, "narrow": 5},
    "dwarf": {"thin and firm": 22, "wide": 18, "thick": 15, "full": 12, "set in a scowl": 10, "narrow": 10, "pursed": 8, "cracked": 5},
    "halfling": {"full": 28, "wide and smiling": 20, "rosy": 15, "bow-shaped": 12, "plump": 10, "thin": 8, "cupid's bow": 7},
    "gnome": {"wide": 22, "thin and expressive": 18, "smirking": 15, "full": 12, "pursed": 10, "bow-shaped": 10, "narrow": 8, "lopsided grin": 5},
}

CHIN_SHAPE: dict[str, dict[str, float]] = {
    "human": {"rounded": 22, "square": 18, "pointed": 12, "strong": 12, "weak": 8, "cleft": 8, "prominent": 8, "receding": 7, "broad": 5},
    "elf": {"pointed": 30, "narrow": 22, "delicate": 15, "angular": 12, "sharp": 10, "refined": 6, "small": 5},
    "half-elf": {"slightly pointed": 25, "rounded": 18, "angular": 15, "narrow": 12, "strong": 10, "delicate": 10, "square": 10},
    "dwarf": {"square and strong": 30, "broad": 20, "jutting": 15, "cleft": 12, "heavy": 10, "blocky": 8, "double": 5},
    "halfling": {"round": 28, "soft": 20, "small": 15, "dimpled": 12, "weak": 10, "button": 10, "receding": 5},
    "gnome": {"pointed": 25, "round": 20, "small and sharp": 15, "prominent": 12, "weak": 10, "narrow": 10, "jutting": 8},
}

HEIGHT: dict[str, dict[str, float]] = {
    "human": {"average": 35, "tall": 20, "short": 15, "very tall": 5, "very short": 5, "above average": 10, "below average": 10},
    "elf": {"tall": 35, "very tall": 15, "above average": 20, "average": 20, "slender tall": 10},
    "half-elf": {"above average": 25, "tall": 20, "average": 25, "below average": 10, "short": 5, "very tall": 5, "slender tall": 10},
    "dwarf": {"short": 45, "very short": 20, "below average": 15, "stocky short": 10, "average": 10},
    "halfling": {"very short": 40, "short": 35, "tiny": 10, "below average": 10, "average": 5},
    "gnome": {"very short": 35, "short": 30, "tiny": 15, "below average": 10, "average": 10},
}

WEIGHT: dict[str, dict[str, float]] = {
    "human": {"average": 35, "thin": 12, "chubby": 12, "muscular": 10, "fat": 5, "skinny": 5, "stocky": 8, "lean": 8, "broad": 5},
    "elf": {"thin": 30, "slender": 25, "lean": 20, "average": 15, "willowy": 10},
    "half-elf": {"average": 25, "lean": 20, "slender": 15, "thin": 10, "muscular": 10, "stocky": 5, "chubby": 5, "broad": 5, "athletic": 5},
    "dwarf": {"stocky": 30, "broad": 20, "muscular": 15, "chubby": 10, "fat": 5, "barrel-chested": 10, "average": 10},
    "halfling": {"plump": 25, "chubby": 20, "average": 20, "round": 10, "stocky": 10, "thin": 8, "fat": 7},
    "gnome": {"wiry": 25, "thin": 20, "average": 18, "stocky": 12, "plump": 10, "slight": 10, "round": 5},
}


# ===========================================================================
# GENERATION-BASED TABLES (old / mid / young)
# ===========================================================================

SKIN_TEXTURE_BY_GENERATION: dict[str, dict[str, float]] = {
    "young": {"smooth": 40, "soft": 25, "clear": 15, "fresh": 10, "unblemished": 10},
    "mid": {"weathered": 20, "lined": 18, "tanned": 15, "rough": 12, "smooth": 12, "calloused": 8, "sun-worn": 8, "scarred": 7},
    "old": {"wrinkled": 30, "deeply lined": 18, "weathered": 15, "leathery": 12, "spotted": 8, "thin and papery": 7, "sagging": 5, "rough": 5},
}

AGE_LOOK_BY_GENERATION: dict[str, dict[str, float]] = {
    "young": {"young": 45, "younger": 20, "youthful": 15, "adolescent": 10, "adult": 10},
    "mid": {"adult": 35, "middle-aged": 30, "mature": 15, "young": 10, "old": 10},
    "old": {"old": 40, "elderly": 20, "aged": 15, "older": 10, "middle-aged": 15},
}

# Elf age look modifier — elves look younger than their generation suggests
ELF_AGE_LOOK_MODIFIER: dict[str, dict[str, float]] = {
    "young": {"younger": 30, "young": 30, "youthful": 25, "adolescent": 15},
    "mid": {"young": 35, "youthful": 25, "adult": 20, "younger": 10, "mature": 10},
    "old": {"adult": 30, "mature": 25, "middle-aged": 20, "young": 10, "old": 10, "aged": 5},
}

FACIAL_HAIR: dict[str, dict[str, dict[str, float]]] = {
    "human": {
        "young": {"clean-shaven": 50, "light stubble": 20, "thin mustache": 10, "short goatee": 10, "patchy beard": 10},
        "mid": {"short beard": 20, "full beard": 15, "mustache": 12, "goatee": 12, "stubble": 15, "clean-shaven": 18, "sideburns": 8},
        "old": {"full beard": 25, "long beard": 15, "bushy mustache": 12, "short beard": 12, "goatee": 10, "stubble": 8, "clean-shaven": 10, "mutton chops": 8},
    },
    "elf": {
        "young": {"clean-shaven": 95, "barely visible stubble": 5},
        "mid": {"clean-shaven": 90, "barely visible stubble": 7, "thin sideburns": 3},
        "old": {"clean-shaven": 80, "wispy beard": 8, "thin goatee": 7, "barely visible stubble": 5},
    },
    "half-elf": {
        "young": {"clean-shaven": 60, "light stubble": 20, "thin mustache": 10, "patchy": 10},
        "mid": {"clean-shaven": 30, "short beard": 18, "stubble": 18, "goatee": 12, "mustache": 12, "light stubble": 10},
        "old": {"short beard": 22, "full beard": 15, "goatee": 15, "clean-shaven": 15, "mustache": 12, "stubble": 10, "bushy mustache": 6, "long beard": 5},
    },
    "dwarf": {
        "young": {"short braided beard": 25, "stubble": 20, "thin beard": 18, "short beard": 15, "goatee": 12, "clean-shaven": 10},
        "mid": {"thick braided beard": 25, "full braided beard": 20, "bushy beard": 15, "elaborate braided beard": 10, "forked beard": 10, "long beard": 10, "wide beard": 10},
        "old": {"massive braided beard": 25, "long flowing beard": 20, "ornately braided beard": 15, "forked and beaded beard": 12, "chest-length beard": 10, "wild bushy beard": 10, "ancient braided beard": 8},
    },
    "halfling": {
        "young": {"clean-shaven": 70, "peach fuzz": 15, "thin sideburns": 10, "light stubble": 5},
        "mid": {"clean-shaven": 40, "sideburns": 20, "thin mustache": 15, "short mutton chops": 10, "light stubble": 10, "small goatee": 5},
        "old": {"bushy sideburns": 20, "thin mustache": 15, "clean-shaven": 15, "small beard": 12, "mutton chops": 12, "goatee": 10, "wispy beard": 8, "handlebar mustache": 8},
    },
    "gnome": {
        "young": {"clean-shaven": 55, "thin mustache": 15, "goatee": 10, "stubble": 10, "unusual shaped sideburns": 10},
        "mid": {"elaborate mustache": 20, "pointed goatee": 15, "bushy mustache": 12, "short beard": 12, "clean-shaven": 12, "curled mustache": 10, "braided goatee": 10, "wild sideburns": 9},
        "old": {"long pointed beard": 20, "wild bushy beard": 15, "elaborate curled mustache": 12, "braided beard with trinkets": 12, "enormous mustache": 10, "forked beard": 10, "flowing white beard": 10, "goatee": 6, "clean-shaven": 5},
    },
}


# ===========================================================================
# NON-RACE-SPECIFIC TABLES
# ===========================================================================

PHYSICAL_DETAIL: dict[str, float] = {
    "None": 35,
    "a scar across the cheek": 5, "a scar on the forehead": 4,
    "a tattoo on the arm": 4, "a facial tattoo": 3,
    "a birthmark on the neck": 4, "a birthmark on the cheek": 3,
    "a missing tooth": 4, "several missing teeth": 2,
    "a crooked nose": 3, "a broken nose": 3,
    "freckles across the nose": 4, "heavy freckles": 2,
    "a mole on the chin": 3, "a prominent mole": 2,
    "burn scars on the hands": 2, "burn scars on the face": 1,
    "a milky blind eye": 2, "heterochromatic eyes": 1,
    "a limp": 2, "missing fingers": 1,
    "pockmarked skin": 2, "calloused hands": 3,
    "a long scar across the neck": 1, "a cleft lip": 1,
}

CLOTHING_MATERIAL: dict[str, float] = {
    "wool": 20, "linen": 18, "leather": 15, "cotton": 15,
    "rough-spun": 8, "canvas": 5, "silk": 4,
    "fur-trimmed": 5, "velvet": 3, "chain-backed": 2,
    "homespun": 3, "burlap": 2,
}

CLOTHING_COLOR: dict[str, float] = {
    "brown": 18, "gray": 12, "forest green": 8, "dark blue": 8,
    "off-white": 7, "black": 7, "tan": 7, "dark red": 5,
    "faded blue": 5, "russet": 5, "cream": 4, "charcoal": 4,
    "olive": 3, "burgundy": 3, "teal": 2, "mustard": 2,
}

CLOTHING_STYLE_BY_GENDER: dict[str, dict[str, float]] = {
    "male": {
        "tunic and breeches": 25, "loose shirt and trousers": 18,
        "jerkin and pants": 12, "vest and work pants": 10,
        "robes": 8, "doublet and hose": 6,
        "simple shirt and shorts": 5, "overalls": 4,
        "tabard over chainmail": 3, "traveling cloak and trousers": 4,
        "apron over shirt": 3, "padded jacket and breeches": 2,
    },
    "female": {
        "simple dress": 20, "blouse and skirt": 15,
        "practical dress with apron": 12, "tunic and trousers": 10,
        "layered robes": 8, "bodice and skirt": 8,
        "traveling dress": 6, "work dress": 6,
        "corseted gown": 4, "loose shirt and breeches": 5,
        "smock": 3, "shawl-wrapped dress": 3,
    },
}

CLOTHING_ACCESSORY: dict[str, float] = {
    "none": 30,
    "belt with pouch": 12, "hooded cloak": 10,
    "leather gloves": 6, "scarf": 5,
    "wide-brimmed hat": 4, "bandana": 4,
    "necklace": 3, "bracelet": 3,
    "ring": 3, "earring": 2,
    "sash": 3, "shoulder bag": 3,
    "brooch": 2, "arm wraps": 2,
    "knee-high boots": 3, "fur-lined cape": 2,
    "feathered cap": 1, "eye patch": 1, "spectacles": 1,
}

PORTRAIT_POV: dict[str, float] = {
    "front view": 30,
    "three-quarter view": 25,
    "slight left angle": 10,
    "slight right angle": 10,
    "profile left": 5,
    "profile right": 5,
    "looking over shoulder": 5,
    "slightly from below": 5,
    "slightly from above": 5,
}


# ===========================================================================
# FAMILY INHERITANCE
# ===========================================================================

# Traits that can be inherited and their probability of inheriting from a parent
HERITABLE_TRAITS: dict[str, float] = {
    "hair_color": 0.70,
    "eye_color": 0.65,
    "skin_tone": 0.80,
    "face_shape": 0.55,
    "nose_shape": 0.50,
    "lip_shape": 0.45,
    "chin_shape": 0.50,
}

# Positions that are children (inherit from parents at full rate)
CHILD_POSITIONS: set[str] = {
    "son", "daughter", "eldest son", "eldest daughter",
    "youngest son", "youngest daughter", "child", "eldest child",
    "youngest child", "grandson", "granddaughter", "grandchild",
}

# Positions that are extended family (reduced inheritance rate)
UNCLE_AUNT_POSITIONS: set[str] = {"uncle", "aunt", "pibling"}
COUSIN_POSITIONS: set[str] = {"cousin"}

# Inheritance multiplier for extended family
UNCLE_AUNT_INHERITANCE_MULT = 0.40 / 0.70  # ~0.57 of base rate
COUSIN_INHERITANCE_MULT = 0.25 / 0.70  # ~0.36 of base rate


# ===========================================================================
# GENERATION FUNCTIONS
# ===========================================================================

def generate_clothing(gender: str, rng: random.Random) -> dict[str, str]:
    """Generate a clothing set for an NPC."""
    return {
        "clothing_material": _pick(CLOTHING_MATERIAL, rng),
        "clothing_color": _pick(CLOTHING_COLOR, rng),
        "clothing_style": _pick(CLOTHING_STYLE_BY_GENDER.get(gender, CLOTHING_STYLE_BY_GENDER["male"]), rng),
        "clothing_accessory": _pick(CLOTHING_ACCESSORY, rng),
    }


def pick_portrait_pov(rng: random.Random) -> str:
    """Pick a portrait point-of-view angle."""
    return _pick(PORTRAIT_POV, rng)


def apply_age_modifiers(appearance: dict[str, str], generation: str, race: str, rng: random.Random) -> None:
    """Apply age-based modifiers to appearance (graying hair, skin texture).

    Modifies appearance dict in-place.
    """
    # Skin texture is always from generation table
    appearance["skin_texture"] = _pick(
        SKIN_TEXTURE_BY_GENERATION.get(generation, SKIN_TEXTURE_BY_GENERATION["mid"]), rng,
    )

    # Age look — elves use modifier table
    if race in ("elf", "half-elf"):
        appearance["age_look"] = _pick(
            ELF_AGE_LOOK_MODIFIER.get(generation, ELF_AGE_LOOK_MODIFIER["mid"]), rng,
        )
    else:
        appearance["age_look"] = _pick(
            AGE_LOOK_BY_GENERATION.get(generation, AGE_LOOK_BY_GENERATION["mid"]), rng,
        )

    # Hair graying for older NPCs
    if generation == "old" and rng.random() < 0.60:
        color = appearance.get("hair_color", "")
        prefix = rng.choice(["gray-streaked", "silver-streaked", "white-streaked", "graying"])
        appearance["hair_color"] = f"{prefix} {color}"
    elif generation == "mid" and rng.random() < 0.15:
        color = appearance.get("hair_color", "")
        prefix = rng.choice(["slightly graying", "gray-touched", "silver-touched"])
        appearance["hair_color"] = f"{prefix} {color}"


def generate_family_phenotype(family_race: str, rng: random.Random) -> dict[str, dict[str, str]]:
    """Generate heritable traits for both parents of a family.

    Returns {"father": {trait: value, ...}, "mother": {trait: value, ...}}.
    For half-elf families, each parent uses their individual race tables.
    """
    phenotype: dict[str, dict[str, str]] = {}

    for parent, parent_race in [("father", family_race), ("mother", family_race)]:
        # For half-elf families, assign different races to parents
        if family_race == "half-elf":
            parent_race = "human" if parent == "father" else "elf"

        traits: dict[str, str] = {}
        traits["hair_color"] = _pick_for_race(HAIR_COLOR, parent_race, rng)
        traits["eye_color"] = _pick_for_race(EYE_COLOR, parent_race, rng)
        traits["skin_tone"] = _pick_for_race(SKIN_TONE, parent_race, rng)
        traits["face_shape"] = _pick_for_race(FACE_SHAPE, parent_race, rng)
        traits["nose_shape"] = _pick_for_race(NOSE_SHAPE, parent_race, rng)
        traits["lip_shape"] = _pick_for_race(LIP_SHAPE, parent_race, rng)
        traits["chin_shape"] = _pick_for_race(CHIN_SHAPE, parent_race, rng)
        phenotype[parent] = traits

    return phenotype


def generate_appearance(
    race: str,
    gender: str,
    generation: str,
    rng: random.Random,
    family_phenotype: dict[str, dict[str, str]] | None = None,
    position: str = "",
) -> dict[str, str]:
    """Generate a full appearance dict for an NPC.

    If family_phenotype is provided and the position is a child/relative,
    heritable traits may be inherited from parents.
    """
    appearance: dict[str, str] = {}

    # --- Heritable traits (may inherit from family) ---
    trait_tables: dict[str, Any] = {
        "hair_color": (HAIR_COLOR, "race"),
        "eye_color": (EYE_COLOR, "race"),
        "skin_tone": (SKIN_TONE, "race"),
        "face_shape": (FACE_SHAPE, "race"),
        "nose_shape": (NOSE_SHAPE, "race"),
        "lip_shape": (LIP_SHAPE, "race"),
        "chin_shape": (CHIN_SHAPE, "race"),
    }

    # Determine inheritance multiplier based on position
    inheritance_mult = 0.0
    pos_lower = position.lower()
    if family_phenotype:
        if pos_lower in {p.lower() for p in CHILD_POSITIONS}:
            inheritance_mult = 1.0
        elif pos_lower in {p.lower() for p in UNCLE_AUNT_POSITIONS}:
            inheritance_mult = UNCLE_AUNT_INHERITANCE_MULT
        elif pos_lower in {p.lower() for p in COUSIN_POSITIONS}:
            inheritance_mult = COUSIN_INHERITANCE_MULT
        # Parents themselves don't inherit (they ARE the source)

    for trait, (table, _) in trait_tables.items():
        inherited = False
        if family_phenotype and inheritance_mult > 0:
            base_prob = HERITABLE_TRAITS[trait]
            prob = base_prob * inheritance_mult
            if rng.random() < prob:
                # Pick from father or mother (50/50)
                parent = rng.choice(["father", "mother"])
                parent_value = family_phenotype.get(parent, {}).get(trait)
                if parent_value:
                    appearance[trait] = parent_value
                    inherited = True

        if not inherited:
            appearance[trait] = _pick_for_race(table, race, rng)

    # --- Non-heritable traits (always random) ---
    appearance["hair_length"] = _pick_for_race_gender(HAIR_LENGTH, race, gender, rng)
    appearance["hair_style"] = _pick_for_race_gender(HAIR_STYLE, race, gender, rng)
    appearance["eye_shape"] = _pick_for_race(EYE_SHAPE, race, rng)
    appearance["height"] = _pick_for_race(HEIGHT, race, rng)
    appearance["weight"] = _pick_for_race(WEIGHT, race, rng)
    appearance["physical_detail"] = _pick(PHYSICAL_DETAIL, rng)
    appearance["portrait_pov"] = pick_portrait_pov(rng)

    # Facial hair — males only
    if gender == "male":
        facial_hair_table = FACIAL_HAIR.get(race, FACIAL_HAIR.get("human", {}))
        gen_table = facial_hair_table.get(generation, facial_hair_table.get("mid", {}))
        appearance["facial_hair"] = _pick(gen_table, rng)
    else:
        appearance["facial_hair"] = ""

    # Clothing
    clothing = generate_clothing(gender, rng)
    appearance.update(clothing)

    # Age modifiers (graying hair, skin texture, age_look)
    apply_age_modifiers(appearance, generation, race, rng)

    return appearance


# ---------------------------------------------------------------------------
# Composite field builders (backward-compatible summary fields)
# ---------------------------------------------------------------------------

def build_composite_fields(appearance: dict[str, str]) -> dict[str, str]:
    """Build backward-compatible composite fields from granular appearance data.

    Returns a dict with 'hair', 'eyes', 'skin', 'clothes' keys.
    """
    hair_parts = [appearance.get("hair_length", ""), appearance.get("hair_style", ""), appearance.get("hair_color", "")]
    hair = " ".join(p for p in hair_parts if p)

    eye_parts = [appearance.get("eye_shape", ""), appearance.get("eye_color", "")]
    eyes = " ".join(p for p in eye_parts if p)

    skin_parts = [appearance.get("skin_texture", ""), appearance.get("skin_tone", "")]
    skin = " ".join(p for p in skin_parts if p)

    clothes_parts = [
        appearance.get("clothing_color", ""),
        appearance.get("clothing_material", ""),
        appearance.get("clothing_style", ""),
    ]
    clothes = " ".join(p for p in clothes_parts if p)
    accessory = appearance.get("clothing_accessory", "")
    if accessory and accessory != "none":
        clothes = f"{clothes}, {accessory}"

    return {"hair": hair, "eyes": eyes, "skin": skin, "clothes": clothes}
