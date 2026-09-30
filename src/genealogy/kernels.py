"""Native CSR matching and household destination kernels; no Python objects per person.

Randomness uses Numba's isolated random state, seeded from the yearly process
stream. Single-thread order is deliberate: mutable marriage markets are not
independent draws. Every accepted pair still passes an exact bounded pedigree check.
"""

import numpy as np
from numba import njit, prange


@njit(cache=True, nogil=True)
def census_counts(ids, birth, sex, race, partner, minimum, maximum, year):
    young, adults, elders, fertile, partnered = 0, 0, 0, 0, 0
    for index in prange(len(ids)):
        pid = ids[index]
        age = year - birth[pid]
        young += int(age < 15)
        adults += int(15 <= age < 50)
        elders += int(age >= 50)
        eligible = sex[pid] == 1 and minimum[race[pid]] <= age <= maximum[race[pid]]
        fertile += int(eligible)
        partnered += int(eligible and partner[pid] >= 0)
    return young, adults, elders, fertile, partnered


# Separate cache identities prevent parallel code from replacing the serial kernel.
@njit(cache=True, nogil=True, parallel=True)
def census_counts_parallel(ids, birth, sex, race, partner, minimum, maximum, year):
    young, adults, elders, fertile, partnered = 0, 0, 0, 0, 0
    for index in prange(len(ids)):
        pid = ids[index]
        age = year - birth[pid]
        young += int(age < 15)
        adults += int(15 <= age < 50)
        elders += int(age >= 50)
        eligible = sex[pid] == 1 and minimum[race[pid]] <= age <= maximum[race[pid]]
        fertile += int(eligible)
        partnered += int(eligible and partner[pid] >= 0)
    return young, adults, elders, fertile, partnered


@njit(cache=True, nogil=True)
def choose_activities(slots, draws, offsets, options, cumulative):
    result = np.empty(len(slots), np.int16)
    for index in range(len(slots)):
        low, high = offsets[slots[index]], offsets[slots[index] + 1]
        while low < high:
            middle = (low + high) // 2
            if draws[index] < cumulative[middle]:
                high = middle
            else:
                low = middle + 1
        result[index] = options[low]
    return result


@njit(cache=True, nogil=True)
def fertile_ids(ids, birth, sex, race, partner, last_birth, minimum, maximum, spacing, year):
    result = np.empty(len(ids), np.int32)
    count = 0
    for pid in ids:
        r = race[pid]
        age = year - birth[pid]
        if (
            sex[pid] == 1
            and partner[pid] >= 0
            and minimum[r] <= age <= maximum[r]
            and year - last_birth[pid] >= spacing[r]
        ):
            result[count] = pid
            count += 1
    return result[:count].copy()


@njit(cache=True, nogil=True)
def household_heads(ids, partner, birth, race, dependent_age, year):
    result = np.empty(len(ids), np.int32)
    count = 0
    for pid in ids:
        p = partner[pid]
        if (p < 0 and year - birth[pid] >= dependent_age[race[pid]]) or (p >= 0 and pid < p):
            result[count] = pid
            count += 1
    return result[:count].copy()


@njit(cache=True, nogil=True)
def guardian_pairs(
    ids, birth, race, partner, mother, father, death, place, age_limit, year, no_year
):
    children, guardians = np.empty(len(ids), np.int32), np.empty(len(ids), np.int32)
    count = 0
    for pid in ids:
        if year - birth[pid] >= age_limit[race[pid]] or partner[pid] >= 0:
            continue
        guardian = -1
        m, f = mother[pid], father[pid]
        if m >= 0 and death[m] == no_year and place[m] == place[pid]:
            guardian = m
        elif f >= 0 and death[f] == no_year and place[f] == place[pid]:
            guardian = f
        if guardian >= 0:
            children[count], guardians[count] = pid, guardian
            count += 1
    return children[:count].copy(), guardians[:count].copy()


@njit(cache=True, nogil=True)
def stable_groups(codes, group_count):
    """Counting sort preserves within-group ID order and consumes no randomness."""
    counts = np.zeros(group_count, np.int64)
    for code in codes:
        counts[code] += 1
    starts = np.zeros(group_count, np.int64)
    total = 0
    for group in range(group_count):
        starts[group] = total
        total += counts[group]
    cursors = starts.copy()
    order = np.empty(len(codes), np.int64)
    for index in range(len(codes)):
        group = codes[index]
        order[cursors[group]] = index
        cursors[group] += 1
    keys = np.flatnonzero(counts)
    return order, keys, starts[keys], counts[keys]


@njit(cache=True)
def mark_ancestors(fathers, mothers, identity, depth, marks, stamp, queue, levels):
    queue[0], levels[0] = identity, 0
    read, size = 0, 1
    while read < size:
        pid, level = queue[read], levels[read]
        read += 1
        marks[pid] = stamp
        if level < depth:
            father, mother = fathers[pid], mothers[pid]
            if father >= 0:
                queue[size], levels[size] = father, level + 1
                size += 1
            if mother >= 0:
                queue[size], levels[size] = mother, level + 1
                size += 1


