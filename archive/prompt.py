import json

import defines as D


def prompt_bootstrap(content): #TODO add prosperity
    prompt = f"""
I want to generate data for a {content["type"]}. The {content["type"]} exists in the following lore:
{content["lore"]["description"]}

The {content["type"]} exists at a {content["scale"]} scale and has a population of {content["size"]}. It can be described as follows:
{content["details"]["description"]}

From this information, I want you to generate a json object with the following keys:
{{
    "name": "", // an unexpected, original and {{content["lore"]["world_type"]}} name
    "structure": "", // 1 of [["despotism", "hierarchy", "democracy", "cooperative groups", "decentralized", "autonomous groups", "anarchy"]]
    "keywords": [], // 10 keywords that describe the {content["type"]}
    "lore keywords": [] // 6 keywords that describe the lore
    "culture": [], // 6 keywords that describe the {content["type"]} culture
    "customs": [], // 6 keywords that describe the {content["type"]} customs
    "goals" : [], // 6 keywords that describe the {content["type"]} goals
    "resources" : [], // 8 keywords that describe the {content["type"]} resources
    "history": [], // 6 keywords that describe the {content["type"]} history
    "external_influences": [], // 6 keywords that describe the {content["type"]} external influences such as other {content["type"]} or other groups and entities
    "timeline": [], // 6 keywords that describe events that happened to the {content["type"]} either one shot or recurring (rituals, celebrations, natural disasters, etc.)
    "sites": [], // keywords that describe the main sites related to the {content["type"]} (buildings, sites, points of interest, temples, etc.)
    "anecdotes": [], // 6 keywords that describe anecdotes related to the {content["type"]} (stories, legends, myths, etc.)
}}

Respect the number of keywords asked.
Your json object: """

    return prompt


categories_to_keep = {
    "customs": ["culture", "goals", "resources", "history", "timeline", "sites"],
    "resources": ["customs", "goals", "history", "external_influences", "timeline", "sites"],
    "history": ["customs", "goals", "resources", "external_influences", "timeline", "sites"],
    "external_influences": ["culture", "customs", "goals", "resources", "history", "timeline", "sites", "anecdotes"],
    "timeline": ["culture", "customs", "goals", "resources", "history", "external_influences", "sites"],
    "sites": ["customs", "goals", "resources", "history", "external_influences", "timeline", "anecdotes"],
    "anecdotes": ["customs", "goals", "resources", "history", "external_influences", "timeline", "sites"],
    "clusters": ["customs", "resources", "history", "goals", "external_influences", "sites"],
    "groups": ["lore", "details"],
    "workplaces": ["customs", "resources", "history", "goals", "external_influences", "sites"],
    "families": ["resources", "customs", "history", "timeline", "sites"],
}


def small_prompt_group(content, category=None):
    prompt_json = {
        "name": content["name"],
        "type": content["type"],
        "keywords": content["details"]["keywords"],
        "lore keywords": content["lore"]["keywords"],
        "people_count": content["size"],
        # "prosperity": content["prosperity"],
    }
    if category:
        for key in categories_to_keep[category]:
            prompt_json[key] = content[key]["keywords"]

    return prompt_json


def prompt_category(content, category):
    prompt_json = small_prompt_group(content, category)

    prompt = f"""
I have the following data that describes a {content["type"]}:
{json.dumps(prompt_json)}

In this context, I have the following information about the {category}:
{json.dumps(content[category]["keywords"])}

For every element of the {category}, I want you to generate a TEXT WITH 500 WORDS ! that describes specifically the element and taking into account all the information provided before.
I want your answer in a json object following this format:
{{"{category}": ["text_1","text_2","text_3", "etc.",]}}

Your json object:
"""

    return prompt

# Relationships = {
#     "Family": ["Ancient", "Parent", "Child", "Sibling", "Spouse", "Cousin"],
#     "Social": ["Crush", "Romantic partner", "Friend", "Rival", "Enemy", "Ally", "Acquaintance", "Frenemy"],
#     "Professional": ["Colleague", "Boss", "Employee", "Assistant", "Master", "Apprentice"]
# }



