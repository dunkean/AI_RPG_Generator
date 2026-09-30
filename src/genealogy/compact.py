"""Portable packed binary export with implicit IDs and memory-mapped ancestry.

SQLite remains the indexed explorer archive. This export removes SQL row/index
overhead, preserves exact dates and relations, and is readable without SQLite.
No per-person JSON or Python object is stored. Sparse annotations remain JSON.
"""

from __future__ import annotations

import json
from collections import deque
from contextlib import closing
from pathlib import Path

import numpy as np

from .store import Archive

UNKNOWN_PERSON = 2**32 - 1
UNKNOWN_PLACE = 2**16 - 1
UNKNOWN_DATE = -32768


def export_compact(source: Path, destination: Path):
    archive = Archive(source)
    destination = destination.resolve()
    staging = destination.with_name(destination.name + ".partial")
    if destination.exists() or staging.exists():
        raise FileExistsError("Choose a new compact archive directory")
    config = archive.config
    # Scenario dates span <=10,000 years, and founders live <=2,000 years.
    # All dates fit signed relative int16, including the unknown-date sentinel.
    places = archive.overview()["settlements"]
    place_ids = [p["id"] for p in places]
    slots = {identity: slot for slot, identity in enumerate(place_ids)}
    if len(places) >= UNKNOWN_PLACE:
        raise ValueError("Too many sites for compact uint16 slots")
    max_levels = max(
        [
            len(config.society.status_weights),
            *(len(p.society.status_weights or []) for p in config.periods),
        ]
    )
    small = "u1" if max_levels <= 128 else "<u2"
    dtype = np.dtype(
        [
            ("father", "<u4"),
            ("mother", "<u4"),
            ("birth", "<i2"),
            ("death", "<i2"),
            ("birth_place", "<u2"),
            ("place", "<u2"),
            ("death_place", "<u2"),
            ("sex_status", small),
            ("activity", "u1" if len(archive.overview()["activities"]) <= 256 else "<u2"),
            ("race", "u1" if len(config.races) <= 256 else "<u2"),
        ]
    )
    staging.mkdir(parents=True)
    with closing(archive.connect()) as db:
        n = db.execute("SELECT count(*) FROM people").fetchone()[0]
        if n >= UNKNOWN_PERSON:
            raise ValueError("Too many records for uint32 parent IDs")
        people = np.lib.format.open_memmap(
            staging / "people.npy", mode="w+", dtype=dtype, shape=(n,)
        )
        cursor = db.execute("SELECT * FROM people ORDER BY id")
        position = 0
        while rows := cursor.fetchmany(10000):
            count = len(rows)
            ids = np.fromiter((r["id"] for r in rows), dtype=np.int64)
            if not np.array_equal(ids, np.arange(position, position + count)):
                raise ValueError("Compact export requires dense person IDs")
            if any(
                r[field] is not None and not 0 <= r[field] < r["id"]
                for r in rows
                for field in ("father", "mother")
            ):
                raise ValueError("Invalid parent ID/order in source archive")
            for field in ("father", "mother"):
                people[field][position : position + count] = [
                    UNKNOWN_PERSON if r[field] is None else r[field] for r in rows
                ]
            for field in ("birth", "death"):
                people[field][position : position + count] = [
                    UNKNOWN_DATE if r[field] is None else r[field] - config.start_year for r in rows
                ]
            for field in ("birth_place", "place", "death_place"):
                people[field][position : position + count] = [
                    UNKNOWN_PLACE if r[field] is None else slots[r[field]] for r in rows
                ]
            people["sex_status"][position : position + count] = [
                r["sex"] | (r["status"] << 1) for r in rows
            ]
            for field in ("activity", "race"):
                people[field][position : position + count] = [r[field] for r in rows]
            position += count
        people.flush()
        del people  # close the mapping before renaming on Windows

        reason_names = sorted(
            {r[0] for r in db.execute("SELECT DISTINCT reason FROM unions") if r[0] is not None}
            | {r[0] for r in db.execute("SELECT DISTINCT reason FROM migrations")}
        )
        reasons = {name: i for i, name in enumerate(reason_names)}
        if len(reasons) > 254:
            raise ValueError("Too many event reasons")
        for table, layout in (
            (
                "unions",
                [
                    ("male", "<u4"),
                    ("female", "<u4"),
                    ("start", "<i2"),
                    ("end", "<i2"),
                    ("place", "<u2"),
                    ("reason", "u1"),
                ],
            ),
            (
                "migrations",
                [
                    ("person", "<u4"),
                    ("year", "<i2"),
                    ("origin", "<u2"),
                    ("destination", "<u2"),
                    ("reason", "u1"),
                ],
            ),
        ):
            size = db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
            data = np.lib.format.open_memmap(
                staging / f"{table}.npy", mode="w+", dtype=np.dtype(layout), shape=(size,)
            )
            cursor = db.execute(f"SELECT * FROM {table} ORDER BY id")
            position = 0
            while rows := cursor.fetchmany(10000):
                for field, _ in layout:
                    if field in ("start", "end", "year"):
                        values = [
                            UNKNOWN_DATE if r[field] is None else r[field] - config.start_year
                            for r in rows
                        ]
                    elif field in ("place", "origin", "destination"):
                        values = [slots[r[field]] for r in rows]
                    elif field == "reason":
                        values = [255 if r[field] is None else reasons[r[field]] for r in rows]
                    else:
                        values = [r[field] for r in rows]
                    data[field][position : position + len(rows)] = values
                position += len(rows)
            data.flush()
            del data
        manifest = {
            "format": "ttrpg-compact-v1",
            "person_bytes": dtype.itemsize,
            "people": n,
            "config": config.model_dump(mode="json"),
            "overview": archive.overview(),
            "place_ids": place_ids,
            "reasons": reason_names,
            "family": "patriline root; derived from father links",
        }
        # Stream sparse extensions and saved aggregates, avoiding a global list in RAM.
        for table in (
            "person_annotations",
            "settlement_census",
            "population_census",
            "settlement_race_census",
            "migration_flows",
        ):
            if (
                table not in ("person_annotations", "settlement_census")
                and not archive.has_distributions
            ):
                continue
            with (staging / f"{table}.jsonl").open("w", encoding="utf-8") as output:
                for row in db.execute(f"SELECT * FROM {table}"):
                    output.write(json.dumps(dict(row)) + "\n")
        (staging / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    staging.rename(destination)
    return {
        "directory": str(destination),
        "person_bytes": dtype.itemsize,
        "people": n,
        "total_bytes": sum(p.stat().st_size for p in destination.iterdir()),
    }


class CompactArchive:
    """Direct record/parent access; no global load and no fabricated ancestors."""

    def __init__(self, directory: Path):
        self.manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        if self.manifest["format"] != "ttrpg-compact-v1":
            raise ValueError("Unsupported compact archive")
        self.people = np.load(directory / "people.npy", mmap_mode="r", allow_pickle=False)

    def close(self):
        self.people._mmap.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def person(self, identity: int):
        if not 0 <= identity < len(self.people):
            raise KeyError(identity)
        row = self.people[identity]
        result = {name: int(row[name]) for name in row.dtype.names}
        result["id"] = identity
        result["sex"], result["status"] = result.pop("sex_status") & 1, int(row["sex_status"]) >> 1
        for field in ("father", "mother"):
            if result[field] == UNKNOWN_PERSON:
                result[field] = None
        for field in ("birth", "death"):
            value = result[field]
            result[field] = (
                None if value == UNKNOWN_DATE else value + self.manifest["config"]["start_year"]
            )
        for field in ("birth_place", "place", "death_place"):
            value = result[field]
            result[field] = None if value == UNKNOWN_PLACE else self.manifest["place_ids"][value]
        root = identity
        while int(self.people["father"][root]) != UNKNOWN_PERSON:
            root = int(self.people["father"][root])
        result["family"] = root
        return result

    def ancestors(self, identity: int, depth: int = 4, limit: int = 1000):
        if not 1 <= depth <= 1000 or not 1 <= limit <= 100000:
            raise ValueError("Use depth 1..1000 and limit 1..100000")
        self.person(identity)
        frontier, seen, result = deque([(identity, 0)]), {identity}, []
        while frontier:
            pid, level = frontier.popleft()
            if level >= depth:
                continue
            person = self.person(pid)
            for parent in (person["father"], person["mother"]):
                if parent is not None and parent not in seen:
                    if len(result) >= limit:
                        return {"people": result, "truncated": True}
                    seen.add(parent)
                    result.append(self.person(parent))
                    frontier.append((parent, level + 1))
        return {"people": result, "truncated": False}
