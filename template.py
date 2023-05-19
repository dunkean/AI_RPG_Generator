from dataclasses import dataclass, field
from enum import Enum
from typing import List, Type, Tuple


class EnumType(Enum):
    INDIVIDUAL = "Individual"
    COMMUNITY = "Community"
    WORK_GROUP = "Work group"
    GROUP_OF_INTEREST = "Group of Interest"
    RELIGIOUS = "Religious"
    POLITICAL = "Political"
    EDUCATIONAL = "Educational"


class EnumStructure(Enum):
    HIERARCHY = "hierarchy"
    DECENTRALIZED = "decentralized"
    AUTONOMOUS_GROUPS = "autonomous groups"
    ANARCHY = "anarchy"


class EnumRelation(Enum):
    DESPOTISM = "despotism"
    DEMOCRACY = "democracy"
    FRIEND = "friend"
    RIVAL = "rival"
    BUSINESS = "business"
    RELIGION = "religion"
    POLITICS = "politics"
    EDUCATION = "education"
    CRIMINAL = "criminal"

class EnumScale(Enum):
    INDIVIDUAL = "individual"
    LOCAL = "local"
    REGIONAL = "regional"
    COUNTRY = "country"
    WORLD = "world"

@dataclass
class Description:
    keywords: List[str] = field(default_factory=list)
    visual: List[str] = field(default_factory=list)
    short_description: str = ""
    description: str = ""


@dataclass
class Relation:
    type: str = ""
    description: Description = Description()
    contacts: List[Type['Entity']] = field(default_factory=list)


@dataclass
class Inclusion:
    role: Description = Description()
    position: Description = Description()


@dataclass
class Entity:
    name: List[str] = field(default_factory=list)
    type: EnumType = EnumType.INDIVIDUAL
    structure: EnumStructure = EnumStructure.HIERARCHY
    prosperity: List[str] = field(default_factory=list)
    activity: List[str] = field(default_factory=list)
    description: Description = Description()
    culture: Description = Description()
    customs: Description = Description()
    goals: Description = Description()
    resources: Description = Description()
    history: Description = Description()
    timeline: Description = Description()
    sites: Description = Description()
    anecdotes: Description = Description()
    potential_plot: Description = Description()
    relationships: List[Tuple[Relation, Type['Entity']]] = field(default_factory=list)
    parents: List[Tuple[Inclusion, Type['Entity']]] = field(default_factory=list)

    
class Group(Entity):
    structure: List[EnumStructure] = field(default_factory=list)
    size: int = 0
    scale: EnumScale = EnumScale.LOCAL
    key_entities: List[Type['Entity']] = field(default_factory=list)
    sub_groups: List[Tuple[Inclusion, Entity]] = field(default_factory=list)


class Person(Entity):
    type = EnumType.INDIVIDUAL
    surname: str = ""
    age: int = 0
    gender: str = ""


class Lore(Description):
    world_type: str = ""
    rules: str = ""