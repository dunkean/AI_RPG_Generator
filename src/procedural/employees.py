"""Workplace employee assignment — Step 7.

Assigns NPCs from social groups to activity groups (workplaces)
using preferential selection based on composition, type, age, and structure.
"""

from __future__ import annotations

import logging
import random
from copy import deepcopy

import numpy as np
from numpy import random as npr

from .distributions import (
    AGE_WEIGHT_DICT,
    GROUP_FILTERS,
    GROUP_WEIGHTS_IND,
    TRANSLATION_DICT,
    age_weight,
    translate,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Group sizing
# ---------------------------------------------------------------------------

def _generate_distributed_integers(n: int, total: int, spread: float = 0.3) -> list[int]:
    """Generate *n* integers that sum to *total* with controlled spread."""
    if n == 0:
        return []
    if n == 1:
        return [total]
    mean = total / n
    std = (total * spread) / n
    numbers = np.random.normal(mean, std, n)
    numbers = np.maximum(numbers, 1)
    numbers *= total / np.sum(numbers)
    numbers = np.round(numbers).astype(int)
    numbers[-1] += total - np.sum(numbers)
    return list(numbers)


def _get_group_sizes(composition: str, wtype: str, size: int) -> list[int]:
    """Determine sub-group sizes for a workplace based on its type."""
    wtype = translate(wtype)

    if wtype == "family":
        return [size]
    elif wtype in ("cooperative", "guild"):
        mean_sizes = [2, 3, 4, 5, 6, 7, 8]
        weights = [0.1, 0.2, 0.3, 0.2, 0.1, 0.05, 0.05]
        n_sub = [size // m for m in mean_sizes]
        coop_size = random.choices(n_sub, weights=weights, k=1)[0]
        coop_size = max(1, coop_size)
        return [max(1, int(npr.default_rng().gumbel(size / coop_size, 1)))
                for _ in range(coop_size)]
    elif wtype in ("crew", "illegal"):
        n = random.choices([0, 1, 2, 3, 4], weights=[0.05, 0.8, 0.1, 0.05, 0.05], k=1)[0]
        return _generate_distributed_integers(n, size)
    elif wtype == "company":
        n = random.choices([0, 1, 2, 3, 4], weights=[0.5, 0.1, 0.1, 0.1, 0.1], k=1)[0]
        return _generate_distributed_integers(n, size)
    elif wtype == "council":
        return []
    elif wtype == "team":
        n = random.choices([0, 1, 2, 3, 4], weights=[0.05, 0.6, 0.2, 0.1, 0.05], k=1)[0]
        return _generate_distributed_integers(n, size)
    else:
        logger.warning("Unknown workplace type: %s, treating as team", wtype)
        return _generate_distributed_integers(1, size)


# ---------------------------------------------------------------------------
# Group selection
# ---------------------------------------------------------------------------

def _choose_groups_by_type(
    group_pool: list[dict],
    composition_filter: dict,
    type_filter: dict,
    sizes: list[int],
) -> tuple[list[dict[str, dict]], list[tuple[str, str]]]:
    """Choose social groups from pool based on weighted criteria."""
    chosen_groups: list[dict[str, dict]] = []
    chosen_details: list[tuple[str, str]] = []

    for size in sizes:
        if not group_pool:
            logger.warning("No groups left to choose from")
            break

        weights = {}
        for g in group_pool:
            comp_ratio = composition_filter.get(g.get("origin", "natives"), 1.0)
            type_ratio = type_filter.get(g.get("type", ""), 1.0)
            size_diff = abs(g.get("size", len(g.get("members", []))) - size)
            size_weight = 1.0 / (size_diff + 1)
            weights[g["name"]] = comp_ratio * type_ratio * size_weight

        if not weights:
            break

        chosen_name = random.choices(
            list(weights.keys()), weights=list(weights.values()), k=1
        )[0]
        idx = next(i for i, g in enumerate(group_pool) if g["name"] == chosen_name)
        chosen = group_pool.pop(idx)

        members_dict = {
            f"{m.get('first_name', '')} {m.get('last_name', '')}": m
            for m in chosen.get("members_data", [])
        }
        chosen_groups.append(members_dict)
        chosen_details.append((chosen["name"], chosen.get("type", "")))

    return chosen_groups, chosen_details


# ---------------------------------------------------------------------------
# Individual selection
# ---------------------------------------------------------------------------

def _clean_pool(
    pool: list[dict[str, dict]],
    individual_pool: dict[str, dict],
    src_weights: list[float],
) -> None:
    """Remove assigned individuals from all source pools."""
    to_remove_pools = []
    for i, src in enumerate(pool):
        if src is individual_pool:
            continue
        to_delete = [name for name in src if name not in individual_pool]
        for name in to_delete:
            del src[name]
        if not src:
            to_remove_pools.append(i)

    for i in reversed(to_remove_pools):
        pool.pop(i)
        src_weights.pop(i)


def _select_individuals(
    workplace: dict,
    individual_pool: dict[str, dict],
    group_members_pools: list[dict[str, dict]],
    ages_str: str,
) -> list[dict]:
    """Select individuals for a workplace using weighted preferential selection."""
    wtype = translate(workplace.get("type", "team"))
    wcompo = translate(workplace.get("composition", "mix"))

    ind_weight = GROUP_WEIGHTS_IND.get(wtype, {}).get(wcompo, 0.3)
    n_groups = len(group_members_pools)
    group_weight = (1.0 - ind_weight) / max(n_groups, 1) if n_groups else 0.0

    pool = [*group_members_pools, individual_pool]
    src_weights = [group_weight] * n_groups + [ind_weight]

    target = int(workplace.get("population", 0))
    selected = []

    for _ in range(target):
        _clean_pool(pool, individual_pool, src_weights)
        if not pool or all(len(p) == 0 for p in pool):
            logger.warning("Ran out of individuals for workplace %s", workplace.get("name"))
            break

        # Filter out empty pools
        available = [(p, w) for p, w in zip(pool, src_weights) if p]
        if not available:
            break
        avail_pools, avail_weights = zip(*available)

        source = random.choices(list(avail_pools), weights=list(avail_weights), k=1)[0]

        # Weight by age appropriateness
        age_weights = [
            age_weight(ages_str, p.get("generation", "mid"))
            for p in source.values()
        ]

        # Weight by structure preference
        structure_factors = [
            3.0 if p.get("structure_preference", "").lower() in wtype.lower() else 0.5
            for p in source.values()
        ]
        combined = [a * f for a, f in zip(age_weights, structure_factors)]

        chosen_name = random.choices(
            list(source.keys()), weights=combined, k=1
        )[0]
        chosen = source.pop(chosen_name)
        selected.append(chosen)

        if chosen_name in individual_pool:
            individual_pool.pop(chosen_name, None)

    return selected


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def assign_employees(content: dict) -> dict:
    """Step 7: Assign NPCs from social groups to workplaces.

    Returns a patch that adds employee lists to activity groups.
    """
    seed = content.get("generation", {}).get("seed", 42)
    random.seed(seed + 1000)  # offset from population seed
    np.random.seed(seed + 1000)

    npcs = content.get("npcs", {})
    social_groups = content.get("groups", {}).get("social", {})
    activity_groups = content.get("groups", {}).get("activity", {})

    if not npcs or not activity_groups:
        return {}

    # Build an individual pool: full_name -> npc data
    individual_pool: dict[str, dict] = {}
    for npc_id, npc in npcs.items():
        full_name = npc.get("full_name", f"{npc.get('first_name', '')} {npc.get('last_name', '')}")
        npc_copy = {**npc, "_id": npc_id}
        individual_pool[full_name] = npc_copy

    # Build social group pool for group-based selection
    social_pool: list[dict] = []
    for gid, group in social_groups.items():
        members_data = []
        for mid in group.get("members", []):
            if mid in npcs:
                members_data.append({**npcs[mid], "_id": mid})
        social_pool.append({
            "name": gid,
            "origin": "natives" if group.get("origin") == "local" else "outsiders",
            "type": group.get("type", "family") + "_type",
            "size": len(members_data),
            "members_data": members_data,
        })

    # Assign employees to each workplace
    patch: dict = {"groups": {"activity": {}}}

    for wid, workplace in activity_groups.items():
        wtype = translate(workplace.get("structure", workplace.get("type", "team")))
        wcompo = "mix"  # derive from origin ratios
        origin = workplace.get("origin", {})
        if isinstance(origin, dict):
            local_ratio = origin.get("local", 0.5)
            if local_ratio > 0.8:
                wcompo = "natives"
            elif local_ratio < 0.2:
                wcompo = "outsiders"

        ages_str = "mix"
        age_ratio = workplace.get("age_ratio", {})
        if isinstance(age_ratio, dict):
            max_age = max(age_ratio, key=age_ratio.get, default="adult")
            if max_age in ("old", "middle-aged"):
                ages_str = "old"
            elif max_age in ("teen", "child"):
                ages_str = "young"

        sizes = _get_group_sizes(wcompo, wtype, int(workplace.get("population", 0)))

        # Group-based selection
        pool_copy = deepcopy(social_pool)
        filters = GROUP_FILTERS.get(wtype, GROUP_FILTERS.get("team", {}))
        comp_filters = filters.get(wcompo, ({}, {}))
        if isinstance(comp_filters, tuple) and len(comp_filters) == 2:
            comp_filter, type_filter = comp_filters
        else:
            comp_filter, type_filter = {}, {}

        group_members, _ = _choose_groups_by_type(
            pool_copy, comp_filter, type_filter, sizes,
        )

        # Individual selection
        employees = _select_individuals(
            {**workplace, "composition": wcompo, "type": wtype},
            deepcopy(individual_pool),
            group_members,
            ages_str,
        )

        # Store employee IDs
        employee_ids = [e.get("_id", "") for e in employees if e.get("_id")]
        patch["groups"]["activity"][wid] = {"employees": employee_ids}

        # Mark NPCs with workplace assignment
        for emp in employees:
            npc_id = emp.get("_id")
            if npc_id and npc_id in npcs:
                npcs[npc_id]["workplace"] = wid

    return patch
