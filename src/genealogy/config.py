"""Validated, versioned scenario settings; probabilities are annual."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Annotated, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, create_model, model_validator

Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
Positive = Annotated[float, Field(gt=0, allow_inf_nan=False)]
Nonnegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Settlement(Settings):
    id: int = Field(ge=0, lt=2**31)
    name: str
    x: float
    y: float
    kind: str = "village"
    initial_weight: Positive = 1
    capacity: int = Field(default=1000, gt=0)
    activities: dict[str, Nonnegative] = Field(default_factory=lambda: {"agriculture": 1})
    metadata: dict = Field(default_factory=dict)
    races: dict[str, Nonnegative] = Field(default_factory=dict)

    @model_validator(mode="after")
    def activity_weights(self):
        if not self.activities or sum(self.activities.values()) <= 0:
            raise ValueError("Every settlement needs positive activity weights")
        return self


class Demography(Settings):
    max_age: int = Field(default=100, ge=60, le=2000)
    infant_mortality: Probability = 0.18
    child_mortality: Probability = 0.025
    child_max_age: int = Field(default=14, ge=1, le=1999)
    adult_mortality: Probability = 0.006
    aging_coefficient: Nonnegative = 0.00008
    aging_exponent: Positive = 0.095
    male_mortality_factor: Positive = 1.1
    maternal_mortality: Probability = 0.008
    male_birth_probability: Probability = 0.512
    fertility_peak: Probability = 0.32
    fertility_peak_age: int = Field(default=27, ge=18, le=2000)
    fertility_width: Positive = 10
    fertility_min_age: int = Field(default=18, ge=18, le=2000)
    fertility_max_age: int = Field(default=45, ge=18, le=2000)
    birth_spacing: int = Field(default=2, ge=1, le=100)
    # Historical periods can override any of these annual settings.

    @model_validator(mode="after")
    def ages_ordered(self):
        if self.fertility_max_age < self.fertility_min_age:
            raise ValueError("fertility_max_age must be >= fertility_min_age")
        if self.fertility_max_age >= self.max_age:
            raise ValueError("Fertility window must end before maximum lifespan")
        if self.child_max_age >= self.max_age:
            raise ValueError("Child age band must end before maximum lifespan")
        return self


class Society(Settings):
    marriage_rate: Probability = 0.30
    founder_match_participation: Probability = 0.85
    marriage_min_age: int = Field(default=18, ge=18, le=2000)
    marriage_max_age: int = Field(default=65, ge=18, le=2000)
    max_age_gap: int = Field(default=18, ge=0, le=2000)
    divorce_rate: Probability = 0.002
    remarriage_delay: int = Field(default=1, ge=1)
    kinship_depth: int = Field(default=3, ge=1, le=6)
    matching_attempts: int = Field(default=12, ge=1, le=100)
    status_affinity: Probability = 0.8
    status_weights: list[Nonnegative] = Field(default_factory=lambda: [0.76, 0.19, 0.045, 0.005])
    status_inheritance: Probability = 0.9
    activity_inheritance: Probability = 0.8
    migration_rate: Probability = 0.01
    dependent_age: int = Field(default=18, ge=1, le=1000)
    residence: Literal["patrilocal", "matrilocal", "either"] = "either"
    distance_scale: Positive = 25
    marriage_radius: Positive = 60
    migration_radius: Positive = 100
    max_neighbors: int = Field(default=12, ge=1, le=100)
    local_marriage_weight: Positive = 4
    capacity_growth: Nonnegative = 0.002

    @model_validator(mode="after")
    def bounds(self):
        if self.marriage_max_age < self.marriage_min_age:
            raise ValueError("marriage_max_age must be >= marriage_min_age")
        if not self.status_weights or len(self.status_weights) > 256:
            raise ValueError("Use between 1 and 256 social levels")
        if sum(self.status_weights) <= 0:
            raise ValueError("status_weights must have positive total")
        return self


DemographyPatch = create_model(
    "DemographyPatch",
    __base__=Settings,
    **{
        name: (field.rebuild_annotation() | None, None)
        for name, field in Demography.model_fields.items()
    },
)
SocietyPatch = create_model(
    "SocietyPatch",
    __base__=Settings,
    **{
        name: (field.rebuild_annotation() | None, None)
        for name, field in Society.model_fields.items()
    },
)


class Period(Settings):
    start_year: int
    demography: DemographyPatch = Field(default_factory=DemographyPatch)
    society: SocietyPatch = Field(default_factory=SocietyPatch)


class Race(Settings):
    """Fictional ancestry/species category; no inherent economic or social ranking."""

    name: str
    initial_weight: Nonnegative = 1
    demography: DemographyPatch = Field(default_factory=DemographyPatch)
    marriage_min_age: int | None = Field(default=None, ge=18, le=2000)
    marriage_max_age: int | None = Field(default=None, ge=18, le=2000)
    dependent_age: int | None = Field(default=None, ge=1, le=1000)
    max_age_gap: int | None = Field(default=None, ge=0, le=2000)
    metadata: dict = Field(default_factory=dict)


class Crossbreeding(Settings):
    """An unordered parental pairing with explicit fertility and offspring outcomes."""

    parents: tuple[str, str]
    marriage_affinity: Probability = 0.05
    fertility_factor: Nonnegative = 1
    max_age_gap: int | None = Field(default=None, ge=0, le=2000)
    offspring: dict[str, Nonnegative]

    @model_validator(mode="after")
    def positive_outcomes(self):
        if not self.offspring or sum(self.offspring.values()) <= 0:
            raise ValueError("Crossbreeding needs positive offspring weights")
        return self


class Event(Settings):
    name: str
    start_year: int
    end_year: int
    settlements: list[int] = Field(default_factory=list)
    mortality_factor: Nonnegative = 1
    extra_mortality: Probability = 0
    fertility_factor: Nonnegative = 1
    migration_factor: Nonnegative = 1
    capacity_factor: Positive = 1
    min_age: int = Field(default=0, ge=0)
    max_age: int = Field(default=2000, ge=0)
    sex: Literal["all", "male", "female"] = "all"
    races: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    @model_validator(mode="after")
    def ordered(self):
        if self.end_year < self.start_year or self.max_age < self.min_age:
            raise ValueError("Event date/age interval is reversed")
        return self


class Scenario(Settings):
    schema_version: Literal[1] = 1
    seed: int = Field(default=42, ge=0)
    start_year: int = Field(default=1000, ge=-100000, le=100000)
    generations: int = Field(default=5, ge=1, le=100)
    generation_years: int = Field(default=25, ge=1, le=100)
    years: int | None = Field(default=None, ge=1, le=10000)
    initial_population: int = Field(default=2000, ge=2, le=100_000_000)
    target_population: int | None = Field(default=None, ge=2, le=100_000_000)
    calibration_population: int = Field(default=2000, ge=100, le=100000)
    target_tolerance: Probability = 0.1
    virtual_settlements: int = Field(default=16, ge=1, le=10000)
    virtual_spacing: Positive = 20
    capacity_mode: Literal["scale", "fixed"] = "scale"
    demography: Demography = Field(default_factory=Demography)
    society: Society = Field(default_factory=Society)
    periods: list[Period] = Field(default_factory=list)
    events: list[Event] = Field(default_factory=list)
    settlements: list[Settlement] = Field(default_factory=list)
    races: list[Race] = Field(default_factory=lambda: [Race(name="human")])
    crossbreeding: list[Crossbreeding] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)

    @property
    def duration(self) -> int:
        return self.years if self.years is not None else self.generations * self.generation_years

    @model_validator(mode="after")
    def references(self):
        ids = [p.id for p in self.settlements]
        if len(ids) != len(set(ids)):
            raise ValueError("Settlement IDs must be unique")
        valid = set(ids) if ids else set(range(self.virtual_settlements))
        for event in self.events:
            if not set(event.settlements) <= valid:
                raise ValueError(f"Unknown settlements in event {event.name}")
        dates = [p.start_year for p in self.periods]
        if len(dates) != len(set(dates)):
            raise ValueError("Period start years must be unique")
        demo, society = self.demography, self.society
        for period in sorted(self.periods, key=lambda p: p.start_year):
            if not self.start_year <= period.start_year <= self.start_year + self.duration:
                raise ValueError("Period is outside simulation dates")
            demo = Demography.model_validate(
                {
                    **demo.model_dump(),
                    **period.demography.model_dump(exclude_none=True),
                }
            )
            society = Society.model_validate(
                {
                    **society.model_dump(),
                    **period.society.model_dump(exclude_none=True),
                }
            )
        for event in self.events:
            if (
                event.end_year <= self.start_year
                or event.start_year > self.start_year + self.duration
            ):
                raise ValueError("Event does not overlap simulated years")
        names = [r.name for r in self.races]
        if not names or len(names) > 32767 or len(names) != len(set(names)):
            raise ValueError("Use 1..32767 uniquely named races")
        if sum(r.initial_weight for r in self.races) <= 0:
            raise ValueError("Positive founder race weights are required")
        for event in self.events:
            if not set(event.races) <= set(names):
                raise ValueError("Unknown event race")
        pairs = set()
        for rule in self.crossbreeding:
            pair = tuple(sorted(rule.parents))
            if pair in pairs:
                raise ValueError("Duplicate crossbreeding rule")
            pairs.add(pair)
            if not set(rule.parents + tuple(rule.offspring)) <= set(names):
                raise ValueError("Unknown race in crossbreeding rule")
        for place in self.settlements:
            if not set(place.races) <= set(names) or place.races and sum(place.races.values()) <= 0:
                raise ValueError("Invalid settlement race weights")
        demographic_bases = [self.demography]
        base = self.demography
        for period in sorted(self.periods, key=lambda p: p.start_year):
            base = Demography.model_validate(
                {**base.model_dump(), **period.demography.model_dump(exclude_none=True)}
            )
            demographic_bases.append(base)
        for race in self.races:
            for base in demographic_bases:
                Demography.model_validate(
                    {**base.model_dump(), **race.demography.model_dump(exclude_none=True)}
                )
            low = race.marriage_min_age or self.society.marriage_min_age
            high = race.marriage_max_age or self.society.marriage_max_age
            if low > high:
                raise ValueError(f"Reversed marriage ages for {race.name}")
        return self


def load_scenario(path: Path) -> Scenario:
    return Scenario.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def virtual_map(config: Scenario) -> list[Settlement]:
    """A reproducible grid with agricultural, market, mining and coastal economies."""
    if config.settlements:
        if config.capacity_mode == "fixed":
            return config.settlements
        total = sum(p.capacity for p in config.settlements)
        scale = max(1, 1.5 * max(config.initial_population, config.target_population or 0) / total)
        return [
            p.model_copy(update={"capacity": round(p.capacity * scale)}) for p in config.settlements
        ]
    width = math.ceil(math.sqrt(config.virtual_settlements))
    result = []
    for i in range(config.virtual_settlements):
        kind, capacity, activities = (
            ("town", 5000, {"agriculture": 4, "craft": 3, "trade": 3})
            if i % 7 == 0
            else ("mining", 1200, {"mining": 7, "craft": 2, "agriculture": 1})
            if i % 5 == 0
            else ("port", 1800, {"fishing": 5, "trade": 3, "craft": 2})
            if i % width == 0
            else ("village", 1000, {"agriculture": 9, "craft": 1})
        )
        result.append(
            Settlement(
                id=i,
                name=f"{kind.title()} {i}",
                kind=kind,
                capacity=capacity,
                initial_weight=capacity,
                x=(i % width) * config.virtual_spacing,
                y=(i // width) * config.virtual_spacing,
                activities=activities,
            )
        )
    # Virtual worlds automatically scale their economic support to scenario size.
    scale = max(
        1,
        1.5
        * max(config.initial_population, config.target_population or 0)
        / sum(p.capacity for p in result),
    )
    if config.capacity_mode == "fixed":
        scale = 1
    return [p.model_copy(update={"capacity": round(p.capacity * scale)}) for p in result]
