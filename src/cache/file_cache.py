"""Dual-layer file caching: hash-based + project-based."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class FileCache:
    """Two-layer cache that persists LLM responses to disk.

    * **Hash layer**: MD5 of (prompt + model + temperature) -> single file.
    * **Project layer**: ``{project_id}/{step_name}/{hash}.json`` with metadata.
    """

    def __init__(self, cache_dir: str | Path):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Hash helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _hash(prompt: str, model: str = "", temperature: float = 0.0) -> str:
        payload = f"{prompt}|{model}|{temperature}"
        return hashlib.md5(payload.encode("utf-8")).hexdigest()

    # ------------------------------------------------------------------
    # Hash-based cache
    # ------------------------------------------------------------------

    def _hash_path(self, h: str) -> Path:
        return self.cache_dir / "hash" / f"{h}.json"

    def get_by_hash(
        self, prompt: str, model: str = "", temperature: float = 0.0
    ) -> str | None:
        h = self._hash(prompt, model, temperature)
        path = self._hash_path(h)
        if path.exists():
            logger.debug("Cache hit (hash): %s", h)
            return path.read_text(encoding="utf-8")
        return None

    def set_by_hash(
        self, prompt: str, response: str, model: str = "", temperature: float = 0.0
    ) -> None:
        h = self._hash(prompt, model, temperature)
        path = self._hash_path(h)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(response, encoding="utf-8")

    # ------------------------------------------------------------------
    # Project-based cache
    # ------------------------------------------------------------------

    def _project_path(self, project_id: str, step_name: str, h: str) -> Path:
        return self.cache_dir / project_id / step_name / f"{h}.json"

    def get_by_project(
        self, project_id: str, step_name: str, prompt: str,
        model: str = "", temperature: float = 0.0,
    ) -> str | None:
        h = self._hash(prompt, model, temperature)
        path = self._project_path(project_id, step_name, h)
        if path.exists():
            logger.debug("Cache hit (project): %s/%s/%s", project_id, step_name, h)
            data = json.loads(path.read_text(encoding="utf-8"))
            return data.get("response")
        return None

    def set_by_project(
        self, project_id: str, step_name: str, prompt: str, response: str,
        model: str = "", temperature: float = 0.0,
    ) -> None:
        h = self._hash(prompt, model, temperature)
        path = self._project_path(project_id, step_name, h)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "prompt_hash": h,
            "model": model,
            "temperature": temperature,
            "timestamp": datetime.now().isoformat(),
            "response": response,
        }
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Convenience: try both layers
    # ------------------------------------------------------------------

    def get(
        self, project_id: str, step_name: str, prompt: str,
        model: str = "", temperature: float = 0.0,
    ) -> str | None:
        """Try project cache first, then hash cache."""
        result = self.get_by_project(project_id, step_name, prompt, model, temperature)
        if result is not None:
            return result
        return self.get_by_hash(prompt, model, temperature)

    def set(
        self, project_id: str, step_name: str, prompt: str, response: str,
        model: str = "", temperature: float = 0.0,
    ) -> None:
        """Write to both layers."""
        self.set_by_hash(prompt, response, model, temperature)
        self.set_by_project(project_id, step_name, prompt, response, model, temperature)
