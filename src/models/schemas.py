"""Pydantic response models for every LLM step."""

from __future__ import annotations

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Step 1: Bootstrap
# ---------------------------------------------------------------------------

class BootstrapResponse(BaseModel):
    name: str = ""
    keywords: list[str] = Field(default_factory=list)
    setting_setting: list[str] = Field(default_factory=list)
    influence_areas: list[str] = Field(default_factory=list)
    structure: str = ""
    prosperity: str = ""
    culture: list[str] = Field(default_factory=list)
    customs: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    history: list[str] = Field(default_factory=list)
    external_influences: list[str] = Field(default_factory=list)
    timeline: list[str] = Field(default_factory=list)
    sites: list[str] = Field(default_factory=list)
    anecdotes: list[str] = Field(default_factory=list)
    races: dict[str, float] = Field(default_factory=dict)
    member_bonds: dict[str, float] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Step 2: Details
# ---------------------------------------------------------------------------

class DetailResponse(BaseModel):
    """A category expanded into titled paragraphs. Keys are section titles."""
    # Dynamic keys — use model_extra or just parse as dict
    model_config = {"extra": "allow"}


class DescriptionResponse(BaseModel):
    class LongDescription(BaseModel):
        model_config = {"extra": "allow"}

    class Descriptions(BaseModel):
        short: str = ""
        long: dict[str, str] = Field(default_factory=dict)

    descriptions: "DescriptionResponse.Descriptions" = Field(
        default_factory=lambda: DescriptionResponse.Descriptions()
    )


# ---------------------------------------------------------------------------
# Step 3: External Influences
# ---------------------------------------------------------------------------

class ExternalInfluenceEntry(BaseModel):
    type: str = ""
    scale: str = ""
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    population: int = 0
    relationship: str = ""


# ---------------------------------------------------------------------------
# Step 4: Workplaces / Activity Groups
# ---------------------------------------------------------------------------

class WorkplaceEntry(BaseModel):
    name: str = ""
    activity: str = ""
    type: str = ""
    keywords: list[str] = Field(default_factory=list)
    motivations: list[str] = Field(default_factory=list)
    role: str = ""
    structure: str = ""
    population: int = 0
    prosperity: str = ""
    origin: dict[str, float] = Field(default_factory=dict)
    age_ratio: dict[str, float] = Field(default_factory=dict)
    common_bonds: list[str] = Field(default_factory=list)


class ActivityGroupsResponse(BaseModel):
    groups: list[WorkplaceEntry] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Step 6: NPC Enrichment
# ---------------------------------------------------------------------------

class NPCEnrichment(BaseModel):
    full_name: str = ""
    key_figure: bool = False
    age: int = 0
    rank: str = ""
    description: str = ""
    traits: str = ""
    clothes_detail: str = ""
    nickname: str = ""
    secret: str = ""
    quote: str = ""
    relationship: str = ""
    structure_preference: str = ""


class PopulationDetailsResponse(BaseModel):
    members: list[NPCEnrichment] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Step 8: Employee Enrichment
# ---------------------------------------------------------------------------

class EmployeeEnrichment(BaseModel):
    name: str = ""
    key_figure: bool = False
    job: str = ""
    rank: str = ""
    skill_level: str = ""
    description: str = ""
    working_clothes: str = ""
    nickname: str = ""
    quote: str = ""
    relations: str = ""


class EmployeeDetailsResponse(BaseModel):
    employees: list[EmployeeEnrichment] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Step 9: Workplace Details
# ---------------------------------------------------------------------------

class WorkplaceDetailResponse(BaseModel):
    name: str = ""
    new_name: str = ""
    description: str = ""
    customs: str = ""
    goals_keywords: list[str] = Field(default_factory=list)
    history: str = ""
    relationship: str = ""
    timeline: list[str] = Field(default_factory=list)
    anecdotes: list[str] = Field(default_factory=list)
    sites: dict[str, list[str]] = Field(default_factory=dict)
    plot: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Step 10: Architecture
# ---------------------------------------------------------------------------

class ArchitectureResponse(BaseModel):
    architecture: list[str] = Field(default_factory=list)
    global_view: str = ""
    global_view_detailed: str = ""
    sites_keywords: dict[str, list[str]] = Field(default_factory=dict)
    sites_details: dict[str, str] = Field(default_factory=dict)


class SiteArchitecture(BaseModel):
    architecture: list[str] = Field(default_factory=list)
    details: str = ""
    type: str = ""
    state: str = ""
    inherits_architecture: bool = False


# ---------------------------------------------------------------------------
# Step 11: Key Figures
# ---------------------------------------------------------------------------

class KeyFigureResponse(BaseModel):
    full_name: str = ""
    description: str = ""
    habits: str = ""
    goals_keywords: list[str] = Field(default_factory=list)
    history: str = ""
    anecdotes: list[str] = Field(default_factory=list)
    plot: list[str] = Field(default_factory=list)
    relationship: dict[str, str] = Field(default_factory=dict)
