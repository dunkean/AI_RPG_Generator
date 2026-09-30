"""Workplace-related prompts — Steps 4, 8, 9."""

from __future__ import annotations

import json

from .context import context_json


def activity_groups(content: dict) -> str:
    """Step 4: generate activity groups / workplaces as JSON (not table)."""
    details = content["details"]
    context = context_json(content, "activity_groups")
    mean_group_size = content.get("generation", {}).get("mean_group_size", 7)
    nb_sub_groups = details["population"] // mean_group_size

    prompt = f"""
{details["name"]} is a {details["type"]} in a {content["setting"]["type"]} context. It is described in json as follows:
{json.dumps(context)}

I want you to generate all the sub-groups (between {int(nb_sub_groups)} and {int(nb_sub_groups * 1.5)}) that compose {details["name"]} and sort them by activities. Activities mean an occupation that can be a full-time occupation for members of {details["name"]}. The sub-groups should include all the possible activities: leadership, services, crafting, factions, criminals, resources, trade, etc. (but not {details["name"]} itself).
When generating the sub-groups, take into account the structure "{details.get("structure", "")}" of {details["name"]}.

For each sub-group, generate the following fields:
- name: (ie. "the blacksmiths", "the dead skulls", etc.)
- activity: the activity of the subgroup within {details["name"]}
- type: the global type of the subgroup
- keywords: a list of 5 keywords describing the group
- motivations: a list of 5 keywords describing what motivates members
- role: the role of the subgroup in {details["name"]}
- structure: one of ["despotism", "hierarchy", "democracy", "collaborative", "decentralized", "anarchy"]
- population: integer, the number of people in the group
- prosperity: one of ["poor", "average", "rich", "very rich"]
- origin: {{"local": float, "foreign": float}} — between 0 and 1
- age_ratio: {{"child": float, "teen": float, "adult": float, "middle-aged": float, "old": float}} — between 0 and 1
- common_bonds: a list of the 4 main bonds of the group. Bond types: blood, friendship, business, cause, identity, ideology, knowledge, place, past, interests.

The sum of the population of all sub-groups should equal the population of {details["name"]} ({details["population"]}).

Return a JSON object with the following structure:
{{ "groups": [
    {{
        "name": "...",
        "activity": "...",
        "type": "...",
        "keywords": ["...", "..."],
        "motivations": ["...", "..."],
        "role": "...",
        "structure": "...",
        "population": 0,
        "prosperity": "...",
        "origin": {{"local": 0.0, "foreign": 0.0}},
        "age_ratio": {{"child": 0.0, "teen": 0.0, "adult": 0.0, "middle-aged": 0.0, "old": 0.0}},
        "common_bonds": ["...", "...", "...", "..."]
    }}
] }}

Your json object:
"""
    return prompt


def employee_details(content: dict, workplace: dict) -> str:
    """Step 8: generate detailed employee attributes for a workplace."""
    details = content["details"]
    context = context_json(content, "workplaces")
    npcs = content.get("npcs", {})
    employee_refs = workplace.get("employees", [])

    persons_str = ""
    for emp_ref in employee_refs:
        # employees can be UUID strings or dicts
        if isinstance(emp_ref, str):
            emp = npcs.get(emp_ref, {})
        else:
            emp = emp_ref
        persons_str += f"- {emp.get('full_name', 'Unknown')}: {emp.get('race', '')}, {emp.get('gender', '')}, {emp.get('description', '')}, {emp.get('traits', '')}\n"

    prompt = f"""
{details["name"]} is a {details["type"]} in a {content["setting"]["type"]} context. It is described in json as follows:
{json.dumps(context)}

In {details["name"]}, there is a place called {workplace["name"]} where {int(workplace.get("population", 0))} people work or live. The group is described as follows:
{json.dumps({k: workplace[k] for k in ["activity", "keywords", "prosperity"] if k in workplace})}

Here are the members:
{persons_str}

For each member, generate:
- name: the full name
- key_figure: true/false (if the person is a key figure of the place — at least one)
- job: the job of the person
- rank: boss, apprentice, senior, etc.
- skill_level: master, expert, novice, etc.
- description: few words describing the person
- working_clothes: type - color - etc.
- nickname: nickname at work
- quote: a quote related to the work
- relations: short description of relationships with other members

Return a JSON object:
{{ "employees": [
    {{
        "name": "...",
        "key_figure": false,
        "job": "...",
        "rank": "...",
        "skill_level": "...",
        "description": "...",
        "working_clothes": "...",
        "nickname": "...",
        "quote": "...",
        "relations": "..."
    }}
] }}

Your json object:
"""
    return prompt


def workplace_details(content: dict, workplace: dict) -> str:
    """Step 9: generate detailed workplace descriptions."""
    details = content["details"]
    context = context_json(content, "workplaces")
    npcs = content.get("npcs", {})
    employee_refs = workplace.get("employees", [])

    persons_str = ""
    for emp_ref in employee_refs:
        emp = npcs.get(emp_ref, {}) if isinstance(emp_ref, str) else emp_ref
        persons_str += f"- {emp.get('full_name', 'Unknown')}: {emp.get('race', '')}, {emp.get('gender', '')}, job={emp.get('job', '')}, rank={emp.get('rank', '')}\n"

    prompt = f"""
{details["name"]} is a {details["type"]} in a {content["setting"]["type"]} context. It is described in json as follows:
{json.dumps(context)}

In {details["name"]}, there is a place called {workplace["name"]} where {int(workplace.get("population", 0))} people work or live. This group is described as follows:
{json.dumps({k: workplace[k] for k in ["activity", "keywords", "prosperity"] if k in workplace})}

Members:
{persons_str}

From this data, generate a json object describing the place in detail:
{{
    "name": "", // the actual name of the group
    "new_name": "", // a more appropriate name based on the data
    "description": "", // a long description of the group
    "customs": "", // a paragraph describing the customs
    "goals_keywords": [], // 4 keywords that describe the goals
    "history": "", // short history of the group
    "relationship": "", // long description of relationship with {details["name"]}
    "timeline": [], // 6 keywords describing events (rituals, celebrations, etc.)
    "anecdotes": [], // 3 long anecdotes related to the group
    "sites": {{ // 1 to 5 sites related to the activities
        "site_name": [] // list of visual keywords describing the site externally
    }},
    "plot": [] // list of potential plots or story hooks related to the group
}}

Your json object:
"""
    return prompt
