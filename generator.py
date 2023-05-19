# def fill_workplaces(content, new_content):
#     workplaces = []
#     for workplace in new_content["workplaces"]:
#         workplaces.append({"name": workplace})
#     content["workplaces"] = workplaces
#     return content

import numpy as np
from numpy import random as npr
import random
from pynames.generators.iron_kingdoms import DwarfFullnameGenerator
from pynames.generators.elven import DnDNamesGenerator
from pynames.generators.iron_kingdoms import CaspianMidlunderSuleseFullnameGenerator, KhadoranFullnameGenerator, GobberFullnameGenerator, IossanNyssFullnameGenerator, ThurianFullnameGenerator, ThurianMorridaneFullnameGenerator, OgrunFullnameGenerator, MorridaneFullnameGenerator, TordoranFullnameGenerator, RynFullnameGenerator, TrollkinFullnameGenerator
from pynames import GENDER, LANGUAGE


generators = {"human": CaspianMidlunderSuleseFullnameGenerator(), "elf": DnDNamesGenerator(), "half-elf": DnDNamesGenerator(), 
              "dwarf": DwarfFullnameGenerator(), "halfling": ThurianMorridaneFullnameGenerator(), "gnome": IossanNyssFullnameGenerator()}


age_weights_per_situations = {
    "old member":[0.4,0.55,0.05], 
    "recent member":[0.05,0.55,0.4], 
    "chief":[0.6,0.3,0.1], 
    "vice-chief":[0.1,0.6,0.3], 
    "underling":[0.05,0.55,0.4], 
    "newbie":[0.05,0.35,0.6], 
    "follower":[0.05,0.55,0.4], 
    "old follower":[0.4,0.55,0.05], 
    "grandparent":[0.6,0.3,0.1],
    "grandmother":[0.6,0.3,0.1],
    "grandfather":[0.6,0.3,0.1],
    "parent":[0.3,0.6,0.1],
    "mother":[0.3,0.6,0.1],
    "father":[0.3,0.6,0.1],
    "child":[0.05,0.4,0.55], 
    "son":[0.05,0.4,0.55],
    "daughter":[0.05,0.4,0.55],
    "grandchild":[0.05,0.25,0.7],
    "grandson":[0.05,0.25,0.7],
    "granddaughter":[0.05,0.25,0.7],
    "cousin":[0.05,0.55,0.4],
    "pibling":[0.4,0.5,0.1],
    "uncle":[0.5,0.5,0.1],
    "aunt":[0.5,0.5,0.1],
    "boss":[0.6,0.3,0.1],
    "adventurer":[0.2,0.6,0.2],
    "on the run":[0.2,0.6,0.2],
    "traveler":[0.2,0.6,0.2],
    "wanderer":[0.3,0.5,0.2],
    "assignment":[0.2,0.6,0.2],
    "quest":[0.2,0.6,0.2],
    "eldest child":[0.05,0.55,0.4],
    "youngest child":[0.05,0.35,0.6],
    "eldest son":[0.05,0.55,0.4],
    "youngest son":[0.05,0.35,0.6],
    "eldest daughter":[0.05,0.55,0.4],
    "youngest daughter":[0.05,0.35,0.6],
}

def get_family_members(size, generator, family_name, family_race):
    rd_situation = {
        "male": {"son": 0.6, "cousin": 0.1, "uncle": 0.1, "grandson": 0.1},
        "female": {"daughter": 0.6, "cousin": 0.1, "aunt": 0.1, "granddaughter": 0.1}
    }
    situations = {
        "male": {"father": 1, "grandfather": 0.2, "grandfather": 0.2, "eldest son": 0.4, "son": 0.2, "son": 0.2, "grandson": 0.2, "grandson": 0.2, "youngest son": 0.2, "cousin": 0.2, "cousin": 0.2, "uncle": 0.1, "uncle": 0.1},
        "female": {"mother": 1, "grandmother": 0.2, "grandmother": 0.2, "eldest daughter": 0.4, "daughter": 0.2, "daughter": 0.2, "granddaughter": 0.2, "granddaughter": 0.2, "youngest daughter": 0.2, "cousin": 0.2, "cousin": 0.2, "aunt": 0.1, "aunt": 0.1}
    }
    members = []
    for _ in range(size):
        gender = random.choice(["male", "female"])
        name_gender = GENDER.MALE if gender == "male" else GENDER.FEMALE
        full_name = str(generator.get_name(name_gender))
        name = full_name.split(" ")[0]
        while (name in [member["name"] for member in members]):
            full_name = str(generator.get_name(name_gender))
            name = full_name.split(" ")[0]

        situation = None
        if not situations[gender]:
            s_keys = list(rd_situation[gender].keys())
            s_values = list(rd_situation[gender].values())
            situation = random.choices(s_keys, weights=s_values)[0]
        else:
            s_keys = list(situations[gender].keys())
            s_values = list(situations[gender].values())
            situation = random.choices(s_keys, weights=s_values)[0]
            del situations[gender][situation]

        race = family_race
        if family_race == "half-elf":
            race = random.choices(["human", "elf", "half-elf"], weights=[0.1, 0.1, 0.8])[0]
        
        generation = random.choices(["old", "mid", "young"], weights=age_weights_per_situations[situation])[0]
        members.append({
            "name": name,
            "surname": family_name,
            "race": race,
            "gender": gender,
            "origin": "native",
            "generation": generation,
            "situation": situation,
            "beauty": random.choices(["very ugly", "ugly", "average", "pretty", "very pretty"], weights=[0.05, 0.1, 0.5, 0.2, 0.15])[0],
        })

    return members


