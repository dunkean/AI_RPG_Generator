# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TTRPG Content Generator: a Python tool that procedurally generates rich content for tabletop RPGs (communities, NPCs, factions, workplaces, architecture) by combining LLM queries with algorithmic population generation. It uses Flux.1 (HuggingFace API or ComfyUI) for portrait/building images.

## Running

### CLI

```bash
pip install -e .                          # Install in development mode
pip install -e ".[dev]"                   # With dev dependencies (pytest, ruff)

ttrpg-generate enclave                    # Full generation
ttrpg-generate enclave --steps 1-4        # Partial run (steps 1 through 4)
ttrpg-generate enclave --no-images        # Skip image generation
ttrpg-generate enclave --no-cache         # Force re-generation
ttrpg-generate enclave --seed 123         # Override seed
ttrpg-generate enclave -v                 # Verbose logging
```

Or run directly: `python -m src.cli enclave`

### Environment

Requires a `.env` file with:
```
OPENAI_API_KEY=sk-...
HF_TOKEN=hf_...        # Optional, for HuggingFace image generation
```

### Tests

```bash
pytest                                    # Run all tests
pytest tests/test_parsers.py              # Run specific test file
pytest -v                                 # Verbose output
```

## Key Dependencies

- `openai>=1.0` (AsyncOpenAI client, default model: `gpt-4.1-mini`)
- `pydantic>=2.0` + `pydantic-settings` (config validation, response models)
- `numpy` (statistical distributions for population generation)
- `pynames` (fantasy name generation — Iron Kingdoms / D&D generators)
- `shortuuid` (unique IDs for groups/NPCs)
- `jinja2` (HTML rendering)
- `pyyaml` (config files)
- `tenacity` (retry logic for LLM calls)
- `httpx` (async HTTP for image generation)
- `rich` (CLI logging and progress)

## Architecture

### Directory Structure

```
src/
    cli.py                  # Entry point (argparse + asyncio)
    pipeline.py             # Pipeline orchestration (11-step sequence)
    config.py               # YAML config + Pydantic settings
    utils.py                # update_dict() deep merge helper
    models/
        schemas.py          # Pydantic response models per LLM step
        content.py          # TypedDict for content dict (documentation)
    providers/
        base.py             # LLMProvider ABC
        openai_provider.py  # OpenAI implementation (async, tenacity retry)
    prompts/
        context.py          # context_json() + categories_to_keep mapping
        bootstrap.py        # Step 1: name, keywords, structure, etc.
        details.py          # Steps 2-3: detail, description, external_influences
        workplaces.py       # Steps 4, 8, 9: activity_groups, employee/workplace details
        population.py       # Step 6: NPC enrichment
        architecture.py     # Step 10: architecture and site descriptions
        key_figures.py      # Step 11: detailed NPC bios
    procedural/
        distributions.py    # Weight tables, age data, position pools, group filters
        names.py            # pynames race-specific name generation
        population.py       # Step 5: social group + NPC generation
        employees.py        # Step 7: preferential workplace assignment
    parsers/
        json_parser.py      # JSON with comment stripping + ast.literal_eval fallback
        table_parser.py     # Markdown table parser (legacy compat)
    validators/
        bootstrap.py        # Step 1 validator
        details.py          # Steps 2 validator (detail + descriptions)
        external_influences.py  # Step 3 validator
        workplaces.py       # Step 4 validator (population normalization)
        population.py       # Step 6 validator
        employees.py        # Step 8 validator
        workplace_details.py    # Step 9 validator
        architecture.py     # Step 10 validator
        key_figures.py      # Step 11 validator
    image/
        base.py             # ImageProvider ABC
        factory.py          # create_image_provider() from config
        flux_hf.py          # HuggingFace Inference API backend
        portrait_generator.py   # NPC portrait prompt builder
        building_generator.py   # Site/building prompt builder
        comfyui/
            client.py       # ComfyUI HTTP API client (submit/poll/download)
            provider.py     # ComfyUIProvider(ImageProvider) — composes client + workflow
            workflows/
                base.py     # WorkflowBuilder ABC + GenerationParams
                registry.py # name → workflow class mapping
                flux.py     # Flux.1 / Flux.2 workflow
                sdxl_turbo.py   # SDXL Turbo workflow
                cogview.py  # CogView/GLM-Image workflow
                qwen.py     # Qwen-Image workflow
                lora.py     # LoRA injection utility
    output/
        renderer.py         # Jinja2 HTML rendering
    cache/
        file_cache.py       # Dual-layer file caching (hash + project)
config/
    default.yaml            # Default generation parameters
    projects/
        enclave.yaml        # Example project config
templates/
    place.html              # Jinja2 HTML template
    style.css               # Stylesheet
tests/
    fixtures/
        mock_responses.py   # LLM response fixtures
    test_parsers.py
    test_validators.py
    test_procedural.py
    test_config.py
archive/                    # Old codebase (preserved for reference)
```

### Generation Pipeline (src/pipeline.py)

The pipeline runs 11 steps sequentially, building up a `content` dict:

1. **Bootstrap** — LLM generates name, keywords, structure, culture, etc.
2. **Details** — LLM expands categories into long-form text (parallel x6)
3. **External Influences** — LLM generates neighboring factions
4. **Activity Groups** — LLM generates workplaces as JSON
5. **Population** — Procedural: social groups + NPCs (Gumbel distributions)
6. **Population Details** — LLM enriches NPCs (parallel per group)
7. **Employees** — Procedural: preferential workplace assignment
8. **Employee Details** — LLM enriches workplace roles (parallel per workplace)
9. **Workplace Details** — LLM generates site descriptions (parallel)
10. **Architecture** — LLM generates visual descriptions + per-site architecture
11. **Key Figures** — LLM generates detailed NPC bios (parallel)

### Core Pattern

- `Pipeline._query()`: build prompt → check cache → call LLM → parse → validate → return patch
- `Pipeline._query_multiple()`: same but with `asyncio.gather()` + semaphore for concurrency
- `Pipeline._generate()`: run procedural generation, return patch
- All patches are merged into `content` via `update_dict()` (recursive deep merge)

### Configuration

- `config/default.yaml` — default parameters (seed, temperature, model, folders)
- `config/projects/{name}.yaml` — per-project settings (lore, community, race ratios)
- Merged at load time: defaults + project overrides → Pydantic `ProjectConfig`
- Secrets loaded from `.env` via `pydantic-settings`

### Caching

Dual-layer file cache (`src/cache/file_cache.py`):
- **Hash layer**: MD5 of (prompt + model + temperature) → `cache/hash/{hash}.json`
- **Project layer**: `cache/{project_id}/{step_name}/{hash}.json` with metadata

### Key Conventions

- The central data structure is a nested `content` dict (see `src/models/content.py` for TypedDict)
- LLM prompts request JSON output, parsed/validated before merging
- Population generation uses numpy weighted random (Gumbel, normal distributions)
- All LLM calls are async with tenacity retry (exponential backoff, 3 attempts)
- Project config is YAML-based, not hardcoded
