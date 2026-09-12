"""Fit-basis ortho scale with automatic cell fill and reserved margins."""
import pytest

from framemill.settings import (
    AA_MARGIN,
    FEET_GROUND_MARGIN,
    RenderSettings,
    fit_ortho_extent,
    fit_reserved_fraction,
    framing_ortho_scale,
    framing_target,
)


def _expected_scale(size, settings):
    aspect = settings.frame_width / settings.frame_height
    extent = fit_ortho_extent(size, settings.fit_basis, aspect)
    reserved = fit_reserved_fraction(settings.anchor)
    return extent / (1.0 - reserved) * settings.ortho_scale_mult


def test_fit_basis_tall_vs_wide_size():
    # Default cell is 96 x 128, so aspect = 0.75.
    # Tall: horiz 1, height 4 -> width extent = 1 / 0.75 = 4/3.
    # Wide: horiz 6, height 2 -> width extent = 6 / 0.75 = 8.
    tall = (1.0, 1.0, 4.0)
    wide = (6.0, 2.0, 2.0)
    common = {"framing_mode": "fit", "anchor": "center", "ortho_scale_mult": 2}
    height = RenderSettings(fit_basis="height", **common)
    width = RenderSettings(fit_basis="width", **common)
    contain = RenderSettings(fit_basis="contain", **common)
    assert framing_ortho_scale(height, tall) == pytest.approx(_expected_scale(tall, height))
    assert framing_ortho_scale(width, tall) == pytest.approx(_expected_scale(tall, width))
    assert framing_ortho_scale(contain, tall) == pytest.approx(_expected_scale(tall, contain))
    assert framing_ortho_scale(height, wide) == pytest.approx(_expected_scale(wide, height))
    assert framing_ortho_scale(width, wide) == pytest.approx(_expected_scale(wide, width))
    assert framing_ortho_scale(contain, wide) == pytest.approx(_expected_scale(wide, contain))
    assert framing_ortho_scale(contain, tall) > framing_ortho_scale(width, tall)
    assert framing_ortho_scale(contain, wide) == pytest.approx(framing_ortho_scale(width, wide))


def test_fit_basis_default_is_contain_and_roundtrips():
    settings = RenderSettings()
    assert settings.fit_basis == "contain"
    assert settings.ortho_scale_mult == 1.0
    assert RenderSettings.from_dict(settings.to_dict()).fit_basis == "contain"
    settings.fit_basis = "height"
    assert settings.render_config()["fit_basis"] == "height"


def test_invalid_fit_basis_is_rejected():
    with pytest.raises(ValueError, match="Fit basis"):
        RenderSettings(fit_basis="diagonal").validate()


def test_default_fit_fills_most_of_the_cell_without_clipping():
    settings = RenderSettings()
    center, size = (0.0, 0.0, 2.0), (1.0, 1.0, 4.0)
    scale = framing_ortho_scale(settings, size)
    assert size[2] / scale >= 0.90
    reserved = fit_reserved_fraction(settings.anchor)
    assert reserved == pytest.approx(AA_MARGIN + FEET_GROUND_MARGIN)
    aim = framing_target(center, size, settings)
    feet_z = center[2] - size[2] / 2.0
    head_z = center[2] + size[2] / 2.0
    window_bottom = aim[2] - scale / 2.0
    window_top = aim[2] + scale / 2.0
    assert window_bottom < feet_z
    assert window_top > head_z
    assert feet_z - window_bottom == pytest.approx(scale * FEET_GROUND_MARGIN)
    assert window_top - head_z == pytest.approx(scale * AA_MARGIN)
