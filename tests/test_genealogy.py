"""Life-history invariants, deterministic scenarios and fantasy ancestry."""

import sqlite3
from contextlib import closing
from itertools import pairwise

import numpy as np
import pytest
from pydantic import ValidationError

from src.genealogy.config import Scenario, load_scenario, virtual_map
from src.genealogy.engine import Engine, generate, scaled_probability
from src.genealogy.store import Archive


def scenario(**changes):
    return Scenario.model_validate({"initial_population": 300, "years": 30, **changes})


def quiet_demography(**changes):
    return {
        "infant_mortality": 0,
        "child_mortality": 0,
        "adult_mortality": 0,
        "aging_coefficient": 0,
        "maternal_mortality": 0,
        **changes,
    }


def test_virtual_place_quotas_minima_and_profile_inheritance():
    config = scenario(
        virtual_settlements=10,
        capacity_mode="fixed",
        settlement_types=[
            {
                "kind": "capital",
                "share": 0,
                "minimum_count": 1,
                "capacity": 10000,
                "initial_weight": 0.1,
                "activities": {"trade": 1},
                "races": {"human": 1},
                "metadata": {"seat": True},
            },
            {"kind": "village", "share": 2, "capacity": 600},
            {"kind": "hamlet", "share": 1, "capacity": 100},
        ],
    )
    places = virtual_map(config)
    assert [p.model_dump() for p in places] == [p.model_dump() for p in virtual_map(config)]
    assert {
        kind: sum(p.kind == kind for p in places) for kind in ("capital", "village", "hamlet")
    } == {"capital": 1, "village": 6, "hamlet": 3}
    capital = next(p for p in places if p.kind == "capital")
    assert capital.capacity == 10000 and capital.initial_weight == 1000
    assert capital.activities == {"trade": 1}
    assert capital.races == {"human": 1} and capital.metadata == {"seat": True}


@pytest.mark.parametrize(
    "types",
    [
        [],
        [{"kind": "village", "capacity": 10, "share": 0}],
        [{"kind": "village", "capacity": 10, "minimum_count": 3}],
        [{"kind": "village", "capacity": 10, "races": {"unknown": 1}}],
        [{"kind": "village", "capacity": 10, "activities": {"craft": 0}}],
    ],
)
def test_invalid_virtual_place_profiles(types):
    with pytest.raises(ValidationError):
        scenario(virtual_settlements=2, settlement_types=types)


def test_small_virtual_map_and_explicit_map_override():
    assert len(virtual_map(scenario(virtual_settlements=1))) == 1
    config = scenario(
        capacity_mode="fixed",
        settlement_types=[],
        settlements=[
            {"id": 42, "name": "Custom", "kind": "fortress", "x": 5, "y": 8, "capacity": 20},
        ],
    )
    assert virtual_map(config) == config.settlements


def test_fractional_place_quotas_and_independent_metadata():
    config = scenario(
        virtual_settlements=7,
        settlement_types=[
            {
                "kind": "mining_village",
                "share": 2,
                "capacity": 600,
                "metadata": {"resources": ["iron"]},
            },
            {"kind": "hamlet", "share": 1, "capacity": 100},
        ],
    )
    places = virtual_map(config)
    mining = [p for p in places if p.kind == "mining_village"]
    assert len(mining) == 5 and len(places) == 7
    assert mining[0].name.startswith("Mining Village")
    mining[0].metadata["resources"].append("gold")
    assert mining[1].metadata["resources"] == ["iron"]
    assert config.settlement_types[0].metadata["resources"] == ["iron"]


def test_exact_place_counts_allow_zero_shares_and_distinct_profiles_of_same_kind():
    config = scenario(
        virtual_settlements=2,
        capacity_mode="fixed",
        settlement_types=[
            {
                "kind": "village",
                "share": 0,
                "minimum_count": 1,
                "capacity": 100,
                "activities": {"fishing": 1},
            },
            {
                "kind": "village",
                "share": 0,
                "minimum_count": 1,
                "capacity": 200,
                "activities": {"agriculture": 1},
            },
        ],
    )
    places = virtual_map(config)
    assert sorted(p.capacity for p in places) == [100, 200]
    assert {next(iter(p.activities)) for p in places} == {"fishing", "agriculture"}


