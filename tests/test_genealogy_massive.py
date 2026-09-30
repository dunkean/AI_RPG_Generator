"""Native graph, political chronology and large-map regression checks."""

import itertools
from contextlib import closing

import numpy as np
import pytest
from pydantic import ValidationError

from src.genealogy.config import Scenario, virtual_map
from src.genealogy.engine import Engine, generate
from src.genealogy.kernels import mark_ancestors, shares_ancestor
from src.genealogy.politics import PoliticalTimeline
from src.genealogy.store import Archive


def test_dispersed_map_keeps_all_500_sites_and_seed():
    config = Scenario(virtual_settlements=500, seed=987)
    places = virtual_map(config)
    assert len(places) == len({p.id for p in places}) == 500
    assert places == virtual_map(config)
    assert places != virtual_map(config.model_copy(update={"seed": 988}))
    assert len({p.x for p in places}) == 500
    assert len({p.y for p in places}) == 500


def test_native_kinship_matches_independent_ancestor_search():
    rng = np.random.default_rng(112)
    fathers = np.full(200, -1, np.int32)
    mothers = fathers.copy()
    for pid in range(20, 200):
        fathers[pid], mothers[pid] = rng.choice(pid, 2, replace=False)

    def ancestors(pid, depth):
        result, frontier = {pid}, [pid]
        for _ in range(depth):
            frontier = [
                parent
                for node in frontier
                for parent in (fathers[node], mothers[node])
                if parent >= 0
            ]
            result.update(frontier)
        return result

    for depth in range(1, 7):
        marks = np.zeros(200, np.int32)
        queue = np.empty((1 << (depth + 1)) - 1, np.int64)
        levels = np.empty(len(queue), np.int32)
        for stamp in range(1, 51):
            a, b = rng.choice(200, 2, replace=False)
            mark_ancestors(fathers, mothers, a, depth, marks, stamp, queue, levels)
            found = shares_ancestor(fathers, mothers, b, depth, marks, stamp, queue, levels)
            assert found == bool(ancestors(a, depth) & ancestors(b, depth))


def political_config(**changes):
    source = {
        "initial_population": 500,
        "years": 10,
        "virtual_settlements": 2,
        "nations": [
            {"name": "west", "founded": 1000, "dissolved": 1005, "capital": 0},
            {"name": "east", "founded": 1000, "capital": 1},
        ],
        "territories": [
            {"nation": "west", "settlements": [0], "start_year": 1000, "end_year": 1005},
            {"nation": "east", "settlements": [1], "start_year": 1000},
            {"nation": "east", "settlements": [0], "start_year": 1005},
        ],
        "nation_contacts": [
            {
                "nations": ["west", "east"],
                "start_year": 1003,
                "end_year": 1005,
                "marriage_factor": 0.2,
                "migration_factor": 1,
            }
        ],
    }
    return Scenario.model_validate({**source, **changes})


def test_sovereignty_contacts_and_annexation_dates():
    config = political_config()
    timeline = PoliticalTimeline(config, virtual_map(config))
    assert timeline.at(1002)[0].tolist() == [0, 1]
    assert timeline.factor(0, 1, 1002, "migrations") == 0
    assert timeline.factor(0, 1, 1003, "migrations") == 1
    assert timeline.factor(0, 1, 1003, "marriages") == 0.2
    assert timeline.at(1005)[0].tolist() == [1, 1]
    assert timeline.factor(0, 1, 1005, "marriages") == 1


@pytest.mark.parametrize("backend", ["compiled", "reference"])
def test_closed_borders_prevent_cross_nation_unions_and_migrations(backend):
    config = political_config(backend=backend, years=2, society={"migration_rate": 1})
    engine = Engine(config)
    engine.run()
    assert engine.rows[-1][6] == 0  # marriage moves within a site are not recorded
    partners = engine.data["partner"][engine.alive]
    paired = engine.alive[partners >= 0]
    assert np.all(
        engine.data["birth_place"][paired]
        == engine.data["birth_place"][engine.data["partner"][paired]]
    )


