"""Architecture prompts — Step 10."""

from __future__ import annotations

import json

from .context import context_json


def architecture_and_poi(content: dict) -> str:
    """Step 10a: global architecture style and site descriptions."""
    details = content["details"]
    context = context_json(content, "sites")

    sites_keywords = details.get("sites", {})
    if isinstance(sites_keywords, dict):
        kw = sites_keywords.get("keywords", [])
        desc = sites_keywords.get("descriptions", {})
    else:
        kw = sites_keywords
        desc = {}

    prompt = f"""
{details["name"]} is a {details["type"]} in a {content["setting"]["type"]} context. It is described in json as follows:
{json.dumps(context)}

And in text as follows:
{details["description"]}

In {details["name"]}, there are these notable sites:
{json.dumps(kw)}
{json.dumps(desc) if desc else ""}

For me to be able to draw those places, generate architectural information about {details["name"]} and its sites:
{{
    "architecture": [], // 6 architectural keywords describing the visual style (e.g. "thatched roof, wooden walls, small windows")
    "global_view": "", // short visual description from external POV
    "global_view_detailed": "", // long visual description with details, colors, architecture
    "sites_keywords": {{ // for each site, 6 architectural keywords
        "site_name_1": [],
        "site_name_2": []
    }},
    "sites_details": {{ // for each site, a short visual description
        "site_name_1": "",
        "site_name_2": ""
    }}
}}

Your json object:
"""
    return prompt


def workplace_sites(content: dict, workplace: dict) -> str:
    """Step 10b: per-workplace site architecture."""
    details = content["details"]
    context = context_json(content)

    architecture = content.get("architecture", {})
    arch_kw = architecture.get("architecture", [])
    arch_sites = architecture.get("sites_keywords", {})

    wp_sites = workplace.get("sites", {})

    prompt = f"""
{details["name"]} is a {details["type"]} in a {content["setting"]["type"]} context. It is described in json as follows:
{json.dumps(context)}

{details["name"]} has the following architecture:
{json.dumps(arch_kw)}
and the following sites:
{json.dumps(arch_sites)}

In {details["name"]}, there is a workplace called {workplace.get("name", "Unknown")} where {int(workplace.get("population", 0))} people work or live:
{json.dumps({k: workplace[k] for k in ["activity", "keywords", "prosperity"] if k in workplace})}

The workplace uses these sites:
{json.dumps(wp_sites)}

Generate architectural information for the workplace sites:
{{
    "site_name": {{
        "architecture": [], // 6 architectural keywords
        "details": "", // short visual description
        "type": "", // building, inn, street, landscape, forest, etc.
        "state": "", // ruins, abandoned, inhabited, under construction, etc.
        "inherits_architecture": false // true if same style as {details["name"]}
    }}
}}

Your json object:
"""
    return prompt
