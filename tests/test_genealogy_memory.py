"""Exact archive parity, seeded compatibility and no-write studio regressions."""

import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from src.genealogy.config import Scenario, load_scenario
from src.genealogy.engine import Engine, generate
from src.genealogy.kernels import census_counts, census_counts_parallel, stable_groups
from src.genealogy.store import Archive
from src.genealogy.studio import Studio


class Trace:
    def __init__(self):
        self.rows = {
            key: [] for key in ("unions", "close_unions", "migrations", "census", "distributions")
        }

    def unions(self, rows):
        self.rows["unions"].extend(rows)

    def close_unions(self, rows):
        self.rows["close_unions"].extend(rows)

    def migrations(self, rows):
        self.rows["migrations"].extend(rows)

    def census(self, row, places, span=1):
        self.rows["census"].append((row, list(places), span))

    def distributions(self, year, groups, rows):
        self.rows["distributions"].append(
            (year, {k: v.tolist() for k, v in groups.items()}, list(rows))
        )


@pytest.mark.parametrize(
    "fantasy,digest",
    [
        (False, "7186d2cbee2e2ed40eb42246ea0cb0b26952e112c5bd0c398cc3a6b32941123e"),
        (True, "0c44af8281a73efda56f1eca33fa38c6f12fd1a29d663439504cd994eaf60484"),
    ],
)
def test_exact_pre_optimization_history(fantasy, digest):
    # Captured from a92216d BEFORE optimization, including runtime state and every event.
    config = Scenario(seed=42, initial_population=10000, virtual_settlements=50, years=60)
    if fantasy:
        config = load_scenario(Path("config/genealogy/fantasy.yaml")).model_copy(
            update={"initial_population": 3000, "years": 60, "target_population": None}
        )
    sink = Trace()
    engine = Engine(config, sink)
    engine.run()
    result = hashlib.sha256()
    for name in engine.data.columns:
        result.update(engine.data[name][: engine.n].tobytes())
    result.update(json.dumps(sink.rows, sort_keys=True).encode())
    assert result.hexdigest() == digest


@pytest.mark.parametrize("backend", ["compiled", "reference"])
def test_memory_explorer_matches_sqlite(tmp_path, backend):
    config = Scenario(
        seed=123, initial_population=500, virtual_settlements=16, years=70, backend=backend
    )
    path = tmp_path / "reference.sqlite"
    generate(config, path)
    sql = Archive(path)
    memory = generate(config, None)
    assert memory.summary["disk_bytes_written"] == 0
    assert memory.overview()["history"] == sql.overview()["history"]
    for pid in np.linspace(0, memory.n - 1, 80, dtype=int):
        assert memory.person(int(pid)) == sql.person(int(pid))
        assert memory.lineage(int(pid), 5) == sql.lineage(int(pid), 5)
        assert memory.lineage(int(pid), 3, "descendants") == sql.lineage(int(pid), 3, "descendants")
        for year in [999, 1000, 1030, 1070]:
            assert memory.residence(int(pid), year) == sql.residence(int(pid), year)
    for year in memory.saved_years:
        assert memory.map_at(year) == sql.map_at(year)
        assert memory.map_at(year, 0) == sql.map_at(year, 0)
        a, b = memory.distributions(year), sql.distributions(year)
        assert a["groups"] == b["groups"]
        assert sorted(a["flows"], key=str) == sorted(b["flows"], key=str)
    for settlement in range(16):
        assert memory.residents(settlement, limit=7, after=200) == sql.residents(
            settlement, limit=7, after=200
        )


def test_studio_default_never_writes(tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("No SQLite or filesystem write permitted")

    monkeypatch.setattr("src.genealogy.engine.Store", forbidden)
    monkeypatch.setattr(Path, "mkdir", forbidden)
    initial = generate(Scenario(initial_population=50, years=2), None)
    studio = Studio(initial)
    studio.start({"scenario": {"seed": 19, "initial_population": 100, "years": 5}})
    studio.worker.join(timeout=20)
    status = studio.status()
    assert status["state"] == "complete", status
    assert not list(tmp_path.iterdir())
    studio.select(status["archive"])
    assert studio.config()["seed"] == 19
    assert len(studio.catalogue()["archives"]) == 2
    assert studio.current().person(0)["id"] == 0


def test_native_grouping_and_parallel_integer_census_are_exact():
    rng = np.random.default_rng(91)
    codes = rng.integers(0, 500, 10000)
    order, keys, starts, sizes = stable_groups(codes, 500)
    np.testing.assert_array_equal(order, np.argsort(codes, kind="stable"))
    np.testing.assert_array_equal(keys, np.unique(codes))
    assert np.sum(sizes) == len(codes)
    assert starts[0] == 0
    engine = Engine(Scenario(initial_population=1000, years=1))
    d = engine.data
    args = (
        engine.alive,
        d["birth"],
        d["sex"],
        d["race"],
        d["partner"],
        engine.race_fertility_min,
        engine.race_fertility_max,
        engine.year,
    )
    assert census_counts(*args) == census_counts_parallel(*args)


def test_shuffled_ids_keep_original_draw_order_and_event_history():
    config = Scenario.model_validate(
        {
            "seed": 246,
            "initial_population": 2000,
            "years": 60,
            "society": {"migration_rate": 0.08, "divorce_rate": 0.03},
            "settlements": [
                {
                    "id": pid,
                    "name": str(pid),
                    "x": x,
                    "y": y,
                    "capacity": 2000,
                    "activities": {activity: 1},
                }
                for pid, x, y, activity in [
                    (30, 0, 0, "farm"),
                    (4, 4, 0, "mine"),
                    (20, 0, 4, "trade"),
                    (1, 4, 4, "craft"),
                ]
            ],
            "events": [
                {
                    "name": "crisis",
                    "start_year": 1020,
                    "end_year": 1025,
                    "extra_mortality": 0.04,
                    "settlements": [30, 4],
                }
            ],
        }
    )
    trace = Trace()
    engine = Engine(config, trace)
    engine.run()
    digest = hashlib.sha256()
    for name in engine.data.columns:
        digest.update(engine.data[name][: engine.n].tobytes())
    digest.update(json.dumps(trace.rows, sort_keys=True).encode())
    assert digest.hexdigest() == "84b52f75f0ef21aaa61d6b8f0e6d18a9b5c2b11f2430b60c0ef2cbc2182ccf68"


def test_memory_custom_rules_and_retention(tmp_path):
    class NoBirths:
        def apply(self, engine, process, ids, hazards):
            if process == "births":
                hazards["fertility"][:] = 0

    config = Scenario(
        initial_population=100, years=10, target_population=100, calibration_population=100
    )
    memory = generate(config, None, rules=[NoBirths()])
    saved = generate(config, tmp_path / "rules.sqlite", rules=[NoBirths()])
    assert memory.summary["births"] == saved["births"] == 0
    assert memory.summary["calibration"] == saved["calibration"]
    studio = Studio(memory)
    for seed in range(4):
        studio.start({"scenario": {"seed": seed, "initial_population": 40, "years": 2}})
        studio.worker.join(timeout=10)
        assert studio.status()["state"] == "complete"
    assert len(studio.archives) == 3
    assert studio.current() is memory
    assert studio.active in studio.archives
    assert studio.status()["archive"] in studio.archives
