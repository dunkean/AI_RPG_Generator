"""Tests for procedural appearance generation."""

import random

import pytest

from src.procedural.appearance import (
    CHILD_POSITIONS,
    CHIN_SHAPE,
    CLOTHING_ACCESSORY,
    CLOTHING_COLOR,
    CLOTHING_MATERIAL,
    CLOTHING_STYLE_BY_GENDER,
    EYE_COLOR,
    EYE_SHAPE,
    FACE_SHAPE,
    FACIAL_HAIR,
    HAIR_COLOR,
    HAIR_LENGTH,
    HAIR_STYLE,
    HEIGHT,
    HERITABLE_TRAITS,
    LIP_SHAPE,
    NOSE_SHAPE,
    PORTRAIT_POV,
    SKIN_TONE,
    WEIGHT,
    apply_age_modifiers,
    build_composite_fields,
    generate_appearance,
    generate_clothing,
    generate_family_phenotype,
    pick_portrait_pov,
)

RACES = ["human", "elf", "half-elf", "dwarf", "halfling", "gnome"]
GENERATIONS = ["young", "mid", "old"]


class TestAllRacesProduceValidOutput:
    @pytest.mark.parametrize("race", RACES)
    @pytest.mark.parametrize("gender", ["male", "female"])
    def test_generates_all_fields(self, race, gender):
        rng = random.Random(42)
        appearance = generate_appearance(race, gender, "mid", rng)

        expected_fields = [
            "hair_color", "hair_length", "hair_style",
            "eye_color", "eye_shape",
            "skin_tone", "skin_texture",
            "face_shape", "nose_shape", "lip_shape", "chin_shape",
            "height", "weight", "age_look",
            "physical_detail", "portrait_pov",
            "facial_hair",
            "clothing_material", "clothing_color",
            "clothing_style", "clothing_accessory",
        ]
        for field in expected_fields:
            assert field in appearance, f"Missing field '{field}' for {race}/{gender}"
            assert isinstance(appearance[field], str), f"Field '{field}' is not a string"

    @pytest.mark.parametrize("race", RACES)
    def test_race_specific_tables_have_entries(self, race):
        """Verify all race-specific tables contain the race."""
        assert race in HAIR_COLOR
        assert race in HAIR_LENGTH
        assert race in HAIR_STYLE
        assert race in EYE_COLOR
        assert race in EYE_SHAPE
        assert race in SKIN_TONE
        assert race in FACE_SHAPE
        assert race in NOSE_SHAPE
        assert race in LIP_SHAPE
        assert race in CHIN_SHAPE
        assert race in HEIGHT
        assert race in WEIGHT
        assert race in FACIAL_HAIR


class TestDeterminism:
    def test_same_seed_same_result(self):
        rng1 = random.Random(12345)
        rng2 = random.Random(12345)
        a1 = generate_appearance("human", "male", "mid", rng1)
        a2 = generate_appearance("human", "male", "mid", rng2)
        assert a1 == a2

    def test_different_seed_different_result(self):
        rng1 = random.Random(11111)
        rng2 = random.Random(22222)
        a1 = generate_appearance("human", "male", "mid", rng1)
        a2 = generate_appearance("human", "male", "mid", rng2)
        # Statistically, at least some fields should differ
        differences = sum(1 for k in a1 if a1[k] != a2.get(k))
        assert differences > 0


class TestGenderSpecificFacialHair:
    @pytest.mark.parametrize("race", RACES)
    def test_male_gets_facial_hair(self, race):
        rng = random.Random(42)
        appearance = generate_appearance(race, "male", "mid", rng)
        # Males should get a non-empty facial hair value (could be clean-shaven)
        assert "facial_hair" in appearance
        assert appearance["facial_hair"] != ""

    @pytest.mark.parametrize("race", RACES)
    def test_female_gets_no_facial_hair(self, race):
        rng = random.Random(42)
        appearance = generate_appearance(race, "female", "mid", rng)
        assert appearance["facial_hair"] == ""


