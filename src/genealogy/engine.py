"""Annual spatial life histories with dense IDs and bounded partner search.

Census is at year end. Births precede mortality, including birth-year infant
deaths. Founder history before the initial census is explicitly unknown.
"""

from __future__ import annotations

import json
import math
import time
from collections import defaultdict
from itertools import pairwise
from pathlib import Path
from zlib import crc32

import numpy as np

from .config import Demography, Scenario, Society, virtual_map
from .schema import DTYPE, NO_YEAR
from .store import Store


def mortality_table(demo: Demography):
    ages = np.arange(demo.max_age + 1)
    rates = demo.adult_mortality + demo.aging_coefficient * np.exp(
        np.minimum(demo.aging_exponent * ages, 700)
    )
    rates[ages <= demo.child_max_age] = demo.child_mortality
    rates[0] = demo.infant_mortality
    rates[-1] = 1
    return np.clip(rates, 0, 1)


def scaled_probability(probability, factor):
    """Multiply cumulative hazard: 1 - (1 - q)**factor, including q=1/factor=0."""
    return 1 - np.power(1 - np.clip(probability, 0, 1), factor)


class DependentIndex:
    """Sorted guardian/child arrays without a Python object per living minor."""

    def __init__(self, children, guardians):
        order = np.argsort(guardians, kind="stable")
        self.children, self.guardians = children[order], guardians[order]

    def get(self, parent, default=()):
        start = np.searchsorted(self.guardians, parent, side="left")
        end = np.searchsorted(self.guardians, parent, side="right")
        return self.children[start:end] if end > start else default

    def __getitem__(self, parent):
        return self.get(parent)


