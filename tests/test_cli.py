"""Image reproducibility and CLI configuration tests."""

from src.cli import _image_seed


def test_image_seed_is_reproducible_and_asset_specific():
    assert _image_seed(42, "portrait", "Alma") == _image_seed(42, "portrait", "Alma")
    assert _image_seed(42, "portrait", "Alma") != _image_seed(42, "portrait", "Borin")
    assert _image_seed(42, "portrait", "Alma") != _image_seed(42, "site", "Alma")
    assert _image_seed(42, "portrait", "Alma") != _image_seed(43, "portrait", "Alma")
    assert 0 <= _image_seed(42, "portrait", "Alma") < 2**63
