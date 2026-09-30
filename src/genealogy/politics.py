"""Dated sovereignty and contact graphs, independent of ancestry and residence."""

from __future__ import annotations

from threading import RLock

import numpy as np

from .config import Scenario, Settlement


class PoliticalTimeline:
    def __init__(self, config: Scenario, settlements: list[Settlement]):
        self.config, self.settlements = config, settlements
        self.index = {n.name: i for i, n in enumerate(config.nations)}
        self.slots = {p.id: i for i, p in enumerate(settlements)}
        self.coordinates = np.array([(p.x, p.y) for p in settlements])
        rng = np.random.default_rng(config.seed ^ 0xC017AC7)
        canonical = sorted(range(len(settlements)), key=lambda i: settlements[i].id)
        automatic = np.asarray(canonical)[rng.permutation(len(settlements))]
        self.capitals = [
            self.slots[n.capital] if n.capital is not None else int(automatic[i % len(automatic)])
            for i, n in enumerate(config.nations)
        ]
        dates = {config.start_year}
        for n in config.nations:
            dates.add(n.founded)
            if n.dissolved is not None:
                dates.add(n.dissolved)
        for item in [*config.territories, *config.nation_contacts]:
            dates.add(item.start_year)
            if item.end_year is not None:
                dates.add(item.end_year)
        self.dates = sorted(dates)
        self.key = None
        self.lock = RLock()

    def at(self, year: int):
        with self.lock:
            return self._at(year)

    def _at(self, year: int):
        key = int(np.searchsorted(self.dates, year, side="right"))
        if key == self.key:
            return self.owners, self.marriage, self.migration
        self.key = key
        count = len(self.config.nations)
        owners = np.full(len(self.settlements), -1, np.int32)
        active = [
            i
            for i, n in enumerate(self.config.nations)
            if n.founded <= year and (n.dissolved is None or year < n.dissolved)
        ]
        # Without explicit territorial claims, political areas follow nearest active capitals.
        if active and self.config.territory_mode == "nearest_capital":
            centers = self.coordinates[[self.capitals[i] for i in active]]
            distances = ((self.coordinates[:, None] - centers) ** 2).sum(axis=2)
            owners[:] = np.asarray(active)[np.argmin(distances, axis=1)]
        for claim in self.config.territories:
            if claim.start_year <= year and (claim.end_year is None or year < claim.end_year):
                owners[[self.slots[pid] for pid in claim.settlements]] = self.index[claim.nation]
        # The last index represents unclaimed territory, with normal spatial contact.
        marriage = np.full((count + 1, count + 1), self.config.foreign_marriage_factor, dtype=float)
        migration = np.full(
            (count + 1, count + 1), self.config.foreign_migration_factor, dtype=float
        )
        for matrix in (marriage, migration):
            np.fill_diagonal(matrix, 1)
            matrix[-1, :] = matrix[:, -1] = 1
        for contact in self.config.nation_contacts:
            if contact.start_year <= year and (contact.end_year is None or year < contact.end_year):
                a, b = (self.index[name] for name in contact.nations)
                marriage[a, b] = marriage[b, a] = contact.marriage_factor
                migration[a, b] = migration[b, a] = contact.migration_factor
        self.owners, self.marriage, self.migration = owners, marriage, migration
        return owners, marriage, migration

    def factor(self, origin: int, destination: int, year: int, process: str):
        owners, marriage, migration = self.at(year)
        matrix = marriage if process == "marriages" else migration
        return matrix[owners[self.slots[origin]], owners[self.slots[destination]]]
