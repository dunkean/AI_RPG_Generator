import json
import defines as D


def bootstrap(content):
    details = content["details"]
    setting = content["setting"]
    
    prompt = f"""
I want to generate json data for a fictional {details["type"]} in a {setting["type"]} setting. The setting is described as follows:
{setting["description"]}

The {details["type"]} is described as follows:
{details["description"]}


From this information, I want you to generate the missing values of the following json data:
{{
    "name": "{details.get("name", "")}", // an unexpected, original and {setting["type"]} name
    "keywords": {details.get("keywords", "[]")}", // 10 keywords that describe the {details["type"]}
    "setting_setting": {setting.get("keywords", "[]")} // 10 keywords that describe the setting in detail
    "influence_areas": {details.get("influence_areas", "[]")}", // a list of areas where the {details["type"]} has influence
    "structure": "{details.get("structure", "")}", // 1 of [["despotism" (1 ruler), "hierarchy" (pyramidal), "democracy", "collaborative" (cooperative groups), "decentralized" ("autonomous groups"), anarchy"]]
    "prosperity": "{details.get("prosperity", "")}", // 1 of [["poor", "low", "medium", "high", "wealthy"]]
    "culture": {details.get("culture", "[]")}, // 6 keywords that describe the {details["type"]} culture
    "customs": {details.get("customs", "[]")}, // 6 keywords that describe the {details["type"]} customs
    "goals" : {details.get("goals", "[]")}, // 6 keywords that describe the {details["type"]} goals
    "resources" : {details.get("resources", "[]")}, // 8 keywords that describe the {details["type"]} resources
    "history": {details.get("history", "[]")}, // 6 keywords that describe the {details["type"]} history
    "external_influences": {details.get("external_influences", "[]")}, // 10 keywords that describe the {details["type"]} external influences such as other {details["type"]} or other groups and entities
    "timeline": {details.get("timeline", "[]")}, // 6 keywords that describe events that happened to the {details["type"]} either one shot or recurring (rituals, celebrations, natural disasters, etc.)
    "sites": {details.get("sites", "[]")}, // 5 keywords that describe the main sites related to the {details["type"]} (buildings, sites, points of interest, temples, etc.)
    "anecdotes": {details.get("anecdotes", "[]")}, // 6 keywords that describe anecdotes related to the {details["type"]} (stories, legends, myths, etc.)
    "races": {details.get("anecdotes", "{}")}, //a dict with all the races of the {details["type"]} and their respective population. ie. {{"black": 0.5, "asian":0.2, "amerindian": 0.05, "white": 0.2}} or {{"human": 0.75, "dwarf": 0.1, "elf": 0.1, "halfling": 0.05}} - depending on the setting and potential races.
    "member_bonds": {details.get("member_bonds", "{}")}, // a dict with thre proportions of types of bonds between members and their respective population. Types of possible bonds are [family, friends, colleagues (common employer), allies (common enemy), strangers, common goal, common status (ie. race, beliefs, place, etc.)]. keep only the relevant ones. ie. {{"family": 0.5, "friends:0.2", "colleagues": 0.05, "strangers": 0.2, "common goal": 0.05}}
}}

Please comply with the number of keywords asked.
Your json: """
    return prompt


