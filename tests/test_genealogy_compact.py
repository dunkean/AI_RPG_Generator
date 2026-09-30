"""Packed life-history exports must preserve the actual simulated pedigree."""

from contextlib import closing

import numpy as np
import pytest

from src.genealogy.compact import CompactArchive, export_compact
from src.genealogy.config import Scenario
from src.genealogy.engine import generate
from src.genealogy.store import Archive


def test_packed_export_roundtrips_people_dates_and_relations(tmp_path):
    path, target = tmp_path / "world.sqlite", tmp_path / "compact"
    generate(Scenario(initial_population=200, years=30, start_year=-50), path)
    result = export_compact(path, target)
    assert result["person_bytes"] == 21
    compact, archive = CompactArchive(target), Archive(path)
    with closing(archive.connect()) as db:
        for row in db.execute("SELECT * FROM people"):
            restored = compact.person(row["id"])
            assert all(restored[name] == row[name] for name in restored)
        assert (
            len(np.load(target / "unions.npy"))
            == db.execute("SELECT count(*) FROM unions").fetchone()[0]
        )
        assert (
            len(np.load(target / "migrations.npy"))
            == db.execute("SELECT count(*) FROM migrations").fetchone()[0]
        )
    youngest = len(compact.people) - 1
    a = compact.ancestors(youngest, 100)
    b = compact.ancestors(youngest, 100)
    assert a == b
    assert a["people"]
    assert not a["truncated"]
    assert all(p["birth"] < compact.person(youngest)["birth"] for p in a["people"])
    with pytest.raises(FileExistsError):
        export_compact(path, target)
    with pytest.raises(KeyError):
        compact.person(-1)


def test_packed_export_preserves_noncontiguous_places_and_long_lifetimes(tmp_path):
    path, target = tmp_path / "elves.sqlite", tmp_path / "elves"
    generate(
        Scenario.model_validate(
            {
                "initial_population": 100,
                "years": 5,
                "settlements": [
                    {"id": 70000, "name": "high", "x": 0, "y": 0},
                    {"id": 99000, "name": "low", "x": 10, "y": 10},
                ],
                "races": [
                    {
                        "name": "elf",
                        "demography": {
                            "max_age": 1200,
                            "aging_exponent": 0.005,
                            "aging_coefficient": 0.00001,
                        },
                    }
                ],
            }
        ),
        path,
    )
    export_compact(path, target)
    compact = CompactArchive(target)
    assert compact.person(0)["birth_place"] in (70000, 99000)
    with closing(Archive(path).connect()) as db:
        for row in db.execute("SELECT * FROM people"):
            assert compact.person(row["id"])["birth"] == row["birth"]


def test_pedigree_collapse_does_not_hide_shorter_path_ancestors():
    archive = object.__new__(CompactArchive)
    links = {8: (7, 6), 7: (4, None), 6: (5, None), 5: (4, None), 4: (3, None), 3: (None, None)}
    archive.person = lambda identity: {
        "id": identity,
        "father": links[identity][0],
        "mother": links[identity][1],
    }
    result = archive.ancestors(8, depth=3)
    assert {p["id"] for p in result["people"]} == {7, 6, 5, 4, 3}


def test_compact_wide_categories_and_empty_event_tables(tmp_path):
    config = Scenario.model_validate(
        {
            "initial_population": 10,
            "years": 1,
            "settlements": [
                {
                    "id": 0,
                    "name": "one",
                    "x": 0,
                    "y": 0,
                    "activities": {f"activity_{i:03d}": int(i == 256) for i in range(257)},
                }
            ],
            "races": [{"name": str(i), "initial_weight": int(i == 256)} for i in range(257)],
            "society": {"status_weights": [int(i == 128) for i in range(129)]},
        }
    )
    path, target = tmp_path / "wide.sqlite", tmp_path / "wide"
    generate(config, path)
    assert export_compact(path, target)["person_bytes"] == 24
    with CompactArchive(target) as compact:
        record = compact.person(0)
        assert (record["status"], record["activity"], record["race"]) == (128, 256, 256)
