"""Compact normalized SQLite archive and bounded indexed historical queries."""

from __future__ import annotations

import json
import sqlite3
from collections import Counter
from contextlib import closing
from hashlib import sha256
from pathlib import Path

import numpy as np

from .config import Scenario, Settlement
from .inspection import resident_atlas
from .politics import PoliticalTimeline
from .reproduction import ReproductiveTraits
from .schema import STORED_FIELDS, null_sentinel

PERSON_COLUMNS = "id INTEGER PRIMARY KEY," + ",".join(
    f"{name} INTEGER" + ("" if nullable else " NOT NULL") for name, _, nullable in STORED_FIELDS
)
PERSON_INSERT = (
    "INSERT INTO people VALUES (" + ",".join("?" for _ in range(len(STORED_FIELDS) + 1)) + ")"
)
SCHEMA = f"""
CREATE TABLE metadata(key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE settlements(id INTEGER PRIMARY KEY, name TEXT, x REAL, y REAL, kind TEXT,
                         capacity INTEGER, metadata TEXT);
CREATE TABLE activities(id INTEGER PRIMARY KEY, name TEXT UNIQUE);
CREATE TABLE races(id INTEGER PRIMARY KEY, name TEXT UNIQUE, metadata TEXT);
CREATE TABLE person_annotations(person INTEGER, key TEXT, value TEXT,
                               PRIMARY KEY(person,key)) WITHOUT ROWID;
CREATE TABLE people({PERSON_COLUMNS});
CREATE TABLE unions(id INTEGER PRIMARY KEY, male INTEGER NOT NULL, female INTEGER NOT NULL,
 start INTEGER NOT NULL, end INTEGER, place INTEGER NOT NULL, reason TEXT);
CREATE TABLE migrations(id INTEGER PRIMARY KEY, person INTEGER NOT NULL, year INTEGER NOT NULL,
 origin INTEGER NOT NULL, destination INTEGER NOT NULL, reason TEXT NOT NULL);
CREATE TABLE census(year INTEGER PRIMARY KEY, population INTEGER, births INTEGER, deaths INTEGER,
 marriages INTEGER, divorces INTEGER, migrations INTEGER, infant_deaths INTEGER,
 age_0_14 INTEGER, age_15_49 INTEGER, age_50_plus INTEGER, fertile_women INTEGER,
 partnered_fertile_women INTEGER, local_marriages INTEGER, span INTEGER DEFAULT 1);
CREATE TABLE settlement_census(year INTEGER, settlement INTEGER, population INTEGER,
 PRIMARY KEY(year, settlement)) WITHOUT ROWID;
CREATE TABLE population_census(year INTEGER, kind TEXT, category INTEGER, population INTEGER,
 PRIMARY KEY(year,kind,category)) WITHOUT ROWID;
CREATE TABLE settlement_race_census(year INTEGER, settlement INTEGER, race INTEGER,
 population INTEGER, PRIMARY KEY(year,settlement,race)) WITHOUT ROWID;
CREATE TABLE migration_flows(year INTEGER, origin INTEGER, destination INTEGER, reason TEXT,
 population INTEGER, PRIMARY KEY(year,origin,destination,reason)) WITHOUT ROWID;
"""


