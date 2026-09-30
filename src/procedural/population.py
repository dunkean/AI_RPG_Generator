"""Social group generation and NPC population — Steps 5."""

from __future__ import annotations

import random
from copy import deepcopy

import numpy as np
from numpy import random as npr
import shortuuid

from . import names
from .appearance import (
    build_composite_fields,
    generate_appearance,
    generate_family_phenotype,
)
from .distributions import (
    AGE_WEIGHTS_PER_SITUATION,
    FAMILY_POSITIONS,
    OUTSIDER_POSITIONS,
)


# ---------------------------------------------------------------------------
# Family member generation
# ---------------------------------------------------------------------------

def _pick_position(pool: dict[str, float], default: dict[str, float]) -> str:
    """Pick a position from the pool (depleting it), falling back to default."""
    if pool:
        keys = list(pool.keys())
        weights = list(pool.values())
        chosen = random.choices(keys, weights=weights, k=1)[0]
        del pool[chosen]
        return chosen
    else:
        keys = list(default.keys())
        weights = list(default.values())
        return random.choices(keys, weights=weights, k=1)[0]


def _get_generation(situation: str) -> str:
    """Choose old/mid/young based on situation weights."""
    weights = AGE_WEIGHTS_PER_SITUATION.get(situation, [0.2, 0.5, 0.3])
    return random.choices(["old", "mid", "young"], weights=weights, k=1)[0]


def _populate_family(
    size: int,
    family_race: str,
    family_name: str,
    race_ratio: dict[str, float],
    existing_names: set[str],
    appearance_rng: random.Random,
) -> list[dict]:
    """Generate family members with race-appropriate names and appearance."""
    male_pool = deepcopy(FAMILY_POSITIONS["male"]["pool"])
    male_default = FAMILY_POSITIONS["male"]["default"]
    female_pool = deepcopy(FAMILY_POSITIONS["female"]["pool"])
    female_default = FAMILY_POSITIONS["female"]["default"]

    # Generate family phenotype for inheritance
    family_phenotype = generate_family_phenotype(family_race, appearance_rng)

    members = []
    for _ in range(size):
        gender = random.choice(["male", "female"])

        if gender == "male":
            position = _pick_position(male_pool, male_default)
        else:
            position = _pick_position(female_pool, female_default)

        # Race inheritance for half-elf families
        race = family_race
        if family_race == "half-elf":
            race = random.choices(
                ["human", "elf", "half-elf"], weights=[0.1, 0.1, 0.8], k=1
            )[0]

        # Generate unique first name
        first_name = names.get_first_name(race, gender)
        attempts = 0
        while first_name in existing_names and attempts < 20:
            first_name = names.get_first_name(race, gender)
            attempts += 1
        existing_names.add(first_name)

        generation = _get_generation(position)
        beauty = random.choices(
            ["very ugly", "ugly", "average", "pretty", "very pretty"],
            weights=[0.05, 0.1, 0.5, 0.2, 0.15], k=1,
        )[0]

        member = {
            "first_name": first_name,
            "last_name": family_name,
            "full_name": f"{first_name} {family_name}",
            "race": race,
            "gender": gender,
            "origin": "native",
            "generation": generation,
            "group_position": position,
            "beauty": beauty,
            "iq": float(npr.normal(100, 15)),
        }

        # 70% chance mothers/grandmothers get a birth name
        if position in ("mother", "grandmother") and random.random() < 0.7:
            member["birth_name"] = names.get_last_name(race)

        # Generate procedural appearance with family inheritance
        appearance = generate_appearance(
            race, gender, generation, appearance_rng,
            family_phenotype=family_phenotype, position=position,
        )
        member.update(appearance)
        member.update(build_composite_fields(appearance))

        members.append(member)

    return members