def family_distribution(population, ratio):
    gen_population = 0
    groups = []
    while gen_population < population:
        size = int(npr.default_rng().gumbel(7, 3, 1))
        if size <= 0:
            size = 1
        race = npr.choice(list(ratio.keys()), p=list(ratio.values()))
        
        generator = generators[race]
        family_name = str(generator.get_name()).split(" ")[-1]
        while (family_name in [group["name"] for group in groups]):
            family_name = str(generator.get_name()).split(" ")[-1]
        
        groups.append({
            "name": family_name,
            "size": size,
            "origin": "natives",
            "race": race,
            "type": "family_type",
            "members": get_family_members(size, generator, family_name, race),
        })
        gen_population += size
    
    for g in groups:
        # member_list = [f"{m['name']} {m['surname']}" for m in g["members"]]
        for m in g["members"]:
            # m["main_group_members"] = [mate for mate in member_list if mate != f"{m['name']} {m['surname']}"]
            if m["situation"].lower() in ["mother", "grandmother"]:
                if random.random() < 0.7:
                    m["birth name"] = npr.choice([group["name"] for group in groups])
                    while m["birth name"] == m["surname"]:
                        m["birth name"] = npr.choice([group["name"] for group in groups])
    
    return groups




def get_outsider_members(size, group_type, individuals, ratio):
    rd_situation = {
        "team_type": {"old member": 0.7, "recent member": 0.3},
        "hierarchy_type": {"vice-chief": 0.1, "underling": 0.85, "newbie": 0.05},
        "cult_type": {"follower": 0.9, "old follower": 0.05},
        "family_type": {"grandparent": 0.2, "child": 0.2, "grandchild": 0.1, "cousin": 0.1, "pibling": 0.1},
    }
    situations = {
        "team_type": {"old member": 0.2, "old member": 0.2, "recent member": 0.2},
        "hierarchy_type": {"chief": 1, "vice-chief": 0.5, "underling": 0.5, "underling": 0.5, "newbie": 0.4},
        "cult_type": {"boss": 1, "old follower": 0.2, "follower": 0.2},
        "solo_type": {"adventurer": 0.3, "on the run": 0.2, "wanderer": 0.2, "traveler": 0.1, "assignment": 0.1, "quest": 0.1},
        "family_type": {"parent": 1, "parent": 0.3, "grandparent": 0.2, "eldest child": 0.4, "child": 0.2, "child": 0.2, "grandchild": 0.2, "grandchild": 0.2, "youngest child": 0.2, "cousin": 0.2, "pibling": 0.1},
    }
    members = []
    team_situation = random.choices( list(situations[group_type].keys()), weights=list(situations[group_type].values()))[0]
    for _ in range(size):
        gender = random.choice(["male", "female"])
        name_gender = GENDER.MALE if gender == "male" else GENDER.FEMALE
        race = npr.choice(list(ratio.keys()), p=list(ratio.values()))
        generator = generators[race]
        full_name = str(generator.get_name(name_gender))
        name = full_name.split(" ")[0]
        surname = full_name.split(" ")[-1]
        while f"{name} {surname}" in individuals:
            full_name = str(generator.get_name(name_gender))
            name = full_name.split(" ")[0]
            surname = full_name.split(" ")[-1]
        
        situation = None
        if group_type == "solo_type":
            situation = team_situation
        elif not situations[group_type]:
            s_keys = list(rd_situation[group_type].keys())
            s_values = list(rd_situation[group_type].values())
            situation = random.choices(s_keys, weights=s_values)[0]
        else:
            s_keys = list(situations[group_type].keys())
            s_values = list(situations[group_type].values())
            situation = random.choices(s_keys, weights=s_values)[0]
            del situations[group_type][situation]

        generation = random.choices(["old", "mid", "young"], weights=age_weights_per_situations[situation])[0]
        members.append({
            "name": name,
            "surname": surname,
            "race": race,
            "gender": gender,
            "generation": generation,
            "origin": "outsider",
            "situation": situation,
            "beauty": random.choices(["very ugly", "ugly", "average", "pretty", "very pretty"], weights=[0.05, 0.1, 0.5, 0.2, 0.15])[0],
        })

    return members


