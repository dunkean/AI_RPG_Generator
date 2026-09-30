##TODO init seed
import random
from numpy import random as npr

from copy import deepcopy as dc
import shortuuid

import name_generator as NG


positions = {
    "family": {
        "male": {
            "default": {"son": 0.6, "cousin": 0.1, "uncle": 0.1, "grandson": 0.1},
            "pool": {"father": 1, "grandfather": 0.2, "grandfather": 0.2, "eldest son": 0.4, "son": 0.2, "son": 0.2, "grandson": 0.2, "grandson": 0.2, "youngest son": 0.2, "cousin": 0.2, "cousin": 0.2, "uncle": 0.1, "uncle": 0.1},
        },
        "female": {
            "default": {"daughter": 0.6, "cousin": 0.1, "aunt": 0.1, "granddaughter": 0.1},
            "pool": {"mother": 1, "grandmother": 0.2, "grandmother": 0.2, "eldest daughter": 0.4, "daughter": 0.2, "daughter": 0.2, "granddaughter": 0.2, "granddaughter": 0.2, "youngest daughter": 0.2, "cousin": 0.2, "cousin": 0.2, "aunt": 0.1, "aunt": 0.1},
        }
    },
    "friends": {
        "default": {"old member": 0.7, "recent member": 0.3},
        "pool": {},
    },
    "colleagues": {
        "default": {"vice-chief": 0.1, "underling": 0.85, "newbie": 0.05},
        "pool": {"chief": 1, "vice-chief": 0.5, "underling": 0.5, "underling": 0.5, "newbie": 0.4},
    },
    "allies": {
        "default": {"prominent member": 0.2, "member": 0.8},
        "pool": {},
    },
    "common goal": {
        "default": {"prominent member": 0.2, "member": 0.8},
        "pool": {},
    },
    "common status": {
        "default": {"prominent member": 0.2, "member": 0.8},
        "pool": {},
    },
    "strangers": {
        "default": {"adventurer": 0.3, "on the run": 0.2, "wanderer": 0.2, "traveler": 0.2, "external employee": 0.1},
        "pool": {},
    },
    "solo": {
        "default": {"adventurer": 0.3, "on the run": 0.2, "wanderer": 0.2, "traveler": 0.2, "external employee": 0.1},
        "pool": {},
    },
}


def populate(content, group, group_id):
    group_pool = dc(positions[group["type"]])
    
    if group["type"] != "family":
        pool = group_pool["pool"]
        default_pool = group_pool["default"]

    family_race = random.choices(
        list(content["details"]["races"].keys()), 
        weights=list(content["details"]["races"].values()))[0]
    family_name = NG.get_last_name(family_race)
    race = ""

    members = {}
    for _ in range(group["population"]):
        gender = random.choice(["male", "female"])

        if group["type"] == "family":
            last_name = family_name
            race = family_race
            pool = group_pool[gender]["pool"]
            default_pool = group_pool[gender]["default"]
        else:
            race = random.choices(list(content["details"]["races"].keys()), weights=list(content["details"]["races"].values()))[0]
            last_name = NG.get_last_name(race)

        first_name = NG.get_first_name(race, gender)

        if len(pool) > 0:
            position = random.choices(list(pool.keys()), weights=list(pool.values()))[0]
            del pool[position]
        else:
            position = random.choices(list(default_pool.keys()), weights=list(default_pool.values()))[0]
        beauty = random.choice(["very ugly", "ugly", "average", "pretty", "very pretty"])
        iq = npr.normal(100, 15, 1)[0]

        members[shortuuid.uuid()] = {
            "full_name": first_name + " " + last_name,
            "first_name": first_name,
            "last_name": last_name,
            "race": race,
            "group_position": position,
            "beauty": beauty,
            "iq": iq,
            "social_group": group_id
        }

    return members


def population(content):
    count_per_age = {"child": 0, "teen": 0, "adult": 0, "middle-aged": 0, "old": 0}
    count_per_origin = {"local": 0, "foreign": 0}
    for _, v in content["groups"]["activity"].items():
        pop = float(v["population"])
        factor = pop / sum(v["age_ratio"].values())
        for age, count in v["age_ratio"].items():
            count_per_age[age] += count * factor
        count_per_origin["local"] += pop * v["origin"]["local"]
        count_per_origin["foreign"] += pop * v["origin"]["foreign"]


    group_types = ["family", "friends", "colleagues", "allies", "strangers", "common goal", "common status"]
    group_types_weights = {
        "local": [0.6, 0.4, 0.02, 0.02, 0.02, 0.02, 0.02],
        "foreign": [0.2, 0.2, 0.2, 0.2, 0.1, 0.2, 0.1]
    }
    group_types_distribution = {
        "local": (7, 3, 1),
        "foreign": (2, 1, 1)
    }

    # generate groups
    groups = {}
    for origin, population in count_per_origin.items():
        generated_population = 0
        while generated_population < population:
            group = {
                "origin": origin,
                "type": random.choices(group_types, weights=group_types_weights[origin])[0],
                "population": max(1, int(npr.default_rng().gumbel(*group_types_distribution[origin])))
            }
            if group["population"] == 1:
                group["type"] = "solo"
            groups[shortuuid.uuid()] = group
            generated_population += group["population"]

    # populate groups
    npcs = {}
    for g_id, group in groups.items():
        members = populate(content, group, g_id)
        npcs.update(members)
        group["members"] = list(members.keys())

    return {
        "groups": {"social": groups},
        "npcs": npcs
    }


def activity_members(content):
    # BERT transformation
    # for each person
    #  for each group
    #   compute BERT vector and cosine similarity
    
    # Linear programming 
    # Allocate people to groups based on the cos similarity matrix
    
    # Create new clusters from Bert pop matrix
    

    # for _, group in content["groups"]["activity"].items():
    #     # for member_id in group["members"]:
    #     #     content["npcs"][member_id]["activity_group"] = group["id"]

    return content


# Blood > 1 family
# Interests > random pick (ask gpt or something)
# Occupation > pick
# Enemy >

# >> LIVING GROUPS TYPOLOGY
# - **Common blood**: Groups based on genetic or biological ties, such as family, relatives, blood type, bloodline, etc.
# - **Common interests**: Groups based on shared hobbies, passions, or activities, such as book club, hacker group, knitting club, etc.
# - **Common business**: Groups based on shared occupation, profession, or function, related to money, such as corporation, trading team, union, etc.
# - **Common enemy**: Groups based on shared opposition or conflict with another group or entity, such as resistance group, alliance, coalition, etc.
# - **Common cause**: Groups based on shared objective or purpose, such as charity group, campaign group, support group, etc.
# - **Common identity**: Groups based on shared social status or shared individual features, such as ethnicity, age, sexuality, etc.
# - **Common ideology**: Groups based on shared beliefs, values, or principles, such as political party, religious group, social movement, etc.
# - **Common past**: Groups based on shared history or experience, such as alumni group, reunion group, veterans group, etc.
# - **Common knowledge**: Groups based on shared information or skills, such as study group, trivia group, school, etc.
# - **Common place**: Groups based on shared location or origin, such as town, community group, country club, etc.
# - **Common friendship**: Groups based on shared bond or connection with others, such as friends, buddies, pals, etc.