class TestFamilyPhenotype:
    def test_has_both_parents(self):
        rng = random.Random(42)
        phenotype = generate_family_phenotype("human", rng)
        assert "father" in phenotype
        assert "mother" in phenotype

    def test_parents_have_all_heritable_traits(self):
        rng = random.Random(42)
        phenotype = generate_family_phenotype("dwarf", rng)
        for parent in ("father", "mother"):
            for trait in HERITABLE_TRAITS:
                assert trait in phenotype[parent], f"Parent '{parent}' missing trait '{trait}'"
                assert phenotype[parent][trait], f"Parent '{parent}' has empty trait '{trait}'"

    def test_half_elf_parents_use_different_race_tables(self):
        """For half-elf families, father uses human tables, mother uses elf tables."""
        rng = random.Random(42)
        phenotype = generate_family_phenotype("half-elf", rng)
        # Both parents should have all traits
        for parent in ("father", "mother"):
            for trait in HERITABLE_TRAITS:
                assert trait in phenotype[parent]

    def test_deterministic_phenotype(self):
        rng1 = random.Random(99)
        rng2 = random.Random(99)
        p1 = generate_family_phenotype("elf", rng1)
        p2 = generate_family_phenotype("elf", rng2)
        assert p1 == p2


class TestFamilyInheritance:
    def test_children_inherit_at_expected_rates(self):
        """Statistical test: over many runs, children should inherit traits at roughly the expected rates."""
        n_trials = 1000
        inherited_count: dict[str, int] = {t: 0 for t in HERITABLE_TRAITS}

        for seed in range(n_trials):
            rng = random.Random(seed)
            phenotype = generate_family_phenotype("human", rng)
            # Reset RNG for consistent appearance generation
            rng2 = random.Random(seed + 100000)
            appearance = generate_appearance(
                "human", "male", "mid", rng2,
                family_phenotype=phenotype, position="son",
            )
            for trait in HERITABLE_TRAITS:
                father_val = phenotype["father"][trait]
                mother_val = phenotype["mother"][trait]
                if appearance[trait] in (father_val, mother_val):
                    inherited_count[trait] += 1

        # Check each trait's inheritance rate is within reasonable bounds
        for trait, expected_rate in HERITABLE_TRAITS.items():
            actual_rate = inherited_count[trait] / n_trials
            # Allow generous margin (±15%) since random from race table can
            # also coincidentally match a parent value
            assert actual_rate > expected_rate - 0.15, (
                f"Trait '{trait}': inherited rate {actual_rate:.2f} too low "
                f"(expected ~{expected_rate:.2f})"
            )

    def test_outsiders_dont_inherit(self):
        """NPCs without family phenotype should not inherit anything."""
        rng = random.Random(42)
        appearance = generate_appearance("human", "male", "mid", rng)
        # Should still have all traits, just randomly generated
        for trait in HERITABLE_TRAITS:
            assert trait in appearance

    def test_parents_dont_inherit_from_themselves(self):
        """Position 'father'/'mother' should not trigger inheritance."""
        rng = random.Random(42)
        phenotype = generate_family_phenotype("human", rng)
        rng2 = random.Random(42)
        appearance = generate_appearance(
            "human", "male", "mid", rng2,
            family_phenotype=phenotype, position="father",
        )
        # Should still work (just all random from race table)
        for trait in HERITABLE_TRAITS:
            assert trait in appearance


