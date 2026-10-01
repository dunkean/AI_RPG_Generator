"""Exact native binary histories and indexed exploration, without filesystem I/O."""

from __future__ import annotations

import json
import threading
import time
from collections import Counter
from pathlib import Path

import numpy as np

from .politics import PoliticalTimeline
from .reproduction import ReproductiveTraits
from .schema import STORED_FIELDS, null_sentinel

REASONS = {"death": 1, "divorce": 2, "marriage": 3, "household": 4}
REASON_NAMES = {value: key for key, value in REASONS.items()}
CENSUS_FIELDS = [
    "year",
    "population",
    "births",
    "deaths",
    "marriages",
    "divorces",
    "migrations",
    "infant_deaths",
    "age_0_14",
    "age_15_49",
    "age_50_plus",
    "fertile_women",
    "partnered_fertile_women",
    "local_marriages",
    "span",
]


class BinaryTable:
    """Geometrically grown packed rows; append and updates use native array operations."""

    def __init__(self, fields):
        self.data = np.empty(0, dtype=fields)
        self.n = 0

    def append(self, rows):
        if rows is None or not len(rows):
            return
        end = self.n + len(rows)
        if end > len(self.data):
            enlarged = np.empty(max(end, 4096, len(self.data) * 2), dtype=self.data.dtype)
            enlarged[: self.n] = self.data[: self.n]
            self.data = enlarged
        for i, field in enumerate(self.data.dtype.names):
            self.data[field][self.n : end] = rows[:, i]
        self.n = end

    def seal(self):
        self.data = self.data[: self.n].copy()


