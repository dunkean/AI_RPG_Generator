"""Detail, description, and external influences prompts — Steps 2-3."""

from __future__ import annotations

import json

from .context import context_json


def detail(content: dict, category: str) -> str:
    """Step 2: expand a category's keywords into titled paragraphs."""
    details = content["details"]
    context = context_json(content, category)

    prompt = f"""
{details["name"]} is a {details["type"]} in a {content["setting"]["type"]} context. It is described in json as follows:
{json.dumps(context)}

Based on all this information, I want you to write for every keyword of the {category} of the {details["name"]}:
- section title: a meaningful title that uses the keyword (ie. the keyword "war" could be transformed in "A long tradition of war", or "Love" in "Love is all around", depending on the category, context and keywords.)
- paragraph: a long text that describes in great detail the keyword in the {category} of the {details["name"]}.

I want you to format your response as a json object with the following structure:

{{ "{category}": {{
    "a section title (not only the keyword)": "the long paragraph 1",
    "a section title (not only the keyword)": "the long paragraph 2",
    "etc.": "etc.",
    }} }}

Your json object:
"""
    return prompt


def description(content: dict) -> str:
    """Step 2 (descriptions): short + long descriptions."""
    details = content["details"]
    context = context_json(content, "description")

    prompt = f"""
{details["name"]} is a {details["type"]} in a {content["setting"]["type"]} context. It is described in json as follows:
{json.dumps(context)}

In natural language, {details["name"]} is described as follows:
{details["description"]}

I want you to rewrite the description in two parts:
1- a short description in 50 words,
2- a long description of {details["name"]} following the "keywords", using literary style organized as follow:
- section title: a meaningful title that uses the keyword
- paragraph: a long text that describes in great detail the {details["name"]} based on the keyword.

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


def external_influences(content: dict) -> str:
    """Step 3: generate neighboring factions/entities."""
    details = content["details"]
    context = context_json(content, "external_influences")

    prompt = f"""
{details["name"]} is a {details["type"]} in a {content["setting"]["type"]} context. It is described in json as follows:
{json.dumps(context)}

Based on all this information, I want you to generate information for every external influence.
I want you to format your response as a json object with the following structure:

{{ "External influence name": {{
    "type": "", // the type of the external influence (ie. village, gang, guild, cult, etc.)
    "scale": "", // the scale of the external influence (ie. local, regional, global, pervasive, etc.)
    "description": "", // a long detailed description of the external influence (100 words)
    "keywords": [], // a list of 8 keywords describing the external influence
    "population": 0, // the count of individuals belonging to this external influence
    "relationship": "", // a long description of the relationship between the external influence and {details["name"]} (300 words)
    }} }}

Your json object:
"""
    return prompt