categories_to_keep = {
    "description": {"details": ["culture", "customs", "goals", "resources", "history", "external_influences", "timeline", "anecdotes"]},
    "culture": {"details": ["culture", "customs", "goals", "resources", "history", "external_influences", "timeline", "anecdotes"]},
    "customs": {"details": ["customs", "goals", "resources", "history", "external_influences", "timeline", "anecdotes"]},
    "goals": {"details": ["customs", "goals", "resources", "history", "external_influences", "timeline", "anecdotes"]},
    "resources": {"details": ["customs", "goals", "resources", "history", "external_influences", "timeline", "anecdotes"]},
    "history": {"details": ["customs", "goals", "resources", "history", "external_influences", "timeline", "anecdotes"]},
    "external_influences": {"details": ["customs", "goals", "resources", "history", "external_influences", "timeline", "anecdotes"]},
    "timeline": {"details": ["customs", "goals", "resources", "history", "external_influences", "timeline", "anecdotes"]},
    "sites": {"details": ["customs", "goals", "resources", "history", "external_influences", "timeline", "anecdotes"]},
    "anecdotes": {"details": ["customs", "goals", "resources", "history", "external_influences", "timeline", "anecdotes"]},
    #
    "activity_groups": {"details": ["customs", "goals", "resources"]},
    # "groups": ["lore", "details"],
    "workplaces": {"details": ["customs", "resources", "history", "goals", "external_influences", "sites"]},
    "families": {"details": ["resources", "customs", "history", "timeline", "sites"]},
}


def context_json(content, category=None):
    details = content["details"]
    prompt_json = {
        "name": details["name"],
        "type": details["type"],
        "structure": details["structure"],
        "keywords": details["keywords"],
        "setting": content["setting"]["keywords"],
        "population": details["population"],
        "prosperity": details["prosperity"],
    }

    # cat_list = ["culture", "customs", "goals", "resources", "history", "external_influences", "timeline", "anecdotes"]
    # for key in cat_list:
    if category:
        for key, val in categories_to_keep[category].items():
            for v in val:
                prompt_json[v] = content[key][v]["keywords"]

    return prompt_json


def detail(content, category):
    details = content["details"]
    context = context_json(content, category)

    prompt = f"""
{details["name"]} is a {details["type"]} in a {content["setting"]["type"]} context. It is described in json as follows :
{json.dumps(context)}

Base on all this information, I want you to write for every keyword of the {category} of the {details["name"]}:
- section title: a meaningful title that use the keyword (ie. the keyword "war" could be transformed in "A long tradition of war", or "Love" in "Love is all around", depending on the category, context and keywords.)
- paragraph: a long text that describe in great details keyword in the {category} of the {details["name"]}".

I want you to format your response as a json object with the following structure:

{{ {category}: {{
    "a section title (not only the keyword)": "the long paragraph 1",
    "a section title (not only the keyword)": "the long paragraph 2",
    "etc.": "etc.",
    }} }}

Your json object:
"""

    return prompt


def description(content):
    details = content["details"]
    context = context_json(content, "description")

    prompt = f"""
{details["name"]} is a {details["type"]} in a {content["setting"]["type"]} context. It is described in json as follows :
{json.dumps(context)}

In natural language, {details["name"]} is described as follows:
{details["description"]}

I want you to rewrite the description in two parts:
1- a short description in 50 words,
2- a long description of {details["name"]} following the "keywords", using literary style organized as follow:
- section title: a meaningful title that use the keyword (ie. the keyword "war" could be transformed in "A long tradition of war", or "Love" in "Love is all around", depending on the category, context and keywords.)
- paragraph: a long text that describe in great details the {details["name"]}" based on the keyword.

You will follow this json structure:

{{ "descriptions": {{
    "short": "a short description of {details["name"]}",
    "long": {{
        "paragraph 1 title": "a long paragraph",
        "paragraph 2 title": "a long paragraph",
        "etc.": "etc.",
    }}
}}}}

Your json object:
"""

    return prompt


def external_influences(content):
    details = content["details"]
    context = context_json(content, "external_influences")

    prompt = f"""
{details["name"]} is a {details["type"]} in a {content["setting"]["type"]} context. It is described in json as follows :
{json.dumps(context)}

Base on all this information, I want you to generate information for every external influence.
I want you to format your response as a json object with the following structure:

{{ "External influence name": {{
    "type": "", // the type of the external influence (ie. village, gang, guild, cult, etc.)
    "scale": "", // the scale of the external influence (ie. local, regional, global, pervasive, etc.)
    "description": "", // a long detailed description of the external influence (100 words)
    "keywords": [], // a list of 8 keywords describing the external influence
    "population": int, // generate the count of individuals or entities belonging to this external influence or interacts with {details["name"]}
    "relationship": "", // a long description of the relationship between the external influence and the {details["name"]} (300 words)
    }} }}

Your json object:
"""

    return prompt