class Engine:
    def __init__(self, config: Scenario, store: Store | None = None, rules=()):
        self.config, self.store = config, store
        self.rules = tuple(rules)
        self.society = config.society
        self.rng = np.random.default_rng(config.seed)
        self.settlements = virtual_map(config)
        self.place_ids = np.array([p.id for p in self.settlements], dtype=np.int32)
        self.place_index = {p.id: i for i, p in enumerate(self.settlements)}
        self.sorted_slots = np.argsort(self.place_ids)
        self.sorted_places = self.place_ids[self.sorted_slots]
        self.activities = sorted({a for p in self.settlements for a in p.activities})
        self.race_index = {race.name: i for i, race in enumerate(config.races)}
        self.crossbreeding = {
            tuple(sorted(self.race_index[name] for name in rule.parents)): rule
            for rule in config.crossbreeding
        }
        self.race_matches = {}
        for first in range(len(config.races)):
            matches = []
            for second in range(len(config.races)):
                rule = self.crossbreeding.get(tuple(sorted((first, second))))
                affinity = rule.marriage_affinity if rule else float(first == second)
                if affinity > 0:
                    matches.append((second, affinity))
            self.race_matches[first] = matches
        if len(self.activities) > 32767:
            raise ValueError("Too many activity types for int16 storage")
        self.activity_index = {a: i for i, a in enumerate(self.activities)}
        self.activity_options = {}
        self.activity_sets = {}
        for place in self.settlements:
            weights = np.array(list(place.activities.values()), dtype=float)
            self.activity_options[place.id] = (
                np.array([self.activity_index[a] for a in place.activities], dtype=np.int16),
                weights / weights.sum(),
            )
            self.activity_sets[place.id] = set(map(int, self.activity_options[place.id][0]))
        self.neighbors = self._neighbors()
        self.data = np.zeros(max(4096, config.initial_population * 2), dtype=DTYPE)
        self.n = 0
        self.next_union = 0
        self.year = config.start_year
        self.demography = config.demography
        self._apply_periods()
        self.rows = []
        self.moves, self.new_unions, self.closed_unions = [], [], []
        self.kin_checks = self.kin_rejections = 0
        self._initialize()

    def _random_stream(self, process):
        # Isolated draws per process/year; configuration changes do not shift another stream.
        codes = {"births": 1, "deaths": 2, "divorces": 3, "marriages": 4, "migrations": 5}
        self.rng = np.random.default_rng(
            [self.config.seed, self.year - self.config.start_year, codes[process]]
        )

    def stream(self, name, process="custom"):
        if getattr(self, "_stream_year", None) != self.year:
            self._stream_year, self._rule_streams = self.year, {}
        key = name, process
        if key not in self._rule_streams:
            self._rule_streams[key] = np.random.default_rng(
                [
                    self.config.seed,
                    self.year - self.config.start_year,
                    crc32(name.encode("utf-8")),
                    crc32(process.encode("utf-8")),
                ]
            )
        return self._rule_streams[key]

    def _neighbors(self):
        """Radius graph using spatial buckets; never allocate an S x S matrix."""
        society = self.society
        radius = max(
            society.marriage_radius,
            society.migration_radius,
            *(
                value
                for period in self.config.periods
                for value in (
                    period.society.marriage_radius or 0,
                    period.society.migration_radius or 0,
                )
            ),
        )
        buckets = defaultdict(list)
        for place in self.settlements:
            buckets[math.floor(place.x / radius), math.floor(place.y / radius)].append(place)
        graph = {}
        for origin in self.settlements:
            cell = math.floor(origin.x / radius), math.floor(origin.y / radius)
            candidates = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dest in buckets.get((cell[0] + dx, cell[1] + dy), []):
                        if dest.id == origin.id:
                            continue
                        distance = math.hypot(dest.x - origin.x, dest.y - origin.y)
                        if distance <= radius:
                            candidates.append((distance, dest.id))
            candidates.sort()
            max_neighbors = max(
                [
                    society.max_neighbors,
                    *(p.society.max_neighbors or 0 for p in self.config.periods),
                ]
            )
            marriage_radius = max(
                [
                    society.marriage_radius,
                    *(p.society.marriage_radius or 0 for p in self.config.periods),
                ]
            )
            migration_radius = max(
                [
                    society.migration_radius,
                    *(p.society.migration_radius or 0 for p in self.config.periods),
                ]
            )
            # Bound stored edges even with thousands of settlements at identical coordinates.
            nearby_marriage = [pair for pair in candidates if pair[0] <= marriage_radius][
                :max_neighbors
            ]
            nearby_migration = [pair for pair in candidates if pair[0] <= migration_radius][
                :max_neighbors
            ]
            graph[origin.id] = sorted(set(nearby_marriage + nearby_migration))
        return graph

    def _allocate(self, count):
        if self.n + count >= 2**31:
            raise OverflowError("Dense IDs exceed int32; use a partitioned/int64 backend")
        if self.n + count > len(self.data):
            enlarged = np.zeros(max(self.n + count, len(self.data) * 2), dtype=DTYPE)
            enlarged[: self.n] = self.data[: self.n]
            self.data = enlarged
        ids = np.arange(self.n, self.n + count, dtype=np.int32)
        self.n += count
        for field in ("death", "father", "mother", "death_place", "partner", "union"):
            self.data[field][ids] = -1
        self.data["death"][ids] = NO_YEAR
        self.data["last_birth"][ids] = self.config.start_year - 1000
        self.data["eligible_year"][ids] = self.config.start_year
        return ids

    def _activity(self, ids, places, inherited=None):
        if not len(ids):
            return
        order = np.argsort(places, kind="stable")
        sorted_places = places[order]
        boundaries = np.concatenate(([0], np.flatnonzero(np.diff(sorted_places)) + 1, [len(ids)]))
        compatible = np.zeros(len(ids), bool)
        for start, end in pairwise(boundaries):
            positions = order[start:end]
            selection = ids[positions]
            options, weights = self.activity_options[int(sorted_places[start])]
            self.data["activity"][selection] = self.rng.choice(options, len(selection), p=weights)
            if inherited is not None:
                compatible[positions] = np.isin(inherited[positions], options)
        if inherited is not None:
            keep = self.rng.random(len(ids)) < self.society.activity_inheritance
            self.data["activity"][ids[keep & compatible]] = inherited[keep & compatible]

    def _initialize(self):
        ids = self._allocate(self.config.initial_population)
        demo = self.demography
        weights = np.array([p.initial_weight for p in self.settlements])
        places = self.rng.choice(self.place_ids, len(ids), p=weights / weights.sum())
        self.data["place"][ids] = self.data["birth_place"][ids] = places
        self.data["place_slot"][ids] = self.sorted_slots[
            np.searchsorted(self.sorted_places, places)
        ]
        race_weights = np.array([r.initial_weight for r in self.config.races])
        self.data["race"][ids] = self.rng.choice(
            len(race_weights), len(ids), p=race_weights / race_weights.sum()
        )
        order = np.argsort(places, kind="stable")
        grouped_places = places[order]
        boundaries = np.concatenate(([0], np.flatnonzero(np.diff(grouped_places)) + 1, [len(ids)]))
        for start, end in pairwise(boundaries):
            place = self.settlements[self.place_index[int(grouped_places[start])]]
            if place.races:
                selection = ids[order[start:end]]
                options = [self.race_index[name] for name in place.races]
                weights = np.array(list(place.races.values()))
                self.data["race"][selection] = self.rng.choice(
                    options, len(selection), p=weights / weights.sum()
                )
        for race, demo in enumerate(self.race_demography):
            selection = ids[self.data["race"][ids] == race]
            if not len(selection):
                continue
            # Stationary survivorship distribution; ancestry before the boundary unknown.
            survival = np.concatenate(([1.0], np.cumprod(1 - mortality_table(demo)[:-1])))
            survival[0] *= 1 - demo.infant_mortality
            survival[-1] = 0  # maximum-age individuals cannot be alive at the initial census
            if survival.sum() == 0:
                raise ValueError("No founder survivors under configured infant mortality")
            ages = self.rng.choice(
                np.arange(len(survival)), len(selection), p=survival / survival.sum()
            )
            self.data["birth"][selection] = self.year - ages
            self.data["sex"][selection] = (
                self.rng.random(len(selection)) >= demo.male_birth_probability
            )
        self.data["family"][ids] = ids
        status = np.array(self.society.status_weights)
        self.data["status"][ids] = self.rng.choice(len(status), len(ids), p=status / status.sum())
        self._activity(ids, places)
        self.alive = ids
        # Initial adult partnerships, explicitly dated at the simulation boundary.
        self._apply_periods()
        marriages, local = self._marriages(initial=True)
        partnered = ids[(self.data["sex"][ids] == 1) & (self.data["partner"][ids] >= 0)]
        spacing = self.race_birth_spacing[self.data["race"][partnered]]
        self.data["last_birth"][partnered] = self.year - self.rng.integers(0, spacing + 1)
        migrations = len(self.moves)
        self._flush_history()
        self._census(0, 0, marriages, 0, migrations, 0, local)

    def ancestors(self, identity, depth=None):
        seen, frontier = {int(identity)}, [int(identity)]
        for _ in range(depth or self.society.kinship_depth):
            upcoming = []
            for pid in frontier:
                for field in ("father", "mother"):
                    parent = int(self.data[field][pid])
                    if parent >= 0 and parent not in seen:
                        seen.add(parent)
                        upcoming.append(parent)
            frontier = upcoming
            if not frontier:
                break
        return seen

    def related(self, first, second):
        self.kin_checks += 1
        answer = bool(self.ancestors(first) & self.ancestors(second))
        self.kin_rejections += answer
        return answer

    def _move(self, ids, destination, reason):
        ids = np.asarray(ids, dtype=np.int32)
        ids = ids[self.data["place"][ids] != destination]
        for pid in ids:
            self.moves.append(
                (int(pid), self.year, int(self.data["place"][pid]), int(destination), reason)
            )
        if len(ids):
            old = self.data["activity"][ids].copy()
            self.data["place"][ids] = destination
            self.data["place_slot"][ids] = self.place_index[destination]
            # Preserve a supported occupation on moving; only retrain incompatible members.
            unsupported = np.array([int(a) not in self.activity_sets[destination] for a in old])
            options, weights = self.activity_options[destination]
            self.data["activity"][ids[unsupported]] = self.rng.choice(
                options, int(unsupported.sum()), p=weights
            )

    def _dependents(self):
        """Vectorized maternal custody, then co-resident father; orphans stay put."""
        d, ids = self.data, self.alive
        age = self.year - d["birth"][ids]
        children = ids[(age < self.race_dependent_age[d["race"][ids]]) & (d["partner"][ids] < 0)]
        guardians = np.full(len(children), -1, dtype=np.int32)
        for field in ("mother", "father"):
            parent = d[field][children]
            safe = np.maximum(parent, 0)
            valid = (
                (parent >= 0)
                & (guardians < 0)
                & (d["death"][safe] == NO_YEAR)
                & (d["place"][safe] == d["place"][children])
            )
            guardians[valid] = parent[valid]
        valid = guardians >= 0
        return DependentIndex(children[valid], guardians[valid])

    def _household(self, adults, dependents):
        members = set(map(int, adults))
        for adult in adults:
            origin = self.data["place"][adult]
            for child in dependents.get(int(adult), []):
                if self.data["place"][child] == origin:
                    members.add(child)
        return sorted(members)

    def _marriages(self, initial=False):
        society, d = self.society, self.data
        age = self.year - d["birth"][self.alive]
        races = d["race"][self.alive]
        eligible = self.alive[
            (d["partner"][self.alive] < 0)
            & (age >= self.race_marriage_min[races])
            & (age <= self.race_marriage_max[races])
            & (d["eligible_year"][self.alive] <= self.year)
        ]
        # Founder unions need a higher prevalence than one year's formation hazard.
        eligible = eligible[
            self.rng.random(len(eligible))
            < (society.founder_match_participation if initial else society.marriage_rate)
        ]
        men = defaultdict(list)
        for pid in eligible[d["sex"][eligible] == 0]:
            men[int(d["place"][pid]), int(d["race"][pid])].append(int(pid))
        women = eligible[d["sex"][eligible] == 1].copy()
        self.rng.shuffle(women)
        dependents = self._dependents()
        count, local = 0, 0
        for female in women:
            origin = int(d["place"][female])
            locations = [(0.0, origin)] + [
                (dist, place)
                for dist, place in self.neighbors[origin]
                if dist <= society.marriage_radius
            ][: society.max_neighbors]
            compatible = self.race_matches[int(d["race"][female])]
            candidates = [
                (dist, p, race, affinity)
                for dist, p in locations
                for race, affinity in compatible
                if men[p, race]
            ]
            if not candidates:
                continue
            weights = np.array(
                [
                    math.exp(-dist / society.distance_scale)
                    * (society.local_marriage_weight if p == origin else 1)
                    * len(men[p, race]) ** 0.5
                    * affinity
                    for dist, p, race, affinity in candidates
                ]
            )
            weights /= weights.sum()
            for _ in range(society.matching_attempts):
                _, place, race, _ = candidates[int(self.rng.choice(len(candidates), p=weights))]
                pool = men[place, race]
                index = int(self.rng.integers(len(pool)))
                male = pool[index]
                max_gap = max(
                    self.race_age_gap[d["race"][male]], self.race_age_gap[d["race"][female]]
                )
                rule = self.crossbreeding.get(tuple(sorted((race, int(d["race"][female])))))
                if rule and rule.max_age_gap is not None:
                    max_gap = rule.max_age_gap
                if abs(int(d["birth"][male]) - int(d["birth"][female])) > max_gap:
                    continue
                gap = abs(int(d["status"][male]) - int(d["status"][female]))
                if self.rng.random() > (1 - society.status_affinity) ** gap:
                    continue
                if self.related(male, female):
                    continue
                pool[index] = pool[-1]
                pool.pop()
                d["partner"][male], d["partner"][female] = female, male
                d["union"][[male, female]] = self.next_union
                local += place == origin
                residence = place if society.residence == "patrilocal" else origin
                if society.residence == "either":
                    residence = place if self.rng.random() < 0.5 else origin
                self.new_unions.append((self.next_union, male, int(female), self.year, residence))
                self.next_union += 1
                self._move(self._household([male, int(female)], dependents), residence, "marriage")
                count += 1
                break
        return count, local

    def _end_union(self, identities, reason):
        d = self.data
        active = identities[d["union"][identities] >= 0]
        union_ids, positions = np.unique(d["union"][active], return_index=True)
        for union, pid in zip(union_ids, active[positions], strict=True):
            partner = int(d["partner"][pid])
            pair = [int(pid), partner]
            self.closed_unions.append((self.year, reason, int(union)))
            d["partner"][pair] = d["union"][pair] = -1
            d["eligible_year"][pair] = self.year + self.society.remarriage_delay
        return len(union_ids)

    def _events(self, ids, process="diagnostic"):
        """Composable yearly hazards; local effects and age/sex targeting."""
        size = len(ids)
        mortality, extra, fertility, migration = (
            np.ones(size),
            np.zeros(size),
            np.ones(size),
            np.ones(size),
        )
        capacity = np.ones(len(self.settlements))
        ages = self.year - self.data["birth"][ids]
        for event in self.config.events:
            if not event.start_year <= self.year <= event.end_year:
                continue
            location = (
                np.isin(self.data["place"][ids], event.settlements)
                if event.settlements
                else np.ones(size, bool)
            )
            mask = location & (ages >= event.min_age) & (ages <= event.max_age)
            if event.sex != "all":
                mask &= self.data["sex"][ids] == (event.sex == "female")
            if event.races:
                mask &= np.isin(
                    self.data["race"][ids], [self.race_index[name] for name in event.races]
                )
            mortality[mask] *= event.mortality_factor
            extra[mask] = 1 - (1 - extra[mask]) * (1 - event.extra_mortality)
            fertility[mask] *= event.fertility_factor
            migration[mask] *= event.migration_factor
            places = (
                [self.place_index[p] for p in event.settlements]
                if event.settlements
                else list(range(len(capacity)))
            )
            capacity[places] *= event.capacity_factor
        hazards = {
            "mortality": mortality,
            "extra_mortality": extra,
            "fertility": fertility,
            "migration": migration,
            "capacity": capacity,
        }
        for rule in self.rules:
            rule.apply(self, process, ids, hazards)
        return (
            hazards["mortality"],
            hazards["extra_mortality"],
            hazards["fertility"],
            hazards["migration"],
            hazards["capacity"],
        )

    def _births(self):
        d = self.data
        ids = self.alive
        ages = self.year - d["birth"][ids]
        races = d["race"][ids]
        fertile = ids[
            (d["sex"][ids] == 1)
            & (d["partner"][ids] >= 0)
            & (ages >= self.race_fertility_min[races])
            & (ages <= self.race_fertility_max[races])
            & (self.year - d["last_birth"][ids] >= self.race_birth_spacing[races])
        ]
        ages = self.year - d["birth"][fertile]
        _, _, factor, _, capacity_factor = self._events(fertile, "births")
        counts = np.bincount(d["place_slot"][ids], minlength=len(self.settlements))
        capacity = np.array([p.capacity for p in self.settlements], dtype=float)
        capacity *= (1 + self.society.capacity_growth) ** (self.year - self.config.start_year)
        capacity *= capacity_factor
        pressure = np.minimum(1, capacity / np.maximum(counts, 1))
        local_pressure = pressure[d["place_slot"][fertile]]
        races = d["race"][fertile]
        probability = self.race_fertility_peak[races] * np.exp(
            -0.5
            * ((ages - self.race_fertility_peak_age[races]) / self.race_fertility_width[races]) ** 2
        )
        pair_codes = np.sort(np.column_stack((races, d["race"][d["partner"][fertile]])), axis=1)
        for pair, crossing in self.crossbreeding.items():
            mask = (pair_codes[:, 0] == pair[0]) & (pair_codes[:, 1] == pair[1])
            factor[mask] *= crossing.fertility_factor
        mothers = fertile[
            self.rng.random(len(fertile)) < scaled_probability(probability, factor * local_pressure)
        ]
        fathers = d["partner"][mothers].copy()
        babies = self._allocate(len(mothers))
        d = self.data  # allocation may have grown the array
        d["mother"][babies], d["father"][babies] = mothers, fathers
        d["birth"][babies] = self.year
        d["race"][babies] = d["race"][mothers]
        parent_pairs = np.sort(np.column_stack((d["race"][mothers], d["race"][fathers])), axis=1)
        for pair, crossing in self.crossbreeding.items():
            mask = (parent_pairs[:, 0] == pair[0]) & (parent_pairs[:, 1] == pair[1])
            options = [self.race_index[name] for name in crossing.offspring]
            weights = np.array(list(crossing.offspring.values()))
            d["race"][babies[mask]] = self.rng.choice(
                options, int(mask.sum()), p=weights / weights.sum()
            )
        d["sex"][babies] = (
            self.rng.random(len(babies)) >= self.race_male_probability[d["race"][babies]]
        )
        d["place"][babies] = d["birth_place"][babies] = d["place"][mothers]
        d["place_slot"][babies] = d["place_slot"][mothers]
        d["family"][babies] = d["family"][fathers]
        d["status"][babies] = d["status"][fathers]
        change = self.rng.random(len(babies)) > self.society.status_inheritance
        status_shift = self.rng.choice([-1, 1], len(babies))
        d["status"][babies[change]] = np.clip(
            d["status"][babies[change]].astype(int) + status_shift[change],
            0,
            len(self.society.status_weights) - 1,
        )
        self._activity(babies, d["place"][babies], d["activity"][fathers])
        d["last_birth"][mothers] = self.year
        self.alive = np.concatenate((self.alive, babies))
        maternal = mothers[
            self.rng.random(len(mothers)) < self.race_maternal_mortality[d["race"][mothers]]
        ]
        return len(babies), maternal

    def _deaths(self, maternal):
        d, ids = self.data, self.alive
        ages = self.year - d["birth"][ids]
        races = d["race"][ids]
        rate = self.race_mortality[races, np.minimum(ages, self.race_max_age[races])]
        rate *= np.where(d["sex"][ids] == 0, self.race_male_mortality[races], 1)
        factor, extra, _, _, _ = self._events(ids, "deaths")
        rate = 1 - (1 - scaled_probability(rate, factor)) * (1 - extra)
        rate[ages >= self.race_max_age[races]] = 1
        dead = np.union1d(ids[self.rng.random(len(ids)) < rate], maternal).astype(np.int32)
        infants = int(np.sum(self.year - d["birth"][dead] == 0))
        d["death"][dead] = self.year
        d["death_place"][dead] = d["place"][dead]
        self._end_union(dead, "death")
        self.alive = ids[d["death"][ids] == NO_YEAR]
        return len(dead), infants

    def _migrations(self):
        d, society, ids = self.data, self.society, self.alive
        # One decision per couple or single adult, never a second independent spouse roll.
        heads = ids[
            (
                (d["partner"][ids] < 0)
                & (self.year - d["birth"][ids] >= self.race_dependent_age[d["race"][ids]])
            )
            | ((d["partner"][ids] >= 0) & (ids < d["partner"][ids]))
        ]
        _, _, _, factor, capacity_factor = self._events(heads, "migrations")
        paired = d["partner"][heads] >= 0
        if np.any(paired):
            _, _, _, partner_factor, _ = self._events(d["partner"][heads[paired]], "migrations")
            factor[paired] = np.maximum(factor[paired], partner_factor)
        heads = heads[self.rng.random(len(heads)) < np.clip(society.migration_rate * factor, 0, 1)]
        dependents = self._dependents()
        counts = np.bincount(d["place_slot"][ids], minlength=len(self.settlements))
        attraction = (
            np.array([p.capacity for p in self.settlements]) * capacity_factor / (counts + 1)
        )
        for head in heads:
            origin = int(d["place"][head])
            candidates = [
                (distance, p)
                for distance, p in self.neighbors[origin]
                if distance <= society.migration_radius
            ][: society.max_neighbors]
            if not candidates:
                continue
            weights = np.array(
                [
                    math.exp(-dist / society.distance_scale) * attraction[self.place_index[p]]
                    for dist, p in candidates
                ]
            )
            destination = candidates[
                int(self.rng.choice(len(candidates), p=weights / weights.sum()))
            ][1]
            adults = [int(head)]
            if d["partner"][head] >= 0:
                adults.append(int(d["partner"][head]))
            members = self._household(adults, dependents)
            for member in members:
                counts[self.place_index[int(d["place"][member])]] -= 1
                counts[self.place_index[destination]] += 1
            self._move(members, destination, "household")

    def _flush_history(self):
        if self.store:
            self.store.unions(self.new_unions)
            self.store.close_unions(self.closed_unions)
            self.store.migrations(self.moves)
        self.new_unions, self.closed_unions, self.moves = [], [], []

    def _census(self, births, deaths, marriages, divorces, migrations, infants, local):
        d, ids = self.data, self.alive
        ages = self.year - d["birth"][ids]
        races = d["race"][ids]
        fertile = (
            (d["sex"][ids] == 1)
            & (ages >= self.race_fertility_min[races])
            & (ages <= self.race_fertility_max[races])
        )
        row = (
            self.year,
            len(ids),
            births,
            deaths,
            marriages,
            divorces,
            migrations,
            infants,
            int(np.sum(ages < 15)),
            int(np.sum((ages >= 15) & (ages < 50))),
            int(np.sum(ages >= 50)),
            int(np.sum(fertile)),
            int(np.sum(fertile & (d["partner"][ids] >= 0))),
            local,
        )
        self.rows.append(row)
        if self.store:
            places, counts = np.unique(d["place"][ids], return_counts=True)
            lookup = dict(zip(map(int, places), map(int, counts), strict=True))
            self.store.census(
                row, [(self.year, p.id, lookup.get(p.id, 0)) for p in self.settlements]
            )

    def _apply_periods(self):
        key = tuple(p.start_year for p in self.config.periods if p.start_year <= self.year)
        if getattr(self, "_period_key", None) == key:
            return
        self._period_key = key
        demo, society = self.config.demography, self.config.society
        for period in sorted(self.config.periods, key=lambda p: p.start_year):
            if period.start_year <= self.year:
                demo = Demography.model_validate(
                    {**demo.model_dump(), **period.demography.model_dump(exclude_none=True)}
                )
                society = Society.model_validate(
                    {**society.model_dump(), **period.society.model_dump(exclude_none=True)}
                )
        self.demography, self.society = demo, society
        self.race_demography = [
            Demography.model_validate(
                {
                    **demo.model_dump(),
                    **race.demography.model_dump(exclude_none=True),
                }
            )
            for race in self.config.races
        ]
        for field in (
            "max_age",
            "fertility_min_age",
            "fertility_max_age",
            "fertility_peak",
            "fertility_peak_age",
            "fertility_width",
            "birth_spacing",
            "maternal_mortality",
        ):
            attribute = (
                field.replace("_min_age", "_min").replace("_max_age", "_max")
                if field.startswith("fertility_")
                else field
            )
            setattr(
                self,
                "race_" + attribute,
                np.array([getattr(d, field) for d in self.race_demography]),
            )
        self.race_mortality = np.zeros(
            (len(self.race_demography), max(d.max_age for d in self.race_demography) + 1)
        )
        for race, racial_demo in enumerate(self.race_demography):
            self.race_mortality[race, : racial_demo.max_age + 1] = mortality_table(racial_demo)
        self.race_male_mortality = np.array([d.male_mortality_factor for d in self.race_demography])
        self.race_male_probability = np.array(
            [d.male_birth_probability for d in self.race_demography]
        )
        self.race_marriage_min = np.array(
            [race.marriage_min_age or society.marriage_min_age for race in self.config.races]
        )
        self.race_marriage_max = np.array(
            [race.marriage_max_age or society.marriage_max_age for race in self.config.races]
        )
        self.race_dependent_age = np.array(
            [race.dependent_age or society.dependent_age for race in self.config.races]
        )
        self.race_age_gap = np.array(
            [
                race.max_age_gap if race.max_age_gap is not None else society.max_age_gap
                for race in self.config.races
            ]
        )

    def run(self, progress=None):
        for year in range(
            self.config.start_year + 1, self.config.start_year + self.config.duration + 1
        ):
            self.year = year
            self._apply_periods()
            self._random_stream("births")
            births, maternal = self._births()
            self._random_stream("deaths")
            deaths, infants = self._deaths(maternal)
            ids = self.alive[self.data["union"][self.alive] >= 0]
            ids = ids[ids < self.data["partner"][ids]]
            self._random_stream("divorces")
            divorces = self._end_union(
                ids[self.rng.random(len(ids)) < self.society.divorce_rate], "divorce"
            )
            self._random_stream("marriages")
            marriages, local = self._marriages()
            self._random_stream("migrations")
            self._migrations()
            migrations = len(self.moves)
            self._flush_history()
            self._census(births, deaths, marriages, divorces, migrations, infants, local)
            if progress:
                progress(self.year, len(self.alive))
        return self.summary()

    def summary(self):
        births = sum(row[2] for row in self.rows)
        dead = self.data["death"][: self.n] != NO_YEAR
        ages = self.data["death"][: self.n][dead] - self.data["birth"][: self.n][dead]
        marriages = sum(row[4] for row in self.rows)
        return {
            "start_year": self.config.start_year,
            "end_year": self.year,
            "initial_population": self.config.initial_population,
            "population": len(self.alive),
            "people_ever": self.n,
            "births": births,
            "deaths": int(dead.sum()),
            "marriages": marriages,
            "divorces": sum(row[5] for row in self.rows),
            "migrations": sum(row[6] for row in self.rows),
            "birth_year_mortality": sum(row[7] for row in self.rows) / max(births, 1),
            "mean_observed_age_at_death": float(ages.mean()) if len(ages) else None,
            "local_marriage_fraction": sum(row[13] for row in self.rows) / max(marriages, 1),
            "kinship_checks": self.kin_checks,
            "kinship_rejections": self.kin_rejections,
            "person_bytes": DTYPE.itemsize,
            "allocated_person_bytes": self.data.nbytes,
            "target_population": self.config.target_population,
            "target_status": (
                "within_tolerance"
                if abs(len(self.alive) / self.config.target_population - 1)
                <= self.config.target_tolerance
                else "outside_tolerance"
            )
            if self.config.target_population
            else "not_requested",
            "target_relative_error": (len(self.alive) / self.config.target_population - 1)
            if self.config.target_population
            else None,
            "founder_ancestry": "unknown before simulation boundary",
            "population_by_race": {
                race.name: int(np.sum(self.data["race"][self.alive] == i))
                for i, race in enumerate(self.config.races)
            },
        }


