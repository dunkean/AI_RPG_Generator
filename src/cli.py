"""Command-line interface for the TTRPG content generator."""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import sys
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler

from .cache.file_cache import FileCache
from .config import EnvSettings, load_config
from .image.factory import create_image_provider
from .image.building_generator import generate_building
from .image.portrait_generator import generate_portrait
from .output.renderer import render
from .pipeline import Pipeline
from .providers.openai_provider import OpenAIProvider

console = Console()


def _image_seed(seed: int, kind: str, identity: str) -> int:
    """Derive a stable, distinct image seed from the project seed and asset identity."""
    payload = f"{seed}:{kind}:{identity}".encode()
    return int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % (2**63)


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


def _parse_steps(steps_str: str) -> range:
    """Parse a step range like '1-4' or '5' into a range."""
    if "-" in steps_str:
        start, end = steps_str.split("-", 1)
        return range(int(start), int(end) + 1)
    return range(int(steps_str), int(steps_str) + 1)


async def _run(args: argparse.Namespace) -> None:
    # Load config
    config = load_config(args.project)
    env = EnvSettings()

    if args.seed is not None:
        config.generation.seed = args.seed
    if args.model is not None:
        config.image.model = args.model

    # Setup provider
    api_key = env.openai_api_key
    if args.api_key_file:
        try:
            api_key = Path(args.api_key_file).read_text(encoding="utf-8-sig").strip()
        except OSError as exc:
            console.print(f"[red]Cannot read API key file: {exc}[/red]")
            sys.exit(1)
    if not api_key:
        console.print("[red]Error: set OPENAI_API_KEY or pass --api-key-file[/red]")
        sys.exit(1)

    provider = OpenAIProvider(
        api_key=api_key,
        model=config.provider.model,
        max_tokens=config.provider.max_tokens,
        reasoning_effort=config.provider.reasoning_effort,
    )

    # Setup cache
    cache_dir = Path(config.folders.cache)
    if args.no_cache:
        # Use a temp dir that won't hit any existing cache
        import tempfile
        cache_dir = Path(tempfile.mkdtemp())
    cache = FileCache(cache_dir)

    # Parse steps
    steps = None
    if args.steps:
        steps = _parse_steps(args.steps)

    # Run pipeline
    resume = not args.no_resume
    pipeline = Pipeline(config=config, provider=provider, cache=cache, resume=resume)

    console.print(f"[bold green]Starting generation for project: {config.project_id}[/bold green]")
    console.print(f"  LLM: {config.provider.model}")
    console.print(f"  Image model: {config.image.model} ({config.image.provider})")
    console.print(f"  Seed: {config.generation.seed}")
    console.print(f"  Population: {config.community.population}")
    if steps:
        console.print(f"  Steps: {list(steps)}")
    console.print(f"  Resume: {'enabled' if resume else 'disabled'}")

    content = await pipeline.run(steps=steps)

    # Save content JSON
    output_dir = Path(config.folders.output) / config.project_id
    output_dir.mkdir(parents=True, exist_ok=True)
    content_path = output_dir / "content.json"
    content_path.write_text(json.dumps(content, indent=2, default=str), encoding="utf-8")
    console.print(f"[green]Content saved to: {content_path}[/green]")

    # Generate images (unless --no-images)
    if not args.no_images:
        await _generate_images(config, env, content, output_dir)

    # Render HTML
    render(content, output_dir)
    console.print(f"[bold green]Done! Output at: {output_dir}[/bold green]")


async def _generate_images(config, env, content: dict, output_dir: Path) -> None:
    logger = logging.getLogger(__name__)

    # Setup image provider via factory
    img_provider = create_image_provider(config.image, hf_token=env.hf_token)
    if img_provider is None:
        console.print("[yellow]Image provider not available, skipping image generation[/yellow]")
        return

    npcs = content.get("npcs", {})
    architecture = content.get("architecture", {})

    portraits_dir = output_dir / "portraits"
    sites_dir = output_dir / "sites"

    # Generate portraits for key figures
    key_figures = [npc for npc in npcs.values() if npc.get("key_figure")]
    if key_figures:
        console.print(f"Generating {len(key_figures)} portraits...")
        for npc in key_figures:
            try:
                await generate_portrait(
                    npc, img_provider, portraits_dir,
                    width=config.image.portrait_width,
                    height=config.image.portrait_height,
                    seed=_image_seed(config.generation.seed, "portrait", npc.get("full_name", "")),
                )
            except Exception as e:
                logger.warning("Failed to generate portrait for %s: %s",
                             npc.get("full_name"), e)

    # Generate building images
    sites = architecture.get("sites_details", {})
    if sites:
        console.print(f"Generating {len(sites)} building images...")
        global_arch = architecture.get("architecture", [])
        for site_name, site_desc in sites.items():
            site_data = {
                "details": site_desc,
                "architecture": architecture.get("sites_keywords", {}).get(site_name, []),
            }
            try:
                await generate_building(
                    site_name, site_data, img_provider, sites_dir,
                    global_arch=global_arch,
                    width=config.image.building_width,
                    height=config.image.building_height,
                    seed=_image_seed(config.generation.seed, "site", site_name),
                )
            except Exception as e:
                logger.warning("Failed to generate building for %s: %s", site_name, e)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ttrpg-generate",
        description="TTRPG Content Generator — generate rich tabletop RPG content",
    )
    parser.add_argument(
        "project",
        help="Project name (must match a YAML file in config/projects/)",
    )
    parser.add_argument(
        "--steps",
        help="Step range to run (e.g. '1-4', '5', '1-11'). Default: all.",
    )
    parser.add_argument(
        "--model",
        help="Image model to use (e.g. 'flux', 'sdxl_turbo', 'cogview', 'qwen')",
    )
    parser.add_argument(
        "--api-key-file",
        help="Read the OpenAI API key from a UTF-8 file instead of OPENAI_API_KEY",
    )
    parser.add_argument(
        "--no-images",
        action="store_true",
        help="Skip image generation",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Ignore cached responses, force re-generation",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Override the random seed",
    )
    parser.add_argument(
        "--no-resume",
        action="store_true",
        help="Ignore checkpoint file and start from scratch",
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose/debug logging",
    )

    args = parser.parse_args()
    _setup_logging(args.verbose)
    asyncio.run(_run(args))


if __name__ == "__main__":
    main()