def prompt_workplaces(content):
    prompt_json = small_prompt_group(content, "clusters")
    cluster_count = content["size"] // D.MEAN_GROUP_SIZE
    
    prompt = f"""{content["name"]} is a {content["type"]} with {content["size"]} inhabitants. It is described in json as follows:
{json.dumps(prompt_json)}

I want you to generate all the active groups for the {content["size"]} members of the {content["type"]}. You should generate all the groups relevant to describe the {content["type"]} in the provided lore, with respect to the realism of the lore, the realism of a human society and the resources of {content["name"]}.
I want the group to have one of the following types: "family" (a group created around a family), "guild"(a group created around an activity), "cooperative" (union of multiple groups) or "company"(a group driven by one boss or few individuals and composed of employees or underlings).
It's for a roleplaying game also so bring up interesting stuff for potential plots.
Generate a table with {cluster_count} groups with the following columns:
|name (an original, credible, fantasy name)|activity|type|keywords: 5 keywords|members count|role in the {content["type"]}|sites or workplaces|structure(one of [["despotism", "hierarchy", "democracy", "cooperative groups", "decentralized", "autonomous groups", "anarchy"]])|prosperity|

Your table:
"""

    return prompt

def prompt_one_shot_pop(content):
    prompt_json = small_prompt_group(content)
    count = content["size"] // 2
    prompt = f"""I have a {content["type"]} described in json as follows:
{json.dumps(prompt_json)}
I want you to generate a table with half the most interesting inhabitants.
I want you to be creative, consistent with the background (tabletop medieval fantasy rpg) and I want you to generate individuals age and name to illustrate that they belong to groups, families, bands, guilds, etc. The individuals should be the ones traditionnaly found in a medieval setup (peasants, innkeepers, beggars, miners, etc.) and a few from fantasy rpg (warriors, wizards, priests, thieves, etc.) but you can add some originality. I particularly want you that you create local families and outsiders groups.

You will generate a table with 100 persons as rows with the following columns (one word per column):
|name|surname|age|gender|origin|situation|occupation|

your table with 100 rows:
"""
    return prompt

def prompt_wk2(content):
    prompt_json = small_prompt_group(content, "clusters")
    cluster_count = content["size"] // D.MEAN_GROUP_SIZE
    manual_count = int(content["size"] * 0.4)
    
    prompt = f"""{content["name"]} is a {content["type"]} with {content["size"]} inhabitants. It is described in json as follows:
{json.dumps(prompt_json)}

I want you to generate all the groups of individuals for the {content["size"]} members of the {content["type"]}. 
I want the group to have one of the following types: "family" (a group created around a family), "guild"(a group created around an activity), "cooperative" (union of multiple groups), "council" (reunion of individuals), "team" (a group of friends or colleagues) or "company"(a group driven by one boss or few individuals and composed of employees or underlings).

The groups should cover all aspect of the life of the {content["type"]} and be relevant to the medieval fantasy setup for a roleplaying game (no anachronisms, a majority of peasants, serfs and manual workers, but a very few artists, intellectuals, soldiers, etc.). Also, you should be careful to provide group realistic for the scale of the {content["type"]} (ie. no magical academy in a small village or no hospital in a settlement). Proportion and size of groups should be adequate with the medieval realities. The list should be exhaustive, no groups of {content["name"]} should be left out.
I want a list of groups for all the possible fields of activity: work, business, ideologies, religion, administration, community (a leading figure or council is mandatory), care, crews, bands, teams, hobbies, customs, secret societies, illegal activities, wanderers, adventurers, homeless, hermits, outcasts, etc. The size and proportion of various groups should reflect the lore and the size of the {content["type"]}.
The sum of population members count should be equal to the {content["size"]} inhabitants of {content["name"]} and there should be {cluster_count} groups.
Do not hesitate to generate multiple groups with the same activity (ie. multiple farming families or concurrent blacksmiths, etc.). Do not forget: {content["name"]} should have many farmers, peasants and related workers (around {manual_count}), many manual workers and just a few others people.
Be creative, realistic and bring up interesting stuff for potential plots.


For each category generate a table with the following columns:
name: a fantasy original and innovative name
activity: main activity of the group
type: one of [family, guild, cooperative, council, team or company]
field: the field of activity
keywords: 5 keywords
population: members count (should reflect the lore and the size of the {content["type"]})
prosperity: the prosperity of the group
composition: natives, outsiders or mix
ages: one of [old (mostly old people), mid, young, old_mix (olds and mid), young_mix (young and mid) or mix (all ages)]

for example a generated table could be:
|name|activity|type|field|keywords|population|part-time|composition|ages|
|church of piety|church|religion|company|["piety", "faith", "god", "prayer", "sacrifice"]|5|2|mix|olds|
|valley farmers|farming|business|cooperative|["farming", "agriculture", "crops", "harvest", "fields"]|60|50|natives|mix|
|vale sanitarium|health|care|company|["health", "medicine", "doctor", "nurse", "patient"]|3|1|mix|mid|
|the red hand|theft|crime|guild|["crime", "thief", "robbery", "assassin", "smuggling"]|3|0|outsiders|young_mix|
...

The generated table with {cluster_count} rows (one for each group):
"""

    return prompt