def generate(config: Scenario, path: Path, progress=None, rules=(), calibration_progress=None):
    """Publish only a complete archive; never overwrite an existing generation."""
    rules = tuple(rules)
    descriptors = [
        getattr(
            rule,
            "descriptor",
            {
                "type": f"{type(rule).__module__}.{type(rule).__qualname__}",
                "parameters": "not supplied",
            },
        )
        for rule in rules
    ]
    json.dumps(descriptors)  # reject unserializable provenance before an expensive run
    path = path.resolve()
    if path.exists():
        raise FileExistsError(f"Choose a new output path: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = path.with_suffix(path.suffix + ".partial")
    if staging.exists():
        raise FileExistsError(f"Previous incomplete run exists: {staging}")
    started = time.perf_counter()
    calibration = None
    if config.target_population:
        pilot = config.model_copy(
            update={"initial_population": config.calibration_population, "target_population": None}
        )
        pilot_engine = Engine(pilot, rules=rules)
        pilot_summary = pilot_engine.run(calibration_progress)
        ratio = pilot_summary["population"] / pilot.initial_population
        if ratio < 0.05:
            raise ValueError(
                "Pilot population collapsed; revise demography/events before targeting"
            )
        initial = max(2, round(config.target_population / ratio))
        if initial > 100_000_000:
            raise ValueError("Calibrated founding population exceeds 100 million")
        calibration = {
            "pilot_initial": pilot.initial_population,
            "pilot_final": pilot_summary["population"],
            "growth_ratio": ratio,
            "estimated_initial": initial,
        }
        config = config.model_copy(update={"initial_population": initial})
        del pilot_engine
    settlements = virtual_map(config)
    activities = sorted({a for p in settlements for a in p.activities})
    store = Store(staging, config, settlements, activities)
    try:
        engine = Engine(config, store, rules=rules)
        summary = engine.run(progress)
        summary["calibration"] = calibration
        summary["rules"] = descriptors
        summary["simulation_seconds"] = time.perf_counter() - started
        store.finish(engine.data[: engine.n], summary)
        summary["archive_bytes"] = staging.stat().st_size
        summary["total_seconds"] = time.perf_counter() - started
        store.update_summary(summary)
        if summary["archive_bytes"] != staging.stat().st_size:
            summary["archive_bytes"] = staging.stat().st_size
            store.update_summary(summary)
    finally:
        store.close()
    # Atomic no-clobber publication on Windows; existing path was checked above.
    staging.rename(path)
    summary["archive_bytes"] = path.stat().st_size
    summary["total_seconds"] = time.perf_counter() - started
    return summary
