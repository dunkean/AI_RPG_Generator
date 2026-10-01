"""Local generation jobs and archive selection for the browser studio."""

from __future__ import annotations

import json
import sqlite3
import threading
from contextlib import closing
from pathlib import Path
from uuid import uuid4

import yaml

from .config import Scenario, load_scenario
from .engine import generate
from .store import Archive


class BusyError(ValueError):
    pass


class CancelledError(RuntimeError):
    pass


class Studio:
    def __init__(self, archive: Archive, output_dir: Path | None = None):
        self.memory_only = output_dir is None
        self.lock = threading.RLock()
        self.archive = archive
        self.output_dir = output_dir or archive.path.parent / "web_runs"
        self.archives = {"initial": archive}
        self.descriptions = {"initial": self.describe(archive)}
        self.active = "initial"
        self.job = None
        self.worker = None
        self.cancel_event = threading.Event()
        paths = (
            []
            if self.memory_only
            else sorted(self.output_dir.glob("world_*.sqlite"), key=lambda p: p.stat().st_mtime)
        )
        for path in paths[-100:]:
            try:
                saved = Archive(path)
                description = self.describe(saved)
                self.archives[path.stem] = saved
                self.descriptions[path.stem] = description
            except (ValueError, OSError, KeyError, sqlite3.Error):
                continue

    @staticmethod
    def describe(archive):
        if getattr(archive, "ephemeral", False):
            return {
                "name": "Monde en mémoire",
                "seed": archive.config.seed,
                "summary": archive.summary,
                "created": archive.created,
                "places": len(archive.settlements),
                "ephemeral": True,
            }
        with closing(archive.connect()) as db:
            metadata = dict(db.execute("SELECT key,value FROM metadata"))
        scenario = json.loads(metadata["config"])
        return {
            "name": archive.path.name,
            "seed": json.loads(metadata["config"])["seed"],
            "summary": json.loads(metadata["summary"]),
            "created": archive.path.stat().st_mtime,
            "places": len(scenario.get("settlements", [])) or scenario["virtual_settlements"],
        }

    def current(self):
        with self.lock:
            return self.archive

    def snapshot(self, key=None):
        with self.lock:
            key = self.active if key is None else key
            return key, self.archives[key]

    def config(self, archive=None):
        current = archive or self.current()
        if getattr(current, "ephemeral", False):
            return current.config.model_dump(mode="json")
        with closing((archive or self.current()).connect()) as db:
            source = json.loads(
                db.execute("SELECT value FROM metadata WHERE key='config'").fetchone()[0]
            )
        return Scenario.model_validate(source).model_dump(mode="json")

    def presets(self):
        directory = Path(__file__).resolve().parents[2] / "config" / "genealogy"
        result = {"current": self.config()}
        for name in ("civilization", "medieval", "fantasy"):
            path = directory / f"{name}.yaml"
            if path.is_file():
                result[name] = load_scenario(path).model_dump(mode="json")
        result["blank"] = Scenario().model_dump(mode="json")
        return result

    @staticmethod
    def validate(payload):
        source = yaml.safe_load(payload["yaml"]) if "yaml" in payload else payload["scenario"]
        return Scenario.model_validate(source)

    def catalogue(self):
        with self.lock:
            entries = [
                {"id": key, **self.descriptions[key]}
                for key, archive in self.archives.items()
                if getattr(archive, "ephemeral", False) or archive.path.is_file()
            ]
            active = self.active
        return {
            "active": active,
            "archives": sorted(entries, key=lambda entry: entry["created"], reverse=True),
        }

    def select(self, key):
        with self.lock:
            self.archive = self.archives[key]
            self.active = key
        return {"active": key}

    def status(self):
        with self.lock:
            return dict(self.job) if self.job else {"state": "idle"}

    def start(self, payload):
        config = self.validate(payload)
        with self.lock:
            if self.job and self.job["state"] == "running":
                raise BusyError("Une génération est déjà en cours.")
            key = uuid4().hex
            self.cancel_event.clear()
            self.job = {
                "id": key,
                "state": "running",
                "year": config.start_year,
                "start_year": config.start_year,
                "end_year": config.start_year + config.duration,
                "population": config.initial_population,
                "progress": 0,
                "phase": "Simulation annuelle · régulation dynamique"
                if config.target_mode == "bounded" and config.target_population
                else "Simulation annuelle",
            }
            self.worker = threading.Thread(target=self._run, args=(key, config), daemon=True)
            self.worker.start()
            return dict(self.job)

    def cancel(self):
        with self.lock:
            if self.job and self.job["state"] == "running":
                self.cancel_event.set()
                self.job["phase"] = "Arrêt demandé · fin de l'année courante"
            return self.status()

    def _run(self, key, config):
        path = self.output_dir / f"world_{key}.sqlite"

        def progress(year, count):
            if self.cancel_event.is_set():
                raise CancelledError("Génération annulée")
            with self.lock:
                self.job.update(
                    year=year,
                    population=count,
                    phase=(
                        "Finalisation du monde en mémoire"
                        if self.memory_only
                        else "Enregistrement de l'archive"
                    )
                    if year == config.start_year + config.duration
                    else "Simulation annuelle",
                    progress=(year - config.start_year) / config.duration,
                )

        try:
            summary = generate(
                config,
                None if self.memory_only else path,
                progress,
            )
            if self.memory_only:
                archive, summary = summary, summary.summary
            else:
                archive = Archive(path)
            description = self.describe(archive)
            with self.lock:
                self.archives[path.stem] = archive
                self.descriptions[path.stem] = description
                if self.memory_only:
                    # Keep the active world and two recent alternatives for quick iteration.
                    while len(self.archives) > 3:
                        oldest = next(k for k in self.archives if k != self.active)
                        del self.archives[oldest]
                        del self.descriptions[oldest]
                self.job.update(state="complete", progress=1, summary=summary, archive=path.stem)
        except Exception as exc:  # noqa: BLE001 -- job boundary reports unexpected failures too
            try:
                if not self.memory_only:
                    path.with_suffix(".sqlite.partial").unlink(missing_ok=True)
            except OSError:
                pass
            with self.lock:
                self.job.update(
                    state="cancelled" if isinstance(exc, CancelledError) else "failed",
                    error=str(exc),
                )