def outsiders_distribution(population, individuals, ratio):
    gen_population = 0
    groups = []
    groups_names = []
    while gen_population < population:
        size = int(npr.default_rng().gumbel(2, 1, 1))
        if size <= 0:
            size = 1
        group_type = npr.choice(["team_type", "hierarchy_type", "cult_type", "family_type"])
        if size == 1:
            group_type = "solo_type"
        if size == 2:
            group_type = random.choices(["solo_type", "family_type", group_type], weights=[0.4, 0.3, 0.3])[0]
        group_name = TordoranFullnameGenerator().get_name_simple()
        while group_name in groups_names:
            group_name = TordoranFullnameGenerator().get_name_simple()
        groups_names.append(group_name)

        groups.append({
            "name": group_name,
            "origin": "outsiders",
            "size": size,
            "type": group_type,
            "members": get_outsider_members(size, group_type, individuals, ratio),
        })
        gen_population += size
    
    # for g in groups:
        # member_list = [f"{m['name']} {m['surname']}" for m in g["members"]]
        # for m in g["members"]:
        #     m["main_group_members"] = [mate for mate in member_list if mate != f"{m['name']} {m['surname']}"]
    return groups




def get_native_populations(content):
    groups = content["workplaces"].copy()
    ratio = content["size"] / sum([int(v["population"]) for v in groups])
    for g in groups:
        g["population"] = max(1, ratio * int(g["population"]))
        # g["part-time"] = max(1, ratio * int(g["part-time"]))

    natives_count = sum([int(v["population"])
                        for v in groups if v["composition"].lower() == "natives"])
    mix_count = sum([int(v["population"])
                    for v in groups if v["composition"].lower() == "mix"])
    outsiders_count = sum([int(v["population"])
                        for v in groups if v["composition"].lower() == "outsiders"])

    natives = int(natives_count + mix_count * 0.6)
    outsiders = int(outsiders_count + mix_count * 0.4)
    return natives, outsiders, groups



age_weight_dict = {
    "old": {"old": 1, "mid": 0.1, "young": 0.02},
    "olds": {"old": 1, "mid": 0.1, "young": 0.02},
    "olds and mid": {"old": 1, "mid": 1, "young": 0.1},
    "old and mid": {"old": 1, "mid": 1, "young": 0.1},
    "mid": {"old": 0.1, "mid": 1, "young": 0.1},
    "young": {"old": 0.02, "mid": 0.1, "young": 1},
    "young and mid": {"old": 0.1, "mid": 1, "young": 1},
    "youngs": {"old": 0.02, "mid": 0.1, "young": 1},
    "old_mix": {"old": 0.5, "mid": 0.25, "young": 0.02},
    "old mix": {"old": 0.5, "mid": 0.25, "young": 0.02},
    "olds mix": {"old": 0.5, "mid": 0.25, "young": 0.02},
    "mid_mix": {"old": 0.25, "mid": 0.5, "young": 0.25},
    "mid mix": {"old": 0.25, "mid": 0.5, "young": 0.25},
    "young_mix": {"old": 0.02, "mid": 0.25, "young": 0.5},
    "young mix": {"old": 0.02, "mid": 0.25, "young": 0.5},
    "young and mix": {"old": 0.02, "mid": 0.25, "young": 0.5},
    "mix": {"old": 0.3, "mid": 0.4, "young": 0.3},
    "all": {"old": 0.3, "mid": 0.4, "young": 0.3},
}


def age_weight(ages, generation):
    return age_weight_dict[ages][generation]


