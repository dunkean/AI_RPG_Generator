"""Key figures prompt — Step 11."""

from __future__ import annotations

import json

from .context import context_json


def key_figure(content: dict, npc: dict) -> str:
    """Step 11: generate detailed bio for a key NPC."""
    details = content["details"]
    context = context_json(content)
    npcs = content.get("npcs", {})

    name = npc.get("full_name", "Unknown")

    # Find the NPC's social group and colleagues
    social_group_id = npc.get("social_group", "")
    social_group = content.get("groups", {}).get("social", {}).get(social_group_id, {})
    family_str = ""
    for mid in social_group.get("members", []):
        m = npcs.get(mid, {})
        if m.get("full_name") != name:
            family_str += f"- {m.get('full_name', '')}: {m.get('group_position', '')}, {m.get('description', '')}\n"

    workplace_id = npc.get("workplace", "")
    workplace = content.get("groups", {}).get("activity", {}).get(workplace_id, {})
    colleagues_str = ""
    for eid in workplace.get("employees", []):
        emp = npcs.get(eid, {})
        if emp.get("full_name") != name:
            colleagues_str += f"- {emp.get('full_name', '')}: {emp.get('job', '')}, {emp.get('rank', '')}\n"

    prompt = f"""
{details["name"]} is a {details["type"]} in a {content["setting"]["type"]} context. It is described in json as follows:
{json.dumps(context)}

{name} is an inhabitant of {details["name"]} and is described as follows:
{json.dumps({k: v for k, v in npc.items() if not k.startswith("_")})}

{name}'s living group (type: {social_group.get('type', 'unknown')}, origin: {social_group.get('origin', 'unknown')}):
{family_str if family_str else "No group members found."}

{name}'s workplace ({workplace.get('name', 'Unknown')}):
{colleagues_str if colleagues_str else "No colleagues found."}

From this data, generate a detailed json object about {name}:
{{
    "full_name": "", // repeat the full name
    "description": "", // a long description of {name} and their life
    "habits": "", // a paragraph describing habits
    "goals_keywords": [], // 4 keywords for goals
    "history": "", // a long personal history (take into account their group and origins)
    "anecdotes": [], // anecdotes related to {name}
    "plot": [], // potential plot hooks related to {name}, be precise and explicit
    "relationship": {{ // relationships with people they know
        "person_name": "" // description of relationship
    }}
}}

Your json object:
"""
    return prompt