class MemoryArchive:
    """Store sink and immutable explorer; individuals are never Python objects in storage."""

    ephemeral = True

    def __init__(self, path, config, settlements, activities):
        self.path = Path("memory.world")
        self.created = time.time()
        self.config, self.settlements, self.activities = config, settlements, activities
        self.reproductive_traits = ReproductiveTraits(config)
        self.start_year = config.start_year
        self.politics = PoliticalTimeline(config, settlements)
        self.saved_years, self.has_distributions = set(), True
        self.union_table = BinaryTable(
            [
                ("id", "i4"),
                ("male", "i4"),
                ("female", "i4"),
                ("start", "i4"),
                ("place", "i4"),
                ("end", "i4"),
                ("reason", "u1"),
            ]
        )
        self.move_table = BinaryTable(
            [
                ("person", "i4"),
                ("year", "i4"),
                ("origin", "i4"),
                ("destination", "i4"),
                ("reason", "u1"),
            ]
        )
        self.history, self.maps, self.groups, self.racial_maps, self.flows = [], {}, {}, {}, {}
        self.pending_flows = Counter()
        self.annotation_values = {}
        self.indexes = {}
        self.lock = threading.RLock()

    def unions(self, rows):
        values = rows.numeric()
        if values is not None:
            extra = np.column_stack(
                (
                    np.full(len(values), null_sentinel("death"), dtype=np.int32),
                    np.zeros(len(values), dtype=np.int32),
                )
            )
            self.union_table.append(np.column_stack((values, extra)))

    def close_unions(self, rows):
        values = rows.numeric(REASONS)
        if values is not None:
            self.union_table.data["end"][values[:, 1]] = values[:, 0]
            self.union_table.data["reason"][values[:, 1]] = values[:, 2]

    def migrations(self, rows):
        values = rows.numeric(REASONS)
        self.move_table.append(values)
        if values is not None:
            codes = (values[:, 2].astype(np.uint64) << np.uint64(32)) | values[:, 3].astype(
                np.uint32
            ).astype(np.uint64)
            pairs, counts = np.unique(codes, return_counts=True)
            self.pending_flows.update(
                {
                    (int(code >> np.uint64(32)), int(code & np.uint64(0xFFFFFFFF))): int(count)
                    for code, count in zip(pairs, counts, strict=True)
                }
            )

    def _store_distributions(self, year, groups, racial_places):
        self.groups[year] = {key: value.copy() for key, value in groups.items()}
        self.racial_maps[year] = np.array(list(racial_places), dtype=np.int64).reshape(-1, 4)

    def census(self, row, places, span=1):
        self.saved_years.add(row[0])
        self.history.append(dict(zip(CENSUS_FIELDS, (*row, span), strict=True)))
        self.maps[row[0]] = np.array(places, dtype=np.int64)
        self.flows[row[0]] = [
            {"origin": a, "destination": b, "population": count}
            for (a, b), count in sorted(
                self.pending_flows.items(), key=lambda item: (-item[1], item[0])
            )[:150]
        ]
        self.pending_flows.clear()

    def annotations(self, rows):
        for pid, key, value in rows:
            self.annotation_values.setdefault(pid, {})[key] = value

    def finish(self, data, summary, count=None):
        self.n = len(data) if count is None else count
        # Own compact columns; release runtime fields and unused allocation capacity.
        stored = {name for name, _, _ in STORED_FIELDS}
        for name in list(data.columns):
            if name not in stored:
                del data.columns[name]
        self.data = {}
        for name, _, _ in STORED_FIELDS:
            column = data.columns.pop(name)
            self.data[name] = column[: self.n].copy()
            del column
        self.union_table.seal()
        self.move_table.seal()
        self.summary = summary
        summary["storage"] = "native-binary-memory-v1"
        summary["archive_bytes"] = sum(a.nbytes for a in self.data.values()) + (
            self.union_table.data.nbytes + self.move_table.data.nbytes
        )
        summary["disk_bytes_written"] = 0
        from .kernels import stable_groups

        alive = np.flatnonzero(self.data["death"] == null_sentinel("death")).astype(np.int32)
        place_ids = np.array(sorted(p.id for p in self.settlements), np.int32)
        codes = np.searchsorted(place_ids, self.data["place"][alive])
        order, keys, starts, sizes = stable_groups(codes, len(place_ids))
        self.resident_ids = alive[order]
        self.resident_ranges = {
            int(place_ids[k]): (int(a), int(a + size))
            for k, a, size in zip(keys, starts, sizes, strict=True)
        }

    def update_summary(self, summary):
        self.summary = summary

    def close(self):
        pass

    def overview(self):
        return {
            "summary": self.summary,
            "settlements": [
                {**p.model_dump(mode="json"), "metadata": json.dumps(p.metadata)}
                for p in self.settlements
            ],
            "activities": [{"id": i, "name": a} for i, a in enumerate(self.activities)],
            "races": [
                {"id": i, "name": r.name, "metadata": json.dumps(r.metadata)}
                for i, r in enumerate(self.config.races)
            ],
            "history": self.history,
        }

    def _person(self, identity):
        if not 0 <= identity < self.n:
            raise KeyError(identity)
        result = {"id": int(identity)}
        for name, _, nullable in STORED_FIELDS:
            value = int(self.data[name][identity])
            result[name] = None if nullable and value == null_sentinel(name) else value
        if self.summary.get("reproductive_traits_version") == 1:
            result.update(self.reproductive_traits.describe(result))
        return result

    def _lookup(self, key, column, value):
        # Build only requested indexes, once per immutable archive. No O(N) query per ancestor.
        with self.lock:
            if key not in self.indexes:
                order = np.argsort(column, kind="stable").astype(np.int32)
                self.indexes[key] = order
            order = self.indexes[key]
        a, b = (
            np.searchsorted(column, value, side="left", sorter=order),
            np.searchsorted(column, value, side="right", sorter=order),
        )
        return order[a:b]

    def _children(self, identity):
        return np.union1d(
            self._lookup("father", self.data["father"], identity),
            self._lookup("mother", self.data["mother"], identity),
        )

    def person(self, identity):
        result = self._person(identity)
        result["founder"] = result["father"] is None and result["mother"] is None
        result["history_known_from"] = self.start_year if result["founder"] else result["birth"]
        result["annotations"] = self.annotation_values.get(identity, {})
        children = self._children(identity)
        children = children[np.argsort(self.data["birth"][children], kind="stable")][:200]
        result["children"] = [self._person(int(pid)) for pid in children]
        unions = self.union_table.data
        indices = np.union1d(
            self._lookup("male", unions["male"], identity),
            self._lookup("female", unions["female"], identity),
        )
        result["unions"] = []
        for index in indices:
            row = {field: int(unions[field][index]) for field in unions.dtype.names}
            row["end"] = None if row["end"] == null_sentinel("death") else row["end"]
            row["reason"] = REASON_NAMES.get(row["reason"])
            result["unions"].append(row)
        moves = self.move_table.data
        result["migrations"] = [
            {
                "id": int(i) + 1,
                **{
                    field: REASON_NAMES[int(moves[field][i])]
                    if field == "reason"
                    else int(moves[field][i])
                    for field in moves.dtype.names
                },
            }
            for i in self._lookup("moves", moves["person"], identity)
        ]
        return result

    def lineage(self, identity, depth=4, direction="ancestors", limit=1000):
        if not 0 <= depth <= 12 or not 1 <= limit <= 5000:
            raise ValueError("depth must be 0..12 and limit 1..5000")
        if direction not in {"ancestors", "descendants"}:
            raise ValueError("Unknown lineage direction")
        self._person(identity)
        seen, frontier, rows = {identity}, [identity], []
        for generation in range(1, depth + 1):
            upcoming = []
            for pid in frontier:
                candidates = sorted({int(self.data[k][pid]) for k in ("father", "mother")})
                if direction == "descendants":
                    candidates = self._children(pid)
                for candidate in candidates:
                    if candidate < 0 or candidate in seen:
                        continue
                    if len(rows) >= limit:
                        return {"people": rows, "truncated": True}
                    seen.add(candidate)
                    upcoming.append(candidate)
                    rows.append({**self._person(candidate), "generation": generation})
            frontier = upcoming
        return {"people": rows, "truncated": False}

    def residence(self, identity, year):
        person = self._person(identity)
        boundary = self.start_year if person["father"] is None else person["birth"]
        if (
            year < boundary
            or year < person["birth"]
            or (person["death"] is not None and year >= person["death"])
        ):
            return None
        place = person["birth_place"]
        moves = self.move_table.data
        indices = self._lookup("moves", moves["person"], identity)
        end = np.searchsorted(moves["year"][indices], year, side="right")
        if end:
            place = int(moves["destination"][indices[end - 1]])
        return place

    def residents(self, settlement, limit=100, after=-1):
        if not 1 <= limit <= 500:
            raise ValueError("limit must be 1..500")
        a, b = self.resident_ranges.get(settlement, (0, 0))
        ids = self.resident_ids[a:b]
        start = np.searchsorted(ids, after, side="right")
        ids = ids[start : start + limit]
        return [self._person(int(pid)) for pid in ids]

    def map_at(self, year, race=None):
        if year not in self.saved_years:
            raise ValueError("No stored census at this year; choose an available snapshot")
        counts = dict(self.maps[year][:, 1:3])
        if race is not None:
            rows = self.racial_maps[year]
            counts = dict(rows[rows[:, 2] == race][:, [1, 3]])
        owners, _, _ = self.politics.at(year)
        return [
            {"settlement": p.id, "population": int(counts.get(p.id, 0)), "nation": int(owners[i])}
            for i, p in enumerate(self.settlements)
        ]

    def distributions(self, year, groups=None, racial_places=None):
        if groups is not None:
            return self._store_distributions(year, groups, racial_places)
        if year not in self.saved_years:
            raise ValueError("No stored census at this year")
        return {
            "available": True,
            "groups": {
                kind: [
                    {"kind": kind, "category": i, "population": int(value)}
                    for i, value in enumerate(values)
                    if value
                ]
                for kind, values in self.groups[year].items()
            },
            "flows": self.flows[year],
        }