def small_workplaces(content):
    small_workplaces = []
    for workplace in content["workplaces"]:
        small_workplaces.append({
            "name": workplace["Name"],
            "keywords": workplace["Keywords"],
            "activity": workplace["Activity"],
        })

    return small_workplaces



import numpy as np
from numpy import random
from pynames.generators.iron_kingdoms import DwarfFullnameGenerator
from pynames.generators.elven import DnDNamesGenerator
from pynames.generators.iron_kingdoms import CaspianMidlunderSuleseFullnameGenerator, KhadoranFullnameGenerator, GobberFullnameGenerator, IossanNyssFullnameGenerator, ThurianFullnameGenerator, ThurianMorridaneFullnameGenerator, OgrunFullnameGenerator, MorridaneFullnameGenerator, TordoranFullnameGenerator, RynFullnameGenerator, TrollkinFullnameGenerator
from pynames import GENDER, LANGUAGE

ratio = {"human": 0.75, "elf": 0.05, "half-elf": 0.05, "dwarf": 0.1, "halfling": 0.025, "gnome": 0.025}
generators = {"human": CaspianMidlunderSuleseFullnameGenerator(), "elf": DnDNamesGenerator(), "half-elf": DnDNamesGenerator(), 
              "dwarf": DwarfFullnameGenerator(), "halfling": ThurianMorridaneFullnameGenerator(), "gnome": IossanNyssFullnameGenerator()}


def groups_distribution(population):
    gen_population = 0
    groups_size = []
    while gen_population < population:
        size = int(random.default_rng().laplace(5, 3, 1))
        if size <= 0:
            size = 1
        race = random.choice(list(ratio.keys()), p=list(ratio.values()))
        family_name = str(generators[race].get_name()).split(" ")[-1]
        groups_size.append({
            "name": family_name,
            "size": size,
            "race": race,
        })
        gen_population += size
    return groups_size


def prompts_groups_family(content):
    small_workplaces = []
    sum_workers = sum([int(workplace["Members Count"]) for workplace in content["workplaces"]])
    ratio = int(content["size"]) / sum_workers
    
    for workplace in content["workplaces"]:
        small_workplaces.append({
            "name": workplace["Name"],
            "activity": workplace["Activity"],
            "keywords": workplace["Keywords"],
            "members count": int(int(workplace["Members Count"])*ratio),
            "type": workplace["Type"],
        })
    groups = groups_distribution(content["size"])
    
    
    prompt = f"""
{content["name"]} is a {content["type"]} with {content["size"]} members. 
In {content["name"]}, there are the following active groups:
{json.dumps(small_workplaces)}
For each group I want you to generate the repartition of the members per employment and per skill level following the following format:

{{
    "workplace_name": {{employment: {{full_time: count, part_time: count, seasonal: count}}, skills: {{skill_level: count, skill_level: count, etc.}}}},
}}

For the skill_level, possible values are 'master', 'expert', 'professional', 'junior', 'novice', 'apprentice', 'assistant'.
For the employment take the activity into account.
If the count is 0, do not write it.
you json:
"""
    return prompt


