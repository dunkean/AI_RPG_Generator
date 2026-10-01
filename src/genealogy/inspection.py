"""Exact resident cohorts and bounded, deterministic display samples (read-only)."""

import numpy as np


def resident_atlas(data, ids, year, min_age=0, max_age=2000, race=None, sex=None, limit=1200):
    """Aggregate the entire settlement, then sample within the selected cohort.

    Sampling bounds browser payload size; group counts always cover all matching
    residents. IDs are stable, so the same selection produces the same markers.
    """
    if not 0 <= min_age <= max_age <= 2000 or not 1 <= limit <= 2000:
        raise ValueError("Use ages 0..2000 and display limit 1..2000")
    if race is not None and race < 0 or sex not in (None, 0, 1):
        raise ValueError("Invalid resident category")
    total = len(ids)
    ages = year - data["birth"][ids]
    races, sexes = data["race"][ids], data["sex"][ids]
    mask = (ages >= min_age) & (ages <= max_age)
    if race is not None:
        mask &= races == race
    if sex is not None:
        mask &= sexes == sex
    ids, ages, races, sexes = ids[mask], ages[mask], races[mask], sexes[mask]
    race_count = int(races.max()) + 1 if len(races) else 1
    codes = (ages.astype(np.int64) * race_count + races) * 2 + sexes
    if len(codes) and codes.max() > 1_000_000:
        occupied, counts = np.unique(codes, return_counts=True)
    else:
        bins = np.bincount(codes)
        occupied = np.flatnonzero(bins)
        counts = bins[occupied]
    positions = np.linspace(0, len(ids) - 1, min(len(ids), limit), dtype=np.int64)
    return {
        "year": year,
        "total": total,
        "matched": len(ids),
        "sampled": len(ids) > limit,
        "groups": [
            {
                "age": int(code // (race_count * 2)),
                "race": int(code // 2 % race_count),
                "sex": int(code % 2),
                "count": int(count),
            }
            for code, count in zip(occupied, counts, strict=True)
        ],
        "people": [
            {
                "id": int(ids[i]),
                "birth": int(year - ages[i]),
                "sex": int(sexes[i]),
                "race": int(races[i]),
            }
            for i in positions
        ],
    }
