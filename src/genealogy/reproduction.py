"""Stable lifetime reproduction states, reconstructed without archive columns.

Two independent hash streams assign biological infertility and a lifetime choice
not to reproduce. Parameters apply at birth (at the start boundary for founders).
They are scenario assumptions, not estimates of clinical prevalence.
"""

from __future__ import annotations

import numpy as np

from .schema import NO_YEAR


class ReproductiveTraits:
    """One runtime byte per person, no extra archived bytes or yearly redraws."""

    def __init__(self, config):
        self.start = config.start_year
        self.keys = np.random.SeedSequence([config.seed, 0x52455052]).generate_state(2)
        demo, society = config.demography.model_dump(), config.society.model_dump()
        self.epochs, self.rates = [], []
        periods = sorted(config.periods, key=lambda p: p.start_year)
        # Merge all pre-boundary periods before assigning the founder population.
        for period in periods:
            if period.start_year <= self.start:
                demo.update(period.demography.model_dump(exclude_none=True))
                society.update(period.society.model_dump(exclude_none=True))
        self._append(self.start, demo, society, config.races)
        for period in periods:
            if period.start_year > self.start:
                demo.update(period.demography.model_dump(exclude_none=True))
                society.update(period.society.model_dump(exclude_none=True))
                self._append(period.start_year, demo, society, config.races)
        self.rates = np.asarray(self.rates)

    def _append(self, year, demo, society, races):
        self.epochs.append(year)
        self.rates.append(
            [
                [
                    values["male_infertility_rate"],
                    values["female_infertility_rate"],
                    society["childfree_rate"],
                ]
                for race in races
                for values in [{**demo, **race.demography.model_dump(exclude_none=True)}]
            ]
        )

    def _uniform(self, ids, channel):
        values = np.asarray(ids, dtype=np.uint32) ^ self.keys[channel]
        values = values ^ (values >> 16)
        values = values * np.uint32(0x7FEB352D)
        values = values ^ (values >> 15)
        values = values * np.uint32(0x846CA68B)
        values = values ^ (values >> 16)
        return values.astype(np.float64) / 2**32

    def flags(self, ids, sexes, races, births):
        epochs = np.searchsorted(self.epochs, np.maximum(births, self.start), side="right") - 1
        rates = self.rates[epochs, races]
        infertility = self._uniform(ids, 0) < rates[np.arange(len(ids)), sexes]
        childfree = self._uniform(ids, 1) < rates[:, 2]
        return infertility.astype(np.uint8) | (childfree.astype(np.uint8) << 1)

    def describe(self, person):
        flags = int(
            self.flags(
                [person["id"]],
                np.array([person["sex"]]),
                [person["race"]],
                [person["birth"]],
            )[0]
        )
        return {"infertile": bool(flags & 1), "childfree": bool(flags & 2)}


def mortality_summary(data, count, founders, end_year):
    """Observed integer-year death ages, with explicit censoring of young cohorts.

    The completed-childhood rate excludes founders (unknown earlier survival)
    and everyone born less than 15 years before the final census. A death-age
    histogram avoids sorting all deceased individuals to calculate the median.
    """
    histogram = np.zeros(2001, dtype=np.int64)
    resolved_count = childhood_count = unresolved_count = 0
    for start in range(0, count, 1_000_000):
        stop = min(count, start + 1_000_000)
        births, deaths = data["birth"][start:stop], data["death"][start:stop]
        dead = deaths != NO_YEAR
        ages = deaths[dead].astype(np.int64) - births[dead]
        observed = np.bincount(ages, minlength=len(histogram))
        if len(observed) > len(histogram):
            histogram = np.pad(histogram, (0, len(observed) - len(histogram)))
        histogram[: len(observed)] += observed
        boundary = max(0, founders - start)
        born_births, born_deaths = births[boundary:], deaths[boundary:]
        completed = end_year - born_births >= 15
        childhood = (born_deaths != NO_YEAR) & (born_deaths.astype(np.int64) - born_births < 15)
        resolved_count += int(completed.sum())
        childhood_count += int((completed & childhood).sum())
        unresolved_count += int((~completed).sum())
    total = int(histogram.sum())
    if total:
        cumulative = histogram.cumsum()
        median = float(
            (
                np.searchsorted(cumulative, (total + 1) // 2)
                + np.searchsorted(cumulative, total // 2 + 1)
            )
            / 2
        )
        mean = float(np.dot(histogram, np.arange(len(histogram))) / total)
    else:
        median = mean = None
    return {
        "observed_deaths": total,
        "mean_age_at_death": mean,
        "median_age_at_death": median,
        "deaths_under_15": int(histogram[:15].sum()),
        "deaths_under_15_fraction": float(histogram[:15].sum() / total) if total else None,
        "death_age_bands": {
            "0": int(histogram[:1].sum()),
            "1–4": int(histogram[1:5].sum()),
            "5–14": int(histogram[5:15].sum()),
            "15–49": int(histogram[15:50].sum()),
            "50+": int(histogram[50:].sum()),
        },
        "completed_childhood_cohort": resolved_count,
        "childhood_deaths_in_completed_cohort": childhood_count,
        "completed_childhood_mortality": (
            childhood_count / resolved_count if resolved_count else None
        ),
        "unresolved_childhood_cohort": unresolved_count,
        "excluded_founders": founders,
        "childhood_cutoff_age": 15,
    }