### For human, add racial morphotype
def prompt_people_in_groups(content, group, workplace):
    prompt_json = small_prompt_group(content, "clusters")
    persons_str = "|name|surname|race|gender|generation|situation|beauty|\n"
    workplace_str = "" if workplace is None else f"""
Many if not all members of the groups work at the workplace "{workplace["name"]}" which deals with {workplace["activity"]} and is described with the following keywords: {workplace["keywords"]}."""

    for m in group["members"]:
        persons_str += f"""|{m["name"]}|{m["surname"]}|{m["race"]}|{m["gender"]}|{m["generation"]}|{m['situation']}|{m["beauty"]}|
"""
    prompt = f"""{content["name"]} is a {content["type"]} with {content["size"]} inhabitants. It is described in json as follows:
{json.dumps(prompt_json)}

In {content["name"]}, there is multiple groups of people, one of them being a group of type {group['type']} with {len(group["members"])} persons. The group is described in json as follows:
{json.dumps({"name":group["name"], "type":group["type"], "origin":group["origin"]})}
The name is the name of the family or a random name used as an id if the group is not a family. The origin indicates if the group is native of {content["name"]}.
{workplace_str}
I have a list of members for this group and I want you to generate new data and complete it.
The list:
{persons_str}

I want you to generate a table with the following columns for each member of the list:
name
key_figure: [yes, no] (if the person is one of the key figures of the group)
gender
situation: the given situation related to the main character of the group (usually father, boss, chief, etc.)
race
age: the exact age in years (In a family try to generate valid ages with generation gap between grandparents, parents, children and grandchildren. ie. a grandson should be a least 38 years younger than the father of the group)
rank: the position of the person in the group, not in the workplace [such as mentor, leader, family head, etc.]
description: few words describing the person in the group
traits: 4 traits
clothes: type - color - etc.
eyes: color
hair: color - length
skin: color - texture
height: one of [huge, tall, average, short, small]
weight: one of [fat, chubby, average, thin, skinny]
age_look: one of [older, old, middle-age, adult, young, younger, infant]
physical detail: "None" or a physical detail
nickname: nickname in the group
secret: a short secret
quote: a quote
relationship: short description of relationship with other members of the group
structure_preference: one of ["family", "guild", "cooperative", "council", "team", "company"]. It represents the type of structure or organization in which the person feels the most comfortable (usually close to the type of the group). "family" represents tight bounds, guild represents hierarchy, cooperative represents equality and share, council represents democracy, team represents a group of people working together, company represents a group of people working together for a common goal.

for example a person could be:
|name|surname|key_figure|gender|situation|race|age|rank|description|traits|clothes|eyes|hair|skin|height|weight|age_look|physical detail|nickname|secret|quote|relationship|structure_preference|
|Edd|Korok|yes|male|father|human|45|family chief|rude but kind guy from the countryside|honorable, loyal, lawful|leather blacksmith outfit|dark|long and grey|white|tall|average|old|scar on the left cheek|Edd|he is a bastard|let me work you useless prick|hates his father|guild|

So be original, realistic seeing the context (a medieval fantasy setup for a tabletop rpg).
Your completed list:
"""
    return prompt


def prompt_workplace_employees(content, wk, employees):
    prompt_json = small_prompt_group(content, "clusters")
    persons_str = "|name|race|gender|age|origin|description|traits|\n"
    for m in employees:
        persons_str += f"""|{m["fullname"]}|{m["race"]}|{m["gender"]}|{m["age"]}|{m['origin']}|{m["description"]}|{m["traits"]}|
"""
    
    prompt = f"""{content["name"]} is a {content["type"]} with {content["size"]} inhabitants. It is described in json as follows:
{json.dumps(prompt_json)}

In {content["name"]}, there is a place called {wk["name"]} where {int(wk["population"])} people work or live. The group is described in json as follows:
{json.dumps({"field":wk["field"], "activity":wk["activity"], "keywords":wk["keywords"], "prosperity":wk["prosperity"]})}

I have a list of members for this group (members that originate from family of {content["name"]} or from outside the {content["type"]}) and I want you to complete it.
The list:
{persons_str}


I want you to generate a table with the following columns for each member of the list:
name
key_figure: [yes, no] (if the person is a key figure of the place - at least one)
job: the job of the person
rank: [boss, apprentice, senior, etc.]
skill level: [master, expert, novice, etc.]
description: few words describing the person in the group
working_clothes: type - color - etc.
nickname: nickname at work (be creative)
quote: a quote related to the work
relations: short description of relationship with other members of the group

for example a person could be:
|name|key_figure|job|rank|skill level|description|working_clothes|nickname|quote|relations|
|ed Obart|yes|blacksmith|boss|master|rude but kind with apprentices|leather blacksmith outfit|the hammer|steel never lie|see Stephan as a son he never had|

So be original, realistic seeing the context (a medieval fantasy setup for a tabletop rpg).

Do not forget a column !
Your completed list:
"""
    return prompt