def couple(config):
    engine = Engine(config)
    engine.year = config.start_year + 1
    d = engine.data
    d["sex"][:2] = [0, 1]
    d["birth"][:2] = engine.year - 27
    d["partner"][:2] = [1, 0]
    d["union"][:2] = 0
    d["last_birth"][:2] = config.start_year - 10
    d["place"][:2] = d["birth_place"][0]
    d["place_slot"][:2] = d["place_slot"][0]
    return engine


@pytest.mark.parametrize(
    "invalid",
    [
        {"seed": -1},
        {"demography": {"fertility_peak": 1.1}},
        {"society": {"status_weights": [0, 0]}},
        {"events": [{"name": "war", "start_year": 1001, "end_year": 1002, "settlements": [999]}]},
        {"periods": [{"start_year": 1001, "demography": {"fertility_min_age": 50}}]},
        {"crossbreeding": [{"parents": ["human", "elf"], "offspring": {"half": 1}}]},
        {"unsupported_option": True},
    ],
)
def test_invalid_configuration_rejected(invalid):
    with pytest.raises(ValidationError):
        scenario(**invalid)


def test_periods_merge_partial_settings_and_keep_previous_changes():
    engine = Engine(
        scenario(
            demography={"adult_mortality": 0.04},
            periods=[
                {
                    "start_year": 1001,
                    "demography": {"infant_mortality": 0.1},
                    "society": {"marriage_min_age": 21},
                },
                {"start_year": 1002, "demography": {"fertility_peak": 0.2}},
            ],
        )
    )
    engine.year = 1002
    engine._apply_periods()
    assert engine.demography.adult_mortality == 0.04
    assert engine.demography.infant_mortality == 0.1
    assert engine.demography.fertility_peak == 0.2
    assert engine.society.marriage_min_age == 21


def test_seed_determinism_and_no_global_rng_change():
    np.random.seed(91)
    expected = np.random.random()
    np.random.seed(91)
    first, second = Engine(scenario()), Engine(scenario())
    first.run()
    second.run()
    np.testing.assert_array_equal(first.data[: first.n], second.data[: second.n])
    assert first.rows == second.rows
    assert np.random.random() == expected


def test_unknown_parents_do_not_create_false_kinship():
    engine = Engine(scenario(initial_population=6, years=1))
    assert not engine.related(0, 1)
    engine.data["father"][2:4] = 0
    engine.data["mother"][2:4] = 1
    assert engine.related(2, 3)
    assert engine.related(0, 2)
    engine.data["father"][4] = 2
    engine.data["father"][5] = 3
    assert engine.related(4, 5)


def test_birth_year_infant_deaths_and_birth_spacing():
    engine = couple(
        scenario(
            initial_population=2,
            years=3,
            demography=quiet_demography(fertility_peak=1),
            events=[
                {
                    "name": "Infant mortality",
                    "start_year": 1001,
                    "end_year": 1001,
                    "min_age": 0,
                    "max_age": 0,
                    "extra_mortality": 1,
                }
            ],
        )
    )
    births, maternal = engine._births()
    assert births == 1
    baby = engine.n - 1
    assert engine.data["mother"][baby] == 1
    assert engine.data["father"][baby] == 0
    deaths, infants = engine._deaths(maternal)
    assert deaths == infants == 1
    assert engine.data["birth"][baby] == engine.data["death"][baby]
    engine.year += 1
    assert engine._births()[0] == 0


def test_household_migration_and_maternal_custody_after_divorce():
    engine = couple(
        scenario(initial_population=2, years=5, demography=quiet_demography(fertility_peak=1))
    )
    engine._births()
    child = engine.n - 1
    guardians = engine._dependents()
    assert child in guardians[1]
    assert child not in guardians[0]
    members = engine._household([0, 1], guardians)
    destination = int(engine.place_ids[-1])
    engine._move(members, destination, "test")
    assert all(engine.data["place"][pid] == destination for pid in members)
    engine._end_union(np.array([0], dtype=np.int32), "divorce")
    engine._move(engine._household([0], engine._dependents()), int(engine.place_ids[0]), "test")
    assert engine.data["place"][child] == engine.data["place"][1]