class Store:
    def __init__(self, path: Path, config, settlements, activities):
        self.pending_flows = Counter()
        self.connection = sqlite3.connect(path)
        self.connection.executescript(SCHEMA)
        self.connection.execute("PRAGMA journal_mode=DELETE")
        self.connection.execute("PRAGMA synchronous=NORMAL")
        self.connection.executemany(
            "INSERT INTO metadata VALUES (?, ?)",
            [
                ("schema_version", "1"),
                ("config", config.model_dump_json()),
                ("config_sha256", sha256(config.model_dump_json().encode()).hexdigest()),
                ("complete", "false"),
            ],
        )
        self.connection.executemany(
            "INSERT INTO settlements VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                (p.id, p.name, p.x, p.y, p.kind, p.capacity, json.dumps(p.metadata))
                for p in settlements
            ],
        )
        self.connection.executemany("INSERT INTO activities VALUES (?, ?)", enumerate(activities))
        self.connection.executemany(
            "INSERT INTO races VALUES (?,?,?)",
            [(i, race.name, json.dumps(race.metadata)) for i, race in enumerate(config.races)],
        )

    def unions(self, rows):
        self.connection.executemany("INSERT INTO unions VALUES (?, ?, ?, ?, NULL, ?, NULL)", rows)

    def close_unions(self, rows):
        self.connection.executemany("UPDATE unions SET end=?, reason=? WHERE id=?", rows)

    def migrations(self, rows):
        self.connection.executemany(
            "INSERT INTO migrations(person,year,origin,destination,reason) VALUES (?,?,?,?,?)", rows
        )
        self.pending_flows.update(
            (origin, destination, reason) for _, _, origin, destination, reason in rows
        )

    def distributions(self, year, groups, racial_places):
        self.connection.executemany(
            "INSERT INTO population_census VALUES (?,?,?,?)",
            (
                (year, kind, category, int(count))
                for kind, values in groups.items()
                for category, count in enumerate(values)
                if count
            ),
        )
        self.connection.executemany(
            "INSERT INTO settlement_race_census VALUES (?,?,?,?)", racial_places
        )

    def census(self, row, places, span=1):
        self.connection.execute(
            "INSERT INTO census VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (*row, span)
        )
        self.connection.executemany(
            "INSERT INTO migration_flows VALUES (?,?,?,?,?)",
            ((row[0], *key, count) for key, count in self.pending_flows.items()),
        )
        self.pending_flows.clear()
        self.connection.executemany("INSERT INTO settlement_census VALUES (?,?,?)", places)
        self.connection.commit()

    def finish(self, data, summary, count=None):
        # Chunk conversion limits temporary Python objects; dense array index is the ID.
        count = len(data) if count is None else count
        for start in range(0, count, 10000):
            end = min(start + 10000, count)
            columns = []
            for field, _, nullable in STORED_FIELDS:
                column = data[field][start:end].tolist()
                if nullable:
                    sentinel = null_sentinel(field)
                    column = [None if value == sentinel else value for value in column]
                columns.append(column)
            rows = zip(range(start, end), *columns, strict=True)
            self.connection.executemany(PERSON_INSERT, rows)
            self.connection.commit()
        self.connection.executescript("""
        CREATE INDEX people_father ON people(father) WHERE father IS NOT NULL;
        CREATE INDEX people_mother ON people(mother) WHERE mother IS NOT NULL;
        CREATE INDEX people_place ON people(place,death,id);
        CREATE INDEX unions_male ON unions(male,start);
        CREATE INDEX unions_female ON unions(female,start);
        CREATE INDEX migrations_person ON migrations(person,year,id);
        """)
        self.connection.execute(
            "INSERT INTO metadata VALUES ('summary', ?)", (json.dumps(summary),)
        )
        self.connection.execute("UPDATE metadata SET value='true' WHERE key='complete'")
        self.connection.commit()

    def annotations(self, rows):
        """Optional JSON metadata outside compact core: (person_id, key, value)."""
        self.connection.executemany(
            "INSERT OR REPLACE INTO person_annotations VALUES (?,?,?)",
            ((pid, key, json.dumps(value)) for pid, key, value in rows),
        )

    def update_summary(self, summary):
        self.connection.execute(
            "UPDATE metadata SET value=? WHERE key='summary'", (json.dumps(summary),)
        )
        self.connection.commit()

    def close(self):
        self.connection.close()