def prompt_workplace_details(content, wk, employees):
    prompt_json = small_prompt_group(content, "workplaces")
    persons_str = "|name|race|gender|age|origin|description|job|rank|skill|\n"
    for m in employees:
        persons_str += f"""|{m["fullname"]}|{m["race"]}|{m["gender"]}|{m["age"]}|{m['origin']}|{m["description"]}|{m["job"]}|m{"rank"}|m{"skill level"}|\n"""

    prompt = f"""{content["name"]} is a {content["type"]} with {content["size"]} inhabitants. It is described in json as follows:
{json.dumps(prompt_json)}

In {content["name"]}, there is a place called {wk["name"]} where {int(wk["population"])} people work or live. This group is described in json as follows:
{json.dumps({"field":wk["field"], "activity":wk["activity"], "keywords":wk["keywords"], "prosperity":wk["prosperity"]})}

I have the list of all the group members:
{persons_str}

From this data, I want you to generate a json object which describe in details the place/group following the structure:
{{
    "name": "", //the actual name of the group
    "new_name": "", // generate a new name that seems more appropriate with the newly generated data
    "desc": "", // a long description of the group
    "customs": "", // a paragraph describing the customs
    "goals_keywords" : [], // 4 keywords that describe the goals of the group
    "history": "", //short history of the group
    "relationship": "", //long description of relationship of the group with {content["name"]}
    "timeline": "", // 6 keywords that describe events that happened to the group either one shot or recurring (rituals, celebrations, natural disasters, etc.)
    "anecdotes": "", // 3 long anecdotes related to the group
    "sites": {{ // a small list (1 to 5) of sites related to the activities or the members of the group
        "site_name": [], // a list of keywords describing visually the site from an external point of view (for example: "small house, red roof, wooden walls, cosy, tall chimney")
        "site_name": [],
        etc.,
    }},
    "plot": "", // a list of long potential plots, stories or synopsis related to the group
}}

Respect the format !
Your json object: """
    return prompt



def prompt_architecture_and_sites(content):
    prompt_json = small_prompt_group(content, "workplaces")


    prompt = f"""{content["name"]} is a {content["type"]} with {content["size"]} inhabitants. It is described in json as follows:
{json.dumps(prompt_json)}
and in text as follows:
{content["details"]["description"]}

In {content["name"]}, there is {len(content["sites"]["keywords"])} sites. Described as follows:
{json.dumps(content["sites"]["keywords"])}
{json.dumps(content["sites"]["details"])}

For me to be able to draw those places, I want you to generate architectural information about {content["name"]} and about the sites. I want you to generate a json object with the following structure:
{{
    "architecture": "", // a list of 6 architectural keywords describing the visual style of {content["name"]} (for example: "tatched roof, wooden walls, small windows, etc.")
    "global_view": "", // a short visual description of {content["name"]} from an external point of view (for example: "a small colorful village in the middle of a lush forest")
    "global_view_detailed": "", // a long visual description of {content["name"]}. Includes details, colors, architecture, etc.
    "sites_keywords": {{ // for each site, a list of 6 architectural keywords describing the visual style et setup of the site (precise if the architecture is different from the main place and do not if it is the same)
        "site_name_1": [], //for example [isolated building, surrounded by fields, etc.]
        "site_name_2": [], //for example [stone walls, Timber-framed, slate roof, flowers, weeds, tall building]
        "site_name_3": [], //for example [clearing, water source, tall oak trees, etc.]
    }},
    "sites_details": {{ //for each site a very shot visual description
        "site_name_1": "", //for example "a small peasant house in the middle of the fields"
        "site_name_2": "", //for example "a tall building with a small garden"
        "site_name_3": "", //for example "a peaceful clearing in the middle of an oak forest"
    }}
}}

Your json object: """
    return prompt