@njit(cache=True)
def shares_ancestor(fathers, mothers, identity, depth, marks, stamp, queue, levels):
    queue[0], levels[0] = identity, 0
    read, size = 0, 1
    while read < size:
        pid, level = queue[read], levels[read]
        read += 1
        if marks[pid] == stamp:
            return True
        if level < depth:
            father, mother = fathers[pid], mothers[pid]
            if father >= 0:
                queue[size], levels[size] = father, level + 1
                size += 1
            if mother >= 0:
                queue[size], levels[size] = mother, level + 1
                size += 1
    return False


@njit(cache=True, nogil=True)
def match_pairs(
    birth,
    place_slot,
    races,
    status,
    partners,
    fathers,
    mothers,
    marks,
    first_stamp,
    men,
    group_keys,
    offsets,
    sizes,
    women,
    neighbors,
    proximity,
    race_count,
    race_offsets,
    compatible_races,
    affinity,
    max_gaps,
    status_affinity,
    attempts,
    depth,
    residence_mode,
    seed,
):
    np.random.seed(seed)
    pairs = np.empty((len(women), 3), np.int32)
    # The stamp array is 4 bytes per recorded person; reuse BFS buffers across all pairs.
    queue = np.empty((1 << (depth + 1)) - 1, np.int32)
    levels = np.empty(len(queue), np.int32)
    maximum = neighbors.shape[1] * max(1, np.max(np.diff(race_offsets)))
    pools = np.empty(maximum, np.int64)
    slots = np.empty(maximum, np.int32)
    gaps = np.empty(maximum, np.int32)
    weights = np.empty(maximum, np.float64)
    count, local, checks, rejected = 0, 0, 0, 0
    for wi in range(len(women)):
        female = women[wi]
        origin, race = place_slot[female], races[female]
        stamp = first_stamp + wi + 1
        mark_ancestors(fathers, mothers, female, depth, marks, stamp, queue, levels)
        candidates, total = 0, 0.0
        for ni in range(neighbors.shape[1]):
            destination = neighbors[origin, ni]
            if destination < 0:
                continue
            for ci in range(race_offsets[race], race_offsets[race + 1]):
                key = destination * race_count + compatible_races[ci]
                group = np.searchsorted(group_keys, key)
                if group >= len(group_keys) or group_keys[group] != key or sizes[group] == 0:
                    continue
                weight = proximity[origin, ni] * np.sqrt(sizes[group]) * affinity[ci]
                if weight <= 0:
                    continue
                pools[candidates], slots[candidates], gaps[candidates] = (
                    group,
                    destination,
                    max_gaps[ci],
                )
                weights[candidates] = weight
                total += weight
                candidates += 1
        if candidates == 0:
            continue
        for _ in range(attempts):
            target, selected = np.random.random() * total, candidates - 1
            for ci in range(candidates):
                target -= weights[ci]
                if target < 0:
                    selected = ci
                    break
            group = pools[selected]
            index = offsets[group] + np.random.randint(sizes[group])
            male = men[index]
            if abs(np.int64(birth[male]) - np.int64(birth[female])) > gaps[selected]:
                continue
            gap = abs(np.int64(status[male]) - np.int64(status[female]))
            if np.random.random() > (1 - status_affinity) ** gap:
                continue
            checks += 1
            if shares_ancestor(fathers, mothers, male, depth, marks, stamp, queue, levels):
                rejected += 1
                continue
            sizes[group] -= 1
            men[index] = men[offsets[group] + sizes[group]]
            destination = slots[selected] if residence_mode == 0 else origin
            if residence_mode == 2 and np.random.random() < 0.5:
                destination = slots[selected]
            partners[male], partners[female] = female, male
            pairs[count, 0], pairs[count, 1], pairs[count, 2] = male, female, destination
            count += 1
            local += slots[selected] == origin
            break
    return pairs[:count], local, checks, rejected


@njit(cache=True, nogil=True)
def migration_destinations(origins, neighbors, proximity, attraction, seed):
    np.random.seed(seed)
    destinations = np.full(len(origins), -1, np.int32)
    for i in range(len(origins)):
        origin, total = origins[i], 0.0
        for ni in range(neighbors.shape[1]):
            slot = neighbors[origin, ni]
            if slot >= 0:
                total += proximity[origin, ni] * attraction[slot]
        if total <= 0:
            continue
        target = np.random.random() * total
        for ni in range(neighbors.shape[1]):
            slot = neighbors[origin, ni]
            if slot < 0:
                continue
            destinations[i] = slot  # last valid destination also handles rounding residue
            target -= proximity[origin, ni] * attraction[slot]
            if target <= 0:
                destinations[i] = slot
                break
    return destinations