#############################################


def activity_groups(content):
    details = content["details"]
    context = context_json(content, "activity_groups")
    nb_sub_groups = details["population"] // D.MEAN_GROUP_SIZE

    prompt = f"""
{details["name"]} is a {details["type"]} in a {content["setting"]["type"]} context. It is described in json as follows :
{json.dumps(context)}

I want you to generate a table with all the sub-groups (between {int(nb_sub_groups)} and {int(nb_sub_groups * 1.5)}) that compose the {details["name"]} and sort them by activities. Activities mean an occupation that can be a full-time occupation for members of {details["name"]}.  The sub-groups should include all the possible activities leadership, services, crafting, factions, criminals, resources, trade, etc., (but not the {details["name"]} group itself). 
When generating all sub-groups that of the {details["name"]}, you should take into account the structure {details["structure"]} of the {details["name"]}.

To generate those sub-groups do that, you will use the following columns:
- name: (ie. "the blacksmiths", "the dead skulls", etc.)
- activity: the activity of the subgroup (ie. "blacksmith", "techies", "fighters", "administrators", etc.) within the {details["name"]}.
- type: the global type of the subgroup
- keywords: a list of 5 keywords describing the group
- motivations: a list of 5 keywords describing what activities motivate the members to be in this particular group
- role: the role of the subgroup in the {details["name"]}
- structure: the leadership structure of the group,  // 1 of [["despotism" (1 ruler), "hierarchy" (pyramidal), "democracy", "collaborative" (cooperative groups), "decentralized" ("autonomous groups"), anarchy"]]
- population: int, the number of people in the group
- prosperity: the prosperity of the group (ie. "poor", "average", "rich", "very rich", etc.)
- origin: {{local:float, foreign:float}} // the origin repartition in the group - between 0 and 1 (local being from the same place as the {details["name"]} and foreign being from outside)
- age_ratio:{{child:float, teen:float, adult:float, middle-aged:float, old:float}} // the age repartition in the group - between 0 and 1
- common_bonds: [] // a list of the 4 main bonds of the groups (ordered per importance). Bonds represent what members of the group have in common (ie. blood for family business, ideology for a cult, or cause for a rebel militia, etc.). Commons bonds are only of types: blood, friendship, business, cause (enemy, goals, dreams, etc.), identity (race, gender, status, etc.), ideology (beliefs, philosophy, etc.), knowledge (school, etc.), place (originates from the same place), past (shared history), interests (hobbies, etc.).

The sum of the population of all the sub-groups should be equal to the population of the {details["name"]}.
The table should have exactly the following columns:

| name | activity | type | keywords | motivations | role | structure | population | prosperity | origin | age_ratio | common_bonds |

your table:
"""

    return prompt


    # "blood": 0.9,
    # "interests": 0.8,
    # "business": 0.7,
    # "enemy": -0.9,
    # "cause": 0.6,
    # "identity": 0.5,
    # "ideology": 0.4,
    # "past": 0.3,
    # "knowledge": 0.2,
    # "place": 0.1,
    # "friendship": 0.05
    
# That's a very broad and difficult question. There are many possible ways to classify groups of people based on affinity, and there is no definitive or exhaustive list. However, based on my previous lists and some additional research, here is one possible list of categories for groups based on affinity:

