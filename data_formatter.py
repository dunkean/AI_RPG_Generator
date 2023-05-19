
import defines as D


def bootstrap_content(id, lore, group_type, scale, population, group_description, world_type):
    content = {
        "project_id": id,
        "type": group_type,
        "name": "",
        "scale": scale,
        "size": population,
        "lore": {
            "world_type": world_type,
            "description": lore,
            "keywords": [],
        },
        "details": {
            "description": group_description,
            "keywords": [],
        },
    }

    return content


def format_bootstrap_query(content, new_content):
    content["name"] = new_content["name"]
    content["structure"] = new_content["structure"]
    if "lore keywords" in new_content:
        content["lore"]["keywords"] = new_content["lore keywords"]
    elif "lore_keywords" in new_content:
        content["lore"]["keywords"] = new_content["lore_keywords"]
    content["details"]["keywords"] = new_content["keywords"]

    for key in D.GROUP_CATEGORIES:
        content[key] = {"keywords": new_content[key]}
    return content


def format_category_query(content, new_content, category):
    if isinstance(new_content[category], list):
        if len(new_content[category]) == 1:
            new_content[category] = new_content[category][0].split("\\n\\n") # TODO: make this more robust and verify the bug on customs
    content[category]["details"] = new_content[category]
    return content

# def format_groups(content, new_content):
    