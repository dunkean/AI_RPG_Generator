"""Building/site image generation from architecture data."""

from __future__ import annotations

import logging
from pathlib import Path

from .base import ImageProvider

logger = logging.getLogger(__name__)


def build_building_prompt(site_name: str, site_data: dict, global_arch: list[str] | None = None) -> str:
    """Build a Flux.1 building prompt from site architecture data."""
    parts = [
        "landscape painting",
        "heroic fantasy architecture",
        "RPG illustration",
        "exterior view",
    ]

    # Architecture keywords
    arch_kw = site_data.get("architecture", [])
    if arch_kw:
        parts.extend(arch_kw)
    elif global_arch:
        parts.extend(global_arch)

    # Site details
    details = site_data.get("details", "")
    if details:
        parts.append(details)

    # Site type and state
    site_type = site_data.get("type", "")
    if site_type:
        parts.append(site_type)
    state = site_data.get("state", "")
    if state:
        parts.append(state)

    parts.extend([
        "detailed environment",
        "cinematic lighting",
        "sharp focus",
        "high quality",
    ])

    return ", ".join(parts)


BUILDING_NEGATIVE = (
    "blurry, low quality, deformed, text, watermark, "
    "signature, people, modern, contemporary"
)


async def generate_building(
    site_name: str,
    site_data: dict,
    provider: ImageProvider,
    output_dir: Path,
    global_arch: list[str] | None = None,
    width: int = 1024,
    height: int = 768,
    seed: int = -1,
) -> Path:
    """Generate and save a building/site image."""
    prompt = build_building_prompt(site_name, site_data, global_arch)
    safe_name = site_name.replace(" ", "_").lower()

    logger.info("Generating building image for %s", site_name)
    image_bytes = await provider.generate(
        prompt=prompt,
        negative=BUILDING_NEGATIVE,
        width=width,
        height=height,
        seed=seed,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{safe_name}.png"
    output_path.write_bytes(image_bytes)
    logger.info("Building image saved: %s", output_path)
    return output_path