# - **Common blood**: Groups based on genetic or biological ties, such as family, relatives, blood type, bloodline, etc.
# - **Common interests**: Groups based on shared hobbies, passions, or activities, such as book club, chess club, knitting club, etc.
# - **Common occupation**: Groups based on shared occupation, profession, or function, such as department, project team, union, etc.
# - **Common enemy**: Groups based on shared opposition or conflict with another group or entity, such as resistance group, alliance, coalition, etc.
# - **Common cause**: Groups based on shared objective or purpose, such as charity group, campaign group, support group, etc.
# - **Common status**: Groups based on shared social or professional position or rank, such as social class, level, role, etc.
# - **Common ideology**: Groups based on shared beliefs, values, or principles, such as political party, religious group, social movement, etc.
# - **Common past**: Groups based on shared history or experience, such as alumni group, reunion group, veterans group, etc.
# - **Common knowledge**: Groups based on shared information or skills, such as study group, trivia group, quiz group, etc.
# - **Common caring**: Groups based on shared affection or concern for others, such as family, friends, caregivers, volunteers, etc.
# - **Common place**: Groups based on shared location or origin, such as neighborhood association, community group, country club, etc.
# - **Common friendship**: Groups based on shared bond or connection with others, such as friends, buddies, pals, etc.

#Common identity: Groups based on shared characteristics or traits that define who they are, such as gender, race, ethnicity, sexual orientation, disability, etc.
# Common culture: Groups based on shared customs, traditions, languages, or values that define how they live, such as religion, nationality, ethnicity, region, etc.
# Common occupation: Groups based on shared work or profession that define what they do, such as department, project team, union, profession, etc.
# Common cause: Groups based on shared mission or vision that define why they do what they do, such as charity group, campaign group, support group, etc.
# Common challenge: Groups based on shared problem or difficulty that they face or overcome, such as enemy group, resistance group, alliance group, etc.
# Common interest: Groups based on shared hobbies, passions, or activities that they enjoy or pursue, such as book club, chess club, knitting club, etc.
# Common learning: Groups based on shared information or skills that they acquire or share, such as study group, trivia group, quiz group, etc.
# Common fun: Groups based on shared bond or connection that they have or create with others, such as friends, buddies, pals, etc.
# This is not a perfect or complete list. There may be other categories that are not included here. There may also be some overlap or ambiguity between some categories. For example, some groups may have more than one affinity or fit into more than one category. Some categories may be too broad or too narrow to capture the diversity of groups within them. Some categories may be subjective or dependent on context. Therefore, this list should be taken as a tentative and flexible suggestion rather than a definitive and rigid answer. I hope this helps you with your problem. Do you have any feedback or questions?

# - type: the global type of the subgroup that describe the bonds between members. One of [solo, duo, family (family business, etc.), friends, tribe (multiple families), cooperative (multiples groups), colleagues (people working together), employees (people working under the same boss), followers (people following the same person or belief), servants (people forced to work together), club (people having something in common), race]
# - member_motivation: {{family:float, friends:float, business:float, allies:float, common goal:float, common status:float}}, // a dict with the proportions of types of motivation among the members to be in the group. Types of possible bonds are [family, friends, business (money or employer), allies (common enemy), common goal, common status (ie. race, beliefs, place, etc.)]. keep only the relevant ones. ie. {{"family": 0.5, "friends:0.2", "colleagues": 0.05, "strangers": 0.2, "common goal": 0.05}}

# def small_workplaces(content):
#     small_workplaces = []
#     for workplace in content["workplaces"]:
#         small_workplaces.append({
#             "name": workplace["Name"],
#             "keywords": workplace["Keywords"],
#             "activity": workplace["Activity"],
#         })

#     return small_workplaces



# import numpy as np
# from numpy import random
# from pynames.generators.iron_kingdoms import DwarfFullnameGenerator
# from pynames.generators.elven import DnDNamesGenerator
# from pynames.generators.iron_kingdoms import CaspianMidlunderSuleseFullnameGenerator, KhadoranFullnameGenerator, GobberFullnameGenerator, IossanNyssFullnameGenerator, ThurianFullnameGenerator, ThurianMorridaneFullnameGenerator, OgrunFullnameGenerator, MorridaneFullnameGenerator, TordoranFullnameGenerator, RynFullnameGenerator, TrollkinFullnameGenerator
# from pynames import GENDER, LANGUAGE