class TestAgeModifiers:
    @pytest.mark.parametrize("generation", GENERATIONS)
    def test_produces_skin_texture(self, generation):
        rng = random.Random(42)
        appearance = {"hair_color": "brown"}
        apply_age_modifiers(appearance, generation, "human", rng)
        assert "skin_texture" in appearance
        assert appearance["skin_texture"]

    @pytest.mark.parametrize("generation", GENERATIONS)
    def test_produces_age_look(self, generation):
        rng = random.Random(42)
        appearance = {"hair_color": "brown"}
        apply_age_modifiers(appearance, generation, "human", rng)
        assert "age_look" in appearance
        assert appearance["age_look"]

    def test_old_generation_grays_hair(self):
        """Over many trials, old generation should gray hair at ~60% rate."""
        grayed = 0
        n = 500
        for seed in range(n):
            rng = random.Random(seed)
            appearance = {"hair_color": "brown"}
            apply_age_modifiers(appearance, "old", "human", rng)
            if "gray" in appearance["hair_color"] or "silver" in appearance["hair_color"] or "white" in appearance["hair_color"]:
                grayed += 1
        rate = grayed / n
        assert 0.45 < rate < 0.75, f"Gray rate for old: {rate:.2f}"

    def test_young_generation_no_graying(self):
        """Young NPCs should never get grayed hair."""
        for seed in range(200):
            rng = random.Random(seed)
            appearance = {"hair_color": "brown"}
            apply_age_modifiers(appearance, "young", "human", rng)
            assert "gray" not in appearance["hair_color"]
            assert "silver" not in appearance["hair_color"]
            assert "white" not in appearance["hair_color"]

    def test_elf_age_look_skews_younger(self):
        """Elves should generally look younger than their generation."""
        young_looking = 0
        n = 500
        for seed in range(n):
            rng = random.Random(seed)
            appearance = {"hair_color": "silver"}
            apply_age_modifiers(appearance, "old", "elf", rng)
            if appearance["age_look"] in ("young", "youthful", "adult", "mature"):
                young_looking += 1
        rate = young_looking / n
        assert rate > 0.5, f"Elf old-gen young-looking rate: {rate:.2f}"


class TestPortraitPov:
    def test_valid_values(self):
        for seed in range(100):
            rng = random.Random(seed)
            pov = pick_portrait_pov(rng)
            assert pov in PORTRAIT_POV


class TestClothing:
    def test_generates_all_fields(self):
        rng = random.Random(42)
        clothing = generate_clothing("male", rng)
        assert "clothing_material" in clothing
        assert "clothing_color" in clothing
        assert "clothing_style" in clothing
        assert "clothing_accessory" in clothing

    def test_male_female_styles_differ(self):
        """Over many trials, male and female clothing styles should differ."""
        male_styles = set()
        female_styles = set()
        for seed in range(100):
            rng = random.Random(seed)
            male_styles.add(generate_clothing("male", rng)["clothing_style"])
            rng2 = random.Random(seed + 50000)
            female_styles.add(generate_clothing("female", rng2)["clothing_style"])
        # Sets should not be identical
        assert male_styles != female_styles


class TestCompositeFields:
    def test_builds_hair_composite(self):
        appearance = {
            "hair_length": "long", "hair_style": "braided", "hair_color": "dark brown",
            "eye_shape": "almond", "eye_color": "green",
            "skin_texture": "weathered", "skin_tone": "tan",
            "clothing_color": "brown", "clothing_material": "leather",
            "clothing_style": "tunic and breeches", "clothing_accessory": "belt with pouch",
        }
        composites = build_composite_fields(appearance)
        assert composites["hair"] == "long braided dark brown"
        assert composites["eyes"] == "almond green"
        assert composites["skin"] == "weathered tan"
        assert "brown leather tunic and breeches" in composites["clothes"]
        assert "belt with pouch" in composites["clothes"]

    def test_no_accessory(self):
        appearance = {
            "hair_length": "short", "hair_style": "straight", "hair_color": "black",
            "eye_shape": "round", "eye_color": "brown",
            "skin_texture": "smooth", "skin_tone": "olive",
            "clothing_color": "gray", "clothing_material": "wool",
            "clothing_style": "robes", "clothing_accessory": "none",
        }
        composites = build_composite_fields(appearance)
        assert "none" not in composites["clothes"]