def test_archive_census_migration_parentage_and_unions(tmp_path):
    path = tmp_path / "world.sqlite"
    config = scenario(
        initial_population=600, years=45, society={"divorce_rate": 0.08, "migration_rate": 0.2}
    )
    result = generate(config, path)
    archive = Archive(path)
    with closing(archive.connect()) as db:
        people = {r["id"]: dict(r) for r in db.execute("SELECT * FROM people")}
        census = list(db.execute("SELECT * FROM census ORDER BY year"))
        for old, new in pairwise(census):
            assert new["population"] == old["population"] + new["births"] - new["deaths"]
        for row in census:
            assert (
                row["population"]
                == db.execute(
                    "SELECT count(*) FROM people WHERE birth<=? AND (death IS NULL OR death>?)",
                    (row["year"], row["year"]),
                ).fetchone()[0]
            )
            assert (
                row["marriages"]
                == db.execute(
                    "SELECT count(*) FROM unions WHERE start=?", (row["year"],)
                ).fetchone()[0]
            )
            assert (
                row["migrations"]
                == db.execute(
                    "SELECT count(*) FROM migrations WHERE year=?", (row["year"],)
                ).fetchone()[0]
            )
        episodes = {}
        for union in db.execute("SELECT * FROM unions ORDER BY start,id"):
            assert union["end"] is None or union["end"] >= union["start"]
            for pid in (union["male"], union["female"]):
                assert pid not in episodes or episodes[pid] < union["start"]
                episodes[pid] = union["end"] or config.start_year + config.duration + 1
        for pid, p in people.items():
            if p["mother"] is not None:
                mother, father = people[p["mother"]], people[p["father"]]
                assert (
                    config.demography.fertility_min_age
                    <= p["birth"] - mother["birth"]
                    <= config.demography.fertility_max_age
                )
                assert mother["death"] is None or mother["death"] >= p["birth"]
                assert father["death"] is None or father["death"] >= p["birth"]
            place = p["birth_place"]
            for move in db.execute(
                "SELECT * FROM migrations WHERE person=? ORDER BY year,id", (pid,)
            ):
                assert move["origin"] == place
                place = move["destination"]
            assert place == p["place"]
            if p["death"] is not None:
                assert p["birth"] <= p["death"] <= p["birth"] + config.demography.max_age
                assert p["death_place"] == place
        assert result["population"] == sum(p["death"] is None for p in people.values())
    pid = max(people)
    assert archive.lineage(pid)["people"]
    assert archive.residence(pid, people[pid]["birth"] - 1) is None
    with pytest.raises(FileExistsError):
        generate(config, path)
    with pytest.raises(ValueError):
        archive.lineage(pid, 100)


def test_close_kin_never_married_even_after_generations(tmp_path):
    config = scenario(
        initial_population=80,
        years=100,
        virtual_settlements=1,
        demography=quiet_demography(fertility_peak=0.5),
    )
    engine = Engine(config)
    engine.run()
    # Current unions plus the archive's complete history are checked independently.
    path = tmp_path / "kin.sqlite"
    generate(config, path)
    with closing(Archive(path).connect()) as db:
        for union in db.execute("SELECT * FROM unions"):
            assert not engine.ancestors(union["male"]) & engine.ancestors(union["female"])
    assert engine.kin_rejections > 0


def test_sparse_external_place_ids_and_occupation_compatibility():
    config = scenario(
        settlements=[
            {"id": 200, "name": "Mine", "x": 0, "y": 0, "activities": {"mining": 1}},
            {"id": 5, "name": "Port", "x": 1, "y": 0, "activities": {"fishing": 1}},
        ],
        society={"migration_rate": 0.5},
    )
    engine = Engine(config)
    engine.run()
    for pid in engine.alive:
        assert engine.place_ids[engine.data["place_slot"][pid]] == engine.data["place"][pid]
        assert (
            engine.data["activity"][pid]
            in engine.activity_options[int(engine.data["place"][pid])][0]
        )


def test_target_virtual_capacity_scales_and_error_is_reported(tmp_path):
    config = scenario(target_population=10000, years=20)
    assert sum(p.capacity for p in virtual_map(config)) >= 1.5 * config.target_population - 20
    result = generate(config, tmp_path / "target.sqlite")
    assert abs(result["target_relative_error"]) < 0.20
    assert result["calibration"]["estimated_initial"] == result["initial_population"]


