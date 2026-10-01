"""Resident visualization counts remain exact despite bounded display samples."""

import numpy as np

from src.genealogy.inspection import resident_atlas


def test_atlas_filters_all_residents_and_samples_stable_real_ids():
    data = {"birth": np.full(5000, 980), "race": np.arange(5000) % 3,
            "sex": np.arange(5000) % 2}
    ids = np.arange(100, 5000, 2)
    result = resident_atlas(data, ids, 1000, race=1, sex=0, min_age=20, max_age=20, limit=12)
    expected = ids[data["race"][ids] == 1]
    assert result["total"] == len(ids)
    assert result["matched"] == len(expected)
    assert result["sampled"]
    assert sum(g["count"] for g in result["groups"]) == len(expected)
    assert len(result["people"]) == 12
    assert all(p["id"] in expected and p["sex"] == 0 and p["race"] == 1 for p in result["people"])
    assert resident_atlas(data, ids, 1000, race=1, sex=0, min_age=20, max_age=20, limit=12) == result


def test_empty_resident_atlas_is_a_valid_visualization():
    data = {"birth": np.array([], dtype=int), "race": np.array([], dtype=int),
            "sex": np.array([], dtype=int)}
    result = resident_atlas(data, np.array([], dtype=int), 1000)
    assert result["matched"] == 0
    assert result["groups"] == []
    assert result["people"] == []