# ratio = {"human": 0.75, "elf": 0.05, "half-elf": 0.05, "dwarf": 0.1, "halfling": 0.025, "gnome": 0.025}
# generators = {"human": CaspianMidlunderSuleseFullnameGenerator(), "elf": DnDNamesGenerator(), "half-elf": DnDNamesGenerator(), 
#               "dwarf": DwarfFullnameGenerator(), "halfling": ThurianMorridaneFullnameGenerator(), "gnome": IossanNyssFullnameGenerator()}


# def groups_distribution(population):
#     gen_population = 0
#     groups_size = []
#     while gen_population < population:
#         size = int(random.default_rng().laplace(5, 3, 1))
#         if size <= 0:
#             size = 1
#         race = random.choice(list(ratio.keys()), p=list(ratio.values()))
#         family_name = str(generators[race].get_name()).split(" ")[-1]
#         groups_size.append({
#             "name": family_name,
#             "size": size,
#             "race": race,
#         })
#         gen_population += size
#     return groups_size


# def prompts_groups_family(content):
#     small_workplaces = []
#     sum_workers = sum([int(workplace["Members Count"]) for workplace in content["workplaces"]])
#     ratio = int(content["size"]) / sum_workers
    
#     for workplace in content["workplaces"]:
#         small_workplaces.append({
#             "name": workplace["Name"],
#             "activity": workplace["Activity"],
#             "keywords": workplace["Keywords"],
#             "members count": int(int(workplace["Members Count"])*ratio),
#             "type": workplace["Type"],
#         })
#     groups = groups_distribution(content["size"])
    
    
#     prompt = f"""
# {content["name"]} is a {content["type"]} with {content["size"]} members. 
# In {content["name"]}, there are the following active groups:
# {json.dumps(small_workplaces)}
# For each group I want you to generate the repartition of the members per employment and per skill level following the following format:

# {{
#     "workplace_name": {{employment: {{full_time: count, part_time: count, seasonal: count}}, skills: {{skill_level: count, skill_level: count, etc.}}}},
# }}

# For the skill_level, possible values are 'master', 'expert', 'professional', 'junior', 'novice', 'apprentice', 'assistant'.
# For the employment take the activity into account.
# If the count is 0, do not write it.
# you json:
# """
#     return prompt


# ### For human, add racial morphotype
# def prompt_people_in_groups(content, group, workplace):
#     prompt_json = small_prompt_group(content, "clusters")
#     persons_str = "|name|surname|race|gender|generation|situation|beauty|\n"
#     workplace_str = "" if workplace is None else f"""
# Many if not all members of the groups work at the workplace "{workplace["name"]}" which deals with {workplace["activity"]} and is described with the following keywords: {workplace["keywords"]}."""

#     for m in group["members"]:
#         persons_str += f"""|{m["name"]}|{m["surname"]}|{m["race"]}|{m["gender"]}|{m["generation"]}|{m['situation']}|{m["beauty"]}|
# """
#     prompt = f"""{content["name"]} is a {content["type"]} with {content["size"]} inhabitants. It is described in json as follows:
# {json.dumps(prompt_json)}

# In {content["name"]}, there is multiple groups of people, one of them being a group of type {group['type']} with {len(group["members"])} persons. The group is described in json as follows:
# {json.dumps({"name":group["name"], "type":group["type"], "origin":group["origin"]})}
# The name is the name of the family or a random name used as an id if the group is not a family. The origin indicates if the group is native of {content["name"]}.
# {workplace_str}
# I have a list of members for this group and I want you to generate new data and complete it.
# The list:
# {persons_str}