def test_fantasy_crossbreeding_and_racial_fertility(tmp_path):
    config = scenario(
        initial_population=2,
        years=2,
        demography=quiet_demography(fertility_peak=1),
        races=[
            {"name": "human"},
            {
                "name": "elf",
                "initial_weight": 0,
                "marriage_min_age": 60,
                "marriage_max_age": 350,
                "demography": {
                    "max_age": 500,
                    "fertility_min_age": 60,
                    "fertility_max_age": 300,
                    "fertility_peak_age": 100,
                },
            },
            {"name": "half_elf", "initial_weight": 0},
        ],
        crossbreeding=[
            {"parents": ["human", "elf"], "marriage_affinity": 0.02, "offspring": {"half_elf": 1}}
        ],
    )
    engine = couple(config)
    engine.data["race"][:2] = [0, 1]
    engine.data["birth"][1] = engine.year - 27
    assert engine._births()[0] == 0  # elf parent not mature
    engine.data["birth"][1] = engine.year - 100
    assert engine._births()[0] == 1
    assert engine.data["race"][engine.n - 1] == 2
    sterile_config = Scenario.model_validate(
        {
            **config.model_dump(),
            "crossbreeding": [
                {"parents": ["human", "elf"], "fertility_factor": 0, "offspring": {"half_elf": 1}},
            ],
        }
    )
    sterile = couple(sterile_config)
    sterile.data["race"][:2] = [0, 1]
    sterile.data["birth"][1] = sterile.year - 100
    assert sterile._births()[0] == 0


def test_rare_crossing_and_elf_lifespan():
    config = scenario(
        initial_population=1500,
        years=20,
        races=[
            {"name": "human"},
            {
                "name": "elf",
                "demography": {
                    "max_age": 400,
                    "adult_mortality": 0.001,
                    "aging_coefficient": 0.000001,
                    "aging_exponent": 0.025,
                },
            },
            {"name": "half_elf", "initial_weight": 0},
        ],
        crossbreeding=[
            {"parents": ["human", "elf"], "marriage_affinity": 0.03, "offspring": {"half_elf": 1}}
        ],
    )
    engine = Engine(config)
    assert np.any(
        (engine.data["race"][: engine.n] == 1) & (1000 - engine.data["birth"][: engine.n] > 100)
    )
    engine.run()
    births = np.arange(config.initial_population, engine.n)
    mother_race = engine.data["race"][engine.data["mother"][births]]
    father_race = engine.data["race"][engine.data["father"][births]]
    mixed = mother_race != father_race
    assert 0 < mixed.sum() < len(births) * 0.15
    assert np.all(engine.data["race"][births[mixed]] == 2)


def test_race_scoped_epidemic_includes_old_elves():
    config = scenario(
        initial_population=2,
        years=2,
        races=[
            {"name": "human"},
            {"name": "elf", "initial_weight": 0, "demography": {"max_age": 500}},
        ],
        events=[
            {
                "name": "elf plague",
                "start_year": 1001,
                "end_year": 1001,
                "races": ["elf"],
                "extra_mortality": 1,
            }
        ],
    )
    engine = couple(config)
    engine.data["race"][:2] = [0, 1]
    engine.data["birth"][1] = engine.year - 250
    _, extra, _, _, _ = engine._events(engine.alive)
    assert extra.tolist() == [0, 1]


def test_custom_rule_extension_and_hazard_composition():
    class NoBirths:
        def apply(self, engine, process, ids, hazards):
            hazards["fertility"][:] = 0

    engine = Engine(scenario(), rules=[NoBirths()])
    assert engine.run()["births"] == 0
    assert scaled_probability(0.2, 2) == pytest.approx(0.36)
    assert scaled_probability(1, 0) == 0


def test_negative_calendar_deaths_round_trip(tmp_path):
    config = scenario(
        initial_population=100,
        years=4,
        start_year=-3,
        demography=quiet_demography(fertility_peak=0),
        events=[
            {"name": "catastrophe", "start_year": -1, "end_year": -1, "extra_mortality": 1},
        ],
    )
    path = tmp_path / "negative.sqlite"
    result = generate(config, path)
    assert result["population"] == 0
    archive = Archive(path)
    with closing(archive.connect()) as db:
        assert db.execute("SELECT count(*) FROM people WHERE death=-1").fetchone()[0] == 100
        assert db.execute("SELECT count(*) FROM people WHERE death IS NULL").fetchone()[0] == 0
    assert archive.residence(0, -2) is not None
    assert archive.residence(0, -1) is None