def choose_group_by_type(group_pool, composition_filter, group_type_filter, sizes):
    """
    The function chooses groups from a pool based on composition, type, and size filters, and returns a
    list of chosen groups and their details.
    
    :param group_pool: A list of dictionaries representing available groups to choose from. Each
    dictionary contains information about the group, such as its name, type, size, and members
    :param composition_filter: A dictionary that filters groups based on their composition. The keys are
    the origin of the group (e.g. "US", "UK", "Canada") and the values are the ratio of how much the
    group's origin matches the desired origin. For example, if the desired origin is "US"
    :param group_type_filter: A dictionary that filters the groups based on their type. The keys are the
    group types and the values are the ratios by which the groups of that type should be preferred. For
    example, if group_type_filter = {"A": 2, "B": 1}, then groups of type "A
    :param sizes: A list of integers representing the desired sizes of the groups to be formed
    :return: a tuple containing two lists: `group_list` and `group_details`. `group_list` contains
    dictionaries representing the chosen groups, where each dictionary has the members of a group as
    values and the members' names as keys. `group_details` contains tuples representing the details of
    the chosen groups, where each tuple has the name and type of a group.
    """
    group_list = []
    group_details = []
    # print(composition_filter, group_type_filter, len(group_pool), sizes)
    for size in sizes:
        groups_weights = {}
        for g in group_pool:
            comp_ratio = 1 if g["origin"] not in composition_filter else composition_filter[g["origin"]]
            type_ratio = 1 if g["type"] not in group_type_filter else group_type_filter[g["type"]]
            size_weight = 1 / (abs(int(g["size"]) - size) + 1)
            groups_weights[g["name"]] = comp_ratio * type_ratio * size_weight

        if len(groups_weights) == 0:
            print("No groups left to choose from")

        group = random.choices(list(groups_weights.keys()), weights=list(groups_weights.values()), k=1)[0]
        group_idx = [i for i, g in enumerate(group_pool) if g["name"] == group][0]

        group_chosen = group_pool.pop(group_idx)
        group_chosen_obj = {f"{m['name']} {m['surname']}": m for m in group_chosen["members"]}
        group_list.append(group_chosen_obj)
        group_details.append((group_chosen["name"], group_chosen["type"]))

    return group_list, group_details


def generate_distributed_integers(n, S, spread=0.3):
    if n == 0:
        return []
    elif n == 1:
        return [S]
    mean = S/n
    std_dev = (S*spread)/n
    numbers = np.random.normal(mean, std_dev, n)
    numbers = np.maximum(numbers, 1)
    numbers *= S/np.sum(numbers)
    numbers = np.round(numbers).astype(int)
    numbers[-1] += S - np.sum(numbers)
    return list(numbers)