# I want you to generate a table with the following columns for each member of the list:
# name
# key_figure: [yes, no] (if the person is one of the key figures of the group)
# gender
# situation: the given situation related to the main character of the group (usually father, boss, chief, etc.)
# race
# age: the exact age in years (In a family try to generate valid ages with generation gap between grandparents, parents, children and grandchildren. ie. a grandson should be a least 38 years younger than the father of the group)
# rank: the position of the person in the group, not in the workplace [such as mentor, leader, family head, etc.]
# description: few words describing the person in the group
# traits: 4 traits
# clothes: type - color - etc.
# eyes: color
# hair: color - length
# skin: color - texture
# height: one of [huge, tall, average, short, small]
# weight: one of [fat, chubby, average, thin, skinny]
# age_look: one of [older, old, middle-age, adult, young, younger, infant]
# physical detail: "None" or a physical detail
# nickname: nickname in the group
# secret: a short secret
# quote: a quote
# relationship: short description of relationship with other members of the group
# structure_preference: one of ["family", "guild", "cooperative", "council", "team", "company"]. It represents the type of structure or organization in which the person feels the most comfortable (usually close to the type of the group). "family" represents tight bounds, guild represents hierarchy, cooperative represents equality and share, council represents democracy, team represents a group of people working together, company represents a group of people working together for a common goal.

# for example a person could be:
# |name|surname|key_figure|gender|situation|race|age|rank|description|traits|clothes|eyes|hair|skin|height|weight|age_look|physical detail|nickname|secret|quote|relationship|structure_preference|
# |Edd|Korok|yes|male|father|human|45|family chief|rude but kind guy from the countryside|honorable, loyal, lawful|leather blacksmith outfit|dark|long and grey|white|tall|average|old|scar on the left cheek|Edd|he is a bastard|let me work you useless prick|hates his father|guild|

# So be original, realistic seeing the context (a medieval fantasy setup for a tabletop rpg).
# Your completed list:
# """
#     return prompt


# def prompt_workplace_employees(content, wk, employees):
#     prompt_json = small_prompt_group(content, "clusters")
#     persons_str = "|name|race|gender|age|origin|description|traits|\n"
#     for m in employees:
#         persons_str += f"""|{m["fullname"]}|{m["race"]}|{m["gender"]}|{m["age"]}|{m['origin']}|{m["description"]}|{m["traits"]}|
# """
    
#     prompt = f"""{content["name"]} is a {content["type"]} with {content["size"]} inhabitants. It is described in json as follows:
# {json.dumps(prompt_json)}

# In {content["name"]}, there is a place called {wk["name"]} where {int(wk["population"])} people work or live. The group is described in json as follows:
# {json.dumps({"field":wk["field"], "activity":wk["activity"], "keywords":wk["keywords"], "prosperity":wk["prosperity"]})}

# I have a list of members for this group (members that originate from family of {content["name"]} or from outside the {content["type"]}) and I want you to complete it.
# The list:
# {persons_str}


# I want you to generate a table with the following columns for each member of the list:
# name
# key_figure: [yes, no] (if the person is a key figure of the place - at least one)
# job: the job of the person
# rank: [boss, apprentice, senior, etc.]
# skill level: [master, expert, novice, etc.]
# description: few words describing the person in the group
# working_clothes: type - color - etc.
# nickname: nickname at work (be creative)
# quote: a quote related to the work
# relations: short description of relationship with other members of the group

# for example a person could be:
# |name|key_figure|job|rank|skill level|description|working_clothes|nickname|quote|relations|
# |ed Obart|yes|blacksmith|boss|master|rude but kind with apprentices|leather blacksmith outfit|the hammer|steel never lie|see Stephan as a son he never had|

# So be original, realistic seeing the context (a medieval fantasy setup for a tabletop rpg).

# Do not forget a column !
# Your completed list:
# """
#     return prompt


# def prompt_workplace_details(content, wk, employees):
#     prompt_json = small_prompt_group(content, "workplaces")
#     persons_str = "|name|race|gender|age|origin|description|job|rank|skill|\n"
#     for m in employees:
#         persons_str += f"""|{m["fullname"]}|{m["race"]}|{m["gender"]}|{m["age"]}|{m['origin']}|{m["description"]}|{m["job"]}|m{"rank"}|m{"skill level"}|\n"""

