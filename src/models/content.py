"""TypedDict annotations for the content dict.

These provide documentation and IDE autocomplete but are not enforced at
runtime — the content dict remains a plain dict throughout the pipeline.
"""

from __future__ import annotations

from typing import TypedDict, NotRequired


class GenerationInfo(TypedDict):
    seed: int
    mean_group_size: int
    instruction: str


class SettingInfo(TypedDict):
    description: str
    type: str
    keywords: NotRequired[list[str]]


class CategoryInfo(TypedDict, total=False):
    keywords: list[str]
    descriptions: dict[str, str]


class ExternalInfluenceGroup(TypedDict, total=False):
    name: str
    type: str
    scale: str
    description: str
    keywords: list[str]
    population: int
    relationship: str


class DetailsInfo(TypedDict, total=False):
    type: str
    scale: str
    population: int
    description: str
    races: dict[str, float]
    name: str
    keywords: list[str]
    structure: str
    prosperity: str
    culture: CategoryInfo
    customs: CategoryInfo
    goals: CategoryInfo
    resources: CategoryInfo
    history: CategoryInfo
    external_influences: CategoryInfo
    timeline: CategoryInfo
    sites: CategoryInfo
    anecdotes: CategoryInfo
    descriptions: dict
    member_bonds: dict[str, float]


class NPCInfo(TypedDict, total=False):
    first_name: str
    last_name: str
    full_name: str
    race: str
    gender: str
    origin: str
    generation: str
    group_position: str
    beauty: str
    iq: float
    social_group: str
    workplace: str
    # Procedural appearance fields (Step 5)
    hair_color: str
    hair_length: str
    hair_style: str
    eye_color: str
    eye_shape: str
    skin_tone: str
    skin_texture: str
    face_shape: str
    nose_shape: str
    lip_shape: str
    chin_shape: str
    facial_hair: str
    height: str
    weight: str
    age_look: str
    physical_detail: str
    clothing_material: str
    clothing_color: str
    clothing_style: str
    clothing_accessory: str
    portrait_pov: str
    # Composite fields (backward-compatible, built from granular fields)
    hair: str
    eyes: str
    skin: str
    clothes: str
    # Enriched fields (Step 6)
    key_figure: bool
    age: int
    rank: str
    description: str
    traits: str
    clothes_detail: str
    nickname: str
    secret: str
    quote: str
    relationship: str
    structure_preference: str
    # Key figure fields (Step 11)
    habits: str
    goals_keywords: list[str]
    history: str
    anecdotes: list[str]
    plot: list[str]


class SocialGroup(TypedDict, total=False):
    origin: str
    type: str
    population: int
    members: list[str]  # NPC UUIDs


class ActivityGroup(TypedDict, total=False):
    name: str
    activity: str
    type: str
    keywords: list[str]
    motivations: list[str]
    role: str
    structure: str
    population: int
    prosperity: str
    origin: dict[str, float]
    age_ratio: dict[str, float]
    common_bonds: list[str]
    employees: list[str]  # NPC UUIDs
    # Enriched (Step 9)
    new_name: str
    description: str
    customs: str
    goals_keywords: list[str]
    history: str
    relationship: str
    timeline: list[str]
    anecdotes: list[str]
    sites: dict[str, list[str]]
    plot: list[str]


class GroupsInfo(TypedDict, total=False):
    social: dict[str, SocialGroup]
    activity: dict[str, ActivityGroup]


class ArchitectureInfo(TypedDict, total=False):
    architecture: list[str]
    global_view: str
    global_view_detailed: str
    sites_keywords: dict[str, list[str]]
    sites_details: dict[str, str]


class ContentDict(TypedDict, total=False):
    project_id: str
    generation: GenerationInfo
    setting: SettingInfo
    details: DetailsInfo
    groups: GroupsInfo
    npcs: dict[str, NPCInfo]
    architecture: ArchitectureInfo
