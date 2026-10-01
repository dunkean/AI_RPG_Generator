"""Lifetime infertility, voluntary childlessness and censored mortality statistics."""

import numpy as np
import pytest
from pydantic import ValidationError

from src.genealogy.config import Scenario
from src.genealogy.engine import Engine, generate
from src.genealogy.reproduction import ReproductiveTraits, mortality_summary
from src.genealogy.schema import NO_YEAR, STORED_FIELDS


@pytest.mark.parametrize("backend", ["compiled", "reference"])
@pytest.mark.parametrize(
    "field", ["female_infertility_rate", "male_infertility_rate", "childfree_rate"]
)
def test_either_parent_can_prevent_births_even_under_population_regulation(backend, field):
    demography = {"female_infertility_rate": 0, "male_infertility_rate": 0}
    society = {"childfree_rate": 0}
    (society if field == "childfree_rate" else demography)[field] = 1
    archive = generate(
        Scenario(
            seed=300,
            backend=backend,
            initial_population=300,
            target_population=600,
            years=35,
            demography=demography,
            society=society,
        ),
        None,
    )
    assert archive.n == 300
    assert archive.summary["births"] == 0
    assert archive.summary["simulation_runs"] == 1
    for row in archive.overview()["history"]:
        assert row["births"] == 0


def test_hash_traits_are_stable_across_batching_order_and_birth_periods():
    config = Scenario(
        seed=17,
        demography={"female_infertility_rate": 0, "male_infertility_rate": 0},
        society={"childfree_rate": 0},
        periods=[
            {
                "start_year": 1010,
                "demography": {"male_infertility_rate": 1},
                "society": {"childfree_rate": 1},
            }
        ],
        races=[{"name": "human"}, {"name": "other", "demography": {"female_infertility_rate": 1}}],
    )
    traits = ReproductiveTraits(config)
    ids = np.arange(6)
    sexes = np.array([0, 1, 0, 1, 0, 1])
    races = np.array([0, 0, 0, 0, 1, 1])
    births = np.array([980, 1000, 1010, 1010, 1010, 1000])
    expected = np.array([0, 0, 3, 2, 3, 1], dtype=np.uint8)
    np.testing.assert_array_equal(traits.flags(ids, sexes, races, births), expected)
    order = np.array([5, 0, 3, 1, 2, 4])
    np.testing.assert_array_equal(
        traits.flags(ids[order], sexes[order], races[order], births[order]), expected[order]
    )
    np.testing.assert_array_equal(
        traits.flags(ids[:3], sexes[:3], races[:3], births[:3]), expected[:3]
    )


def test_traits_have_independent_configurable_frequencies_without_rng_side_effects():
    traits = ReproductiveTraits(
        Scenario(
            seed=55, demography={"female_infertility_rate": 0.2}, society={"childfree_rate": 0.3}
        )
    )
    ids = np.arange(100000)
    flags = traits.flags(
        ids, np.ones(len(ids), dtype=int), np.zeros(len(ids), dtype=int), np.full(len(ids), 1000)
    )
    assert 0.19 < np.mean(flags & 1 != 0) < 0.21
    assert 0.29 < np.mean(flags & 2 != 0) < 0.31
    assert 0.05 < np.mean(flags == 3) < 0.07


def test_every_recorded_parent_is_fertile_and_wants_children_and_traits_reconstruct():
    config = Scenario(seed=9, initial_population=500, years=60, virtual_settlements=12)
    engine = Engine(config)
    engine.run()
    assert engine.n > config.initial_population
    ids = np.arange(config.initial_population, engine.n)
    for field in ("mother", "father"):
        assert np.all(engine.data["reproduction_flags"][engine.data[field][ids]] == 0)
    traits = ReproductiveTraits(config)
    reconstructed = traits.flags(
        np.arange(engine.n),
        engine.data["sex"][: engine.n],
        engine.data["race"][: engine.n],
        engine.data["birth"][: engine.n],
    )
    np.testing.assert_array_equal(reconstructed, engine.data["reproduction_flags"][: engine.n])
    # The archived record stays at 38 bytes; the additional byte is runtime only.
    assert sum(np.dtype(dtype).itemsize for _, dtype, _ in STORED_FIELDS) == 38


def test_old_worlds_do_not_invent_reproduction_traits():
    archive = generate(Scenario(initial_population=20, years=1), None)
    assert "infertile" in archive.person(0)
    archive.summary.pop("reproductive_traits_version")
    assert "infertile" not in archive.person(0)
    assert "childfree" not in archive.person(0)


def test_death_metrics_separate_dead_children_from_fully_followed_birth_cohorts():
    data = {
        "birth": np.array([970, 1000, 1000, 1000, 1010, 1020], dtype=np.int32),
        "death": np.array([1010, 1000, 1007, NO_YEAR, 1012, NO_YEAR], dtype=np.int32),
    }
    result = mortality_summary(data, 6, 1, 1020)
    assert result["observed_deaths"] == 4
    assert result["mean_age_at_death"] == 12.25
    assert result["median_age_at_death"] == 4.5
    assert result["deaths_under_15_fraction"] == 0.75
    assert result["completed_childhood_cohort"] == 3
    assert result["completed_childhood_mortality"] == pytest.approx(2 / 3)
    assert result["unresolved_childhood_cohort"] == 2
    assert result["excluded_founders"] == 1


def test_death_metrics_aggregate_across_chunk_boundary_without_counting_founders():
    size, founders = 1_000_003, 999_999
    data = {
        "birth": np.full(size, 1000, dtype=np.int32),
        "death": np.full(size, NO_YEAR, dtype=np.int32),
    }
    data["death"][[0, 999999, 1000000]] = [1040, 1003, 1005]
    result = mortality_summary(data, size, founders, 1020)
    assert result["observed_deaths"] == 3
    assert result["median_age_at_death"] == 5
    assert result["completed_childhood_cohort"] == 4
    assert result["completed_childhood_mortality"] == 0.5


def test_unobserved_mortality_rates_are_null():
    result = mortality_summary(
        {"birth": np.array([1000, 1001]), "death": np.array([NO_YEAR, NO_YEAR])}, 2, 1, 1002
    )
    assert result["mean_age_at_death"] is None
    assert result["median_age_at_death"] is None
    assert result["completed_childhood_mortality"] is None
    assert result["deaths_under_15_fraction"] is None


@pytest.mark.parametrize(
    "changes",
    [
        {"demography": {"female_infertility_rate": 1.1}},
        {"demography": {"male_infertility_rate": -1}},
        {"society": {"childfree_rate": 1.1}},
    ],
)
def test_lifetime_reproduction_rates_are_validated(changes):
    with pytest.raises(ValidationError):
        Scenario(**changes)
