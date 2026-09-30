"""Tests for validators."""

import pytest

from src.parsers.json_parser import parse_json
from src.validators.bootstrap import validate_bootstrap
from src.validators.details import validate_detail, validate_descriptions
from src.validators.external_influences import validate_external_influences
from src.validators.population import validate_population_details
from src.validators.workplaces import validate_activity_groups
from tests.fixtures.mock_responses import (
    bootstrap,
    description,
    culture,
    external_influences,
    activity_groups,
)


class TestBootstrapValidator:
    def test_separates_setting_keywords(self):
        response = parse_json(bootstrap())
        patch = validate_bootstrap(response)

        assert "setting" in patch
        assert "keywords" in patch["setting"]
        assert len(patch["setting"]["keywords"]) == 10

    def test_wraps_categories_in_keywords(self):
        response = parse_json(bootstrap())
        patch = validate_bootstrap(response)

        for cat in ["culture", "customs", "goals", "resources", "history",
                     "external_influences", "timeline", "sites", "anecdotes"]:
            assert cat in patch["details"]
            assert "keywords" in patch["details"][cat]

    def test_direct_fields_preserved(self):
        response = parse_json(bootstrap())
        patch = validate_bootstrap(response)

        assert patch["details"]["name"] == "Rust Riders"
        assert patch["details"]["structure"] == "hierarchy"
        assert patch["details"]["prosperity"] == "low"


class TestDetailValidator:
    def test_wraps_in_descriptions(self):
        response = parse_json(culture())
        patch = validate_detail(response)

        assert "details" in patch
        assert "culture" in patch["details"]
        assert "descriptions" in patch["details"]["culture"]

    def test_descriptions_contains_titles(self):
        response = parse_json(culture())
        patch = validate_detail(response)

        desc = patch["details"]["culture"]["descriptions"]
        assert "A Resilient Brotherhood" in desc


class TestDescriptionsValidator:
    def test_adds_ordering(self):
        response = parse_json(description())
        patch = validate_descriptions(response)

        assert "details" in patch
        desc = patch["details"]["descriptions"]
        assert "order" in desc
        assert desc["order"] == ["Overview", "The Charismatic Leader"]


class TestExternalInfluencesValidator:
    def test_creates_uuid_keyed_groups(self):
        response = parse_json(external_influences())
        patch = validate_external_influences(response)

        groups = patch["details"]["external_influences"]["groups"]
        assert len(groups) == 2

        # All groups should have a name field
        for g in groups.values():
            assert "name" in g
            assert "type" in g


class TestActivityGroupsValidator:
    def test_normalizes_population(self):
        response = parse_json(activity_groups())
        content = {"details": {"population": 80}}
        patch = validate_activity_groups(content, response)

        assert "groups" in patch
        assert "activity" in patch["groups"]
        groups = patch["groups"]["activity"]
        total = sum(g["population"] for g in groups.values())
        # Should be close to target (rounding may cause small differences)
        assert abs(total - 80) <= len(groups)

    def test_creates_uuid_keys(self):
        response = parse_json(activity_groups())
        content = {"details": {"population": 20}}
        patch = validate_activity_groups(content, response)

        groups = patch["groups"]["activity"]
        for key in groups:
            assert len(key) > 10  # UUID-like


class TestPopulationValidator:
    def test_strips_old_visual_fields(self):
        """LLM may still return old visual fields — validator should strip them."""
        response = {
            "members": [
                {
                    "full_name": "John Smith",
                    "key_figure": False,
                    "age": 35,
                    "rank": "father",
                    "description": "A sturdy man",
                    "traits": "brave, kind, honest, loyal",
                    "clothes": "leather armor",  # should be stripped
                    "eyes": "brown",  # should be stripped
                    "hair": "dark",  # should be stripped
                    "skin": "tan",  # should be stripped
                    "height": "tall",  # should be stripped
                    "weight": "average",  # should be stripped
                    "age_look": "adult",  # should be stripped
                    "physical_detail": "scar",  # should be stripped
                    "clothes_detail": "embroidered cuffs",
                    "nickname": "Big John",
                    "secret": "hides gold",
                    "quote": "Stand firm.",
                    "relationship": "loves his family",
                    "structure_preference": "family",
                }
            ]
        }
        patch = validate_population_details(response)
        member = patch["npcs"]["John Smith"]

        # Old visual fields should be stripped
        for field in ("clothes", "eyes", "hair", "skin", "height", "weight",
                       "age_look", "physical_detail"):
            assert field not in member, f"Field '{field}' should have been stripped"

        # Non-visual fields should be preserved
        assert member["full_name"] == "John Smith"
        assert member["traits"] == "brave, kind, honest, loyal"
        assert member["clothes_detail"] == "embroidered cuffs"
        assert member["nickname"] == "Big John"

    def test_preserves_valid_fields(self):
        response = {
            "members": [
                {
                    "full_name": "Jane Doe",
                    "age": 28,
                    "rank": "daughter",
                    "description": "Cheerful",
                    "traits": "curious",
                    "clothes_detail": "",
                    "nickname": "Janie",
                    "secret": "none",
                    "quote": "Hello!",
                    "relationship": "sister",
                    "structure_preference": "team",
                }
            ]
        }
        patch = validate_population_details(response)
        member = patch["npcs"]["Jane Doe"]
        assert member["full_name"] == "Jane Doe"
        assert member["age"] == 28
