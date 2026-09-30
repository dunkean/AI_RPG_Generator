"""Bootstrap prompt — Step 1: generate name, keywords, structure, etc."""

from __future__ import annotations


def bootstrap(content: dict) -> str:
    """Build the bootstrap prompt from content dict.

    Uses ``content["details"]["description"]`` (not ``bootstrap_description``)
    and ``content["setting"]["description"]`` for the lore.
    """
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
    "keywords": {details.get("keywords", "[]")}, // 10 keywords that describe the {details["type"]}
    "setting_setting": {setting.get("keywords", "[]")}, // 10 keywords that describe the setting in detail
    "influence_areas": {details.get("influence_areas", "[]")}, // a list of areas where the {details["type"]} has influence
    "structure": "{details.get("structure", "")}", // 1 of ["despotism", "hierarchy", "democracy", "collaborative", "decentralized", "anarchy"]
    "prosperity": "{details.get("prosperity", "")}", // 1 of ["poor", "low", "medium", "high", "wealthy"]
    "culture": {details.get("culture", "[]")}, // 6 keywords that describe the {details["type"]} culture
    "customs": {details.get("customs", "[]")}, // 6 keywords that describe the {details["type"]} customs
    "goals": {details.get("goals", "[]")}, // 6 keywords that describe the {details["type"]} goals
    "resources": {details.get("resources", "[]")}, // 8 keywords that describe the {details["type"]} resources
    "history": {details.get("history", "[]")}, // 6 keywords that describe the {details["type"]} history
    "external_influences": {details.get("external_influences", "[]")}, // 10 keywords that describe the {details["type"]} external influences
    "timeline": {details.get("timeline", "[]")}, // 6 keywords that describe events that happened to the {details["type"]}
    "sites": {details.get("sites", "[]")}, // 5 keywords that describe the main sites related to the {details["type"]}
    "anecdotes": {details.get("anecdotes", "[]")}, // 6 keywords that describe anecdotes related to the {details["type"]}
    "races": {details.get("races", "{}")}, // a dict with all the races and their respective population ratios
    "member_bonds": {details.get("member_bonds", "{}")} // a dict with proportions of types of bonds between members
}}

Please comply with the number of keywords asked.
Your json: """
    return prompt