def test_mortality_table_no_nan_for_long_lived_species():
    from src.genealogy.config import Demography
    from src.genealogy.engine import mortality_table

    table = mortality_table(Demography(max_age=2000, aging_exponent=5, aging_coefficient=0))
    assert np.isfinite(table).all()


def test_minority_partner_matching_uses_compatible_pool():
    engine = Engine(
        scenario(
            initial_population=4000,
            years=1,
            virtual_settlements=1,
            races=[{"name": "human", "initial_weight": 99}, {"name": "elf", "initial_weight": 1}],
        )
    )
    ids = engine.alive
    d = engine.data
    eligible = (
        (d["race"][ids] == 1)
        & (d["sex"][ids] == 1)
        & (1000 - d["birth"][ids] >= 18)
        & (1000 - d["birth"][ids] <= 65)
    )
    assert eligible.sum() > 5
    assert np.sum(eligible & (d["partner"][ids] >= 0)) >= eligible.sum() * 0.25


def test_generate_calibration_respects_custom_rules(tmp_path):
    class NoBirths:
        def apply(self, engine, process, ids, hazards):
            if process == "births":
                hazards["fertility"][:] = 0

    config = scenario(target_population=1000, years=10)
    result = generate(config, tmp_path / "rules.sqlite", rules=[NoBirths()])
    assert result["births"] == 0
    pilot = Engine(
        scenario(initial_population=config.calibration_population, years=10), rules=[NoBirths()]
    )
    expected = pilot.run()["population"]
    assert result["calibration"]["pilot_final"] == expected


def test_extension_random_streams_advance_and_isolate_processes():
    first, second = Engine(scenario()), Engine(scenario())
    a = first.stream("custom_rule", "births").random(5)
    b = first.stream("custom_rule", "births").random(5)
    assert not np.array_equal(a, b)
    np.testing.assert_array_equal(a, second.stream("custom_rule", "births").random(5))
    np.testing.assert_array_equal(b, second.stream("custom_rule", "births").random(5))
    assert not np.array_equal(a, first.stream("custom_rule", "deaths").random(5))


def test_married_people_migrate_independently_of_parental_dependent_age():
    config = scenario(
        initial_population=2, years=1, society={"dependent_age": 100, "migration_rate": 1}
    )
    engine = couple(config)
    initial = int(engine.data["place"][0])
    engine._migrations()
    assert engine.data["place"][0] != initial
    assert engine.data["place"][0] == engine.data["place"][1]


def test_example_scenarios_load():
    from pathlib import Path

    for name in ("medieval", "fantasy"):
        assert load_scenario(Path(f"config/genealogy/{name}.yaml")).duration > 0


def test_http_explorer_endpoints_are_read_only_and_bounded(tmp_path):
    import json
    import threading
    from http.server import ThreadingHTTPServer
    from urllib.error import HTTPError
    from urllib.request import urlopen

    from src.genealogy.server import make_handler

    path = tmp_path / "http.sqlite"
    summary = generate(scenario(initial_population=80, years=5), path)
    archive = Archive(path)
    assert archive.overview()["summary"]["archive_bytes"] == path.stat().st_size
    assert summary["total_seconds"] > 0
    with ThreadingHTTPServer(("127.0.0.1", 0), make_handler(archive)) as server:
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        root = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(root, timeout=5) as response:
                assert b"Atlas" in response.read()
            with urlopen(root + "/api/person?id=0", timeout=5) as response:
                person = json.load(response)
                assert person["founder"]
            with urlopen(root + "/api/lineage?id=0&depth=4", timeout=5) as response:
                assert not json.load(response)["truncated"]
            for suffix, code in [
                ("/api/person?id=999999", 404),
                ("/api/lineage?id=0&depth=999", 400),
            ]:
                with pytest.raises(HTTPError) as error:
                    urlopen(root + suffix, timeout=5)
                assert error.value.code == code
        finally:
            server.shutdown()
            worker.join(timeout=5)
    with (
        closing(archive.connect()) as db,
        pytest.raises(sqlite3.OperationalError, match="readonly"),
    ):
        db.execute("DELETE FROM people")
