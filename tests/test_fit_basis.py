"""Fit-basis ortho scale: height (default), width, and contain."""
import pytest

from framemill.settings import RenderSettings, framing_ortho_scale


def test_fit_basis_tall_vs_wide_size():
    # Default cell is 96 x 128, so aspect = 0.75.
    # Tall: horiz 1, height 4 -> width extent = 1 / 0.75 = 4/3.
    # Wide: horiz 6, height 2 -> width extent = 6 / 0.75 = 8.
    tall = (1.0, 1.0, 4.0)
    wide = (6.0, 2.0, 2.0)
    height = RenderSettings(framing_mode="fit", fit_basis="height", ortho_scale_mult=2)
    width = RenderSettings(framing_mode="fit", fit_basis="width", ortho_scale_mult=2)
    contain = RenderSettings(framing_mode="fit", fit_basis="contain", ortho_scale_mult=2)
    assert framing_ortho_scale(height, tall) == pytest.approx(8)
    assert framing_ortho_scale(width, tall) == pytest.approx(8 / 3)
    assert framing_ortho_scale(contain, tall) == pytest.approx(8)
    assert framing_ortho_scale(height, wide) == pytest.approx(4)
    assert framing_ortho_scale(width, wide) == pytest.approx(16)
    assert framing_ortho_scale(contain, wide) == pytest.approx(16)


def test_fit_basis_default_matches_height_and_roundtrips():
    settings = RenderSettings()
    assert settings.fit_basis == "height"
    assert RenderSettings.from_dict(settings.to_dict()).fit_basis == "height"
    settings.fit_basis = "contain"
    assert settings.render_config()["fit_basis"] == "contain"


def test_invalid_fit_basis_is_rejected():
    with pytest.raises(ValueError, match="Fit basis"):
        RenderSettings(fit_basis="diagonal").validate()