def _populate_outsiders(
    size: int,
    group_type: str,
    race_ratio: dict[str, float],
    existing_names: set[str],
    appearance_rng: random.Random,
) -> list[dict]:
    """Generate outsider group members."""
    positions = OUTSIDER_POSITIONS.get(group_type, OUTSIDER_POSITIONS["strangers"])
    pool = deepcopy(positions["pool"])
    default = positions["default"]

    # For solo type, pick one situation for all members
    solo_situation = None
    if group_type == "solo" and default:
        keys = list(default.keys())
        weights = list(default.values())
        solo_situation = random.choices(keys, weights=weights, k=1)[0]

    races = list(race_ratio.keys())
    race_weights = list(race_ratio.values())

    members = []
    for _ in range(size):
        gender = random.choice(["male", "female"])
        race = random.choices(races, weights=race_weights, k=1)[0]

        first_name = names.get_first_name(race, gender)
        last_name = names.get_last_name(race)
        full_name = f"{first_name} {last_name}"
        attempts = 0
        while full_name in existing_names and attempts < 20:
            first_name = names.get_first_name(race, gender)
            last_name = names.get_last_name(race)
            full_name = f"{first_name} {last_name}"
            attempts += 1
        existing_names.add(full_name)

        if solo_situation:
            position = solo_situation
        else:
            position = _pick_position(pool, default)

        generation = _get_generation(position)
        beauty = random.choices(
            ["very ugly", "ugly", "average", "pretty", "very pretty"],
            weights=[0.05, 0.1, 0.5, 0.2, 0.15], k=1,
        )[0]

        member = {
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "race": race,
            "gender": gender,
            "origin": "outsider",
            "generation": generation,
            "group_position": position,
            "beauty": beauty,
            "iq": float(npr.normal(100, 15)),
        }

        # Generate procedural appearance (no family inheritance for outsiders)
        appearance = generate_appearance(race, gender, generation, appearance_rng)
        member.update(appearance)
        member.update(build_composite_fields(appearance))

        members.append(member)

    return members


# ---------------------------------------------------------------------------
# Main population generation
# ---------------------------------------------------------------------------

def generate_population(content: dict) -> dict:
    """Step 5: Generate social groups and populate with NPCs.

    Creates local groups (60% family / 40% friends, Gumbel(7,3))
    and foreign groups (Gumbel(2,1), various types).
    """
    seed = content.get("generation", {}).get("seed", 42)
    random.seed(seed)
    np.random.seed(seed)
    rng = np.random.default_rng(seed)
    appearance_rng = random.Random(seed)

    race_ratio = content["details"]["races"]

    # Count target populations per origin from activity groups
    count_per_origin = {"local": 0.0, "foreign": 0.0}
    for v in content.get("groups", {}).get("activity", {}).values():
        pop = float(v.get("population", 0))
        origin = v.get("origin", {"local": 1.0, "foreign": 0.0})
        if isinstance(origin, dict):
            count_per_origin["local"] += pop * origin.get("local", 0.5)
            count_per_origin["foreign"] += pop * origin.get("foreign", 0.5)
        else:
            count_per_origin["local"] += pop

    group_types = ["family", "friends", "colleagues", "allies", "strangers", "common goal", "common status"]
    group_type_weights = {
        "local": [0.6, 0.4, 0.02, 0.02, 0.02, 0.02, 0.02],
        "foreign": [0.2, 0.2, 0.2, 0.2, 0.1, 0.2, 0.1],
    }
    group_size_params = {
        "local": (7, 3),
        "foreign": (2, 1),
    }

    groups: dict[str, dict] = {}
    npcs: dict[str, dict] = {}
    all_names: set[str] = set()

    for origin, target_pop in count_per_origin.items():
        generated = 0
        while generated < target_pop:
            loc, scale = group_size_params[origin]
            pop = max(1, int(rng.gumbel(loc, scale)))
            gtype = random.choices(
                group_types, weights=group_type_weights[origin], k=1
            )[0]
            if pop == 1:
                gtype = "solo"

            group_id = shortuuid.uuid()
            group = {
                "origin": origin,
                "type": gtype,
                "population": pop,
            }

            # Generate members
            if gtype == "family":
                family_race = random.choices(
                    list(race_ratio.keys()),
                    weights=list(race_ratio.values()), k=1,
                )[0]
                family_name = names.get_last_name(family_race)
                members = _populate_family(
                    pop, family_race, family_name, race_ratio, all_names,
                    appearance_rng,
                )
            else:
                members = _populate_outsiders(
                    pop, gtype, race_ratio, all_names,
                    appearance_rng,
                )

            # Register NPCs
            member_ids = []
            for m in members:
                npc_id = shortuuid.uuid()
                m["social_group"] = group_id
                npcs[npc_id] = m
                member_ids.append(npc_id)

            group["members"] = member_ids
            groups[group_id] = group
            generated += pop

    return {
        "groups": {"social": groups},
        "npcs": npcs,
    }