class Archive:
    """Read-only explorer. NULL means unknown parent or no recorded death."""

    def __init__(self, path: Path):
        if not path.is_file():
            raise FileNotFoundError(path)
        self.path = path.resolve()
        with closing(self.connect()) as db:
            complete = db.execute("SELECT value FROM metadata WHERE key='complete'").fetchone()
            if complete is None or complete[0] != "true":
                raise ValueError("Archive is incomplete")
            self.start_year = json.loads(
                db.execute("SELECT value FROM metadata WHERE key='config'").fetchone()[0]
            )["start_year"]
            source = json.loads(
                db.execute("SELECT value FROM metadata WHERE key='config'").fetchone()[0]
            )
            self.config = Scenario.model_validate(source)
            self.reproductive_traits = (
                ReproductiveTraits(self.config)
                if json.loads(
                    db.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0]
                ).get("reproductive_traits_version")
                == 1
                else None
            )
            places = [
                Settlement(**{k: row[k] for k in ("id", "name", "x", "y", "kind", "capacity")})
                for row in db.execute("SELECT * FROM settlements ORDER BY id")
            ]
            self.politics = PoliticalTimeline(self.config, places)
            self.saved_years = {r[0] for r in db.execute("SELECT year FROM census")}
            self.has_distributions = (
                db.execute("SELECT 1 FROM sqlite_master WHERE name='population_census'").fetchone()
                is not None
            )

    def connect(self):
        db = sqlite3.connect(self.path.as_uri() + "?mode=ro", uri=True)
        db.row_factory = sqlite3.Row
        return db

    def overview(self):
        with closing(self.connect()) as db:
            return {
                "summary": json.loads(
                    db.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0]
                ),
                "settlements": [dict(r) for r in db.execute("SELECT * FROM settlements")],
                "activities": [dict(r) for r in db.execute("SELECT * FROM activities")],
                "races": [dict(r) for r in db.execute("SELECT * FROM races")],
                "history": [dict(r) for r in db.execute("SELECT * FROM census ORDER BY year")],
            }

    def person(self, identity: int):
        with closing(self.connect()) as db:
            row = db.execute("SELECT * FROM people WHERE id=?", (identity,)).fetchone()
            if row is None:
                raise KeyError(identity)
            result = dict(row)
            if self.reproductive_traits is not None:
                result.update(self.reproductive_traits.describe(result))
            result["founder"] = row["father"] is None and row["mother"] is None
            result["history_known_from"] = self.start_year if result["founder"] else row["birth"]
            result["annotations"] = {
                r["key"]: json.loads(r["value"])
                for r in db.execute(
                    "SELECT key,value FROM person_annotations WHERE person=?",
                    (identity,),
                )
            }
            result["children"] = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM people WHERE father=? OR mother=? ORDER BY birth LIMIT 200",
                    (identity, identity),
                )
            ]
            if self.reproductive_traits is not None:
                for child in result["children"]:
                    child.update(self.reproductive_traits.describe(child))
            result["unions"] = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM unions WHERE male=? OR female=? ORDER BY start",
                    (identity, identity),
                )
            ]
            result["migrations"] = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM migrations WHERE person=? ORDER BY year,id", (identity,)
                )
            ]
            return result

    def lineage(self, identity: int, depth: int = 4, direction: str = "ancestors", limit=1000):
        if not 0 <= depth <= 12 or not 1 <= limit <= 5000:
            raise ValueError("depth must be 0..12 and limit 1..5000")
        if direction not in {"ancestors", "descendants"}:
            raise ValueError("Unknown lineage direction")
        self.person(identity)
        with closing(self.connect()) as db:
            seen, frontier, rows = {identity}, [identity], []
            for generation in range(1, depth + 1):
                upcoming = []
                for pid in frontier:
                    if direction == "ancestors":
                        candidates = db.execute(
                            "SELECT * FROM people WHERE id IN "
                            "(SELECT father FROM people WHERE id=? UNION "
                            "SELECT mother FROM people WHERE id=?)",
                            (pid, pid),
                        )
                    else:
                        candidates = db.execute(
                            "SELECT * FROM people WHERE father=? OR mother=? ORDER BY id",
                            (pid, pid),
                        )
                    for row in candidates:
                        if row["id"] in seen:
                            continue
                        if len(rows) >= limit:
                            return {"people": rows, "truncated": True}
                        seen.add(row["id"])
                        upcoming.append(row["id"])
                        item = dict(row)
                        if self.reproductive_traits is not None:
                            item.update(self.reproductive_traits.describe(item))
                        rows.append({**item, "generation": generation})
                frontier = upcoming
                if not frontier:
                    break
            return {"people": rows, "truncated": False}

    def residence(self, identity: int, year: int):
        person = self.person(identity)
        if (
            year < person["history_known_from"]
            or year < person["birth"]
            or person["death"] is not None
            and year >= person["death"]
        ):
            return None
        place = person["birth_place"]
        for move in person["migrations"]:
            if move["year"] > year:
                break
            place = move["destination"]
        return place

    def residents(self, settlement: int, limit: int = 100, after: int = -1):
        if not 1 <= limit <= 500:
            raise ValueError("limit must be 1..500")
        with closing(self.connect()) as db:
            rows = [
                dict(r)
                for r in db.execute(
                    "SELECT * FROM people WHERE place=? AND death IS NULL AND id>? ORDER BY id LIMIT ?",
                    (settlement, after, limit),
                )
            ]

            if self.reproductive_traits is not None:
                for row in rows:
                    row.update(self.reproductive_traits.describe(row))
            return rows

    def resident_atlas(self, settlement, **filters):
        with closing(self.connect()) as db:
            rows = db.execute(
                "SELECT id,birth,race,sex FROM people WHERE place=? AND death IS NULL ORDER BY id",
                (settlement,),
            ).fetchall()
            year = json.loads(
                db.execute("SELECT value FROM metadata WHERE key='summary'").fetchone()[0]
            )["end_year"]
        values = np.asarray(rows, dtype=np.int64).reshape(-1, 4)
        # The shared reducer uses dense local row positions, while returned IDs
        # must retain their original archived identity.
        data = {key: values[:, i] for i, key in enumerate(("id", "birth", "race", "sex"))}
        result = resident_atlas(data, np.arange(len(values)), year, **filters)
        for person in result["people"]:
            person["id"] = int(values[person["id"], 0])
        return result

    def map_at(self, year: int, race: int | None = None):
        if year not in self.saved_years:
            raise ValueError("No stored census at this year; choose an available snapshot")
        with closing(self.connect()) as db:
            if race is not None:
                if not self.has_distributions:
                    raise ValueError("Race maps require a newly generated archive")
                rows = [
                    dict(row)
                    for row in db.execute(
                        "SELECT s.id settlement,coalesce(c.population,0) population FROM settlements s "
                        "LEFT JOIN settlement_race_census c ON c.settlement=s.id AND c.year=? "
                        "AND c.race=?",
                        (year, race),
                    )
                ]
            else:
                rows = [
                    dict(r)
                    for r in db.execute(
                        "SELECT settlement,population FROM settlement_census WHERE year=?", (year,)
                    )
                ]
        owners, _, _ = self.politics.at(year)
        for row in rows:
            row["nation"] = int(owners[self.politics.slots[row["settlement"]]])
        return rows

    def distributions(self, year):
        if year not in self.saved_years:
            raise ValueError("No stored census at this year")
        if not self.has_distributions:
            return {"available": False, "groups": {}, "flows": []}
        with closing(self.connect()) as db:
            groups = {}
            for row in db.execute(
                "SELECT kind,category,population FROM population_census WHERE year=?", (year,)
            ):
                groups.setdefault(row["kind"], []).append(dict(row))
            flows = [
                dict(row)
                for row in db.execute(
                    "SELECT origin,destination,sum(population) population FROM migration_flows "
                    "WHERE year=? GROUP BY origin,destination ORDER BY population DESC LIMIT 150",
                    (year,),
                )
            ]
        return {"available": True, "groups": groups, "flows": flows}
