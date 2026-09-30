"""Tests for procedural generation."""

import pytest

from src.procedural.population import generate_population
from src.procedural.names import get_name, get_last_name, get_first_name, get_group_name


class TestNameGeneration:
    def test_get_name_human(self):
        first, last = get_name("human", "male")
        assert first
        assert last

    def test_get_name_dwarf(self):
        first, last = get_name("dwarf", "female")
        assert first
        assert last

    def test_get_last_name(self):
        name = get_last_name("elf")
        assert name

    def test_get_first_name(self):
        name = get_first_name("halfling", "male")
        assert name

    def test_get_group_name(self):
        name = get_group_name()
        assert name

    def test_unknown_race_falls_back(self):
        first, last = get_name("orc", "male")
        assert first  # Falls back to human generator


class TestPopulationGeneration:
    @pytest.fixture
    def content(self):
        return {
            "generation": {"seed": 42, "mean_group_size": 7},
            "details": {
                "type": "small community",
                "population": 80,
                "races": {"human": 0.6, "dwarf": 0.2, "elf": 0.2},
            },
            "groups": {
                "activity": {
                    "g1": {
                        "population": 30,
                        "origin": {"local": 0.8, "foreign": 0.2},
                        "age_ratio": {"child": 0, "teen": 0.1, "adult": 0.7, "middle-aged": 0.1, "old": 0.1},
                    },
                    "g2": {
                        "population": 30,
                        "origin": {"local": 0.5, "foreign": 0.5},
                        "age_ratio": {"child": 0.1, "teen": 0.1, "adult": 0.5, "middle-aged": 0.2, "old": 0.1},
                    },
                    "g3": {
                        "population": 20,
                        "origin": {"local": 0.3, "foreign": 0.7},
                        "age_ratio": {"child": 0, "teen": 0.2, "adult": 0.6, "middle-aged": 0.1, "old": 0.1},
                    },
                }
            },
        }

    def test_generates_groups_and_npcs(self, content):
        result = generate_population(content)
        assert "groups" in result
        assert "social" in result["groups"]
        assert "npcs" in result

    def test_generates_expected_population(self, content):
        result = generate_population(content)
        total_npcs = len(result["npcs"])
        # Should be at least the target population (may exceed due to group sizes)
        assert total_npcs >= content["details"]["population"] * 0.8

    def test_no_duplicate_npc_ids(self, content):
        result = generate_population(content)
        npc_ids = list(result["npcs"].keys())
        assert len(npc_ids) == len(set(npc_ids))

    def test_npcs_have_required_fields(self, content):
        result = generate_population(content)
        for npc in result["npcs"].values():
            assert "first_name" in npc
            assert "last_name" in npc
            assert "full_name" in npc
            assert "race" in npc
            assert "gender" in npc
            assert "generation" in npc
            assert "group_position" in npc
            assert "social_group" in npc

    def test_npcs_have_appearance_fields(self, content):
        result = generate_population(content)
        appearance_fields = [
            "hair_color", "hair_length", "hair_style",
            "eye_color", "eye_shape", "skin_tone", "skin_texture",
            "face_shape", "nose_shape", "lip_shape", "chin_shape",
            "height", "weight", "age_look", "physical_detail",
            "portrait_pov", "facial_hair",
            "clothing_material", "clothing_color",
            "clothing_style", "clothing_accessory",
        ]
        for npc in result["npcs"].values():
            for field in appearance_fields:
                assert field in npc, f"Missing appearance field '{field}' on NPC {npc.get('full_name')}"

    def test_npcs_have_composite_fields(self, content):
        result = generate_population(content)
        for npc in result["npcs"].values():
            assert "hair" in npc
            assert "eyes" in npc
            assert "skin" in npc
            assert "clothes" in npc

    def test_race_distribution_reasonable(self, content):
        result = generate_population(content)
        races = [npc["race"] for npc in result["npcs"].values()]
        human_pct = races.count("human") / len(races)
        # Should be roughly in the range of the configured ratio (0.6)
        assert 0.3 < human_pct < 0.9

    def test_deterministic_with_same_seed(self, content):
        result1 = generate_population(content)
        result2 = generate_population(content)
        # Same seed should produce same group count and NPC count
        assert len(result1["groups"]["social"]) == len(result2["groups"]["social"])
        assert len(result1["npcs"]) == len(result2["npcs"])

    def test_groups_reference_valid_npcs(self, content):
        result = generate_population(content)
        for group in result["groups"]["social"].values():
            for member_id in group["members"]:
                assert member_id in result["npcs"]