def prompt_sites(content, wk, wk_details):
    prompt_json = small_prompt_group(content)

    prompt = f"""{content["name"]} is a {content["type"]} with {content["size"]} inhabitants. It is described in json as follows:
{json.dumps(prompt_json)}
and in text as follows:
{content["details"]["description"]}

{content["name"]} has the following architecture:
{json.dumps(content["architecture"]["architecture"])}
and the following sites:
{json.dumps(content["architecture"]["sites_keywords"])}


In {content["name"]}, there is a workplace called {wk["name"]} where {int(wk["population"])} people work or live. The workplace is described in json as follows:
{json.dumps({"field":wk["field"], "activity":wk["activity"], "keywords":wk["keywords"], "prosperity":wk["prosperity"]})}

{wk_details["name"]} workers use the following sites:
{json.dumps(wk_details["sites"])}

For me to be able to draw the {wk_details["name"]} places, I want you to generate architectural information about them (not the site of {content["name"]}, just the site for the workplace). I want you to generate a json object with the following structure:
{{
    "site_name": {{// the name of the site. It may happen that one of {wk_details["name"]} sites in actually a site of {content["name"]} and is already described. In this case, copy exactly the key of the site from {content["name"]}
        "architecture": "", a list of 6 architectural keywords describing the visual style et setup of the site that may be inspired by {content["name"]} //for example [isolated building, surrounded by fields, etc.]
        "details": "", //a very shot visual description: for example  "a small peasant hut in the middle of the fields"
        "type": "", // the type of the site, ie. "building", "inn", "street", "landscape", "forest", etc.
        "state": "", // the state of the site, ie. "ruins", "abandoned", "inhabited", "under construction", etc.
        "inherits_architecture": "", // a boolean that is true if the architecture of the site is the same style as the architecture of {content["name"]}
    }},
    etc.
}}

Your json object: """
    return prompt



def prompt_member_details(content, mb, colleagues, family, workplace):
    prompt_json = small_prompt_group(content)
    colleagues_str = "\n".join([f"""|{colleague["fullname"]}|{colleague["job"]}|{colleague["rank"]}|{colleague["description"]}|""" for colleague in colleagues])# if colleague["fullname"] != mb["fullname"]])
    family_str = "\n".join([f"""|{member['fullname']}|{member['rank']}|{member['age']} yo|{member['situation']}|{member['description']}|{member['traits']}|""" for member in family["members"] if "rank" in member])
    

    prompt = f"""{content["name"]} is a {content["type"]} with {content["size"]} inhabitants. It is described in json as follows:
{json.dumps(prompt_json)}

{mb["fullname"]} is a inhabitant of {content["name"]} and is described in json as follows:
{json.dumps(mb)}

{mb["fullname"]} works at {workplace["name"]} which described as follows:
{json.dumps(workplace)}
The list of all the {workplace["name"]} employees is:
{colleagues_str}

The group in which {mb["fullname"]} live is a group with origins:{family["origin"]} and is of type {family["type"]}. Its only members are:
{family_str}

Be careful, the group is the main source of background info for the character. All the info is here which means that you cannot generate new characters such as siblings or parents.

From this data, I want you to generate a json object which describe in details {mb["name"]} following the structure:
{{
    "fullname": "", //repeat the fullname of the member
    "desc": "", // a long description of {mb["name"]} and its life in {content["name"]}
    "habits": "", // a paragraph describing the habits of {mb["name"]}
    "goals_keywords" : [], // 4 keywords that describe the goals of {mb["name"]}
    "history": "", //a long history of {mb["name"]} (take into account particularly the group where {mb["name"]} lives and its origins)
    "anecdotes": [], // anecdotes related to {mb["name"]}
    "plot": [], // a paragraph per potential plots related to {mb["name"]}. Be precise and explicit.
    "relationship": {{ // A description of the relationship between {mb["name"]} and the persons he may know in {content["name"]} (workplace or living group)
        "person_name": "", //a description of the relationship between {mb["name"]} and the person (taken from the family or the colleagues)
        ...
    }}
}}

Your json object: """
    return prompt