def test_invalid_period_marriage_window_and_overlapping_claim_rejected():
    with pytest.raises(ValidationError, match="Reversed marriage ages"):
        Scenario.model_validate(
            {
                "races": [{"name": "elf", "marriage_min_age": 60}],
                "periods": [{"start_year": 1001, "society": {"marriage_max_age": 50}}],
            }
        )
    with pytest.raises(ValidationError, match="Overlapping territorial"):
        political_config(
            territories=[
                {"nation": "west", "settlements": [0], "start_year": 1000, "end_year": 1005},
                {"nation": "east", "settlements": [0], "start_year": 1004},
            ]
        )


def test_500_site_archive_and_aggregates_reconcile(tmp_path):
    path = tmp_path / "large_map.sqlite"
    generate(
        Scenario(initial_population=5000, virtual_settlements=500, years=3, snapshot_interval=1),
        path,
    )
    archive = Archive(path)
    assert len(archive.map_at(1003)) == 500
    assert len(archive.map_at(1003, race=0)) == 500
    for row in archive.overview()["history"]:
        distributions = archive.distributions(row["year"])
        groups = distributions["groups"]
        for kind in ("race", "status", "activity", "nation"):
            assert sum(r["population"] for r in groups[kind]) == row["population"]
        assert (
            sum(r["population"] for r in groups.get("age_male", []) + groups.get("age_female", []))
            == row["population"]
        )
    with closing(archive.connect()) as db:
        assert (
            db.execute("SELECT sum(population) FROM migration_flows").fetchone()[0]
            == db.execute("SELECT count(*) FROM migrations").fetchone()[0]
        )


def test_decadal_snapshots_preserve_all_exact_events(tmp_path):
    path = tmp_path / "sparse.sqlite"
    generate(Scenario(initial_population=1000, years=23, snapshot_interval=10), path)
    archive = Archive(path)
    history = archive.overview()["history"]
    assert [r["year"] for r in history] == [1000, 1010, 1020, 1023]
    assert [r["span"] for r in history] == [1, 10, 10, 3]
    for previous, current in itertools.pairwise(history):
        assert (
            current["population"] == previous["population"] + current["births"] - current["deaths"]
        )
    with closing(archive.connect()) as db:
        assert (
            sum(r["births"] for r in history)
            == db.execute("SELECT count(*) FROM people WHERE mother IS NOT NULL").fetchone()[0]
        )
        assert (
            sum(r["migrations"] for r in history)
            == db.execute("SELECT count(*) FROM migrations").fetchone()[0]
        )
        assert db.execute("SELECT count(DISTINCT year) FROM migrations").fetchone()[0] > 4
    with pytest.raises(ValueError, match="No stored census"):
        archive.map_at(1001)


def test_capitals_do_not_depend_on_explicit_settlement_order():
    places = [{"id": i, "name": str(i), "x": i, "y": i * 2} for i in [20, 5, 10]]
    source = Scenario.model_validate(
        {
            "settlements": places,
            "nations": [{"name": "a", "founded": 1000}, {"name": "b", "founded": 1000}],
        }
    )
    forward = PoliticalTimeline(source, virtual_map(source))
    backward = PoliticalTimeline(source, sorted(virtual_map(source), key=lambda p: p.id))
    a = {p.id: int(owner) for p, owner in zip(forward.settlements, forward.at(1000)[0])}
    b = {p.id: int(owner) for p, owner in zip(backward.settlements, backward.at(1000)[0])}
    assert a == b


@pytest.mark.parametrize("backend", ["compiled", "reference"])
def test_closed_migration_border_also_prevents_marital_moves(backend):
    config = political_config(
        backend=backend, years=2, foreign_marriage_factor=1, society={"residence": "patrilocal"}
    )
    engine = Engine(config)
    engine.run()
    assert all(row[6] == 0 for row in engine.rows)
