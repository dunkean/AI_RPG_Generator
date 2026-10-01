"""One-run bounds, preserved crises, biological birth limits and seeded histories."""

import numpy as np
import pytest

from src.genealogy.config import Scenario
from src.genealogy.engine import Engine, generate
from src.genealogy.regulation import PopulationRegulator
from src.genealogy.schema import NO_YEAR


def test_ceiling_is_hard_and_crisis_recovers_through_real_births():
    scenario = Scenario(
        initial_population=3000,
        target_population=3600,
        years=80,
        snapshot_interval=1,
        events=[
            {
                "name": "plague",
                "start_year": 1010,
                "end_year": 1010,
                "extra_mortality": 0.4,
                "fertility_factor": 0.25,
            }
        ],
    )
    engine = Engine(scenario)
    summary = engine.run()
    populations = {row[0]: row[1] for row in engine.rows}
    assert all(pop <= 3600 for pop in populations.values())
    assert populations[1010] < 3000
    assert sum(engine.data["death"][: engine.n] == 1010) > 1000
    assert summary["population"] >= 3000
    assert summary["regulation"]["additional_births"] > 0
    assert summary["regulation"]["additional_deaths"] > 0
    assert summary["regulation"]["below_floor_years"] > 0
    histories = {row["year"]: row for row in summary["regulation"]["history"]}
    assert histories[1010]["birth_probability_factor"] == 1
    assert histories[1011]["birth_probability_factor"] > 1
    d = engine.data
    children = np.arange(scenario.initial_population, engine.n)
    for field, sex in (("mother", 1), ("father", 0)):
        parents = d[field][children]
        assert np.all(parents < children)
        assert np.all(d["sex"][parents] == sex)
        assert np.all(
            (d["death"][parents] == NO_YEAR) | (d["death"][parents] >= d["birth"][children])
        )
    for mother in np.unique(d["mother"][children]):
        dates = np.sort(d["birth"][children[d["mother"][children] == mother]])
        assert np.all(np.diff(dates) >= scenario.demography.birth_spacing)


def test_no_pilots_or_founder_changes_even_for_legacy_configs(monkeypatch):
    config = Scenario(
        initial_population=100, target_population=150, years=10, target_mode="calibrate_founders"
    )
    assert config.target_mode == "bounded"
    calls = []
    real = Engine

    def counted(*args, **kwargs):
        calls.append(args[0].initial_population)
        return real(*args, **kwargs)

    monkeypatch.setattr("src.genealogy.engine.Engine", counted)

    def forbidden(*args):
        raise AssertionError("Calibration callbacks must never run")

    archive = generate(config, None, calibration_progress=forbidden, calibration_stage=forbidden)
    assert calls == [100]
    assert archive.summary["simulation_runs"] == 1
    assert archive.summary["calibration"] is None
    assert archive.summary["initial_population"] == 100


def test_regulation_preserves_partial_crisis_and_zero_fertility():
    regulator = PopulationRegulator(Scenario(initial_population=1000, target_population=2000))
    base = np.array([0, 0.02, 0.1, 0.3])
    np.testing.assert_array_equal(
        regulator.birth_probabilities(base, 200, 30, 0.8, crisis=True), base
    )
    modified = regulator.birth_probabilities(base, 200, 30, 0.8)
    assert modified[0] == 0
    assert np.all(modified >= base)
    assert np.all(modified <= base * 4)
    assert np.all(modified <= 0.85)


def test_ceiling_never_revives_natural_deaths_and_handles_zero_rates():
    regulator = PopulationRegulator(Scenario(initial_population=2, target_population=2))
    q = np.array([1, 0.1, 0.1, 0, 0, 0])
    draws = np.array([0.2, 0.01, 0.5, 0.4, 0.7, 0.9])
    deaths = draws < q
    result = regulator.enforce_ceiling(q, draws, deaths)
    assert result[0] and result[1]
    assert np.sum(~result) == 2
    assert regulator.extra_deaths == 2


def test_invalid_ceiling_and_seeded_memory_determinism():
    with pytest.raises(ValueError, match="ceiling"):
        Scenario(initial_population=100, target_population=99)
    config = Scenario(initial_population=400, target_population=450, years=30)
    a, b = generate(config, None), generate(config, None)
    assert a.overview()["history"] == b.overview()["history"]
    assert a.summary["regulation"] == b.summary["regulation"]
    for field in a.data:
        np.testing.assert_array_equal(a.data[field], b.data[field])