#     prompt = f"""{content["name"]} is a {content["type"]} with {content["size"]} inhabitants. It is described in json as follows:
# {json.dumps(prompt_json)}

# In {content["name"]}, there is a place called {wk["name"]} where {int(wk["population"])} people work or live. This group is described in json as follows:
# {json.dumps({"field":wk["field"], "activity":wk["activity"], "keywords":wk["keywords"], "prosperity":wk["prosperity"]})}

# I have the list of all the group members:
# {persons_str}

# From this data, I want you to generate a json object which describe in details the place/group following the structure:
# {{
#     "name": "", //the actual name of the group
#     "new_name": "", // generate a new name that seems more appropriate with the newly generated data
#     "desc": "", // a long description of the group
#     "customs": "", // a paragraph describing the customs
#     "goals_keywords" : [], // 4 keywords that describe the goals of the group
#     "history": "", //short history of the group
#     "relationship": "", //long description of relationship of the group with {content["name"]}
#     "timeline": "", // 6 keywords that describe events that happened to the group either one shot or recurring (rituals, celebrations, natural disasters, etc.)
#     "anecdotes": "", // 3 long anecdotes related to the group
#     "sites": {{ // a small list (1 to 5) of sites related to the activities or the members of the group
#         "site_name": [], // a list of keywords describing visually the site from an external point of view (for example: "small house, red roof, wooden walls, cosy, tall chimney")
#         "site_name": [],
#         etc.,
#     }},
#     "plot": "", // a list of long potential plots, stories or synopsis related to the group
# }}

# Respect the format !
# Your json object: """
#     return prompt



# def prompt_architecture_and_sites(content):
#     prompt_json = small_prompt_group(content, "workplaces")


#     prompt = f"""{content["name"]} is a {content["type"]} with {content["size"]} inhabitants. It is described in json as follows:
# {json.dumps(prompt_json)}
# and in text as follows:
# {content["details"]["description"]}

# In {content["name"]}, there is {len(content["sites"]["keywords"])} sites. Described as follows:
# {json.dumps(content["sites"]["keywords"])}
# {json.dumps(content["sites"]["details"])}

# For me to be able to draw those places, I want you to generate architectural information about {content["name"]} and about the sites. I want you to generate a json object with the following structure:
# {{
#     "architecture": "", // a list of 6 architectural keywords describing the visual style of {content["name"]} (for example: "tatched roof, wooden walls, small windows, etc.")
#     "global_view": "", // a short visual description of {content["name"]} from an external point of view (for example: "a small colorful village in the middle of a lush forest")
#     "global_view_detailed": "", // a long visual description of {content["name"]}. Includes details, colors, architecture, etc.
#     "sites_keywords": {{ // for each site, a list of 6 architectural keywords describing the visual style et setup of the site (precise if the architecture is different from the main place and do not if it is the same)
#         "site_name_1": [], //for example [isolated building, surrounded by fields, etc.]
#         "site_name_2": [], //for example [stone walls, Timber-framed, slate roof, flowers, weeds, tall building]
#         "site_name_3": [], //for example [clearing, water source, tall oak trees, etc.]
#     }},
#     "sites_details": {{ //for each site a very shot visual description
#         "site_name_1": "", //for example "a small peasant house in the middle of the fields"
#         "site_name_2": "", //for example "a tall building with a small garden"
#         "site_name_3": "", //for example "a peaceful clearing in the middle of an oak forest"
#     }}
# }}

# Your json object: """
#     return prompt


# def prompt_sites(content, wk, wk_details):
#     prompt_json = small_prompt_group(content)

#     prompt = f"""{content["name"]} is a {content["type"]} with {content["size"]} inhabitants. It is described in json as follows:
# {json.dumps(prompt_json)}
# and in text as follows:
# {content["details"]["description"]}

