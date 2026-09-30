"""Portrait image generation from NPC attributes."""

from __future__ import annotations

import logging
from pathlib import Path

from .base import ImageProvider

logger = logging.getLogger(__name__)


def build_portrait_prompt(npc: dict) -> str:
    """Build a Flux.1 portrait prompt from NPC attributes.

    Uses granular procedural appearance fields for maximum visual variation
    between characters. Falls back to composite fields when granular data
    is missing (backward compatibility).
    """
    parts = []

    race = npc.get("race", "human")
    gender = npc.get("gender", "")
    age_look = npc.get("age_look", "adult")
    height = npc.get("height", "average")
    weight = npc.get("weight", "average")
    beauty = npc.get("beauty", "average")
    job = npc.get("job", "")
    environment = npc.get("environment", "")

    # Style prefix
    parts.append("fine art painting, heroic fantasy, RPG book illustration")

    # POV — use portrait_pov if available, else default
    pov = npc.get("portrait_pov", "front view")
    parts.append(f"{pov} bust portrait of a single character")

    # Core identity
    parts.append(f"{age_look} {gender} {race}")
    if job:
        parts.append(job)

    # Face — granular features
    face_shape = npc.get("face_shape", "")
    if face_shape:
        parts.append(f"{beauty} {face_shape} face")
    else:
        parts.append(f"{beauty} face")

    nose_shape = npc.get("nose_shape", "")
    lip_shape = npc.get("lip_shape", "")
    chin_shape = npc.get("chin_shape", "")
    face_details = []
    if nose_shape:
        face_details.append(f"{nose_shape} nose")
    if lip_shape:
        face_details.append(f"{lip_shape} lips")
    if chin_shape:
        face_details.append(f"{chin_shape} chin")
    if face_details:
        parts.append(", ".join(face_details))

    # Body type
    parts.append(f"{weight} build, {height} height")

    # Hair — granular or composite fallback
    hair_color = npc.get("hair_color", "")
    hair_length = npc.get("hair_length", "")
    hair_style = npc.get("hair_style", "")
    if hair_color or hair_length or hair_style:
        hair_desc = " ".join(p for p in [hair_length, hair_style, hair_color] if p)
        parts.append(f"{hair_desc} hair")
    elif npc.get("hair"):
        parts.append(f"{npc['hair']} hair")

    # Eyes — granular or composite fallback
    eye_shape = npc.get("eye_shape", "")
    eye_color = npc.get("eye_color", "")
    if eye_shape or eye_color:
        eye_desc = " ".join(p for p in [eye_shape, eye_color] if p)
        parts.append(f"{eye_desc} eyes")
    elif npc.get("eyes"):
        parts.append(f"{npc['eyes']} eyes")

    # Skin — granular or composite fallback
    skin_texture = npc.get("skin_texture", "")
    skin_tone = npc.get("skin_tone", "")
    if skin_texture or skin_tone:
        skin_desc = " ".join(p for p in [skin_texture, skin_tone] if p)
        parts.append(f"{skin_desc} skin")
    elif npc.get("skin"):
        parts.append(f"{npc['skin']} skin")

    # Facial hair
    facial_hair = npc.get("facial_hair", "")
    if facial_hair and facial_hair.lower() not in ("", "clean-shaven"):
        parts.append(facial_hair)

    # Physical detail
    physical_detail = npc.get("physical_detail", "")
    if physical_detail and physical_detail.lower() not in ("none", ""):
        parts.append(physical_detail)

    # Clothing — combine procedural + LLM refinement
    clothing_parts = []
    clothing_color = npc.get("clothing_color", "")
    clothing_material = npc.get("clothing_material", "")
    clothing_style = npc.get("clothing_style", "")
    clothing_accessory = npc.get("clothing_accessory", "")
    if clothing_color or clothing_material or clothing_style:
        base = " ".join(p for p in [clothing_color, clothing_material, clothing_style] if p)
        clothing_parts.append(base)
    if clothing_accessory and clothing_accessory != "none":
        clothing_parts.append(clothing_accessory)
    clothes_detail = npc.get("clothes_detail", "")
    if clothes_detail:
        clothing_parts.append(clothes_detail)
    # Fallback to composite
    if not clothing_parts and npc.get("clothes"):
        clothing_parts.append(npc["clothes"])
    if clothing_parts:
        parts.append(f"wearing {', '.join(clothing_parts)}")

    # Background/environment
    if environment:
        parts.append(f"{environment} background")

    # Quality suffix
    parts.append("detailed face, realistic eyes, cinematic lighting, sharp focus")

    return ", ".join(parts)


async def generate_portrait(
    npc: dict,
    provider: ImageProvider,
    output_dir: Path,
    width: int = 768,
    height: int = 1024,
    seed: int = -1,
) -> Path:
    """Generate and save a portrait for an NPC."""
    prompt = build_portrait_prompt(npc)
    full_name = npc.get("full_name", "unknown")
    safe_name = full_name.replace(" ", "_").lower()

    logger.info("Generating portrait for %s", full_name)
    image_bytes = await provider.generate(
        prompt=prompt,
        width=width,
        height=height,
        seed=seed,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{safe_name}.png"
    output_path.write_bytes(image_bytes)
    logger.info("Portrait saved: %s", output_path)
    return output_path
