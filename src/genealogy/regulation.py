"""One-run population feedback, separate from biological eligibility and life history."""

import numpy as np


class PopulationRegulator:
    def __init__(self, config):
        self.enabled = config.target_mode == "bounded" and config.target_population is not None
        self.floor = config.initial_population
        self.ceiling = config.target_population
        self.buffer = config.regulation_buffer
        self.response_years = config.regulation_response_years
        self.max_fertility_factor = config.regulation_max_fertility_factor
        self.max_birth_probability = config.regulation_max_birth_probability
        self.extra_births = self.extra_deaths = self.below_floor_years = 0
        self.birth_factor = 1.0
        self.year_extra_births = self.year_extra_deaths = 0
        self.unmet_expected_births = 0.0
        self.history = []

    def birth_probabilities(
        self, probabilities, population, expected_deaths, survival, crisis=False
    ):
        self.birth_factor = 1.0
        self.year_extra_births = self.year_extra_deaths = 0
        if not self.enabled or crisis:
            return probabilities
        goal = min(self.ceiling, self.floor * (1 + self.buffer))
        if population >= goal:
            return probabilities
        desired = (expected_deaths + (goal - population) / self.response_years) / max(
            survival, 1e-6
        )
        base = float(probabilities.sum())
        if desired <= base:
            return probabilities
        # Zero probabilities stay zero: sterility, crises and rule prohibitions remain effective.
        eligible = probabilities > 0
        caps = np.maximum(
            probabilities,
            np.minimum(self.max_birth_probability, probabilities * self.max_fertility_factor),
        )
        spare = float(np.sum(caps[eligible] - probabilities[eligible]))
        adjusted = probabilities.copy()
        if spare:
            adjusted[eligible] += min(1, (desired - base) / spare) * (
                caps[eligible] - probabilities[eligible]
            )
        np.minimum(adjusted, caps, out=adjusted)
        achieved = float(adjusted.sum())
        self.birth_factor = achieved / base if base else 1.0
        self.unmet_expected_births += max(0.0, desired - achieved)
        return adjusted

    def record_births(self, draws, base, adjusted):
        self.year_extra_births = int(np.sum(draws < adjusted) - np.sum(draws < base))
        self.extra_births += self.year_extra_births

    def enforce_ceiling(self, rates, draws, mortality):
        if not self.enabled:
            return mortality
        excess = len(mortality) - int(mortality.sum()) - self.ceiling
        if excess <= 0:
            return mortality
        survivors = np.flatnonzero(~mortality)
        q = rates[survivors]
        # Conditional residual uniforms reuse the annual death draws; no second RNG stream.
        residual = np.clip((draws[survivors] - q) / (1 - q), 0, 1 - np.finfo(float).eps)
        hazards = np.maximum(-np.log1p(-q), 1e-9)
        scores = -np.log1p(-residual) / hazards
        chosen = survivors[np.argpartition(scores, excess - 1)[:excess]]
        mortality[chosen] = True
        self.year_extra_deaths = int(excess)
        self.extra_deaths += int(excess)
        return mortality

    def checkpoint(self, year, population, snapshot):
        below = self.enabled and population < self.floor
        self.below_floor_years += int(below)
        if self.enabled and snapshot:
            self.history.append(
                {
                    "year": year,
                    "population": population,
                    "birth_probability_factor": self.birth_factor,
                    "additional_births": self.year_extra_births,
                    "additional_deaths": self.year_extra_deaths,
                    "below_floor": bool(below),
                }
            )

    def summary(self):
        return {
            "enabled": self.enabled,
            "method": "single-run-biological-feedback-v1",
            "floor": self.floor,
            "ceiling": self.ceiling,
            "floor_policy": "recover-after-crisis",
            "response_years": self.response_years,
            "buffer": self.buffer,
            "additional_births": self.extra_births,
            "additional_deaths": self.extra_deaths,
            "below_floor_years": self.below_floor_years,
            "unmet_expected_births": self.unmet_expected_births,
            "history": self.history,
        }
