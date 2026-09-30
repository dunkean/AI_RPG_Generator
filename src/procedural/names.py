"""Fantasy name generation using pynames (race-specific generators)."""

from __future__ import annotations

from pynames import GENDER
from pynames.generators.iron_kingdoms import (
    CaspianMidlunderSuleseFullnameGenerator,
    DwarfFullnameGenerator,
    IossanNyssFullnameGenerator,
    ThurianMorridaneFullnameGenerator,
    TordoranFullnameGenerator,
)
from pynames.generators.elven import DnDNamesGenerator

# Race -> pynames generator mapping
_GENERATORS: dict[str, object] = {
    "human": CaspianMidlunderSuleseFullnameGenerator(),
    "elf": DnDNamesGenerator(),
    "half-elf": DnDNamesGenerator(),
    "dwarf": DwarfFullnameGenerator(),
    "halfling": ThurianMorridaneFullnameGenerator(),
    "gnome": IossanNyssFullnameGenerator(),
}

# Fallback for group naming (outsider groups)
_GROUP_NAME_GEN = TordoranFullnameGenerator()


def _gender_enum(gender: str) -> object:
    return GENDER.MALE if gender.lower() == "male" else GENDER.FEMALE


def get_name(race: str, gender: str) -> tuple[str, str]:
    """Generate a (first_name, last_name) pair for a given race and gender."""
    gen = _GENERATORS.get(race.lower(), _GENERATORS["human"])
    gender_enum = _gender_enum(gender)
    full = str(gen.get_name(gender_enum))
    parts = full.split(" ", 1)
    first = parts[0]
    last = parts[1] if len(parts) > 1 else parts[0]
    return first, last


def get_last_name(race: str) -> str:
    """Generate a last name (surname) for a given race."""
    gen = _GENERATORS.get(race.lower(), _GENERATORS["human"])
    full = str(gen.get_name())
    return full.split(" ")[-1]


def get_first_name(race: str, gender: str) -> str:
    """Generate a first name for a given race and gender."""
    gen = _GENERATORS.get(race.lower(), _GENERATORS["human"])
    full = str(gen.get_name(_gender_enum(gender)))
    return full.split(" ")[0]


def get_group_name() -> str:
    """Generate a name for an outsider group."""
    return str(_GROUP_NAME_GEN.get_name_simple())
