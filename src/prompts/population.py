"""Population enrichment prompt — Step 6."""

from __future__ import annotations

import json

from .context import context_json


def population_details(content: dict, group: dict) -> str:
    """Step 6: enrich social group members with detailed NPC attributes."""
    details = content["details"]
    context = context_json(content, "families")
    npcs = content.get("npcs", {})

    # Build member info string with procedural appearance as read-only context
    members_str = ""
    for mid in group.get("members", []):
        npc = npcs.get(mid, {})
        appearance_parts = []
        for field in ("hair", "eyes", "skin", "height", "weight", "age_look",
                       "physical_detail", "clothes", "facial_hair"):
            val = npc.get(field, "")
            if val and val != "None":
                appearance_parts.append(f"{field}={val}")
        appearance_ctx = ", ".join(appearance_parts)

        members_str += (
            f"- {npc.get('full_name', 'Unknown')}: "
            f"{npc.get('race', '')}, {npc.get('gender', '')}, "
            f"generation={npc.get('generation', '')}, "
            f"position={npc.get('group_position', '')}, "
            f"beauty={npc.get('beauty', '')}"
        )
        if appearance_ctx:
            members_str += f" [{appearance_ctx}]"
        members_str += "\n"

    prompt = f"""
{details["name"]} is a {details["type"]} in a {content["setting"]["type"]} context. It is described in json as follows:
{json.dumps(context)}

In {details["name"]}, there is a group of type "{group.get('type', 'unknown')}" with {group.get('population', len(group.get('members', [])))} persons. The group is of origin "{group.get('origin', 'unknown')}".

The members are (physical appearance in brackets is already determined — do not generate visual attributes):
{members_str}

For each member, generate detailed attributes in JSON format:
{{
    "members": [
        {{
            "full_name": "", // repeat the full name
            "key_figure": false, // true if this person is a key figure of the group
            "age": 0, // exact age in years (respect generational gaps in families)
            "rank": "", // position in the group (mentor, leader, family head, etc.)
            "description": "", // few words describing the person (personality, not appearance)
            "traits": "", // 4 personality traits
            "clothes_detail": "", // optional refinement of clothing (e.g. "embroidered cuffs", "patched elbows") — NOT the full outfit
            "nickname": "", // nickname in the group
            "secret": "", // a short secret
            "quote": "", // a quote
            "relationship": "", // short description of relationships with other members
            "structure_preference": "" // one of ["family", "guild", "cooperative", "council", "team", "company"]
        }}
    ]
}}

Be original and realistic for a {content["setting"]["type"]} tabletop RPG setting.
Your json object:
"""
    return prompt