# {content["name"]} has the following architecture:
# {json.dumps(content["architecture"]["architecture"])}
# and the following sites:
# {json.dumps(content["architecture"]["sites_keywords"])}


# In {content["name"]}, there is a workplace called {wk["name"]} where {int(wk["population"])} people work or live. The workplace is described in json as follows:
# {json.dumps({"field":wk["field"], "activity":wk["activity"], "keywords":wk["keywords"], "prosperity":wk["prosperity"]})}

# {wk_details["name"]} workers use the following sites:
# {json.dumps(wk_details["sites"])}

# For me to be able to draw the {wk_details["name"]} places, I want you to generate architectural information about them (not the site of {content["name"]}, just the site for the workplace). I want you to generate a json object with the following structure:
# {{
#     "site_name": {{// the name of the site. It may happen that one of {wk_details["name"]} sites in actually a site of {content["name"]} and is already described. In this case, copy exactly the key of the site from {content["name"]}
#         "architecture": "", a list of 6 architectural keywords describing the visual style et setup of the site that may be inspired by {content["name"]} //for example [isolated building, surrounded by fields, etc.]
#         "details": "", //a very shot visual description: for example  "a small peasant hut in the middle of the fields"
#         "type": "", // the type of the site, ie. "building", "inn", "street", "landscape", "forest", etc.
#         "state": "", // the state of the site, ie. "ruins", "abandoned", "inhabited", "under construction", etc.
#         "inherits_architecture": "", // a boolean that is true if the architecture of the site is the same style as the architecture of {content["name"]}
#     }},
#     etc.
# }}

# Your json object: """
#     return prompt



# def prompt_member_details(content, mb, colleagues, family, workplace):
#     prompt_json = small_prompt_group(content)
#     colleagues_str = "\n".join([f"""|{colleague["fullname"]}|{colleague["job"]}|{colleague["rank"]}|{colleague["description"]}|""" for colleague in colleagues])# if colleague["fullname"] != mb["fullname"]])
#     family_str = "\n".join([f"""|{member['fullname']}|{member['rank']}|{member['age']} yo|{member['situation']}|{member['description']}|{member['traits']}|""" for member in family["members"] if "rank" in member])
    

#     prompt = f"""{content["name"]} is a {content["type"]} with {content["size"]} inhabitants. It is described in json as follows:
# {json.dumps(prompt_json)}

# {mb["fullname"]} is a inhabitant of {content["name"]} and is described in json as follows:
# {json.dumps(mb)}

# {mb["fullname"]} works at {workplace["name"]} which described as follows:
# {json.dumps(workplace)}
# The list of all the {workplace["name"]} employees is:
# {colleagues_str}

# The group in which {mb["fullname"]} live is a group with origins:{family["origin"]} and is of type {family["type"]}. Its only members are:
# {family_str}

# Be careful, the group is the main source of background info for the character. All the info is here which means that you cannot generate new characters such as siblings or parents.

# From this data, I want you to generate a json object which describe in details {mb["name"]} following the structure:
# {{
#     "fullname": "", //repeat the fullname of the member
#     "desc": "", // a long description of {mb["name"]} and its life in {content["name"]}
#     "habits": "", // a paragraph describing the habits of {mb["name"]}
#     "goals_keywords" : [], // 4 keywords that describe the goals of {mb["name"]}
#     "history": "", //a long history of {mb["name"]} (take into account particularly the group where {mb["name"]} lives and its origins)
#     "anecdotes": [], // anecdotes related to {mb["name"]}
#     "plot": [], // a paragraph per potential plots related to {mb["name"]}. Be precise and explicit.
#     "relationship": {{ // A description of the relationship between {mb["name"]} and the persons he may know in {content["name"]} (workplace or living group)
#         "person_name": "", //a description of the relationship between {mb["name"]} and the person (taken from the family or the colleagues)
#         ...
#     }}
# }}

# Your json object: """
#     return prompt
