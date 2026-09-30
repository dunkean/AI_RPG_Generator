"""Jinja2 HTML renderer — transforms content dict into HTML output."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent / "templates"


def _portrait_path(full_name: str, output_dir: Path) -> str:
    """Return the relative portrait path if the image exists, else empty string."""
    safe = full_name.replace(" ", "_").lower()
    rel = f"portraits/{safe}.png"
    return rel if (output_dir / rel).exists() else ""


def render(content: dict, output_dir: Path, templates_dir: Path | None = None) -> Path:
    """Render content dict to HTML using Jinja2 templates.

    Returns the path to the generated index.html.
    """
    templates_dir = templates_dir or TEMPLATES_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(templates_dir)),
        autoescape=False,
    )

    # Build template variables from content dict
    details = content.get("details", {})
    npcs = content.get("npcs", {})
    groups = content.get("groups", {})
    architecture = content.get("architecture", {})

    # Prepare NPC data for template
    template_npcs = {}
    key_npcs = {}
    lo_npcs = {}
    for npc_id, npc in npcs.items():
        full_name = npc.get("full_name", f"{npc.get('first_name', '')} {npc.get('last_name', '')}")
        npc_data = {
            "fullname": full_name,
            "age": npc.get("age", "?"),
            "age_look": npc.get("age_look", ""),
            "beauty": npc.get("beauty", ""),
            "clothes": npc.get("clothes", ""),
            "eyes": npc.get("eyes", ""),
            "gender": npc.get("gender", ""),
            "generation": npc.get("generation", ""),
            "habits": npc.get("habits", ""),
            "hair": npc.get("hair", ""),
            "height": npc.get("height", ""),
            "origin": npc.get("origin", ""),
            "physical_detail": npc.get("physical_detail", ""),
            "race": npc.get("race", ""),
            "skin": npc.get("skin", ""),
            "structure_preference": npc.get("structure_preference", ""),
            "surname": npc.get("last_name", ""),
            "traits": npc.get("traits", ""),
            "weight": npc.get("weight", ""),
            "quote": npc.get("quote", ""),
            "short_description": npc.get("description", ""),
            "secret": npc.get("secret", ""),
            "nickname": npc.get("nickname", ""),
            "img_path": _portrait_path(full_name, output_dir),
            "family": {
                "family_name": npc.get("last_name", ""),
                "situation": npc.get("group_position", ""),
                "rank": npc.get("rank", ""),
            },
        }

        # Job info if assigned to workplace
        if npc.get("workplace"):
            npc_data["job"] = {
                "workplace": npc.get("workplace", ""),
                "job": npc.get("job", ""),
                "rank": npc.get("rank", ""),
                "skill level": npc.get("skill_level", ""),
            }

        # Key figure details
        if npc.get("key_figure"):
            npc_data["relationship"] = npc.get("relationship", {})
            npc_data["anecdotes"] = npc.get("anecdotes", [])
            npc_data["goals"] = npc.get("goals_keywords", [])
            npc_data["plot"] = npc.get("plot", [])
            key_npcs[full_name] = npc_data
        else:
            lo_npcs[full_name] = npc_data

        template_npcs[full_name] = npc_data

    # Prepare details sections
    template_details = {}
    for cat in ["culture", "customs", "goals", "resources", "history",
                 "timeline", "sites", "anecdotes"]:
        cat_data = details.get(cat, {})
        template_details[cat] = {
            "keywords": cat_data.get("keywords", []),
            "details": list(cat_data.get("descriptions", {}).values())
            if isinstance(cat_data.get("descriptions"), dict) else [],
        }

    # Architecture section
    if architecture:
        # Build sites_img mapping from generated building images
        sites_img = {}
        for site_key in architecture.get("sites_details", {}):
            safe_name = site_key.replace(" ", "_").lower()
            img_rel = f"sites/{safe_name}.png"
            if (output_dir / img_rel).exists():
                sites_img[site_key] = img_rel

        template_details["architecture"] = {
            "keywords": architecture.get("architecture", []),
            "details": [architecture.get("global_view_detailed", "")],
            "global_view": architecture.get("global_view", ""),
            "global_view_detailed": architecture.get("global_view_detailed", ""),
            "style": architecture.get("architecture", []),
            "sites_keywords": architecture.get("sites_keywords", {}),
            "sites_details": architecture.get("sites_details", {}),
            "sites_img": sites_img,
        }

    # Prepare workplaces
    template_workplaces = {}
    for wid, wp in groups.get("activity", {}).items():
        wp_name = wp.get("new_name") or wp.get("name", wid)
        template_workplaces[wp_name] = {
            "name": wp_name,
            "type": wp.get("type", ""),
            "field": wp.get("role", ""),
            "activity": wp.get("activity", ""),
            "desc": wp.get("description", ""),
            "population": wp.get("population", 0),
            "employees": wp.get("employees", []),
            "prosperity": wp.get("prosperity", ""),
            "relationship": wp.get("relationship", ""),
            "history": wp.get("history", ""),
            "anecdotes": wp.get("anecdotes", []),
            "plot": wp.get("plot", []),
            "keywords": wp.get("keywords", []),
            "goals_keywords": wp.get("goals_keywords", []),
            "sites": wp.get("sites", {}),
            "rsite": "",
        }

    # Prepare social groups
    template_groups = {}
    for gid, grp in groups.get("social", {}).items():
        members = grp.get("members", [])
        key_figs = [m for m in members if npcs.get(m, {}).get("key_figure")]
        name = gid
        if members:
            first_npc = npcs.get(members[0], {})
            name = first_npc.get("last_name", gid)

        template_groups[gid] = {
            "name": name,
            "rtype": grp.get("type", ""),
            "origin": grp.get("origin", ""),
            "size": len(members),
            "members": [npcs.get(m, {}).get("full_name", m) for m in members],
            "key_figures": [npcs.get(m, {}).get("full_name", m) for m in key_figs],
            "workplace": "",
        }

    # Global views
    global_views = {}
    global_view_img = output_dir / "sites" / "global_view.png"
    if architecture.get("global_view") and global_view_img.exists():
        global_views["Global View"] = "sites/global_view.png"

    # Render template
    template_vars = {
        "name": details.get("name", content.get("project_id", "Unknown")),
        "lore": {
            "description": content.get("setting", {}).get("description", ""),
            "keywords": content.get("setting", {}).get("keywords", []),
            "world_type": content.get("setting", {}).get("type", ""),
        },
        "details": template_details,
        "workplaces": template_workplaces,
        "groups": template_groups,
        "npcs": template_npcs,
        "key_npcs": key_npcs,
        "lo_npcs": lo_npcs,
    }

    # Add global_views to details.description
    template_vars["details"]["description"] = {
        "description": details.get("descriptions", {}).get("short", ""),
        "keywords": details.get("keywords", []),
        "global_views": global_views,
    }

    template = env.get_template("place.html")
    html = template.render(**template_vars)

    output_path = output_dir / "index.html"
    output_path.write_text(html, encoding="utf-8")
    logger.info("Rendered HTML to: %s", output_path)

    # Copy CSS if it exists
    css_src = templates_dir / "style.css"
    if css_src.exists():
        shutil.copy2(css_src, output_dir / "style.css")

    return output_path