def get_group_sizes(composition, type, ages, size):
    if type == "family":
        return [size]
    elif type == "cooperative":
        mean_size_group_weights = [0.1, 0.2, 0.3, 0.2, 0.1, 0.05, 0.05]
        mean_size_group = [2, 3, 4, 5, 6, 7, 8]
        n_subgroups = [size // m for m in mean_size_group]
        coop_size = random.choices(
            n_subgroups, weights=mean_size_group_weights)[0]
        sizes = [max(1, int(npr.default_rng().gumbel(size / coop_size, 1, 1))) for _ in range(coop_size)]
        return sizes
    elif type == "guild":
        mean_size_group_weights = [0.1, 0.2, 0.3, 0.2, 0.1, 0.05, 0.05]
        mean_size_group = [2, 3, 4, 5, 6, 7, 8]
        n_subgroups = [size // m for m in mean_size_group]
        coop_size = random.choices(
            n_subgroups, weights=mean_size_group_weights)[0]
        sizes = [max(1, int(npr.default_rng().gumbel(size / coop_size, 1, 1))) for _ in range(coop_size)]
        return sizes
    elif type == "crew":
        n_groups = random.choices([0, 1, 2, 3, 4], weights=[0.05, 0.8, 0.1, 0.05, 0.05])[0]
        sizes = generate_distributed_integers(n_groups, size)
    elif type == "illegal":
        n_groups = random.choices([0, 1, 2, 3, 4], weights=[0.05, 0.8, 0.1, 0.05, 0.05])[0]
        sizes = generate_distributed_integers(n_groups, size)
    elif type == "company":
        n_groups = random.choices([0, 1, 2, 3, 4], weights=[0.5, 0.1, 0.1, 0.1, 0.1])[0]
        sizes = generate_distributed_integers(n_groups, size)
    elif type == "council":
        sizes = []
    elif type == "team":
        n_groups = random.choices([0, 1, 2, 3, 4], weights=[0.05, 0.6, 0.2, 0.1, 0.05])[0]
        sizes = generate_distributed_integers(n_groups, size)
    else:
        print("Unknown group type", type)

    return sizes


group_filters = {
    "family": {
        "natives": ({"outsiders": 0.001}, {"family_type": 10}),
        "mix": ({"outsiders": 0.2}, {"family_type": 10}),
        "outsiders": ({"natives": 0.001}, {"family_type": 10}),
    },
    "cooperative": {
        "natives": ({"outsiders": 0.001}, {"family_type": 10}),
        "mix": ({"outsiders": 0.2}, {"family_type": 10}),
        "outsiders": ({"natives": 0.001}, {"family_type": 10}),
    },
    "guild": {
        "natives": ({"outsiders": 0.2}, {"hierarchy_type": 5, "cult_type": 2}),
        "mix": ({}, {"hierarchy_type": 5, "cult_type": 2}),
        "outsiders": ({"natives": 0.2}, {"hierarchy_type": 5, "cult_type": 2}),
    },
    "crew": {
        "natives": ({"outsiders": 0.05}, {"hierarchy_type": 2, "team_type": 5, "cult_type": 5}),
        "mix": ({}, {"hierarchy_type": 2, "team_type": 5, "cult_type": 5}),
        "outsiders": ({"natives": 0.05}, {"hierarchy_type": 2, "team_type": 5, "cult_type": 5}),
    },
    "illegal": {
        "natives": ({"outsiders": 0.2}, {"hierarchy_type": 10, "team_type": 0.2, "family_type": 2, "cult_type": 3}),
        "mix": ({}, {"hierarchy_type": 10, "team_type": 0.2, "family_type": 2, "cult_type": 3}),
        "outsiders": ({"natives": 0.4}, {"hierarchy_type": 10, "team_type": 0.2, "family_type": 2, "cult_type": 3}),
    },
    "company": {
        "natives": ({"outsiders": 0.2}, {"hierarchy_type": 10, "team_type": 0.2, "family_type": 2, "cult_type": 3}),
        "mix": ({}, {"hierarchy_type": 10, "team_type": 0.2, "family_type": 2, "cult_type": 3}),
        "outsiders": ({"natives": 0.4}, {"hierarchy_type": 10, "team_type": 0.2, "family_type": 2, "cult_type": 3}),
    },
    "council": {
        "natives": ({"outsiders": 0.001}, {}),
        "mix": ({"outsiders": 0.5}, {}),
        "outsiders": ({"natives": 0.05}, {}),
    },
    "team": {
        "natives": ({"outsiders": 0.1}, {"hierarchy_type": 0.5, "team_type": 10, "family_type": 2, "cult_type": 0.2}),
        "mix": ({}, {"hierarchy_type": 0.5, "team_type": 10, "family_type": 2, "cult_type": 0.2}),
        "outsiders": ({"natives": 0.2}, {"hierarchy_type": 0.5, "team_type": 10, "family_type": 2, "cult_type": 0.2}),
    }
}

# team_type", "hierarchy_type", "cult_type", "family_type"

GROUP_WEIGHTS_IND = {
    "family": {
        "natives": 0.1,
        "mix": 0.2,
        "outsiders": 0.1,
    },
    "cooperative": {
        "natives": 0.1,
        "mix": 0.2,
        "outsiders": 0.1,
    },
    "guild": {
        "natives": 0.3,
        "mix": 0.5,
        "outsiders": 0.2,
    },
    "crew": {
        "natives": 0.05,
        "mix": 0.05,
        "outsiders": 0.1,
    },
    "company": {
        "natives": 0.4,
        "mix": 0.5,
        "outsiders": 0.4,
    },
    "council": {
        "natives": 0.4,
        "mix": 0.05,
        "outsiders": 0.05,
    },
    "team": {
        "natives": 0.1,
        "mix": 0.3,
        "outsiders": 0.2,
    },
    "illegal": {
        "natives": 0.1,
        "mix": 0.3,
        "outsiders": 0.7,
    },

}


def preferential_group_selection(composition, type, ages, size, group_pool, individuals_pool):
    group_list = None
    group_details = {}
    if ages not in age_weight_dict:
        ages = ages.replace(" ", "_")

    if composition in translation_dict:
        composition = translation_dict[composition]
    if type in translation_dict:
        type = translation_dict[type]

    group_sizes = get_group_sizes(composition, type, ages, size)
    filters = group_filters[type][composition]
    group_list, group_details = choose_group_by_type(group_pool, *filters, sizes=group_sizes)

    return group_list, group_details

# def choose_individuals(sources, weights, count, ages, individuals_pool):
#     individuals = []
#     for _ in range(int(count)):
#         src_idx = random.choices(range(len(sources)), weights=weights, k=1)[0]
#         source = sources[src_idx]
#         age_weights = [age_weight(ages, p["generation"]) for k, p in source.items()]
#         ind_chosen = random.choices( list(source.keys()), weights=age_weights, k=1)[0]
#         individuals.append(source.pop(ind_chosen))
#         if len(source) == 0:
#             del sources[src_idx]
#             weights.pop(src_idx)

#         if ind_chosen in individuals_pool:
#             individuals_pool.pop(ind_chosen)
#     return individuals


translation_dict = {
    "mixture": "mix",
    "band": "crew",
    "coven": "guild",
    "corporation": "company",
    "business": "company",
}


def tr(w):
    if w in translation_dict:
        return translation_dict[w]
    else:
        return w


def clean_pool(pool, individual_pool, src_weights):
    for i, src_pool in enumerate(pool):
        if src_pool is individual_pool:
            continue

        to_delete = []
        for fullname in src_pool.keys():
            if fullname not in individual_pool:
                to_delete.append(fullname)
        
        for name in to_delete:
            del src_pool[name]

        if len(src_pool.items()) == 0:
            pool.pop(i)
            src_weights.pop(i)


def preferential_individual_selection(workplace, individual_pool, wk_group_members_pool):
    wk_type = tr(workplace["type"].lower())
    wk_compo = tr(workplace["composition"].lower())
    individual_group_weight = GROUP_WEIGHTS_IND[wk_type][wk_compo]
    wk_groups = list(wk_group_members_pool[workplace["name"]].values())
    workplace_groups_weights_normalized = [(1 - individual_group_weight) / len(wk_groups) for _ in range(len(wk_groups))]

    pool = [*wk_groups, individual_pool]
    print("Number of pools: ", len(pool))
    src_weights = [*workplace_groups_weights_normalized, individual_group_weight]

    selected_individuals = []
    print("available people:", sum([len(p.values()) for p in pool]), workplace["population"])
    
    for _ in range(int(workplace["population"])):
        clean_pool(pool, individual_pool, src_weights)
        source_pool = random.choices(pool, weights=src_weights, k=1)[0]
        age_weights = [age_weight(workplace["ages"].lower(), p["generation"].lower()) for p in source_pool.values()]
        factors = [3 if p["structure_preference"].lower() in workplace["type"].lower() else 0.5 for p in source_pool.values()]
        weights = [w * f for w, f in zip(age_weights, factors)]

        selected_full_name = random.choices(list(source_pool.keys()), weights=weights, k=1)[0]
        selected_individuals.append(source_pool.pop(selected_full_name))
        if selected_full_name in individual_pool:
            individual_pool.pop(selected_full_name)

    return selected_individuals


# def fill_workplace(workplace, families):
#     business_type = workplace["type"].lower()
#     n_families_prob = {
#         "family": 1,
#         "guild": 0,
#         "company": random.choices([0, 1], weights=[0.8, 0.2])[0],
#         "cooperative": random.choices([2, 3, 4, 5, 6], weights=[0.2, 0.3, 0.3, 0.1, 0.1])[0]
#     }
#     n_families = n_families_prob[business_type]
    
#     # families = []
#     # for _ in range(n_families):
        

# def fill_workplaces(content, new_content):
#     families = family_distribution(content["size"])
#     for workplace in new_content["workplaces"]:
#         workplace["persons"] = get_persons(content["name"], workplace, families)


# def get_persons(place, workplace):
   
#     random_family = {
#         "male": {"son": 0.6, "cousin": 0.1, "uncle": 0.1, "grandson": 0.1},
#         "female": {"daughter": 0.6, "cousin": 0.1, "aunt": 0.1, "granddaughter": 0.1}
#     }

#     person_list = []
#     surnames = []
#     for _ in range(min(30, int(int(workplace["workers"])*1.25))):
#         gender = random.choice(["male", "female"])
#         name_gender = GENDER.MALE if gender == "male" else GENDER.FEMALE
#         isFamily = len(families) > 0 and random.random() > 0.2
#         family = random.choice(families) if isFamily else None
#         race = family["race"] if isFamily else random.choices(
#             list(ratio.keys()), weights=list(ratio.values()), k=1)[0]
#         full_name = str(generators[race].get_name(name_gender))
#         name = full_name.split(" ")[0]
#         if isFamily:
#             surname = family["name"]
#             keys = list(family["members"][gender].keys())
#             values = list(family["members"][gender].values())
#             if not keys:
#                 situation = random.choices(list(random_family[gender].keys()), weights=list(
#                     random_family[gender].values()))[0]
#             else:
#                 situation = random.choices(keys, weights=values)[0]
#                 del family["members"][gender][situation]
#         else:
#             situation = random.choices(
#                 ["worker", "outsider", "retired"], weights=[0.7, 0.15, 0.15])[0]
#             surname = (
#                 random.choice(surnames)
#                 if random.random() < 0.1 and surnames
#                 else full_name.split(" ")[-1]
#             )
#         person = {
#             "name": name,
#             "surname": surname,
#             "race": race,
#             "gender": gender,
#             "situation": situation,
#             "beauty": random.choices(["very ugly", "ugly", "average", "pretty", "very pretty"], weights=[0.05, 0.1, 0.5, 0.2, 0.15])[0],
#         }
#         person_list.append(person)
#     return person_list



# from base64 import b64encode
# from os import urandom
# import collections

# default_id = b64encode(urandom(4)).decode("utf-8")


# class ContentGenerator():
#     def __init__(self, instruction, lore, *, options):
#         self.instruction = instruction
#         self.lore = lore
#         self.options = options
#         self.id = default_id

#     def generate_context(prompt, *, options):
#         pass

#     def generate_calendar(prompt, *, options):
#         pass

#     def generate_poi(prompt, *, options):
#         pass

#     def generate_people_cluster(prompt, *, options):
#         pass

#     def generate_place(prompt, *, options):
#         pass

#     # def full_generation(prompt, id=None,*, options):
#     #     place = generate_place(prompt, options=options)
#     #     # if id == None:
#     #         # id 
#     #     people_cluster = generate_people_cluster(prompt, options=options)
        
#     # def execute_step(self, generation_step, generated_content, *, options):
#     #     for sub_step in generation_step:
#     #         sub_step_name = sub_step.__name__
#     #         print("Executing substep", sub_step_name")
#     #         generated_content = sub_step(generated_content, options=options)

#     #     return generated_content

#     # def execute_pipeline(self, id, pipeline, bootstrap_content, *, options):
#     #     options["id"] = id
#     #     generated_content = bootstrap_content
#     #     for step in pipeline:
#     #         print(f"Generating {step}")
#     #         new_content = self.execute_step(pipeline[step], generated_content, options=options)
#     #         generated_content.update(new_content)7
#     #     return generated_content
    
# # class SocialGroup:
# #     def __init__(self, name, size, structure, culture, goals, history, resources):
# #         self.name = name
# #         self.size = size
# #         self.structure = structure
# #         self.culture = culture
# #         self.goals = goals
# #         self.history = history
# #         self.resources = resources
# #         self.subgroups = []
# #         self.individuals = []
# #         self.parent = None

# #     def add_subgroup(self, subgroup):
# #         self.subgroups.append(subgroup)
# #         subgroup.parent = self

# #     def add_individual(self, individual):
# #         self.individuals.append(individual)
# #         individual.groups.append(self)

# #     def remove_subgroup(self, subgroup):
# #         self.subgroups.remove(subgroup)
# #         subgroup.parent = None

# #     def remove_individual(self, individual):
# #         self.individuals.remove(individual)
# #         individual.groups.remove(self)
    
# #     def __str__(self):
# #         return self.name

# # Generators = collections.namedtuple("Generators", "generator prompter parser reducer")
# # G = Generators(generator=ContentGenerator(), prompter=Prompter(), parser=Parser(), renderer=Renderer())

# # pipeline = {
# #     "place generation": [G.prompter.prompt_place, G.generator.generate_place, G.parser.parse_place],
# #     "context generation": [G.prompter.prompt_context, G.generator.generate_context, G.parser.parse_context],
# #     "people clusters generation": [G.prompter.prompt_people_cluster, G.generator.generate_people_cluster, G.parser.parse_people_cluster],
# #     "calendar generation": [G.prompter.prompt_calendar, G.generator.generate_calendar, G.parser.parse_calendar],
# #     "poi generation": [G.prompter.prompt_poi, G.generator.generate_poi, G.parser.parse_poi],
# #     "plots generation": [G.prompter.prompt_plot, G.generator.generate_plot, G.parser.parse_plot],
# #     "places rendering": [G.renderer.render_places],
# #     "people rendering": [G.renderer.render_people],
# # }

# # Generation defines




# class SocialGroup:
#     def __init__(self, name, size, structure, culture, goals, history, resources):
#         self.name = name
#         self.size = size
#         self.structure = structure
#         self.culture = culture
#         self.goals = goals
#         self.history = history
#         self.resources = resources
#         self.subgroups = []
#         self.individuals = []
#         self.parent = None

#     def add_subgroup(self, subgroup):
#         self.subgroups.append(subgroup)
#         subgroup.parent = self

#     def add_individual(self, individual):
#         self.individuals.append(individual)
#         individual.groups.append(self)

#     def remove_subgroup(self, subgroup):
#         self.subgroups.remove(subgroup)
#         subgroup.parent = None

#     def remove_individual(self, individual):
#         self.individuals.remove(individual)
#         individual.groups.remove(self)
    
#     def __str__(self):
#         return self.name

# # query_1 = ["name", {"structure":["despotic", "hierarchic", "teams", "decentralized", "anarchy"]}, "goals":[], "culture":[], "resources":[], "history":[]]

# def prompt_group(content):
#     pass

# import prompt as P
# import data_formatter as DF
# import query
# from parsers import json_parser

# Q = query.LLM_Query()

# PROJECT_ID = "A"
# LORE = """A medieval fantasy world, monotheist (the god is non-gendered and called "the Old One"), no undead, only one big empire on a unique continent the size of europe. """
# GROUP_DESCRIPTION =  "Near an ancient forest, a small village surrounded by a lush valley. Ruins can be found in the forest, and the village is near a river. Mountains can be seen in the distance. The village was founded centuries ago by groups of scholars and adventurers who came to study an event long forgotten. Heritage of the ancients settlers still remain faintly in the village, and the ruins of the ancient forest are still a mystery."



# content = DF.bootstrap_content(PROJECT_ID, LORE, "village", "local", 250, GROUP_DESCRIPTION, "medieval fantasy")
# prompt = P.prompt_group(content)
# new_content = Q.query(prompt, json_parser)



# # full_content: {
# #     groups: [],
# #     individuals: [],
# #     sites: [],
# #     events: [],
# # }

# # "culture":["militaristic", "religious", "industrial", "agricultural", "artisanal", "academic", "scientific", "exploratory", "adveturous", "mercantile", "mythological", "mystical", "magical"]

#     # place = {
#     #     "name": contents[0],
#     #     "biomes": contents[1],
#     #     "population": contents[2],
#     #     "count": int(''.join(filter(str.isdigit, contents[2]))),
#     #     "prosperity": contents[3],
#     #     "keywords": contents[4].split(", "),
#     #     "description": contents[5],
#     #     "history": contents[6],
#     #     "very_short_description": contents[7],
#     #     "anecdotes": [contents[8], contents[9], contents[10]],
#     #     "neighbors": contents[11]
#     # }

# # social_group = {
# #     type: "", # one of ["community", "family", "organization", "social_group", "religion", "business"]
# #     scale: "", # one of ["local", "regional", "national", "international", "global"]
# #     size: "", # number of members
# #     name: "",
# #     structure: "", # one of ["despotic", "hierarchic", "teams", "decentralized", "anarchy"] # from 1 man leading to no leader
# #     bootstrap_prompt: "", # short description of the group of people to build (dedicated to prompts)
# #     description: "", # description of the group of people to build
    
# #     history: "", # history of the group, anecdotes, plots, etc.
# #     context: "", # group of people revolving around the group (states, religions, cities, competitors, etc.) {interaction, influence}
# #     customs: "", # laws, customs, events, rituals, celebrations, habits, secret signs or languages, etc.
    
# #     sites: "", # places where the group is active (buildings, monuments, workplaces, hideouts, etc.)
# #     clusters: "", # recursively sub social groups inside the group (families, guilds, crews, friends, etc.) - should reflect the organisation of the group
# #     parent_group: "", # the group of people that contains the group (family, city, state, religion, etc.)
# #     individuals: [], # individuals that are part of the group (members, followers, etc.)
# # }

# # site {
# #     location: "",
# #     history: "",
# #     description: "",
# #     appearance: "",
# #     plots: [],
# # }

# # individual = {
# #     name: "",
# #     surname: "",
# #     nickname: "",
# #     age: "",
# #     appearance: {
# #         skin_color: "",
# #         hair_color: "",
# #         haircut: "",
# #         eyes: "",
# #         size: "",
# #         weight: "",
# #         clothes: ""
# #     },
# #     traits: [],
# #     groups: [
# #         id: {
# #             name: "",
# #             activity: "",
# #             rank: ""
# #         }
# #     ],
# #     relationships: [(type, person, intensity), (type, person, intensity), (type, person, intensity)],
    
    
# # }

# # social_group type = ["geographic area", "social group", "family", "organization", "religion", "business", "club", etc.] # the type of group of people to build
# # social_context # same as before, group of people revolving around the group
# # historical_context # history of the group, anecdotes, plots, etc.
# # laws_customs # laws and customs of the group (events, celebrations, rituals, etc.)
# # link: "", # link between individuals of the group ["common_place (community, town, country, etc.)", "common_blood (family, brothers in arms)", "common_goals (organization, political party, secret societies, etc.)", "common_traits (race, gender, age, social status, sexual orientation, etc.)", "common_beliefs (religion, cult, etc.)", "common_business (companies, guilds, military, etc.)"]
# # 