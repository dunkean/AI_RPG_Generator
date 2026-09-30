"""Tests for configuration loading and pipeline checkpoint."""

import json
import pytest
from pathlib import Path

from src.config import load_config, ProjectConfig, _deep_merge


class TestDeepMerge:
    def test_simple_merge(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        result = _deep_merge(base, override)
        assert result == {"a": 1, "b": 3, "c": 4}

    def test_nested_merge(self):
        base = {"a": {"x": 1, "y": 2}}
        override = {"a": {"y": 3, "z": 4}}
        result = _deep_merge(base, override)
        assert result == {"a": {"x": 1, "y": 3, "z": 4}}

    def test_override_non_dict_with_dict(self):
        base = {"a": 1}
        override = {"a": {"x": 1}}
        result = _deep_merge(base, override)
        assert result == {"a": {"x": 1}}


class TestLoadConfig:
    def test_loads_enclave(self):
        config = load_config("enclave")
        assert config.project_id == "Enclave"
        assert config.community.population == 80
        assert config.community.race_ratio["human"] == 0.6

    def test_default_values(self):
        config = load_config("enclave")
        assert config.generation.seed == 42
        assert config.provider.model == "gpt-6-luna"
        assert config.provider.reasoning_effort == "low"
        assert config.provider.temperature == 1

    def test_setting_lore(self):
        config = load_config("enclave")
        assert "medieval fantasy" in config.setting.lore.lower()
        assert config.setting.type == "Medieval fantasy"

    def test_community_config(self):
        config = load_config("enclave")
        assert config.community.type == "small community"
        assert config.community.scale == "local"
        assert "dwarf" in config.community.race_ratio

    def test_pydantic_validation(self):
        config = ProjectConfig(
            project_id="test",
            generation={"seed": 123},
        )
        assert config.generation.seed == 123
        assert config.provider.model == "gpt-6-luna"

    def test_missing_project_uses_defaults(self):
        config = load_config("nonexistent_project_xyz")
        assert config.project_id == "default"


class TestPipelineCheckpoint:
    """Tests for checkpoint save/load in Pipeline."""

    @pytest.fixture
    def pipeline(self, tmp_path):
        """Create a Pipeline with a temp output folder."""
        from unittest.mock import AsyncMock
        from src.pipeline import Pipeline
        from src.cache.file_cache import FileCache

        config = load_config("enclave")
        # Override output folder to tmp_path
        config.folders.output = str(tmp_path / "output")
        provider = AsyncMock()
        cache = FileCache(tmp_path / "cache")
        return Pipeline(config=config, provider=provider, cache=cache, resume=True)

    def test_save_and_load_checkpoint(self, pipeline):
        pipeline.content = {"details": {"name": "Test Village"}, "npcs": {"id1": {"name": "Bob"}}}
        pipeline._save_checkpoint(4)

        # Verify file exists
        path = pipeline._checkpoint_path()
        assert path.exists()

        data = json.loads(path.read_text(encoding="utf-8"))
        assert data["_checkpoint_step"] == 4
        assert data["_checkpoint_seed"] == pipeline.config.generation.seed
        assert data["content"]["details"]["name"] == "Test Village"

        # Load it back
        pipeline.content = {}
        step = pipeline._load_checkpoint()
        assert step == 4
        assert pipeline.content["details"]["name"] == "Test Village"
        assert pipeline.content["npcs"]["id1"]["name"] == "Bob"

    def test_load_returns_none_when_no_file(self, pipeline):
        assert pipeline._load_checkpoint() is None

    def test_load_rejects_different_seed(self, pipeline):
        pipeline.content = {"details": {"name": "Test"}}
        pipeline._save_checkpoint(3)

        # Change seed
        pipeline.config.generation.seed = 999
        pipeline.content = {}
        step = pipeline._load_checkpoint()
        assert step is None
        assert pipeline.content == {}  # content not restored

    def test_checkpoint_atomicity(self, pipeline):
        """Checkpoint write should not leave a .tmp file behind."""
        pipeline.content = {"x": 1}
        pipeline._save_checkpoint(1)

        path = pipeline._checkpoint_path()
        tmp_path = path.with_suffix(".tmp")
        assert path.exists()
        assert not tmp_path.exists()

    @pytest.mark.parametrize("field,value", [("model", "gpt-5-mini"), ("reasoning_effort", "high")])
    def test_checkpoint_rejects_changed_provider(self, pipeline, field, value):
        pipeline._save_checkpoint(11)
        setattr(pipeline.config.provider, field, value)
        assert pipeline._load_checkpoint() is None

    def test_checkpoint_rejects_changed_lore(self, pipeline):
        pipeline._save_checkpoint(11)
        pipeline.config.setting.lore = "A different world"
        assert pipeline._load_checkpoint() is None

    def test_checkpoint_accepts_image_only_changes(self, pipeline):
        pipeline._save_checkpoint(11)
        pipeline.config.image.model = "flux"
        assert pipeline._load_checkpoint() == 11

    def test_checkpoint_rejects_legacy_config(self, pipeline):
        pipeline._save_checkpoint(11)
        path = pipeline._checkpoint_path()
        data = json.loads(path.read_text(encoding="utf-8"))
        del data["_checkpoint_config"]
        path.write_text(json.dumps(data), encoding="utf-8")
        assert pipeline._load_checkpoint() is None

    def test_cache_identity_changes_with_reasoning(self, pipeline):
        original = pipeline._cache_prompt("same prompt")
        pipeline.config.provider.reasoning_effort = "high"
        assert pipeline._cache_prompt("same prompt") != original

    def test_cache_identity_changes_with_system_instruction(self, pipeline):
        original = pipeline._cache_prompt("same prompt")
        pipeline._instruction = "different instruction"
        assert pipeline._cache_prompt("same prompt") != original
