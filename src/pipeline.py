"""Pipeline orchestration — runs the 11-step generation sequence."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Callable

from .cache.file_cache import FileCache
from .config import ProjectConfig
from .parsers.json_parser import parse_json, ParseError
from .parsers.table_parser import parse_table, TableParseError
from .providers.base import LLMProvider
from .utils import update_dict

# Prompts
from .prompts.bootstrap import bootstrap as prompt_bootstrap
from .prompts.details import detail as prompt_detail, description as prompt_description
from .prompts.details import external_influences as prompt_external_influences
from .prompts.workplaces import activity_groups as prompt_activity_groups
from .prompts.workplaces import employee_details as prompt_employee_details
from .prompts.workplaces import workplace_details as prompt_workplace_details
from .prompts.population import population_details as prompt_population_details
from .prompts.architecture import architecture_and_poi as prompt_architecture
from .prompts.architecture import workplace_sites as prompt_workplace_sites
from .prompts.key_figures import key_figure as prompt_key_figure

# Validators
from .validators.bootstrap import validate_bootstrap
from .validators.details import validate_detail, validate_descriptions
from .validators.external_influences import validate_external_influences
from .validators.workplaces import validate_activity_groups
from .validators.population import validate_population_details
from .validators.employees import validate_employee_details
from .validators.workplace_details import validate_workplace_details
from .validators.architecture import validate_architecture, validate_workplace_sites
from .validators.key_figures import validate_key_figure

# Procedural generation
from .procedural.population import generate_population
from .procedural.employees import assign_employees

logger = logging.getLogger(__name__)


class Pipeline:
    """Orchestrates the full content generation pipeline."""

    def __init__(
        self,
        config: ProjectConfig,
        provider: LLMProvider,
        cache: FileCache,
        *,
        resume: bool = True,
    ):
        self.config = config
        self.provider = provider
        self.cache = cache
        self.resume = resume
        self.content: dict[str, Any] = {}
        self._instruction = (
            f"You are an assistant who generates on-demand data for a tabletop "
            f"{config.setting.type} role-playing game"
        )

    # ------------------------------------------------------------------
    # Checkpoint save / load
    # ------------------------------------------------------------------

    def _checkpoint_path(self) -> Path:
        """Return the path to the checkpoint file for this project."""
        output_dir = Path(self.config.folders.output) / self.config.project_id
        return output_dir / "checkpoint.json"

    def _generation_fingerprint(self) -> str:
        """Invalidate text checkpoints when the model or content configuration changes."""
        config = self.config.model_dump(exclude={"image", "folders"})
        encoded = json.dumps(config, sort_keys=True, ensure_ascii=True).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _cache_prompt(self, prompt: str) -> str:
        """Include instruction and request settings in the cached request identity."""
        return json.dumps(
            {"instructions": self._instruction, "input": prompt,
             "provider": self.config.provider.model_dump()},
            sort_keys=True,
        )

    def _save_checkpoint(self, step: int) -> None:
        """Save current content + completed step to a checkpoint file."""
        path = self._checkpoint_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "_checkpoint_step": step,
            "_checkpoint_seed": self.config.generation.seed,
            "_checkpoint_config": self._generation_fingerprint(),
            "content": self.content,
        }
        # Write to a temp file first, then rename for atomicity
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        tmp.replace(path)
        logger.debug("Checkpoint saved after step %d → %s", step, path)

    def _load_checkpoint(self) -> int | None:
        """Load checkpoint if it exists and seed matches.

        Returns the last completed step number, or None if no valid checkpoint.
        """
        path = self._checkpoint_path()
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Could not read checkpoint: %s", exc)
            return None

        saved_seed = data.get("_checkpoint_seed")
        if saved_seed != self.config.generation.seed:
            logger.info(
                "Checkpoint seed (%s) differs from config seed (%s) — starting fresh",
                saved_seed, self.config.generation.seed,
            )
            return None

        if data.get("_checkpoint_config") != self._generation_fingerprint():
            logger.info("Checkpoint configuration changed or is legacy — starting fresh")
            return None

        self.content = data.get("content", {})
        last_step = data.get("_checkpoint_step", 0)
        logger.info("Resumed from checkpoint — last completed step: %d", last_step)
        return last_step

    def _bootstrap_content(self) -> dict[str, Any]:
        """Initialize the content dict from config."""
        return {
            "project_id": self.config.project_id,
            "generation": {
                "seed": self.config.generation.seed,
                "mean_group_size": self.config.generation.mean_group_size,
                "instruction": self._instruction,
            },
            "setting": {
                "description": self.config.setting.lore,
                "type": self.config.setting.type,
            },
            "details": {
                "type": self.config.community.type,
                "scale": self.config.community.scale,
                "population": self.config.community.population,
                "description": self.config.community.description,
                "races": dict(self.config.community.race_ratio),
            },
        }

    async def _query(
        self,
        step_name: str,
        prompt_func: Callable[..., str],
        prompt_args: tuple = (),
        parser: Callable[[str], Any] = parse_json,
        validator: Callable[..., dict] | None = None,
        validator_needs_content: bool = False,
    ) -> dict:
        """Core query pattern: build prompt, check cache, call LLM, parse, validate."""
        prompt_text = prompt_func(self.content, *prompt_args)
        project_id = self.config.project_id
        model = self.config.provider.model
        temp = self.config.provider.temperature
        cache_prompt = self._cache_prompt(prompt_text)

        # Check cache
        cached = self.cache.get(project_id, step_name, cache_prompt, model, temp)
        if cached is not None:
            logger.info("Using cached response for step: %s", step_name)
            raw = cached
        else:
            logger.info("Querying LLM for step: %s", step_name)
            raw = await self.provider.query(
                self._instruction, prompt_text, temperature=temp,
            )
            self.cache.set(project_id, step_name, cache_prompt, raw, model, temp)

        # Parse
        try:
            parsed = parser(raw)
        except (ParseError, TableParseError) as exc:
            logger.error("Parse failed for step %s: %s", step_name, exc)
            raise

        # Validate
        if validator is not None:
            if validator_needs_content:
                patch = validator(self.content, parsed)
            else:
                patch = validator(parsed)
        else:
            patch = parsed if isinstance(parsed, dict) else {"_raw": parsed}

        return patch

    async def _query_multiple(
        self,
        step_name: str,
        items: list[tuple[str, Callable, tuple]],
        parser: Callable[[str], Any] = parse_json,
        validator: Callable[..., dict] | None = None,
        validator_needs_content: bool = False,
    ) -> list[dict]:
        """Query LLM for multiple items with concurrency control."""
        sem = asyncio.Semaphore(self.config.generation.max_concurrent_queries)

        async def _run_one(sub_name: str, prompt_func: Callable, args: tuple) -> dict:
            async with sem:
                prompt_text = prompt_func(self.content, *args)
                project_id = self.config.project_id
                model = self.config.provider.model
                temp = self.config.provider.temperature
                cache_prompt = self._cache_prompt(prompt_text)

                cached = self.cache.get(project_id, sub_name, cache_prompt, model, temp)
                if cached is not None:
                    logger.info("Cache hit: %s", sub_name)
                    raw = cached
                else:
                    logger.info("Querying: %s", sub_name)
                    raw = await self.provider.query(
                        self._instruction, prompt_text, temperature=temp,
                    )
                    self.cache.set(project_id, sub_name, cache_prompt, raw, model, temp)

                try:
                    parsed = parser(raw)
                except (ParseError, TableParseError) as exc:
                    logger.error("Parse failed for %s: %s", sub_name, exc)
                    raise

                if validator is not None:
                    if validator_needs_content:
                        return validator(self.content, parsed)
                    return validator(parsed)
                return parsed if isinstance(parsed, dict) else {"_raw": parsed}

        tasks = [_run_one(name, func, args) for name, func, args in items]
        return await asyncio.gather(*tasks)

    def _generate(
        self,
        step_name: str,
        generator_func: Callable[[dict], dict],
    ) -> dict:
        """Run procedural generation and return patch."""
        logger.info("Running procedural generation: %s", step_name)
        return generator_func(self.content)

    async def run(self, steps: range | None = None) -> dict[str, Any]:
        """Execute the pipeline. Returns the final content dict."""
        all_steps = range(1, 12)
        steps_to_run = steps or all_steps

        # Try to resume from checkpoint
        resumed_step: int | None = None
        if self.resume:
            resumed_step = self._load_checkpoint()

        if resumed_step is None:
            self.content = self._bootstrap_content()

        # Create project folders
        project_id = self.config.project_id
        for folder_name in ["output", "log", "portraits", "buildings"]:
            folder = getattr(self.config.folders, folder_name, folder_name)
            Path(folder, project_id).mkdir(parents=True, exist_ok=True)

        def _should_run(step: int) -> bool:
            """Check if a step should run (requested AND not already completed)."""
            if step not in steps_to_run:
                return False
            if resumed_step is not None and step <= resumed_step:
                logger.info("Skipping step %d (already completed in checkpoint)", step)
                return False
            return True

        # Step 1: Bootstrap
        if _should_run(1):
            logger.info("=== Step 1: Bootstrap ===")
            patch = await self._query(
                "bootstrap", prompt_bootstrap,
                validator=validate_bootstrap,
            )
            update_dict(self.content, patch)
            self._save_checkpoint(1)

        # Step 2: Details (parallel per category)
        if _should_run(2):
            logger.info("=== Step 2: Details ===")
            detail_categories = self.config.detail_categories

            items = [
                (f"detail_{cat}", prompt_detail, (cat,))
                for cat in detail_categories
            ]
            patches = await self._query_multiple(
                "details", items,
                validator=validate_detail,
            )
            for patch in patches:
                update_dict(self.content, patch)

            # Also generate descriptions
            desc_patch = await self._query(
                "description", prompt_description,
                validator=validate_descriptions,
            )
            update_dict(self.content, desc_patch)
            self._save_checkpoint(2)

        # Step 3: External Influences
        if _should_run(3):
            logger.info("=== Step 3: External Influences ===")
            patch = await self._query(
                "external_influences", prompt_external_influences,
                validator=validate_external_influences,
            )
            update_dict(self.content, patch)
            self._save_checkpoint(3)

        # Step 4: Activity Groups / Workplaces
        if _should_run(4):
            logger.info("=== Step 4: Activity Groups ===")
            patch = await self._query(
                "workplaces", prompt_activity_groups,
                validator=validate_activity_groups,
                validator_needs_content=True,
            )
            update_dict(self.content, patch)
            self._save_checkpoint(4)

        # Step 5: Procedural Population Generation
        if _should_run(5):
            logger.info("=== Step 5: Population Generation ===")
            patch = self._generate("population", generate_population)
            update_dict(self.content, patch)
            self._save_checkpoint(5)

        # Step 6: Population Details (parallel per group)
        if _should_run(6):
            logger.info("=== Step 6: Population Details ===")
            social_groups = self.content.get("groups", {}).get("social", {})
            items = [
                (f"population_{gid}", prompt_population_details, (group,))
                for gid, group in social_groups.items()
            ]
            if items:
                patches = await self._query_multiple(
                    "population_details", items,
                    validator=validate_population_details,
                )
                for patch in patches:
                    update_dict(self.content, patch)
            self._save_checkpoint(6)

        # Step 7: Employee Assignment
        if _should_run(7):
            logger.info("=== Step 7: Employee Assignment ===")
            patch = self._generate("employees", assign_employees)
            update_dict(self.content, patch)
            self._save_checkpoint(7)

        # Step 8: Employee Details (parallel per workplace)
        if _should_run(8):
            logger.info("=== Step 8: Employee Details ===")
            activity_groups = self.content.get("groups", {}).get("activity", {})
            items = [
                (f"employees_{wid}", prompt_employee_details, (wp,))
                for wid, wp in activity_groups.items()
                if wp.get("employees")
            ]
            if items:
                patches = await self._query_multiple(
                    "employee_details", items,
                    validator=validate_employee_details,
                )
                for patch in patches:
                    update_dict(self.content, patch)
            self._save_checkpoint(8)

        # Step 9: Workplace Details (parallel per workplace)
        if _should_run(9):
            logger.info("=== Step 9: Workplace Details ===")
            activity_groups = self.content.get("groups", {}).get("activity", {})
            items = [
                (f"workplace_{wid}", prompt_workplace_details, (wp,))
                for wid, wp in activity_groups.items()
            ]
            if items:
                patches = await self._query_multiple(
                    "workplace_details", items,
                    validator=validate_workplace_details,
                )
                for patch in patches:
                    update_dict(self.content, patch)
            self._save_checkpoint(9)

        # Step 10: Architecture
        if _should_run(10):
            logger.info("=== Step 10: Architecture ===")
            arch_patch = await self._query(
                "architecture", prompt_architecture,
                validator=validate_architecture,
            )
            update_dict(self.content, arch_patch)

            # Per-workplace sites
            activity_groups = self.content.get("groups", {}).get("activity", {})
            items = [
                (f"wp_sites_{wid}", prompt_workplace_sites, (wp,))
                for wid, wp in activity_groups.items()
            ]
            if items:
                patches = await self._query_multiple(
                    "workplace_sites", items,
                    validator=validate_workplace_sites,
                )
                for patch in patches:
                    update_dict(self.content, patch)
            self._save_checkpoint(10)

        # Step 11: Key Figures
        if _should_run(11):
            logger.info("=== Step 11: Key Figures ===")
            key_figures = self._collect_key_figures()
            items = [
                (f"key_figure_{kf.get('full_name', 'unknown')}", prompt_key_figure, (kf,))
                for kf in key_figures
            ]
            if items:
                patches = await self._query_multiple(
                    "key_figures", items,
                    validator=validate_key_figure,
                )
                for patch in patches:
                    update_dict(self.content, patch)
            self._save_checkpoint(11)

        logger.info("Pipeline complete. Content keys: %s", list(self.content.keys()))
        return self.content

    def _collect_key_figures(self) -> list[dict]:
        """Gather all NPCs marked as key figures from groups and workplaces."""
        key_figures = []
        npcs = self.content.get("npcs", {})

        # From social groups
        for group in self.content.get("groups", {}).get("social", {}).values():
            for member_id in group.get("members", []):
                npc = npcs.get(member_id, {})
                if npc.get("key_figure"):
                    key_figures.append(npc)

        # From activity groups
        for wp in self.content.get("groups", {}).get("activity", {}).values():
            for emp in wp.get("employees", []):
                if isinstance(emp, dict) and emp.get("key_figure"):
                    key_figures.append(emp)
                elif isinstance(emp, str):
                    npc = npcs.get(emp, {})
                    if npc.get("key_figure"):
                        key_figures.append(npc)

        return key_figures
